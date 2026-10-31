"""Move every object on one plate of a Bambu 3MF to another filament, then slice all plates.

Only the extruder values of the target plate's objects change. Every other archive
entry is copied byte-for-byte, and the config is edited as text rather than
re-serialized, so nothing else in the project shifts.

Standard library only; run with ``python -I`` because the input is a downloaded file.
"""
from __future__ import annotations

import argparse
import copy
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

CONFIG_ENTRY = "Metadata/model_settings.config"
REQUIRED_ENTRIES = ("[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model", CONFIG_ENTRY)
DEFAULT_INPUT = r"C:\Users\cplacentile\Downloads\SSBAP02_Black.3mf"
DEFAULT_OUTPUT = r"C:\Users\cplacentile\Downloads\SSBAP02_Plate6_Fila2.3mf"


class ProjectError(Exception):
    """The project does not match what this script expects, or verification failed."""


def _metadata(element: ET.Element) -> dict[str, str | None]:
    return {m.get("key"): m.get("value") for m in element.findall("metadata") if m.get("key")}


def extruder_snapshot(config_text: str) -> dict[tuple[str, str | None], str | None]:
    """Map (object id, part id or None) to each explicit extruder value in the config."""
    snapshot: dict[tuple[str, str | None], str | None] = {}
    for obj in ET.fromstring(config_text).findall("object"):
        object_id = obj.get("id", "")
        snapshot[(object_id, None)] = _metadata(obj).get("extruder")
        for part in obj.findall("part"):
            part_extruder = _metadata(part).get("extruder")
            if part_extruder is not None:
                snapshot[(object_id, part.get("id"))] = part_extruder
    return snapshot


def plate_objects(config_text: str) -> dict[int, list[str]]:
    """Map each plate number to the object ids placed on it."""
    plates: dict[int, list[str]] = {}
    for plate in ET.fromstring(config_text).findall("plate"):
        number = int(_metadata(plate)["plater_id"])
        plates[number] = [
            str(_metadata(instance)["object_id"]) for instance in plate.findall("model_instance")
        ]
    return plates


def retarget_objects(config_text: str, object_ids: list[str], old: str, new: str) -> str:
    """Rewrite the extruder of the given objects, including any part-level overrides."""
    extruder_re = re.compile(r'(<metadata key="extruder" value=")([^"]*)("\s*/>)')

    for object_id in object_ids:
        block_re = re.compile(rf'<object id="{re.escape(object_id)}">.*?</object>', re.S)
        block = block_re.search(config_text)
        if block is None:
            raise ProjectError(f"Object {object_id} is on the plate but has no config block.")

        values = [match.group(2) for match in extruder_re.finditer(block.group(0))]
        if not values or any(value != old for value in values):
            raise ProjectError(f"Object {object_id}: expected extruder {old}, found {values}.")

        updated = extruder_re.sub(rf"\g<1>{new}\g<3>", block.group(0))
        config_text = config_text[: block.start()] + updated + config_text[block.end() :]
    return config_text


def write_archive(source: zipfile.ZipFile, output: Path, new_config: bytes) -> None:
    """Write a copy of the archive with the config swapped, replacing the output atomically."""
    temp = output.with_name(output.name + ".tmp")
    try:
        with zipfile.ZipFile(temp, "w") as target:
            for info in source.infolist():
                data = new_config if info.filename == CONFIG_ENTRY else source.read(info.filename)
                target.writestr(copy.copy(info), data)
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)


def verify_archive(input_path: Path, output_path: Path, targets: list[str], old: str, new: str) -> None:
    """Re-read both files from disk and confirm that only the intended values changed."""
    with zipfile.ZipFile(input_path) as before, zipfile.ZipFile(output_path) as after:
        corrupt = after.testzip()
        if corrupt:
            raise ProjectError(f"Output entry failed its CRC check: {corrupt}")
        if before.namelist() != after.namelist():
            raise ProjectError("Output archive entries differ from the input.")

        missing = [name for name in REQUIRED_ENTRIES if name not in after.namelist()]
        if missing:
            raise ProjectError(f"Output is missing required 3MF entries: {missing}")
        ET.fromstring(after.read("3D/3dmodel.model"))

        changed = [
            name
            for name in before.namelist()
            if before.getinfo(name).CRC != after.getinfo(name).CRC
        ]
        if changed != [CONFIG_ENTRY]:
            raise ProjectError(f"Expected only {CONFIG_ENTRY} to change, but found: {changed}")

        old_text = before.read(CONFIG_ENTRY).decode("utf-8")
        new_text = after.read(CONFIG_ENTRY).decode("utf-8")

    old_values = extruder_snapshot(old_text)
    new_values = extruder_snapshot(new_text)
    if old_values.keys() != new_values.keys():
        raise ProjectError("The set of extruder entries changed.")
    if plate_objects(old_text) != plate_objects(new_text):
        raise ProjectError("Plate layout changed.")

    for key, old_value in old_values.items():
        expected = new if key[0] in targets else old_value
        if new_values[key] != expected:
            raise ProjectError(f"Object {key}: expected extruder {expected}, got {new_values[key]}.")
    if not all(old_values[key] == old for key in old_values if key[0] in targets):
        raise ProjectError(f"A target object was not on extruder {old} in the input.")

    print("Filament per plate (input -> output):")
    for number, objects in sorted(plate_objects(new_text).items()):
        before_set = sorted({str(old_values[(oid, None)]) for oid in objects})
        after_set = sorted({str(new_values[(oid, None)]) for oid in objects})
        print(f"  Plate {number}: {before_set} -> {after_set} ({len(objects)} objects)")
    print("Archive valid; only the target objects' extruders changed.")


