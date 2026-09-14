#!/usr/bin/env python3
"""Import directional still poses or 4x4 sheets into the Green Hero test package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

import generate_green_hero_animations as generator


DEFAULT_PACKAGE_ROOT = generator.DEFAULT_MANIFEST.parent.parent / "test"
COMPASS_KEYS = {
    "N": "N", "NO": "NO", "NE": "NO", "O": "O", "E": "O",
    "SO": "SO", "SE": "SO", "S": "S", "SW": "SW", "W": "W", "NW": "NW",
}
LEGACY_KEYS = {
    "w": "N", "wd": "NO", "d": "O", "sd": "SO",
    "s": "S", "sa": "SW", "a": "W", "wa": "NW",
}
SHEET_PATTERN = re.compile(
    r"greenhero_(N|NO|NW|O|S|SO|SW|W)_(stand|walk)_spritesheet_4x4_o\.png",
)
LEGACY_SHEET_PATTERN = re.compile(
    r"greenhero_(w|wd|d|sd|s|sa|a|wa)_(stand|walk)_spritesheet_4x4_o\.png",
)
COMPASS_SHEET_PATTERN = re.compile(r"([a-z]+)_solo_4x4(?:_o)?\.png", re.IGNORECASE)
STILL_PATTERN = re.compile(r"greenhero_(N|NO|NW|O|S|SO|SW|W|w|wd|d|sd|s|sa|a|wa)_stand\.png")
POSE_PATTERN = re.compile(
    r"greenhero_(?:hd|test|ultra|pixel_art)_"
    r"(stand|walk|run|sneak|sprint|jump)_(N|NO|NW|O|S|SO|SW|W)"
    r"(_solo_4x4(?:_o)?)?\.png",
)
LAYOUT_FIELDS = (
    "columns", "rows", "frame_count", "frame_order", "frame_durations_ms",
    "loop", "height_pixels", "foot_anchor",
)


def _find_pose_sources(
    source_root: Path, *, include_action_folders: bool = True,
) -> dict[str, dict[str, tuple[Path, int]]]:
    """Prefer individual images over their matching grids, retaining folder overrides."""

    result: dict[str, dict[str, tuple[Path, int]]] = {}
    folders = [source_root]
    if include_action_folders:
        folders.extend(source_root / action for action in generator.TEST_ACTIONS)
    for folder in folders:
        if not folder.is_dir():
            continue
        selected: dict[tuple[str, str, int], Path] = {}
        for path in sorted(folder.iterdir()):
            match = POSE_PATTERN.fullmatch(path.name)
            if not path.is_file() or match is None:
                continue
            action, direction = match[1], match[2]
            grid = 4 if match[3] else 1
            key = (action, direction, grid)
            if key in selected:
                raise generator.AnimationPackageError(
                    f"ambiguous {action} direction {direction}: "
                    f"{selected[key].name}, {path.name}"
                )
            selected[key] = path
        for (action, direction, grid), path in selected.items():
            if grid == 4 and (action, direction, 1) in selected:
                continue
            result.setdefault(action, {})[direction] = (path, grid)
    return result


def _select_sources(
    package_root: Path, source_root: Path | None, action: str,
) -> tuple[dict[str, dict[str, tuple[Path, int]]], bool]:
    if source_root is None:
        sources = package_root / "sources"
        if _find_pose_sources(sources):
            source_root = sources
        else:
            has_loose_inputs = any(package_root.glob("*.png"))
            source_root = package_root if has_loose_inputs else sources
    source_root = source_root.resolve()
    poses = _find_pose_sources(
        source_root, include_action_folders=source_root != package_root,
    )
    if action == "all":
        actions = tuple(item for item in generator.TEST_ACTIONS if item in poses)
        actions = actions or generator.EXPECTED_ACTIONS
    else:
        actions = generator.EXPECTED_ACTIONS if action == "both" else (action,)
    if poses:
        for item in actions:
            missing = set(generator.EXPECTED_DIRECTIONS) - poses.get(item, {}).keys()
            if missing:
                raise generator.AnimationPackageError(
                    f"missing {item} poses for keys {', '.join(sorted(missing))}"
                )
        return {item: poses[item] for item in actions}, True
    return {
        item: {
            direction: (path, 4)
            for direction, path in _find_sources(
                source_root, item, include_action_folders=source_root != package_root,
            ).items()
        }
        for item in actions
    }, False


def _read_input(source: Path, grid: int) -> tuple[bytes, tuple[int, int]]:
    payload = source.read_bytes()
    png = generator._png_info(payload, source)
    if png.width % grid or png.height % grid:
        raise generator.AnimationPackageError(
            f"{source.name}: expected a complete {grid}x{grid} grid"
        )
    generator._expect_png_contract(png, (png.width, png.height), source)
    return payload, (png.width // grid, png.height // grid)


def _find_sources(
    source_root: Path,
    action: str,
    *,
    include_action_folders: bool = True,
) -> dict[str, Path]:
    result: dict[str, Path] = {}
    folders = (source_root, source_root / action) if include_action_folders else (source_root,)
    for folder in folders:
        if not folder.is_dir():
            continue
        selected: dict[str, Path] = {}
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix.lower() != ".png":
                continue
            canonical = SHEET_PATTERN.fullmatch(path.name)
            legacy = LEGACY_SHEET_PATTERN.fullmatch(path.name)
            compass = COMPASS_SHEET_PATTERN.fullmatch(path.name)
            if canonical is not None:
                if canonical[2] != action:
                    continue
                key = canonical[1]
            elif legacy is not None:
                if legacy[2] != action:
                    continue
                key = LEGACY_KEYS[legacy[1]]
            elif compass is not None:
                key = COMPASS_KEYS.get(compass[1].upper(), "")
            elif STILL_PATTERN.fullmatch(path.name):
                continue
            else:
                key = ""
            if not key:
                raise generator.AnimationPackageError(
                    f"unrecognized sheet {path.name}; use N_solo_4x4.png, "
                    "N_solo_4x4_o.png, or canonical names"
                )
            if key in selected:
                raise generator.AnimationPackageError(
                    f"ambiguous {action} direction {key}: {selected[key].name}, {path.name}"
                )
            selected[key] = path
        result.update(selected)
    missing = sorted(set(generator.EXPECTED_DIRECTIONS) - result.keys())
    if missing:
        raise generator.AnimationPackageError(
            f"missing {action} sheets for keys {', '.join(missing)}; "
            "provide all eight directions in sources or its action subfolder"
        )
    return result


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
        mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
        temporary_path.chmod(mode)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _commit_files(
    package_root: Path, staged_root: Path, paths: list[Path], removals: list[Path],
) -> None:
    originals: dict[Path, bytes | None] = {}
    for relative in paths + removals:
        destination = package_root / relative
        if not destination.resolve().is_relative_to(package_root):
            raise generator.AnimationPackageError(f"output escapes test package: {relative}")
        originals[relative] = destination.read_bytes() if destination.exists() else None
    written: list[Path] = []
    try:
        for relative in paths:
            _write_atomic(package_root / relative, (staged_root / relative).read_bytes())
            written.append(relative)
        for relative in removals:
            (package_root / relative).unlink()
            written.append(relative)
    except OSError:
        for relative in reversed(written):
            original = originals[relative]
            if original is None:
                (package_root / relative).unlink()
            else:
                _write_atomic(package_root / relative, original)
        raise


def _archive_replaced_images(
    package: generator.AnimationPackage,
    manifest: dict,
    package_root: Path,
    staged_root: Path,
) -> tuple[list[Path], list[Path]]:
    """Retain superseded runtime images as sources before removing old import sidecars."""

    current_paths = {raw["runtime_file"] for raw in manifest["animations"]}
    archives: list[Path] = []
    removals: list[Path] = []
    for spec in package.animations:
        relative = Path(spec.runtime_file)
        previous = package_root / relative
        if relative.as_posix() in current_paths or not previous.is_file():
            continue
        payload = previous.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        archive = Path("sources", "previous", digest, relative)
        (staged_root / archive).parent.mkdir(parents=True, exist_ok=True)
        (staged_root / archive).write_bytes(payload)
        archives.append(archive)
        removals.append(relative)
        sidecar = relative.with_suffix(relative.suffix + ".import")
        if (package_root / sidecar).is_file():
            removals.append(sidecar)
    return archives, removals


def prepare_test_package(
    package_root: Path = DEFAULT_PACKAGE_ROOT,
    *,
    source_root: Path | None = None,
    action: str = "all",
    dry_run: bool = False,
) -> tuple[str, ...]:
    """Validate a complete input batch before replacing test assets; preserve input files.

    Named pose batches in sources take precedence over loose legacy sheets in test.
    Runtime action folders are never read as input. Matching individual poses take
    precedence over their 4x4 grids and share the standing calibration. Legacy grids
    retain animated stand/walk import. Validation precedes all package writes.
    """

    if action not in ("all", "both", *generator.TEST_ACTIONS):
        raise generator.AnimationPackageError("unsupported test action")
    package_root = package_root.resolve()
    manifest_path = package_root / "stand_walk_manifest.json"
    package = generator.load_package(manifest_path)
    if package.variant != "test" or package_root.name != "test":
        raise generator.AnimationPackageError("only the test package may be replaced")
    sources, still_poses = _select_sources(package_root, source_root, action)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = {raw["name"]: raw for raw in manifest["animations"]}
    specs = {spec.name: spec for spec in package.animations}
    reference_spec = specs[package.reference_pose.animation]
    pose_canvas = reference_spec.source_canvas
    pose_height = package.reference_pose.height_pixels
    pose_anchor = package.reference_pose.foot_anchor
    if still_poses and reference_spec.action in sources:
        reference_source, reference_grid = sources[reference_spec.action][reference_spec.direction]
        _, pose_canvas = _read_input(reference_source, reference_grid)
        if pose_canvas != reference_spec.source_canvas:
            pose_height = pose_canvas[1]
            pose_anchor = (pose_canvas[0] // 2, pose_canvas[1])
    for name, raw in records.items():
        spec = specs[name]
        raw["source_canvas"] = list(spec.source_canvas)
        for field in LAYOUT_FIELDS:
            value = getattr(spec, field)
            raw[field] = list(value) if isinstance(value, tuple) else value
    messages: list[str] = []
    changed_paths: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="green-hero-test-") as temporary_directory:
        staged_root = Path(temporary_directory) / "test"
        shutil.copytree(package_root, staged_root)
        for item, directions in sources.items():
            for direction in generator.EXPECTED_DIRECTIONS:
                source, grid = directions[direction]
                payload, (width, height) = _read_input(source, grid)
                name = f"{item}_{direction}"
                raw = records.setdefault(name, {
                    "name": name, "action": item, "direction": direction, "source_key": direction,
                })
                if still_poses:
                    if (width, height) != pose_canvas:
                        raise generator.AnimationPackageError(
                            f"{source.name}: pose canvas must match {pose_canvas}"
                        )
                    raw.update(
                        source_canvas=list(pose_canvas), crop_rect=[0, 0, width, height],
                        height_pixels=pose_height, foot_anchor=list(pose_anchor),
                    )
                elif name not in specs or (width, height) != specs[name].crop_rect[2:]:
                    raw.update(
                        source_canvas=[width, height], crop_rect=[0, 0, width, height],
                        height_pixels=height, foot_anchor=[width // 2, height],
                    )
                    messages.append(f"{name}: aligned {width} x {height} cell at bottom center")
                frame_count = 1 if still_poses else 16
                raw.update(
                    columns=grid, rows=grid, frame_count=frame_count,
                    frame_order=list(range(frame_count)),
                    frame_durations_ms=[120] * frame_count, loop=not still_poses,
                )
                suffix = "" if grid == 1 else "_spritesheet_4x4_o"
                runtime_path = Path(item, f"greenhero_{direction}_{item}{suffix}.png")
                imported_path = Path("sources", "imported", item, runtime_path.name)
                digest = hashlib.sha256(payload).hexdigest()
                raw["runtime_file"] = runtime_path.as_posix()
                raw["source"] = {
                    "optimized": [runtime_path.as_posix(), digest],
                    "input_sheet": [imported_path.as_posix(), digest],
                }
                for relative in (runtime_path, imported_path):
                    destination = staged_root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(payload)
                    changed_paths.append(relative)
                messages.append(f"{source.name} -> {runtime_path.as_posix()}")

        manifest["actions"] = [
            item for item in generator.TEST_ACTIONS if item in set(package.actions) | sources.keys()
        ]
        manifest["animations"] = [
            records[f"{item}_{direction}"]
            for item in manifest["actions"] for direction in generator.EXPECTED_DIRECTIONS
        ]
        reference = records[package.reference_pose.animation]
        manifest["source_canvas"] = reference["source_canvas"]
        if reference["source_canvas"] != list(reference_spec.source_canvas):
            manifest["reference_pose"].update(
                alpha_bounds=reference["crop_rect"],
                height_pixels=reference["height_pixels"],
                foot_anchor=reference["foot_anchor"],
            )
        manifest["defaults"] = {field: reference[field] for field in LAYOUT_FIELDS}
        for raw in manifest["animations"]:
            for field, value in manifest["defaults"].items():
                if raw[field] == value:
                    raw.pop(field)
        archives, removals = _archive_replaced_images(
            package, manifest, package_root, staged_root,
        )
        staged_manifest = staged_root / manifest_path.name
        staged_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        prepared = generator.load_package(staged_manifest)
        generator.validate_runtime_assets(prepared, staged_root)
        resource_path = Path(prepared.resource_file)
        (staged_root / resource_path).write_text(
            generator.generate_resource(prepared), encoding="utf-8", newline="\n",
        )
        if not dry_run:
            _commit_files(
                package_root, staged_root,
                changed_paths + archives + [resource_path, Path(manifest_path.name)], removals,
            )
    return tuple(messages)


def main() -> int:
    """Run the test-only batch import from the portable shell entry point."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, help="read another input folder")
    parser.add_argument(
        "--action", choices=("all", "both", *generator.TEST_ACTIONS), default="all",
        help="import all detected poses, stand/walk together, or one named action",
    )
    parser.add_argument("--dry-run", action="store_true", help="validate without replacing files")
    arguments = parser.parse_args()
    try:
        messages = prepare_test_package(
            source_root=arguments.source_dir,
            action=arguments.action,
            dry_run=arguments.dry_run,
        )
        for message in messages:
            print(message)
        print("Test package validated." if arguments.dry_run else "Test package ready for Godot.")
        return 0
    except (generator.AnimationPackageError, OSError) as exc:
        print(f"Test import failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
