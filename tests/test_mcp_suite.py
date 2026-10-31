"""Unit tests for 3MF editing, STL inspection, mesh repair, and AMS color matching.

Run with: python -m unittest discover -s tests -p "test_*.py"
"""

from __future__ import annotations

import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

# Add src/ to sys.path for zero-install testing
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bambu_studio_mcp.ai_features import (  # noqa: E402
    match_ams_colors_cielab,
    repair_and_ground_stl,
)
from bambu_studio_mcp.model_3mf import (  # noqa: E402
    add_empty_plate_to_3mf,
    inspect_3d_model,
    list_plates_in_3mf,
    move_object_to_plate_in_3mf,
    remove_plate_from_3mf,
    set_object_settings_in_3mf,
)

Vec3 = Tuple[float, float, float]
Triangle = Tuple[Vec3, Vec3, Vec3]

MODEL_SETTINGS = "Metadata/model_settings.config"
MODEL_XML = b'<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter"/>'
MODEL_SETTINGS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="1">
    <metadata key="name" value="Cube"/>
    <metadata key="extruder" value="1"/>
    <part id="1" subtype="normal_part">
      <metadata key="name" value="Cube Part"/>
      <metadata key="extruder" value="1"/>
    </part>
  </object>
  <object id="2">
    <metadata key="name" value="Bracket"/>
    <metadata key="extruder" value="1"/>
  </object>
  <object id="3">
    <metadata key="name" value="Unplaced"/>
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value="First"/>
    <metadata key="locked" value="false"/>
    <model_instance>
      <metadata key="object_id" value="1"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="101"/>
    </model_instance>
    <model_instance>
      <metadata key="object_id" value="2"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="102"/>
      <metadata key="object_name" value="Bracket Copy"/>
    </model_instance>
  </plate>
  <assemble/>
