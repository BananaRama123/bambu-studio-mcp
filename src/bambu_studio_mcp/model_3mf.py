"""3MF and STL Geometry Inspector, 11-Point Printability Analyzer, and Bambu Project Modifier.

11-Point Printability Analysis inspired by:
- heyixuan2/bambu-studio-ai (https://github.com/heyixuan2/bambu-studio-ai)
- mikedh/trimesh (https://github.com/mikedh/trimesh)
"""

from __future__ import annotations

import json
import math
import shutil
import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


Vec3 = Tuple[float, float, float]


def _compute_11_point_printability(
    triangles: List[Tuple[Vec3, Vec3, Vec3]],
    size_xyz_mm: Tuple[float, float, float],
    min_z: float,
    total_signed_vol: float,
    bottom_contact_mm2: float,
    overhang_area_mm2: float,
) -> Dict[str, Any]:
    """Run an 11-point mesh topology & printability audit inspired by heyixuan2/bambu-studio-ai and trimesh."""
    sx, sy, sz = size_xyz_mm
    tri_count = len(triangles)

    # Quantize vertices to 0.001 mm for topological edge/shell analysis
    # Cap full topology graph at 120,000 triangles to keep pure-Python latency < 0.4s
    topology_analyzed = tri_count <= 120000 and tri_count > 0
    edge_counts: Dict[Tuple[int, int], int] = {}
    vert_map: Dict[Tuple[int, int, int], int] = {}
    parent: List[int] = []
    vert_min_z: List[float] = []

    def find_root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    degenerate_triangles = 0
    bridge_area_mm2 = 0.0
    severe_overhang_mm2 = 0.0
    severe_nz_threshold = -math.cos(math.radians(25.0))  # <25 deg from horizontal (>65 deg from vertical)

    for v0, v1, v2 in triangles:
        area, _, nz = _triangle_metrics(v0, v1, v2)
        if area < 1e-7:
            degenerate_triangles += 1
        avg_z = (v0[2] + v1[2] + v2[2]) / 3.0
        if avg_z > min_z + 1.0:
            if nz < -0.95:
                bridge_area_mm2 += area
            elif nz < severe_nz_threshold:
                severe_overhang_mm2 += area

        if topology_analyzed:
            idxs = []
            for vx, vy, vz in (v0, v1, v2):
                key = (int(round(vx * 1000)), int(round(vy * 1000)), int(round(vz * 1000)))
                idx = vert_map.get(key)
                if idx is None:
                    idx = len(parent)
                    vert_map[key] = idx
                    parent.append(idx)
                    vert_min_z.append(vz)
                idxs.append(idx)

            i0, i1, i2 = idxs
            # Union connected vertices for shell / island detection
            r0, r1, r2 = find_root(i0), find_root(i1), find_root(i2)
            if r0 != r1:
                parent[r1] = r0
                vert_min_z[r0] = min(vert_min_z[r0], vert_min_z[r1])
            r0 = find_root(i0)
            if r0 != r2:
                parent[r2] = r0
                vert_min_z[r0] = min(vert_min_z[r0], vert_min_z[r2])

            for a, b in ((i0, i1), (i1, i2), (i2, i0)):
                if a != b:
                    e = (a, b) if a < b else (b, a)
                    edge_counts[e] = edge_counts.get(e, 0) + 1

    boundary_edges = 0
    non_manifold_edges = 0
    shell_count = 1
    floating_islands = 0

    if topology_analyzed:
        for count in edge_counts.values():
            if count == 1:
                boundary_edges += 1
            elif count > 2:
                non_manifold_edges += 1

        roots: Dict[int, float] = {}
        for idx in range(len(parent)):
            r = find_root(idx)
            if r not in roots:
                roots[r] = vert_min_z[r]
            else:
                roots[r] = min(roots[r], vert_min_z[r])
        shell_count = len(roots)
        floating_islands = sum(1 for z_low in roots.values() if z_low > min_z + 0.6)

    is_watertight = topology_analyzed and boundary_edges == 0 and non_manifold_edges == 0
    normals_outward = total_signed_vol >= 0.0
    max_dim = max(sx, sy, sz)
    min_dim = min(sx, sy, sz)
    unit_scale_ok = 2.0 <= max_dim <= 350.0
    aspect_ratio = sz / max(1.0, min(sx, sy))
    stability_ok = aspect_ratio <= 2.5 and (bottom_contact_mm2 >= 100.0 or sz <= 25.0)
    fits_standard_256 = sx <= 256.0 and sy <= 256.0 and sz <= 256.0

    # Calculate 0-100 Printability Score
    score = 100
    if topology_analyzed and not is_watertight:
        score -= 12
    if non_manifold_edges > 0:
        score -= 10
    if degenerate_triangles > 0:
        score -= 5
    if not normals_outward:
        score -= 15
    if floating_islands > 0:
        score -= 20
    if not stability_ok:
        score -= 12
    if severe_overhang_mm2 > 25.0:
        score -= 10
    if bridge_area_mm2 > 50.0:
        score -= 8
    if not unit_scale_ok:
        score -= 15
    score = max(0, min(100, score))

    return {
        "printability_score_100": score,
        "credits": "11-point audit inspired by heyixuan2/bambu-studio-ai & mikedh/trimesh",
        "checks": {
            "1_watertight_manifold": {
                "passed": is_watertight if topology_analyzed else None,
                "open_boundary_edges": boundary_edges if topology_analyzed else "skipped (>120k tris)",
            },
            "2_non_manifold_edges": {
                "passed": (non_manifold_edges == 0) if topology_analyzed else None,
                "non_manifold_edge_count": non_manifold_edges if topology_analyzed else "skipped (>120k tris)",
            },
            "3_degenerate_triangles": {
                "passed": degenerate_triangles == 0,
                "zero_area_triangle_count": degenerate_triangles,
            },
            "4_outward_face_normals": {
                "passed": normals_outward,
                "signed_volume_mm3": round(total_signed_vol, 2),
            },
            "5_disconnected_shells_and_floating_islands": {
                "passed": floating_islands == 0,
                "shell_count": shell_count if topology_analyzed else "skipped",
                "floating_midair_shells": floating_islands if topology_analyzed else "skipped",
            },
            "6_bed_adhesion_contact_area": {
                "passed": bottom_contact_mm2 >= 100.0 or sz <= 20.0,
                "bottom_contact_mm2": round(bottom_contact_mm2, 1),
            },
            "7_tipping_stability_aspect_ratio": {
                "passed": stability_ok,
                "height_to_base_ratio": round(aspect_ratio, 2),
            },
            "8_overhang_severity": {
                "passed": severe_overhang_mm2 <= 25.0,
                "overhang_over_35deg_mm2": round(overhang_area_mm2, 1),
                "severe_overhang_over_65deg_mm2": round(severe_overhang_mm2, 1),
            },
            "9_horizontal_bridge_risk": {
                "passed": bridge_area_mm2 <= 50.0,
                "elevated_flat_downward_area_mm2": round(bridge_area_mm2, 1),
            },
            "10_unit_and_scale_sanity": {
                "passed": unit_scale_ok,
                "max_dimension_mm": round(max_dim, 2),
                "min_dimension_mm": round(min_dim, 2),
                "warning": (
                    "Model looks tiny (<2mm) — check if exported in inches/meters!"
                    if max_dim < 2.0
                    else ("Model exceeds 350mm — may require splitting/cutting!" if max_dim > 350.0 else None)
                ),
            },
            "11_standard_build_volume_fit": {
                "passed": fits_standard_256,
                "fits_256x256x256_mm": fits_standard_256,
            },
        },
    }


