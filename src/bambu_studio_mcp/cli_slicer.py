"""Headless Bambu Studio CLI Slicing, G-Code / 3MF Metadata Parser, and GUI Launcher."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import discover_environment
from .profiles import catalog


def _format_duration(seconds: float) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def parse_sliced_metadata(
    file_path: str,
    spool_cost_per_kg: float = 20.0,
) -> Dict[str, Any]:
    """Extract print time, filament usage (g / m), cost, and layer count from a .gcode.3mf or .gcode file."""
    p = Path(file_path)
    if not p.exists():
        return {"error": f"File not found: '{file_path}'"}

    if p.suffix.lower() == ".3mf" and zipfile.is_zipfile(p):
        return _parse_3mf_slice_results(p, spool_cost_per_kg)
    return _parse_raw_gcode_text(p.read_text(encoding="utf-8", errors="ignore"), str(p), spool_cost_per_kg)


def _parse_3mf_slice_results(path: Path, spool_cost_per_kg: float) -> Dict[str, Any]:
    plates_out: List[Dict[str, Any]] = []
    total_time_s = 0.0
    total_weight_g = 0.0
    total_length_m = 0.0
    gcode_header_metrics: Dict[str, Any] = {}

    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        if "Metadata/slice_info.config" in names:
            try:
                root = ET.fromstring(zf.read("Metadata/slice_info.config"))
                for plate in root.iter("plate"):
                    meta_map: Dict[str, str] = {}
                    for m in plate.findall("metadata"):
                        k = m.attrib.get("key")
                        v = m.attrib.get("value")
                        if k and v is not None:
                            meta_map[k] = v

                    pred_s = float(meta_map.get("prediction", "0") or 0)
                    weight_g = float(meta_map.get("weight", "0") or 0)

                    fils: List[Dict[str, Any]] = []
                    plate_len_m = 0.0
                    for f in plate.findall("filament"):
                        f_attr = dict(f.attrib)
                        used_m = float(f_attr.get("used_m", "0") or 0)
                        used_g = float(f_attr.get("used_g", "0") or 0)
                        plate_len_m += used_m
                        fils.append({
                            "id": f_attr.get("id"),
                            "type": f_attr.get("type"),
                            "color": f_attr.get("color"),
                            "used_m": round(used_m, 2),
                            "used_g": round(used_g, 2),
                        })

                    total_time_s += pred_s
                    total_weight_g += weight_g
                    total_length_m += plate_len_m

                    plates_out.append({
                        "index": meta_map.get("index", "1"),
                        "print_time_seconds": round(pred_s, 1),
                        "print_time_human": _format_duration(pred_s),
                        "filament_weight_g": round(weight_g, 2),
                        "filament_length_m": round(plate_len_m, 2),
                        "estimated_cost_usd": round((weight_g / 1000.0) * spool_cost_per_kg, 2),
                        "filaments": fils,
                    })
            except Exception as exc:
                gcode_header_metrics["slice_info_parse_error"] = str(exc)

        # Also inspect any Metadata/plate_*.gcode header/footer comments if present
        gcode_files = [n for n in names if n.endswith(".gcode")]
        if gcode_files:
            try:
                raw_bytes = zf.read(gcode_files[0])
                # Read first 32KB and last 32KB where Bambu Studio writes summary comments
                head_tail = (
                    raw_bytes[:32768].decode("utf-8", errors="ignore")
                    + "\n"
                    + raw_bytes[-32768:].decode("utf-8", errors="ignore")
                )
                gcode_header_metrics = _parse_raw_gcode_text(head_tail, gcode_files[0], spool_cost_per_kg)
            except Exception:
                pass

    if total_time_s == 0.0 and gcode_header_metrics.get("print_time_seconds"):
        total_time_s = float(gcode_header_metrics["print_time_seconds"])
    if total_weight_g == 0.0 and gcode_header_metrics.get("filament_weight_g"):
        total_weight_g = float(gcode_header_metrics["filament_weight_g"])

    return {
        "file_path": str(path),
        "is_sliced": bool(plates_out or gcode_header_metrics.get("layer_count")),
        "total_print_time_seconds": round(total_time_s, 1),
        "total_print_time_human": _format_duration(total_time_s),
        "total_filament_weight_g": round(total_weight_g, 2),
        "total_filament_length_m": round(total_length_m, 2),
        "estimated_cost_usd": round((total_weight_g / 1000.0) * spool_cost_per_kg, 2),
        "spool_cost_per_kg_assumed": spool_cost_per_kg,
        "plates": plates_out,
        "gcode_details": gcode_header_metrics,
    }


def _parse_raw_gcode_text(text: str, source_name: str, spool_cost_per_kg: float) -> Dict[str, Any]:
    layer_count = None
    max_z = None
    weight_g = None
    length_m = None
    time_str = None

    for line in text.splitlines():
        s = line.strip()
        if not s.startswith(";"):
            continue
        if "total layer number" in s.lower():
            m = re.search(r"(\d+)", s)
            if m:
                layer_count = int(m.group(1))
        elif "max_z_height" in s.lower():
            m = re.search(r"([\d.]+)", s)
            if m:
                max_z = float(m.group(1))
        elif "total filament weight [g]" in s.lower() or "filament used [g]" in s.lower():
            nums = [float(x) for x in re.findall(r"[\d.]+", s.split(":")[-1])]
            if nums:
                weight_g = round(sum(nums), 2)
        elif "total filament length [mm]" in s.lower() or "filament used [mm]" in s.lower():
            nums = [float(x) for x in re.findall(r"[\d.]+", s.split(":")[-1])]
            if nums:
                length_m = round(sum(nums) / 1000.0, 2)
        elif "estimated printing time" in s.lower() or "model printing time" in s.lower():
            time_str = s.split(":", 1)[-1].strip()

    return {
        "source": source_name,
        "layer_count": layer_count,
        "max_z_height_mm": max_z,
        "filament_weight_g": weight_g,
        "filament_length_m": length_m,
        "estimated_time_comment": time_str,
        "estimated_cost_usd": round((weight_g / 1000.0) * spool_cost_per_kg, 2) if weight_g else None,
    }


def slice_model_cli(
    input_file: str,
    printer_profile: Optional[str] = None,
    process_profile: Optional[str] = None,
    filament_profile: Optional[str] = None,
    settings_overrides: Optional[Dict[str, Any]] = None,
    auto_orient: bool = False,
    auto_arrange: bool = True,
    output_3mf_path: Optional[str] = None,
    spool_cost_per_kg: float = 20.0,
    timeout_seconds: int = 180,
) -> Dict[str, Any]:
    """Run headless Bambu Studio CLI to slice a .stl or .3mf file and parse the results."""
    env = discover_environment()
    if not env.executable_path or not env.executable_path.exists():
        return {
            "success": False,
            "error": "Bambu Studio executable not found. Set BAMBU_STUDIO_EXE or install Bambu Studio.",
        }

    src = Path(input_file)
    if not src.exists():
        return {"success": False, "error": f"Input file not found: '{input_file}'"}

    out_path = (
        Path(output_3mf_path)
        if output_3mf_path
        else src.with_name(f"{src.stem}_sliced.gcode.3mf")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="bambu_mcp_slice_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        cmd: List[str] = [str(env.executable_path)]

        if auto_orient:
            cmd.extend(["--orient", "1"])
        if auto_arrange:
            cmd.extend(["--arrange", "1"])

        # Prepare resolved machine + process settings if requested
        settings_files: List[str] = []
        if printer_profile:
            m_data, _ = catalog.resolve_profile("machine", printer_profile)
            if m_data:
                m_path = tmp_dir / "machine.json"
                m_path.write_text(json.dumps(m_data, indent=2), encoding="utf-8")
                settings_files.append(str(m_path))

        if process_profile or settings_overrides:
            base_proc = process_profile or "0.20mm Standard @BBL X1C"
            p_data, _ = catalog.resolve_profile("process", base_proc)
            if not p_data:
                # Fallback to first available process profile
                procs = catalog.list_profiles("process", limit=1).get("profiles", [])
                if procs:
                    p_data, _ = catalog.resolve_profile("process", procs[0]["name"])
            if p_data:
                if settings_overrides:
                    for k, v in settings_overrides.items():
                        if k in p_data and isinstance(p_data[k], list) and not isinstance(v, list):
                            p_data[k] = [str(v)]
                        else:
                            p_data[k] = str(v) if not isinstance(v, (list, dict)) else v
                p_path = tmp_dir / "process.json"
                p_path.write_text(json.dumps(p_data, indent=2), encoding="utf-8")
                settings_files.append(str(p_path))

        if settings_files:
            cmd.extend(["--load-settings", ";".join(settings_files)])

        if filament_profile:
            f_data, _ = catalog.resolve_profile("filament", filament_profile)
            if f_data:
                f_path = tmp_dir / "filament.json"
                f_path.write_text(json.dumps(f_data, indent=2), encoding="utf-8")
                cmd.extend(["--load-filaments", str(f_path)])

        cmd.extend([
            "--slice", "0",
            "--outputdir", str(out_path.parent),
            "--export-3mf", out_path.name,
            str(src),
        ])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Bambu Studio CLI slicing timed out after {timeout_seconds}s.",
                "command": cmd,
            }
        except Exception as exc:
            return {
                "success": False,
                "error": f"Failed to execute Bambu Studio CLI: {exc}",
                "command": cmd,
            }

        if not out_path.exists():
            return {
                "success": False,
                "return_code": proc.returncode,
                "error": "Bambu Studio CLI finished but output .gcode.3mf was not created. Note: slicing raw .stl via CLI requires specifying valid printer_profile, process_profile, and filament_profile names (or slicing an existing .3mf project).",
                "stdout": proc.stdout[-2000:] if proc.stdout else "",
                "stderr": proc.stderr[-2000:] if proc.stderr else "",
                "command": cmd,
            }

        metrics = parse_sliced_metadata(str(out_path), spool_cost_per_kg=spool_cost_per_kg)
        return {
            "success": True,
            "return_code": proc.returncode,
            "input_file": str(src),
            "output_sliced_3mf": str(out_path),
            "applied_overrides": settings_overrides or {},
            "slice_metrics": metrics,
        }


def open_in_bambu_studio_gui(file_path: Optional[str] = None) -> Dict[str, Any]:
    """Launch Bambu Studio GUI optionally opening a .3mf or .stl file."""
    env = discover_environment()
    if not env.executable_path or not env.executable_path.exists():
        return {"success": False, "error": "Bambu Studio executable not found."}

    cmd = [str(env.executable_path)]
    if file_path:
        p = Path(file_path)
        if not p.exists():
            return {"success": False, "error": f"File not found: '{file_path}'"}
        cmd.append(str(p))

    try:
        subprocess.Popen(cmd, close_fds=True)
        return {
            "success": True,
            "executable": str(env.executable_path),
            "opened_file": str(Path(file_path).resolve()) if file_path else None,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to launch Bambu Studio: {exc}"}
