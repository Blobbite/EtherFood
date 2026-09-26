#!/usr/bin/env python3
"""Eigenständiger, einmaliger Farbprofil-Abgleich für einen PNG-Bildsatz.

Im PNG-Ordner: PyImgTuneColor --load --allow-color-merges
Lädt color_profile.json aus dem PNG-Ordner, optional --load DATEI.json.
Relative --load-Dateinamen beziehen sich auf den Bildordner.
Transparente Spritesheets werden automatisch in gleichgewichteten Frames gemessen.
Ein gemeinsamer Farbtransform erhält gleiche Farben über alle Animationsframes.
Keine Abhängigkeit zu PyImgTestColorInt.py; nur Python und Pillow >=9.1.
Keine Test-/Optimierungsschleife. Originale werden niemals überschrieben.
"""

# BEGIN STANDALONE COLOR CORE
# Intentionally embedded in both standalone tools. No cross-script imports.
# The regression suite checks these blocks and their numeric results for parity.
from __future__ import annotations

import argparse
import bisect
import errno
import hashlib
import io
import json
import math
import os
import statistics
import sys
import tempfile
import unicodedata
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageCms, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Pillow fehlt: python3 -m pip install 'Pillow>=9.1'")

VERSION = "1.3.0"
SCHEMA_VERSION = 3
DEFAULT_PROFILE_NAME = "color_profile.json"
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
MAX_PIXELS = 40_000_000
MAX_RGB_COLORS = 1_000_000
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_SPRITE_FRAMES = 4096
KEYS = ("lightness", "contrast", "chroma", "chroma_p90", "neutral_percent")
LABELS = {
    "lightness": "Helligkeit L*",
    "contrast": "Kontrast P90-P10 L*",
    "chroma": "Farbintensität C*ab",
    "chroma_p90": "C*ab P90",
    "neutral_percent": "Neutralanteil %",
}
# W3C sRGB/XYZ matrices. Lab deliberately uses D65, not CSS lab() D50.
# https://www.w3.org/TR/css-color-4/#color-conversion-code
RGB_TO_XYZ = (
    (506752 / 1228815, 87881 / 245763, 12673 / 70218),
    (87098 / 409605, 175762 / 245763, 12673 / 175545),
    (7918 / 409605, 87881 / 737289, 1001167 / 1053270),
)
XYZ_TO_RGB = (
    (12831 / 3959, -329 / 214, -1974 / 3959),
    (-851781 / 878810, 1648619 / 878810, 36519 / 878810),
    (705 / 12673, -2585 / 12673, 705 / 667),
)
WHITE = (0.3127 / 0.3290, 1.0, (1 - 0.3127 - 0.3290) / 0.3290)
LINEAR = tuple(v / 255 / 12.92 if v / 255 <= 0.04045
               else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in range(256))
LEGACY_MODEL = {
    "id": "pyimg-color-int-v1",
    "space": "CIELAB_D65_from_8bit_sRGB",
    "sampling": "all_pixels_no_resize_no_composite",
    "pixel_weight": "alpha/255; alpha=0 ignored",
    "lightness": "weighted_P05_P95_inclusive_trimmed_mean_Lstar",
    "contrast": "weighted_P90_Lstar_minus_P10_Lstar",
    "chroma": "weighted_P05_P95_inclusive_trimmed_mean_sqrt(a*a+b*b)",
    "neutral": "Cstar<5",
    "quantile": "first cumulative weight >= q * total weight",
    "group": "median_of_image_values_equal_image_weight",
    "score": "100*exp(-ln(100/90)*sum(weight*(absolute_delta/scale)^2))",
    "score_scales": dict(zip(KEYS, (2.0, 5.0, 3.0, 6.0, 8.0))),
    "score_weights": dict(zip(KEYS, (0.20, 0.25, 0.40, 0.10, 0.05))),
    "meaning": "heuristic consistency of global statistics; not artistic quality or visual identity",
    "icc": "embedded RGB/gray profiles converted to sRGB; relative colorimetric; no BPC",
    "untagged": "sRGB assumed; conflicting PNG gamma/chromaticity rejected",
    "geometry": "stored pixels; EXIF orientation not applied",
}
V2_MODEL = {
    **LEGACY_MODEL,
    "id": "pyimg-color-int-v2",
    "group": "median_of_frame_values_equal_frame_weight",
    "spritesheets": "auto_regular_alpha_gaps_v1; empty_cells_ignored; single_image_fallback",
}
DISTRIBUTION_AXES = {"lightness": (0.0, 400), "a": (-128.0, 1024),
                     "b": (-128.0, 1024), "chroma": (0.0, 800)}
DISTRIBUTION_STEP = 0.25
DISTRIBUTION_ID = "frame_balanced_Lab_C_histogram_025_v1"
MODEL = {**V2_MODEL, "id": "pyimg-color-int-v3",
         "spritesheets": "auto_periodic_alpha_grid_v2; alpha_gap_fallback; empty_cells_ignored",
         "color_distribution": DISTRIBUTION_ID}


