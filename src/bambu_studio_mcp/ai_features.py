"""AI-Enhanced 3D Printing Pipelines: CIELAB AMS Color Matching, Mesh Auto-Repair, and Model Discovery.

Credits & Upstream Inspiration:
- heyixuan2/bambu-studio-ai (https://github.com/heyixuan2/bambu-studio-ai) — End-to-end 3D printing agent workflow,
  11-point printability audit concept, CIELAB perceptual AMS color mapping, and MakerWorld/Printables discovery.
- mikedh/trimesh (https://github.com/mikedh/trimesh) — Mesh topology & repair conventions.
- bambulabs_api (https://github.com/BambuTools/bambulabs_api) — Bambu Lab telemetry & AMS spool conventions.
"""

from __future__ import annotations

import json
import math
import re
import struct
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Official Bambu Lab PLA Basic reference palette (Hex -> Name)
BAMBU_DEFAULT_PALETTE: List[Dict[str, str]] = [
    {"slot": "Bambu PLA Basic Jade White", "hex": "#FFFFFF", "material": "PLA"},
    {"slot": "Bambu PLA Basic Black", "hex": "#000000", "material": "PLA"},
    {"slot": "Bambu PLA Basic Gray", "hex": "#8E9089", "material": "PLA"},
    {"slot": "Bambu PLA Basic Silver", "hex": "#A6A9AA", "material": "PLA"},
    {"slot": "Bambu PLA Basic Red", "hex": "#C12E1F", "material": "PLA"},
    {"slot": "Bambu PLA Basic Orange", "hex": "#FF6A13", "material": "PLA"},
    {"slot": "Bambu PLA Basic Sunflower Yellow", "hex": "#FEC600", "material": "PLA"},
    {"slot": "Bambu PLA Basic Bambu Green", "hex": "#00AE42", "material": "PLA"},
    {"slot": "Bambu PLA Basic Mistletoe Green", "hex": "#3F8E43", "material": "PLA"},
    {"slot": "Bambu PLA Basic Cyan", "hex": "#0086D6", "material": "PLA"},
    {"slot": "Bambu PLA Basic Blue", "hex": "#0A2989", "material": "PLA"},
    {"slot": "Bambu PLA Basic Purple", "hex": "#5E43B7", "material": "PLA"},
    {"slot": "Bambu PLA Basic Magenta", "hex": "#EC008C", "material": "PLA"},
    {"slot": "Bambu PLA Basic Pink", "hex": "#F55A74", "material": "PLA"},
    {"slot": "Bambu PLA Basic Beige", "hex": "#F7E6DE", "material": "PLA"},
    {"slot": "Bambu PLA Basic Brown", "hex": "#9D432C", "material": "PLA"},
    {"slot": "Bambu PLA Basic Gold", "hex": "#E4BD68", "material": "PLA"},
]


def _parse_hex_rgb(color_str: str) -> Tuple[int, int, int]:
    """Parse '#RRGGBB', '#RRGGBBAA', or 'R,G,B' into (R, G, B) in 0..255."""
    s = color_str.strip()
    if "," in s:
        parts = [int(x.strip()) for x in s.split(",")[:3]]
        return (
            max(0, min(255, parts[0])),
            max(0, min(255, parts[1])),
            max(0, min(255, parts[2])),
        )
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) >= 6:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    raise ValueError(f"Unrecognized color format: '{color_str}' (expected '#RRGGBB' or 'R,G,B')")


