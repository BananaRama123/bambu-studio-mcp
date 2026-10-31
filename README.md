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

4. **3MF & STL Geometry Inspector & Project Optimizer**
   - **`inspect_3d_model`**: Pure-Python `.stl` (binary & ASCII) and `.3mf` analyzer that calculates bounding box dimensions ($X \times Y \times Z$ in mm), volume ($\text{cm}^3$), surface area, bottom bed contact area, steep overhang area ($>35^\circ$), estimated PLA weight, and build-volume fit across Bambu printers.
   - **`optimize_3mf_project`**: Injects Smart Advisor recommendations or custom overrides directly into a `.3mf` file's `Metadata/project_settings.config` without opening the GUI.
   - **`add_plate_to_3mf`**: Programmatically adds a new empty build plate (`<plate>`) to any `.3mf` project file.

5. **Headless CLI Slicing, Cost/Time Estimator & GUI Launcher**
   - **`slice_model_headless`**: Runs `bambu-studio` CLI headlessly (`--slice 0 --export-3mf`) with resolved printer/process/filament profiles and overrides.
   - **`parse_sliced_file_metrics`**: Extracts exact print time (`Xh Ym Zs`), filament weight (g), length (m), per-slot AMS usage, layer count, and estimated filament cost (`$`) from any `.gcode.3mf` or `.gcode` file.
   - **`open_in_bambu_studio`**: Opens any `.3mf` or `.stl` directly in the Bambu Studio desktop application.

6. **Direct Live Printer & AMS Control (Local LAN MQTT-TLS)**
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

## Available MCP Tools (17 Tools)

| Tool Name | Purpose |
| :--- | :--- |
| `bambu_environment_info` | Auto-discover Bambu Studio executable, profile folders, and active presets in `BambuStudio.conf` |
| `smart_slicing_advisor` | Convert a plain-English goal + filament + nozzle size into Bambu Studio overrides & GUI walkthrough |
| `explain_bambu_setting` | Search the Bambu Studio Settings Encyclopedia by JSON key, GUI label, or keyword |
| `diagnose_print_defect` | Diagnose print defects/failures (scraping, warping, stringing, fused supports, tight holes) |
| `control_bambu_studio_gui` | Control or inspect the live open Bambu Studio desktop window (`add_plate`, `slice_plate`, `auto_orient`, etc.) |
| `list_bambu_profiles` | Search discovered `machine`, `filament`, and `process` profiles across all printers |
| `inspect_bambu_profile` | Resolve the full `inherits` chain of any profile and inspect its settings |
| `compare_bambu_profiles` | Compare two profiles side-by-side and return all differing keys |
| `create_custom_preset` | Create and save a custom user preset into Bambu Studio's user folder |
| `inspect_3d_model` | Analyze `.stl` / `.3mf` geometry, volume, overhangs, bed stability, and printer fit |
| `optimize_3mf_project` | Inject Smart Advisor settings directly into a `.3mf` project file |
| `add_plate_to_3mf` | Add a new empty build plate (`<plate>`) to a `.3mf` project file |
| `slice_model_headless` | Slice a `.3mf` or `.stl` via headless Bambu Studio CLI and return time/weight/cost |
| `parse_sliced_file_metrics` | Extract print time, filament grams/meters, and cost from `.gcode.3mf` or `.gcode` |
| `open_in_bambu_studio` | Launch Bambu Studio GUI with a `.3mf` or `.stl` file loaded |
| `get_live_printer_status` | Query live printer progress, temps, HMS alerts, and AMS filament trays over LAN MQTT |
| `control_live_printer` | Pause, resume, stop, toggle light, or change speed level on a live printer |
