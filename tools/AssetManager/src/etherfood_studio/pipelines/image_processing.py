"""Shared PyGameTools algorithms, operating on job copies with explicit frame metadata."""

from copy import deepcopy
import math
from pathlib import Path
import re
import sys

from PIL import Image

from ..domain.assets import require
from ..domain.graphics import proportional_size

TOOL_ROOT = Path(__file__).resolve().parents[3] / "PyGameTools/Pipline"


def legacy_modules():
    # Only repository-owned modules, never paths read from recipes or asset metadata.
    for path in (TOOL_ROOT / "PiplineToos", TOOL_ROOT / "2-SpritesheetResolution-Pipline"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import PyImgColorMatch as soft
    import PyImgFixedColors as exact
    import PyImgGrid as grid
    import PyImgFrameSelect as selection
    import SComicMid as comic
    import SPixelHigh as pixel

    return grid, selection, comic, pixel, soft, exact


def split_frames(image, grid):
    require(isinstance(grid, (list, tuple)) and len(grid) == 2 and
            all(type(n) is int and 1 <= n <= 64 for n in grid) and math.prod(grid) <= 64,
            "Ungültiges Frame-Raster.")
    cols, rows = grid
    require(image.width % cols == image.height % rows == 0, "Bild passt nicht zum Frame-Raster.")
    width, height = image.width // cols, image.height // rows
    return [image.crop((x * width, y * height, (x + 1) * width, (y + 1) * height))
            for y in range(rows) for x in range(cols)]


def validate_metadata(meta, image_size=None):
    """Validate provenance and geometry before either processing or accepting an output."""
    fields = {"kind", "grid", "frames", "source_grid", "source_indices", "source_revision",
              "source_sha256", "slot", "profile", "logical_size", "crop_offset", "crop_size",
              "anchor", "frame_size", "pixel_anchor", "display_scale"}
    require(isinstance(meta, dict), "Bildmetadaten müssen ein Objekt sein.")
    if meta.get("kind") == "spritesheet":
        fields.update({"fps", "loop", "duration", "timing_mode"})
        require(type(meta.get("loop")) is bool and meta.get("timing_mode") in
                {"keep_fps", "keep_duration"}, "Ungültiges Loop-/Timing-Verhalten.")
        for name in ("fps", "duration"):
            value = meta.get(name)
            require(type(value) in {int, float} and math.isfinite(value) and value > 0,
                    "Ungültiges Animationstiming: " + name)
        require(meta["fps"] <= 240, "Wiedergabe-FPS überschreiten 240.")
    else:
        require(meta.get("kind") == "single_image", "Unbekannter Bildquelltyp.")
    require(fields <= set(meta) <= fields | {"contract", "image_sha256"},
            "Unvollständige oder unerlaubte Bild-/Animationsmetadaten.")
    for name in ("grid", "source_grid", "frame_size", "logical_size"):
        value = meta[name]
        require(isinstance(value, list) and len(value) == 2 and
                all(type(v) is int and v > 0 for v in value), "Ungültige Bildgröße: " + name)
    require(math.prod(meta["grid"]) <= 64 and math.prod(meta["source_grid"]) <= 64 and
            type(meta["frames"]) is int and meta["frames"] == math.prod(meta["grid"]),
            "Raster und Framezahl stimmen nicht überein.")
    indices = meta["source_indices"]
    require(isinstance(indices, list) and len(indices) == meta["frames"] and
            all(type(i) is int and 0 <= i < math.prod(meta["source_grid"]) for i in indices) and
            indices == sorted(set(indices)), "Ungültige oder wiederholte Quellframeauswahl.")
    for name in ("anchor", "crop_offset", "crop_size", "pixel_anchor", "display_scale"):
        values = meta[name]
        require(isinstance(values, list) and len(values) == 2 and
                all(type(v) in {int, float} and math.isfinite(v) for v in values),
                "Ungültige Frame-Geometrie: " + name)
    require(all(0 <= meta["crop_offset"][i] and 0 < meta["crop_size"][i] and
                meta["crop_offset"][i] + meta["crop_size"][i] <= meta["logical_size"][i] + 1e-7
                for i in (0, 1)), "Zuschnitt liegt außerhalb der logischen Frame-Größe.")
    require(all(0 <= value <= 1 for value in meta["anchor"]),
            "Anker müssen normalisiert zwischen 0 und 1 liegen.")
    require(isinstance(meta["profile"], str) and meta["profile"] and
            isinstance(meta["source_revision"], str) and meta["source_revision"] and
            isinstance(meta["source_sha256"], str) and
            re.fullmatch(r"[a-f0-9]{64}", meta["source_sha256"]) is not None and
            isinstance(meta["slot"], dict) and meta["slot"].get("kind") == meta["kind"],
            "Ungültige Quell-/Profilbindung.")
    size = tuple(meta["grid"][i] * meta["frame_size"][i] for i in (0, 1))
    require(math.prod(size) <= 32_000_000 and (image_size is None or size == image_size),
            "Bildgröße passt nicht zu Raster/Frame-Metadaten oder überschreitet die Grenze.")
    expected = finish_metadata(deepcopy(meta), meta["frame_size"])
    require(all(math.isclose(meta[name][i], expected[name][i], abs_tol=1e-7)
                for name in ("pixel_anchor", "display_scale") for i in (0, 1)),
            "Anker und Weltgröße passen nicht zur Crop-Geometrie.")
    if meta["kind"] == "single_image":
        require(meta["frames"] == 1 and meta["source_grid"] == [1, 1],
                "Einzelbilder dürfen keine Animation enthalten.")
    else:
        require(math.isclose(meta["duration"], meta["frames"] / meta["fps"], abs_tol=1e-7),
                "Animationsdauer stimmt nicht mit Framezahl und FPS überein.")


def expected_metadata(image, metadata, operation, parameters, profile=None):
    """Derive expected geometry from trusted inputs, not the worker's output assertions."""
    validate_metadata(metadata, image.size)
    grid, selection, _, _, _, _ = legacy_modules()
    meta = deepcopy(metadata)
    meta.pop("contract", None)
    meta.pop("image_sha256", None)
    size = tuple(meta["frame_size"])
    if operation.startswith("prepare"):
        count = int(operation.removeprefix("prepare"))
        require(meta["kind"] == "spritesheet" and meta["frames"] == count,
                "Fram8/Fram16 benötigt genau die passende Quellframezahl.")
        box = grid.get_common_content_box(split_frames(image, meta["grid"]))
        require(box is not None, "Alle Frames sind transparent; kein gemeinsamer Inhalt.")
        sx, sy = (meta["crop_size"][i] / size[i] for i in (0, 1))
        meta["crop_offset"] = [meta["crop_offset"][0] + box[0] * sx,
                               meta["crop_offset"][1] + box[1] * sy]
        meta["crop_size"] = [(box[2] - box[0]) * sx, (box[3] - box[1]) * sy]
        size = (box[2] - box[0], box[3] - box[1])
        meta["grid"] = [4, count // 4]
    elif operation == "frames":
        require(meta["kind"] == "spritesheet", "Einzelbilder haben keine Frame-Reduktion.")
        count = parameters["frames"]
        indices = selection.uniform_indices(meta["frames"], count)
        meta["source_indices"] = [meta["source_indices"][index] for index in indices]
        meta["frames"] = count
        meta["grid"] = {8: [4, 2], 10: [5, 2], 12: [4, 3], 14: [7, 2],
                        16: [4, 4]}.get(count, [count, 1])
        meta["fps"] = count / meta["duration"] \
            if parameters["timing"] == "keep_duration" else parameters["fps"]
        meta["duration"] = count / meta["fps"]
        meta["timing_mode"] = parameters["timing"]
    elif operation == "scale":
        require(profile["method"] != "pixel_low" or meta["profile"] == profile["parent"],
                "Pixel Low benötigt das ausdrücklich zugewiesene Pixel-High-Ergebnis.")
        size = proportional_size(*size, profile["mode"], profile["value"])
        meta["profile"] = profile["key"]
    elif operation == "source_color":
        require(meta["kind"] == "single_image",
                "Source-Farbe verarbeitet nur Einzelbilder, keine Animationserzeugung.")
    return finish_metadata(meta, size)


def transform(image, metadata, operation, parameters, resources, *, profile=None):
    from ..packages import process

    return process(image, metadata, operation, parameters, resources, profile)


def finish_metadata(meta, size):
    meta["frame_size"] = list(size)
    meta["pixel_anchor"] = [(meta["anchor"][i] * meta["logical_size"][i] -
                             meta["crop_offset"][i]) * size[i] / meta["crop_size"][i]
                            for i in (0, 1)]
    meta["display_scale"] = [meta["crop_size"][i] / size[i] for i in (0, 1)]
    return meta


def material_mask(path, original_path, meta, palette):
    grid, _, _, _, _, exact = legacy_modules()
    from ..storage.blob_store import file_hash

    with Image.open(original_path) as raw:
        original = raw.convert("RGBA")
    require(file_hash(original_path) == meta["source_sha256"] and
            original.size == tuple(meta["source_grid"][i] * meta["logical_size"][i]
                                   for i in (0, 1)),
            "Materialmaske und Original passen nicht zur eingefrorenen Frame-Geometrie.")
    mask = exact.load_mask(path, original, tuple(meta["source_grid"]), palette["materials"],
                           file_hash(original_path))
    source_frames = split_frames(mask, meta["source_grid"])
    x, y = meta["crop_offset"]
    width, height = meta["crop_size"]
    require(all(float(v).is_integer() for v in (x, y, width, height)),
            "Materialmaske benötigt eindeutig ganzzahlige Crop-Geometrie.")
    box = (int(x), int(y), int(x + width), int(y + height))
    frames = [source_frames[i].crop(box).resize(tuple(meta["frame_size"]),
              Image.Resampling.NEAREST) for i in meta["source_indices"]]
    cols, rows = meta["grid"]
    size = frames[0].size
    result = Image.new("L", (cols * size[0], rows * size[1]))
    for index, frame in enumerate(frames):
        result.paste(frame, (index % cols * size[0], index // cols * size[1]))
    return result
