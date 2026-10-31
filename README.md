# Bambu Studio MCP (`bambu-studio-mcp`)

A full-featured, **100% printer-agnostic Model Context Protocol (MCP) server** for **Bambu Studio** and **Bambu Lab 3D printers**.

Bambu Studio is powerful, but its interface exposes 200+ dense, interconnected parameters across 6 tabs (`Quality`, `Strength`, `Speed`, `Support`, `Others`, `Filament`). **`bambu-studio-mcp`** bridges the gap between plain-English intent and Bambu Studio's slicer engine, profiles, 3MF project files, headless CLI, live desktop GUI window, and live printer/AMS hardware.

---

## Key Capabilities

1. **Smart Slicing Advisor & Settings Encyclopedia**
   - **`smart_slicing_advisor`**: Translates plain-English goals (e.g., *"strong functional bracket"*, *"high detail miniature"*, *"fast draft prototype"*, *"watertight planter"*, *"dimensionally accurate tight holes"*, *"AMS low-poop multicolor"*) + filament type (`PLA`, `PETG`, `ABS`, `ASA`, `TPU`, `Silk PLA`, `PA-CF`) + nozzle size (`0.2`, `0.4`, `0.6`, `0.8` mm) into concrete Bambu Studio setting overrides **and** a step-by-step GUI walkthrough (`Tab -> Section -> Field`).
   - **`explain_bambu_setting`**: Demystifies any Bambu Studio JSON key or GUI label with plain-English explanations, recommended ranges, and trade-offs.
   - **`diagnose_print_defect`**: Diagnoses common failures (nozzle scraping Grid infill, warping corners, stringing, fused supports, tight tolerances, pillowing) and returns exact setting fixes.

2. **Live Desktop GUI Automation**
   - **`control_bambu_studio_gui`**: Interacts directly with your currently open Bambu Studio desktop window—click **Add Plate** (`add_plate`), **Add Object** (`add_object`), **Auto Orient** (`auto_orient`), **Arrange** (`auto_arrange`), **Variable Layer Height** (`variable_layer_height`), **Slice Plate** (`slice_plate`), switch tabs (`tab_prepare`, `tab_preview`, `tab_device`, `tab_project`), or inspect and screenshot the live window (`inspect`).

3. **100% Printer-Agnostic Profile Discovery & Preset Builder**
   - **`list_bambu_profiles`**: Automatically discovers all installed **Machine** (X1C, P1S, P1P, A1, A1 mini, X1E, H2D, P2S, Prusa, Voron, Creality, etc.), **Filament**, and **Process** profiles from your local Bambu Studio installation and user folders across Windows, macOS, and Linux.
   - **`inspect_bambu_profile`**: Resolves Bambu Studio's multi-level `"inherits"` chain from base template to leaf preset.
   - **`compare_bambu_profiles`**: Diffs any two profiles side-by-side (e.g., `0.20mm Standard` vs. `0.20mm Strength`).
   - **`create_custom_preset`**: Saves custom presets directly into your Bambu Studio `user` presets folder so they appear in your dropdowns.

4. **3MF & STL Geometry Inspector, 11-Point Printability Audit & Auto-Repair**
   - **`inspect_3d_model`**: Pure-Python `.stl` (binary & ASCII) and `.3mf` analyzer that calculates bounding box dimensions ($X \times Y \times Z$ in mm), volume ($\text{cm}^3$), surface area, bottom bed contact area, steep overhang area ($>35^\circ$), estimated PLA weight, build-volume fit, and an **11-Point Printability & Topology Audit** (`0–100` score covering watertight manifold check, non-manifold edges, degenerate faces, outward normals, floating mid-air shells, bed adhesion, tipping stability, overhang severity, bridge risk, scale sanity, and printer fit).
   - **`repair_3d_mesh`**: Automatically repairs an `.stl` mesh—removes zero-area degenerate and duplicate triangles, flips inverted face normals if total signed volume is negative, and grounds the model flat onto $Z = 0.0\text{ mm}$.
   - **`optimize_3mf_project`**: Injects Smart Advisor recommendations or custom overrides directly into a `.3mf` file's `Metadata/project_settings.config` without opening the GUI.
   - **`add_plate_to_3mf`**: Programmatically adds a new empty build plate (`<plate>`) to any `.3mf` project file.