def find_executable() -> Path:
    """Locate bambu-studio.exe, honouring the same BAMBU_STUDIO_EXE override as the MCP server."""
    candidates = [
        os.environ.get("BAMBU_STUDIO_EXE"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Bambu Studio", "bambu-studio.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Bambu Studio", "bambu-studio.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise ProjectError("bambu-studio.exe not found. Set BAMBU_STUDIO_EXE.")


def slice_all_plates(project: Path, sliced: Path, timeout: int) -> None:
    """Slice every plate headlessly. --arrange is left out so the plate layout is preserved."""
    sliced.unlink(missing_ok=True)  # A stale file must not pass as this run's result.
    command = [
        str(find_executable()),
        "--slice", "0",
        "--outputdir", str(sliced.parent),
        "--export-3mf", sliced.name,
        str(project),
    ]
    print("Running:", subprocess.list2cmdline(command), flush=True)
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, check=False,
    )
    if result.returncode != 0 or not sliced.is_file():
        raise ProjectError(
            f"Slicing failed (exit {result.returncode}).\n"
            f"stdout: {result.stdout[-2000:]}\nstderr: {result.stderr[-2000:]}"
        )


def verify_sliced(project: Path, sliced: Path) -> None:
    """Confirm that every plate has G-code using exactly the filaments its objects are set to."""
    with zipfile.ZipFile(project) as source:
        config_text = source.read(CONFIG_ENTRY).decode("utf-8")
    values = extruder_snapshot(config_text)
    expected = {
        number: {str(values[(oid, None)]) for oid in objects}
        for number, objects in plate_objects(config_text).items()
    }

    with zipfile.ZipFile(sliced) as result:
        corrupt = result.testzip()
        if corrupt:
            raise ProjectError(f"Sliced entry failed its CRC check: {corrupt}")
        names = set(result.namelist())
        info_root = ET.fromstring(result.read("Metadata/slice_info.config"))

    plates = {int(_metadata(plate)["index"]): plate for plate in info_root.findall("plate")}
    problems = []
    print("Sliced plates:")
    for number, wanted in sorted(expected.items()):
        if f"Metadata/plate_{number}.gcode" not in names or number not in plates:
            problems.append(f"Plate {number}: no G-code in the sliced file.")
            continue

        plate = plates[number]
        details = _metadata(plate)
        filaments = plate.findall("filament")
        used = {filament.get("id") for filament in filaments}
        grams = sum(float(filament.get("used_g", 0)) for filament in filaments)
        print(
            f"  Plate {number}: filament {sorted(used)}, "
            f"{float(details.get('prediction') or 0) / 3600:.2f} h, {grams:.1f} g"
        )
        for warning in plate.findall("warning"):
            print(f"    warning: {warning.get('msg')}")
        if used != wanted:
            problems.append(f"Plate {number}: G-code uses {sorted(used)}, expected {sorted(wanted)}.")

    if problems:
        raise ProjectError("\n".join(problems))
    print(f"Slicing verified: {sliced}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, default=Path(DEFAULT_INPUT))
    parser.add_argument("--output", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--plate", type=int, default=6)
    parser.add_argument("--from-filament", default="4")
    parser.add_argument("--to-filament", default="2")
    parser.add_argument("--no-slice", action="store_true", help="Stop after writing the project.")
    parser.add_argument("--timeout", type=int, default=1800, help="Slicing timeout in seconds.")
    args = parser.parse_args()

    if args.input.resolve() == args.output.resolve():
        parser.error("--output must differ from --input.")

    try:
        with zipfile.ZipFile(args.input) as source:
            config_text = source.read(CONFIG_ENTRY).decode("utf-8")
            targets = plate_objects(config_text).get(args.plate)
            if not targets:
                raise ProjectError(f"Plate {args.plate} has no objects.")
            print(f"Plate {args.plate} object ids: {targets}")
            updated = retarget_objects(config_text, targets, args.from_filament, args.to_filament)
            write_archive(source, args.output, updated.encode("utf-8"))

        verify_archive(args.input, args.output, targets, args.from_filament, args.to_filament)
        print(f"Wrote {args.output}")

        if not args.no_slice:
            sliced = args.output.with_name(f"{args.output.stem}.gcode.3mf")
            slice_all_plates(args.output, sliced, args.timeout)
            verify_sliced(args.output, sliced)
    except (ProjectError, OSError, KeyError, ET.ParseError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
