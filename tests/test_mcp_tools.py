"""Self-test suite for bambu-studio-mcp tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src/ to sys.path for zero-install testing
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bambu_studio_mcp.server import (  # noqa: E402
    bambu_environment_info,
    compare_bambu_profiles,
    diagnose_print_defect,
    explain_bambu_setting,
    inspect_3d_model,
    inspect_bambu_profile,
    list_bambu_profiles,
    smart_slicing_advisor,
)


def create_sample_ascii_stl(path: Path) -> None:
    """Create a 20x20x20mm ASCII STL calibration cube for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # 12 triangles of a 20mm cube from (0,0,0) to (20,20,20)
    s = 20.0
    faces = [
        # Bottom (z=0, normal 0,0,-1)
        ((0, 0, -1), (0, 0, 0), (s, s, 0), (s, 0, 0)),
        ((0, 0, -1), (0, 0, 0), (0, s, 0), (s, s, 0)),
        # Top (z=s, normal 0,0,1)
        ((0, 0, 1), (0, 0, s), (s, 0, s), (s, s, s)),
        ((0, 0, 1), (0, 0, s), (s, s, s), (0, s, s)),
        # Front (y=0, normal 0,-1,0)
        ((0, -1, 0), (0, 0, 0), (s, 0, 0), (s, 0, s)),
        ((0, -1, 0), (0, 0, 0), (s, 0, s), (0, 0, s)),
        # Back (y=s, normal 0,1,0)
        ((0, 1, 0), (0, s, 0), (s, s, s), (s, s, 0)),
        ((0, 1, 0), (0, s, 0), (0, s, s), (s, s, s)),
        # Left (x=0, normal -1,0,0)
        ((-1, 0, 0), (0, 0, 0), (0, 0, s), (0, s, s)),
        ((-1, 0, 0), (0, 0, 0), (0, s, s), (0, s, 0)),
        # Right (x=s, normal 1,0,0)
        ((1, 0, 0), (s, 0, 0), (s, s, 0), (s, s, s)),
        ((1, 0, 0), (s, 0, 0), (s, s, s), (s, 0, s)),
    ]
    lines = ["solid calibration_cube"]
    for n, v0, v1, v2 in faces:
        lines.append(f"  facet normal {n[0]} {n[1]} {n[2]}")
        lines.append("    outer loop")
        lines.append(f"      vertex {v0[0]} {v0[1]} {v0[2]}")
        lines.append(f"      vertex {v1[0]} {v1[1]} {v1[2]}")
        lines.append(f"      vertex {v2[0]} {v2[1]} {v2[2]}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid calibration_cube")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_all_checks() -> None:
    print("1. Checking Bambu Studio Environment...")
    env_info = bambu_environment_info()
    print(json.dumps(env_info["environment"], indent=2))

    print("\n2. Listing Discovered Machine Profiles (sample)...")
    machines = list_bambu_profiles(category="machine", limit=5)
    print(f"Found {machines.get('total_matching', 0)} machine profiles.")
    for m in machines.get("profiles", []):
        print("  -", m["name"], f"({m['source']})")

    print("\n3. Testing Smart Slicing Advisor ('strong functional bracket' in PETG)...")
    adv = smart_slicing_advisor(goal="strong functional bracket", filament_type="PETG")
    print("Matched recipes:", adv["matched_profiles"])
    print("Overrides:", json.dumps(adv["bambu_studio_overrides"], indent=2))

    print("\n4. Testing Settings Encyclopedia ('sparse_infill_pattern')...")
    exp = explain_bambu_setting("sparse_infill_pattern")
    print("Matches:", exp["match_count"])

    print("\n5. Testing Defect Diagnosis ('nozzle scraping and knocking print over')...")
    diag = diagnose_print_defect("nozzle scraping and knocking print over")
    print("Top diagnosis:", diag["matched_issues"][0]["symptom"])

    print("\n6. Testing 3D Model Geometry Inspector on 20mm Calibration Cube...")
    cube_path = ROOT / "examples" / "calibration_cube_20mm.stl"
    create_sample_ascii_stl(cube_path)
    geom = inspect_3d_model(str(cube_path))
    print(json.dumps(geom, indent=2))


if __name__ == "__main__":
    run_all_checks()