5. **Perceptual CIELAB ($\Delta E_{2000}$) AMS Color Matching & 3D Model Discovery**
   - **`match_ams_colors`**: Converts target RGB/Hex colors into perceptual **CIELAB ($L^*, a^*, b^*$)** space and computes **CIEDE2000 ($\Delta E_{2000}$)** color distance against your `.3mf` project's loaded filaments (or the official Bambu Lab PLA Basic palette) to recommend the best AMS slot mapping.
   - **`search_3d_models`**: Searches **MakerWorld**, **Printables**, and **Thangs** for ready-to-print 3D models with live download/like counts and direct URLs.

6. **Headless CLI Slicing, Cost/Time Estimator & GUI Launcher**
   - **`slice_model_headless`**: Runs `bambu-studio` CLI headlessly (`--slice 0 --export-3mf`) with resolved printer/process/filament profiles and overrides.
   - **`parse_sliced_file_metrics`**: Extracts exact print time (`Xh Ym Zs`), filament weight (g), length (m), per-slot AMS usage, layer count, and estimated filament cost (`$`) from any `.gcode.3mf` or `.gcode` file.
   - **`open_in_bambu_studio`**: Opens any `.3mf` or `.stl` directly in the Bambu Studio desktop application.

7. **Direct Live Printer & AMS Control (Local LAN MQTT-TLS)**
   - **`get_live_printer_status`**: Zero-dependency native Python TLS MQTT 3.1.1 client connecting to port `8883` (`bblp` + LAN Access Code) to read live print progress, layer number, remaining time, nozzle/bed/chamber temperatures, HMS alerts, and loaded AMS slots (filament type, hex color, remaining %).
   - **`control_live_printer`**: Pause, resume, or stop prints, toggle the chamber light, or change print speed (`Silent`, `Standard`, `Sport`, `Ludicrous`).

---

## Zero-Dependency Quick Start

`bambu-studio-mcp` includes both `FastMCP` support and a built-in standard-library JSON-RPC 2.0 `stdio` MCP fallback, meaning **it runs out-of-the-box on any Python 3.10+ installation even before installing third-party packages**.

### Option 1: Install via `pip`
```bash
git clone https://github.com/BananaRama123/bambu-studio-mcp.git
cd bambu-studio-mcp
pip install -e .
```
Then add to your MCP client configuration (`~/.gemini/config/mcp_config.json`, Claude Desktop, Cursor, etc.):
```json
{
  "mcpServers": {
    "bambu-studio": {
      "command": "bambu-studio-mcp"
    }
  }
}
```

### Option 2: Run Directly from Source (Zero Install)
```json
{
  "mcpServers": {
    "bambu-studio": {
      "command": "python",
      "args": ["-u", "-m", "bambu_studio_mcp.server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/bambu-studio-mcp/src"
      }
    }
  }
}
```

---

## Available MCP Tools (24 Tools)