def _triangle_metrics(
    v0: Vec3, v1: Vec3, v2: Vec3
) -> Tuple[float, float, float]:
    """Return (area_mm2, signed_volume_mm3, normal_z) for a single triangle."""
    ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]

    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx

    cross_norm = math.sqrt(cx * cx + cy * cy + cz * cz)
    area = 0.5 * cross_norm
    nz = (cz / cross_norm) if cross_norm > 1e-12 else 0.0

    # Signed volume of tetrahedron with origin
    signed_vol = (
        v0[0] * (v1[1] * v2[2] - v1[2] * v2[1])
        - v0[1] * (v1[0] * v2[2] - v1[2] * v2[0])
        + v0[2] * (v1[0] * v2[1] - v1[1] * v2[0])
    ) / 6.0

    return area, signed_vol, nz


def analyze_stl(file_path: Path) -> Dict[str, Any]:
    """Parse binary or ASCII STL and compute dimensions, volume, overhangs, and stability."""
    data = file_path.read_bytes()
    if len(data) < 84:
        return {"error": "File is too small to be a valid STL."}

    tri_count_bin = struct.unpack("<I", data[80:84])[0]
    expected_size = 84 + tri_count_bin * 50

    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    total_area = 0.0
    total_signed_vol = 0.0
    overhang_area = 0.0
    bottom_contact_area = 0.0
    tri_count = 0

    # Threshold angle: 30 deg from horizontal means normal Z < -cos(30 deg) = -0.866 -> wait:
    # A horizontal downward face has normal (0, 0, -1). A vertical wall has normal_z = 0.
    # An overhang at angle alpha from horizontal has normal_z = -cos(alpha).
    # For 35 deg from horizontal, normal_z < -cos(35 deg) = -0.819.
    overhang_nz_threshold = -math.cos(math.radians(35.0))

    if len(data) == expected_size:
        # Binary STL
        offset = 84
        first_pass_min_z = float("inf")
        triangles: List[Tuple[Vec3, Vec3, Vec3]] = []
        for _ in range(tri_count_bin):
            vals = struct.unpack_from("<12fH", data, offset)
            offset += 50
            v0 = (vals[3], vals[4], vals[5])
            v1 = (vals[6], vals[7], vals[8])
            v2 = (vals[9], vals[10], vals[11])
            triangles.append((v0, v1, v2))
            for vx, vy, vz in (v0, v1, v2):
                if vx < min_x:
                    min_x = vx
                if vx > max_x:
                    max_x = vx
                if vy < min_y:
                    min_y = vy
                if vy > max_y:
                    max_y = vy
                if vz < min_z:
                    min_z = vz
                if vz > max_z:
                    max_z = vz
            first_pass_min_z = min_z

        tri_count = len(triangles)
        for v0, v1, v2 in triangles:
            area, svol, nz = _triangle_metrics(v0, v1, v2)
            total_area += area
            total_signed_vol += svol
            avg_z = (v0[2] + v1[2] + v2[2]) / 3.0
            if avg_z <= first_pass_min_z + 0.25 and nz < -0.95:
                bottom_contact_area += area
            elif avg_z > first_pass_min_z + 0.6 and nz < overhang_nz_threshold:
                overhang_area += area
    else:
        # ASCII STL fallback
        text = data.decode("utf-8", errors="ignore")
        verts: List[Vec3] = []
        for line in text.splitlines():
            line_s = line.strip()
            if line_s.startswith("vertex"):
                parts = line_s.split()
                if len(parts) >= 4:
                    vx, vy, vz = float(parts[1]), float(parts[2]), float(parts[3])
                    verts.append((vx, vy, vz))
                    min_x, max_x = min(min_x, vx), max(max_x, vx)
                    min_y, max_y = min(min_y, vy), max(max_y, vy)
                    min_z, max_z = min(min_z, vz), max(max_z, vz)
        tri_count = len(verts) // 3
        triangles = []
        for i in range(0, tri_count * 3, 3):
            v0, v1, v2 = verts[i], verts[i + 1], verts[i + 2]
            triangles.append((v0, v1, v2))
            area, svol, nz = _triangle_metrics(v0, v1, v2)
            total_area += area
            total_signed_vol += svol
            avg_z = (v0[2] + v1[2] + v2[2]) / 3.0
            if avg_z <= min_z + 0.25 and nz < -0.95:
                bottom_contact_area += area
            elif avg_z > min_z + 0.6 and nz < overhang_nz_threshold:
                overhang_area += area

    size_x = max(0.0, max_x - min_x)
    size_y = max(0.0, max_y - min_y)
    size_z = max(0.0, max_z - min_z)
    vol_cm3 = abs(total_signed_vol) / 1000.0
    area_cm2 = total_area / 100.0
    printability = _compute_11_point_printability(
        triangles=triangles,
        size_xyz_mm=(size_x, size_y, size_z),
        min_z=0.0 if min_z == float("inf") else min_z,
        total_signed_vol=total_signed_vol,
        bottom_contact_mm2=bottom_contact_area,
        overhang_area_mm2=overhang_area,
    )

    return _build_geometry_summary(
        file_path=file_path,
        file_format="STL",
        triangle_count=tri_count,
        size_xyz_mm=(size_x, size_y, size_z),
        volume_cm3=vol_cm3,
        surface_area_cm2=area_cm2,
        bottom_contact_mm2=bottom_contact_area,
        overhang_area_mm2=overhang_area,
        printability_11_point=printability,
    )


