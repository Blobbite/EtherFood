#!/usr/bin/env python3
"""Fußanker, Mittelachse, Kopf-/Oberkante und Positionssprünge prüfen.

Eigenständiges Werkzeug: Python >= 3.10 und Pillow >= 9.1. Ohne Argumente
werden Bilder direkt im aktuellen Ordner untersucht. Ein Raster wird nur
aus einer eindeutigen Angabe wie ``spritesheet_4x4`` oder mit ``--grid``
übernommen; die Messung erfolgt pro Zelle in unveränderten Originalpixeln.

Der geschätzte Bodenanker liegt zwischen den robusten horizontalen Grenzen
der unteren Silhouettenzone, auf der unteren Silhouettenkante. Er ist eine
Heuristik für stehende Figuren, kein aus Bildpixeln beweisbarer Gelenkpunkt.
Umhang, Waffen, Schatten, Sprünge und stark versetzte Füße erfordern ggf.
manuelle Anker mit ``--anchors``. Schwerpunkt und Außenkontur werden nur
als ergänzende Messwerte verwendet. Koordinaten: Ursprung oben links,
Pixelmitten bei (x+0.5, y+0.5), untere Pixelkante bei y+1.

Reports: .compare/central_{figure,report}_<UTC-ID>.{png,md,json}.
--no-report liest/schreibt keine Reports und erzeugt keinerlei Dateien.
--align ORDNER exportiert verlustfrei verschobene PNG-Kopien mit gemeinsamem
zusätzlichem Rand; Originale und vorhandene Zieldateien werden nie ersetzt.
Standardmäßig wird ein ganzer Animationsbogen um seinen medianen Anker
verschoben, damit beabsichtigte Bewegung innerhalb der Animation bleibt.
--align-mode frame richtet ausdrücklich jeden Frame einzeln aus.

Exitcodes: 0 = Untersuchung ausgeführt (auch bei geometrischen Befunden),
1 = Eingabe-/Ausgabefehler, 2 = geometrischer Befund mit --strict, 130 = Abbruch.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import io
import json
import math
import os
import re
import statistics
import sys
import tempfile
import unicodedata
import warnings
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Pillow fehlt: python3 -m pip install 'Pillow>=9.1'")

VERSION = "2.0.0"
SCHEMA_VERSION = 2
MODEL_ID = "central-three-axis-original-pixels-v2"
OUTPUT_FOLDER = ".compare"
EXTENSIONS = frozenset({".png", ".webp", ".tga", ".tif", ".tiff", ".gif",
                        ".bmp", ".ico", ".jpg", ".jpeg", ".avif"})
MAX_PIXELS = 40_000_000
MAX_FRAMES = 512
MAX_JSON_BYTES = 16 * 1024 * 1024
DIRECTIONS = ("N", "NO", "O", "SO", "S", "SW", "W", "NW")
CRITERIA = (("x_axis", "X-Ausrichtung", 0),
            ("foot_line", "Fußlinie Y", 1),
            ("head_line", "Kopf-/Oberkante Y", 1))


class CentralError(ValueError):
    """Verständlicher Eingabe- oder Ausgabefehler."""


def clean(value: str) -> str:
    return "".join(c if c.isprintable() else "?" for c in value)


def md(value: str) -> str:
    return clean(value).replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")


def grid_value(value: str) -> tuple[int, int] | None:
    if value == "auto":
        return None
    match = re.fullmatch(r"([1-9]\d*)[xX]([1-9]\d*)", value)
    if not match or int(match[1]) * int(match[2]) > MAX_FRAMES:
        raise argparse.ArgumentTypeError(f"Raster als SPALTENxZEILEN, maximal {MAX_FRAMES} Zellen.")
    return int(match[1]), int(match[2])


def point_value(value: str) -> tuple[float, float]:
    try:
        values = tuple(float(v) for v in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Punkt als X,Y in Pixeln angeben.") from exc
    if len(values) != 2 or not all(math.isfinite(v) for v in values):
        raise argparse.ArgumentTypeError("Punkt als zwei endliche Zahlen X,Y angeben.")
    return values


def find_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise CentralError(f"Kein Bildordner: {folder}")
    def order(path: Path) -> tuple[int, str, str]:
        stem = path.stem.upper()
        return (DIRECTIONS.index(stem) if stem in DIRECTIONS else len(DIRECTIONS),
                path.name.casefold(), path.name)
    return sorted((p for p in folder.iterdir() if not p.name.startswith(".")
                   and not p.is_symlink() and p.is_file()
                   and p.suffix.lower() in EXTENSIONS), key=order)


def image_grid(path: Path, explicit: tuple[int, int] | None) -> tuple[int, int]:
    if explicit is not None:
        return explicit
    matches = re.findall(r"(?:^|[_ -])(?:spritesheet[_ -])?(\d+)x(\d+)(?=[_ -]|$)",
                         path.stem, re.IGNORECASE)
    if len(matches) > 1:
        raise CentralError("Mehrdeutiges Raster im Dateinamen; --grid verwenden.")
    try:
        return grid_value("x".join(matches[0])) if matches else (1, 1)
    except argparse.ArgumentTypeError as exc:
        raise CentralError(str(exc)) from exc


def open_rgba(path: Path) -> Image.Image:
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as opened:
            if getattr(opened, "n_frames", 1) != 1:
                raise CentralError("Animierte/mehrseitige Datei: Frames zuerst als Raster exportieren.")
            if opened.width * opened.height > MAX_PIXELS:
                raise CentralError(f"Bild überschreitet {MAX_PIXELS:,} Pixel.")
            if opened.getexif().get(274, 1) != 1:
                raise CentralError("EXIF-Drehung zuerst anwenden; Rasterkoordinaten wären mehrdeutig.")
            if opened.mode in {"I", "F"} or opened.mode.startswith("I;16"):
                raise CentralError("16-Bit-/HDR-Bilder werden nicht automatisch reduziert.")
            rgba = opened.convert("RGBA")
            rgba.info.clear()
            return rgba


def clean_mask(alpha: Image.Image, threshold: int) -> tuple[Image.Image, dict[str, int]]:
    """8-fach verbundene Komponenten über Zeilenläufe, ohne NumPy/SciPy.

    Nur kleine, abgetrennte Komponenten (<0.1% der größten, mindestens
    zwei Pixel) werden aus der Messmaske entfernt. Die Bildpixel bleiben
    erhalten und werden auch beim Export vollständig berücksichtigt.
    """
    binary = alpha.point([255 if v >= threshold else 0 for v in range(256)])
    raw = binary.tobytes()
    width, height = binary.size
    parent: list[int] = []
    runs: list[tuple[int, int, int, int]] = []

    def root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    previous: list[tuple[int, int, int]] = []
    for y in range(height):
        current = []
        cursor = 0
        for match in re.finditer(b"\xff+", raw[y * width:(y + 1) * width]):
            left, right = match.span()
            label = len(parent)
            parent.append(label)
            while cursor < len(previous) and previous[cursor][1] < left:
                cursor += 1
            j = cursor
            while j < len(previous) and previous[j][0] <= right:
                parent[root(previous[j][2])] = root(label)
                j += 1
            current.append((left, right, label))
            runs.append((y, left, right, label))
        previous = current
    areas: dict[int, int] = defaultdict(int)
    for _y, left, right, label in runs:
        areas[root(label)] += right - left
    if not areas:
        raise CentralError("Keine sichtbare Silhouette oberhalb der Alpha-Schwelle.")
    minimum = max(2, math.ceil(max(areas.values()) * 0.001))
    largest = max(areas, key=areas.get)
    kept = {key for key, area in areas.items() if area >= minimum or key == largest}
    filtered = Image.new("L", binary.size)
    draw = ImageDraw.Draw(filtered)
    for y, left, right, label in runs:
        if root(label) in kept:
            draw.line((left, y, right - 1, y), fill=255)
    return filtered, {"components": len(kept),
                      "removed_pixels": sum(v for k, v in areas.items() if k not in kept)}


def axis_weights(mask: Image.Image, horizontal: bool) -> list[int]:
    im = mask.transpose(Image.Transpose.TRANSPOSE) if horizontal else mask
    raw, width = im.tobytes(), im.width
    return [sum(raw[start:start + width]) for start in range(0, len(raw), width)]


def quantile_index(weights: list[int], fraction: float) -> int:
    target, cumulative = sum(weights) * fraction, 0
    for index, weight in enumerate(weights):
        cumulative += weight
        if weight and cumulative >= target:
            return index
    raise CentralError("Leere Messzone.")


def foot_bounds(mask: Image.Image, bbox: tuple[int, int, int, int],
                fraction: float) -> tuple[float, int, int, int]:
    left, top, right, bottom = bbox
    band_top = max(top, bottom - max(2, math.ceil((bottom - top) * fraction)))
    weights = axis_weights(mask.crop((left, band_top, right, bottom)), True)
    low = left + quantile_index(weights, 0.02)
    high = left + quantile_index(weights, 0.98) + 1
    return (low + high) / 2, band_top, low, high


def measure(image: Image.Image, alpha_threshold: int = 32,
            foot_band: float = 0.12) -> dict[str, Any]:
    alpha = image.getchannel("A")
    if alpha.getextrema()[0] >= alpha_threshold:
        raise CentralError("Keine transparente Trennung zum Hintergrund; Fußanker nicht messbar.")
    mask, cleanup = clean_mask(alpha, alpha_threshold)
    threshold_bbox = alpha.point([255 if v >= alpha_threshold else 0
                                  for v in range(256)]).getbbox()
    bbox = mask.getbbox()
    if bbox is None:
        raise CentralError("Leere Silhouette.")
    x, band_top, low, high = foot_bounds(mask, bbox, foot_band)
    variants = [foot_bounds(mask, bbox, min(0.4, foot_band * factor))[0]
                for factor in (0.75, 1.0, 1.25)]
    # Alpha-gewichteter Schwerpunkt der bereinigten Silhouette, ohne Hintergrund.
    visible_alpha = Image.composite(alpha, Image.new("L", image.size), mask)
    moments = []
    for horizontal in (True, False):
        weights = axis_weights(visible_alpha, horizontal)
        moments.append(sum((i + 0.5) * v for i, v in enumerate(weights)) / sum(weights))
    uncertainty = max(variants) - min(variants)
    notices = []
    top_y = threshold_bbox[1]
    if top_y != bbox[1]:
        notices.append("Oberster Pixel liegt in einem abgetrennten Fragment; obere Messlinie visuell prüfen.")
    if uncertainty > max(3, (bbox[3] - bbox[1]) * 0.02):
        notices.append("Fußmitte hängt stark von der Messbandhöhe ab; Anker visuell prüfen.")
    if cleanup["components"] > 3:
        notices.append("Mehrere getrennte Silhouetten; Raster oder manuelle Anker prüfen.")
    if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == image.width or bbox[3] == image.height:
        notices.append("Silhouette berührt den Zellenrand; möglicher Beschnitt.")
    return {"anchor": [x, float(bbox[3])], "method": "foot_band",
            "top_y": float(top_y), "top_pixel_y": top_y,
            "top_method": "highest_pixel_at_alpha_threshold",
            "cleaned_top_y": float(bbox[1]), "height_px": float(bbox[3] - top_y),
            "bbox": list(bbox), "visible_bbox": list(alpha.getbbox()),
            "bbox_center": [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2],
            "centroid": moments, "foot_band": [low, band_top, high, bbox[3]],
            "band_sensitivity_px": uncertainty, "cleanup": cleanup,
            "confidence": "review" if notices else "estimated", "notices": notices}


def load_anchors(path: Path | None) -> dict[str, list[float]]:
    if path is None:
        return {}
    if path.stat().st_size > MAX_JSON_BYTES:
        raise CentralError("Ankerdatei ist zu groß.")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise CentralError('Ankerdatei: {"N.png": [x, y], "bogen.png#r1c1": [x, y]}.')
    for name, point in data.items():
        if (not isinstance(name, str) or not isinstance(point, list) or len(point) != 2
                or not all(type(v) in (int, float) and math.isfinite(v) for v in point)):
            raise CentralError(f"Ungültiger manueller Anker: {clean(str(name))}")
    return data


def load_frames(folder: Path, args: argparse.Namespace,
                overrides: dict[str, list[float]]) -> tuple[list[dict], list[dict]]:
    frames, sources = [], []
    used = set()
    for path in find_images(folder):
        source: dict[str, Any] = {"name": path.name}
        sources.append(source)
        try:
            cols, rows = image_grid(path, args.grid)
            with open_rgba(path) as image:
                if image.width % cols or image.height % rows:
                    raise CentralError(f"Bildgröße {image.size} ist nicht durch Raster {cols}x{rows} teilbar.")
                if len(frames) + cols * rows > MAX_FRAMES:
                    raise CentralError(f"Maximal {MAX_FRAMES} Frames pro Lauf.")
                width, height = image.width // cols, image.height // rows
                source.update(size=list(image.size), grid=[cols, rows],
                              rgba_sha256=hashlib.sha256(image.tobytes()).hexdigest())
                for row in range(rows):
                    for col in range(cols):
                        key = path.name if cols * rows == 1 else f"{path.name}#r{row + 1}c{col + 1}"
                        frame: dict[str, Any] = {"id": key, "name": path.name,
                                                "index": row * cols + col,
                                                "row": row, "column": col,
                                                "size": [width, height],
                                                "origin": [col * width, row * height]}
                        frames.append(frame)
                        with image.crop((col * width, row * height, (col + 1) * width,
                                         (row + 1) * height)) as cell:
                            try:
                                frame.update(measure(cell, args.alpha_threshold, args.foot_band))
                            except CentralError as exc:
                                frame["error"] = str(exc)
                            if key in overrides:
                                point = overrides[key]
                                if not (0 <= point[0] <= width and 0 <= point[1] <= height):
                                    raise CentralError(f"Manueller Anker außerhalb der Zelle: {key}")
                                if cell.getchannel("A").getbbox() is None:
                                    raise CentralError(f"Manueller Anker für leere Zelle: {key}")
                                used.add(key)
                                frame.pop("error", None)
                                notices = [n for n in frame.get("notices", [])
                                           if not n.startswith("Fußmitte hängt")]
                                frame.update(anchor=list(point), method="manual",
                                             confidence="review" if notices else "manual",
                                             notices=notices, visible_bbox=list(cell.getchannel("A").getbbox()))
        except (OSError, ValueError, SyntaxError, EOFError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as exc:
            source["error"] = clean(str(exc))
    unknown = sorted(set(overrides) - used)
    if unknown:
        raise CentralError("Anker ohne passende gültige Zelle: " + ", ".join(unknown))
    if not sources:
        raise CentralError("Keine unterstützten Bilder direkt im Bildordner gefunden.")
    return frames, sources


def median_point(points: list[list[float]]) -> list[float]:
    return [statistics.median(p[axis] for p in points) for axis in (0, 1)]


def distance(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def integer_shift(value: float) -> int:
    # Bei exakt halben Pixeln zur Null runden. Damit bleiben unvermeidbare
    # +/-0.5-px-Reste beim erneuten Export stabil statt hin und her zu springen.
    magnitude = math.ceil(abs(value) - 0.5)
    return magnitude if value >= 0 else -magnitude


def axis_score(deviation_px: float, reference_px: int) -> float:
    """100 minus der Abweichung in Prozent der jeweiligen Zellenausdehnung.

    Die Pixeltoleranz entscheidet separat über den Befund. Ein kleiner
    Unterschied erhält daher einen kleinen, stetigen Punktabzug, ohne
    Sprung auf 0 bei zehnfacher Toleranz. 100 bedeutet exakte Übereinstimmung.
    """
    return max(0.0, 100.0 * (1.0 - deviation_px / reference_px))


def coordinate(frame: dict, key: str) -> float | None:
    if key == "head_line":
        return frame.get("top_y")
    anchor = frame.get("anchor")
    return anchor[0 if key == "x_axis" else 1] if anchor is not None else None


def axis_result(value: float | None, target: float | None, reference: int,
                tolerance: float) -> dict:
    if value is None or target is None:
        return {"value_px": value, "target_px": target, "offset_px": None,
                "deviation_percent": None, "score": None, "reference_px": reference,
                "status": "unavailable"}
    delta = value - target
    return {"value_px": value, "target_px": target, "offset_px": delta,
            "deviation_percent": 100 * abs(delta) / reference,
            "score": axis_score(abs(delta), reference), "reference_px": reference,
            "status": "pass" if abs(delta) <= tolerance else "deviation"}


def summarize_axes(items: list[dict], by_file: dict[str, list[dict]],
                   size: tuple[int, int], target: list[float],
                   head_target: float | None, tolerance: float) -> dict:
    results = {}
    targets = {"x_axis": target[0], "foot_line": target[1], "head_line": head_target}
    for key, label, axis in CRITERIA:
        observed = [coordinate(f, key) for f in items if coordinate(f, key) is not None]
        expected = targets[key]
        medians = []
        steps = []
        for frames in by_file.values():
            values = [coordinate(f, key) for f in frames if coordinate(f, key) is not None]
            if values:
                medians.append(statistics.median(values))
            if len(frames) > 1:
                for a, b in zip(frames, frames[1:] + frames[:1]):
                    av, bv = coordinate(a, key), coordinate(b, key)
                    if av is not None and bv is not None:
                        steps.append(abs(av - bv))
        errors = [abs(v - expected) for v in observed] if expected is not None else []
        max_target = max(errors, default=None)
        spread = max(medians) - min(medians) if len(medians) > 1 else None
        temporal = max(steps, default=None)
        maximum = max((v for v in (max_target, spread, temporal) if v is not None), default=None)
        complete = len(observed) == len(items) and expected is not None
        score = axis_score(maximum, size[axis]) if maximum is not None else None
        results[key] = {"label": label, "weight": 1 / len(CRITERIA),
                        "reference_px": size[axis], "target_px": expected,
                        "measured_frames": len(observed), "total_frames": len(items),
                        "complete": complete, "max_target_deviation_px": max_target,
                        "mean_target_deviation_px": statistics.mean(errors) if errors else None,
                        "direction_spread_px": spread, "max_animation_step_px": temporal,
                        "deviation_px": maximum,
                        "deviation_percent": 100 * maximum / size[axis] if maximum is not None else None,
                        "score": score,
                        "status": "unavailable" if not complete else
                                  "pass" if maximum <= tolerance else "deviation"}
    return results


def assess(frames: list[dict], sources: list[dict], args: argparse.Namespace) -> list[dict]:
    groups: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for frame in frames:
        if "anchor" in frame:
            groups[tuple(frame["size"])].append(frame)
    summaries = []
    for size, items in groups.items():
        by_file: dict[str, list[dict]] = defaultdict(list)
        for item in items:
            by_file[item["name"]].append(item)
        medians = {name: median_point([f["anchor"] for f in values])
                   for name, values in by_file.items()}
        target = list(args.pivot) if args.pivot else [size[0] / 2, median_point(list(medians.values()))[1]]
        if not (0 <= target[0] <= size[0] and 0 <= target[1] <= size[1]):
            raise CentralError(f"Zielanker {target} liegt außerhalb der Zellengröße {size}.")
        top_medians = [statistics.median(f["top_y"] for f in values if "top_y" in f)
                       for values in by_file.values() if any("top_y" in f for f in values)]
        head_target = args.head_y if args.head_y is not None else (
            statistics.median(top_medians) if top_medians else None)
        if head_target is not None and not 0 <= head_target < size[1]:
            raise CentralError(f"Obere Ziellinie {head_target} liegt außerhalb der Zellengröße {size}.")
        file_results = []
        for name, values in by_file.items():
            anchor = medians[name]
            pairs = list(zip(values, values[1:]))
            jumps = [{"from": a["id"], "to": b["id"],
                      "distance_px": distance(a["anchor"], b["anchor"])} for a, b in pairs]
            temporal_max = max((j["distance_px"] for j in jumps), default=0.0)
            for item in values:
                delta = [target[axis] - item["anchor"][axis] for axis in (0, 1)]
                item.update(target=target, offset_px=[-v for v in delta],
                            shift_px=[integer_shift(v) for v in delta],
                            distance_px=distance(item["anchor"], target),
                            within_sheet_px=distance(item["anchor"], anchor))
                item["head_target_y"] = head_target
                targets = (target[0], target[1], head_target)
                item["criteria"] = {
                    key: axis_result(coordinate(item, key), expected, size[axis], args.tolerance)
                    for (key, _label, axis), expected in zip(CRITERIA, targets)}
            tops = [f["top_y"] for f in values if "top_y" in f]
            heights = [f["height_px"] for f in values if "height_px" in f]
            file_results.append({"name": name, "frame_count": len(values), "anchor": anchor,
                                 "top_y": statistics.median(tops) if tops else None,
                                 "top_range_y": [min(tops), max(tops)] if tops else None,
                                 "height_px": statistics.median(heights) if heights else None,
                                 "height_range_px": [min(heights), max(heights)] if heights else None,
                                 "criteria": summarize_axes(values, {name: values}, size, target,
                                                            head_target, args.tolerance),
                                 "offset_px": [anchor[i] - target[i] for i in (0, 1)],
                                 "shift_px": [integer_shift(target[i] - anchor[i]) for i in (0, 1)],
                                 "max_target_distance_px": max(f["distance_px"] for f in values),
                                 "max_within_sheet_px": max(f["within_sheet_px"] for f in values),
                                 "max_step_px": temporal_max,
                                 "loop_step_px": distance(values[-1]["anchor"], values[0]["anchor"]),
                                 "worst_step": max(jumps, key=lambda j: j["distance_px"], default=None)})
        direction_pairs = [{"from": a, "to": b, "delta_px": [medians[b][i] - medians[a][i] for i in (0, 1)],
                            "distance_px": distance(medians[a], medians[b])}
                           for a, b in combinations(medians, 2)]
        maximum = max(f["distance_px"] for f in items)
        pair_max = max((p["distance_px"] for p in direction_pairs), default=0.0)
        temporal_max = max((max(f["max_step_px"], f["loop_step_px"]) for f in file_results), default=0.0)
        criteria = summarize_axes(items, by_file, size, target, head_target, args.tolerance)
        error = max(maximum, pair_max, temporal_max,
                    *(c["deviation_px"] or 0 for c in criteria.values()))
        complete = all(c["complete"] for c in criteria.values())
        score = statistics.mean(c["score"] for c in criteria.values()) if complete else None
        summaries.append({"frame_size": list(size), "target": target, "files": file_results,
                          "head_target_y": head_target, "criteria": criteria,
                          "measurement_coverage_percent": 100 * sum(c["measured_frames"] for c in criteria.values()) / (3 * len(items)),
                          "max_target_distance_px": maximum, "max_direction_jump_px": pair_max,
                          "max_animation_step_px": temporal_max, "score": score,
                          "status": "review" if not complete else
                                    "pass" if error <= args.tolerance else "deviation",
                          "direction_pairs": direction_pairs,
                          "worst_direction_pair": max(direction_pairs, key=lambda p: p["distance_px"], default=None)})
    return summaries


def make_report(folder: Path, frames: list[dict], sources: list[dict], groups: list[dict],
                args: argparse.Namespace, anchors: dict) -> dict:
    settings = {"id": MODEL_ID, "grid": args.grid, "alpha_threshold": args.alpha_threshold,
                "foot_band": args.foot_band, "tolerance_px": args.tolerance, "pivot": args.pivot,
                "head_y": args.head_y,
                "anchors": anchors, "coordinate_system": "pixel_edges_top_left",
                "top_line": "highest pixel with alpha >= alpha_threshold, including detached fragments",
                "head_target_default": "median of per-file median top_y; files equally weighted",
                "axis_error": "max(target deviation, range of file medians, animation step including loop)",
                "score": "axis = max(0, 100*(1-axis_error/cell_extent)); group = mean of 3 axes; report = min of complete groups",
                "score_weights": {key: 1 / len(CRITERIA) for key, _label, _axis in CRITERIA},
                "tolerance_role": "strict pass/deviation only; does not flatten or clip small score differences",
                "missing_measurement": "null, never assumed perfect; no total score when incomplete"}
    settings = json.loads(json.dumps(settings))
    fingerprint = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    errors = [{"name": s["name"], "reason": s["error"]} for s in sources if "error" in s]
    errors += [{"name": f["id"], "reason": f["error"]} for f in frames if "error" in f]
    notices = []
    if len(groups) > 1:
        notices.append("Verschiedene Zellengrößen: getrennte Gruppen, kein gemeinsamer Pixelvergleich.")
    if len(frames) < 2:
        notices.append("Nur ein Frame: Mittelachse prüfbar, Richtungs-/Animationsvergleich nicht möglich.")
    if any(f.get("confidence") == "review" for f in frames):
        notices.append("Mindestens ein geschätzter Anker benötigt eine visuelle Prüfung.")
    if any(c["status"] == "unavailable" for g in groups for c in g["criteria"].values()):
        notices.append("Nicht alle drei Kriterien messbar: Teilwerte vorhanden, Gesamtwertung nicht bewertbar.")
    state = ("error" if errors or not groups else "deviation" if any(g["status"] == "deviation" for g in groups)
             else "review" if notices or any(g["status"] == "review" for g in groups) else "pass")
    score = (min(g["score"] for g in groups)
             if groups and not errors and all(g["score"] is not None for g in groups) else None)
    return {"tool": "PyImgTestCentral", "version": VERSION, "schema_version": SCHEMA_VERSION,
            "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ"),
            "folder": str(folder), "model": settings, "model_fingerprint": fingerprint,
            "status": state, "score": score,
            "sources": sources, "frames": frames, "groups": groups, "errors": errors,
            "notices": notices,
            "limitations": ["Geschätzter Fußanker; kein semantisch garantierter Drehpunkt.",
                            "Kopf-/Oberkante = oberster Pixel ab Alpha-Schwelle, obere Pixelkante. Hochgehaltene Hände, Waffen oder Fragmente können höher als der Kopf sein.",
                            "Motivhöhe = untere Silhouettenkante minus oberste Pixelkante; ergänzender Messwert, nicht nochmals im Score gewichtet.",
                            "X-Prozente beziehen sich auf die Zellenbreite, Y-/Kopf-Prozente auf die Zellenhöhe. Ein hoher Score ersetzt den pixelgenauen Toleranzbefund nicht.",
                            "Fehlende Richtungs- oder Animationspaare werden als null ausgegeben und erzeugen keine zusätzlichen Gutpunkte.",
                            "Animation: Zeilenreihenfolge, zusätzlich letzter zu erstem Frame; Bewegung kann beabsichtigt sein.",
                            "Raster ohne Dateinamensangabe mit --grid angeben; Unterordner werden nicht eingelesen."],
            "history": None, "files": {}, "alignment": None}


def history_signature(report: dict) -> list:
    if not isinstance(report.get("sources"), list) or not all(isinstance(s, dict) for s in report["sources"]):
        raise CentralError("Ungültiges Quellenmanifest im Verlauf.")
    return [[s.get("name"), s.get("size"), s.get("grid"), s.get("error")]
            for s in report["sources"]]


def attach_history(report: dict, output: Path) -> None:
    for path in sorted(output.glob("central_report_*.json"), reverse=True):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
            continue
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
            if (old["schema_version"] != SCHEMA_VERSION or old["tool"] != report["tool"]
                    or old["folder"] != report["folder"] or old["model_fingerprint"] != report["model_fingerprint"]
                    or history_signature(old) != history_signature(report) or old["errors"]):
                continue
            old_score = old["score"]
            if type(old_score) not in (float, int) or not math.isfinite(old_score) or not 0 <= old_score <= 100:
                continue
            if report["score"] is None or report["errors"]:
                return
            report["history"] = {"previous": path.name, "score_delta": report["score"] - old_score,
                                 "previous_score": old_score,
                                 "same_pixels": [s.get("rgba_sha256") for s in old["sources"]]
                                 == [s.get("rgba_sha256") for s in report["sources"]]}
            return
        except (OSError, ValueError, KeyError, TypeError):
            continue


def ensure_output(folder: Path) -> Path:
    path = folder / OUTPUT_FOLDER
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise CentralError(".compare muss ein regulärer Ordner sein.")
    path.mkdir(exist_ok=True)
    return path


def atomic_new_bytes(path: Path, data: bytes) -> None:
    """Neue Datei exklusiv veröffentlichen; vorhandene Reports nie ersetzen."""
    fd, temporary_name = tempfile.mkstemp(prefix=".central-", dir=path.parent)
    temporary = Path(temporary_name)
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
            with path.open("xb") as stream:
                stream.write(data)
    finally:
        temporary.unlink(missing_ok=True)


def json_bytes(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def png_bytes(image: Image.Image) -> bytes:
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_figure(report: dict) -> bytes:
    """Kontaktstreifen mit EINEM Maßstab pro Größengruppe, ohne Motivbeschnitt."""
    items = report["frames"]
    if not items:
        items = [{"id": s["name"], "name": s["name"], "error": s.get("error", "Nicht messbar")}
                 for s in report["sources"]]
    columns = min(8, len(items))
    card_w, card_h, top = 270, 450, 148
    height = top + math.ceil(len(items) / columns) * card_h + 40
    figure = Image.new("RGB", (max(960, columns * card_w), height), "#101823")
    draw = ImageDraw.Draw(figure)
    font, small, title = load_font(15), load_font(12), load_font(22)
    draw.text((16, 12), "PyImgTestCentral - X-Achse, Fusslinie & Kopf-/Oberkante", fill="#edf4ff", font=title)
    draw.text((16, 45), "Gruen: Zielachsen inkl. obere Linie | Orange: Fussanker / Ist-Achsen | Pink: oberster Pixel", fill="#c3cede", font=small)
    draw.text((16, 67), "Gleicher Massstab je Zellengroesse; komplette Zellen. X nach rechts, Y nach unten.", fill="#c3cede", font=small)
    draw.text((16, 88), f"Toleranz: {report['model']['tolerance_px']:g} px | Status: {report['status']} | Fussanker sind Schaetzungen.", fill="#c3cede", font=small)
    draw.text((16, 109), "Teilwerte: X, Fuss-Y, Kopf-Y je 1/3. Prozentabweichung relativ zur Zellenbreite/-hoehe.", fill="#c3cede", font=small)
    score_text = f"{report['score']:.2f}%" if report['score'] is not None else "nicht bewertbar"
    summary = f"Gesamt: {score_text}"
    if len(report["groups"]) == 1:
        group = report["groups"][0]
        c = group["criteria"]
        summary += (f" | X {number(c['x_axis']['score'], '%')}"
                    f" | Fuss {number(c['foot_line']['score'], '%')}"
                    f" | Kopf {number(c['head_line']['score'], '%')}"
                    f" | Ziel X/Y {group['target'][0]:.1f}/{group['target'][1]:.1f}"
                    f" | Kopfziel Y {number(group['head_target_y'])}")
    draw.text((16, 128), summary, fill="#edf4ff", font=small)
    cached_name, cached_image = None, None
    try:
        for index, item in enumerate(items):
            ox, oy = (index % columns) * card_w, top + (index // columns) * card_h
            draw.rectangle((ox + 4, oy + 4, ox + card_w - 4, oy + card_h - 4), outline="#364558")
            label = clean(item["id"])
            while len(label) > 6 and draw.textbbox((0, 0), label, font=small)[2] > card_w - 20:
                label = label[:-5] + "..."
            draw.text((ox + 10, oy + 10), label, fill="#f4f7fc", font=small)
            if "anchor" not in item:
                draw.text((ox + 12, oy + 85), "NICHT MESSBAR", fill="#ff9b78", font=font)
                continue
            if cached_name != item["name"]:
                if cached_image is not None:
                    cached_image.close()
                cached_name = item["name"]
                cached_image = open_rgba(Path(report["folder"]) / cached_name)
            width, height = item["size"]
            x, y = item["origin"]
            scale = min(216 / width, 244 / height, 1.0)
            sw, sh = max(1, round(width * scale)), max(1, round(height * scale))
            left, upper = ox + (card_w - sw) // 2, oy + 34 + (244 - sh) // 2
            for yy in range(0, sh, 10):
                for xx in range(0, sw, 10):
                    draw.rectangle((left + xx, upper + yy, left + min(xx + 9, sw - 1),
                                    upper + min(yy + 9, sh - 1)),
                                   fill="#303b48" if (xx // 10 + yy // 10) % 2 else "#26313e")
            with cached_image.crop((x, y, x + width, y + height)) as cell:
                preview = cell.resize((sw, sh), Image.Resampling.NEAREST)
                figure.paste(preview, (left, upper), preview)
            def point(p: list[float]) -> tuple[int, int]:
                return left + round(p[0] * sw / width), upper + round(p[1] * sh / height)
            tx, ty = point(item["target"])
            draw.line((tx, upper, tx, upper + sh), fill="#71edb1", width=1)
            draw.line((left, ty, left + sw, ty), fill="#71edb1", width=1)
            axp, ayp = point(item["anchor"])
            for yy in range(upper, upper + sh, 8):
                draw.line((axp, yy, axp, min(yy + 3, upper + sh)), fill="#ffb95c")
            for xx in range(left, left + sw, 8):
                draw.line((xx, ayp, min(xx + 3, left + sw), ayp), fill="#ffb95c")
            if item.get("head_target_y") is not None:
                _, hy = point([0, item["head_target_y"]])
                draw.line((left, hy, left + sw, hy), fill="#71edb1", width=1)
            if item.get("top_y") is not None:
                _, hy = point([0, item["top_y"]])
                for xx in range(left, left + sw, 8):
                    draw.line((xx, hy, min(xx + 4, left + sw), hy), fill="#ff8fdf", width=2)
            if "foot_band" in item:
                band = item["foot_band"]
                draw.rectangle((*point(band[:2]), *point(band[2:])), outline="#ffb95c")
            for key, color in (("bbox_center", "#73bfff"), ("centroid", "#d79bff"), ("anchor", "#ffb95c")):
                if key in item:
                    px, py = point(item[key])
                    draw.line((px - 4, py, px + 4, py), fill=color, width=2)
                    draw.line((px, py - 4, px, py + 4), fill=color, width=2)
            ax, ay = item["anchor"]
            dx, dy = item["shift_px"]
            draw.text((ox + 12, oy + 283), f"Anker {ax:.1f}, {ay:.1f} px", fill="#ffcc8a", font=small)
            draw.text((ox + 12, oy + 302), f"Verschieben X {dx:+d}, Y {dy:+d} px", fill="#e5eef9", font=small)
            top_y, height_px = item.get("top_y"), item.get("height_px")
            text = (f"Kopf oben {top_y:.1f} | Hoehe {height_px:.1f} px"
                    if top_y is not None and height_px is not None else "Kopf / Hoehe: nicht messbar")
            draw.text((ox + 12, oy + 322), text, fill="#ffb7e9", font=small)
            for n, (key, label) in enumerate((("x_axis", "X"), ("foot_line", "Fuss-Y"), ("head_line", "Kopf-Y"))):
                c = item["criteria"][key]
                text = (f"{label}: {c['offset_px']:+.1f}px / {c['deviation_percent']:.2f}% | {c['score']:.2f}%"
                        if c["score"] is not None else f"{label}: nicht bewertbar")
                draw.text((ox + 12, oy + 343 + 19 * n), text, fill="#e5eef9", font=small)
            if item.get("confidence") == "review":
                draw.text((ox + 12, oy + 410), "Anker visuell pruefen", fill="#ff9b78", font=small)
    finally:
        if cached_image is not None:
            cached_image.close()
    return png_bytes(figure)


def number(value: float | None, suffix: str = "") -> str:
    return "—" if value is None else f"{value:.2f}{suffix}"


def markdown_report(report: dict) -> str:
    lines = ["# PyImgTestCentral", "", f"Bildordner: `{md(report['folder'])}`", "",
             f"Status: **{report['status']}** · Toleranz: {report['model']['tolerance_px']:g} px", "",
             f"Gesamtwertung: **{number(report['score'], ' %') if report['score'] is not None else 'nicht bewertbar'}**", "",
             "Der Fußanker ist eine Schätzung aus der unteren Silhouette. "
             "Ein echter Drehpunkt lässt sich ohne Metadaten nicht eindeutig aus Pixeln ableiten. "
             "Alle Koordinaten liegen im lokalen Frame, Ursprung oben links; X nach rechts, Y nach unten.", ""]
    for group in report["groups"]:
        lines += [f"## Zellengröße {group['frame_size'][0]} × {group['frame_size'][1]}", "",
                  f"Zielanker: {group['target'][0]:.2f}, {group['target'][1]:.2f} px. "
                  "Standard: halbe Zellenbreite und Median der Bodenhöhen, jede Datei gleich gewichtet.", "",
                  f"Obere Ziellinie: **{number(group['head_target_y'], ' px')}**; Standard: Median der oberen Dateimediane. "
                  f"Messabdeckung: {group['measurement_coverage_percent']:.2f} %.", "",
                  "| Kriterium (je ⅓) | Zielabweichung max. | Richtungsstreuung | Animationsschritt inkl. Schleife | Bewertete Abweichung | Bezugsmaß | Teilwertung |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for c in group["criteria"].values():
            lines.append(f"| {c['label']} | {number(c['max_target_deviation_px'], ' px')} | "
                         f"{number(c['direction_spread_px'], ' px')} | {number(c['max_animation_step_px'], ' px')} | "
                         f"{number(c['deviation_px'], ' px')} / {number(c['deviation_percent'], ' %')} | "
                         f"{c['reference_px']} px | {number(c['score'], ' %')} ({c['status']}) |")
        lines += ["", f"Gruppenwertung: {number(group['score'], ' %')}. Fehlende Messungen erhalten keine Gutpunkte.", "",
                  "| Datei | Frames | Anker X / Y | Kopf-/Oberkante Y (Median) | Motivhöhe | Verschiebung X / Y | Frame-Schritt | Schleifenschluss |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for item in group["files"]:
            x, y = item["anchor"]
            dx, dy = item["shift_px"]
            lines.append(f"| {md(item['name'])} | {item['frame_count']} | {x:.2f} / {y:.2f} | "
                         f"{number(item['top_y'], ' px')} | {number(item['height_px'], ' px')} | "
                         f"{dx:+d} / {dy:+d} | {item['max_step_px']:.2f} px | {item['loop_step_px']:.2f} px |")
        worst = group["worst_direction_pair"]
        if worst:
            lines += ["", f"Größter Versatz zwischen Dateimedianen: {worst['distance_px']:.2f} px "
                      f"({md(worst['from'])} ↔ {md(worst['to'])})."]
        lines += ["", f"Größte Abweichung eines Frames vom Ziel: {group['max_target_distance_px']:.2f} px.", ""]
    lines += ["## Einzelmessungen pro Frame / Rasterabschnitt", "",
              "| Frame | Fußanker X / Y | Oberster Pixel Y | Motivhöhe | Δ X (px / %) | Δ Fuß-Y (px / %) | Δ Kopf-Y (px / %) | Bandempfindlichkeit | Befund |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for item in report["frames"]:
        def fmt(key: str) -> str:
            p = item.get(key)
            return f"{p[0]:.2f} / {p[1]:.2f}" if p else "—"
        note = item.get("error") or "; ".join(item.get("notices", [])) or item.get("method", "—")
        offsets = []
        for key, _label, _axis in CRITERIA:
            c = item.get("criteria", {}).get(key, {})
            offsets.append(f"{number(c.get('offset_px'))} / {number(c.get('deviation_percent'))}")
        lines.append(f"| {md(item['id'])} | {fmt('anchor')} | {number(item.get('top_y'))} | "
                     f"{number(item.get('height_px'))} | {' | '.join(offsets)} | "
                     f"{number(item.get('band_sensitivity_px'), ' px')} | {md(note)} |")
    lines += ["", "## Hinweise", ""]
    lines += [f"- {md(t)}" for t in report["notices"] + report["limitations"]]
    lines += [f"- Fehler {md(e['name'])}: {md(e['reason'])}" for e in report["errors"]]
    lines += ["", "Die Prozentzahl ist ein geometrischer Konsistenzindex, keine Wahrscheinlichkeit. "
              "Pro Kriterium zählt das Maximum aus Zielabweichung, Streuung der Dateimediane und Animationsschritt inklusive Schleife. "
              "Abweichung (%) = 100 × Abweichung (px) / Bezugsmaß (Zellenbreite bei X, Zellenhöhe bei Y und Kopf). "
              "Teilwertung = max(0, 100 − Abweichung in %). Die drei Teilwertungen tragen jeweils ein Drittel zur Gruppenwertung bei. "
              "Bei mehreren Zellengrößen gilt die niedrigste vollständige Gruppenwertung. "
              "Die Toleranz entscheidet unabhängig davon über den Befund; 100 % setzt exakte Übereinstimmung voraus. "
              "Motivhöhe, Konturmitte und Schwerpunkt sind zusätzliche Messwerte ohne Doppelgewichtung. "
              "Nicht messbar = keine Gesamtwertung, niemals automatisch 100 %.", ""]
    if report["history"]:
        lines += [f"Vorheriger vergleichbarer Report: `{report['history']['previous']}`; "
                  f"Änderung {report['history']['score_delta']:+.2f} Prozentpunkte.", ""]
    if report["alignment"]:
        lines += [f"Korrekturkopien: `{md(report['alignment']['folder'])}`. "
                  "Neue Zellengröße und Engine-Pivot stehen in alignment.json. "
                  "Die Tabellen oben beschreiben die Eingangsbilder.", ""]
    if report["files"]:
        lines += [f"![Fußanker, Mittelachsen und obere Messlinien]({report['files']['figure']})", ""]
    return "\n".join(lines)


def export_aligned(report: dict, destination: Path, mode: str) -> dict:
    """Ganzzahlige Translation; gemeinsamer Rand verhindert jeden Alpha-Beschnitt."""
    if report["errors"] or len(report["groups"]) != 1:
        raise CentralError("Korrektur benötigt fehlerfreie Eingaben mit einer gemeinsamen Zellengröße.")
    if destination.exists() or destination.is_symlink():
        raise CentralError(f"Korrekturordner muss neu sein: {destination}")
    group = report["groups"][0]
    width, height = group["frame_size"]
    file_shifts = {f["name"]: f["shift_px"] for f in group["files"]}
    planned = []
    pad_x = pad_top = pad_bottom = 0
    for frame in report["frames"]:
        dx, dy = frame["shift_px"] if mode == "frame" else file_shifts[frame["name"]]
        left, top, right, bottom = frame["visible_bbox"]
        # Mindestens ein transparenter Randpixel: nicht nur beschnittfrei,
        # sondern auch im nächsten Test eindeutig vom Zellenrand getrennt.
        pad_x = max(pad_x, 1 - left - dx, right + dx - width + 1)
        pad_top = max(pad_top, 1 - top - dy)
        pad_bottom = max(pad_bottom, bottom + dy - height + 1)
        planned.append({"id": frame["id"], "name": frame["name"], "index": frame["index"],
                        "origin": frame["origin"], "shift_px": [dx, dy], "anchor_before": frame["anchor"]})
    out_width, out_height = width + 2 * pad_x, height + pad_top + pad_bottom
    names = [Path(s["name"]).stem + ".png" for s in report["sources"]]
    if len({n.casefold() for n in names}) != len(names):
        raise CentralError("Mehrere Quellen würden denselben PNG-Dateinamen erhalten.")
    for source in report["sources"]:
        cols, rows = source["grid"]
        if out_width * cols * out_height * rows > MAX_PIXELS:
            raise CentralError("Korrektur würde das Pixelbudget überschreiten.")
    alignment = {"tool": "PyImgTestCentral", "version": VERSION, "folder": str(destination),
                 "mode": mode, "input_frame_size": [width, height],
                 "output_frame_size": [out_width, out_height],
                 "padding": {"left": pad_x, "right": pad_x, "top": pad_top, "bottom": pad_bottom},
                 "pivot_px": [group["target"][0] + pad_x, group["target"][1] + pad_top],
                 "coordinate_system": "pixel_edges_top_left", "sources": report["sources"], "frames": planned}
    alignment["pivot_normalized_top_left"] = [alignment["pivot_px"][0] / out_width,
                                               alignment["pivot_px"][1] / out_height]
    # Ein neuer Ordner ist die Transaktionseinheit; bei Abbruch bleibt er erkennbar unvollständig.
    destination.mkdir(parents=True, exist_ok=False)
    by_source: dict[str, list[dict]] = defaultdict(list)
    for item in planned:
        by_source[item["name"]].append(item)
    for source, name in zip(report["sources"], names):
        cols, rows = source["grid"]
        with open_rgba(Path(report["folder"]) / source["name"]) as image:
            if hashlib.sha256(image.tobytes()).hexdigest() != source["rgba_sha256"]:
                raise CentralError(f"Quelle wurde während der Prüfung verändert: {source['name']}")
            result = Image.new("RGBA", (cols * out_width, rows * out_height))
            for frame in by_source[source["name"]]:
                x, y = frame["origin"]
                dx, dy = frame["shift_px"]
                tx, ty = dx + pad_x, dy + pad_top
                # Erst innerhalb der eigenen Zelle verschieben: kein Übergreifen auf Nachbarframes.
                with image.crop((x, y, x + width, y + height)) as cell:
                    moved = Image.new("RGBA", (out_width, out_height))
                    moved.paste(cell, (tx, ty))  # Keine Alpha-Maske: RGBA-Werte exakt kopieren.
                    col, row = frame["index"] % cols, frame["index"] // cols
                    result.paste(moved, (col * out_width, row * out_height))
                frame["translation_px"] = [tx, ty]
                frame["anchor_after"] = [frame["anchor_before"][0] + tx, frame["anchor_before"][1] + ty]
                frame["residual_px"] = [frame["anchor_after"][i] - alignment["pivot_px"][i] for i in (0, 1)]
            atomic_new_bytes(destination / name, png_bytes(result))
    atomic_new_bytes(destination / "alignment.json", json_bytes(alignment))
    return alignment


def print_report(report: dict, no_color: bool) -> None:
    colored = not no_color and sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"
    def paint(text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if colored else text
    print("\n📐 PyImgTestCentral\n")
    print(f"📁 Bildordner: {clean(report['folder'])}")
    print(f"🖼️  {len(report['sources'])} Dateien · {len(report['frames'])} Frames · Toleranz {report['model']['tolerance_px']:g} px")
    for group in report["groups"]:
        print(f"\n🎯 Zelle {group['frame_size'][0]}×{group['frame_size'][1]} · Zielanker X {group['target'][0]:.2f}, Y {group['target'][1]:.2f}")
        print(f"📐 Obere Ziellinie Y {number(group['head_target_y'])} px · Messabdeckung {group['measurement_coverage_percent']:.2f}%")
        for item in group["files"]:
            x, y = item["anchor"]
            dx, dy = item["shift_px"]
            print(f"  {clean(item['name'])}: Anker ({x:.2f}, {y:.2f}) · Verschieben ({dx:+d}, {dy:+d}) px"
                  f" · Frames {item['frame_count']} · Schritt max. {item['max_step_px']:.2f} px")
            print(f"    Kopf-/Oberkante Y {number(item['top_y'])} px · Motivhöhe {number(item['height_px'])} px")
            for key, label, _axis in CRITERIA:
                c = item["criteria"][key]
                print(f"    {label}: Abweichung {number(c['deviation_px'])} px / {number(c['deviation_percent'])}%"
                      f" · Teilwertung {number(c['score'])}% · {c['status']}")
        worst = group["worst_direction_pair"]
        if worst:
            print(f"↔️  Größter Richtungsversatz: {worst['distance_px']:.2f} px ({clean(worst['from'])} ↔ {clean(worst['to'])})")
        print(f"📏 Zielabweichung max. {group['max_target_distance_px']:.2f} px · Animationsschritt inkl. Schleife max. {group['max_animation_step_px']:.2f} px")
        for c in group["criteria"].values():
            print(f"  📊 {c['label']} (⅓): {number(c['score'])}% · Abweichung {number(c['deviation_px'])} px"
                  f" = {number(c['deviation_percent'])}% von {c['reference_px']} px · {c['status']}")
    score = report["score"]
    score_text = "nicht bewertbar" if score is None else f"[{'█' * round(score / 5)}{'░' * (20 - round(score / 5))}] {score:.2f}%"
    label = {"pass": "✅ Ausrichtung und Kopfhöhe innerhalb der Toleranz", "deviation": "❌ Positions-/Höhenabweichung erkannt",
             "review": "⚠️ Prüfung eingeschränkt", "error": "❌ Eingaben nicht vollständig messbar"}[report["status"]]
    print(paint(f"\n{label} · {score_text}", "32" if report["status"] == "pass" else "33"))
    print("ℹ️ Fußanker geschätzt; Versätze in Animationen können beabsichtigt sein.")
    print("ℹ️ X, Fuß-Y und Kopf-Y zählen je ⅓. Teilwertung = 100 − Abweichung in % der Zellenbreite/-höhe.")
    print("ℹ️ Die obere Linie misst den obersten Pixel ab Alpha-Schwelle. Toleranzbefund und Prozentwertung sind getrennt.")
    for text in report["notices"]:
        print(f"⚠️ {clean(text)}")
    notices_by_file: dict[tuple[str, str], int] = defaultdict(int)
    for item in report["frames"]:
        for note in item.get("notices", []):
            notices_by_file[item["name"], note] += 1
    for (name, note), count in notices_by_file.items():
        print(f"⚠️ {clean(name)} ({count} Frames): {clean(note)}")
    for error in report["errors"]:
        print(f"❌ {clean(error['name'])}: {clean(error['reason'])}")
    if report["history"]:
        print(f"📈 Vergleichbarer Vorlauf: {report['history']['score_delta']:+.2f} Prozentpunkte")
    if report["alignment"]:
        a = report["alignment"]
        print(f"💾 Korrekturkopien: {a['folder']} · neue Zelle {a['output_frame_size']} · Pivot {a['pivot_px']}")
    for kind, name in report["files"].items():
        print(f"📄 {kind}: {OUTPUT_FOLDER}/{name}")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", nargs="?", type=Path, default=Path.cwd(), help="Bildordner; Standard: aktueller Ordner")
    parser.add_argument("--grid", type=grid_value, default=None, metavar="SPALTENxZEILEN", help="Standard auto aus Dateinamen, sonst 1x1; --grid 1x1 erzwingt Einzelbilder")
    parser.add_argument("--alpha-threshold", type=int, default=32, help="Silhouettenschwelle 1..255 (Standard 32)")
    parser.add_argument("--foot-band", type=float, default=0.12, help="Anteil der unteren Motivhöhe, 0.03..0.4 (Standard 0.12)")
    parser.add_argument("--tolerance", type=float, default=2.0, help="Erlaubter Abstand in Originalpixeln (Standard 2)")
    parser.add_argument("--pivot", type=point_value, metavar="X,Y", help="Gemeinsamer Zielanker in lokalen Zellenpixeln")
    parser.add_argument("--head-y", type=float, metavar="PIXEL", help="Obere Ziellinie; Standard: Median der obersten Pixel je Dateimedian")
    parser.add_argument("--anchors", type=Path, help="JSON mit manuell festgelegten Quellankern pro Datei/Frame")
    parser.add_argument("--align", type=Path, metavar="NEUER_ORDNER", help="Zentrierte PNG-Kopien und alignment.json exportieren; relativer Pfad zum Bildordner")
    parser.add_argument("--align-mode", choices=("sheet", "frame"), default="sheet", help="Ganze Bögen verschieben (sheet), oder jeden Frame (frame)")
    parser.add_argument("--strict", action="store_true", help="Bei Versatz/eingeschränkter Prüfung Exitcode 2 statt 0")
    parser.add_argument("--no-report", action="store_true", help="Nur Terminal; keine Dateien/Verlauf; nicht mit --align kombinierbar")
    parser.add_argument("--no-color", action="store_true", help="ANSI-Farben ausschalten")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.alpha_threshold <= 255:
        parser.error("--alpha-threshold muss zwischen 1 und 255 liegen.")
    if not math.isfinite(args.foot_band) or not 0.03 <= args.foot_band <= 0.4:
        parser.error("--foot-band muss zwischen 0.03 und 0.4 liegen.")
    if not math.isfinite(args.tolerance) or args.tolerance <= 0:
        parser.error("--tolerance muss eine positive, endliche Pixelzahl sein.")
    if args.head_y is not None and (not math.isfinite(args.head_y) or args.head_y < 0):
        parser.error("--head-y muss eine nichtnegative, endliche Pixelzahl sein.")
    if args.no_report and args.align:
        parser.error("--no-report erzeugt keine Dateien und ist nicht mit --align kombinierbar.")
    try:
        folder = args.folder.resolve()
        anchors = load_anchors(args.anchors)
        frames, sources = load_frames(folder, args, anchors)
        groups = assess(frames, sources, args)
        report = make_report(folder, frames, sources, groups, args, anchors)
        if args.align:
            destination = args.align if args.align.is_absolute() else folder / args.align
            report["alignment"] = export_aligned(report, destination, args.align_mode)
        if not args.no_report:
            output = ensure_output(folder)
            attach_history(report, output)
            report["files"] = {"figure": f"central_figure_{report['run_id']}.png",
                               "markdown": f"central_report_{report['run_id']}.md",
                               "json": f"central_report_{report['run_id']}.json"}
            atomic_new_bytes(output / report["files"]["figure"], make_figure(report))
            atomic_new_bytes(output / report["files"]["markdown"], markdown_report(report).encode("utf-8"))
            atomic_new_bytes(output / report["files"]["json"], json_bytes(report))
        print_report(report, args.no_color)
        return 1 if report["errors"] or not groups else 2 if args.strict and report["status"] != "pass" else 0
    except KeyboardInterrupt:
        print("\nAbgebrochen. Quelldateien bleiben unverändert.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        print(f"FEHLER: {clean(str(exc))}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