def _rgb_to_cielab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert sRGB (0..255) to CIE 1976 (L*, a*, b*) under D65 illuminant."""
    def pivot_rgb(c: float) -> float:
        c_norm = c / 255.0
        return ((c_norm + 0.055) / 1.055) ** 2.4 if c_norm > 0.04045 else c_norm / 12.92

    rl, gl, bl = pivot_rgb(r), pivot_rgb(g), pivot_rgb(b)

    # sRGB to XYZ (D65)
    x = (rl * 0.4124564 + gl * 0.3575761 + bl * 0.1804375) / 0.95047
    y = (rl * 0.2126729 + gl * 0.7151522 + bl * 0.0721750) / 1.00000
    z = (rl * 0.0193339 + gl * 0.1191920 + bl * 0.9503041) / 1.08883

    def pivot_xyz(t: float) -> float:
        return t ** (1.0 / 3.0) if t > 0.008856 else (7.787 * t) + (16.0 / 116.0)

    fx, fy, fz = pivot_xyz(x), pivot_xyz(y), pivot_xyz(z)
    L = (116.0 * fy) - 16.0
    a = 500.0 * (fx - fy)
    b_val = 200.0 * (fy - fz)
    return (L, a, b_val)


def _ciede2000(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
    """Compute perceptual CIEDE2000 (Delta E 2000) color difference between two CIELAB colors."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    C_bar = 0.5 * (C1 + C2)
    C_bar7 = C_bar ** 7
    G = 0.5 * (1.0 - math.sqrt(C_bar7 / (C_bar7 + 25.0 ** 7)))

    a1_p = (1.0 + G) * a1
    a2_p = (1.0 + G) * a2
    C1_p = math.hypot(a1_p, b1)
    C2_p = math.hypot(a2_p, b2)

    h1_p = math.degrees(math.atan2(b1, a1_p)) % 360.0 if C1_p > 1e-9 else 0.0
    h2_p = math.degrees(math.atan2(b2, a2_p)) % 360.0 if C2_p > 1e-9 else 0.0

    dL_p = L2 - L1
    dC_p = C2_p - C1_p

    if C1_p * C2_p == 0.0:
        dh_p = 0.0
    else:
        diff = h2_p - h1_p
        if abs(diff) <= 180.0:
            dh_p = diff
        elif diff > 180.0:
            dh_p = diff - 360.0
        else:
            dh_p = diff + 360.0

    dH_p = 2.0 * math.sqrt(C1_p * C2_p) * math.sin(math.radians(dh_p * 0.5))

    L_bar_p = 0.5 * (L1 + L2)
    C_bar_p = 0.5 * (C1_p + C2_p)

    if C1_p * C2_p == 0.0:
        h_bar_p = h1_p + h2_p
    else:
        if abs(h1_p - h2_p) <= 180.0:
            h_bar_p = 0.5 * (h1_p + h2_p)
        elif (h1_p + h2_p) < 360.0:
            h_bar_p = 0.5 * (h1_p + h2_p + 360.0)
        else:
            h_bar_p = 0.5 * (h1_p + h2_p - 360.0)

    T = (
        1.0
        - 0.17 * math.cos(math.radians(h_bar_p - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * h_bar_p))
        + 0.32 * math.cos(math.radians(3.0 * h_bar_p + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * h_bar_p - 63.0))
    )

    d_theta = 30.0 * math.exp(-(((h_bar_p - 275.0) / 25.0) ** 2))
    C_bar_p7 = C_bar_p ** 7
    R_C = 2.0 * math.sqrt(C_bar_p7 / (C_bar_p7 + 25.0 ** 7))
    S_L = 1.0 + (0.015 * ((L_bar_p - 50.0) ** 2)) / math.sqrt(20.0 + ((L_bar_p - 50.0) ** 2))
    S_C = 1.0 + 0.045 * C_bar_p
    S_H = 1.0 + 0.015 * C_bar_p * T
    R_T = -math.sin(math.radians(2.0 * d_theta)) * R_C

    de00 = math.sqrt(
        (dL_p / S_L) ** 2
        + (dC_p / S_C) ** 2
        + (dH_p / S_H) ** 2
        + R_T * (dC_p / S_C) * (dH_p / S_H)
    )
    return de00


def _extract_spools_from_3mf(path_3mf: Path) -> List[Dict[str, str]]:
    """Extract loaded project filament slots and hex colors from a Bambu Studio .3mf archive."""
    spools: List[Dict[str, str]] = []
    if not path_3mf.exists() or not zipfile.is_zipfile(path_3mf):
        return spools

    with zipfile.ZipFile(path_3mf, "r") as zf:
        if "Metadata/project_settings.config" in zf.namelist():
            try:
                cfg = json.loads(
                    zf.read("Metadata/project_settings.config").decode("utf-8", errors="replace")
                )
                colors = cfg.get("filament_colour", [])
                types = cfg.get("filament_type", [])
                vendors = cfg.get("filament_vendor", [])
                for i, hex_col in enumerate(colors):
                    mat = types[i] if i < len(types) else "PLA"
                    ven = vendors[i] if i < len(vendors) else "Bambu"
                    spools.append({
                        "slot": f"Project Filament #{i + 1} ({ven} {mat})",
                        "hex": hex_col,
                        "material": mat,
                    })
            except Exception:
                pass
    return spools