def model_fingerprint(model: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(model, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


MODEL_FINGERPRINT = model_fingerprint(MODEL)
LEGACY_MODEL_FINGERPRINT = model_fingerprint(LEGACY_MODEL)
V2_MODEL_FINGERPRINT = model_fingerprint(V2_MODEL)


class ColorError(ValueError):
    """Actionable input or validation error."""


@dataclass
class Frame:
    path: Path
    image: Image.Image
    weights: dict[tuple[int, int, int], int]
    record: dict[str, Any]


def pixels(image: Image.Image):
    method = getattr(image, "get_flattened_data", None)
    return method() if method else image.getdata()


@lru_cache(maxsize=262144)
def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    linear = tuple(LINEAR[v] for v in rgb)
    xyz = [sum(row[i] * linear[i] for i in range(3)) for row in RGB_TO_XYZ]
    f = [v ** (1 / 3) if v > (6 / 29) ** 3 else v / (3 * (6 / 29) ** 2) + 4 / 29
         for v in (xyz[i] / WHITE[i] for i in range(3))]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def lab_to_linear(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    light, a, b = lab
    fy = (light + 16) / 116
    fs = (fy + a / 500, fy, fy - b / 200)
    xyz = tuple(WHITE[i] * (v ** 3 if v > 6 / 29 else 3 * (6 / 29) ** 2 * (v - 4 / 29))
                for i, v in enumerate(fs))
    return tuple(sum(row[i] * xyz[i] for i in range(3)) for row in XYZ_TO_RGB)


def encode_linear(linear: tuple[float, float, float]) -> tuple[int, int, int]:
    def encode(v: float) -> int:
        v = min(1.0, max(0.0, v))
        return round(255 * (12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055))
    return tuple(encode(v) for v in linear)


def rgba_hash(image: Image.Image) -> str:
    digest = hashlib.sha256(f"RGBA:{image.width}:{image.height}:".encode())
    digest.update(image.tobytes())
    return digest.hexdigest()


def profile_in_folder(value: Path, folder: Path) -> Path:
    """New --save/--load relative names are anchored to the PNG folder."""
    return value if value.is_absolute() else folder / value


def find_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise ColorError(f"Kein Bildordner: {folder}")
    result = sorted((p for p in folder.iterdir()
                     if not p.name.startswith(".") and not p.is_symlink()
                     and p.is_file() and p.suffix.lower() in EXTENSIONS),
                    key=lambda p: (p.name.casefold(), p.name))
    if not result:
        raise ColorError(f"Keine unterstützten Bilddateien direkt in {folder}")
    names = [unicodedata.normalize("NFC", p.name) for p in result]
    if len(names) != len(set(names)):
        raise ColorError("Dateinamen sind nach Unicode-Normalisierung mehrdeutig.")
    return result


def open_image(path: Path) -> tuple[Image.Image, dict[str, Any]]:
    if path.is_symlink():
        raise ColorError(f"Symbolische Bilddatei nicht unterstützt: {path}")
    with path.open("rb") as stream:
        header = stream.read(29)
    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 25 and header[24] == 16:
        raise ColorError(f"{path.name}: 16-Bit-PNG; bitte explizit als 8-Bit-sRGB exportieren.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as source:
            if getattr(source, "n_frames", 1) > 1:
                raise ColorError(f"{path.name}: Animation/Mehrseitenbild nicht unterstützt.")
            if source.width * source.height > MAX_PIXELS:
                raise ColorError(f"{path.name}: Grenze von {MAX_PIXELS} Pixeln überschritten.")
            if source.mode not in {"RGB", "RGBA", "P", "L", "LA", "1"}:
                raise ColorError(f"{path.name}: Modus {source.mode}; 8-Bit-RGB/Palette erforderlich.")
            bits = getattr(source, "tag_v2", {}).get(258, ())
            if isinstance(bits, int):
                bits = (bits,)
            if bits and max(bits) > 8:
                raise ColorError(f"{path.name}: mehr als 8 Bit pro Kanal nicht unterstützt.")
            source.load()
            image = source.convert("RGBA")
            notes = []
            icc = source.info.get("icc_profile")
            management = "assumed_sRGB"
            if icc:
                try:
                    profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                    base = source.convert("L") if source.mode in {"L", "LA", "1"} else source.convert("RGB")
                    converted = ImageCms.profileToProfile(
                        base, profile, ImageCms.createProfile("sRGB"),
                        renderingIntent=1, outputMode="RGB",
                    )
                    alpha, old = image.getchannel("A"), image
                    image = converted.convert("RGBA")
                    image.putalpha(alpha)
                    hidden = alpha.point(lambda a: 255 if a == 0 else 0)
                    image.paste(old, (0, 0), hidden)
                    management = "ICC_to_sRGB"
                    notes.append("Eingebettetes ICC-Profil vor Messung nach sRGB konvertiert.")
                except Exception as exc:
                    raise ColorError(f"{path.name}: ICC-Profil nicht konvertierbar: {exc}") from exc
            else:
                gamma, chrom = source.info.get("gamma"), source.info.get("chromaticity")
                if "srgb" not in source.info:
                    if gamma is not None and abs(gamma - 0.45455) > 0.005:
                        raise ColorError(f"{path.name}: abweichendes PNG-Gamma ohne ICC/sRGB-Profil.")
                    srgb_chrom = (0.3127, 0.3290, 0.64, 0.33, 0.30, 0.60, 0.15, 0.06)
                    if chrom and (len(chrom) != 8 or any(abs(a-b) > 0.002 for a, b in zip(chrom, srgb_chrom))):
                        raise ColorError(f"{path.name}: abweichende PNG-Primärfarben ohne ICC/sRGB-Profil.")
                management = "tagged_sRGB" if "srgb" in source.info else "assumed_sRGB"
            orientation = source.getexif().get(274, 1)
            if orientation != 1:
                notes.append(f"EXIF-Ausrichtung {orientation}: gespeichertes Raster wird unverändert gemessen.")
    image.info.clear()
    return image, {"color_management": management, "notes": notes,
                   "icc_sha256": hashlib.sha256(icc).hexdigest() if icc else None}


def distribution(values: list[tuple[float, int]]) -> dict[str, Any]:
    values.sort()
    total = sum(w for _, w in values)
    if total <= 0:
        raise ColorError("Keine sichtbaren Pixel für die Messung.")
    def q(p: float) -> float:
        target, running = total * p, 0
        for value, weight in values:
            running += weight
            if running >= target:
                return value
        return values[-1][0]
    quantiles = {f"p{p:02}": q(p / 100) for p in (5, 10, 25, 50, 75, 90, 95)}
    trimmed = [(v, w) for v, w in values if quantiles["p05"] <= v <= quantiles["p95"]]
    mean = math.fsum(v * w for v, w in values) / total
    robust = math.fsum(v * w for v, w in trimmed) / sum(w for _, w in trimmed)
    return {"mean": mean, "trimmed_mean": robust, **quantiles,
            "stddev": math.sqrt(math.fsum(w * (v - mean) ** 2 for v, w in values) / total)}


def measure(image: Image.Image) -> tuple[dict[str, Any], dict[tuple[int, int, int], int]]:
    counts = image.getcolors(maxcolors=image.width * image.height)
    if counts is None:
        raise ColorError("Bildhistogramm konnte nicht aufgebaut werden.")
    weights: dict[tuple[int, int, int], int] = defaultdict(int)
    visible = partial = 0
    for count, (r, g, b, a) in counts:
        if a:
            visible += count
            partial += count if a < 255 else 0
            weights[(r, g, b)] += count * a
    if not visible:
        raise ColorError("Bild ist vollständig transparent; keine Farbwerte messbar.")
    if len(weights) > MAX_RGB_COLORS:
        raise ColorError(f"Mehr als {MAX_RGB_COLORS} sichtbare RGB-Farben; Grenze dieser Version.")
    light_values, chroma_values = [], []
    neutral = rail = 0
    for rgb, weight in sorted(weights.items()):
        light, a, b = rgb_to_lab(rgb)
        chroma = math.hypot(a, b)
        light_values.append((light, weight))
        chroma_values.append((chroma, weight))
        if chroma < 5.0:
            neutral += weight
        if 0 in rgb or 255 in rgb:
            rail += weight
    total = sum(weights.values())
    ls, cs = distribution(light_values), distribution(chroma_values)
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    record = {
        "size": list(image.size), "bbox": list(bbox),
        "visible_height": bbox[3] - bbox[1], "bottom_visible_y": bbox[3] - 1,
        "visible_pixels": visible, "partial_alpha_pixels": partial,
        "alpha_sha256": hashlib.sha256(alpha.tobytes()).hexdigest(),
        "rgba_sha256": rgba_hash(image), "visible_rgb_colors": len(weights),
        "metrics": {"lightness": ls["trimmed_mean"], "contrast": ls["p90"] - ls["p10"],
                    "chroma": cs["trimmed_mean"], "chroma_p90": cs["p90"],
                    "neutral_percent": 100 * neutral / total},
        "lightness_distribution": ls, "chroma_distribution": cs,
        "rgb_rail_percent": 100 * rail / total,
    }
    return record, dict(weights)


def empty_color_distribution() -> dict[str, Any]:
    return {"id": DISTRIBUTION_ID, "frame_count": 0,
            "histograms": {key: [0.0] * (count + 1) for key, (_, count) in DISTRIBUTION_AXES.items()}}


@lru_cache(maxsize=262144)
def color_bins(rgb: tuple[int, int, int]) -> tuple[int, ...]:
    light, a, b = rgb_to_lab(rgb)
    return tuple(min(count, max(0, round((value-low) / DISTRIBUTION_STEP)))
                 for value, (low, count) in zip((light, a, b, math.hypot(a, b)), DISTRIBUTION_AXES.values()))


def add_frame_distribution(result: dict[str, Any], weights: dict) -> None:
    total = sum(weights.values())
    histograms = tuple(result["histograms"].values())
    for rgb, weight in weights.items():
        share = weight / total
        for histogram, index in zip(histograms, color_bins(rgb)):
            histogram[index] += share
    result["frame_count"] += 1


def combine_color_distributions(records: list[dict[str, Any]]) -> dict[str, Any]:
    result = empty_color_distribution()
    for record in records:
        distribution = record["color_distribution"]
        result["frame_count"] += distribution["frame_count"]
        for key, histogram in result["histograms"].items():
            for index, weight in enumerate(distribution["histograms"][key]):
                histogram[index] += weight
    return result


def validate_color_distribution(value: Any) -> None:
    if not isinstance(value, dict) or value.get("id") != DISTRIBUTION_ID:
        raise ColorError("Unbekannte oder fehlende Farbverteilung im Profil; Profil mit --save neu erstellen.")
    count = value.get("frame_count")
    histograms = value.get("histograms")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1 or not isinstance(histograms, dict):
        raise ColorError("Ungültige Frame-Anzahl/Farbverteilung im Profil.")
    if histograms.keys() != DISTRIBUTION_AXES.keys():
        raise ColorError("Unvollständige Farbkanäle im Profil.")
    for key, (_, bins) in DISTRIBUTION_AXES.items():
        values = histograms[key]
        if not isinstance(values, list) or len(values) != bins + 1 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= count * (1 + 1e-8)
                for v in values):
            raise ColorError(f"Ungültiges Farbhistogramm {key} im Profil.")
        if abs(math.fsum(values) - count) > max(1e-6, count * 1e-8):
            raise ColorError(f"Ungültige Gewichtssumme für {key} im Profil.")


def color_quantiles(value: dict[str, Any]) -> dict[str, list[float]]:
    result = {}
    for key, (low, _) in DISTRIBUTION_AXES.items():
        histogram = value["histograms"][key]
        occupied = [(low + i * DISTRIBUTION_STEP, w) for i, w in enumerate(histogram) if w > 0]
        total = math.fsum(w for _, w in occupied)
        index, cumulative = 0, occupied[0][1]
        quantiles = []
        for q in range(257):
            while cumulative + total * 1e-12 < q / 256 * total and index < len(occupied) - 1:
                index += 1
                cumulative += occupied[index][1]
            quantiles.append(occupied[index][0])
        result[key] = quantiles
    return result


def distribution_comparison(current: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    actual, target = color_quantiles(current), color_quantiles(reference)
    # Exclude the most extreme 1% at either end from the mean error, and check
    # the chroma P90 separately. These describe reference agreement, not artistry.
    errors = {key: statistics.mean(abs(a-b) for a, b in zip(actual[key][3:-3], target[key][3:-3]))
              for key in DISTRIBUTION_AXES}
    chroma_p90_delta = actual["chroma"][230] - target["chroma"][230]
    return {"mean_absolute_error": errors, "mean_error": statistics.mean(errors.values()),
            "chroma_p90_delta": chroma_p90_delta,
            "tolerances": {"channel_mean_error": 0.5, "chroma_p90_delta": 0.75},
            "within_tolerance": all(error <= 0.5 for error in errors.values()) and abs(chroma_p90_delta) <= 0.75}


def spritesheet_mode(value: str) -> str:
    value = value.lower().replace("×", "x")
    if value in {"auto", "off"}:
        return value
    parts = value.split("x")
    if len(parts) == 2 and all(p.isascii() and p.isdigit() and int(p) > 0 for p in parts):
        return "x".join(str(int(p)) for p in parts)
    raise argparse.ArgumentTypeError("Spritesheet: auto, off oder Framegröße wie 64x64 angeben.")


def add_spritesheet_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--spritesheet", type=spritesheet_mode, default="auto", metavar="auto|off|BxH",
                        help="automatische Frame-Erkennung (Standard); off = ganzes Bild; "
                             "z.B. 64x64 = festes Raster ohne Rand/Zwischenabstand")


def axis_partitions(projection: list[int]) -> list[list[int]]:
    """Candidate cuts only in empty gaps, grouped by gap width and regular spacing.

    Grouping small gaps first keeps detached details with the sprite when their
    spacing/size does not itself form a repeated sequence. Counts are not fixed.
    """
    spans = []
    start = None
    for position, occupied in enumerate([*projection, 0]):
        if occupied and start is None:
            start = position
        elif not occupied and start is not None:
            spans.append((start, position))
            start = None
    options = [[0, len(projection)]]
    if len(spans) < 2:
        return options
    gaps = [right[0] - left[1] for left, right in zip(spans, spans[1:])]
    thresholds = sorted(set(gaps))
    if len(thresholds) > 32:
        thresholds = [thresholds[i * (len(thresholds) - 1) // 31] for i in range(32)]
    for threshold in thresholds:
        bands = [spans[0]]
        for gap, span in zip(gaps, spans[1:]):
            if gap < threshold:
                bands[-1] = (bands[-1][0], span[1])
            else:
                bands.append(span)
        if not 2 <= len(bands) <= MAX_SPRITE_FRAMES:
            continue
        widths = [end - begin for begin, end in bands]
        typical_width = statistics.median(widths)
        if min(widths) < max(2, typical_width * 0.4) or max(widths) > typical_width * 2.5:
            continue
        centers = [(begin + end) / 2 for begin, end in bands]
        pitches = [b - a for a, b in zip(centers, centers[1:])]
        pitch = statistics.median(pitches)
        if any(abs(p - pitch) > max(2, pitch * 0.25) for p in pitches):
            continue
        cuts = [0, *[(left[1] + right[0]) // 2 for left, right in zip(bands, bands[1:])], len(projection)]
        if cuts not in options:
            options.append(cuts)
    return options


def periodic_partitions(density: list[float]) -> list[list[int]]:
    """Uniform cells supported by sparse seams AND a repeating opacity pattern.

    A few hairs/cape pixels may cross a boundary. An arbitrary empty band is
    insufficient: the contents of the proposed cells must repeat as well.
    """
    length = len(density)
    peak = max(density, default=0)
    if not peak:
        return []
    prefix = [0.0]
    for value in density:
        prefix.append(prefix[-1] + value)
    options = []
    for count in range(2, min(MAX_SPRITE_FRAMES, length // 4) + 1):
        if length % count:
            continue
        pitch = length // count
        radius = max(1, min(3, pitch // 100))
        if any(min(density[cut-radius:cut+radius+1]) > max(2.0, peak * 0.04)
               for cut in range(pitch, length, pitch)):
            continue
        signatures = []
        bins = min(32, pitch)
        for start in range(0, length, pitch):
            mass = prefix[start+pitch] - prefix[start]
            if mass < peak * pitch * 0.01:
                continue
            signatures.append([(prefix[start+(i+1)*pitch//bins] - prefix[start+i*pitch//bins]) / mass
                               for i in range(bins)])
        if len(signatures) < 2:
            continue
        typical = [statistics.median(row[i] for row in signatures) for i in range(bins)]
        errors = [sum(abs(a-b) for a, b in zip(row, typical)) for row in signatures]
        if max(errors) > 0.35:
            continue
        options.append(list(range(0, length+1, pitch)))
    return options


def detect_spritesheet(image: Image.Image, mode: str = "auto") -> dict[str, Any]:
    single = {"detected": False, "method": "single_image", "frame_count": 1,
              "grid": None, "boxes": [], "reason": "Keine eindeutige regelmäßige Aufteilung durch transparente Abstände."}
    if mode == "off":
        return {**single, "reason": "Frame-Erkennung ausgeschaltet."}
    alpha = image.getchannel("A")
    if mode != "auto":
        width, height = (int(v) for v in mode.split("x"))
        if image.width % width or image.height % height:
            raise ColorError(f"Bildmaße {image.width}x{image.height} sind nicht durch Framegröße {mode} teilbar.")
        columns, rows = image.width // width, image.height // height
        if columns * rows > MAX_SPRITE_FRAMES:
            raise ColorError(f"Mehr als {MAX_SPRITE_FRAMES} Rasterzellen werden nicht unterstützt.")
        boxes = [(x, y, x + width, y + height)
                 for y in range(0, image.height, height) for x in range(0, image.width, width)]
        boxes = [list(box) for box in boxes if alpha.crop(box).getbbox()]
        return {"detected": len(boxes) > 1, "method": "explicit_grid", "frame_count": len(boxes),
                "grid": [columns, rows], "boxes": boxes, "reason": f"Vorgegebene Framegröße {mode}."}
    px, py = alpha.getprojection()
    x_options, y_options = axis_partitions(px), axis_partitions(py)
    mask = alpha.point(lambda a: 255 if a else 0)
    # Only the detector reduces opacity to one-dimensional densities. Color
    # measurements and output images always use the full original pixels.
    x_regular = periodic_partitions(list(pixels(mask.resize((image.width, 1), Image.Resampling.BOX))))
    y_regular = periodic_partitions(list(pixels(mask.resize((1, image.height), Image.Resampling.BOX))))
    x_options = x_regular + [cuts for cuts in x_options if cuts not in x_regular]
    y_options = y_regular + [cuts for cuts in y_options if cuts not in y_regular]
    candidates = [(xs, ys) for xs in x_options for ys in y_options
                  if 2 <= (len(xs) - 1) * (len(ys) - 1) <= MAX_SPRITE_FRAMES]
    # A bounded number of full alpha scans, independent of image content complexity.
    candidates.sort(key=lambda pair: (len(pair[0]) - 1) * (len(pair[1]) - 1), reverse=True)
    best = None
    best_count = 1
    for xs, ys in candidates[:32]:
        boxes, widths, heights = [], [], []
        for top, bottom in zip(ys, ys[1:]):
            for left, right in zip(xs, xs[1:]):
                box = (left, top, right, bottom)
                bounds = alpha.crop(box).getbbox()
                if bounds:
                    boxes.append(list(box))
                    widths.append(bounds[2] - bounds[0])
                    heights.append(bounds[3] - bounds[1])
        if len(boxes) <= best_count or len(boxes) * 2 < (len(xs) - 1) * (len(ys) - 1):
            continue
        # Tiny particles, detached shadows and strongly unequal body parts are
        # insufficient evidence for separate animation frames.
        limit = 1.5 if len(boxes) == 2 else 2.5
        if any(min(sizes) < 2 or max(sizes) > min(sizes) * limit for sizes in (widths, heights)):
            continue
        best_count = len(boxes)
        regular = (len(xs) == 2 or xs in x_regular) and (len(ys) == 2 or ys in y_regular)
        best = {"detected": True, "method": "auto_periodic_grid" if regular else "auto_alpha_gaps", "frame_count": best_count,
                "grid": [len(xs) - 1, len(ys) - 1], "boxes": boxes,
                "reason": "Regelmäßiger Zellabstand, wiederkehrende Silhouetten und weitgehend transparente Grenzen."
                          if regular else "Wiederkehrende transparente Abstände und ähnlich große Sprite-Bereiche."}
    return best or single


def measure_asset(image: Image.Image, mode: str = "auto", layout: dict[str, Any] | None = None
                  ) -> tuple[dict[str, Any], dict[tuple[int, int, int], int]]:
    record, weights = measure(image)
    layout = detect_spritesheet(image, mode) if layout is None else layout
    sheet = {key: value for key, value in layout.items() if key != "frames"}
    color_distribution = empty_color_distribution()
    if sheet["detected"]:
        parts = []
        for index, box in enumerate(sheet["boxes"]):
            part, part_weights = measure(image.crop(tuple(box)))
            add_frame_distribution(color_distribution, part_weights)
            parts.append({"index": index, "box": box, "metrics": part["metrics"],
                          "visible_pixels": part["visible_pixels"]})
        sheet["frames"] = parts
        record["whole_image_metrics"] = record["metrics"]
        record["metrics"] = group_metrics(parts)
    else:
        add_frame_distribution(color_distribution, weights)
    record["spritesheet"] = sheet
    record["color_distribution"] = color_distribution
    return record, weights


def measurement_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [part for record in records for part in record.get("spritesheet", {}).get("frames", [record])]


def print_spritesheets(report: dict[str, Any]) -> None:
    for row in report["images"]:
        sheet = row["spritesheet"]
        if sheet["detected"]:
            columns, rows = sheet["grid"]
            print(f"🧩 {safe_text(row['name'])}: Spritesheet {columns} × {rows}, "
                  f"{sheet['frame_count']} sichtbare Frames; jeder Frame zählt gleich.")
    singles = sum(not row["spritesheet"]["detected"] for row in report["images"])
    if singles:
        print(f"Frame-Erkennung: {singles} Datei(en) als Einzelbild gemessen. "
              "Bei unerkanntem Sheet: --spritesheet BREITExHÖHE (z.B. 64x64).")


def load_frames(folder: Path, spritesheet: str = "auto") -> list[Frame]:
    frames = []
    for path in find_images(folder):
        try:
            image, metadata = open_image(path)
            record, weights = measure_asset(image, spritesheet)
            record.update(metadata)
            record["name"] = unicodedata.normalize("NFC", path.name)
            record["file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            frames.append(Frame(path, image, weights, record))
        except (OSError, ValueError, Image.DecompressionBombWarning) as exc:
            raise ColorError(f"{path.name}: {exc}") from exc
    return frames


def group_metrics(records: list[dict[str, Any]]) -> dict[str, float]:
    samples = measurement_records(records)
    return {key: statistics.median(r["metrics"][key] for r in samples) for key in KEYS}


def compare_metrics(current: dict[str, float], reference: dict[str, float]) -> dict[str, Any]:
    deltas = {k: current[k] - reference[k] for k in KEYS}
    distances = {k: (deltas[k] / MODEL["score_scales"][k]) ** 2 for k in KEYS}
    squared = math.fsum(MODEL["score_weights"][k] * distances[k] for k in KEYS)
    score = 100 * math.exp(-math.log(100 / 90) * squared)
    return {"score": score, "delta": deltas,
            "delta_percent": {k: deltas[k] / reference[k] * 100 if abs(reference[k]) > 1e-9 else None for k in KEYS},
            "component_scores": {k: 100 * math.exp(-math.log(100 / 90) * distances[k]) for k in KEYS}}


def utc_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def make_report(frames: list[Frame], folder: Path, label: str = "") -> dict[str, Any]:
    records = [dict(f.record) for f in frames]
    samples = measurement_records(records)
    group = group_metrics(records)
    for record in records:
        record["group_comparison"] = compare_metrics(record["metrics"], group) if len(samples) > 1 else None
    union = set().union(*(f.weights.keys() for f in frames))
    fingerprint = hashlib.sha256(b"".join(bytes(rgb) for rgb in sorted(union))).hexdigest()
    return {
        "kind": "PyImgColorIntReport", "schema_version": SCHEMA_VERSION,
        "tool_version": VERSION, "created_utc": utc_id(), "label": label,
        "folder": str(folder), "model": MODEL, "model_fingerprint": MODEL_FINGERPRINT,
        "environment": {"pillow": Image.__version__, "python": sys.version.split()[0]},
        "images": records, "group": group, "measured_frames": len(samples),
        "color_distribution": combine_color_distributions(records),
        "spritesheet_count": sum(bool(r.get("spritesheet", {}).get("detected")) for r in records),
        "ranges": {k: {"min": min(r["metrics"][k] for r in samples),
                       "max": max(r["metrics"][k] for r in samples)} for k in KEYS},
        "consistency_score": statistics.mean(compare_metrics(r["metrics"], group)["score"] for r in samples) if len(samples) > 1 else None,
        "group_visible_rgb_colors": len(union), "palette_sha256": fingerprint,
        "palette_rgb": [list(rgb) for rgb in sorted(union)] if len(union) <= 256 else None,
        "history": None, "reference": None,
    }


def make_profile(report: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "PyImgColorIntProfile", "schema_version": SCHEMA_VERSION,
            "tool_version": VERSION, "created_utc": report["created_utc"],
            "label": report["label"], "model": MODEL, "model_fingerprint": MODEL_FINGERPRINT,
            "group": report["group"], "group_visible_rgb_colors": report["group_visible_rgb_colors"],
            "color_distribution": report["color_distribution"],
            "palette_rgb": report["palette_rgb"], "palette_sha256": report["palette_sha256"],
            "measured_frames": report["measured_frames"],
            "images": [{k: r[k] for k in ("name", "metrics", "rgba_sha256", "size", "spritesheet") if k in r}
                       for r in report["images"]]}


def validate_metrics(metrics: Any) -> None:
    if not isinstance(metrics, dict):
        raise ColorError("Messwerte fehlen.")
    for k in KEYS:
        value = metrics.get(k)
        limit = 200 if k.startswith("chroma") else 100
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not 0 <= value <= limit or not math.isfinite(value):
            raise ColorError(f"Ungültiger Messwert {k}: {value}")


def read_profile(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ColorError(f"Profil-JSON nicht gefunden: {path}. JSON in den Bildordner legen oder ihren Pfad angeben.")
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ColorError(f"Profil/Report größer als {MAX_JSON_BYTES} Byte: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("kind") not in {"PyImgColorIntProfile", "PyImgColorIntReport"}:
        raise ColorError("Referenz ist kein ColorInt-Profil/Report.")
    current_model = (data.get("schema_version") == SCHEMA_VERSION
                     and data.get("model_fingerprint") == MODEL_FINGERPRINT and data.get("model") == MODEL)
    legacy_model = (data.get("schema_version") == 1
                    and data.get("model_fingerprint") == LEGACY_MODEL_FINGERPRINT and data.get("model") == LEGACY_MODEL)
    v2_model = (data.get("schema_version") == 2
                and data.get("model_fingerprint") == V2_MODEL_FINGERPRINT and data.get("model") == V2_MODEL)
    if not (current_model or legacy_model or v2_model):
        raise ColorError("Referenz verwendet eine inkompatible Version des Messmodells.")
    if current_model or "color_distribution" in data:
        validate_color_distribution(data.get("color_distribution"))
    validate_metrics(data.get("group"))
    images = data.get("images")
    if not isinstance(images, list) or not images:
        raise ColorError("Referenz enthält keine Bildmessungen.")
    names = set()
    for row in images:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or row["name"] in names:
            raise ColorError("Ungültige oder doppelte Bildnamen in der Referenz.")
        names.add(row["name"])
        validate_metrics(row.get("metrics"))
    return data


def attach_reference(report: dict[str, Any], reference: dict[str, Any], path: Path) -> dict[str, Any]:
    old = {r["name"]: r for r in reference["images"]}
    current = {r["name"]: r for r in report["images"]}
    common = sorted(old.keys() & current.keys())
    return {"path": str(path), "label": reference.get("label", ""),
            "same_file_set": old.keys() == current.keys(),
            "same_measurement_model": report["model_fingerprint"] == reference["model_fingerprint"],
            "group_comparison": compare_metrics(report["group"], reference["group"]),
            "reference_group": reference["group"],
            "color_distribution_comparison": distribution_comparison(report["color_distribution"], reference["color_distribution"])
                                             if reference.get("color_distribution") else None,
            "images": {name: compare_metrics(current[name]["metrics"], old[name]["metrics"]) for name in common},
            "missing_names": sorted(old.keys() - current.keys()),
            "new_names": sorted(current.keys() - old.keys())}


def previous_report(folder: Path, report: dict[str, Any]) -> tuple[Path, dict[str, Any]] | None:
    history = folder / ".compare"
    if history.is_symlink():
        raise ColorError("Reportordner .compare darf kein symbolischer Link sein.")
    names = {r["name"] for r in report["images"]}
    for path in sorted(history.glob("color_int_report_*.json"), reverse=True):
        if path.is_symlink():
            continue
        try:
            old = read_profile(path)
            if names == {r["name"] for r in old["images"]}:
                return path, old
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None


def atomic_new_bytes(path: Path, data: bytes) -> None:
    """Exclusive new file; atomic where hardlinks work, exclusive fallback elsewhere."""
    if path.exists() or path.is_symlink():
        raise ColorError(f"Zieldatei existiert bereits: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pyimg-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except OSError as exc:
            if exc.errno not in {errno.EPERM, errno.EOPNOTSUPP, errno.EXDEV, errno.ENOSYS}:
                raise
            stream = path.open("xb")
            try:
                with stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except BaseException:
                path.unlink(missing_ok=True)
                raise
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, data: Any) -> None:
    atomic_new_bytes(path, (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode())


def safe_text(value: str) -> str:
    return "".join(c if c.isprintable() else "?" for c in value)


def md(value: str) -> str:
    return safe_text(value).replace("\\", "\\\\").replace("|", "\\|").replace(chr(96), "\\" + chr(96))


def status(score: float | None) -> str:
    if score is None:
        return "keine Gruppenwertung bei einem Bild"
    return "Sehr gut abgestimmt" if score >= 90 else "Gut abgestimmt" if score >= 75 else "Abweichungen" if score >= 50 else "Starke Abweichungen"


def score_text(score: float | None) -> str:
    return "—" if score is None else f"{score:.2f} %"


def markdown_report(report: dict[str, Any]) -> str:
    lines = ["# PyImgTestColorInt", "", f"Version: {md(report['label']) or report['created_utc']}", "",
             f"Gruppen-Abstimmung: **{score_text(report['consistency_score'])} – {status(report['consistency_score'])}**.", "",
             "Der Score ist eine offengelegte Heuristik, keine künstlerische Qualitätsnote.", "",
             f"{len(report['images'])} Bilddateien, {report['measured_frames']} gemessene Frames. "
             "Gruppenmedian und Score gewichten jeden erkannten Frame wie ein einzelnes Bild.", "",
             "| Messwert | Gruppenmedian | Minimum | Maximum |", "|---|---:|---:|---:|"]
    for k in KEYS:
        lines.append(f"| {LABELS[k]} | {report['group'][k]:.4f} | {report['ranges'][k]['min']:.4f} | {report['ranges'][k]['max']:.4f} |")
    lines += ["", "| Bild | L* | Kontrast L* | C*ab | C* P90 | Neutral % | RGB-Rand % | RGB-Farben | Score |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in report["images"]:
        m = row["metrics"]
        score = row["group_comparison"]["score"] if row["group_comparison"] else None
        lines.append(f"| {md(row['name'])} | " + " | ".join(f"{m[k]:.4f}" for k in KEYS) +
                     f" | {row['rgb_rail_percent']:.4f} | {row['visible_rgb_colors']} | {score_text(score)} |")
    lines += ["", "## Spritesheet-Erkennung", "",
              "| Datei | Auswertung | Frames | Raster |", "|---|---|---:|---|"]
    for row in report["images"]:
        sheet = row["spritesheet"]
        grid = " × ".join(map(str, sheet["grid"])) if sheet["grid"] else "—"
        lines.append(f"| {md(row['name'])} | {sheet['method']} | {sheet['frame_count']} | {grid} |")
    lines += ["", "Die Erkennung prüft regelmäßige Zellabstände und wiederkehrende Silhouetten; "
              "wenige Pixel an einer Grenze sind erlaubt. Transparente Abstände dienen als weitere Heuristik. "
              "Ohne eindeutige Aufteilung bleibt die Datei ein Einzelbild. "
              "Mit --spritesheet off lässt sich die Erkennung abschalten; --spritesheet 64x64 "
              "gibt beispielsweise ein festes Raster vor. Leere Zellen zählen nicht. "
              "Bildzeilen in der Messtabelle zeigen bei Sheets den Median ihrer Frames; "
              "Gruppenwerte, Minima, Maxima und Gesamtscore berücksichtigen alle einzelnen Frames.", ""]
    for key, title in (("reference", "Explizite Referenz"), ("history", "Vorheriger vergleichbarer Lauf")):
        ref = report.get(key)
        if not ref:
            continue
        lines += ["", f"## {title}", "", f"Profil: {md(ref['path'])}", "",
                  f"Gleicher Bildsatz: {'ja' if ref['same_file_set'] else 'nein; Gruppenvergleich nur bedingt interpretierbar'}.", "",
                  f"Gruppenwerte-Übereinstimmung: {ref['group_comparison']['score']:.2f} %.", "",
                  "| Messwert | Referenz | Aktuell | Differenz |", "|---|---:|---:|---:|"]
        for k in KEYS:
            lines.append(f"| {LABELS[k]} | {ref['reference_group'][k]:.4f} | {report['group'][k]:.4f} | {ref['group_comparison']['delta'][k]:+.4f} |")
        comparison = ref.get("color_distribution_comparison")
        if comparison:
            lines += ["", f"Mittlere Abweichung der Farbverteilungen zur Referenz: {comparison['mean_error']:.4f} Lab-Einheiten. "
                      f"C90-Abweichung: {comparison['chroma_p90_delta']:+.4f}. "
                      f"Innerhalb der Verteilungstoleranzen: {'ja' if comparison['within_tolerance'] else 'nein'}.", ""]
        lines += ["", "| Bild | ΔL* | ΔKontrast L* | ΔC* | ΔC* P90 | ΔNeutral pp | Referenzscore |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for name, comparison in ref["images"].items():
            lines.append(f"| {md(name)} | " + " | ".join(f"{comparison['delta'][k]:+.4f}" for k in KEYS) + f" | {comparison['score']:.2f} % |")
        if not ref["same_file_set"]:
            lines.append(f"\nFehlend: {md(', '.join(ref['missing_names']))}; neu: {md(', '.join(ref['new_names']))}.")
        if not ref["same_measurement_model"]:
            lines.append("\nDie Referenz stammt aus einer früheren Messversion. "
                         "Rastererkennung und Messgrundlage können abweichen; gespeicherte Zielwerte werden übernommen.")
    lines += ["", "## Messbedingungen", "",
              "Alle sichtbaren Originalpixel, Gewicht Alpha/255, ohne Skalierung oder Hintergrundkomposition. "
              "CIELAB mit D65-Weißpunkt; unmarkierte Bilder werden als sRGB interpretiert. "
              "L* und C* sind an P05/P95 getrimmte Mittelwerte inklusive der Randwerte. "
              "C*ab ist Chroma, kein Sättigungsprozentwert. Neutral: C* < 5.", "",
              "RGB-Randanteil: mindestens ein Kanal bei 0 oder 255; das allein beweist kein Clipping. "
              "Gleiche Statistiken beweisen keine gleichen Farben, Materialien, Posen oder Bildinhalte. "
              "Andere Richtungen können wegen sichtbarer Materialanteile legitime Unterschiede haben.", "",
              "PyImgTestBC verkleinert die Analysebilder: dessen Werte/Score sind nicht direkt "
              "mit diesem Messmodell gleichzusetzen.", "",
              f"Gemeinsame sichtbare RGB-Farben: {report['group_visible_rgb_colors']}. "
              f"Modell-Fingerprint: {MODEL_FINGERPRINT}.", "",
              "Vollständige Messverteilungen, Hashes und Modellparameter stehen im JSON-Bericht.", ""]
    for row in report["images"]:
        if row["partial_alpha_pixels"]:
            lines.append(f"- {md(row['name'])}: {row['partial_alpha_pixels']} halbtransparente Pixel "
                         "in der gemessenen Datei; dieser Test verändert Alpha nicht.")
        for note in row.get("notes", []):
            lines.append(f"- {md(row['name'])}: {md(note)}")
    return "\n".join(lines)
# END STANDALONE COLOR CORE


TOLERANCES = {"lightness": 0.3, "contrast": 0.5, "chroma": 0.3}


def number(value: str) -> float:
    try:
        result = float(value.replace(",", "."))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Eine Zahl eingeben, z.B. 32.5 oder 32,5.") from exc
    if not math.isfinite(result):
        raise argparse.ArgumentTypeError("NaN und unendliche Werte sind nicht erlaubt.")
    return result


def gamut_rgb(light: float, a: float, b: float) -> tuple[tuple[int, int, int], bool, bool]:
    """Fixed numeric color conversion, not an image/test/target-matching loop."""
    bounded_light = min(100.0, max(0.0, light))
    light_clipped = bounded_light != light
    linear = lab_to_linear((bounded_light, a, b))
    def in_gamut(rgb: tuple[float, float, float]) -> bool:
        return all(-1e-10 <= v <= 1 + 1e-10 for v in rgb)
    reduced = not in_gamut(linear)
    if reduced:
        lower, upper = 0.0, 1.0
        for _ in range(24):
            fraction = (lower + upper) / 2
            if in_gamut(lab_to_linear((bounded_light, a * fraction, b * fraction))):
                lower = fraction
            else:
                upper = fraction
        linear = lab_to_linear((bounded_light, a * lower, b * lower))
    return encode_linear(linear), reduced, light_clipped


def coefficients(source: dict[str, float], target: dict[str, float]) -> dict[str, float]:
    validate_metrics(source)
    validate_metrics({**source, **target})
    def ratio(key: str) -> float:
        before, after = source[key], target[key]
        if before <= 1e-8:
            if after > 1e-8:
                raise ColorError(f"{key}: Ausgangswert ist 0; ein globaler Faktor kann daraus keinen positiven Zielwert erzeugen.")
            return 1.0
        return after / before
    contrast_scale, chroma_scale = ratio("contrast"), ratio("chroma")
    if contrast_scale > 10 or chroma_scale > 10:
        raise ColorError("Ziel erfordert einen Faktor über 10; diese Versuchsversion unterstützt solche Extremänderungen nicht.")
    return {"lightness_pivot": source["lightness"], "target_lightness": target["lightness"],
            "contrast_scale": contrast_scale, "chroma_scale": chroma_scale}


def distribution_parameters(source: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    current, target = color_quantiles(source), color_quantiles(reference)
    curves = {}
    for key, xs in current.items():
        ys = target[key]
        points, values = [], []
        i = 0
        while i < len(xs):
            end = bisect.bisect_right(xs, xs[i])
            points.append(xs[i])
            values.append(statistics.mean(ys[i:end]))
            i = end
        curves[key] = {"source": points, "target": values}
    return {"curves": curves, "identity": all(current[key] == target[key] for key in current),
            "method": "monotone_Lab_quantile_curves_with_chroma_curve",
            "quantile_count": 257, "histogram_step": DISTRIBUTION_STEP}


def curve_value(value: float, curve: dict[str, list[float]]) -> float:
    xs, ys = curve["source"], curve["target"]
    index = bisect.bisect_right(xs, value)
    if index == 0:
        return ys[0]
    if index == len(xs):
        return ys[-1]
    fraction = (value - xs[index-1]) / (xs[index] - xs[index-1])
    return ys[index-1] + fraction * (ys[index] - ys[index-1])


def transform_palette(frames: list[Frame], parameters: dict[str, Any], allow_merges: bool = False) -> tuple[dict, dict[str, Any]]:
    union = sorted(set().union(*(f.weights.keys() for f in frames)))
    if len(union) > MAX_RGB_COLORS:
        raise ColorError(f"Gemeinsame Palette hat mehr als {MAX_RGB_COLORS} Farben.")
    mapping, reduced_colors, clipped_colors = {}, set(), set()
    hue_errors, chroma_losses = {}, {}
    p = parameters
    curves = p.get("curves")
    identity = p["identity"] if curves is not None else (
        abs(p["target_lightness"] - p["lightness_pivot"]) < 1e-10
        and abs(p["contrast_scale"] - 1) < 1e-10 and abs(p["chroma_scale"] - 1) < 1e-10)
    for rgb in union:
        if identity:
            mapping[rgb] = rgb
            continue
        light, a, b = rgb_to_lab(rgb)
        if curves is None:
            wanted_light = p["target_lightness"] + p["contrast_scale"] * (light - p["lightness_pivot"])
            wanted_a, wanted_b = a * p["chroma_scale"], b * p["chroma_scale"]
        else:
            wanted_light = curve_value(light, curves["lightness"])
            wanted_a, wanted_b = curve_value(a, curves["a"]), curve_value(b, curves["b"])
            chroma = math.hypot(wanted_a, wanted_b)
            if chroma > 1e-8:
                factor = curve_value(math.hypot(a, b), curves["chroma"]) / chroma
                wanted_a *= factor
                wanted_b *= factor
        mapped, reduced, clipped = gamut_rgb(wanted_light, wanted_a, wanted_b)
        mapping[rgb] = mapped
        if reduced:
            reduced_colors.add(rgb)
        if clipped:
            clipped_colors.add(rgb)
        _ml, ma, mb = rgb_to_lab(mapped)
        wanted_chroma, final_chroma = math.hypot(wanted_a, wanted_b), math.hypot(ma, mb)
        chroma_losses[rgb] = max(0.0, wanted_chroma - final_chroma)
        if math.hypot(a, b) >= 5 and final_chroma >= 5:
            difference = math.degrees(math.atan2(mb, ma) - math.atan2(b, a))
            hue_errors[rgb] = abs((difference + 180) % 360 - 180)
    output_colors = set(mapping.values())
    collision_count = len(union) - len(output_colors)
    if collision_count and not allow_merges:
        raise ColorError(
            f"Farbkollision: {len(union)} Quellfarben würden zu {len(output_colors)} RGB-Farben. "
            "Keine Bilder geschrieben. Kleinere Änderung wählen oder bewusst --allow-color-merges verwenden."
        )
    per_image = {}
    for frame in frames:
        total = sum(frame.weights.values())
        affected = lambda colors: 100 * sum(w for c, w in frame.weights.items() if c in colors) / total
        per_image[frame.record["name"]] = {
            "gamut_reduced_percent": affected(reduced_colors),
            "lightness_clipped_percent": affected(clipped_colors),
            "mean_chroma_loss_to_requested": sum(frame.weights[c] * v for c, v in chroma_losses.items() if c in frame.weights) / total,
        }
    return mapping, {
        "source_rgb_colors": len(union), "output_rgb_colors": len(output_colors),
        "merged_rgb_colors": collision_count, "gamut_reduced_colors": len(reduced_colors),
        "lightness_clipped_colors": len(clipped_colors),
        "max_hue_error_degrees_for_chromatic_colors": max(hue_errors.values(), default=0.0),
        "identity_transform": identity, "images": per_image,
    }


def apply_mapping(image: Image.Image, mapping: dict) -> Image.Image:
    source = image.tobytes()
    result = bytearray(source)
    mapping_bytes = {bytes(k): bytes(v) for k, v in mapping.items()}
    for offset in range(0, len(source), 4):
        if source[offset + 3]:
            result[offset:offset + 3] = mapping_bytes[source[offset:offset + 3]]
    return Image.frombytes("RGBA", image.size, bytes(result))


def ensure_no_geometry_changes(before: Image.Image, after: Image.Image) -> None:
    if before.size != after.size or before.getchannel("A").tobytes() != after.getchannel("A").tobytes():
        raise ColorError("Interner Fehler: Bildmaße oder Alphakanal wurden verändert.")
    old, new = before.tobytes(), after.tobytes()
    if any(old[i:i+3] != new[i:i+3] for i in range(0, len(old), 4) if old[i+3] == 0):
        raise ColorError("Interner Fehler: unsichtbare RGB-Pixel wurden verändert.")


def tune_once(frames: list[Frame], before: dict[str, Any], target: dict[str, float],
              allow_merges: bool = False, color_reference: dict[str, Any] | None = None
              ) -> tuple[list[Frame], dict[str, Any]]:
    parameters = (distribution_parameters(before["color_distribution"], color_reference) if color_reference is not None
                  else coefficients(before["group"], target))
    mapping, diagnostic = transform_palette(frames, parameters, allow_merges)
    after_frames = []
    for frame in frames:
        image = apply_mapping(frame.image, mapping)
        ensure_no_geometry_changes(frame.image, image)
        record, weights = measure_asset(image, layout=frame.record.get("spritesheet"))
        record.update({"name": frame.record["name"], "color_management": "output_sRGB",
                       "notes": [], "file_sha256": None, "icc_sha256": None})
        after_frames.append(Frame(frame.path, image, weights, record))
    after = make_report(after_frames, Path(before["folder"]), "Einmalige Korrektur")
    target_error = {k: after["group"][k] - target[k] for k in TOLERANCES}
    report = {
        "kind": "PyImgColorTuneReport", "schema_version": SCHEMA_VERSION, "tool_version": VERSION,
        "created_utc": utc_id(), "model": MODEL, "model_fingerprint": MODEL_FINGERPRINT,
        "image_transform_passes": 1, "automatic_retries": 0,
        "mode": "single_shared_RGB_mapping_in_Lab_D65", "parameters": parameters,
        "success_criterion": "three_global_metrics",
        "source_group": before["group"], "target_group": target, "actual_group": after["group"],
        "target_error": target_error, "target_tolerances": TOLERANCES,
        "target_reached": all(abs(target_error[k]) <= TOLERANCES[k] for k in TOLERANCES),
        "diagnostics": diagnostic, "before": before, "after": after,
        "pixel_guards": {"dimensions_unchanged": True, "alpha_identical": True,
                         "hidden_rgb_identical": True, "no_resampling": True,
                         "no_dithering": True, "no_requantization": True,
                         "one_output_color_per_input_color": True},
        "color_map": [{"before": list(rgb), "after": list(mapping[rgb])} for rgb in sorted(mapping)] if len(mapping) <= 4096 else None,
    }
    if color_reference is not None:
        reference_before = distribution_comparison(before["color_distribution"], color_reference)
        reference_after = distribution_comparison(after["color_distribution"], color_reference)
        report.update(mode="spritesheet_color_distribution", success_criterion="reference_color_distribution",
                      distribution_reference={"before": reference_before, "after": reference_after},
                      target_reached=reference_after["within_tolerance"])
    return after_frames, report


def tune_profile(frames: list[Frame], before: dict[str, Any], target: dict[str, float],
                 profile: dict[str, Any] | None, allow_merges: bool = False
                 ) -> tuple[list[Frame], dict[str, Any]]:
    sheets = [frame for frame in frames if frame.record["spritesheet"]["detected"]]
    if not sheets or profile is None:
        return tune_once(frames, before, target, allow_merges)
    reference = profile.get("color_distribution")
    if reference is None:
        raise ColorError("Das geladene Profil enthält noch keine Farbverteilungen für Spritesheets. "
                         "Im Referenzordner mit dem neuen PyImgTestColorInt --save ein neues Profil erstellen "
                         "und hierher kopieren. Einzelbilder und --spritesheet off können das alte Profil weiter nutzen.")
    if len(sheets) == len(frames):
        return tune_once(frames, before, target, allow_merges, reference)
    singles = [frame for frame in frames if not frame.record["spritesheet"]["detected"]]
    # A mixed folder must not opt its single images into distribution matching.
    results, reports = {}, []
    for batch, distribution in ((singles, None), (sheets, reference)):
        batch_before = make_report(batch, Path(before["folder"]), before["label"])
        output, row = tune_once(batch, batch_before, target, allow_merges, distribution)
        reports.append(row)
        results.update((frame.record["name"], frame) for frame in output)
    output = [results[frame.record["name"]] for frame in frames]
    after = make_report(output, Path(before["folder"]), "Gemischter Bildsatz")
    combined = dict(reports[-1])
    diagnostics = dict(reports[-1]["diagnostics"])
    diagnostics.update(source_rgb_colors=before["group_visible_rgb_colors"],
                       output_rgb_colors=after["group_visible_rgb_colors"],
                       identity_transform=all(r["diagnostics"]["identity_transform"] for r in reports),
                       images={k:v for r in reports for k,v in r["diagnostics"]["images"].items()})
    for key in ("merged_rgb_colors", "gamut_reduced_colors", "lightness_clipped_colors"):
        diagnostics[key] = sum(r["diagnostics"][key] for r in reports)
    diagnostics["max_hue_error_degrees_for_chromatic_colors"] = max(
        r["diagnostics"]["max_hue_error_degrees_for_chromatic_colors"] for r in reports)
    combined.update(mode="mixed_single_images_and_spritesheets", success_criterion="all_batch_criteria",
                    before=before, after=after, source_group=before["group"], actual_group=after["group"],
                    target_error={key: after["group"][key]-target[key] for key in TOLERANCES},
                    parameters={"batches": [r["parameters"] for r in reports]}, diagnostics=diagnostics,
                    batches=reports, color_map=None, target_reached=all(r["target_reached"] for r in reports),
                    pixel_guards={**reports[-1]["pixel_guards"], "one_output_color_per_input_color": False,
                                  "one_output_color_per_input_color_within_each_batch": True})
    return output, combined


def print_tune_result(report: dict[str, Any]) -> None:
    for batch in report.get("batches", [report]):
        reference = batch.get("distribution_reference")
        if reference:
            print("Spritesheets: Farbverteilungen zur Referenz angeglichen; gleiche Farbzuordnung für alle Frames.")
            print(f"{'Referenzabweichung':24} {'Vorher':>10} {'Nachher':>10} {'Grenze':>10}")
            for key, label in (("lightness", "Helligkeitsverteilung"), ("a", "Grün–Rot-Verteilung"),
                               ("b", "Blau–Gelb-Verteilung"), ("chroma", "Farbintensitätsverteilung")):
                print(f"{label:24} {reference['before']['mean_absolute_error'][key]:10.4f} "
                      f"{reference['after']['mean_absolute_error'][key]:10.4f} {0.5:10.4f}")
            print(f"C90-Abweichung zur Referenz: {reference['before']['chroma_p90_delta']:+.4f} → "
                  f"{reference['after']['chroma_p90_delta']:+.4f}")
            print("Farbverteilungen innerhalb der Toleranzen: " + ("ja" if batch["target_reached"] else "nein"))
        else:
            print("Bisheriger Abgleich von Helligkeit, Kontrast und Farbintensität.")
            print(f"{'Messwert':24} {'Vorher':>10} {'Ziel':>10} {'Erreicht':>10} {'Rest':>10}")
            for key in TOLERANCES:
                print(f"{LABELS[key]:24} {batch['source_group'][key]:10.4f} {batch['target_group'][key]:10.4f} "
                      f"{batch['actual_group'][key]:10.4f} {batch['target_error'][key]:+10.4f}")


def check_destination(folder: Path, output: Path, names: list[str]) -> None:
    if output.exists() or output.is_symlink():
        raise ColorError(f"Ausgabeordner existiert bereits: {output}. Einen neuen Namen wählen.")
    if output.resolve() == folder or output.resolve() in folder.parents:
        raise ColorError("Ausgabe muss ein neuer eigener Ordner sein.")
    if len({unicodedata.normalize("NFC", n).casefold() for n in names}) != len(names):
        raise ColorError("Mehrere Quellen würden denselben PNG-Ausgabenamen erhalten.")


def tune_markdown(report: dict[str, Any]) -> str:
    lines = ["# PyImgTuneColor – einmaliger Abgleich", "",
             "Ein gemeinsamer Farbdurchlauf; keine Optimierungs- oder Testschleife.", "",
             f"{report['before']['spritesheet_count']} Spritesheets erkannt; "
             f"{report['before']['measured_frames']} Frames insgesamt gleich gewichtet. "
             "Gleiche Quellfarben erhalten innerhalb der gemeinsam korrigierten Sheets dieselbe Zielfarbe. "
             "Einzelbilder behalten ihren bisherigen Abgleich.", ""]
    for batch in report.get("batches", [report]):
        reference = batch.get("distribution_reference")
        if reference:
            lines += ["## Spritesheets: Übereinstimmung mit der Referenz", "",
                      "| Verteilung | Abweichung vorher | Abweichung nachher | Toleranz |", "|---|---:|---:|---:|"]
            for key, label in (("lightness", "Helligkeit L*"), ("a", "Grün–Rot a*"),
                               ("b", "Blau–Gelb b*"), ("chroma", "Farbintensität C*")):
                lines.append(f"| {label} | {reference['before']['mean_absolute_error'][key]:.4f} | "
                             f"{reference['after']['mean_absolute_error'][key]:.4f} | 0.5 |")
            lines += ["", f"C90-Abweichung: {reference['before']['chroma_p90_delta']:+.4f} → "
                      f"{reference['after']['chroma_p90_delta']:+.4f}; Toleranz ±0.75.", "",
                      "Gemessen wird der mittlere absolute Abstand der Verteilungsquantile in Lab-Einheiten. "
                      "Die extremsten 1 % werden beim Mittel ausgeschlossen. Die Erfolgsmeldung bezieht sich "
                      "auf diese vier Fehlergrenzen und C90, nicht auf drei globale Mittelwerte. "
                      "Das ist eine statistische Prüfung, keine Garantie für identische Materialien oder Posen.", ""]
        else:
            lines += ["## Bisheriger Kennzahlen-Abgleich", "",
                      "| Messwert | Vorher | Ziel | Erreicht | Restabweichung |", "|---|---:|---:|---:|---:|"]
            for k in TOLERANCES:
                lines.append(f"| {LABELS[k]} | {batch['source_group'][k]:.4f} | {batch['target_group'][k]:.4f} | "
                             f"{batch['actual_group'][k]:.4f} | {batch['target_error'][k]:+.4f} |")
    d = report["diagnostics"]
    lines += ["", f"Ziel innerhalb der dokumentierten Toleranzen erreicht: **{'ja' if report['target_reached'] else 'nein'}**.", "",
              f"Frame-Ähnlichkeit untereinander: {score_text(report['before']['consistency_score'])} → "
              f"{score_text(report['after']['consistency_score'])}. Dieser Score misst keine Referenzübereinstimmung.", "",
              f"Gemeinsame sichtbare RGB-Farben: {d['source_rgb_colors']} → {d['output_rgb_colors']}; "
              f"zusammengefallen: {d['merged_rgb_colors']}.", "",
              f"Farbraum-begrenzte Farben: {d['gamut_reduced_colors']}; L*-begrenzte Farben: {d['lightness_clipped_colors']}.", "",
              f"Maximale rechnerische Farbtonänderung einschließlich Referenzkorrektur und 8-Bit-Rundung: "
              f"{d['max_hue_error_degrees_for_chromatic_colors']:.3f}° (nur C* vorher/nachher ≥ 5).", "",
              "| Bild | Farbraum-begrenzte Pixel % | L*-begrenzte Pixel % |", "|---|---:|---:|"]
    for name, row in d["images"].items():
        lines.append(f"| {md(name)} | {row['gamut_reduced_percent']:.4f} | {row['lightness_clipped_percent']:.4f} |")
    partial = [r for r in report["before"]["images"] if r["partial_alpha_pixels"]]
    if partial:
        lines += ["", "Alphawerte bereits vorhandener halbtransparenter Pixel bleiben unverändert; "
                  "ihre RGB-Farben werden mitkorrigiert:", ""]
        lines += [f"- {md(r['name'])}: {r['partial_alpha_pixels']} Pixel mit Alpha 1–254." for r in partial]
    if report.get("target_profile"):
        lines += ["", f"Geladenes Zielprofil: {md(report['target_profile']['path'])}.", ""]
    lines += ["", "Maße, Alpha und RGB vollständig transparenter Pixel sind exakt erhalten. "
              "Keine Skalierung, kein Dithering, keine erneute Quantisierung. "
              "Bestehende Farbflecken werden nicht automatisch repariert; eine globale Farbzuordnung "
              "erkennt keine Gesichter oder Materialien.", "",
              "Unterschiedliche Verteilungen von L*, C* und Farben können dieselben drei Zielwerte haben. "
              "Das Werkzeug stellt daher keine andere Version bildgenau wieder her. "
              "Verbleibende Fehler werden ausgewiesen, nicht automatisch nachgeregelt.", "",
              "Die Farbraumanpassung reduziert bei Bedarf C* bei festem rechnerischen L*/Farbton. "
              "Bei starken Änderungen kann dies sichtbar werden. Numerisch erhaltener Lab-Farbton "
              "garantiert keine identische subjektive Farbwahrnehmung.", "",
              "Alle Einzelmesswerte, Parameter, Eingangshashes und bis zu 4096 Farbzuordnungen "
              "sind im JSON-Protokoll enthalten. before_after.png ist eine beschriftete Vorschau "
              "mit neutralem Hintergrund; die ausgegebenen Einzel-PNGs behalten ihren Alphakanal.", ""]
    return "\n".join(lines)


def preview_png(before: list[Frame], after: list[Frame]) -> bytes:
    examples = []
    for original, corrected in zip(before, after):
        layout = original.record["spritesheet"]
        boxes = layout["boxes"] if layout["detected"] else [(0, 0, *original.image.size)]
        indices = sorted({0, len(boxes)//2, len(boxes)-1}) if layout["detected"] else [0]
        for index in indices:
            label = original.record["name"]
            if layout["detected"]:
                label += f" · Frame {index+1}/{len(boxes)}"
            examples.append((original.image.crop(boxes[index]), corrected.image.crop(boxes[index]), label))
    examples = examples[:8]
    width, height = 1040, 42 + len(examples) * 650
    sheet = Image.new("RGB", (width, height), "#e5e6e8")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    draw.text((210, 10), "Vorher", fill="#202630", font=font)
    draw.text((730, 10), "Nachher", fill="#202630", font=font)
    for i, (original, corrected, label) in enumerate(examples):
        for column, thumb in enumerate((original, corrected)):
            thumb.thumbnail((480, 600), Image.Resampling.NEAREST)
            x = column * 520 + (520 - thumb.width) // 2
            y = 42 + i * 650
            sheet.paste(thumb, (x, y), thumb.getchannel("A"))
            draw.text((column * 520 + 10, y + 615), safe_text(label)[-65:], fill="#202630", font=font)
    buffer = io.BytesIO()
    sheet.save(buffer, "PNG")
    return buffer.getvalue()


def publish(folder: Path, output: Path, before_frames: list[Frame], after_frames: list[Frame], report: dict[str, Any]) -> None:
    names = [f.path.stem + ".png" for f in before_frames]
    check_destination(folder, output, names)
    for frame in before_frames:
        if hashlib.sha256(frame.path.read_bytes()).hexdigest() != frame.record["file_sha256"]:
            raise ColorError(f"Quelle wurde während der Arbeit geändert: {frame.path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pyimg-tune-", dir=output.parent) as temporary:
        stage = Path(temporary) / "result"
        stage.mkdir()
        srgb_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        for original, frame, name in zip(before_frames, after_frames, names):
            path = stage / name
            frame.image.save(path, "PNG", icc_profile=srgb_profile)
            with Image.open(path) as decoded:
                if rgba_hash(decoded.convert("RGBA")) != rgba_hash(frame.image):
                    raise ColorError(f"PNG-Roundtrip fehlgeschlagen: {name}")
            frame.record["source_name"] = original.record["name"]
            frame.record["name"] = name
            frame.record["file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            frame.record["icc_sha256"] = hashlib.sha256(srgb_profile).hexdigest()
        after = make_report(after_frames, output, report["after"]["label"])
        after["reference"] = attach_reference(after, report["before"], Path("Eingangssatz"))
        report["after"] = after
        report["output_folder"] = str(output)
        reports = stage / ".compare"
        stem = "color_int_report_" + after["created_utc"]
        write_json(reports / (stem + ".json"), after)
        atomic_new_bytes(reports / (stem + ".md"), markdown_report(after).encode())
        atomic_new_bytes(reports / "color_tune_report.md", tune_markdown(report).encode())
        write_json(reports / "color_tune_report.json", report)
        write_json(reports / "output_color_profile.json", make_profile(after))
        atomic_new_bytes(reports / "before_after.png", preview_png(before_frames, after_frames))
        if output.exists() or output.is_symlink():
            raise ColorError(f"Ausgabeziel wurde inzwischen angelegt: {output}")
        stage.rename(output)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder", nargs="?", type=Path, default=Path.cwd(), help="Bildordner; Standard: aktueller Terminalordner")
    add_spritesheet_argument(p)
    load_group = p.add_mutually_exclusive_group()
    load_group.add_argument("--load", nargs="?", const=Path(DEFAULT_PROFILE_NAME), type=Path, metavar="DATEI.json",
                            help=f"Zielprofil laden; ohne Dateiname: {DEFAULT_PROFILE_NAME} im Bildordner; relative Namen ebenfalls dort")
    load_group.add_argument("--target-profile", type=Path, help="bisherige Ladeoption; relativer Pfad zum Terminalordner")
    p.add_argument("--interactive", action="store_true", help="Zielwerte im Terminal eingeben (Enter = angezeigten Wert behalten)")
    for key, relative, help_text in (("lightness", "lightness-shift", "additive Verschiebung in L*"),
                                    ("contrast", "contrast-scale", "Faktor; 0.9 = 10 Prozent weniger Kontrast"),
                                    ("chroma", "chroma-scale", "Faktor; 0.9 = 10 Prozent weniger C*")):
        group = p.add_mutually_exclusive_group()
        group.add_argument("--" + key, type=number, help=f"absoluter Gruppen-Zielwert {LABELS[key]}")
        group.add_argument("--" + relative, type=number, help=help_text)
    p.add_argument("--output", type=Path, help="neuer Ausgabeordner; Standard: color_tuned_<Zeit> im Bildordner")
    p.add_argument("--dry-run", action="store_true", help="einmal berechnen und messen, keinerlei Dateien schreiben")
    p.add_argument("--allow-color-merges", action="store_true", help="bewusst Farbkollisionen erlauben; exakte Palettengröße kann sinken")
    p.add_argument("--label", default="Einmaliger Farbabgleich", help="Versionsname für den Ergebnisreport")
    p.add_argument("--no-color", action="store_true", help="keine ANSI-Farben; standardmäßig bereits ausgeschaltet")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return p


def resolve_target(args: argparse.Namespace, group: dict[str, float], profile: dict[str, Any] | None) -> dict[str, float]:
    target = dict(group)
    if profile:
        target.update({k: profile["group"][k] for k in TOLERANCES})
    for k in TOLERANCES:
        value = getattr(args, k)
        if value is not None:
            target[k] = value
    if args.lightness_shift is not None:
        target["lightness"] = group["lightness"] + args.lightness_shift
    for k in ("contrast", "chroma"):
        scale = getattr(args, k + "_scale")
        if scale is not None:
            if not 0 <= scale <= 10:
                raise ColorError(f"{k}-scale muss zwischen 0 und 10 liegen.")
            target[k] = group[k] * scale
    if args.interactive:
        if not sys.stdin.isatty():
            raise ColorError("--interactive braucht ein Terminal. Alternativ --load oder --lightness/--contrast/--chroma verwenden.")
        for k in TOLERANCES:
            while True:
                value = input(f"{LABELS[k]} Ziel [{target[k]:.4f}]: ").strip()
                if not value:
                    break
                try:
                    entered = number(value)
                    validate_metrics({**target, k: entered})
                    target[k] = entered
                    break
                except (argparse.ArgumentTypeError, ColorError) as exc:
                    print(exc)
    validate_metrics(target)
    return target


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        folder = args.folder.resolve()
        profile_path = profile_in_folder(args.load, folder) if args.load is not None else args.target_profile
        controls = (args.lightness, args.contrast, args.chroma, args.lightness_shift, args.contrast_scale, args.chroma_scale)
        if profile_path is not None and any(value is not None for value in controls):
            raise ColorError("Entweder --load/--target-profile oder manuelle Zielwerte/Faktoren angeben.")
        if not args.interactive and profile_path is None and all(value is None for value in controls):
            if sys.stdin.isatty():
                args.interactive = True
            else:
                raise ColorError("Zielwerte, --load oder --interactive angeben. Hilfe: --help")
        profile = read_profile(profile_path) if profile_path is not None else None
        output = args.output.absolute() if args.output else folder / ("color_tuned_" + utc_id())
        names = [p.stem + ".png" for p in find_images(folder)]
        check_destination(folder, output, names)
        frames = load_frames(folder, args.spritesheet)
        before = make_report(frames, folder, "Eingangssatz")
        print_spritesheets(before)
        if profile:
            print(f"📂 Zielprofil geladen: {profile_path}")
            if profile["schema_version"] == 1:
                print("Profil aus Version 1.1: gespeicherte Zielwerte übernommen. "
                      "Für eine Referenz aus Spritesheets das Profil mit PyImgTestColorInt --save neu erstellen.")
            if {r["name"] for r in profile["images"]} != {r["name"] for r in before["images"]}:
                print("Hinweis: Zielprofil stammt aus einem anderen Bildsatz; globale Zielwerte werden trotzdem verwendet.")
        target = resolve_target(args, before["group"], profile)
        after_frames, report = tune_profile(frames, before, target, None if args.interactive else profile, args.allow_color_merges)
        report["after"]["label"] = args.label
        if profile is not None:
            report["target_profile"] = {"path": str(profile_path), "label": profile.get("label", ""),
                                        "sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest()}
        print("\n🎛 PyImgTuneColor · ein Durchlauf · keine automatische Nachregelung")
        print_tune_result(report)
        print(f"Frame-Ähnlichkeit untereinander (kein Referenzabgleich): {score_text(before['consistency_score'])} → "
              f"{score_text(report['after']['consistency_score'])}")
        d = report["diagnostics"]
        print(f"RGB-Farben: {d['source_rgb_colors']} → {d['output_rgb_colors']} · Gamut-begrenzt: {d['gamut_reduced_colors']} Farben "
              f"· L*-begrenzt: {d['lightness_clipped_colors']} Farben")
        print("Alpha, Bildmaße und unsichtbare RGB-Pixel unverändert; keine Skalierung/Quantisierung/Dithering.")
        for row in before["images"]:
            if row["partial_alpha_pixels"]:
                print(f"⚠ {safe_text(row['name'])}: bereits vorhandene {row['partial_alpha_pixels']} halbtransparente Pixel beibehalten.")
        if not report["target_reached"]:
            print("⚠ Referenzabgleich außerhalb der angegebenen Toleranzen; Restabweichungen siehe oben. Keine Wiederholung.")
        if d["merged_rgb_colors"]:
            print(f"⚠ {d['merged_rgb_colors']} Farben zusammengefallen (--allow-color-merges aktiv).")
        if args.dry_run:
            print("Dry-run: keine Dateien geschrieben.")
        else:
            publish(folder, output, frames, after_frames, report)
            print(f"\nPNG-Ausgabe: {output}\nBericht/Vorschau: {output / '.compare'}")
        return 0
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