| Tool Name | Purpose |
| :--- | :--- |
| `bambu_environment_info` | Auto-discover Bambu Studio executable, profile folders, and active presets in `BambuStudio.conf` |
| `smart_slicing_advisor` | Convert a plain-English goal + filament + nozzle size into Bambu Studio overrides & GUI walkthrough |
| `explain_bambu_setting` | Search the Bambu Studio Settings Encyclopedia (50+ settings) by JSON key, GUI label, or keyword |
| `diagnose_print_defect` | Diagnose print defects/failures (scraping, warping, stringing, fused supports, tight holes) |
| `get_calibration_guide` | Step-by-step Bambu Studio Calibration workflows, formulas & targets (`flow_dynamics`, `flow_rate`, `max_volumetric_speed`, `temperature_and_retraction`) |
| `control_bambu_studio_gui` | Closed-loop desktop GUI controller (`add_plate`, `remove_plate`, `select_plate_1`..`6`, `view_top`, `slice_plate`, `self_test`, etc.) |
| `list_bambu_profiles` | Search discovered `machine`, `filament`, and `process` profiles across all printers |
| `inspect_bambu_profile` | Resolve the full `inherits` chain of any profile and inspect its settings |
| `compare_bambu_profiles` | Compare two profiles side-by-side and return all differing keys |
| `create_custom_preset` | Create and save a custom user preset into Bambu Studio's user folder |
| `inspect_3d_model` | Analyze `.stl` / `.3mf` geometry, volume, overhangs, 11-point printability audit, and printer fit |
| `repair_3d_mesh` | Auto-repair an `.stl` mesh (remove degenerate/duplicate faces, fix inverted normals, ground onto $Z=0$) |
| `match_ams_colors` | Perceptual CIELAB ($\Delta E_{2000}$) color matching between target RGB/Hex colors and AMS spools |
| `search_3d_models` | Search MakerWorld, Printables, and Thangs for ready-to-print 3D models |
| `optimize_3mf_project` | Inject Smart Advisor settings directly into a `.3mf` project file |
| `add_plate_to_3mf` | Add a new empty build plate (`<plate>`) to a `.3mf` project file |
| `list_plates_in_3mf` | List all `<plate>` entries, lock states, and assigned 3D objects inside a `.3mf` project |
| `remove_plate_from_3mf` | Remove a specific plate by ID from a `.3mf` project and re-number remaining plates (`1..N`) |
| `move_object_to_plate_in_3mf` | Move any 3D object instance (by ID or name) to another build plate inside a `.3mf` project |
| `set_object_settings_in_3mf` | Set per-object slicer overrides (`extruder` AMS slot, `wall_loops`, `sparse_infill_density`, `enable_support`) on a specific object in a `.3mf` file |
| `slice_model_headless` | Slice a `.3mf` or `.stl` via headless Bambu Studio CLI and return time/weight/cost |
| `parse_sliced_file_metrics` | Extract print time, filament grams/meters, and cost from `.gcode.3mf` or `.gcode` |
| `open_in_bambu_studio` | Launch Bambu Studio GUI with a `.3mf` or `.stl` file loaded |
| `get_live_printer_status` | Query live printer progress, temps, HMS alerts, and AMS filament trays over LAN MQTT |
| `control_live_printer` | Pause, resume, stop, toggle light, or change speed level on a live printer |

---

## Running the Automated Test Suite

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## Acknowledgments & Upstream Credits

Special thanks to the open-source projects and authors whose work inspired key capabilities in `bambu-studio-mcp`:

- **[`heyixuan2/bambu-studio-ai`](https://github.com/heyixuan2/bambu-studio-ai)** by **[@heyixuan2](https://github.com/heyixuan2)** — Inspired the **11-Point Printability Audit**, **perceptual CIELAB ($\Delta E$) nearest-neighbor AMS color mapping**, **automated mesh repair**, and **MakerWorld / Printables model discovery** pipelines.
- **[`mikedh/trimesh`](https://github.com/mikedh/trimesh)** by **[@mikedh](https://github.com/mikedh)** (Michael Dawson-Haggerty et al.) — Upstream reference for 3D triangle mesh topology verification, watertight manifold checks, and mesh repair conventions used by `bambu-studio-ai`.
- **[`BambuTools/bambulabs_api`](https://github.com/BambuTools/bambulabs_api)** — Upstream reference for Bambu Lab LAN MQTT telemetry and AMS tray schemas.
- **[`bambulab/BambuStudio`](https://github.com/bambulab/BambuStudio)** — Bambu Lab's open-source slicer engine, profile inheritance architecture, and 3MF project format.
