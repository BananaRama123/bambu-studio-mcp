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
    "ironing_type": {
        "gui_tab": "Quality -> Ironing",
        "gui_label": "Ironing Type",
        "type": "enum",
        "options": ["no ironing", "top surfaces", "topmost surface", "all solid layers"],
        "default_04_nozzle": "no ironing",
        "summary": "Passes the hot nozzle over flat top surfaces a second time extruding a tiny amount (10-15%) of filament to melt lines flat like injection molding.",
        "when_to_change": "Set to 'top surfaces' (with ironing_flow ~15%, ironing_speed ~30-60mm/s) for signs, badges, coasters, and flat-topped boxes.",
        "tradeoffs": "Adds time to flat top layers; has no benefit on curved/domed tops.",
    },
    " wall_generator": {
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
        "summary": "Expands (+) or shrinks (-) the outer boundary of the model in X/Y.",
        "when_to_change": "Set to -0.05mm to -0.10mm when pegs/tabs are too tight to fit into mating slots.",
        "tradeoffs": "Changes outer dimensions slightly.",
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

    # --- OTHERS TAB (ADHESION / MULTI-COLOR / SPECIAL) ---
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
    "flush_into_infill": {
        "gui_tab": "Others -> Flush options",
        "gui_label": "Flush into objects' infill",
        "type": "bool string ('0' or '1')",
        "default_04_nozzle": "0",
        "summary": "During AMS multi-color changes, purges old filament color inside the internal infill of the part instead of ejecting waste ('poop').",
        "when_to_change": "Enable ('1') on opaque multi-color models to reduce filament waste and purge time. Do NOT enable if purging dark black into thin white walls (can bleed through visually).",
        "tradeoffs": "Dark internal infill can show through thin translucent/white shells if wall_loops < 3.",
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
