"""Bambu Studio MCP Server entry point.

Supports both the official `mcp` SDK (FastMCP) and a built-in zero-dependency
JSON-RPC 2.0 stdio MCP server fallback so it runs out-of-the-box on any Python 3.10+ setup.
"""

from __future__ import annotations

import inspect
import json
import sys
from typing import Any, Callable, Dict, List, Optional

from .ai_features import (
    match_ams_colors_cielab,
    repair_and_ground_stl,
    search_3d_models as _search_3d_models,
)
from .cli_slicer import (
    open_in_bambu_studio_gui,
    parse_sliced_metadata,
    slice_model_cli,
)
from .config import discover_environment, read_bambu_studio_conf
from .gui_control import control_bambu_gui
from .knowledge import (
    diagnose_print_issue,
    explain_setting,
    get_calibration_guide as _get_calibration_guide,
    recommend_print_settings,
)
from .model_3mf import (
    add_empty_plate_to_3mf,
    inspect_3d_model as _inspect_3d_model,
    list_plates_in_3mf as _list_plates_in_3mf,
    modify_3mf_settings,
    move_object_to_plate_in_3mf as _move_object_to_plate_in_3mf,
    remove_plate_from_3mf as _remove_plate_from_3mf,
    set_object_settings_in_3mf as _set_object_settings_in_3mf,
)
from .printer_live import query_printer_status, send_printer_command
from .profiles import catalog


# ---------------------------------------------------------------------------
# TOOL IMPLEMENTATIONS
# ---------------------------------------------------------------------------

def bambu_environment_info() -> Dict[str, Any]:
    """Detect Bambu Studio installation path, profile directories, and active presets from BambuStudio.conf."""
    env = discover_environment()
    conf = read_bambu_studio_conf(redact_secrets=True)
    return {
        "environment": env.to_dict(),
        "bambu_studio_conf": conf,
    }


def explain_bambu_setting(query: str) -> Dict[str, Any]:
    """Explain any Bambu Studio setting by JSON key, GUI label, or keyword (e.g. 'infill', 'wall_loops', 'seam', 'support', 'hole', 'brim')."""
    return explain_setting(query)


def smart_slicing_advisor(
    goal: str,
    filament_type: str = "PLA",
    nozzle_size_mm: float = 0.4,
    has_overhangs: Optional[bool] = None,
) -> Dict[str, Any]:
    """Recommend optimal Bambu Studio slicer settings and GUI locations for a plain-English goal.

    Examples of `goal`:
    - 'strong functional bracket'
    - 'high detail miniature figurine'
    - 'fast draft prototype'
    - 'dimensionally accurate tight fit holes'
    - 'easy support removal'
    - 'watertight planter container'
    - 'prevent warping on large flat part'
    - 'multicolor low waste AMS'
    """
    return recommend_print_settings(
        goal=goal,
        filament_type=filament_type,
        nozzle_size_mm=nozzle_size_mm,
        has_overhangs=has_overhangs,
    )


def diagnose_print_defect(symptom_description: str) -> Dict[str, Any]:
    """Diagnose a 3D print failure or quality defect (e.g., 'nozzle scraping infill', 'corners warping', 'stringing', 'supports fused', 'holes too tight', 'pillowing') and return exact Bambu Studio fixes."""
    return diagnose_print_issue(symptom_description)