def match_ams_colors_cielab(
    target_colors: List[str],
    available_spools: Optional[List[Dict[str, str]]] = None,
    project_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Match target RGB/Hex colors to the closest AMS filament spools using perceptual CIELAB (Delta E 2000).

    Inspired by heyixuan2/bambu-studio-ai CIELAB nearest-neighbor AMS color mapping.
    """
    spools: List[Dict[str, str]] = []
    palette_source = "Bambu PLA Basic Reference Palette (17 colors)"

    if available_spools:
        spools = available_spools
        palette_source = f"Custom Provided Spools ({len(spools)} spools)"
    elif project_3mf_path:
        extracted = _extract_spools_from_3mf(Path(project_3mf_path))
        if extracted:
            spools = extracted
            palette_source = f"Extracted from 3MF Project '{Path(project_3mf_path).name}' ({len(spools)} slots)"

    if not spools:
        spools = BAMBU_DEFAULT_PALETTE

    parsed_spools = []
    for sp in spools:
        hex_str = sp.get("hex") or sp.get("color") or "#FFFFFF"
        try:
            rgb = _parse_hex_rgb(hex_str)
            lab = _rgb_to_cielab(*rgb)
            parsed_spools.append({
                "slot": sp.get("slot") or sp.get("name") or hex_str,
                "hex": f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}",
                "material": sp.get("material", "PLA"),
                "rgb": rgb,
                "lab": lab,
            })
        except Exception:
            continue

    mappings = []
    for target in target_colors:
        try:
            t_rgb = _parse_hex_rgb(target)
            t_lab = _rgb_to_cielab(*t_rgb)
        except Exception as exc:
            mappings.append({"target_color": target, "error": str(exc)})
            continue

        ranked = []
        for sp in parsed_spools:
            de00 = _ciede2000(t_lab, sp["lab"])
            ranked.append({
                "slot": sp["slot"],
                "spool_hex": sp["hex"],
                "material": sp["material"],
                "delta_e_2000": round(de00, 2),
            })
        ranked.sort(key=lambda x: x["delta_e_2000"])
        best = ranked[0] if ranked else None
        de = best["delta_e_2000"] if best else 999.0

        if de < 2.3:
            quality = "Exact / Imperceptible Difference (Delta E < 2.3)"
        elif de < 6.0:
            quality = "Close Visual Match (Delta E < 6.0)"
        elif de < 15.0:
            quality = "Noticeable Shade Difference (Delta E < 15.0)"
        else:
            quality = "Distinct Color — Consider loading a closer spool (Delta E >= 15.0)"

        mappings.append({
            "target_input": target,
            "target_hex": f"#{t_rgb[0]:02X}{t_rgb[1]:02X}{t_rgb[2]:02X}",
            "target_cielab": {"L": round(t_lab[0], 1), "a": round(t_lab[1], 1), "b": round(t_lab[2], 1)},
            "best_match": best,
            "match_quality": quality,
            "runner_up_matches": ranked[1:3],
        })

    return {
        "credits": "Perceptual CIELAB (Delta E 2000) AMS color mapping inspired by heyixuan2/bambu-studio-ai",
        "palette_source": palette_source,
        "color_mappings": mappings,
    }


def repair_and_ground_stl(
    input_stl_path: str,
    output_stl_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Auto-repair an STL mesh: remove zero-area degenerate faces, fix inverted normals, and ground onto Z=0.0.

    Inspired by heyixuan2/bambu-studio-ai & mikedh/trimesh automated mesh repair pipeline.
    """
    src = Path(input_stl_path)
    if not src.exists():
        return {"error": f"Input STL not found: '{input_stl_path}'"}

    data = src.read_bytes()
    if len(data) < 84:
        return {"error": "File is too small to be a valid STL."}

    tri_count_bin = struct.unpack("<I", data[80:84])[0]
    expected_size = 84 + tri_count_bin * 50

    raw_tris: List[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]] = []
    if len(data) == expected_size:
        offset = 84
        for _ in range(tri_count_bin):
            vals = struct.unpack_from("<12fH", data, offset)
            offset += 50
            v0 = (vals[3], vals[4], vals[5])
            v1 = (vals[6], vals[7], vals[8])
            v2 = (vals[9], vals[10], vals[11])
            raw_tris.append((v0, v1, v2))
    else:
        text = data.decode("utf-8", errors="ignore")
        verts = []
        for line in text.splitlines():
            ls = line.strip()
            if ls.startswith("vertex"):
                parts = ls.split()
                if len(parts) >= 4:
                    verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
        for i in range(0, (len(verts) // 3) * 3, 3):
            raw_tris.append((verts[i], verts[i + 1], verts[i + 2]))

    valid_tris = []
    removed_degenerate = 0
    removed_duplicates = 0
    seen_faces = set()
    total_signed_vol = 0.0
    min_z = float("inf")

    for v0, v1, v2 in raw_tris:
        ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
        bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
        cx = ay * bz - az * by
        cy = az * bx - ax * bz
        cz = ax * by - ay * bx
        norm = math.sqrt(cx * cx + cy * cy + cz * cz)
        area = 0.5 * norm
        if area < 1e-7:
            removed_degenerate += 1
            continue

        # Deduplicate identical triangles
        q_face = tuple(
            sorted(
                (
                    (round(v0[0], 4), round(v0[1], 4), round(v0[2], 4)),
                    (round(v1[0], 4), round(v1[1], 4), round(v1[2], 4)),
                    (round(v2[0], 4), round(v2[1], 4), round(v2[2], 4)),
                )
            )
        )
        if q_face in seen_faces:
            removed_duplicates += 1
            continue
        seen_faces.add(q_face)

        svol = (
            v0[0] * (v1[1] * v2[2] - v1[2] * v2[1])
            - v0[1] * (v1[0] * v2[2] - v1[2] * v2[0])
            + v0[2] * (v1[0] * v2[1] - v1[1] * v2[0])
        ) / 6.0
        total_signed_vol += svol
        min_z = min(min_z, v0[2], v1[2], v2[2])
        valid_tris.append((v0, v1, v2))

    flipped_normals = False
    if total_signed_vol < 0.0:
        # Invert winding (v0, v2, v1) so face normals point outward
        valid_tris = [(v0, v2, v1) for (v0, v1, v2) in valid_tris]
        flipped_normals = True

    z_shift = -min_z if min_z != float("inf") else 0.0
    dest = Path(output_stl_path) if output_stl_path else src.with_name(f"{src.stem}_repaired.stl")
    dest.parent.mkdir(parents=True, exist_ok=True)

    header = b"Repaired by bambu-studio-mcp (credits: heyixuan2 & trimesh)".ljust(80, b"\x00")
    out_buf = bytearray(header)
    out_buf.extend(struct.pack("<I", len(valid_tris)))

    for v0, v1, v2 in valid_tris:
        v0z = (v0[0], v0[1], v0[2] + z_shift)
        v1z = (v1[0], v1[1], v1[2] + z_shift)
        v2z = (v2[0], v2[1], v2[2] + z_shift)
        ax, ay, az = v1z[0] - v0z[0], v1z[1] - v0z[1], v1z[2] - v0z[2]
        bx, by, bz = v2z[0] - v0z[0], v2z[1] - v0z[1], v2z[2] - v0z[2]
        cx = ay * bz - az * by
        cy = az * bx - ax * bz
        cz = ax * by - ay * bx
        norm = math.sqrt(cx * cx + cy * cy + cz * cz) or 1.0
        nx, ny, nz = cx / norm, cy / norm, cz / norm
        out_buf.extend(
            struct.pack(
                "<12fH",
                nx, ny, nz,
                v0z[0], v0z[1], v0z[2],
                v1z[0], v1z[1], v1z[2],
                v2z[0], v2z[1], v2z[2],
                0,
            )
        )

    dest.write_bytes(bytes(out_buf))
    return {
        "success": True,
        "credits": "Mesh repair pipeline inspired by heyixuan2/bambu-studio-ai & mikedh/trimesh",
        "input_stl": str(src),
        "output_stl": str(dest),
        "original_triangles": len(raw_tris),
        "repaired_triangles": len(valid_tris),
        "removed_degenerate_triangles": removed_degenerate,
        "removed_duplicate_triangles": removed_duplicates,
        "flipped_inverted_normals": flipped_normals,
        "z_grounded_shift_mm": round(z_shift, 4),
    }


def search_3d_models(
    query: str,
    platform: str = "all",
    max_results: int = 8,
) -> Dict[str, Any]:
    """Search MakerWorld, Printables, and Thangs for ready-to-print 3D models.

    Inspired by heyixuan2/bambu-studio-ai model discovery pipeline.
    """
    q_clean = query.strip()
    q_encoded = urllib.parse.quote_plus(q_clean)
    plat = platform.lower().strip()

    direct_search_portals = {
        "makerworld": f"https://makerworld.com/en/search/models?keyword={q_encoded}",
        "printables": f"https://www.printables.com/search/models?q={q_encoded}",
        "thangs": f"https://thangs.com/search/{q_encoded}?scope=all",
    }

    results: List[Dict[str, Any]] = []

    # 1. Query Printables GraphQL API for live 3D printable models
    if plat in ("all", "printables"):
        try:
            gql_payload = json.dumps({
                "operationName": "SearchModels",
                "variables": {
                    "query": q_clean,
                    "limit": min(max_results, 10),
                    "ordering": "makes_count",
                },
                "query": (
                    "query SearchModels($query: String!, $limit: Int, $ordering: SearchChoicesEnum) {"
                    "  result: searchPrints2(query: $query, limit: $limit, ordering: $ordering) {"
                    "    items { id name slug likesCount downloadCount datePublished }"
                    "  }"
                    "}"
                ),
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.printables.com/graphql/",
                data=gql_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                items = ((data.get("data") or {}).get("result") or {}).get("items") or []
                for it in items[:max_results]:
                    mod_id = it.get("id")
                    slug = it.get("slug", "")
                    results.append({
                        "platform": "Printables",
                        "title": it.get("name"),
                        "url": f"https://www.printables.com/model/{mod_id}-{slug}",
                        "downloads": it.get("downloadCount"),
                        "likes": it.get("likesCount"),
                    })
        except Exception:
            pass

    # 2. Query DuckDuckGo HTML lite for MakerWorld direct model links
    if plat in ("all", "makerworld"):
        try:
            ddg_q = urllib.parse.quote_plus(f"site:makerworld.com/en/models {q_clean}")
            req = urllib.request.Request(
                f"https://html.duckduckgo.com/html/?q={ddg_q}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                matches = re.findall(
                    r'href="[^"]*?(https?://makerworld\.com/[a-z]{2}/models/\d+[^"&]*)"[^>]*>(.*?)</a>',
                    html,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                seen_urls = set()
                for raw_url, raw_title in matches:
                    url = urllib.parse.unquote(raw_url).split("#")[0]
                    title = re.sub(r"<[^>]+>", "", raw_title).strip()
                    if url not in seen_urls and title:
                        seen_urls.add(url)
                        results.append({
                            "platform": "MakerWorld",
                            "title": title,
                            "url": url,
                        })
                        if len(seen_urls) >= max_results:
                            break
        except Exception:
            pass

    return {
        "credits": "3D model discovery inspired by heyixuan2/bambu-studio-ai",
        "query": q_clean,
        "direct_search_urls": direct_search_portals,
        "models_found": len(results),
        "results": results[:max_results],
        "workflow_tip": (
            "Download the .3mf or .stl from MakerWorld/Printables, then run 'inspect_3d_model' "
            "for the 11-point printability audit or 'open_in_bambu_studio' to load it directly."
        ),
    }