def _build_geometry_summary(
    file_path: Path,
    file_format: str,
    triangle_count: int,
    size_xyz_mm: Tuple[float, float, float],
    volume_cm3: float,
    surface_area_cm2: float,
    bottom_contact_mm2: float,
    overhang_area_mm2: float,
    extra_metadata: Optional[Dict[str, Any]] = None,
    printability_11_point: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    sx, sy, sz = size_xyz_mm
    footprint_xy = max(1.0, sx * sy)
    aspect_ratio_height_to_base = sz / max(1.0, min(sx, sy))

    needs_supports = overhang_area_mm2 > 25.0
    needs_brim = (aspect_ratio_height_to_base > 2.5) or (bottom_contact_mm2 < 150.0 and sz > 25.0)

    # Rough PLA mass estimate (shell + 15% infill ~ 38% effective density * 1.24 g/cm3)
    approx_pla_grams = round(volume_cm3 * 1.24 * 0.38, 1)

    recommendations: List[str] = []
    if needs_supports:
        recommendations.append(
            f"Detected {round(overhang_area_mm2, 1)} mm² of steep overhang area (>35° from horizontal). Enable supports (e.g., 'tree(auto)' on build plate only)."
        )
    else:
        recommendations.append("Minimal steep overhangs detected — should print cleanly without supports.")

    if needs_brim:
        recommendations.append(
            f"High height-to-base ratio ({round(aspect_ratio_height_to_base, 1)}x) or small bed contact area ({round(bottom_contact_mm2, 1)} mm²). Enable a 5-8mm outer brim and use Gyroid infill so the print won't get knocked over."
        )

    if printability_11_point:
        checks = printability_11_point.get("checks", {})
        if checks.get("1_watertight_manifold", {}).get("passed") is False:
            recommendations.append(
                f"Mesh is non-watertight ({checks['1_watertight_manifold'].get('open_boundary_edges')} open boundary edges). Run 'repair_3d_mesh' or Bambu Studio's Fix Model tool."
            )
        if checks.get("4_outward_face_normals", {}).get("passed") is False:
            recommendations.append(
                "Mesh has inverted face normals (negative signed volume). Run 'repair_3d_mesh' to flip triangle winding."
            )
        if checks.get("5_disconnected_shells_and_floating_islands", {}).get("passed") is False:
            recommendations.append(
                f"Detected {checks['5_disconnected_shells_and_floating_islands'].get('floating_midair_shells')} floating mid-air mesh shell(s)! Use 'Split to Objects' or enable supports."
            )

    printer_compatibility = {
        "fits_A1_mini_180x180x180": sx <= 180 and sy <= 180 and sz <= 180,
        "fits_X1_P1_A1_256x256x256": sx <= 256 and sy <= 256 and sz <= 256,
        "fits_H2D_350x320x325": sx <= 350 and sy <= 320 and sz <= 325,
    }

    res = {
        "file_path": str(file_path),
        "format": file_format,
        "triangle_count": triangle_count,
        "dimensions_mm": {
            "x": round(sx, 2),
            "y": round(sy, 2),
            "z": round(sz, 2),
        },
        "volume_cm3": round(volume_cm3, 2),
        "surface_area_cm2": round(surface_area_cm2, 2),
        "bottom_contact_area_mm2": round(bottom_contact_mm2, 1),
        "steep_overhang_area_mm2": round(overhang_area_mm2, 1),
        "height_to_narrowest_base_ratio": round(aspect_ratio_height_to_base, 2),
        "estimated_pla_weight_g_at_15pct_infill": approx_pla_grams,
        "needs_supports_likely": needs_supports,
        "needs_brim_likely": needs_brim,
        "printer_build_volume_fit": printer_compatibility,
        "smart_geometry_recommendations": recommendations,
    }
    if printability_11_point:
        res["printability_11_point_audit"] = printability_11_point
    if extra_metadata:
        res["bambu_3mf_metadata"] = extra_metadata
    return res


def analyze_3mf(file_path: Path) -> Dict[str, Any]:
    """Inspect a .3mf file (both 3D mesh geometry and Bambu Studio project settings/slice info)."""
    if not zipfile.is_zipfile(file_path):
        return {"error": f"'{file_path}' is not a valid ZIP/3MF archive."}

    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    total_area = 0.0
    total_signed_vol = 0.0
    overhang_area = 0.0
    bottom_contact_area = 0.0
    total_tris = 0
    overhang_nz_threshold = -math.cos(math.radians(35.0))

    bambu_meta: Dict[str, Any] = {
        "archive_files": [],
        "project_settings_overrides": {},
        "objects": [],
        "slice_info": {},
    }

    with zipfile.ZipFile(file_path, "r") as zf:
        names = zf.namelist()
        bambu_meta["archive_files"] = names

        # 1. Parse all .model XML files for mesh geometry
        model_files = [n for n in names if n.endswith(".model")]
        all_triangles: List[Tuple[Vec3, Vec3, Vec3]] = []

        for mf in model_files:
            try:
                xml_bytes = zf.read(mf)
                root = ET.fromstring(xml_bytes)
            except Exception:
                continue

            for obj_elem in root.iter():
                if obj_elem.tag.endswith("object"):
                    obj_id = obj_elem.attrib.get("id")
                    obj_name = obj_elem.attrib.get("name", f"object_{obj_id}")
                    mesh_elem = next((c for c in obj_elem if c.tag.endswith("mesh")), None)
                    if mesh_elem is None:
                        continue

                    verts_elem = next((c for c in mesh_elem if c.tag.endswith("vertices")), None)
                    tris_elem = next((c for c in mesh_elem if c.tag.endswith("triangles")), None)
                    if verts_elem is None or tris_elem is None:
                        continue

                    verts: List[Vec3] = []
                    for v in verts_elem:
                        if v.tag.endswith("vertex"):
                            vx = float(v.attrib.get("x", 0.0))
                            vy = float(v.attrib.get("y", 0.0))
                            vz = float(v.attrib.get("z", 0.0))
                            verts.append((vx, vy, vz))
                            min_x, max_x = min(min_x, vx), max(max_x, vx)
                            min_y, max_y = min(min_y, vy), max(max_y, vy)
                            min_z, max_z = min(min_z, vz), max(max_z, vz)

                    obj_tri_count = 0
                    for t in tris_elem:
                        if t.tag.endswith("triangle"):
                            i1 = int(t.attrib["v1"])
                            i2 = int(t.attrib["v2"])
                            i3 = int(t.attrib["v3"])
                            if i1 < len(verts) and i2 < len(verts) and i3 < len(verts):
                                all_triangles.append((verts[i1], verts[i2], verts[i3]))
                                obj_tri_count += 1

                    bambu_meta["objects"].append({
                        "id": obj_id,
                        "name": obj_name,
                        "source_model": mf,
                        "vertex_count": len(verts),
                        "triangle_count": obj_tri_count,
                    })

        total_tris = len(all_triangles)
        for v0, v1, v2 in all_triangles:
            area, svol, nz = _triangle_metrics(v0, v1, v2)
            total_area += area
            total_signed_vol += svol
            avg_z = (v0[2] + v1[2] + v2[2]) / 3.0
            if avg_z <= min_z + 0.25 and nz < -0.95:
                bottom_contact_area += area
            elif avg_z > min_z + 0.6 and nz < overhang_nz_threshold:
                overhang_area += area

        # 2. Parse Metadata/project_settings.config if present
        if "Metadata/project_settings.config" in names:
            try:
                proj_cfg = json.loads(
                    zf.read("Metadata/project_settings.config").decode("utf-8", errors="replace")
                )
                key_highlights = [
                    "printer_model", "nozzle_diameter", "curr_bed_type",
                    "layer_height", "initial_layer_print_height", "wall_loops",
                    "top_shell_layers", "bottom_shell_layers",
                    "sparse_infill_density", "sparse_infill_pattern",
                    "enable_support", "support_type", "support_on_build_plate_only",
                    "support_top_z_distance", "brim_type", "brim_width",
                    "filament_type", "filament_colour", "outer_wall_speed",
                    "seam_position", "wall_generator", "flush_into_infill",
                ]
                bambu_meta["project_settings_summary"] = {
                    k: proj_cfg.get(k) for k in key_highlights if k in proj_cfg
                }
                bambu_meta["project_settings_overrides"] = proj_cfg.get("different_settings_to_system", [])
            except Exception as exc:
                bambu_meta["project_settings_error"] = str(exc)

        # 3. Parse Metadata/slice_info.config if already sliced
        if "Metadata/slice_info.config" in names:
            try:
                slice_xml = ET.fromstring(zf.read("Metadata/slice_info.config"))
                plates_info = []
                for plate in slice_xml.iter("plate"):
                    p_dict: Dict[str, Any] = {"metadata": {}, "filaments": []}
                    for meta in plate.findall("metadata"):
                        k = meta.attrib.get("key")
                        v = meta.attrib.get("value")
                        if k:
                            p_dict["metadata"][k] = v
                    for fil in plate.findall("filament"):
                        p_dict["filaments"].append(dict(fil.attrib))
                    plates_info.append(p_dict)
                bambu_meta["slice_info"] = {"plates": plates_info}
            except Exception as exc:
                bambu_meta["slice_info_error"] = str(exc)

    sx = 0.0 if min_x == float("inf") else (max_x - min_x)
    sy = 0.0 if min_y == float("inf") else (max_y - min_y)
    sz = 0.0 if min_z == float("inf") else (max_z - min_z)
    printability = _compute_11_point_printability(
        triangles=all_triangles,
        size_xyz_mm=(sx, sy, sz),
        min_z=0.0 if min_z == float("inf") else min_z,
        total_signed_vol=total_signed_vol,
        bottom_contact_mm2=bottom_contact_area,
        overhang_area_mm2=overhang_area,
    )

    return _build_geometry_summary(
        file_path=file_path,
        file_format="3MF",
        triangle_count=total_tris,
        size_xyz_mm=(sx, sy, sz),
        volume_cm3=abs(total_signed_vol) / 1000.0,
        surface_area_cm2=total_area / 100.0,
        bottom_contact_mm2=bottom_contact_area,
        overhang_area_mm2=overhang_area,
        extra_metadata=bambu_meta,
        printability_11_point=printability,
    )


def inspect_3d_model(file_path: str) -> Dict[str, Any]:
    """Inspect a .stl or .3mf file and return geometry, overhang analysis, and Bambu metadata."""
    p = Path(file_path)
    if not p.exists():
        return {"error": f"File not found: '{file_path}'"}
    ext = p.suffix.lower()
    if ext == ".stl":
        return analyze_stl(p)
    if ext == ".3mf":
        return analyze_3mf(p)
    return {"error": f"Unsupported file extension '{ext}'. Please provide a .stl or .3mf file."}


def modify_3mf_settings(
    input_3mf_path: str,
    settings_overrides: Dict[str, Any],
    output_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Modify slicer settings inside a Bambu Studio .3mf project file without opening the GUI."""
    src = Path(input_3mf_path)
    if not src.exists():
        return {"error": f"Input .3mf not found: '{input_3mf_path}'"}
    if not zipfile.is_zipfile(src):
        return {"error": f"'{input_3mf_path}' is not a valid .3mf archive."}

    dest = Path(output_3mf_path) if output_3mf_path else src.with_name(f"{src.stem}_optimized.3mf")
    dest.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = dest.with_suffix(".3mf.tmp")
    updated_keys: Dict[str, Any] = {}

    with zipfile.ZipFile(src, "r") as zin:
        names = zin.namelist()
        proj_cfg: Dict[str, Any] = {}
        if "Metadata/project_settings.config" in names:
            try:
                proj_cfg = json.loads(
                    zin.read("Metadata/project_settings.config").decode("utf-8", errors="replace")
                )
            except Exception:
                proj_cfg = {}

        for k, v in settings_overrides.items():
            if k in proj_cfg and isinstance(proj_cfg[k], list) and not isinstance(v, list):
                proj_cfg[k] = [str(v)]
            else:
                proj_cfg[k] = str(v) if not isinstance(v, (list, dict)) else v
            updated_keys[k] = proj_cfg[k]

        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "Metadata/project_settings.config":
                    continue
                zout.writestr(item, zin.read(item.filename))
            zout.writestr(
                "Metadata/project_settings.config",
                json.dumps(proj_cfg, indent=4).encode("utf-8"),
            )

    shutil.move(str(tmp_path), str(dest))
    return {
        "success": True,
        "input_3mf": str(src),
        "output_3mf": str(dest),
        "applied_settings": updated_keys,
    }


def add_empty_plate_to_3mf(
    input_3mf_path: str,
    plate_name: str = "",
    output_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a new empty build plate to a Bambu Studio .3mf project file (Metadata/model_settings.config)."""
    src = Path(input_3mf_path)
    if not src.exists():
        return {"error": f"Input .3mf not found: '{input_3mf_path}'"}
    if not zipfile.is_zipfile(src):
        return {"error": f"'{input_3mf_path}' is not a valid .3mf archive."}

    dest = Path(output_3mf_path) if output_3mf_path else src
    tmp_path = dest.with_suffix(".3mf.tmp")

    with zipfile.ZipFile(src, "r") as zin:
        names = zin.namelist()
        if "Metadata/model_settings.config" in names:
            xml_bytes = zin.read("Metadata/model_settings.config")
            root = ET.fromstring(xml_bytes)
        else:
            root = ET.Element("config")

        existing_plates = root.findall("plate")
        max_id = 0
        for p in existing_plates:
            for m in p.findall("metadata"):
                if m.attrib.get("key") == "plater_id":
                    try:
                        max_id = max(max_id, int(m.attrib.get("value", "0")))
                    except ValueError:
                        pass

        new_plate_id = max(max_id + 1, len(existing_plates) + 1)
        plate_elem = ET.SubElement(root, "plate")
        ET.SubElement(plate_elem, "metadata", {"key": "plater_id", "value": str(new_plate_id)})
        ET.SubElement(plate_elem, "metadata", {"key": "plater_name", "value": plate_name})
        ET.SubElement(plate_elem, "metadata", {"key": "locked", "value": "false"})

        new_xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")

        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "Metadata/model_settings.config":
                    continue
                zout.writestr(item, zin.read(item.filename))
            zout.writestr("Metadata/model_settings.config", new_xml_bytes)

    shutil.move(str(tmp_path), str(dest))
    return {
        "success": True,
        "input_3mf": str(src),
        "output_3mf": str(dest),
        "new_plate_id": new_plate_id,
        "plate_name": plate_name,
        "total_plates": len(existing_plates) + 1,
    }


def list_plates_in_3mf(input_3mf_path: str) -> Dict[str, Any]:
    """Inspect Metadata/model_settings.config inside a .3mf archive and return all <plate> entries."""
    src = Path(input_3mf_path)
    if not src.exists():
        return {"error": f"Input .3mf not found: '{input_3mf_path}'"}
    if not zipfile.is_zipfile(src):
        return {"error": f"'{input_3mf_path}' is not a valid .3mf archive."}

    with zipfile.ZipFile(src, "r") as zin:
        names = zin.namelist()
        if "Metadata/model_settings.config" not in names:
            return {
                "success": True,
                "input_3mf": str(src),
                "total_plates": 0,
                "plates": [],
            }

        try:
            root = ET.fromstring(zin.read("Metadata/model_settings.config"))
        except Exception as exc:
            return {"error": f"Failed to parse Metadata/model_settings.config: {exc}"}

        object_names: Dict[str, str] = {}
        for obj in root.findall("object"):
            obj_id = obj.attrib.get("id")
            if not obj_id:
                continue
            for m in obj.findall("metadata"):
                if m.attrib.get("key") == "name" and m.attrib.get("value"):
                    object_names[obj_id] = m.attrib["value"]
                    break

        plates: List[Dict[str, Any]] = []
        for idx, plate_elem in enumerate(root.findall("plate"), start=1):
            meta_map: Dict[str, str] = {}
            for m in plate_elem.findall("metadata"):
                k = m.attrib.get("key")
                v = m.attrib.get("value", "")
                if k:
                    meta_map[k] = v

            raw_id = meta_map.get("plater_id", str(idx))
            try:
                plater_id: Any = int(raw_id)
            except ValueError:
                plater_id = raw_id

            plater_name = meta_map.get("plater_name", "")
            locked_str = meta_map.get("locked", "false").lower()
            locked = locked_str in ("true", "1", "yes")

            instances: List[Dict[str, Any]] = []
            for inst_elem in plate_elem.findall("model_instance"):
                inst_data: Dict[str, Any] = dict(inst_elem.attrib)
                for im in inst_elem.findall("metadata"):
                    ik = im.attrib.get("key")
                    iv = im.attrib.get("value", "")
                    if ik:
                        inst_data[ik] = iv
                obj_id = inst_data.get("object_id")
                if obj_id and obj_id in object_names and "object_name" not in inst_data:
                    inst_data["object_name"] = object_names[obj_id]
                instances.append(inst_data)

            plates.append({
                "plater_id": plater_id,
                "plater_name": plater_name,
                "locked": locked,
                "model_instances": instances,
                "instance_count": len(instances),
            })

    return {
        "success": True,
        "input_3mf": str(src),
        "total_plates": len(plates),
        "plates": plates,
    }


def remove_plate_from_3mf(
    input_3mf_path: str,
    plate_id: int,
    output_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Remove a <plate> by plater_id from Metadata/model_settings.config and re-number remaining plates 1..N."""
    src = Path(input_3mf_path)
    if not src.exists():
        return {"error": f"Input .3mf not found: '{input_3mf_path}'"}
    if not zipfile.is_zipfile(src):
        return {"error": f"'{input_3mf_path}' is not a valid .3mf archive."}

    dest = Path(output_3mf_path) if output_3mf_path else src
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest.with_suffix(".3mf.tmp")
    target_id_str = str(plate_id)

    with zipfile.ZipFile(src, "r") as zin:
        names = zin.namelist()
        if "Metadata/model_settings.config" not in names:
            return {"error": f"Metadata/model_settings.config not found in '{input_3mf_path}'."}

        try:
            root = ET.fromstring(zin.read("Metadata/model_settings.config"))
        except Exception as exc:
            return {"error": f"Failed to parse Metadata/model_settings.config: {exc}"}

        existing_plates = root.findall("plate")
        target_plate: Optional[ET.Element] = None
        available_ids: List[str] = []
        removed_plate_name = ""
        removed_instances_count = 0

        for p in existing_plates:
            pid_val = ""
            pname_val = ""
            for m in p.findall("metadata"):
                if m.attrib.get("key") == "plater_id":
                    pid_val = m.attrib.get("value", "")
                elif m.attrib.get("key") == "plater_name":
                    pname_val = m.attrib.get("value", "")
            if pid_val:
                available_ids.append(pid_val)
            if pid_val == target_id_str and target_plate is None:
                target_plate = p
                removed_plate_name = pname_val
                removed_instances_count = len(p.findall("model_instance"))

        if target_plate is None:
            return {
                "error": f"Plate with plater_id={plate_id} not found in '{input_3mf_path}'.",
                "available_plate_ids": available_ids,
            }

        root.remove(target_plate)

        remaining_plates = root.findall("plate")
        renumbered_ids: List[int] = []
        for new_idx, p in enumerate(remaining_plates, start=1):
            id_meta: Optional[ET.Element] = None
            for m in p.findall("metadata"):
                if m.attrib.get("key") == "plater_id":
                    id_meta = m
                    break
            if id_meta is not None:
                id_meta.set("value", str(new_idx))
            else:
                ET.SubElement(p, "metadata", {"key": "plater_id", "value": str(new_idx)})
            renumbered_ids.append(new_idx)

        new_xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")

        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "Metadata/model_settings.config":
                    continue
                zout.writestr(item, zin.read(item.filename))
            zout.writestr("Metadata/model_settings.config", new_xml_bytes)

    shutil.move(str(tmp_path), str(dest))
    return {
        "success": True,
        "input_3mf": str(src),
        "output_3mf": str(dest),
        "removed_plate_id": plate_id,
        "removed_plate_name": removed_plate_name,
        "removed_model_instances": removed_instances_count,
        "total_plates": len(remaining_plates),
        "remaining_plate_ids": renumbered_ids,
    }


def move_object_to_plate_in_3mf(
    input_3mf_path: str,
    object_identifier: str,
    target_plate_id: int,
    output_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Move every <model_instance> matching an object_id or object name to another <plate>.

    Edits Metadata/model_settings.config only, creating the target plate if it does not exist.
    Build-item transforms in 3D/3dmodel.model are left unchanged.
    """
    src = Path(input_3mf_path)
    if not src.exists():
        return {"error": f"Input .3mf not found: '{input_3mf_path}'"}
    if not zipfile.is_zipfile(src):
        return {"error": f"'{input_3mf_path}' is not a valid .3mf archive."}
    if not object_identifier:
        return {"error": "object_identifier must not be empty."}
    if target_plate_id < 1:
        return {"error": f"target_plate_id must be >= 1, got {target_plate_id}."}

    dest = Path(output_3mf_path) if output_3mf_path else src
    tmp_path = dest.with_suffix(".3mf.tmp")
    target_id_str = str(target_plate_id)

    def metadata_map(elem: ET.Element) -> Dict[str, str]:
        return {
            m.attrib["key"]: m.attrib.get("value", "")
            for m in elem.findall("metadata")
            if m.attrib.get("key")
        }

    with zipfile.ZipFile(src, "r") as zin:
        if "Metadata/model_settings.config" not in zin.namelist():
            return {"error": f"Metadata/model_settings.config not found in '{input_3mf_path}'."}

        try:
            root = ET.fromstring(zin.read("Metadata/model_settings.config"))
        except Exception as exc:
            return {"error": f"Failed to parse Metadata/model_settings.config: {exc}"}

        object_names: Dict[str, str] = {}
        for obj in root.findall("object"):
            obj_id = obj.attrib.get("id")
            obj_name = metadata_map(obj).get("name")
            if obj_id and obj_name:
                object_names[obj_id] = obj_name

        plates = [(p, metadata_map(p).get("plater_id", "")) for p in root.findall("plate")]

        matches: List[Tuple[ET.Element, ET.Element, str, Dict[str, str]]] = []
        for plate_elem, plate_id_str in plates:
            for inst_elem in plate_elem.findall("model_instance"):
                inst_data = {**inst_elem.attrib, **metadata_map(inst_elem)}
                obj_id = inst_data.get("object_id", "")
                obj_name = inst_data.get("object_name") or object_names.get(obj_id, "")
                if object_identifier in (obj_id, obj_name):
                    inst_data["object_name"] = obj_name
                    matches.append((plate_elem, inst_elem, plate_id_str, inst_data))

        if not matches:
            return {
                "error": f"No model instance matches object id or name '{object_identifier}' in '{input_3mf_path}'.",
                "available_objects": object_names,
            }

        target_plate = next((p for p, pid in plates if pid == target_id_str), None)
        plate_created = target_plate is None
        if target_plate is None:
            target_plate = ET.Element("plate")
            ET.SubElement(target_plate, "metadata", {"key": "plater_id", "value": target_id_str})
            ET.SubElement(target_plate, "metadata", {"key": "plater_name", "value": ""})
            ET.SubElement(target_plate, "metadata", {"key": "locked", "value": "false"})
            # Keep <plate> elements contiguous so a trailing <assemble> section stays last.
            insert_at = list(root).index(plates[-1][0]) + 1 if plates else len(root)
            root.insert(insert_at, target_plate)

        moved_instances: List[Dict[str, str]] = []
        for source_plate, inst_elem, source_id_str, inst_data in matches:
            if source_plate is target_plate:
                continue
            source_plate.remove(inst_elem)
            target_plate.append(inst_elem)
            moved_instances.append({
                "object_id": inst_data.get("object_id", ""),
                "instance_id": inst_data.get("instance_id", ""),
                "object_name": inst_data["object_name"],
                "from_plate_id": source_id_str,
            })

        new_xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")

        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "Metadata/model_settings.config":
                    continue
                zout.writestr(item, zin.read(item.filename))
            zout.writestr("Metadata/model_settings.config", new_xml_bytes)

    shutil.move(str(tmp_path), str(dest))
    return {
        "success": True,
        "input_3mf": str(src),
        "output_3mf": str(dest),
        "object_identifier": object_identifier,
        "target_plate_id": target_plate_id,
        "target_plate_created": plate_created,
        "moved_count": len(moved_instances),
        "already_on_target_count": len(matches) - len(moved_instances),
        "moved_instances": moved_instances,
        "total_plates": len(plates) + (1 if plate_created else 0),
    }


def _serialize_object_setting(value: Any) -> str:
    """Convert a Python value to the string form used by model_settings.config metadata."""
    if isinstance(value, bool):
        # Bambu config booleans are "1"/"0"; str(True) would not parse as true.
        return "1" if value else "0"
    if isinstance(value, (list, tuple)):
        return ",".join(_serialize_object_setting(v) for v in value)
    if value is None or isinstance(value, dict):
        raise ValueError(f"unsupported value {value!r}")
    return str(value)


def set_object_settings_in_3mf(
    input_3mf_path: str,
    object_identifier: str,
    settings_overrides: Dict[str, Any],
    output_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update per-object <metadata> settings in Metadata/model_settings.config.

    object_identifier is resolved against the most specific match available: <object id>, then
    the object's "name" metadata (every object sharing the name is updated), then a
    <model_instance> "object_name" or "identify_id". instance_id is not matched because it is
    only unique within an object. Writes in place unless output_3mf_path is given.
    """
    src = Path(input_3mf_path)
    if not src.exists():
        return {"error": f"Input .3mf not found: '{input_3mf_path}'"}
    if not zipfile.is_zipfile(src):
        return {"error": f"'{input_3mf_path}' is not a valid .3mf archive."}
    if not object_identifier:
        return {"error": "object_identifier must not be empty."}
    if not settings_overrides:
        return {"error": "settings_overrides must not be empty."}

    serialized: Dict[str, str] = {}
    for key, value in settings_overrides.items():
        if not key:
            return {"error": "settings_overrides keys must not be empty."}
        try:
            serialized[key] = _serialize_object_setting(value)
        except ValueError as exc:
            return {"error": f"Invalid value for setting '{key}': {exc}"}

    dest = Path(output_3mf_path) if output_3mf_path else src
    tmp_path = dest.with_suffix(".3mf.tmp")

    def metadata_map(elem: ET.Element) -> Dict[str, str]:
        return {
            m.attrib["key"]: m.attrib.get("value", "")
            for m in elem.findall("metadata")
            if m.attrib.get("key")
        }

    with zipfile.ZipFile(src, "r") as zin:
        if "Metadata/model_settings.config" not in zin.namelist():
            return {"error": f"Metadata/model_settings.config not found in '{input_3mf_path}'."}

        try:
            root = ET.fromstring(zin.read("Metadata/model_settings.config"))
        except Exception as exc:
            return {"error": f"Failed to parse Metadata/model_settings.config: {exc}"}

        objects = root.findall("object")
        matches = [o for o in objects if o.attrib.get("id") == object_identifier]
        matched_by = "id"
        if not matches:
            matches = [o for o in objects if metadata_map(o).get("name") == object_identifier]
            matched_by = "name"
        if not matches:
            instance_object_ids = set()
            for inst_elem in root.iter("model_instance"):
                inst_data = {**inst_elem.attrib, **metadata_map(inst_elem)}
                if object_identifier in (inst_data.get("object_name"), inst_data.get("identify_id")):
                    instance_object_ids.add(inst_data.get("object_id"))
            matches = [o for o in objects if o.attrib.get("id") in instance_object_ids]
            matched_by = "model_instance"

        if not matches:
            return {
                "error": f"No object matches id, name, or model instance '{object_identifier}' in '{input_3mf_path}'.",
                "available_objects": {
                    o.attrib.get("id", ""): metadata_map(o).get("name", "") for o in objects
                },
            }

        updated_objects: List[Dict[str, Any]] = []
        for obj in matches:
            created_keys: List[str] = []
            updated_keys: List[str] = []
            for key, value in serialized.items():
                existing = [m for m in obj.findall("metadata") if m.attrib.get("key") == key]
                if existing:
                    for m in existing:
                        m.set("value", value)
                    updated_keys.append(key)
                else:
                    # Metadata stays ahead of <part> children, matching Bambu Studio's layout.
                    children = list(obj)
                    insert_at = max(
                        (i + 1 for i, c in enumerate(children) if c.tag == "metadata"),
                        default=0,
                    )
                    new_meta = ET.Element("metadata", {"key": key, "value": value})
                    obj.insert(insert_at, new_meta)
                    created_keys.append(key)
            updated_objects.append({
                "object_id": obj.attrib.get("id", ""),
                "object_name": metadata_map(obj).get("name", ""),
                "created_keys": created_keys,
                "updated_keys": updated_keys,
            })

        new_xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")

        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "Metadata/model_settings.config":
                    continue
                zout.writestr(item, zin.read(item.filename))
            zout.writestr("Metadata/model_settings.config", new_xml_bytes)

    shutil.move(str(tmp_path), str(dest))
    return {
        "success": True,
        "input_3mf": str(src),
        "output_3mf": str(dest),
        "object_identifier": object_identifier,
        "matched_by": matched_by,
        "applied_settings": serialized,
        "updated_objects": updated_objects,
    }


