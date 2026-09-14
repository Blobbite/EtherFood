#!/usr/bin/env python3
"""Validate and generate the Green Hero stand/walk animation package.

The committed manifest is the only generation input for Ultra, HD, and Test.
Packages may contain local sheets or reference stills. An optional working-source
root verifies and synchronizes animated PNGs when reference sheets and timing
GIFs are declared. ``--check`` never writes and verifies both runtime inputs
and the generated Godot resource.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import struct
import sys
import zlib
from dataclasses import dataclass
from functools import reduce
from pathlib import Path, PurePosixPath
from typing import cast


GAME_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    GAME_ROOT
    / "tests"
    / "assets"
    / "characters"
    / "heroes"
    / "green_hero"
    / "ultra"
    / "stand_walk_manifest.json"
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_DIRECTIONS = ("N", "NO", "O", "SO", "S", "SW", "W", "NW")
EXPECTED_ACTIONS = ("stand", "walk")
TEST_ACTIONS = ("stand", "walk", "run", "sneak", "sprint", "jump")
EXPECTED_SOURCE_DIRECTORIES = {
    "stand": "0stand",
    "walk": "1walk",
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class AnimationPackageError(ValueError):
    """Report one actionable manifest, source, or generation failure."""


@dataclass(frozen=True, slots=True)
class FileRecord:
    """Describe one immutable audited working-source file."""

    relative_path: PurePosixPath
    sha256: str


@dataclass(frozen=True, slots=True)
class AnimationSpec:
    """Contain all resolved data for one directional animation."""

    name: str
    action: str
    direction: str
    source_key: str
    runtime_file: PurePosixPath
    source_canvas: tuple[int, int]
    height_pixels: int
    foot_anchor: tuple[int, int]
    crop_rect: tuple[int, int, int, int]
    columns: int
    rows: int
    frame_count: int
    frame_order: tuple[int, ...]
    frame_durations_ms: tuple[int, ...]
    loop: bool
    optimized_source: FileRecord
    reference_sheet: FileRecord | None
    timing_gif: FileRecord | None
    reference_image: FileRecord | None
    input_sheet: FileRecord | None


@dataclass(frozen=True, slots=True)
class ReferencePose:
    """Define the stable pixel-to-world scale and visual foot anchor."""

    animation: str
    frame: int
    alpha_bounds: tuple[int, int, int, int]
    foot_anchor: tuple[int, int]
    height_pixels: int
    world_height: int


@dataclass(frozen=True, slots=True)
class AnimationPackage:
    """Contain the validated Green Hero animation package."""

    package_id: str
    variant: str
    actions: tuple[str, ...]
    resource_file: PurePosixPath
    resource_root: str
    source_canvas: tuple[int, int]
    reference_pose: ReferencePose
    animations: tuple[AnimationSpec, ...]


@dataclass(frozen=True, slots=True)
class PngInfo:
    """Expose the import-relevant properties of one PNG."""

    width: int
    height: int
    bit_depth: int
    color_type: int
    interlace_method: int


@dataclass(frozen=True, slots=True)
class GifInfo:
    """Expose canvas, frame delays, and repetition from one timing GIF."""

    width: int
    height: int
    delays_cs: tuple[int, ...]
    loop_count: int | None


def load_package(manifest_path: Path = DEFAULT_MANIFEST) -> AnimationPackage:
    """Load and strictly validate one animation package manifest."""

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AnimationPackageError(f"cannot read manifest {manifest_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AnimationPackageError(f"invalid JSON in {manifest_path}: {exc}") from exc

    manifest = _mapping(raw, "manifest")
    if _integer(manifest.get("schema_version"), "schema_version") != 1:
        raise AnimationPackageError("schema_version must be 1")
    package_id = _identifier(manifest.get("package_id"), "package_id")
    variant = _identifier(manifest.get("variant"), "variant")
    if variant not in ("ultra", "hd", "test"):
        raise AnimationPackageError("variant must be 'ultra', 'hd', or 'test'")
    actions = tuple(
        _identifier(value, "actions[]")
        for value in _list(manifest.get("actions", list(EXPECTED_ACTIONS)), "actions")
    )
    allowed_actions = TEST_ACTIONS if variant == "test" else EXPECTED_ACTIONS
    if (
        len(set(actions)) != len(actions)
        or not set(EXPECTED_ACTIONS).issubset(actions)
        or not set(actions).issubset(allowed_actions)
    ):
        raise AnimationPackageError("actions require stand/walk and supported variant actions")
    resource_file = _relative_path(manifest.get("resource_file"), "resource_file")
    if resource_file.name != f"{package_id}.tres" or len(resource_file.parts) != 1:
        raise AnimationPackageError("resource_file must match package_id at the package root")
    resource_root = _string(manifest.get("resource_root"), "resource_root")
    if not resource_root.startswith("res://") or ".." in PurePosixPath(resource_root).parts:
        raise AnimationPackageError("resource_root must be a safe res:// path")
    source_canvas = _integer_tuple(
        manifest.get("source_canvas"),
        "source_canvas",
        2,
        positive=True,
    )
    defaults = _mapping(manifest.get("defaults"), "defaults")
    reference_pose = _parse_reference_pose(manifest.get("reference_pose"), source_canvas)

    animation_values = _list(manifest.get("animations"), "animations")
    animations = tuple(
        _parse_animation(value, defaults, source_canvas, index)
        for index, value in enumerate(animation_values)
    )
    _validate_package_contract(animations, reference_pose, actions, variant)
    return AnimationPackage(
        package_id=package_id,
        variant=variant,
        actions=actions,
        resource_file=resource_file,
        resource_root=resource_root.rstrip("/"),
        source_canvas=source_canvas,
        reference_pose=reference_pose,
        animations=animations,
    )


def generate_resource(package: AnimationPackage) -> str:
    """Return the deterministic Godot SpriteFrames resource text."""

    frame_total = sum(animation.frame_count for animation in package.animations)
    load_steps = len(package.animations) + frame_total + 1
    lines = [
        (
            f'[gd_resource type="SpriteFrames" load_steps={load_steps} '
            "format=3]"
        ),
        "",
    ]
    resource_ids: dict[str, str] = {}
    for index, animation in enumerate(package.animations, start=1):
        resource_id = f"{index}_{animation.action}_{animation.direction}"
        resource_ids[animation.name] = resource_id
        resource_path = f"{package.resource_root}/{animation.runtime_file.as_posix()}"
        lines.append(
            f'[ext_resource type="Texture2D" path="{resource_path}" '
            f'id="{resource_id}"]'
        )
    lines.append("")

    subresource_ids: dict[tuple[str, int], str] = {}
    for animation in package.animations:
        canvas_width, canvas_height = animation.source_canvas
        crop_x, crop_y, frame_width, frame_height = animation.crop_rect
        margin_width = canvas_width - frame_width
        margin_height = canvas_height - frame_height
        for output_index, source_index in enumerate(animation.frame_order):
            column = source_index % animation.columns
            row = source_index // animation.columns
            subresource_id = f"AtlasTexture_{animation.name}_{output_index:02d}"
            subresource_ids[(animation.name, output_index)] = subresource_id
            lines.extend(
                [
                    (
                        f'[sub_resource type="AtlasTexture" '
                        f'id="{subresource_id}"]'
                    ),
                    f'atlas = ExtResource("{resource_ids[animation.name]}")',
                    (
                        "region = Rect2("
                        f"{column * frame_width}, {row * frame_height}, "
                        f"{frame_width}, {frame_height})"
                    ),
                    (
                        "margin = Rect2("
                        f"{crop_x}, {crop_y}, {margin_width}, {margin_height})"
                    ),
                    "filter_clip = true",
                    "",
                ]
            )

    lines.extend(["[resource]", "animations = ["])
    for animation_index, animation in enumerate(package.animations):
        timing_unit = reduce(math.gcd, animation.frame_durations_ms)
        speed = 1000.0 / timing_unit
        lines.extend(['{', '"frames": ['])
        for frame_index, duration_ms in enumerate(animation.frame_durations_ms):
            relative_duration = duration_ms / timing_unit
            lines.extend(
                [
                    "{",
                    f'"duration": {_godot_float(relative_duration)},',
                    (
                        '"texture": SubResource('
                        f'"{subresource_ids[(animation.name, frame_index)]}")'
                    ),
                    "}" + ("," if frame_index + 1 < animation.frame_count else ""),
                ]
            )
        lines.extend(
            [
                "],",
                f'"loop": {str(animation.loop).lower()},',
                f'"name": &"{animation.name}",',
                f'"speed": {_godot_float(speed)}',
                "}" + ("," if animation_index + 1 < len(package.animations) else ""),
            ]
        )
    lines.extend(["]", "metadata/animation_layouts = {"])
    for index, animation in enumerate(package.animations):
        scale = _godot_float(package.reference_pose.world_height / animation.height_pixels)
        offset_x = _godot_float(animation.source_canvas[0] / 2 - animation.foot_anchor[0])
        offset_y = _godot_float(animation.source_canvas[1] / 2 - animation.foot_anchor[1])
        lines.append(
            f'&"{animation.name}": {{"scale": Vector2({scale}, {scale}), '
            f'"offset": Vector2({offset_x}, {offset_y})}}'
            + ("," if index + 1 < len(package.animations) else "")
        )
    lines.extend(["}", ""])
    return "\n".join(lines)


def synchronize_sources(
    package: AnimationPackage,
    package_root: Path,
    source_root: Path,
    *,
    check: bool,
) -> tuple[PurePosixPath, ...]:
    """Verify working sources and copy only audited optimized PNGs when allowed."""

    source_root = source_root.resolve()
    _validate_working_sources(package, package_root, source_root)
    changed: list[PurePosixPath] = []
    for animation in package.animations:
        root = (
            package_root
            if animation.reference_image is not None or animation.input_sheet is not None
            else source_root
        )
        source = _joined_path(root, animation.optimized_source.relative_path)
        destination = _joined_path(package_root, animation.runtime_file)
        if destination.is_file() and _sha256(destination) == animation.optimized_source.sha256:
            continue
        changed.append(animation.runtime_file)
        if check:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return tuple(changed)


def validate_runtime_assets(
    package: AnimationPackage,
    package_root: Path,
) -> None:
    """Verify committed runtime PNG identity, format, and manifest dimensions."""

    for animation in package.animations:
        runtime_path = _joined_path(package_root, animation.runtime_file)
        payload = _verified_payload(
            runtime_path,
            animation.optimized_source.sha256,
            f"runtime asset for {animation.name}",
        )
        png = _png_info(payload, runtime_path)
        expected_size = (
            animation.columns * animation.crop_rect[2],
            animation.rows * animation.crop_rect[3],
        )
        _expect_png_contract(png, expected_size, runtime_path)
        if animation.input_sheet is not None:
            _verified_payload(
                _joined_path(package_root, animation.input_sheet.relative_path),
                animation.input_sheet.sha256,
                f"input sheet for {animation.name}",
            )
        if animation.reference_image is not None:
            reference_path = _joined_path(package_root, animation.reference_image.relative_path)
            reference_payload = _verified_payload(
                reference_path,
                animation.reference_image.sha256,
                f"reference image for {animation.name}",
            )
            _expect_png_contract(
                _png_info(reference_payload, reference_path),
                animation.source_canvas,
                reference_path,
            )


def _parse_reference_pose(
    value: object,
    source_canvas: tuple[int, int],
) -> ReferencePose:
    raw = _mapping(value, "reference_pose")
    pose = ReferencePose(
        animation=_animation_name(raw.get("animation"), "reference_pose.animation"),
        frame=_nonnegative_integer(raw.get("frame"), "reference_pose.frame"),
        alpha_bounds=_integer_tuple(
            raw.get("alpha_bounds"),
            "reference_pose.alpha_bounds",
            4,
            nonnegative=True,
        ),
        foot_anchor=_integer_tuple(
            raw.get("foot_anchor"),
            "reference_pose.foot_anchor",
            2,
            nonnegative=True,
        ),
        height_pixels=_positive_integer(
            raw.get("height_pixels"),
            "reference_pose.height_pixels",
        ),
        world_height=_positive_integer(
            raw.get("world_height"),
            "reference_pose.world_height",
        ),
    )
    bound_x, bound_y, bound_width, bound_height = pose.alpha_bounds
    canvas_width, canvas_height = source_canvas
    if bound_height != pose.height_pixels:
        raise AnimationPackageError("reference pose height must match alpha-bounds height")
    if bound_x + bound_width > canvas_width or bound_y + bound_height > canvas_height:
        raise AnimationPackageError("reference pose alpha bounds exceed source_canvas")
    if pose.foot_anchor[0] > canvas_width or pose.foot_anchor[1] > canvas_height:
        raise AnimationPackageError("reference pose foot anchor exceeds source_canvas")
    return pose


def _parse_animation(
    value: object,
    defaults: dict[str, object],
    source_canvas: tuple[int, int],
    index: int,
) -> AnimationSpec:
    label = f"animations[{index}]"
    raw = _mapping(value, label)
    source_canvas = _integer_tuple(
        raw.get("source_canvas", list(source_canvas)),
        f"{label}.source_canvas",
        2,
        positive=True,
    )
    height_pixels = _positive_integer(
        _resolved(raw, defaults, "height_pixels"),
        f"{label}.height_pixels",
    )
    foot_anchor = _integer_tuple(
        _resolved(raw, defaults, "foot_anchor"),
        f"{label}.foot_anchor",
        2,
        nonnegative=True,
    )
    if height_pixels > source_canvas[1] or any(
        anchor > size for anchor, size in zip(foot_anchor, source_canvas)
    ):
        raise AnimationPackageError(f"{label}: visual reference exceeds source canvas")
    columns = _positive_integer(_resolved(raw, defaults, "columns"), f"{label}.columns")
    rows = _positive_integer(_resolved(raw, defaults, "rows"), f"{label}.rows")
    frame_count = _positive_integer(
        _resolved(raw, defaults, "frame_count"),
        f"{label}.frame_count",
    )
    frame_order = _integer_tuple(
        _resolved(raw, defaults, "frame_order"),
        f"{label}.frame_order",
        frame_count,
        nonnegative=True,
    )
    durations = _integer_tuple(
        _resolved(raw, defaults, "frame_durations_ms"),
        f"{label}.frame_durations_ms",
        frame_count,
        positive=True,
    )
    crop_rect = _integer_tuple(
        raw.get("crop_rect"),
        f"{label}.crop_rect",
        4,
        nonnegative=True,
    )
    if crop_rect[2] <= 0 or crop_rect[3] <= 0:
        raise AnimationPackageError(f"{label}.crop_rect needs positive width and height")
    if crop_rect[0] + crop_rect[2] > source_canvas[0]:
        raise AnimationPackageError(f"{label}.crop_rect exceeds source canvas width")
    if crop_rect[1] + crop_rect[3] > source_canvas[1]:
        raise AnimationPackageError(f"{label}.crop_rect exceeds source canvas height")
    if len(set(frame_order)) != frame_count:
        raise AnimationPackageError(f"{label}.frame_order must contain unique indices")
    if max(frame_order) >= columns * rows:
        raise AnimationPackageError(f"{label}.frame_order exceeds its grid")

    source = _mapping(raw.get("source"), f"{label}.source")
    return AnimationSpec(
        name=_animation_name(raw.get("name"), f"{label}.name"),
        action=_identifier(raw.get("action"), f"{label}.action"),
        direction=_compass_direction(raw.get("direction"), f"{label}.direction"),
        source_key=_compass_direction(raw.get("source_key"), f"{label}.source_key"),
        runtime_file=_relative_path(raw.get("runtime_file"), f"{label}.runtime_file"),
        source_canvas=source_canvas,
        height_pixels=height_pixels,
        foot_anchor=foot_anchor,
        crop_rect=crop_rect,
        columns=columns,
        rows=rows,
        frame_count=frame_count,
        frame_order=frame_order,
        frame_durations_ms=durations,
        loop=_boolean(_resolved(raw, defaults, "loop"), f"{label}.loop"),
        optimized_source=_file_record(source.get("optimized"), f"{label}.source.optimized"),
        reference_sheet=(
            _file_record(source["reference_sheet"], f"{label}.source.reference_sheet")
            if "reference_sheet" in source else None
        ),
        timing_gif=(
            _file_record(source["timing_gif"], f"{label}.source.timing_gif")
            if "timing_gif" in source else None
        ),
        reference_image=(
            _file_record(source["reference_image"], f"{label}.source.reference_image")
            if "reference_image" in source else None
        ),
        input_sheet=(
            _file_record(source["input_sheet"], f"{label}.source.input_sheet")
            if "input_sheet" in source else None
        ),
    )


def _validate_package_contract(
    animations: tuple[AnimationSpec, ...],
    reference_pose: ReferencePose,
    actions: tuple[str, ...],
    variant: str,
) -> None:
    expected_names = {
        f"{action}_{direction}"
        for action in actions
        for direction in EXPECTED_DIRECTIONS
    }
    actual_names = {animation.name for animation in animations}
    if len(animations) != len(expected_names) or actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        unexpected = sorted(actual_names - expected_names)
        raise AnimationPackageError(
            f"animations must contain all {len(expected_names)} declared action/direction pairs; "
            f"missing={missing}, unexpected={unexpected}"
        )
    if len(actual_names) != len(animations):
        raise AnimationPackageError("animation names must be unique")

    for animation in animations:
        if animation.action not in actions:
            raise AnimationPackageError(f"unsupported action for {animation.name}")
        if animation.direction not in EXPECTED_DIRECTIONS:
            raise AnimationPackageError(f"unsupported direction for {animation.name}")
        expected_key = animation.direction
        if animation.name != f"{animation.action}_{animation.direction}":
            raise AnimationPackageError(f"animation name does not match {animation.name}")
        if animation.source_key != expected_key:
            raise AnimationPackageError(f"wrong source_key for {animation.name}")
        source_stem = f"greenhero_{expected_key}_{animation.action}"
        grid_suffix = f"{animation.columns}x{animation.rows}"
        expected_filename = (
            f"{source_stem}_spritesheet_{grid_suffix}_o.png"
        )
        if variant == "test" and (animation.columns, animation.rows) == (1, 1):
            expected_filename = f"{source_stem}.png"
        if animation.runtime_file != PurePosixPath(animation.action, expected_filename):
            raise AnimationPackageError(f"wrong runtime_file for {animation.name}")
        if animation.input_sheet is not None:
            if any((animation.reference_image, animation.reference_sheet, animation.timing_gif)):
                raise AnimationPackageError(f"ambiguous sheet sources for {animation.name}")
            if animation.optimized_source.relative_path != animation.runtime_file:
                raise AnimationPackageError(f"wrong optimized path for {animation.name}")
            if animation.input_sheet.relative_path.parts[0] != "sources":
                raise AnimationPackageError(f"input_sheet must be in sources for {animation.name}")
            if animation.input_sheet.sha256 != animation.optimized_source.sha256:
                raise AnimationPackageError(f"input_sheet hash differs for {animation.name}")
            continue
        if animation.reference_image is not None:
            if animation.reference_sheet is not None or animation.timing_gif is not None:
                raise AnimationPackageError(f"invalid still-image sources for {animation.name}")
            if animation.optimized_source.relative_path != animation.runtime_file:
                raise AnimationPackageError(f"wrong optimized path for {animation.name}")
            if animation.reference_image.relative_path != PurePosixPath(
                "sources", "stand", f"greenhero_{expected_key}_stand.png",
            ):
                raise AnimationPackageError(f"wrong reference_image path for {animation.name}")
            continue
        if animation.reference_sheet is None or animation.timing_gif is None:
            raise AnimationPackageError(f"missing animation sources for {animation.name}")
        if animation.action not in EXPECTED_SOURCE_DIRECTORIES:
            raise AnimationPackageError(f"{animation.name} requires local input_sheet sources")
        expected_source_root = PurePosixPath(
            EXPECTED_SOURCE_DIRECTORIES[animation.action],
            source_stem,
        )
        expected_sources = {
            "optimized": expected_source_root / expected_filename,
            "reference_sheet": expected_source_root / f"{source_stem}_spritesheet.png",
            "timing_gif": expected_source_root / f"{source_stem}.gif",
        }
        actual_sources = {
            "optimized": animation.optimized_source.relative_path,
            "reference_sheet": animation.reference_sheet.relative_path,
            "timing_gif": animation.timing_gif.relative_path,
        }
        for source_kind, expected_path in expected_sources.items():
            if actual_sources[source_kind] != expected_path:
                raise AnimationPackageError(
                    f"wrong {source_kind} path for {animation.name}"
                )
    matching_references = [
        animation
        for animation in animations
        if animation.name == reference_pose.animation
    ]
    if len(matching_references) != 1:
        raise AnimationPackageError(
            "reference pose animation must name one package animation"
        )
    reference = matching_references[0]
    if reference_pose.frame >= reference.frame_count:
        raise AnimationPackageError("reference pose frame exceeds its animation")


def _validate_working_sources(
    package: AnimationPackage,
    package_root: Path,
    source_root: Path,
) -> None:
    for animation in package.animations:
        if animation.input_sheet is not None:
            _verified_payload(
                _joined_path(package_root, animation.input_sheet.relative_path),
                animation.input_sheet.sha256,
                f"input sheet for {animation.name}",
            )
            continue
        if animation.reference_image is not None:
            # These reviewed still sheets already live in the committed package.
            # Animated sources, when declared, are synchronized from an external root.
            reference_path = _joined_path(package_root, animation.reference_image.relative_path)
            _verified_payload(
                reference_path,
                animation.reference_image.sha256,
                f"reference image for {animation.name}",
            )
            _verified_payload(
                _joined_path(package_root, animation.optimized_source.relative_path),
                animation.optimized_source.sha256,
                f"optimized source for {animation.name}",
            )
            continue
        if animation.reference_sheet is None or animation.timing_gif is None:
            raise AnimationPackageError(f"missing animation sources for {animation.name}")
        canvas_width, canvas_height = animation.source_canvas
        optimized_path = _joined_path(
            source_root,
            animation.optimized_source.relative_path,
        )
        optimized_payload = _verified_payload(
            optimized_path,
            animation.optimized_source.sha256,
            f"optimized source for {animation.name}",
        )
        expected_optimized_size = (
            animation.columns * animation.crop_rect[2],
            animation.rows * animation.crop_rect[3],
        )
        _expect_png_contract(
            _png_info(optimized_payload, optimized_path),
            expected_optimized_size,
            optimized_path,
        )

        reference_path = _joined_path(source_root, animation.reference_sheet.relative_path)
        reference_payload = _verified_payload(
            reference_path,
            animation.reference_sheet.sha256,
            f"reference sheet for {animation.name}",
        )
        _expect_png_contract(
            _png_info(reference_payload, reference_path),
            (canvas_width * animation.frame_count, canvas_height),
            reference_path,
        )

        gif_path = _joined_path(source_root, animation.timing_gif.relative_path)
        gif_payload = _verified_payload(
            gif_path,
            animation.timing_gif.sha256,
            f"timing GIF for {animation.name}",
        )
        gif = _gif_info(gif_payload, gif_path)
        expected_delays = tuple(duration // 10 for duration in animation.frame_durations_ms)
        if any(duration % 10 != 0 for duration in animation.frame_durations_ms):
            raise AnimationPackageError(f"{animation.name}: GIF timing needs 10 ms units")
        if (gif.width, gif.height) != animation.source_canvas:
            raise AnimationPackageError(f"{gif_path}: GIF canvas does not match manifest")
        if gif.delays_cs != expected_delays:
            raise AnimationPackageError(f"{gif_path}: GIF frame timing does not match manifest")
        if gif.loop_count != 0:
            raise AnimationPackageError(f"{gif_path}: GIF must loop indefinitely")


def _expect_png_contract(png: PngInfo, size: tuple[int, int], path: Path) -> None:
    if (png.width, png.height) != size:
        raise AnimationPackageError(
            f"{path}: expected PNG size {size[0]}x{size[1]}, "
            f"got {png.width}x{png.height}"
        )
    if png.bit_depth != 8 or png.color_type != 6 or png.interlace_method != 0:
        raise AnimationPackageError(f"{path}: expected non-interlaced 8-bit RGBA PNG")


def _png_info(payload: bytes, path: Path) -> PngInfo:
    if not payload.startswith(PNG_SIGNATURE):
        raise AnimationPackageError(f"{path}: invalid PNG signature")
    offset = len(PNG_SIGNATURE)
    info: PngInfo | None = None
    found_end = False
    while offset < len(payload):
        if offset + 12 > len(payload):
            raise AnimationPackageError(f"{path}: truncated PNG chunk")
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        chunk_type = payload[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(payload):
            raise AnimationPackageError(f"{path}: PNG chunk exceeds file size")
        chunk_data = payload[offset + 8 : offset + 8 + length]
        stored_crc = struct.unpack(">I", payload[offset + 8 + length : chunk_end])[0]
        actual_crc = zlib.crc32(chunk_type)
        actual_crc = zlib.crc32(chunk_data, actual_crc) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            raise AnimationPackageError(f"{path}: invalid PNG chunk checksum")
        if chunk_type == b"IHDR":
            if info is not None or length != 13:
                raise AnimationPackageError(f"{path}: invalid PNG header")
            width, height, bit_depth, color_type, compression, filtering, interlace = (
                struct.unpack(">IIBBBBB", chunk_data)
            )
            if compression != 0 or filtering != 0:
                raise AnimationPackageError(f"{path}: unsupported PNG encoding")
            info = PngInfo(width, height, bit_depth, color_type, interlace)
        if chunk_type == b"IEND":
            if length != 0 or chunk_end != len(payload):
                raise AnimationPackageError(f"{path}: invalid PNG end chunk")
            found_end = True
            break
        offset = chunk_end
    if info is None or not found_end:
        raise AnimationPackageError(f"{path}: incomplete PNG")
    return info


def _gif_info(payload: bytes, path: Path) -> GifInfo:
    if len(payload) < 13 or payload[:6] not in (b"GIF87a", b"GIF89a"):
        raise AnimationPackageError(f"{path}: invalid GIF header")
    width, height, packed = struct.unpack("<HHB", payload[6:11])
    offset = 13
    if packed & 0x80:
        offset += 3 * (2 ** ((packed & 0x07) + 1))
    delays: list[int] = []
    pending_delay: int | None = None
    loop_count: int | None = None
    while offset < len(payload):
        marker = payload[offset]
        if marker == 0x3B:
            break
        if marker == 0x21:
            if offset + 2 >= len(payload):
                raise AnimationPackageError(f"{path}: truncated GIF extension")
            label = payload[offset + 1]
            if label == 0xF9:
                if offset + 8 > len(payload) or payload[offset + 2] != 4:
                    raise AnimationPackageError(f"{path}: invalid GIF frame control")
                pending_delay = struct.unpack("<H", payload[offset + 4 : offset + 6])[0]
                if payload[offset + 7] != 0:
                    raise AnimationPackageError(f"{path}: invalid GIF control terminator")
                offset += 8
                continue
            if label == 0xFF:
                loop_count, offset = _read_gif_application_extension(
                    payload,
                    offset,
                    loop_count,
                    path,
                )
                continue
            offset = _skip_gif_blocks(payload, offset + 2, path)
            continue
        if marker == 0x2C:
            if offset + 10 > len(payload):
                raise AnimationPackageError(f"{path}: truncated GIF image descriptor")
            local_packed = payload[offset + 9]
            offset += 10
            if local_packed & 0x80:
                offset += 3 * (2 ** ((local_packed & 0x07) + 1))
            if offset >= len(payload):
                raise AnimationPackageError(f"{path}: missing GIF image data")
            offset = _skip_gif_blocks(payload, offset + 1, path)
            delays.append(0 if pending_delay is None else pending_delay)
            pending_delay = None
            continue
        raise AnimationPackageError(f"{path}: unexpected GIF marker 0x{marker:02x}")
    if not delays:
        raise AnimationPackageError(f"{path}: GIF contains no frames")
    return GifInfo(width, height, tuple(delays), loop_count)


def _read_gif_application_extension(
    payload: bytes,
    offset: int,
    loop_count: int | None,
    path: Path,
) -> tuple[int | None, int]:
    block_size_offset = offset + 2
    if block_size_offset >= len(payload):
        raise AnimationPackageError(f"{path}: truncated GIF application extension")
    block_size = payload[block_size_offset]
    identifier_start = block_size_offset + 1
    identifier_end = identifier_start + block_size
    if identifier_end > len(payload):
        raise AnimationPackageError(f"{path}: invalid GIF application identifier")
    identifier = payload[identifier_start:identifier_end]
    data, next_offset = _read_gif_blocks(payload, identifier_end, path)
    if identifier in (b"NETSCAPE2.0", b"ANIMEXTS1.0") and len(data) >= 3:
        if data[0] == 1:
            loop_count = struct.unpack("<H", data[1:3])[0]
    return loop_count, next_offset


def _skip_gif_blocks(payload: bytes, offset: int, path: Path) -> int:
    _, next_offset = _read_gif_blocks(payload, offset, path)
    return next_offset


def _read_gif_blocks(payload: bytes, offset: int, path: Path) -> tuple[bytes, int]:
    blocks = bytearray()
    while True:
        if offset >= len(payload):
            raise AnimationPackageError(f"{path}: truncated GIF data blocks")
        size = payload[offset]
        offset += 1
        if size == 0:
            return bytes(blocks), offset
        if offset + size > len(payload):
            raise AnimationPackageError(f"{path}: GIF data block exceeds file size")
        blocks.extend(payload[offset : offset + size])
        offset += size


def _verified_payload(path: Path, expected_hash: str, label: str) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise AnimationPackageError(f"{label} is unavailable at {path}: {exc}") from exc
    actual_hash = hashlib.sha256(payload).hexdigest()
    if actual_hash != expected_hash:
        raise AnimationPackageError(
            f"{label} has SHA-256 {actual_hash}, expected {expected_hash}: {path}"
        )
    return payload


def _sha256(path: Path) -> str:
    try:
        with path.open("rb") as source:
            digest = hashlib.sha256()
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise AnimationPackageError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _joined_path(root: Path, relative_path: PurePosixPath) -> Path:
    resolved_root = root.resolve()
    path = resolved_root.joinpath(*relative_path.parts).resolve()
    try:
        path.relative_to(resolved_root)
    except ValueError as exc:
        raise AnimationPackageError(f"path escapes its root: {relative_path}") from exc
    return path


def _file_record(value: object, label: str) -> FileRecord:
    fields = _list(value, label)
    if len(fields) != 2:
        raise AnimationPackageError(f"{label} must contain path and SHA-256")
    relative_path = _relative_path(fields[0], f"{label}[0]")
    digest = _string(fields[1], f"{label}[1]")
    if SHA256_PATTERN.fullmatch(digest) is None:
        raise AnimationPackageError(f"{label}[1] must be a lowercase SHA-256")
    return FileRecord(relative_path, digest)


def _relative_path(value: object, label: str) -> PurePosixPath:
    raw = _string(value, label)
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise AnimationPackageError(f"{label} must be a safe relative POSIX path")
    return path


def _resolved(
    values: dict[str, object],
    defaults: dict[str, object],
    key: str,
) -> object:
    if key in values:
        return values[key]
    if key in defaults:
        return defaults[key]
    raise AnimationPackageError(f"missing animation value and default: {key}")


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise AnimationPackageError(f"{label} must be an object with string keys")
    return cast(dict[str, object], value)


def _list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise AnimationPackageError(f"{label} must be an array")
    return cast(list[object], value)


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AnimationPackageError(f"{label} must be a non-empty string")
    return value


def _compass_direction(value: object, label: str) -> str:
    direction = _string(value, label)
    if direction not in EXPECTED_DIRECTIONS:
        raise AnimationPackageError(f"{label} must be one of N, NO, NW, O, S, SO, SW, W")
    return direction


def _animation_name(value: object, label: str) -> str:
    name = _string(value, label)
    if re.fullmatch(r"(stand|walk|run|sneak|sprint|jump)_(N|NO|NW|O|S|SO|SW|W)", name) is None:
        raise AnimationPackageError(
            f"{label} must combine a supported action and a German compass direction"
        )
    return name


def _identifier(value: object, label: str) -> str:
    identifier = _string(value, label)
    if re.fullmatch(r"[a-z][a-z0-9_]*", identifier) is None:
        raise AnimationPackageError(f"{label} must be a lower_snake_case identifier")
    return identifier


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AnimationPackageError(f"{label} must be an integer")
    return value


def _positive_integer(value: object, label: str) -> int:
    number = _integer(value, label)
    if number <= 0:
        raise AnimationPackageError(f"{label} must be positive")
    return number


def _nonnegative_integer(value: object, label: str) -> int:
    number = _integer(value, label)
    if number < 0:
        raise AnimationPackageError(f"{label} must be nonnegative")
    return number


def _integer_tuple(
    value: object,
    label: str,
    length: int,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> tuple[int, ...]:
    values = _list(value, label)
    if len(values) != length:
        raise AnimationPackageError(f"{label} must contain exactly {length} integers")
    numbers = tuple(_integer(item, f"{label}[{index}]") for index, item in enumerate(values))
    if positive and any(number <= 0 for number in numbers):
        raise AnimationPackageError(f"{label} must contain only positive integers")
    if nonnegative and any(number < 0 for number in numbers):
        raise AnimationPackageError(f"{label} must contain only nonnegative integers")
    return numbers


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise AnimationPackageError(f"{label} must be a boolean")
    return value


def _godot_float(value: float) -> str:
    rendered = format(value, ".12g")
    if "." not in rendered and "e" not in rendered.lower():
        rendered += ".0"
    return rendered


def main() -> int:
    """Run source synchronization, validation, generation, or read-only checks."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="use a different package manifest",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        help="verify the local Animatzion root and synchronize audited PNGs",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify runtime assets and generated resource without writing",
    )
    arguments = parser.parse_args()

    try:
        manifest_path = arguments.manifest.resolve()
        package = load_package(manifest_path)
        package_root = manifest_path.parent
        changed_sources: tuple[PurePosixPath, ...] = ()
        if arguments.source_root is not None:
            changed_sources = synchronize_sources(
                package,
                package_root,
                arguments.source_root,
                check=arguments.check,
            )
        validate_runtime_assets(package, package_root)
        output_path = _joined_path(package_root, package.resource_file)
        generated = generate_resource(package)
        if arguments.check:
            if changed_sources:
                changed = ", ".join(path.as_posix() for path in changed_sources)
                raise AnimationPackageError(f"runtime assets differ from sources: {changed}")
            if not output_path.is_file() or output_path.read_text(encoding="utf-8") != generated:
                raise AnimationPackageError(f"generated resource is outdated: {output_path}")
            print(
                f"verified {len(package.animations)} animations and "
                f"{sum(item.frame_count for item in package.animations)} frames"
            )
            return 0

        output_path.write_text(generated, encoding="utf-8", newline="\n")
        for runtime_file in changed_sources:
            print(f"copied {runtime_file.as_posix()}")
        print(f"generated {output_path.relative_to(GAME_ROOT)}")
        return 0
    except (AnimationPackageError, OSError) as exc:
        print(f"green hero animation generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