def list_bambu_profiles(
    category: str = "machine",
    search: Optional[str] = None,
    printer_filter: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """List printer-agnostic profiles discovered from Bambu Studio's local system and user folders.

    - `category`: 'machine' (printers/nozzles), 'filament' (PLA, PETG, ABS, etc.), or 'process' (layer height/quality profiles)
    - `search`: Optional substring filter on profile name (e.g. 'P1S', 'A1', '0.20mm', 'PLA', 'Strength')
    - `printer_filter`: Optional printer compatibility filter (e.g. 'Bambu Lab X1 Carbon 0.4 nozzle')
    """
    return catalog.list_profiles(
        category=category,
        search=search,
        printer_filter=printer_filter,
        limit=limit,
    )


def inspect_bambu_profile(
    category: str,
    profile_name: str,
    keys_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Resolve the complete inheritance chain of a Bambu Studio profile ('machine', 'filament', or 'process') and return its resolved settings."""
    resolved, chain = catalog.resolve_profile(category, profile_name)
    if not resolved:
        return {"error": f"Profile '{profile_name}' not found in category '{category}'."}

    if keys_filter:
        filtered = {k: resolved.get(k) for k in keys_filter if k in resolved}
    else:
        # Return key actionable settings by default to avoid flooding context with 300+ internal parameters
        important_keys = [
            "name", "inherits", "printer_model", "nozzle_diameter", "Printable Area",
            "printable_height", "layer_height", "initial_layer_print_height", "line_width",
            "wall_loops", "top_shell_layers", "bottom_shell_layers",
            "sparse_infill_density", "sparse_infill_pattern", "outer_wall_speed",
            "inner_wall_speed", "sparse_infill_speed", "initial_layer_speed",
            "enable_support", "support_type", "support_on_build_plate_only",
            "support_top_z_distance", "brim_type", "brim_width", "seam_position",
            "wall_generator", "elefant_foot_compensation", "xy_hole_compensation",
            "filament_type", "nozzle_temperature", "hot_plate_temp",
            "textured_plate_temp", "cool_plate_temp", "filament_max_volumetric_speed",
        ]
        filtered = {k: resolved[k] for k in important_keys if k in resolved}

    return {
        "category": category,
        "profile_name": resolved.get("name", profile_name),
        "inheritance_chain": chain,
        "total_resolved_keys": len(resolved),
        "settings": filtered,
    }


def compare_bambu_profiles(
    category: str,
    profile_a: str,
    profile_b: str,
) -> Dict[str, Any]:
    """Compare two Bambu Studio profiles side-by-side and return all settings that differ between them."""
    return catalog.compare_profiles(category, profile_a, profile_b)


def create_custom_preset(
    category: str,
    base_profile_name: str,
    new_preset_name: str,
    overrides: Dict[str, Any],
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create and save a custom Bambu Studio user preset based on an existing profile plus setting overrides."""
    return catalog.save_custom_preset(
        category=category,
        base_profile_name=base_profile_name,
        new_preset_name=new_preset_name,
        overrides=overrides,
        output_path=output_path,
    )


def inspect_3d_model(file_path: str) -> Dict[str, Any]:
    """Inspect a .stl or .3mf 3D model for dimensions (mm), volume (cm³), 11-point printability audit (watertight, manifold, normals, floating shells, stability), overhang area, printer fit, and embedded Bambu 3MF metadata."""
    import importlib
    from . import model_3mf as _m3
    importlib.reload(_m3)
    return _m3.inspect_3d_model(file_path)


def optimize_3mf_project(
    input_3mf_path: str,
    goal: Optional[str] = None,
    filament_type: str = "PLA",
    nozzle_size_mm: float = 0.4,
    custom_overrides: Optional[Dict[str, Any]] = None,
    output_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Optimize a Bambu Studio .3mf project file by applying a Smart Slicing Advisor goal and/or custom setting overrides directly into the .3mf file."""
    merged_overrides: Dict[str, Any] = {}
    advisor_report = None

    # Auto-inspect geometry first so we know if supports/brim are needed
    geom = _inspect_3d_model(input_3mf_path)
    has_overhangs = geom.get("needs_supports_likely") if isinstance(geom, dict) else None

    if goal:
        advisor_report = recommend_print_settings(
            goal=goal,
            filament_type=filament_type,
            nozzle_size_mm=nozzle_size_mm,
            has_overhangs=has_overhangs,
        )
        merged_overrides.update(advisor_report.get("bambu_studio_overrides", {}))

    if isinstance(geom, dict) and geom.get("needs_brim_likely") and "brim_type" not in merged_overrides:
        merged_overrides["brim_type"] = "outer_only"
        merged_overrides["brim_width"] = "6"

    if custom_overrides:
        merged_overrides.update(custom_overrides)

    mod_res = modify_3mf_settings(
        input_3mf_path=input_3mf_path,
        settings_overrides=merged_overrides,
        output_3mf_path=output_3mf_path,
    )
    if advisor_report:
        mod_res["advisor_reasoning"] = advisor_report.get("why_these_settings", [])
    mod_res["geometry_summary"] = {
        "dimensions_mm": geom.get("dimensions_mm"),
        "volume_cm3": geom.get("volume_cm3"),
        "needs_supports_likely": geom.get("needs_supports_likely"),
        "needs_brim_likely": geom.get("needs_brim_likely"),
    }
    return mod_res


def add_plate_to_3mf(
    input_3mf_path: str,
    plate_name: str = "",
    output_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a new empty build plate to a Bambu Studio .3mf project file."""
    return add_empty_plate_to_3mf(
        input_3mf_path=input_3mf_path,
        plate_name=plate_name,
        output_3mf_path=output_3mf_path,
    )


def slice_model_headless(
    input_file: str,
    printer_profile: Optional[str] = None,
    process_profile: Optional[str] = None,
    filament_profile: Optional[str] = None,
    settings_overrides: Optional[Dict[str, Any]] = None,
    auto_orient: bool = False,
    auto_arrange: bool = True,
    output_3mf_path: Optional[str] = None,
    spool_cost_per_kg: float = 20.0,
) -> Dict[str, Any]:
    """Slice a .3mf or .stl model headlessly using the Bambu Studio CLI and return print time, filament usage (g/m), and cost."""
    return slice_model_cli(
        input_file=input_file,
        printer_profile=printer_profile,
        process_profile=process_profile,
        filament_profile=filament_profile,
        settings_overrides=settings_overrides,
        auto_orient=auto_orient,
        auto_arrange=auto_arrange,
        output_3mf_path=output_3mf_path,
        spool_cost_per_kg=spool_cost_per_kg,
    )


def parse_sliced_file_metrics(
    file_path: str,
    spool_cost_per_kg: float = 20.0,
) -> Dict[str, Any]:
    """Parse an existing sliced .gcode.3mf or .gcode file to extract print time, filament weight (g), length (m), layer count, and cost."""
    return parse_sliced_metadata(file_path=file_path, spool_cost_per_kg=spool_cost_per_kg)


def open_in_bambu_studio(file_path: Optional[str] = None) -> Dict[str, Any]:
    """Launch the Bambu Studio desktop GUI, optionally opening a .3mf or .stl file, or pass 'gui:<action>' to control the live window."""
    import importlib
    from . import gui_control as _gc
    importlib.reload(_gc)
    if file_path and file_path.startswith("gui:"):
        parts = file_path.split(":")
        act = parts[1] if len(parts) > 1 else "inspect"
        rx = int(parts[2]) if len(parts) > 2 else None
        ry = int(parts[3]) if len(parts) > 3 else None
        return _gc.control_bambu_gui(action=act, click_x_offset=rx, click_y_offset=ry)
    return open_in_bambu_studio_gui(file_path=file_path)


def control_bambu_studio_gui(
    action: str = "inspect",
    click_x_offset: Optional[int] = None,
    click_y_offset: Optional[int] = None,
) -> Dict[str, Any]:
    """Control or inspect the currently open Bambu Studio desktop GUI window (e.g., action='add_plate', 'auto_orient', 'auto_arrange', 'inspect', 'click_relative')."""
    import importlib
    from . import gui_control as _gc
    importlib.reload(_gc)
    return _gc.control_bambu_gui(
        action=action,
        click_x_offset=click_x_offset,
        click_y_offset=click_y_offset,
    )


def get_live_printer_status(
    ip: Optional[str] = None,
    access_code: Optional[str] = None,
    serial: Optional[str] = None,
) -> Dict[str, Any]:
    """Query live status, temperatures, print progress, and loaded AMS filaments from a Bambu Lab printer over LAN MQTT-TLS (port 8883)."""
    return query_printer_status(ip=ip, access_code=access_code, serial=serial)


def control_live_printer(
    action: str,
    value: Optional[str] = None,
    ip: Optional[str] = None,
    access_code: Optional[str] = None,
    serial: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a control command ('pause', 'resume', 'stop', 'light_on', 'light_off', or 'speed') to a Bambu Lab printer over LAN MQTT-TLS."""
    return send_printer_command(
        action=action,
        value=value,
        ip=ip,
        access_code=access_code,
        serial=serial,
    )


def match_ams_colors(
    target_colors: List[str],
    project_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Match target RGB/Hex colors to the closest AMS filament spools using perceptual CIELAB (Delta E 2000) color distance (inspired by heyixuan2/bambu-studio-ai)."""
    return match_ams_colors_cielab(
        target_colors=target_colors,
        project_3mf_path=project_3mf_path,
    )


def repair_3d_mesh(
    input_stl_path: str,
    output_stl_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Auto-repair an STL mesh: remove degenerate/duplicate triangles, fix inverted face normals, and ground the model flat onto Z=0.0 mm (inspired by heyixuan2/bambu-studio-ai & trimesh)."""
    return repair_and_ground_stl(
        input_stl_path=input_stl_path,
        output_stl_path=output_stl_path,
    )


def search_3d_models(
    query: str,
    platform: str = "all",
    max_results: int = 8,
) -> Dict[str, Any]:
    """Search MakerWorld, Printables, and Thangs for ready-to-print 3D models matching a query (inspired by heyixuan2/bambu-studio-ai)."""
    return _search_3d_models(
        query=query,
        platform=platform,
        max_results=max_results,
    )


def list_plates_in_3mf(input_3mf_path: str) -> Dict[str, Any]:
    """List all build plates (<plate>) and their assigned objects inside a Bambu Studio .3mf project file."""
    return _list_plates_in_3mf(input_3mf_path=input_3mf_path)


def remove_plate_from_3mf(
    input_3mf_path: str,
    plate_id: int,
    output_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Remove a specific build plate by plate_id from a Bambu Studio .3mf project file and re-number remaining plates."""
    return _remove_plate_from_3mf(
        input_3mf_path=input_3mf_path,
        plate_id=plate_id,
        output_3mf_path=output_3mf_path,
    )


def move_object_to_plate_in_3mf(
    input_3mf_path: str,
    object_identifier: str,
    target_plate_id: int,
    output_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Move a 3D object instance (matched by object_id or object_name) to another build plate inside a .3mf file."""
    return _move_object_to_plate_in_3mf(
        input_3mf_path=input_3mf_path,
        object_identifier=object_identifier,
        target_plate_id=target_plate_id,
        output_3mf_path=output_3mf_path,
    )


def set_object_settings_in_3mf(
    input_3mf_path: str,
    object_identifier: str,
    settings_overrides: Dict[str, Any],
    output_3mf_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Set per-object slicer overrides (e.g. extruder AMS slot, wall_loops, sparse_infill_density, enable_support) on a specific object in a .3mf file."""
    return _set_object_settings_in_3mf(
        input_3mf_path=input_3mf_path,
        object_identifier=object_identifier,
        settings_overrides=settings_overrides,
        output_3mf_path=output_3mf_path,
    )


def get_calibration_guide(
    calibration_type: str = "all",
    filament_type: str = "PLA",
) -> Dict[str, Any]:
    """Get step-by-step Bambu Studio Calibration tab workflows, formulas, and target ranges (flow_dynamics, flow_rate, max_volumetric_speed, temperature_and_retraction)."""
    return _get_calibration_guide(
        calibration_type=calibration_type,
        filament_type=filament_type,
    )


ALL_TOOLS: List[Callable[..., Any]] = [
    bambu_environment_info,
    explain_bambu_setting,
    smart_slicing_advisor,
    diagnose_print_defect,
    get_calibration_guide,
    list_bambu_profiles,
    inspect_bambu_profile,
    compare_bambu_profiles,
    create_custom_preset,
    inspect_3d_model,
    optimize_3mf_project,
    add_plate_to_3mf,
    list_plates_in_3mf,
    remove_plate_from_3mf,
    move_object_to_plate_in_3mf,
    set_object_settings_in_3mf,
    slice_model_headless,
    parse_sliced_file_metrics,
    open_in_bambu_studio,
    control_bambu_studio_gui,
    get_live_printer_status,
    control_live_printer,
    match_ams_colors,
    repair_3d_mesh,
    search_3d_models,
]


# ---------------------------------------------------------------------------
# ZERO-DEPENDENCY JSON-RPC 2.0 STDIO MCP SERVER FALLBACK
# ---------------------------------------------------------------------------

def _python_type_to_json_schema(tp: Any) -> Dict[str, Any]:
    origin = getattr(tp, "__origin__", None)
    args = getattr(tp, "__args__", ())
    if origin is UnionType or str(origin).endswith("Union"):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _python_type_to_json_schema(non_none[0])
    if tp in (str, "str", "Optional[str]"):
        return {"type": "string"}
    if tp in (int, "int", "Optional[int]"):
        return {"type": "integer"}
    if tp in (float, "float", "Optional[float]"):
        return {"type": "number"}
    if tp in (bool, "bool", "Optional[bool]"):
        return {"type": "boolean"}
    if origin in (list, List) or str(tp).startswith(("List[", "Optional[List[")):
        return {"type": "array", "items": {"type": "string"}}
    if origin in (dict, Dict) or str(tp).startswith(("Dict[", "Optional[Dict[")):
        return {"type": "object"}
    return {"type": "string"}


UnionType = type(Optional[str])


def _build_tool_schema(fn: Callable[..., Any]) -> Dict[str, Any]:
    sig = inspect.signature(fn)
    props: Dict[str, Any] = {}
    required: List[str] = []

    for param_name, param in sig.parameters.items():
        ann = param.annotation
        schema = _python_type_to_json_schema(ann)
        if param.default is not inspect.Parameter.empty:
            if param.default is not None:
                schema["default"] = param.default
        else:
            required.append(param_name)
        props[param_name] = schema

    return {
        "name": fn.__name__,
        "description": (inspect.getdoc(fn) or "").strip(),
        "inputSchema": {
            "type": "object",
            "properties": props,
            "required": required,
        },
    }


def _run_stdio_fallback_server() -> None:
    """Lightweight MCP-compliant JSON-RPC 2.0 server over stdin/stdout."""
    tool_map = {fn.__name__: fn for fn in ALL_TOOLS}
    tool_schemas = [_build_tool_schema(fn) for fn in ALL_TOOLS]

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params") or {}

        # Notifications have no id and expect no response
        if req_id is None:
            continue

        result: Any = None
        error: Optional[Dict[str, Any]] = None

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": "bambu-studio-mcp",
                        "version": "0.1.0",
                    },
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": tool_schemas}
            elif method == "tools/call":
                t_name = params.get("name")
                t_args = params.get("arguments") or {}
                if t_name not in tool_map:
                    error = {"code": -32601, "message": f"Unknown tool: {t_name}"}
                else:
                    out = tool_map[t_name](**t_args)
                    result = {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(out, indent=2, default=str),
                            }
                        ],
                        "isError": False,
                    }
            elif method == "resources/list":
                result = {"resources": []}
            elif method == "prompts/list":
                result = {"prompts": []}
            else:
                error = {"code": -32601, "message": f"Method not found: {method}"}
        except Exception as exc:
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"error": str(exc)}, indent=2),
                    }
                ],
                "isError": True,
            }

        resp: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id}
        if error is not None:
            resp["error"] = error
        else:
            resp["result"] = result

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


def main() -> None:
    """Run the Bambu Studio MCP server via FastMCP if installed, or built-in stdio MCP server."""
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore

        mcp = FastMCP("Bambu Studio MCP")
        for fn in ALL_TOOLS:
            mcp.tool()(fn)
        mcp.run()
    except ImportError:
        _run_stdio_fallback_server()


if __name__ == "__main__":
    main()
