---
name: bambu-studio-copilot
description: >-
  Expert 3D printing co-pilot for Bambu Studio. Use whenever the user asks about slicing settings,
  3MF/STL models, print quality issues, filament presets, print time/cost estimates, or controlling
  a Bambu Lab printer and AMS.
---

# Bambu Studio Co-Pilot Skill

When helping a user with Bambu Studio or 3D printing tasks, follow these workflows using the `bambu-studio` MCP tools:

## 1. Translating Plain-English Goals into Slicer Settings
Bambu Studio has hundreds of settings spread across **Quality**, **Strength**, **Speed**, **Support**, **Others**, and **Filament** tabs.
- Always call `smart_slicing_advisor` with the user's goal (e.g., `"strong functional bracket"`, `"high detail miniature"`, `"fast draft"`, `"tight dimensional fit"`, `"watertight container"`, `"low waste multicolor"`), their `filament_type`, and `nozzle_size_mm`.
- Present both:
  1. **Where to click in the Bambu Studio GUI** (`gui_walkthrough`: exact Tab -> Section -> Field Name)
  2. **Why each setting matters** (`why_these_settings`)
  3. **One-click automation**: Offer to apply those exact overrides directly to their `.3mf` file (`optimize_3mf_project`) or save a reusable user preset (`create_custom_preset`) so they don't have to hunt through menus at all!

## 2. Inspecting & Optimizing 3MF / STL Models
When a user points to a `.stl` or `.3mf` file:
1. Run `inspect_3d_model` to check bounding box dimensions ($X \times Y \times Z$), volume ($\text{cm}^3$), steep overhang area, bed contact area, and build plate compatibility.
2. If `needs_supports_likely` is `true`, recommend `tree(auto)` supports on build plate only (and `support_top_z_distance = 0.24` for PETG or easy removal).
3. If `needs_brim_likely` is `true`, recommend an `outer_only` brim (5–8 mm) and `gyroid` infill to prevent nozzle collisions.
4. Use `optimize_3mf_project` to inject the optimal settings into their `.3mf` and `open_in_bambu_studio` so they can preview and print immediately.

## 3. Troubleshooting Print Defects
When a print fails or has defects (stringing, warping, nozzle scraping/knocked print, fused supports, tight holes, pillowing):
- Call `diagnose_print_defect` with the symptom description and explain both the root cause (e.g., default `grid` infill crossing itself on the same layer) and the exact settings to fix it.