</config>
"""


def write_project_3mf(path: Path, settings_xml: str = MODEL_SETTINGS_XML) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("3D/3dmodel.model", MODEL_XML)
        zf.writestr(MODEL_SETTINGS, settings_xml)


def read_settings_root(path: Path) -> ET.Element:
    with zipfile.ZipFile(path, "r") as zf:
        return ET.fromstring(zf.read(MODEL_SETTINGS))


def object_metadata(path: Path, object_id: str) -> Dict[str, str]:
    root = read_settings_root(path)
    obj = next(o for o in root.findall("object") if o.attrib["id"] == object_id)
    return {m.attrib["key"]: m.attrib["value"] for m in obj.findall("metadata")}


def cube_triangles(size: float = 20.0, z_offset: float = 0.0) -> List[Triangle]:
    """Return an outward-wound, watertight cube with its base at z_offset."""
    s = size
    z0, z1 = z_offset, z_offset + s
    a, b, c, d = (0.0, 0.0, z0), (s, 0.0, z0), (s, s, z0), (0.0, s, z0)
    e, f, g, h = (0.0, 0.0, z1), (s, 0.0, z1), (s, s, z1), (0.0, s, z1)
    return [
        (a, c, b), (a, d, c),  # bottom
        (e, f, g), (e, g, h),  # top
        (a, b, f), (a, f, e),  # front
        (b, c, g), (b, g, f),  # right
        (c, d, h), (c, h, g),  # back
        (d, a, e), (d, e, h),  # left
    ]


def write_binary_stl(path: Path, triangles: Sequence[Triangle]) -> None:
    buf = bytearray(b"bambu-studio-mcp test".ljust(80, b"\x00"))
    buf.extend(struct.pack("<I", len(triangles)))
    for v0, v1, v2 in triangles:
        buf.extend(struct.pack("<12fH", 0.0, 0.0, 0.0, *v0, *v1, *v2, 0))
    path.write_bytes(bytes(buf))


def read_binary_stl(path: Path) -> List[Triangle]:
    data = path.read_bytes()
    count = struct.unpack("<I", data[80:84])[0]
    triangles: List[Triangle] = []
    for i in range(count):
        vals = struct.unpack_from("<12fH", data, 84 + i * 50)
        triangles.append((vals[3:6], vals[6:9], vals[9:12]))
    return triangles


class TempDirTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)


class PlateEditingTests(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.project = self.tmp / "project.3mf"
        write_project_3mf(self.project)

    def plate_by_id(self, plate_id: int) -> Dict:
        plates = list_plates_in_3mf(str(self.project))["plates"]
        return next(p for p in plates if p["plater_id"] == plate_id)

    def test_list_plates_reports_instances_and_resolves_names(self) -> None:
        result = list_plates_in_3mf(str(self.project))
        self.assertTrue(result["success"])
        self.assertEqual(result["total_plates"], 1)
        plate = result["plates"][0]
        self.assertEqual(plate["plater_id"], 1)
        self.assertEqual(plate["plater_name"], "First")
        self.assertFalse(plate["locked"])
        self.assertEqual(plate["instance_count"], 2)
        names = [i["object_name"] for i in plate["model_instances"]]
        self.assertEqual(names, ["Cube", "Bracket Copy"])

    def test_list_plates_without_model_settings_is_empty(self) -> None:
        bare = self.tmp / "bare.3mf"
        with zipfile.ZipFile(bare, "w") as zf:
            zf.writestr("3D/3dmodel.model", MODEL_XML)
        result = list_plates_in_3mf(str(bare))
        self.assertTrue(result["success"])
        self.assertEqual(result["plates"], [])

    def test_add_empty_plate_assigns_next_id(self) -> None:
        result = add_empty_plate_to_3mf(str(self.project), plate_name="Second")
        self.assertTrue(result["success"])
        self.assertEqual(result["new_plate_id"], 2)
        self.assertEqual(result["total_plates"], 2)
        plate = self.plate_by_id(2)
        self.assertEqual(plate["plater_name"], "Second")
        self.assertEqual(plate["instance_count"], 0)

    def test_add_empty_plate_to_output_path_leaves_input_unchanged(self) -> None:
        output = self.tmp / "out.3mf"
        add_empty_plate_to_3mf(str(self.project), output_3mf_path=str(output))
        self.assertEqual(list_plates_in_3mf(str(self.project))["total_plates"], 1)
        self.assertEqual(list_plates_in_3mf(str(output))["total_plates"], 2)

    def test_move_object_by_name_to_existing_plate(self) -> None:
        add_empty_plate_to_3mf(str(self.project))
        result = move_object_to_plate_in_3mf(str(self.project), "Cube", 2)
        self.assertTrue(result["success"])
        self.assertEqual(result["moved_count"], 1)
        self.assertFalse(result["target_plate_created"])
        self.assertEqual(self.plate_by_id(1)["instance_count"], 1)
        moved = self.plate_by_id(2)["model_instances"]
        self.assertEqual([i["object_id"] for i in moved], ["1"])

    def test_move_object_by_id_creates_target_plate_before_assemble(self) -> None:
        result = move_object_to_plate_in_3mf(str(self.project), "2", 5)
        self.assertTrue(result["target_plate_created"])
        self.assertEqual(self.plate_by_id(5)["instance_count"], 1)
        self.assertEqual(read_settings_root(self.project)[-1].tag, "assemble")

    def test_move_object_already_on_target_is_a_noop(self) -> None:
        result = move_object_to_plate_in_3mf(str(self.project), "Cube", 1)
        self.assertEqual(result["moved_count"], 0)
        self.assertEqual(result["already_on_target_count"], 1)

    def test_move_unknown_object_returns_error(self) -> None:
        result = move_object_to_plate_in_3mf(str(self.project), "Nope", 1)
        self.assertIn("error", result)
        self.assertEqual(result["available_objects"]["1"], "Cube")

    def test_remove_plate_renumbers_remaining_plates(self) -> None:
        add_empty_plate_to_3mf(str(self.project), plate_name="Second")
        add_empty_plate_to_3mf(str(self.project), plate_name="Third")
        result = remove_plate_from_3mf(str(self.project), 1)
        self.assertTrue(result["success"])
        self.assertEqual(result["removed_plate_name"], "First")
        self.assertEqual(result["removed_model_instances"], 2)
        self.assertEqual(result["remaining_plate_ids"], [1, 2])
        plates = list_plates_in_3mf(str(self.project))["plates"]
        self.assertEqual(
            [(p["plater_id"], p["plater_name"]) for p in plates],
            [(1, "Second"), (2, "Third")],
        )

    def test_remove_unknown_plate_returns_error(self) -> None:
        result = remove_plate_from_3mf(str(self.project), 9)
        self.assertIn("error", result)
        self.assertEqual(result["available_plate_ids"], ["1"])


class SetObjectSettingsTests(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.project = self.tmp / "project.3mf"
        write_project_3mf(self.project)

    def test_updates_existing_and_creates_new_metadata(self) -> None:
        result = set_object_settings_in_3mf(
            str(self.project), "1", {"extruder": 2, "wall_loops": 4, "sparse_infill_density": "25%"}
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["matched_by"], "id")
        self.assertEqual(result["updated_objects"][0]["updated_keys"], ["extruder"])
        self.assertEqual(
            result["updated_objects"][0]["created_keys"], ["wall_loops", "sparse_infill_density"]
        )
        meta = object_metadata(self.project, "1")
        self.assertEqual(meta["extruder"], "2")
        self.assertEqual(meta["wall_loops"], "4")
        self.assertEqual(meta["sparse_infill_density"], "25%")
        self.assertEqual(meta["name"], "Cube")

    def test_only_target_object_is_changed(self) -> None:
        set_object_settings_in_3mf(str(self.project), "1", {"extruder": 2})
        self.assertEqual(object_metadata(self.project, "2")["extruder"], "1")
        obj = read_settings_root(self.project).find("object")
        part_meta = {m.attrib["key"]: m.attrib["value"] for m in obj.find("part").findall("metadata")}
        self.assertEqual(part_meta["extruder"], "1")

    def test_new_metadata_is_placed_before_parts(self) -> None:
        set_object_settings_in_3mf(str(self.project), "1", {"wall_loops": 4})
        obj = read_settings_root(self.project).find("object")
        self.assertEqual([c.tag for c in obj], ["metadata", "metadata", "metadata", "part"])

    def test_booleans_use_bambu_format(self) -> None:
        set_object_settings_in_3mf(
            str(self.project), "1", {"enable_support": True, "ironing": False}
        )
        meta = object_metadata(self.project, "1")
        self.assertEqual(meta["enable_support"], "1")
        self.assertEqual(meta["ironing"], "0")

    def test_matches_by_object_name(self) -> None:
        result = set_object_settings_in_3mf(str(self.project), "Bracket", {"wall_loops": 3})
        self.assertEqual(result["matched_by"], "name")
        self.assertEqual(object_metadata(self.project, "2")["wall_loops"], "3")

    def test_matches_by_instance_object_name(self) -> None:
        result = set_object_settings_in_3mf(str(self.project), "Bracket Copy", {"wall_loops": 3})
        self.assertEqual(result["matched_by"], "model_instance")
        self.assertEqual(object_metadata(self.project, "2")["wall_loops"], "3")

    def test_matches_by_instance_identify_id(self) -> None:
        result = set_object_settings_in_3mf(str(self.project), "101", {"wall_loops": 3})
        self.assertEqual(result["matched_by"], "model_instance")
        self.assertEqual(object_metadata(self.project, "1")["wall_loops"], "3")

    def test_name_shared_by_objects_updates_all(self) -> None:
        settings_xml = """<config>
          <object id="1"><metadata key="name" value="Twin"/></object>
          <object id="2"><metadata key="name" value="Twin"/></object>
        </config>"""
        write_project_3mf(self.project, settings_xml)
        result = set_object_settings_in_3mf(str(self.project), "Twin", {"wall_loops": 3})
        self.assertEqual(len(result["updated_objects"]), 2)
        self.assertEqual(object_metadata(self.project, "1")["wall_loops"], "3")
        self.assertEqual(object_metadata(self.project, "2")["wall_loops"], "3")

    def test_id_takes_precedence_over_name(self) -> None:
        settings_xml = """<config>
          <object id="1"><metadata key="name" value="2"/></object>
          <object id="2"><metadata key="name" value="Other"/></object>
        </config>"""
        write_project_3mf(self.project, settings_xml)
        result = set_object_settings_in_3mf(str(self.project), "2", {"wall_loops": 3})
        self.assertEqual(result["matched_by"], "id")
        self.assertNotIn("wall_loops", object_metadata(self.project, "1"))
        self.assertEqual(object_metadata(self.project, "2")["wall_loops"], "3")

    def test_output_path_preserves_input_and_other_archive_members(self) -> None:
        output = self.tmp / "nested" / "out.3mf"
        original = self.project.read_bytes()
        result = set_object_settings_in_3mf(
            str(self.project), "Cube", {"wall_loops": 4}, str(output)
        )
        self.assertEqual(result["output_3mf"], str(output))
        self.assertEqual(self.project.read_bytes(), original)
        self.assertEqual(object_metadata(output, "1")["wall_loops"], "4")
        with zipfile.ZipFile(output, "r") as zf:
            self.assertEqual(zf.read("3D/3dmodel.model"), MODEL_XML)
            self.assertEqual(zf.namelist().count(MODEL_SETTINGS), 1)
        self.assertEqual(list(self.tmp.rglob("*.tmp")), [])

    def test_unknown_object_returns_error_without_writing(self) -> None:
        output = self.tmp / "out.3mf"
        result = set_object_settings_in_3mf(
            str(self.project), "Nope", {"wall_loops": 4}, str(output)
        )
        self.assertIn("error", result)
        self.assertEqual(result["available_objects"]["2"], "Bracket")
        self.assertFalse(output.exists())

    def test_invalid_inputs_return_errors(self) -> None:
        original = self.project.read_bytes()
        cases = [
            (str(self.tmp / "missing.3mf"), "1", {"wall_loops": 4}),
            (str(self.project), "", {"wall_loops": 4}),
            (str(self.project), "1", {}),
            (str(self.project), "1", {"wall_loops": None}),
            (str(self.project), "1", {"wall_loops": {"nested": 1}}),
        ]
        for path, identifier, overrides in cases:
            with self.subTest(identifier=identifier, overrides=overrides):
                self.assertIn("error", set_object_settings_in_3mf(path, identifier, overrides))
        self.assertEqual(self.project.read_bytes(), original)

    def test_missing_model_settings_returns_error(self) -> None:
        bare = self.tmp / "bare.3mf"
        with zipfile.ZipFile(bare, "w") as zf:
            zf.writestr("3D/3dmodel.model", MODEL_XML)
        self.assertIn("error", set_object_settings_in_3mf(str(bare), "1", {"wall_loops": 4}))

    def test_edited_project_remains_readable_by_plate_tools(self) -> None:
        set_object_settings_in_3mf(str(self.project), "1", {"wall_loops": 4})
        self.assertEqual(list_plates_in_3mf(str(self.project))["plates"][0]["instance_count"], 2)


class InspectStlTests(TempDirTestCase):
    def inspect(self, triangles: Sequence[Triangle]) -> Dict:
        path = self.tmp / "model.stl"
        write_binary_stl(path, triangles)
        return inspect_3d_model(str(path))

    def test_clean_cube_passes_full_audit(self) -> None:
        result = self.inspect(cube_triangles())
        self.assertEqual(result["format"], "STL")
        self.assertEqual(result["triangle_count"], 12)
        self.assertEqual(result["dimensions_mm"], {"x": 20.0, "y": 20.0, "z": 20.0})
        self.assertAlmostEqual(result["volume_cm3"], 8.0, places=2)

        audit = result["printability_11_point_audit"]
        self.assertEqual(audit["printability_score_100"], 100)
        self.assertEqual(len(audit["checks"]), 11)
        for name, check in audit["checks"].items():
            with self.subTest(check=name):
                self.assertIs(check["passed"], True)

    def test_open_mesh_fails_watertight_check_and_lowers_score(self) -> None:
        audit = self.inspect(cube_triangles()[:-1])["printability_11_point_audit"]
        check = audit["checks"]["1_watertight_manifold"]
        self.assertIs(check["passed"], False)
        self.assertEqual(check["open_boundary_edges"], 3)
        self.assertEqual(audit["printability_score_100"], 88)

    def test_inverted_normals_are_detected(self) -> None:
        inverted = [(v0, v2, v1) for v0, v1, v2 in cube_triangles()]
        audit = self.inspect(inverted)["printability_11_point_audit"]
        self.assertIs(audit["checks"]["4_outward_face_normals"]["passed"], False)
        self.assertLess(audit["printability_score_100"], 100)

    def test_degenerate_triangle_is_counted(self) -> None:
        point = (5.0, 5.0, 5.0)
        audit = self.inspect(cube_triangles() + [(point, point, point)])[
            "printability_11_point_audit"
        ]
        check = audit["checks"]["3_degenerate_triangles"]
        self.assertIs(check["passed"], False)
        self.assertEqual(check["zero_area_triangle_count"], 1)

    def test_missing_and_unsupported_files_return_errors(self) -> None:
        self.assertIn("error", inspect_3d_model(str(self.tmp / "missing.stl")))
        unsupported = self.tmp / "model.obj"
        unsupported.write_text("not a mesh")
        self.assertIn("error", inspect_3d_model(str(unsupported)))


class RepairAndGroundStlTests(TempDirTestCase):
    def test_removes_degenerate_face_and_grounds_mesh(self) -> None:
        z_offset = 7.5
        source = self.tmp / "broken.stl"
        output = self.tmp / "fixed.stl"
        collinear = ((0.0, 0.0, z_offset), (10.0, 0.0, z_offset), (20.0, 0.0, z_offset))
        write_binary_stl(source, cube_triangles(z_offset=z_offset) + [collinear])

        result = repair_and_ground_stl(str(source), str(output))

        self.assertTrue(result["success"])
        self.assertEqual(result["original_triangles"], 13)
        self.assertEqual(result["repaired_triangles"], 12)
        self.assertEqual(result["removed_degenerate_triangles"], 1)
        self.assertEqual(result["removed_duplicate_triangles"], 0)
        self.assertFalse(result["flipped_inverted_normals"])
        self.assertAlmostEqual(result["z_grounded_shift_mm"], -z_offset, places=3)

        z_values = [v[2] for tri in read_binary_stl(output) for v in tri]
        self.assertAlmostEqual(min(z_values), 0.0, places=4)
        self.assertAlmostEqual(max(z_values), 20.0, places=4)

        audit = inspect_3d_model(str(output))["printability_11_point_audit"]
        self.assertEqual(audit["printability_score_100"], 100)

    def test_flips_inverted_normals_and_removes_duplicates(self) -> None:
        source = self.tmp / "inverted.stl"
        inverted = [(v0, v2, v1) for v0, v1, v2 in cube_triangles()]
        write_binary_stl(source, inverted + inverted[:1])

        result = repair_and_ground_stl(str(source))

        self.assertTrue(result["flipped_inverted_normals"])
        self.assertEqual(result["removed_duplicate_triangles"], 1)
        self.assertEqual(Path(result["output_stl"]).name, "inverted_repaired.stl")
        audit = inspect_3d_model(result["output_stl"])["printability_11_point_audit"]
        self.assertEqual(audit["printability_score_100"], 100)

    def test_missing_file_returns_error(self) -> None:
        self.assertIn("error", repair_and_ground_stl(str(self.tmp / "missing.stl")))


class MatchAmsColorsTests(TempDirTestCase):
    def test_exact_palette_color_has_zero_delta_e(self) -> None:
        mapping = match_ams_colors_cielab(["#00AE42"])["color_mappings"][0]
        self.assertEqual(mapping["target_hex"], "#00AE42")
        self.assertEqual(mapping["best_match"]["slot"], "Bambu PLA Basic Bambu Green")
        self.assertEqual(mapping["best_match"]["delta_e_2000"], 0.0)
        self.assertTrue(mapping["match_quality"].startswith("Exact"))

    def test_pure_red_uses_known_cielab_and_ranks_matches(self) -> None:
        mapping = match_ams_colors_cielab(["#FF0000"])["color_mappings"][0]
        # Reference sRGB D65 values for pure red.
        self.assertAlmostEqual(mapping["target_cielab"]["L"], 53.2, delta=0.2)
        self.assertAlmostEqual(mapping["target_cielab"]["a"], 80.1, delta=0.3)
        self.assertAlmostEqual(mapping["target_cielab"]["b"], 67.2, delta=0.3)
        self.assertEqual(mapping["best_match"]["slot"], "Bambu PLA Basic Red")
        self.assertGreater(mapping["best_match"]["delta_e_2000"], 0.0)
        ranked = [mapping["best_match"]] + mapping["runner_up_matches"]
        deltas = [m["delta_e_2000"] for m in ranked]
        self.assertEqual(deltas, sorted(deltas))

    def test_results_preserve_input_order(self) -> None:
        result = match_ams_colors_cielab(["#00AE42", "#FF0000"])
        self.assertEqual(
            [m["target_hex"] for m in result["color_mappings"]], ["#00AE42", "#FF0000"]
        )
        self.assertIn("Reference Palette", result["palette_source"])

    def test_custom_spools_override_default_palette(self) -> None:
        spools = [
            {"slot": "AMS A1", "hex": "#FF0000", "material": "PETG"},
            {"slot": "AMS A2", "hex": "#00FF00", "material": "PLA"},
        ]
        result = match_ams_colors_cielab(["#FF0000"], available_spools=spools)
        best = result["color_mappings"][0]["best_match"]
        self.assertEqual(best["slot"], "AMS A1")
        self.assertEqual(best["material"], "PETG")
        self.assertEqual(best["delta_e_2000"], 0.0)

    def test_invalid_color_reports_error_per_entry(self) -> None:
        mappings = match_ams_colors_cielab(["not-a-color", "#00AE42"])["color_mappings"]
        self.assertIn("error", mappings[0])
        self.assertEqual(mappings[1]["target_hex"], "#00AE42")


if __name__ == "__main__":
    unittest.main()
