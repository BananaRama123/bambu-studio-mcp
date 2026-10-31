"""Bambu Studio Settings Encyclopedia, Smart Slicing Advisor, and Troubleshooting Engine.

Translates between confusing Bambu Studio internal JSON keys, GUI tabs/labels,
and plain-English user goals or print quality issues.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 1. BAMBU STUDIO SETTINGS ENCYCLOPEDIA
# ---------------------------------------------------------------------------
SETTINGS_ENCYCLOPEDIA: Dict[str, Dict[str, Any]] = {
    # --- QUALITY TAB ---
    "layer_height": {
        "gui_tab": "Quality -> Layer height",
        "gui_label": "Layer height",
        "type": "float (mm)",
        "default_04_nozzle": "0.2",
        "recommended_range": "0.08 - 0.28 mm (for 0.4mm nozzle, 20%-70% of nozzle diameter)",
        "summary": "Vertical thickness of each printed layer. Primary control for vertical resolution vs. print time.",
        "when_to_change": "Lower (0.08-0.12mm) for miniatures, curved top surfaces, and fine detail. Raise (0.24-0.28mm) for rapid functional drafts.",
        "tradeoffs": "Halving layer height roughly doubles print time and slightly reduces inter-layer strength if too thin.",
    },
    "initial_layer_print_height": {
        "gui_tab": "Quality -> Layer height",
        "gui_label": "First layer height",
        "type": "float (mm)",
        "default_04_nozzle": "0.2",
        "recommended_range": "0.20 - 0.28 mm",
        "summary": "Height of the very first layer on the build plate.",
        "when_to_change": "Keep at 0.20mm or 0.24mm even when printing 0.08mm layers so the first layer absorbs bed unevenness and sticks reliably.",
        "tradeoffs": "Too thin (<0.16mm) risks nozzle scraping or poor adhesion.",
    },
    "line_width": {
        "gui_tab": "Quality -> Line width",
        "gui_label": "Default line width",
        "type": "float or % (mm)",
        "default_04_nozzle": "0.42",
        "recommended_range": "0.40 - 0.50 mm (for 0.4mm nozzle)",
        "summary": "Width of extruded plastic lines.",
        "when_to_change": "Increase outer/infill line width up to 0.50-0.60mm on a 0.4mm nozzle for stronger parts and faster vase-mode walls.",
        "tradeoffs": "Wider lines slightly round off sharp external corners.",
    },
    "seam_position": {
        "gui_tab": "Quality -> Seam",
        "gui_label": "Seam position",
        "type": "enum",
        "options": ["nearest", "aligned", "back", "random"],
        "default_04_nozzle": "aligned",
        "summary": "Controls where the nozzle starts and stops each outer wall loop (the vertical Z-seam line).",
        "when_to_change": "Use 'aligned' for models with corners (hides seam in sharp corners), 'back' for figurines/statues (puts seam on back), or 'random' for cylindrical parts where a vertical ridge must be avoided.",
        "tradeoffs": "'random' eliminates a vertical line but leaves tiny pimples/dots scattered across the surface.",
    },
    "scarf_angle_threshold": {
        "gui_tab": "Quality -> Seam",
        "gui_label": "Scarf joint seam (Contour/Angle threshold)",
        "type": "float (degrees)",
        "default_04_nozzle": "155",
        "summary": "Ramps the start and end of outer wall loops over a ramped overlap to make Z-seams nearly invisible on smooth cylinders.",
        "when_to_change": "Enable Scarf Joint (Contour) when printing smooth round cylinders or organic models without sharp corners.",
        "tradeoffs": "Slightly increases outer wall print time and requires well-tuned flow/pressure advance.",
    },
    "seam_slope_type": {
        "gui_tab": "Quality -> Seam",
        "gui_label": "Scarf joint seam",
        "type": "enum",
        "options": ["none", "contour", "all"],
        "default_04_nozzle": "none",
        "summary": "Enables a tapered 'scarf joint' overlap at the start and end of wall loops to hide vertical Z-seams on smooth cylinders and curved surfaces.",
        "when_to_change": "Set to 'contour' (outer wall only) or 'all' when printing round cylinders, tubes, or smooth organic shapes that lack sharp corners to hide a traditional seam.",
        "tradeoffs": "Requires well-calibrated Flow Dynamics (K-factor); can leave slight artifacts on sharp corners if scarf_angle_threshold is too low.",
    },
    "ironing_type": {
        "gui_tab": "Quality -> Ironing",
        "gui_label": "Ironing Type",
        "type": "enum",
        "options": ["no ironing", "top surfaces", "topmost surface", "all solid layers"],
        "default_04_nozzle": "no ironing",
        "summary": "Passes the hot nozzle over flat top surfaces a second time extruding a tiny amount (10-15%) of filament to melt lines flat for an injection-molded finish.",
        "when_to_change": "Set to 'top surfaces' (with ironing_flow ~15%, ironing_speed ~30-60mm/s) for signs, badges, coasters, and flat-topped boxes.",
        "tradeoffs": "Adds time to flat top layers; has no benefit on curved/domed tops.",
    },
    "ironing_flow": {
        "gui_tab": "Quality -> Ironing",
        "gui_label": "Ironing flow",
        "type": "percent string (e.g. '15%')",
        "default_04_nozzle": "10%",
        "recommended_range": "10% - 22%",
        "summary": "Percentage of normal flow extruded during the top-surface ironing pass to fill microscopic ridges between top lines.",
        "when_to_change": "Increase from 10% to 15%-18% for PLA/PETG on modern high-speed Bambu printers (P1S/X1C/A1) where 10% can leave faint under-ironed lines.",
        "tradeoffs": "Too high (>22%) pushes excess molten plastic to the perimeter edges of the top surface, creating a raised lip.",
    },
    "ironing_speed": {
        "gui_tab": "Quality -> Ironing",
        "gui_label": "Ironing speed",
        "type": "float (mm/s)",
        "default_04_nozzle": "30",
        "recommended_range": "30 - 65 mm/s",
        "summary": "Speed of the nozzle during the top-surface ironing pass.",
        "when_to_change": "Use 30-45 mm/s for small plaques/text or 50-65 mm/s (paired with 15-18% ironing_flow) for large flat lids to achieve a uniform matte/satin finish faster.",
        "tradeoffs": "Too slow on PLA can heat-creep or scorch light-colored filaments; too fast fails to melt lines together.",
    },
    "wall_generator": {
        "gui_tab": "Quality -> Wall generator",
        "gui_label": "Wall generator",
        "type": "enum",
        "options": ["classic", "arachne"],
        "default_04_nozzle": "classic",
        "summary": "Algorithm used to generate perimeter walls. 'Arachne' dynamically varies line width for thin walls and sharp text.",
        "when_to_change": "Switch to 'arachne' for fine embossed/debossed text, logos, gears, or thin tapered walls.",
        "tradeoffs": "'classic' can be slightly more predictable on uniform geometric shells.",
    },
    "elefant_foot_compensation": {
        "gui_tab": "Quality -> Precision",
        "gui_label": "Elephant foot compensation",
        "type": "float (mm)",
        "default_04_nozzle": "0.15",
        "recommended_range": "0.10 - 0.25 mm",
        "summary": "Shrinks the first layer contour inward slightly to counteract the outward squish of the first layer against the build plate.",
        "when_to_change": "Increase to 0.20mm for print-in-place mechanisms, gears, or parts that fit into slots.",
        "tradeoffs": "Too high reduces first-layer contact area on very small footprints.",
    },
    "xy_hole_compensation": {
        "gui_tab": "Quality -> Precision",
        "gui_label": "X-Y hole compensation",
        "type": "float (mm)",
        "default_04_nozzle": "0",
        "recommended_range": "0.05 - 0.15 mm",
        "summary": "Expands internal horizontal holes by the specified radius to compensate for plastic shrinkage and polygon approximation.",
        "when_to_change": "Set to +0.08mm to +0.15mm when screw holes, dowel pins, or bearings fit too tightly.",
        "tradeoffs": "Only affects closed internal holes in X/Y, not outer contours.",
    },
    "xy_contour_compensation": {
        "gui_tab": "Quality -> Precision",
        "gui_label": "X-Y contour compensation",
        "type": "float (mm)",
        "default_04_nozzle": "0",
        "recommended_range": "-0.15 to +0.15 mm",
        "summary": "Expands (+) or shrinks (-) the outer boundary contour in X/Y for outer dimensional scaling tolerance.",
        "when_to_change": "Set to -0.05mm to -0.10mm when external pegs/tabs/threads are too tight to fit into mating slots, or +0.05mm to compensate for high-shrinkage engineering polymers (ABS/ASA/PA).",
        "tradeoffs": "Shifts all outer X/Y dimensions by twice the compensation value (radius offset).",
    },
    "bridge_flow": {
        "gui_tab": "Quality -> Advanced",
        "gui_label": "Bridge flow",
        "type": "float ratio",
        "default_04_nozzle": "1",
        "recommended_range": "0.85 - 1.0",
        "summary": "Extrusion flow multiplier applied to unsupported horizontal bridges.",
        "when_to_change": "Lower slightly to 0.90-0.95 (paired with lower bridge_speed) so bridged strands stay under slight tension instead of sagging downward.",
        "tradeoffs": "Too low (<0.80) causes bridged strands to snap mid-air.",
    },
    "wall_sequence": {
        "gui_tab": "Quality -> Walls and surfaces",
        "gui_label": "Order of walls",
        "type": "enum",
        "options": ["inner/outer", "outer/inner", "inner/outer/inner"],
        "default_04_nozzle": "inner/outer",
        "summary": "Determines which perimeter wall loop prints first on each layer.",
        "when_to_change": "Use 'inner/outer/inner' for best surface finish and dimensional accuracy when overhangs are <45 deg; keep 'inner/outer' when steep overhangs (>50 deg) need an inner wall to grab onto.",
        "tradeoffs": "'outer/inner' gives great dimensional accuracy but poor steep overhang performance.",
    },

    # --- STRENGTH TAB ---
    "wall_loops": {
        "gui_tab": "Strength -> Walls",
        "gui_label": "Wall loops",
        "type": "int",
        "default_04_nozzle": "2",
        "recommended_range": "2 - 6",
        "summary": "Number of perimeter shells around the outside of the part. **Adding wall loops increases part strength far more efficiently than increasing infill %!**",
        "when_to_change": "Use 2 for decorative models, 3-4 for general functional parts, and 5-6 for heavy-duty brackets, hooks, or threaded inserts.",
        "tradeoffs": "Increases filament usage and print time on perimeter-heavy models.",
    },
    "top_shell_layers": {
        "gui_tab": "Strength -> Top/bottom shells",
        "gui_label": "Top shell layers",
        "type": "int",
        "default_04_nozzle": "5",
        "recommended_range": "4 - 7 (or at least 0.8mm - 1.2mm total thickness)",
        "summary": "Number of solid layers closing the top of the model over sparse infill.",
        "when_to_change": "Increase to 6-8 when using low infill (<15%) or small layer heights (0.08-0.12mm) to prevent 'pillowing' (bumps/holes on top surfaces).",
        "tradeoffs": "Slightly increases print time on flat horizontal roofs.",
    },
    "bottom_shell_layers": {
        "gui_tab": "Strength -> Top/bottom shells",
        "gui_label": "Bottom shell layers",
        "type": "int",
        "default_04_nozzle": "3",
        "recommended_range": "3 - 6",
        "summary": "Number of solid layers at the bottom of the model.",
        "when_to_change": "Increase to 5-6 for load-bearing bases or watertight containers.",
        "tradeoffs": "Minimal time impact.",
    },
    "sparse_infill_density": {
        "gui_tab": "Strength -> Sparse infill",
        "gui_label": "Sparse infill density",
        "type": "percent string (e.g. '15%')",
        "default_04_nozzle": "15%",
        "recommended_range": "10% - 40%",
        "summary": "Percentage of internal volume filled with support lattice structure.",
        "when_to_change": "10-15% for visual models, 20-25% for functional parts, 35-50% for high-compression load parts. Rarely needed above 50% (increase wall_loops instead!).",
        "tradeoffs": "High infill (>50%) wastes filament and time with diminishing strength gains compared to adding wall_loops.",
    },
    "sparse_infill_pattern": {
        "gui_tab": "Strength -> Sparse infill",
        "gui_label": "Sparse infill pattern",
        "type": "enum",
        "options": [
            "grid", "gyroid", "honeycomb", "3dhoneycomb", "adaptivecubic",
            "cubic", "triangles", "rectilinear", "lightning", "alignedrectilinear",
            "crosshatch",
        ],
        "default_04_nozzle": "grid",
        "summary": "Geometry of the internal infill structure. **IMPORTANT: Bambu's default 'grid' crosses over itself on the same layer, causing nozzle scraping noises and knocked-over prints!**",
        "when_to_change": "Switch to 'gyroid' or 'crosshatch' (never crosses itself on the same layer, isotropic strength), 'adaptivecubic' (fast + strong, saves filament), or 'lightning' (for hollow decorative statues/busts).",
        "tradeoffs": "'gyroid' causes slight printer vibration at very high speeds; 'crosshatch' or 'adaptivecubic' is smoother and faster.",
    },

    # --- SPEED TAB ---
    "outer_wall_speed": {
        "gui_tab": "Speed -> Other layers speed",
        "gui_label": "Outer wall",
        "type": "float (mm/s)",
        "default_04_nozzle": "200",
        "recommended_range": "60 - 200 mm/s",
        "summary": "Print speed of the visible exterior perimeter wall.",
        "when_to_change": "Drop to 60-100 mm/s for uniform glossy sheen on Silk PLA/PETG, fine miniatures, or eliminating ghosting/ringing.",
        "tradeoffs": "Directly affects total print time on models with lots of surface area.",
    },
    "initial_layer_speed": {
        "gui_tab": "Speed -> First layer speed",
        "gui_label": "Initial layer",
        "type": "float (mm/s)",
        "default_04_nozzle": "50",
        "recommended_range": "25 - 50 mm/s",
        "summary": "Speed of the first layer on the build plate.",
        "when_to_change": "Drop to 25-30 mm/s when printing small details, text on the first layer, or sticky/tricky filaments like PETG and TPU.",
        "tradeoffs": "Only affects the first layer (adds <1-2 minutes).",
    },
    "bridge_speed": {
        "gui_tab": "Speed -> Other layers speed",
        "gui_label": "Bridge",
        "type": "float (mm/s)",
        "default_04_nozzle": "50",
        "recommended_range": "25 - 50 mm/s",
        "summary": "Print speed for horizontal mid-air bridges spanning between two pillars.",
        "when_to_change": "Drop to 25-35 mm/s (paired with 100% part cooling fan and bridge_flow 0.90-0.95) so extruded strands freeze mid-air without sagging or snapping.",
        "tradeoffs": "Minimal impact on total print time since only bridge regions slow down.",
    },
    "overhang_1_4_speed": {
        "gui_tab": "Speed -> Overhang speed",
        "gui_label": "Overhang speed (10% - 25% overhang)",
        "type": "float (mm/s) or percent",
        "default_04_nozzle": "0",
        "recommended_range": "60 - 100 mm/s (0 = no slowdown)",
        "summary": "Speed for mild overhangs where 10%-25% of the extruded line width hangs over air.",
        "when_to_change": "Usually left at 0 (outer wall speed) or set to 80-100 mm/s for consistent sheen transitions.",
        "tradeoffs": "Sudden speed drops on mild slopes can create horizontal gloss/matte bands on Silk PLA or PETG.",
    },
    "overhang_2_4_speed": {
        "gui_tab": "Speed -> Overhang speed",
        "gui_label": "Overhang speed (25% - 50% overhang)",
        "type": "float (mm/s) or percent",
        "default_04_nozzle": "50",
        "recommended_range": "30 - 60 mm/s",
        "summary": "Speed for moderate overhangs (~45 deg) where 25%-50% of the line width is unsupported.",
        "when_to_change": "Drop to 35-45 mm/s if 45-degree chamfers or overhangs curl upward at corners.",
        "tradeoffs": "Slightly slows down sloped perimeters.",
    },
    "overhang_3_4_speed": {
        "gui_tab": "Speed -> Overhang speed",
        "gui_label": "Overhang speed (50% - 75% overhang)",
        "type": "float (mm/s) or percent",
        "default_04_nozzle": "30",
        "recommended_range": "15 - 35 mm/s",
        "summary": "Speed for steep overhangs (~60 deg from vertical) where 50%-75% of the line width hangs in air.",
        "when_to_change": "Drop to 15-25 mm/s to give the part cooling fan maximum time to solidify steep unsupported curves.",
        "tradeoffs": "Printing too slowly with high nozzle temp can occasionally radiate heat into thin overhangs if fan speed is low.",
    },
    "overhang_4_4_speed": {
        "gui_tab": "Speed -> Overhang speed",
        "gui_label": "Overhang speed (75% - 100% overhang / bridge perimeter)",
        "type": "float (mm/s) or percent",
        "default_04_nozzle": "10",
        "recommended_range": "10 - 20 mm/s",
        "summary": "Speed for extreme overhangs (>70 deg from vertical) and curved perimeter bridges.",
        "when_to_change": "Keep at 10-15 mm/s so extreme overhangs and support interfaces anchor cleanly without curling.",
        "tradeoffs": "Only affects extreme overhang perimeters.",
    },
    "slow_down_for_layer_cooling": {
        "gui_tab": "Filament Settings -> Cooling",
        "gui_label": "Slow printing down for better layer cooling",
        "type": "bool string ('0' or '1')",
        "default_04_nozzle": "1",
        "summary": "Automatically reduces print speed on small layers (spires, chimneys, miniature heads) so each layer has at least 'Max fan speed threshold' seconds to solidify before the next layer is deposited.",
        "when_to_change": "Keep enabled ('1') for miniatures, benchy smokestacks, and thin pins. Disable ('0') ONLY if speed variations cause gloss/matte banding on uniform cylinders and part cooling is already sufficient.",
        "tradeoffs": "Can noticeably change surface gloss on layers where the cross-section narrows suddenly.",
    },
    "min_print_speed": {
        "gui_tab": "Filament Settings -> Cooling",
        "gui_label": "Min print speed",
        "type": "float (mm/s)",
        "default_04_nozzle": "20",
        "recommended_range": "10 - 30 mm/s",
        "summary": "Floor speed limit when 'slow_down_for_layer_cooling' throttles small-layer printing.",
        "when_to_change": "Lower to 10-15 mm/s for tiny spire tips, or raise to 25-30 mm/s if the hot nozzle lingering on a tiny tip melts the plastic into a blob.",
        "tradeoffs": "Too low (<10 mm/s) keeps the radiant hotend block parked over the tiny feature, softening it.",
    },

    # --- SUPPORT TAB ---
    "enable_support": {
        "gui_tab": "Support -> Support",
        "gui_label": "Enable support",
        "type": "bool string ('0' or '1')",
        "default_04_nozzle": "0",
        "summary": "Generates removable scaffolding under steep overhangs (>threshold angle) and mid-air bridges.",
        "when_to_change": "Set to '1' whenever your model has overhangs steeper than ~50 degrees from vertical or floating islands.",
        "tradeoffs": "Uses extra filament/time and leaves slight witness marks where support touches the model.",
    },
    "support_type": {
        "gui_tab": "Support -> Support",
        "gui_label": "Type",
        "type": "enum",
        "options": ["normal(auto)", "tree(auto)", "normal(manual)", "tree(manual)"],
        "default_04_nozzle": "normal(auto)",
        "summary": "Style of support structures. 'tree(auto)' grows organic branches from the build plate around the model; 'normal(auto)' builds vertical columns.",
        "when_to_change": "Use 'tree(auto)' for figurines, organic shapes, and avoiding support scars on the lower part of the model. Use 'normal(auto)' (with 'snug' style) for flat horizontal cantilevers and geometric ledges.",
        "tradeoffs": "Tree supports are easier to snap off in one piece and use less filament.",
    },
    "support_on_build_plate_only": {
        "gui_tab": "Support -> Support",
        "gui_label": "On build plate only",
        "type": "bool string ('0' or '1')",
        "default_04_nozzle": "0",
        "summary": "Forces supports to grow only from the build plate and prevents supports from sitting on top of your printed model's surfaces.",
        "when_to_change": "Enable ('1') alongside 'tree(auto)' so tree branches reach around the part without marring the bottom surface of internal cavities.",
        "tradeoffs": "Some internal closed roofs may not be reachable from the build plate.",
    },
    "support_top_z_distance": {
        "gui_tab": "Support -> Advanced",
        "gui_label": "Top Z distance",
        "type": "float (mm)",
        "default_04_nozzle": "0.2",
        "recommended_range": "0.16 - 0.28 mm (or 0.0mm only with dedicated support interface material)",
        "summary": "Vertical air gap between the top of the support interface and the bottom of the supported model layer.",
        "when_to_change": "Increase to 0.24-0.28mm (especially with PETG!) if supports fuse to the part and are hard to remove. Set to 0.0mm ONLY when using PLA as support interface for PETG (or vice versa) with AMS.",
        "tradeoffs": "Larger Z distance makes supports peel off effortlessly, at the cost of slightly looser underside lines.",
    },
    "support_threshold_angle": {
        "gui_tab": "Support -> Support",
        "gui_label": "Threshold angle",
        "type": "int (degrees)",
        "default_04_nozzle": "30",
        "recommended_range": "25 - 45 degrees",
        "summary": "Overhang angle (measured from horizontal in Bambu Studio) below which supports are generated.",
        "when_to_change": "Bambu printers have strong part cooling and easily print 25-30 deg from horizontal without support. Raise to 35-40 deg if steep overhangs curl.",
        "tradeoffs": "Higher angle generates more supports.",
    },
    "support_filament": {
        "gui_tab": "Support -> Filament for Supports",
        "gui_label": "Support/raft base",
        "type": "int (AMS slot index, 0 = default)",
        "default_04_nozzle": "0",
        "summary": "Selects which AMS filament slot builds the main structural body of supports and rafts.",
        "when_to_change": "Keep at '0' (Default = same filament as model) even when using dedicated support material! Only change support_interface_filament so you don't waste expensive support filament and hundreds of AMS swaps on the entire support tower.",
        "tradeoffs": "Setting base support to a different filament forces an AMS swap on every single layer from the bed up.",
    },
    "support_interface_filament": {
        "gui_tab": "Support -> Filament for Supports",
        "gui_label": "Support/raft interface",
        "type": "int (AMS slot index, 0 = default)",
        "default_04_nozzle": "0",
        "summary": "Selects a dedicated AMS filament slot (such as PETG interface for PLA prints, PLA interface for PETG prints, or Bambu Support for PLA/PA) for the top 2-3 roof layers touching the part.",
        "when_to_change": "Assign to your AMS slot loaded with breakaway interface material, then set support_top_z_distance = 0.0mm and support_interface_spacing = 0.0mm for injection-molded-smooth supported undersides that peel off with zero force.",
        "tradeoffs": "Adds 2-3 AMS filament swaps at the height of each supported overhang ledge; requires adequate flush volume (~400-600mm³) when swapping between PLA and PETG so interlayer strength isn't contaminated.",
    },

    # --- OTHERS TAB (ADHESION / MULTI-COLOR / SPECIAL) ---
    "fuzzy_skin": {
        "gui_tab": "Others -> Special mode",
        "gui_label": "Fuzzy skin",
        "type": "enum",
        "options": ["none", "external", "all", "allwalls"],
        "default_04_nozzle": "none",
        "summary": "Oscillates the nozzle randomly in X/Y along perimeter walls to create a uniform matte, pebble-textured grip finish that completely hides layer lines.",
        "when_to_change": "Set to 'external' (Contour) for tool handles, camera grips, planters, and enclosures where an injection-molded VDI-style matte texture is desired without affecting internal hole clearances.",
        "tradeoffs": "Increases outer wall print time by ~15-25%; never use 'all' on mating holes or threads.",
    },
    "fuzzy_skin_point_distance": {
        "gui_tab": "Others -> Special mode",
        "gui_label": "Fuzzy skin point distance",
        "type": "float (mm)",
        "default_04_nozzle": "0.8",
        "recommended_range": "0.3 - 0.8 mm",
        "summary": "Average distance along the perimeter between random oscillation points for Fuzzy Skin.",
        "when_to_change": "Decrease to 0.3-0.4mm (paired with fuzzy_skin_thickness = 0.15-0.20mm) for a fine sandpaper/Powder-coat texture; keep at 0.6-0.8mm for a coarser knurled stone look.",
        "tradeoffs": "Smaller point distance generates many more tiny G-code segments (use Arachne or simplify mesh if buffer stutters).",
    },
    "fuzzy_skin_thickness": {
        "gui_tab": "Others -> Special mode",
        "gui_label": "Fuzzy skin thickness",
        "type": "float (mm)",
        "default_04_nozzle": "0.3",
        "recommended_range": "0.10 - 0.30 mm",
        "summary": "Maximum peak-to-valley amplitude of the random X/Y wall jitter in Fuzzy Skin mode.",
        "when_to_change": "0.15mm gives a subtle matte consumer-electronics texture; 0.25-0.30mm gives a heavy tactile grip.",
        "tradeoffs": "Adds roughly fuzzy_skin_thickness to the effective outer width of the part.",
    },
    "brim_type": {
        "gui_tab": "Others -> Bed adhesion",
        "gui_label": "Brim type",
        "type": "enum",
        "options": ["auto_brim", "no_brim", "outer_only", "inner_only", "outer_and_inner", "painted"],
        "default_04_nozzle": "auto_brim",
        "summary": "Prints flat single-layer rings attached to the base of the model to hold corners down and prevent warping or knocking over.",
        "when_to_change": "Set to 'outer_only' (5-8mm width) for tall/thin parts, sharp corners, or warping-prone materials (ABS/ASA/PA/PC). Set to 'no_brim' for wide flat PLA parts where you want clean bottom edges.",
        "tradeoffs": "Requires peeling/deburring the brim off the bottom edge after printing.",
    },
    "brim_width": {
        "gui_tab": "Others -> Bed adhesion",
        "gui_label": "Brim width",
        "type": "float (mm)",
        "default_04_nozzle": "5",
        "recommended_range": "3 - 10 mm",
        "summary": "Width of the bed-adhesion brim ring around the first layer.",
        "when_to_change": "5-8mm for tall parts or ABS/ASA.",
        "tradeoffs": "Reduces usable X/Y build plate footprint slightly.",
    },
    "brim_object_gap": {
        "gui_tab": "Others -> Bed adhesion",
        "gui_label": "Brim-object gap",
        "type": "float (mm)",
        "default_04_nozzle": "0.1",
        "recommended_range": "0.0 - 0.15 mm",
        "summary": "Tiny gap between the brim and the part's first layer wall.",
        "when_to_change": "0.10-0.12mm makes the brim peel off cleanly by hand without a deburring knife; 0.0mm gives maximum anti-warping grip for ABS/ASA.",
        "tradeoffs": "0.0mm requires a deburring tool to clean up.",
    },
    "draft_shield": {
        "gui_tab": "Others -> Bed adhesion",
        "gui_label": "Draft shield",
        "type": "enum or bool ('0'/'1' or 'disabled'/'enabled')",
        "default_04_nozzle": "0",
        "summary": "Builds a thin single-wall skirt wall all the way up around the model to trap rising warm air from the bed and block room air drafts.",
        "when_to_change": "Enable when printing warping-prone filaments (ABS, ASA, Nylon) on open-frame printers (A1 / A1 mini / P1P) without an enclosure.",
        "tradeoffs": "Consumes extra filament and print time for the sacrificial perimeter shield.",
    },
    "enable_prime_tower": {
        "gui_tab": "Others -> Prime tower",
        "gui_label": "Enable prime tower",
        "type": "bool string ('0' or '1')",
        "default_04_nozzle": "1",
        "summary": "Prints a small auxiliary tower on the build plate during multi-color / multi-material prints to stabilize nozzle pressure and wipe ooze after each AMS filament swap.",
        "when_to_change": "Keep enabled ('1') for all multi-color prints and smooth timelapses so the nozzle restarts on the model with crisp pressure and zero blobs.",
        "tradeoffs": "Takes up a small rectangle on the build plate and uses a modest amount of filament.",
    },
    "prime_tower_width": {
        "gui_tab": "Others -> Prime tower",
        "gui_label": "Tower width",
        "type": "float (mm)",
        "default_04_nozzle": "35",
        "recommended_range": "15 - 45 mm",
        "summary": "X-dimension width of the multi-color prime tower.",
        "when_to_change": "Reduce to 15-25mm (paired with prime_tower_minimal_volume = 15-25mm³) when plate space is tight or to save filament on tall prints.",
        "tradeoffs": "Very narrow tall prime towers (<15mm) can wobble unless prime_tower_brim_width is increased.",
    },
    "prime_tower_brim_width": {
        "gui_tab": "Others -> Prime tower",
        "gui_label": "Brim width (Prime tower)",
        "type": "float (mm)",
        "default_04_nozzle": "3",
        "recommended_range": "3 - 8 mm",
        "summary": "Width of the stabilizing first-layer brim specifically around the prime tower.",
        "when_to_change": "Increase to 5-8mm on tall multi-color prints or when mixing incompatible materials (PLA + PETG support interface) so the prime tower never detaches mid-print.",
        "tradeoffs": "Slightly increases the footprint around the prime tower base.",
    },
    "flush_into_infill": {
        "gui_tab": "Others -> Flush options",
        "gui_label": "Flush into objects' infill",
        "type": "bool string ('0' or '1')",
        "default_04_nozzle": "0",
        "summary": "During AMS multi-color changes, purges old filament color inside the internal infill of the part instead of ejecting waste ('poop').",
        "when_to_change": "Enable ('1') on opaque multi-color models to reduce filament waste and purge time. Do NOT enable if purging dark black into thin white walls (can bleed through visually).",
        "tradeoffs": "Dark internal infill can show through thin translucent/white shells if wall_loops < 3.",
    },
    "flush_multiplier": {
        "gui_tab": "Prepare Tab -> Flushing Volumes",
        "gui_label": "Multiplier (Flushing Volumes)",
        "type": "float",
        "default_04_nozzle": "1.0",
        "recommended_range": "0.5 - 1.0",
        "summary": "Global multiplier scaling all color-to-color AMS purge volumes in the flushing matrix.",
        "when_to_change": "Drop to 0.6 - 0.7 for standard multi-color PLA prints to cut AMS 'poop' waste by 30-40% without color bleed; raise to 1.2+ when swapping between incompatible materials (PLA <-> PETG).",
        "tradeoffs": "Too low (<0.5) when transitioning from dark (black/red) to light (white/yellow) can leave pastel color tinting.",
    },
    "flush_volumes_matrix": {
        "gui_tab": "Prepare Tab -> Flushing Volumes",
        "gui_label": "Flushing Volumes Matrix (mm³)",
        "type": "list of floats (N x N matrix flattened)",
        "default_04_nozzle": "auto-calculated per color pair",
        "recommended_range": "100 - 800 mm³ per swap",
        "summary": "Exact volume of filament (in mm³) purged down the waste chute for every From-Slot -> To-Slot transition in the AMS.",
        "when_to_change": "Use ~120-180 mm³ for light-to-dark transitions (White -> Black), ~350-500 mm³ for dark-to-light transitions (Black -> White), and 500-700 mm³ for PLA <-> PETG support swaps to eliminate cross-contamination.",
        "tradeoffs": "Directly governs total multi-color filament waste ('poop' weight) and swap duration.",
    },
    "spiral_mode": {
        "gui_tab": "Others -> Special mode",
        "gui_label": "Spiral vase",
        "type": "bool string ('0' or '1')",
        "default_04_nozzle": "0",
        "summary": "Prints a single continuous outer wall spiraling smoothly upward with zero Z-seam, zero infill, and zero top layers.",
        "when_to_change": "Enable for vases, lampshades, cups, and trash bins. Pair with line_width = 0.6-0.8mm for sturdy single-wall vases!",
        "tradeoffs": "Only works for single continuous shells without flat horizontal ledges.",
    },
    "print_sequence": {
        "gui_tab": "Others -> Special mode",
        "gui_label": "Print sequence",
        "type": "enum",
        "options": ["by layer", "by object"],
        "default_04_nozzle": "by layer",
        "summary": "'by object' finishes one entire object on the plate before moving to the next.",
        "when_to_change": "Use 'by object' when printing multiple small parts in different colors (reduces AMS color swaps from hundreds to just 1 per color!) or when reducing stringing between parts.",
        "tradeoffs": "Requires extra spacing between objects on the plate so the printhead doesn't collide with finished parts.",
    },
    "timelapse_type": {
        "gui_tab": "Others -> Special mode",
        "gui_label": "Timelapse",
        "type": "enum",
        "options": ["traditional", "smooth"],
        "default_04_nozzle": "traditional",
        "summary": "Controls how the built-in chamber camera captures layer-by-layer timelapse video. 'Traditional' snaps a frame while printing; 'Smooth' parks the toolhead over the purge chute before each frame so the part appears to grow by magic.",
        "when_to_change": "Use 'traditional' for zero print defects and zero extra time. Switch to 'smooth' only for showcase social-media videos (automatically enables a prime tower to catch nozzle ooze while the head parks).",
        "tradeoffs": "'Smooth' timelapse adds travel time on every layer and requires a prime tower so nozzle ooze during camera parking doesn't leave strings on the model.",
    },
}


# ---------------------------------------------------------------------------
# 2. INTENT-BASED SMART SLICING ADVISOR RECIPES
# ---------------------------------------------------------------------------
INTENT_RECIPES: Dict[str, Dict[str, Any]] = {
    "strong_functional": {
        "title": "Strong Functional / Mechanical Part",
        "keywords": ["strong", "strength", "functional", "bracket", "mechanical", "load", "heavy duty", "gear", "mount", "hook"],
        "description": "Maximizes structural strength, impact resistance, and inter-layer bonding without wasting filament on excessive infill.",
        "overrides": {
            "wall_loops": "4",
            "top_shell_layers": "5",
            "bottom_shell_layers": "5",
            "sparse_infill_density": "25%",
            "sparse_infill_pattern": "gyroid",
            "line_width": "0.45",
            "inner_wall_line_width": "0.48",
            "sparse_infill_line_width": "0.50",
            "outer_wall_speed": "120",
        },
        "why_it_works": [
            "4 wall loops (with 0.48mm inner wall width) create a ~1.9mm thick solid outer shell where bending and tensile stresses are highest.",
            "Gyroid infill at 25% provides isotropic 3D strength and never crosses over itself on the same layer (eliminating nozzle collisions).",
            "Slightly reduced outer wall speed (120 mm/s) improves thermal bonding between layers.",
        ],
    },
    "high_detail_miniature": {
        "title": "High-Detail Miniature / Figurine / Statue",
        "keywords": ["miniature", "detail", "fine", "figurine", "statue", "model", "smooth", "sculpture", "character"],
        "description": "Maximizes fine surface detail, clean overhangs, and easy-to-remove organic tree supports.",
        "overrides": {
            "layer_height": "0.08",
            "initial_layer_print_height": "0.20",
            "wall_generator": "arachne",
            "wall_loops": "3",
            "top_shell_layers": "7",
            "sparse_infill_density": "12%",
            "sparse_infill_pattern": "gyroid",
            "outer_wall_speed": "70",
            "enable_support": "1",
            "support_type": "tree(auto)",
            "support_on_build_plate_only": "1",
            "support_top_z_distance": "0.20",
            "seam_position": "back",
        },
        "why_it_works": [
            "0.08mm layer height makes layer lines nearly invisible on curved surfaces while keeping a 0.20mm first layer for reliable bed adhesion.",
            "Arachne wall generator preserves tiny fingers, weapons, and embossed details.",
            "Tree supports on build plate only reach around the miniature without scarring the body, and 70 mm/s outer wall speed prevents ringing.",
        ],
    },
    "fast_draft_prototype": {
        "title": "Fast Draft / Rapid Fit-Check Prototype",
        "keywords": ["fast", "draft", "quick", "prototype", "speed", "test fit", "rapid"],
        "description": "Cuts print time by 35-50% for quick dimensional and form-factor checks.",
        "overrides": {
            "layer_height": "0.28",
            "initial_layer_print_height": "0.24",
            "wall_loops": "2",
            "top_shell_layers": "3",
            "bottom_shell_layers": "3",
            "sparse_infill_density": "10%",
            "sparse_infill_pattern": "adaptivecubic",
            "sparse_infill_line_width": "0.55",
        },
        "why_it_works": [
            "0.28mm layer height prints 40% fewer layers than standard 0.20mm.",
            "Adaptive cubic infill at 10% uses dense infill only near top surfaces and stays sparse in the center.",
        ],
    },
    "dimensional_precision_fit": {
        "title": "Dimensionally Accurate / Tight Clearance / Print-in-Place",
        "keywords": ["accurate", "precision", "tolerance", "clearance", "fit", "hole", "screw", "bearing", "print in place", "hinge", "thread"],
        "description": "Tuned for parts that must mate together, accept screws/bearings, or move freely as print-in-place assemblies.",
        "overrides": {
            "layer_height": "0.16",
            "wall_generator": "arachne",
            "wall_sequence": "inner/outer/inner",
            "elefant_foot_compensation": "0.20",
            "xy_hole_compensation": "0.08",
            "seam_position": "aligned",
            "outer_wall_speed": "100",
            "sparse_infill_pattern": "crosshatch",
        },
        "why_it_works": [
            "'inner/outer/inner' wall order prevents inner wall squish from pushing the outer wall outward.",
            "0.20mm elephant foot compensation stops the first layer from fusing print-in-place hinges or blocking peg insertion.",
            "+0.08mm X-Y hole compensation counteracts polygon shrinkage on vertical screw/pin holes.",
        ],
    },
    "easy_support_removal": {
        "title": "Easy-Peel Supports / Minimal Support Scarring",
        "keywords": ["support", "easy remove", "peel", "overhang", "scar", "stuck support"],
        "description": "Prevents supports from fusing to the model while maintaining clean underside bridges.",
        "overrides": {
            "enable_support": "1",
            "support_type": "tree(auto)",
            "support_on_build_plate_only": "1",
            "support_top_z_distance": "0.24",
            "support_bottom_z_distance": "0.24",
            "support_interface_top_layers": "3",
            "support_interface_spacing": "0.25",
        },
        "why_it_works": [
            "3 dense support interface roof layers create a smooth cushion that peels away as a single ribbon instead of individual strings.",
            "0.24mm top Z distance gives a clean release (especially helpful for PETG or tough PLA).",
        ],
    },
    "watertight_enclosure": {
        "title": "Watertight / Airtight Container, Planter, or Float",
        "keywords": ["watertight", "waterproof", "airtight", "planter", "cup", "bowl", "container", "float", "leak"],
        "description": "Eliminates micro-pinholes at layer seams and floor-to-wall transitions.",
        "overrides": {
            "layer_height": "0.16",
            "wall_loops": "4",
            "top_shell_layers": "6",
            "bottom_shell_layers": "6",
            "line_width": "0.46",
            "seam_position": "aligned",
            "scarf_angle_threshold": "155",
            "sparse_infill_density": "20%",
            "sparse_infill_pattern": "gyroid",
            "outer_wall_speed": "100",
        },
        "why_it_works": [
            "4 overlapping walls at 0.46mm line width + 6 bottom layers block capillary water paths between extrusions.",
            "Lower 0.16mm layer height increases extrusion width-to-height ratio, pressing layers together tightly.",
        ],
    },
    "anti_warping_adhesion": {
        "title": "Maximum Bed Adhesion / Anti-Warping (Large Flat or Tall Parts)",
        "keywords": ["warp", "warping", "lifting", "corner", "adhesion", "stick", "tall", "knocked over", "abs", "asa"],
        "description": "Stops corners from curling off the build plate and prevents tall parts from getting knocked loose.",
        "overrides": {
            "initial_layer_print_height": "0.24",
            "initial_layer_line_width": "0.52",
            "initial_layer_speed": "30",
            "brim_type": "outer_only",
            "brim_width": "7",
            "brim_object_gap": "0.08",
            "sparse_infill_pattern": "gyroid",
        },
        "why_it_works": [
            "Slow (30 mm/s), wide (0.52mm) first layer presses molten plastic deep into PEI texture.",
            "7mm outer brim anchors sharp corners against thermal contraction forces.",
            "Switching from 'grid' to 'gyroid' infill stops the nozzle from hitting crossed infill intersections on tall parts.",
        ],
    },
    "multicolor_low_waste": {
        "title": "AMS Multi-Color Low Poop / Low Waste Optimization",
        "keywords": ["multicolor", "multi-color", "ams", "waste", "poop", "flush", "purge", "color"],
        "description": "Dramatically reduces filament purge waste and swap time on AMS multi-color prints.",
        "overrides": {
            "flush_into_infill": "1",
            "flush_into_support": "1",
            "wall_loops": "3",
            "sparse_infill_density": "15%",
            "sparse_infill_pattern": "gyroid",
        },
        "why_it_works": [
            "Flushes color transitions into the hidden internal infill and support structures instead of the purge chute.",
            "3 wall loops prevent dark infill purges from shadowing through lighter outer walls.",
        ],
    },
}


# ---------------------------------------------------------------------------
# 3. PRINT DEFECT & TROUBLESHOOTING GUIDE
# ---------------------------------------------------------------------------
TROUBLESHOOTING_GUIDE: Dict[str, Dict[str, Any]] = {
    "nozzle_scraping_or_knocked_print": {
        "symptom": "Nozzle makes loud scraping/grinding sounds over the print or knocks the model off the bed mid-print.",
        "root_causes": [
            "Bambu Studio's default 'Grid' infill crosses over already-printed lines on the same layer, building up double-height bumps.",
            "Overhangs curling upward into the nozzle path due to insufficient cooling or printing too fast.",
            "Insufficient first-layer contact area on tall/narrow parts.",
        ],
        "recommended_overrides": {
            "sparse_infill_pattern": "gyroid",
            "brim_type": "outer_only",
            "brim_width": "6",
        },
        "additional_tips": [
            "Always change Sparse Infill Pattern from 'Grid' to 'Gyroid' or 'Crosshatch'.",
            "Disable 'Reduce infill retraction' under the Others tab so the nozzle Z-hops cleanly during travel moves.",
        ],
    },
    "warping_corners_lifting": {
        "symptom": "Bottom corners lift up off the build plate, causing a curved bottom and squished upper layers.",
        "root_causes": [
            "Thermal contraction of upper layers pulling corners upward.",
            "Finger oils on the PEI plate (dish soap + warm water is needed; IPA alone spreads oils).",
            "Auxiliary part cooling fan blowing too hard across the bed on large flat PLA/PETG prints.",
        ],
        "recommended_overrides": {
            "brim_type": "outer_only",
            "brim_width": "8",
            "brim_object_gap": "0.05",
            "initial_layer_speed": "30",
            "initial_layer_line_width": "0.50",
            "sparse_infill_pattern": "gyroid",
        },
        "additional_tips": [
            "Wash the PEI plate with Dawn dish soap and warm water.",
            "For large flat PLA prints on enclosed printers (X1C/P1S), turn OFF the Auxiliary Part Cooling Fan in the Filament -> Cooling tab (it blows from the left side and warps large flat parts!).",
            "Raise bed temperature by +5 C (e.g. 60 C for PLA on Textured PEI, 70-75 C for PETG).",
        ],
    },
    "stringing_and_wisps": {
        "symptom": "Fine cobweb hairs or plastic strings between separate pillars or branches.",
        "root_causes": [
            "Moisture absorbed by the filament (especially PETG, TPU, PA, and Silk PLA).",
            "Nozzle temperature slightly too high.",
            "'Spiral Z hop' leaving tiny wisps on wet filament.",
        ],
        "recommended_overrides": {
            "outer_wall_speed": "120",
        },
        "additional_tips": [
            "Dry the filament spool (50-55 C for PLA, 65 C for PETG/TPU for 6-8 hours).",
            "Lower nozzle temperature by 5-10 C in the Filament profile.",
            "In Filament Settings -> Setting Overrides, change Z hop type from 'Auto'/'Spiral' to 'Normal'.",
        ],
    },
    "supports_fused_to_model": {
        "symptom": "Supports are welded to the part, require pliers to rip off, and leave rough scarred undersides.",
        "root_causes": [
            "Top Z distance is too tight (especially with PETG which has high self-adhesion).",
            "Normal supports placed on detailed surfaces instead of Tree supports.",
        ],
        "recommended_overrides": {
            "support_type": "tree(auto)",
            "support_on_build_plate_only": "1",
            "support_top_z_distance": "0.24",
            "support_interface_top_layers": "3",
            "support_interface_spacing": "0.25",
        },
        "additional_tips": [
            "If you have an AMS, use PLA as the 'Support/raft interface' filament for a PETG print (or PETG interface for a PLA print) with Top Z distance = 0mm — they don't stick to each other and leave a glass-smooth underside!",
        ],
    },
    "holes_or_pegs_too_tight": {
        "symptom": "Screws, bearings, pins, or mating tabs won't fit without drilling or sanding.",
        "root_causes": [
            "First layer squish ('elephant foot') narrows the bottom of holes.",
            "Circular holes approximated as polygons pull slightly inward while molten.",
            "Inner walls printed before outer walls push the outer perimeter outward slightly.",
        ],
        "recommended_overrides": {
            "wall_sequence": "inner/outer/inner",
            "elefant_foot_compensation": "0.20",
            "xy_hole_compensation": "0.10",
            "xy_contour_compensation": "-0.04",
            "outer_wall_speed": "100",
        },
        "additional_tips": [
            "Increase xy_hole_compensation in 0.05mm increments until pins slide in with your desired fit.",
        ],
    },
    "pillowing_or_gaps_on_top_surface": {
        "symptom": "Bumps, holes, or visible infill grid lines showing through flat top surfaces.",
        "root_causes": [
            "Too few top shell layers bridging over low-density infill.",
            "Layer height was lowered (e.g. to 0.08mm) without increasing the number of top shell layers.",
        ],
        "recommended_overrides": {
            "top_shell_layers": "6",
            "sparse_infill_density": "18%",
            "sparse_infill_pattern": "gyroid",
            "ironing_type": "top surfaces",
        },
        "additional_tips": [
            "Ensure total Top Shell Thickness is at least 0.8mm to 1.0mm.",
        ],
    },
}


def explain_setting(query: str) -> Dict[str, Any]:
    """Search the Bambu Studio settings encyclopedia by key, GUI label, or keyword."""
    q = query.strip().lower()
    exact_matches = []
    partial_matches = []

    for key, info in SETTINGS_ENCYCLOPEDIA.items():
        key_clean = key.strip().lower()
        label_clean = info.get("gui_label", "").lower()
        tab_clean = info.get("gui_tab", "").lower()
        summary_clean = info.get("summary", "").lower()

        entry = {"key": key.strip(), **info}
        if q == key_clean or q == label_clean:
            exact_matches.append(entry)
        elif q in key_clean or q in label_clean or q in tab_clean or q in summary_clean:
            partial_matches.append(entry)

    results = exact_matches + partial_matches
    if not results:
        return {
            "query": query,
            "match_count": 0,
            "message": "No direct match in core encyclopedia. Try searching a broader term (e.g., 'infill', 'support', 'wall', 'seam', 'brim', 'hole', 'layer') or list all keys.",
            "available_keys": [k.strip() for k in SETTINGS_ENCYCLOPEDIA.keys()],
        }

    return {
        "query": query,
        "match_count": len(results),
        "settings": results,
    }


def recommend_print_settings(
    goal: str,
    filament_type: str = "PLA",
    nozzle_size_mm: float = 0.4,
    has_overhangs: Optional[bool] = None,
) -> Dict[str, Any]:
    """Recommend Bambu Studio settings overrides and GUI steps for a plain-English goal."""
    goal_lower = goal.lower()
    matched_recipes: List[Dict[str, Any]] = []

    for recipe_id, recipe in INTENT_RECIPES.items():
        score = sum(1 for kw in recipe["keywords"] if kw in goal_lower)
        if recipe_id in goal_lower:
            score += 3
        if score > 0:
            matched_recipes.append({"id": recipe_id, "score": score, **recipe})

    matched_recipes.sort(key=lambda r: r["score"], reverse=True)

    # Default balanced base if no specific keyword hit
    combined_overrides: Dict[str, str] = {
        "sparse_infill_pattern": "gyroid",
    }
    explanations: List[str] = []
    matched_titles: List[str] = []

    if matched_recipes:
        # Merge top matching recipes (primary recipe wins on conflicts)
        for rec in reversed(matched_recipes[:2]):
            combined_overrides.update(rec["overrides"])
        for rec in matched_recipes[:2]:
            matched_titles.append(rec["title"])
            explanations.extend(rec["why_it_works"])
    else:
        combined_overrides.update({
            "layer_height": "0.20",
            "wall_loops": "3",
            "sparse_infill_density": "15%",
            "sparse_infill_pattern": "gyroid",
        })
        matched_titles.append("Balanced Everyday Quality & Strength")
        explanations.append(
            "3 wall loops + 15% Gyroid infill provides a much stronger, scrape-free print than Bambu Studio's stock 2-wall Grid default."
        )

    # Scale layer height & line width if nozzle size != 0.4mm
    if abs(nozzle_size_mm - 0.4) > 0.01:
        scale = nozzle_size_mm / 0.4
        if "layer_height" in combined_overrides:
            lh = float(combined_overrides["layer_height"]) * scale
            lh = max(round(nozzle_size_mm * 0.20, 2), min(round(nozzle_size_mm * 0.70, 2), round(lh, 2)))
            combined_overrides["layer_height"] = f"{lh:.2f}"
        combined_overrides["line_width"] = f"{round(nozzle_size_mm * 1.05, 2):.2f}"
        explanations.append(
            f"Scaled layer height and line width proportionally for your {nozzle_size_mm}mm nozzle."
        )

    # Filament-specific adjustments
    fil_upper = filament_type.upper()
    filament_notes: List[str] = []
    if "PETG" in fil_upper:
        if combined_overrides.get("enable_support") == "1":
            combined_overrides["support_top_z_distance"] = "0.25"
        combined_overrides["outer_wall_speed"] = str(
            min(int(combined_overrides.get("outer_wall_speed", "120")), 120)
        )
        filament_notes.append(
            "PETG Tip: Increased support_top_z_distance to 0.25mm so PETG supports don't weld to the model, and capped outer wall speed at 120 mm/s for glossy finish and strong layer bonding."
        )
    elif any(k in fil_upper for k in ("ABS", "ASA", "PC", "PA", "NYLON")):
        combined_overrides["brim_type"] = "outer_only"
        combined_overrides["brim_width"] = "8"
        combined_overrides["brim_object_gap"] = "0.0"
        filament_notes.append(
            f"{filament_type} Tip: Enabled an 8mm zero-gap outer brim to prevent high-temp thermal warping. Preheat chamber for 10-15 minutes before starting."
        )
    elif "TPU" in fil_upper:
        combined_overrides["outer_wall_speed"] = "60"
        combined_overrides["initial_layer_speed"] = "25"
        combined_overrides["sparse_infill_pattern"] = "gyroid"
        filament_notes.append(
            "TPU Tip: Capped speeds to prevent extruder buckling and selected Gyroid infill for uniform 3D squish/flexibility. Do not feed soft TPU through standard AMS (use external spool or AMS-compatible TPU)."
        )
    elif "SILK" in fil_upper:
        combined_overrides["outer_wall_speed"] = "60"
        combined_overrides["wall_loops"] = str(max(int(combined_overrides.get("wall_loops", "3")), 3))
        filament_notes.append(
            "Silk PLA Tip: Set outer wall speed to a constant 60 mm/s — Silk PLA turns matte if printed too fast and only looks mirror-shiny at 50-70 mm/s!"
        )

    if has_overhangs is True and "enable_support" not in combined_overrides:
        combined_overrides["enable_support"] = "1"
        combined_overrides["support_type"] = "tree(auto)"
        combined_overrides["support_on_build_plate_only"] = "1"
        explanations.append("Enabled Tree(auto) supports on build plate only for overhangs.")
    elif has_overhangs is False:
        combined_overrides["enable_support"] = "0"

    # Build step-by-step GUI walkthrough so the user can also apply it visually if they want
    gui_steps = []
    for k, v in combined_overrides.items():
        meta = SETTINGS_ENCYCLOPEDIA.get(k, {})
        gui_steps.append({
            "json_key": k,
            "recommended_value": v,
            "where_in_bambu_studio_gui": meta.get("gui_tab", "Process Settings"),
            "gui_field_name": meta.get("gui_label", k),
        })

    return {
        "goal": goal,
        "filament_type": filament_type,
        "nozzle_size_mm": nozzle_size_mm,
        "matched_profiles": matched_titles,
        "bambu_studio_overrides": combined_overrides,
        "gui_walkthrough": gui_steps,
        "why_these_settings": explanations,
        "filament_specific_advice": filament_notes,
    }


def diagnose_print_issue(symptom_description: str) -> Dict[str, Any]:
    """Diagnose a 3D printing defect or failure and return Bambu Studio fixes."""
    q = symptom_description.lower()
    matches = []

    keyword_map = {
        "nozzle_scraping_or_knocked_print": ["scrape", "scraping", "knock", "hit", "collision", "grid", "grinding", "fell over", "spaghetti"],
        "warping_corners_lifting": ["warp", "lifting", "curl", "peel", "corner", "adhesion", "unstick", "first layer"],
        "stringing_and_wisps": ["string", "stringing", "cobweb", "hair", "ooze", "oozing", "wisp", "wet"],
        "supports_fused_to_model": ["support", "fused", "stuck", "hard to remove", "scar", "underside"],
        "holes_or_pegs_too_tight": ["tight", "hole", "fit", "tolerance", "clearance", "elephant", "screw", "peg", "dimension"],
        "pillowing_or_gaps_on_top_surface": ["pillow", "pillowing", "top surface", "gaps on top", "holes on top", "rough top"],
    }

    for issue_id, kws in keyword_map.items():
        score = sum(1 for kw in kws if kw in q)
        if score > 0:
            matches.append({"issue_id": issue_id, "score": score, **TROUBLESHOOTING_GUIDE[issue_id]})

    matches.sort(key=lambda m: m["score"], reverse=True)
    if not matches:
        return {
            "symptom_description": symptom_description,
            "matched_issues": list(TROUBLESHOOTING_GUIDE.values()),
            "note": "Showing all common Bambu Studio troubleshooting guides.",
        }

    return {
        "symptom_description": symptom_description,
        "matched_issues": matches,
    }


# ---------------------------------------------------------------------------
# 4. BAMBU STUDIO FILAMENT CALIBRATION ENGINE
# ---------------------------------------------------------------------------
FILAMENT_CALIBRATION_TARGETS: Dict[str, Dict[str, Any]] = {
    "PLA": {
        "k_factor_range": "0.015 - 0.025 (Direct Drive 0.4mm nozzle)",
        "flow_ratio_typical": "0.96 - 0.99",
        "max_volumetric_speed_mm3_s": "18 - 24 mm³/s (Standard PLA) / 24 - 28 mm³/s (Bambu PLA Basic/High Speed)",
        "nozzle_temp_range_c": "210 - 230 °C (Tower range: 195 - 235 °C)",
        "retraction_length_mm": "0.6 - 0.8 mm @ 30 mm/s",
    },
    "SILK": {
        "k_factor_range": "0.020 - 0.030 (Direct Drive 0.4mm nozzle)",
        "flow_ratio_typical": "0.95 - 0.98 (die swell requires carefully tuned flow)",
        "max_volumetric_speed_mm3_s": "10 - 14 mm³/s (keep outer wall 50-70 mm/s for mirror shine)",
        "nozzle_temp_range_c": "215 - 235 °C (Higher temp = higher gloss)",
        "retraction_length_mm": "0.6 - 0.8 mm @ 30 mm/s (Normal Z-hop)",
    },
    "PETG": {
        "k_factor_range": "0.025 - 0.045 (Direct Drive 0.4mm nozzle)",
        "flow_ratio_typical": "0.94 - 0.97 (slightly lower to prevent nozzle blob buildup)",
        "max_volumetric_speed_mm3_s": "11 - 16 mm³/s (Standard PETG) / 18 - 22 mm³/s (PETG-HF)",
        "nozzle_temp_range_c": "245 - 265 °C (Tower range: 235 - 270 °C)",
        "retraction_length_mm": "0.8 - 1.0 mm @ 30 mm/s (set Z-hop type to Normal to prevent wisps)",
    },
    "ABS": {
        "k_factor_range": "0.018 - 0.030 (Direct Drive 0.4mm nozzle)",
        "flow_ratio_typical": "0.94 - 0.98",
        "max_volumetric_speed_mm3_s": "16 - 22 mm³/s",
        "nozzle_temp_range_c": "255 - 275 °C (Tower range: 245 - 280 °C, Chamber >45 °C)",
        "retraction_length_mm": "0.6 - 0.8 mm @ 30 mm/s",
    },
    "ASA": {
        "k_factor_range": "0.018 - 0.030 (Direct Drive 0.4mm nozzle)",
        "flow_ratio_typical": "0.94 - 0.98",
        "max_volumetric_speed_mm3_s": "15 - 20 mm³/s",
        "nozzle_temp_range_c": "255 - 275 °C (Tower range: 245 - 280 °C, Chamber >45 °C)",
        "retraction_length_mm": "0.6 - 0.8 mm @ 30 mm/s",
    },
    "TPU": {
        "k_factor_range": "0.060 - 0.120 (higher elasticity requires higher K-factor)",
        "flow_ratio_typical": "0.98 - 1.03",
        "max_volumetric_speed_mm3_s": "3.2 - 6.5 mm³/s (95A TPU)",
        "nozzle_temp_range_c": "220 - 240 °C (Tower range: 210 - 245 °C)",
        "retraction_length_mm": "0.4 - 0.6 mm @ 20 mm/s (avoid long/fast retractions that jam soft filament)",
    },
    "PA": {
        "k_factor_range": "0.020 - 0.035 (Direct Drive 0.4mm nozzle)",
        "flow_ratio_typical": "0.95 - 0.99",
        "max_volumetric_speed_mm3_s": "10 - 15 mm³/s",
        "nozzle_temp_range_c": "270 - 295 °C (Dry at 80 °C for 12h before calibrating!)",
        "retraction_length_mm": "0.8 - 1.0 mm @ 30 mm/s",
    },
}


def get_calibration_guide(
    calibration_type: str = "all",
    filament_type: str = "PLA",
) -> Dict[str, Any]:
    """Return step-by-step Bambu Studio Calibration tab workflows, formulas, and target values."""
    fil_upper = filament_type.strip().upper()
    target_key = "PLA"
    for candidate in ("SILK", "PETG", "ABS", "ASA", "TPU", "PA"):
        if candidate in fil_upper:
            target_key = candidate
            break
    if "NYLON" in fil_upper:
        target_key = "PA"

    targets = FILAMENT_CALIBRATION_TARGETS[target_key]

    workflows: Dict[str, Dict[str, Any]] = {
        "flow_dynamics": {
            "title": "1. Flow Dynamics Calibration (Pressure Advance / K-Factor)",
            "bambu_studio_location": "Top Navigation Bar -> Calibration -> Flow Dynamics",
            "purpose": (
                "Compensates for molten plastic pressure lag inside the nozzle during rapid acceleration "
                "and deceleration. Eliminates bulging sharp corners, gaps at seam restarts, and uneven line widths."
            ),
            "recommended_target": targets["k_factor_range"],
            "steps": [
                "Open the 'Calibration' tab at the top of Bambu Studio and select 'Flow Dynamics'.",
                "Choose 'Manual' calibration (Line Method or Pattern Method) or 'Auto-Calibration' (X1C / A1 eddy-current / Micro-Lidar).",
                "Set K-value range: for Direct Drive 0.4mm nozzles, start at 0.000, end at 0.050 (or 0.120 for TPU), step 0.005.",
                "Inspect the printed lines/chevrons: pick the K-value where the transition between slow->fast->slow extrusion is most uniform without thinning gaps (K too high) or blobs/bulges (K too low).",
                "Click 'Manage Result' in the Calibration tab (or Device -> AMS slot edit) to save the K-factor profile and bind it to your filament slot.",
            ],
            "formula_and_rules": {
                "parameter_name": "pressure_advance (K-factor)",
                "rule_of_thumb": "Always run Flow Dynamics (K-factor) BEFORE Flow Rate calibration so corner pressure doesn't skew surface smoothness.",
            },
        },
        "flow_rate": {
            "title": "2. Flow Rate Calibration (Pass 1 & Pass 2 Extrusion Multiplier)",
            "bambu_studio_location": "Top Navigation Bar -> Calibration -> Flow Rate",
            "purpose": (
                "Tunes the exact volume of plastic extruded (`filament_flow_ratio`) so top surfaces are glassy smooth "
                "without gaps between lines (under-extrusion) or rough plowed ridges (over-extrusion)."
            ),
            "recommended_target": targets["flow_ratio_typical"],
            "steps": [
                "In the 'Calibration' tab, select 'Flow Rate' -> 'Pass 1' (coarse test chips from -20 to +20).",
                "Examine the 9 printed test swatches by sight and fingernail feel across the center (ignore perimeter edges). Select the smoothest swatch modifier (e.g., +5 or 0).",
                "Enter that Pass 1 value into Bambu Studio to generate 'Pass 2' (fine test chips from -9 to +0 around your Pass 1 winner).",
                "After Pass 2 finishes, pick the smoothest chip modifier and let Bambu Studio calculate and save the updated Flow Ratio into your custom Filament Preset (`filament_flow_ratio`).",
            ],
            "formula_and_rules": {
                "formula": "New Ratio = Old Ratio * (100 + modifier) / 100",
                "example": (
                    "If Old Ratio = 0.98 and Pass 1 winner is +5: Pass 1 Ratio = 0.98 * (100 + 5) / 100 = 1.029. "
                    "If Pass 2 winner is -2: Final Ratio = 1.029 * (100 - 2) / 100 = 1.008."
                ),
            },
        },
        "max_volumetric_speed": {
            "title": "3. Max Volumetric Speed Calibration (mm³/s Hotend Melt Ceiling)",
            "bambu_studio_location": "Filament Settings -> Filament -> Max volumetric speed (or Calibration -> More)",
            "purpose": (
                "Finds the maximum cubic millimeters of plastic per second (mm³/s) your hotend can fully melt before "
                "the extruder clicks, skips steps, or prints dull/under-extruded brittle layers."
            ),
            "recommended_target": targets["max_volumetric_speed_mm3_s"],
            "steps": [
                "Generate a Max Volumetric Speed tower (starting at 8 mm³/s, stepping by +0.5 mm³/s per millimeter of Z height up to 30 mm³/s).",
                "Watch and inspect the meandering wall as Z height increases: note the exact height (mm) where surface sheen turns matte, wavy, or under-extruded.",
                "Compute the failure volumetric flow rate and subtract 10-15% as a safety margin.",
                "Save the safe value in Filament Settings -> 'Max volumetric speed' (`filament_max_volumetric_speed`). Bambu Studio will automatically cap all print speeds whenever `Speed * Line Width * Layer Height` reaches this ceiling!",
            ],
            "formula_and_rules": {
                "volumetric_flow_formula": "Volumetric Flow (mm³/s) = Print Speed (mm/s) * Line Width (mm) * Layer Height (mm)",
                "tower_height_formula": "Flow at Height Z = Start_Flow + (Z_height_mm * Step_per_mm)  (Safe Target = Failure_Flow * 0.85)",
                "speed_cap_example": "At 21 mm³/s with 0.42mm line width and 0.20mm layer height, Bambu Studio automatically caps print speed at 21 / (0.42 * 0.20) = 250 mm/s.",
            },
        },
        "temperature_and_retraction": {
            "title": "4. Temperature Tower & Retraction / Stringing Test",
            "bambu_studio_location": "Filament Settings -> Filament (Nozzle Temp) & Setting Overrides (Retraction)",
            "purpose": (
                "Identifies the optimal nozzle temperature for inter-layer strength, overhang crispness, and minimal stringing, "
                "then fine-tunes retraction distance and Z-hop style."
            ),
            "recommended_target": {
                "nozzle_temp": targets["nozzle_temp_range_c"],
                "retraction": targets["retraction_length_mm"],
            },
            "steps": [
                "Dry the filament first! Wet PETG/TPU/PA/PLA will string at every temperature and invalidate retraction tests.",
                "Print a Temperature Tower spanning the filament's range in 5 °C increments (e.g., 230 °C down to 195 °C for PLA; 265 °C down to 235 °C for PETG).",
                "Inspect bridges, 45°/60° overhang cones, and stringing pins on each tier; test layer adhesion by trying to snap the tier joints with pliers.",
                "Pick the lowest temperature that still delivers strong layer bonding and uniform surface gloss.",
                "If fine cobweb wisps remain, print a 2-post Retraction Tower and adjust Filament Settings -> Setting Overrides -> 'Retraction length' (0.6-1.0mm) and change 'Z hop type' from 'Auto/Spiral' to 'Normal'.",
            ],
            "formula_and_rules": {
                "golden_rule": "Never exceed 1.2mm retraction length on Bambu Direct Drive all-metal hotends, or molten filament can be pulled into the cold zone and cause heat-creep clogs.",
            },
        },
    }

    q = calibration_type.strip().lower()
    if q in ("all", "", "*"):
        selected = workflows
    else:
        selected = {}
        alias_map = {
            "flow_dynamics": ["flow_dynamics", "dynamics", "pressure", "pa", "k-factor", "k_factor", "k factor"],
            "flow_rate": ["flow_rate", "flow rate", "pass 1", "pass 2", "extrusion multiplier", "ratio"],
            "max_volumetric_speed": ["max_volumetric_speed", "volumetric", "mvs", "mm3", "speed", "ceiling"],
            "temperature_and_retraction": ["temperature_and_retraction", "temp", "temperature", "retraction", "stringing", "tower"],
        }
        for key, aliases in alias_map.items():
            if q == key or any(a in q for a in aliases):
                selected[key] = workflows[key]
        if not selected:
            selected = workflows

    return {
        "calibration_type": calibration_type,
        "filament_type": filament_type,
        "matched_material_profile": target_key,
        "recommended_calibration_order": [
            "1. Dry Filament & Temperature Tower (establish thermal baseline)",
            "2. Flow Dynamics / Pressure Advance K-Factor (stabilize corner & acceleration pressure)",
            "3. Flow Rate Pass 1 & Pass 2 (`New Ratio = Old Ratio * (100 + modifier) / 100`)",
            "4. Max Volumetric Speed Ceiling (`mm³/s = Speed * Line Width * Layer Height`)",
            "5. Retraction & Z-Hop Fine Tuning",
        ],
        "target_values_for_filament": targets,
        "workflows": selected,
    }

