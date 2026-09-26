#!/usr/bin/env python3
"""PyImgCompare: Bildgruppen im aktuellen Arbeitsordner vergleichen.

Das Werkzeug liest unterstützte, statische Rasterbilder direkt aus dem
aktuellen Terminalordner (ohne Unterordner), prüft globale Set-Merkmale sowie
die Geometrie automatisch erkannter Bildtypen und erzeugt im versteckten
Ordner ``.compare``. Jeder Lauf erhält eine UTC-ID, damit frühere Ergebnisse
erhalten bleiben:

* ``spritesheet_<UTC-ID>.png`` – kompaktes Raster oder Richtungsraster
* ``report_<UTC-ID>.md``       – ausführlicher, lesbarer Bericht
* ``report_<UTC-ID>.json``     – dieselben Ergebnisse für weitere Werkzeuge

Ein Fortschrittswert wird nur mit dem letzten gültigen JSON-Report desselben
logischen Dateisatzes und Bewertungsmodells verglichen. Vorhandene Reportdateien
werden nie ersetzt.

Mit ``--no-report`` erfolgt die Ausgabe ausschließlich im Terminal. Das für
den Arbeitsablauf benötigte Spritesheet wird dann nur im System-Temp-Verzeichnis
angelegt und nach der Berechnung automatisch entfernt; ``.compare`` bleibt
unangetastet.

Unterstützt werden PNG, JPEG, WebP, AVIF, BMP, TIFF, statisches GIF, TGA,
ICO und Netpbm-Formate, soweit die installierte Pillow-Version den jeweiligen
Codec bereitstellt. Versteckte Einträge, symbolische Links und sämtliche
Unterordner werden ignoriert. Die Quelldateien bleiben unverändert.

Abhängigkeit: Python >= 3.10 und Pillow >= 9.1
Installation: python3 -m pip install --upgrade Pillow
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import math
import os
import re
import statistics
import sys
import tempfile
import unicodedata
import warnings
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path
from typing import Any

VERSION = "1.4.0"
SCHEMA_VERSION = 5
SCORING_MODEL_ID = "sprite-consistency-v3"
SCORING_MODEL_VERSION = 3
OUTPUT_FOLDER = ".compare"
SPRITESHEET_NAME = "spritesheet.png"
MARKDOWN_REPORT_NAME = "report.md"
JSON_REPORT_NAME = "report.json"
MAX_REPORT_HISTORY_BYTES = 16 * 1024 * 1024

# Bewusst nicht nur PNG. Dateien werden trotzdem erst nach erfolgreichem
# Öffnen als Bilder gewertet; optionale Formate benötigen den Pillow-Codec.
SUPPORTED_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".jpe",
        ".jfif",
        ".webp",
        ".avif",
        ".bmp",
        ".dib",
        ".tif",
        ".tiff",
        ".gif",
        ".tga",
        ".icb",
        ".vda",
        ".vst",
        ".ico",
        ".ppm",
        ".pgm",
        ".pbm",
        ".pnm",
    }
)

ANALYSIS_EDGE = 256
COLOR_EDGE = 96
SHAPE_EDGE = 64
SHAPE_PADDING = 4
SILHOUETTE_ALPHA_THRESHOLD = 32
OPAQUE_BACKGROUND_LIMIT = 0.01
LAB_HISTOGRAM_BINS = 8
DOMINANT_PALETTE_SIZE = 5
COLOR_LAYOUT_EDGE = 12
ALPHA_LAYOUT_EDGE = 32
MAX_SHEET_PIXELS = 64_000_000
BAR_WIDTH = 20
NEARLY_EMPTY_MEDIAN_RATIO = 0.10

SCORE_WEIGHTS: dict[str, float] = {
    "size": 0.15,
    "coverage": 0.08,
    "position": 0.07,
    "anchor": 0.15,
    "alpha": 0.08,
    "color": 0.22,
    "color_layout": 0.12,
    "shape": 0.13,
}
GLOBAL_METRICS = frozenset({"alpha", "color"})
ACTION_METRICS = frozenset({"coverage", "position", "shape"})
DIRECTIONAL_METRICS = frozenset({"color_layout"})
ANCHOR_REFERENCE_HEIGHT = 128.0
ANCHOR_VERTICAL_SHARE = 0.80
ANCHOR_HORIZONTAL_SHARE = 0.20
SIZE_WARNING_THRESHOLD = 90.0
COLOR_WARNING_THRESHOLD = 55.0
COLOR_CRITICAL_THRESHOLD = 30.0
ANCHOR_WARNING_THRESHOLD = 70.0
ANCHOR_CRITICAL_THRESHOLD = 40.0
COLOR_LAYOUT_WARNING_THRESHOLD = 40.0
MIXED_CLUSTER_JOIN_THRESHOLD = 75.0
MIXED_ACROSS_MAXIMUM = 72.0
MIXED_MINIMUM_GAP = 20.0

METRIC_LABELS = {
    "size": "Größe",
    "coverage": "Sichtfläche",
    "position": "Position",
    "anchor": "Sprite-Anker",
    "alpha": "Alpha",
    "color": "Farbe",
    "color_layout": "Räumliche Farbe",
    "shape": "Form",
}

STATUS_DATA = {
    "very_good": ("Sehr gut kompatibel", "✅", "32"),
    "good": ("Gut kompatibel", "🟢", "32"),
    "warning": ("Warnung", "⚠️", "33"),
    "critical": ("Kritisch", "❌", "31"),
}
STATUS_RANK = {"very_good": 0, "good": 1, "warning": 2, "critical": 3}

DIRECTION_POSITIONS: dict[str, tuple[int, int]] = {
    "nw": (0, 0),
    "n": (0, 1),
    "ne": (0, 2),
    "w": (1, 0),
    "e": (1, 2),
    "sw": (2, 0),
    "s": (2, 1),
    "se": (2, 2),
}

DIRECTION_LABELS = {
    "nw": "Nordwest",
    "n": "Nord",
    "ne": "Nordost",
    "w": "West",
    "e": "Ost",
    "sw": "Südwest",
    "s": "Süd",
    "se": "Südost",
}

MIRROR_DIRECTIONS = {
    "e": "w",
    "w": "e",
    "ne": "nw",
    "nw": "ne",
    "se": "sw",
    "sw": "se",
}

DIRECTION_ALIASES = {
    "nw": "nw",
    "northwest": "nw",
    "nordwest": "nw",
    "n": "n",
    "north": "n",
    "nord": "n",
    "ne": "ne",
    "no": "ne",
    "northeast": "ne",
    "nordost": "ne",
    "w": "w",
    "west": "w",
    "e": "e",
    "o": "e",
    "east": "e",
    "ost": "e",
    "sw": "sw",
    "southwest": "sw",
    "sudwest": "sw",
    "s": "s",
    "south": "s",
    "sud": "s",
    "se": "se",
    "so": "se",
    "southeast": "se",
    "sudost": "se",
}

DIRECTION_PAIRS = {
    ("north", "west"): "nw",
    ("nord", "west"): "nw",
    ("north", "east"): "ne",
    ("nord", "ost"): "ne",
    ("south", "west"): "sw",
    ("sud", "west"): "sw",
    ("south", "east"): "se",
    ("sud", "ost"): "se",
}

# Geometrie nur zwischen vergleichbaren Bewegungstypen mitteln. Farbe, Canvas
# und Alpha bleiben trotzdem global, damit beispielsweise ein blauer Ausreißer
# in einem überwiegend grünen Set zuverlässig auffällt.
ACTION_ALIASES = {
    "art": "artwork",
    "artwork": "artwork",
    "concept": "artwork",
    "portrait": "artwork",
    "walk": "walk",
    "walking": "walk",
    "gehen": "walk",
    "run": "run",
    "running": "run",
    "lauf": "run",
    "laufen": "run",
    "rennen": "run",
    "stand": "stand",
    "standing": "stand",
    "idle": "stand",
    "jump": "jump",
    "jumping": "jump",
    "sprung": "jump",
    "attack": "attack",
    "angriff": "attack",
    "hurt": "hurt",
    "hit": "hurt",
    "death": "death",
    "dead": "death",
    "tod": "death",
}

SCORING_MODEL_DESCRIPTION: dict[str, Any] = {
    "id": SCORING_MODEL_ID,
    "version": SCORING_MODEL_VERSION,
    "weights": SCORE_WEIGHTS,
    "aggregation": {
        "method": "renormalized_weighted_mean",
        "missing_metric_policy": (
            "redistribute_proportionally_across_available_metrics"
        ),
        "findings_change_numeric_score": False,
        "trimmed_mean_minimum_peers": 5,
        "duplicate_cluster_weight": 1,
    },
    "thresholds": {
        "empty_total_score": 0.0,
        "nearly_empty_median_ratio": NEARLY_EMPTY_MEDIAN_RATIO,
        "size_warning": SIZE_WARNING_THRESHOLD,
        "color_warning": COLOR_WARNING_THRESHOLD,
        "color_critical": COLOR_CRITICAL_THRESHOLD,
        "anchor_warning": ANCHOR_WARNING_THRESHOLD,
        "anchor_critical": ANCHOR_CRITICAL_THRESHOLD,
        "color_layout_warning": COLOR_LAYOUT_WARNING_THRESHOLD,
        "mixed_cluster_join": MIXED_CLUSTER_JOIN_THRESHOLD,
        "mixed_across_maximum": MIXED_ACROSS_MAXIMUM,
        "mixed_minimum_gap": MIXED_MINIMUM_GAP,
    },
    "metric_versions": {
        "mask": 2,
        "anchor": 2,
        "alpha": 2,
        "color": 2,
        "color_layout": 2,
        "shape": 2,
    },
    "layout": {
        "color_cells": [COLOR_LAYOUT_EDGE, COLOR_LAYOUT_EDGE],
        "alpha_cells": [ALPHA_LAYOUT_EDGE, ALPHA_LAYOUT_EDGE],
    },
    "metric_scopes": {
        "global": sorted(GLOBAL_METRICS),
        "action_group": sorted(ACTION_METRICS),
        "directional": sorted(DIRECTIONAL_METRICS),
        "anchor_vertical": "action_group_consensus",
        "anchor_horizontal": "same_direction_or_horizontal_mirror",
    },
    "anchor_curve": [[0, 100], [1, 92], [2, 78], [3, 58], [5, 25]],
    "anchor_distance": (
        "canonical_128px_per_subject_height; 80_percent_vertical_group_consensus; "
        "20_percent_horizontal_same_direction_or_mirror"
    ),
    "mask_rule": (
        "alpha_for_transparency_else_border_foreground_and_content_edges; "
        "isolated_bottom_pixel_rejected"
    ),
    "direction_rule": (
        "directional_metrics_use_same_direction_then_horizontal_mirror; "
        "unavailable_without_compatible_peer"
    ),
}
SCORING_MODEL_FINGERPRINT = (
    "sha256:"
    + hashlib.sha256(
        json.dumps(
            SCORING_MODEL_DESCRIPTION,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
)


class SkipImage(Exception):
    """Eine erkannte Datei kann bewusst nicht sicher ausgewertet werden."""


@dataclass(frozen=True)
class ImageFeatures:
    path: Path
    logical_name: str
    rgba_sha256: str
    width: int
    height: int
    total_pixels: int
    visible_pixels: int
    transparent_pixels: int
    partial_pixels: int
    visible_fraction: float
    transparent_fraction: float
    comparison_pixels: int
    comparison_fraction: float
    comparison_background_fraction: float
    alpha_bbox: tuple[int, int, int, int] | None
    bbox: tuple[int, int, int, int] | None
    centroid: tuple[float, float] | None
    mask_source: str
    mean_alpha: float
    soft_alpha_fraction: float
    alpha_histogram: tuple[float, ...]
    alpha_layout: bytes
    color_histogram: tuple[float, ...]
    mean_lab: tuple[float, float, float]
    dominant_palette: tuple[tuple[float, float, float, float], ...]
    luminance: float
    saturation: float
    color_weight: float
    color_layout: tuple[tuple[float, float, float, float] | None, ...]
    shape_mask: bytes
    mirrored_shape_mask: bytes
    shape_pixels: int
    shape_aspect: float | None
    shape_edge_pixels: int
    shape_components: int
    anchor_x_px: float | None
    anchor_y_px: float | None
    bottom_margin_px: float | None
    left_anchor_offset_px: float | None
    anchor_confidence: float
    hidden_rgb_pixels: int
    direction: str | None
    action_group: str
    duplicate_of: str | None = None
    duplicate_cluster_size: int = 1


@dataclass(frozen=True)
class ScoreFinding:
    metric: str
    severity: str
    value: float
    threshold: float
    message: str


@dataclass(frozen=True)
class ScoredImage:
    features: ImageFeatures
    scores: Mapping[str, float | None]
    effective_weights: Mapping[str, float]
    metric_peer_counts: Mapping[str, int]
    weighted_score: float
    total_score: float
    status: str
    score_status: str
    classification: str
    confidence: str
    comparison_count: int
    group_median_score: float
    group_score_stddev: float
    worst_comparison_file: str | None
    worst_comparison_score: float
    findings: tuple[ScoreFinding, ...]
    anchor_diagnostics: Mapping[str, Any]
    hints: tuple[str, ...]


@dataclass(frozen=True)
class SkippedFile:
    path: Path
    reason: str


@dataclass(frozen=True)
class SheetLayout:
    kind: str
    columns: int
    rows: int
    positions: Mapping[Path, tuple[int, int]]


@dataclass(frozen=True)
class ReportPaths:
    run_id: str
    created_at_utc: str
    spritesheet: Path
    markdown: Path
    json: Path


@dataclass(frozen=True)
class PreviousReport:
    path: Path
    average_score: float
    scoring_model_fingerprint: str | None
    logical_names: tuple[str, ...] | None
    items: Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True)
class PreviousReportSearch:
    report: PreviousReport | None
    invalid_reports_seen: bool


@dataclass(frozen=True)
class HistoryResult:
    status: str
    reason: str
    previous_report: str | None = None
    previous_average_score: float | None = None
    current_average_score: float | None = None
    delta_percentage_points: float | None = None
    direction: str | None = None
    item_changes: Mapping[str, Mapping[str, Any]] | None = None


class Theme:
    """ANSI-Farben nur verwenden, wenn das Terminal sie sinnvoll darstellt."""

    RESET = "\033[0m"

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def paint(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}{self.RESET}"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="PyImgCompare",
        description=(
            "Vergleicht alle unterstützten Bilder direkt im aktuellen "
            "Terminalordner als Gruppe. Keine Unterordner und keine Rekursion."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ausgabe im aktuellen Ordner (für jeden Lauf mit neuer UTC-ID):
  .compare/spritesheet_<UTC-ID>.png
  .compare/report_<UTC-ID>.md
  .compare/report_<UTC-ID>.json

Vergleich:
  Das Modell sprite-consistency-v3 prüft Canvas, Motivfläche, Position,
  Bodenanker, Alpha, Lab-Palette, räumliche Farbverteilung und Silhouette.
  Der Prozentwert ist das gewichtete Mittel aller verfügbaren Teilwerte. Fehlt
  ein zulässiger Richtungsvergleich, wird dessen Gewicht auf die übrigen Werte
  verteilt. Auffälligkeiten ändern den Status, deckeln aber nicht die Prozentzahl.
  Exakte RGBA-Duplikate erhalten zusammen nur Gruppengewicht 1.

Intelligentes Raster:
  Enthalten genügend Dateinamen eindeutige Richtungen wie n, no/ne, o/e,
  so/se, s, sw, w oder nw, wird ein Kompassraster verwendet. Andernfalls
  entsteht automatisch ein möglichst kompaktes Raster.

Mindestens zwei lesbare, statische Bilder sind erforderlich. Quelldateien
werden nie verändert. Frühere Dateien in .compare bleiben erhalten; neue Reports
zeigen eine Veränderung nur bei identischem logischem Bildbestand und identischem
Bewertungsmodell. Mit --no-report bleibt nur die gleiche Terminalanzeige. Das
Spritesheet wird temporär erzeugt und wieder entfernt; .compare wird weder
gelesen, angelegt noch geändert.
""",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="ANSI-Farben auch in einem Terminal abschalten.",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help=(
            "Nur im Terminal ausgeben; temporäres Spritesheet wieder entfernen "
            "sowie keinen Verlauf laden und .compare nicht verändern."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return make_parser().parse_args(argv)


def load_pillow() -> None:
    global Image, ImageFilter, ImageOps
    try:
        from PIL import Image, ImageFilter, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "Pillow fehlt. Installieren mit:\n  python3 -m pip install --upgrade Pillow"
        ) from exc
    if not hasattr(Image, "Resampling"):
        raise RuntimeError(
            "Pillow ist zu alt (mindestens 9.1 erforderlich). Aktualisieren mit:\n"
            "  python3 -m pip install --upgrade Pillow"
        )
    warnings.simplefilter("error", Image.DecompressionBombWarning)


def find_images(folder: Path) -> list[Path]:
    """Nur passende normale Dateien direkt im angegebenen Ordner finden."""
    return sorted(
        (
            path
            for path in folder.iterdir()
            if not path.name.startswith(".")
            and not path.is_symlink()
            and path.is_file()
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ),
        key=lambda path: (path.name.casefold(), path.name),
    )


def normalized_name_tokens(stem: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", stem.casefold())
    ascii_like = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", ascii_like)


def logical_name(path: Path) -> str:
    """Einen stabilen, plattformneutralen Namen für Historienvergleiche bilden."""
    tokens = normalized_name_tokens(path.stem)
    stem = (
        "-".join(tokens)
        if tokens
        else unicodedata.normalize("NFKC", path.stem).casefold()
    )
    return f"{stem}{path.suffix.casefold()}"


def rgba_content_hash(image: Any, raw_rgba: bytes | None = None) -> str:
    """Canvas und dekodierte RGBA-Pixel unabhängig von der Dateikodierung hashen."""
    digest = hashlib.sha256()
    digest.update(b"PyImgCompare-RGBA-v1\0")
    digest.update(image.width.to_bytes(8, "big"))
    digest.update(image.height.to_bytes(8, "big"))
    digest.update(raw_rgba if raw_rgba is not None else image.tobytes())
    return digest.hexdigest()


def detect_direction(stem: str) -> str | None:
    """Eindeutige, getrennte Richtungsangabe aus einem Dateinamen lesen."""
    tokens = normalized_name_tokens(stem)
    matches: list[str] = []
    consumed: set[int] = set()
    for index in range(len(tokens) - 1):
        direction = DIRECTION_PAIRS.get((tokens[index], tokens[index + 1]))
        if direction is not None:
            matches.append(direction)
            consumed.update((index, index + 1))
    for index, token in enumerate(tokens):
        if index not in consumed and token in DIRECTION_ALIASES:
            matches.append(DIRECTION_ALIASES[token])
    unique = set(matches)
    return next(iter(unique)) if len(unique) == 1 else None


def detect_action_group(stem: str) -> str:
    """Letzten eindeutigen Bewegungs-/Bildtyp aus dem Dateinamen ableiten."""
    matches = [
        ACTION_ALIASES[token]
        for token in normalized_name_tokens(stem)
        if token in ACTION_ALIASES
    ]
    return matches[-1] if matches else "general"


def open_static_rgba(path: Path) -> Any:
    """Ein einzelnes 8-Bit-Bild laden und EXIF-Ausrichtung anwenden."""
    with Image.open(path) as opened:
        if getattr(opened, "is_animated", False) or getattr(opened, "n_frames", 1) > 1:
            raise SkipImage("animierte oder mehrseitige Datei")
        if opened.mode in {"I", "F"} or opened.mode.startswith("I;16"):
            raise SkipImage("HDR-/16-Bit-Graubild; keine automatische 8-Bit-Reduktion")
        opened.load()
        oriented = ImageOps.exif_transpose(opened)
        result = oriented.convert("RGBA")
        result.info.clear()
        return result


def resized_for_analysis(image: Any, max_edge: int) -> Any:
    """Seitenverhältnis erhalten und transparente Farben korrekt filtern."""
    if max(image.size) <= max_edge:
        return image.copy()
    scale = max_edge / max(image.size)
    size = (
        max(1, round(image.width * scale)),
        max(1, round(image.height * scale)),
    )
    premultiplied = image.convert("RGBa")
    resized = None
    try:
        resized = premultiplied.resize(size, Image.Resampling.LANCZOS)
        return resized.convert("RGBA")
    finally:
        premultiplied.close()
        if resized is not None:
            resized.close()


def flattened_pixels(image: Any) -> Iterable[Any]:
    """Pixeliterator für alte und neue Pillow-Versionen ohne Abkündigungswarnung."""
    getter = getattr(image, "get_flattened_data", None)
    return getter() if getter is not None else image.getdata()


def alpha_centroid(alpha: Any) -> tuple[float, float] | None:
    """Alpha-gewichteten Mittelpunkt in normierten Canvas-Koordinaten messen."""
    width, height = alpha.size
    total_weight = 0
    weighted_x = 0.0
    weighted_y = 0.0
    for index, value in enumerate(flattened_pixels(alpha)):
        if value:
            x = index % width
            y = index // width
            total_weight += value
            weighted_x += (x + 0.5) * value
            weighted_y += (y + 0.5) * value
    if total_weight == 0:
        return None
    return (
        weighted_x / total_weight / width,
        weighted_y / total_weight / height,
    )


def normalized_alpha_histogram(
    histogram: Sequence[int], visible: int
) -> tuple[float, ...]:
    bins = [0] * 16
    if visible == 0:
        return tuple(0.0 for _ in bins)
    for value, count in enumerate(histogram[1:], start=1):
        bins[min(15, value // 16)] += count
    return tuple(count / visible for count in bins)


def rgb_to_lab(red: int, green: int, blue: int) -> tuple[float, float, float]:
    """sRGB über D65-XYZ in CIE L*a*b* umrechnen."""

    def linear(channel: int) -> float:
        value = channel / 255.0
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    r = linear(red)
    g = linear(green)
    b = linear(blue)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def pivot(value: float) -> float:
        delta = 6.0 / 29.0
        return (
            value ** (1.0 / 3.0)
            if value > delta**3
            else value / (3 * delta**2) + 4.0 / 29.0
        )

    fx = pivot(x)
    fy = pivot(y)
    fz = pivot(z)
    return 116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)


def lab_histogram_index(lightness: float, green_red: float, blue_yellow: float) -> int:
    bins = LAB_HISTOGRAM_BINS
    light_bin = min(bins - 1, max(0, int(lightness / 100.0 * bins)))
    green_red_bin = min(bins - 1, max(0, int((green_red + 128.0) / 256.0 * bins)))
    blue_yellow_bin = min(bins - 1, max(0, int((blue_yellow + 128.0) / 256.0 * bins)))
    return (light_bin * bins + green_red_bin) * bins + blue_yellow_bin


def histogram_percentile(histogram: Sequence[int], quantile: float) -> int:
    total = sum(histogram)
    if total == 0:
        return 255
    target = total * clamp_unit(quantile)
    accumulated = 0
    for value, count in enumerate(histogram):
        accumulated += count
        if accumulated >= target:
            return value
    return 255


def content_comparison_mask(image: Any) -> Any:
    """Motivhinweis für undurchsichtige Bilder aus Randfarbe und Kanten bauen."""
    sample = resized_for_analysis(image, ANALYSIS_EDGE)
    rgb = sample.convert("RGB")
    gray = edges = dilated_edges = None
    try:
        width, height = rgb.size
        pixels = list(flattened_pixels(rgb))
        border_indices = set(range(width))
        border_indices.update(range((height - 1) * width, height * width))
        border_indices.update(row * width for row in range(height))
        border_indices.update(row * width + width - 1 for row in range(height))
        border = [pixels[index] for index in border_indices]
        border_color = tuple(
            statistics.median(pixel[channel] for pixel in border)
            for channel in range(3)
        )
        border_distances = [math.dist(pixel, border_color) for pixel in border]
        median_distance = statistics.median(border_distances)
        deviation = statistics.median(
            abs(distance - median_distance) for distance in border_distances
        )
        color_threshold = max(24.0, median_distance + 3.0 * max(2.0, deviation))
        foreground = bytearray(
            255 if math.dist(pixel, border_color) > color_threshold else 0
            for pixel in pixels
        )
        foreground_fraction = foreground.count(255) / len(foreground)
        use_foreground = 0.002 <= foreground_fraction <= 0.85

        gray = rgb.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_values = bytearray(flattened_pixels(edges))
        for x in range(width):
            edge_values[x] = 0
            edge_values[(height - 1) * width + x] = 0
        for y in range(height):
            edge_values[y * width] = 0
            edge_values[y * width + width - 1] = 0
        edge_histogram = [0] * 256
        for value in edge_values:
            if value:
                edge_histogram[value] += 1
        edge_threshold = max(12, histogram_percentile(edge_histogram, 0.75))
        edge_binary = Image.frombytes(
            "L",
            (width, height),
            bytes(255 if value >= edge_threshold else 0 for value in edge_values),
        )
        try:
            dilated_edges = edge_binary.filter(ImageFilter.MaxFilter(3))
        finally:
            edge_binary.close()
        edge_pixels = flattened_pixels(dilated_edges)
        if use_foreground:
            combined = bytes(
                255 if foreground_value or edge_value else 0
                for foreground_value, edge_value in zip(foreground, edge_pixels)
            )
        else:
            combined = bytes(edge_pixels)
        return Image.frombytes("L", (width, height), combined)
    finally:
        for buffer in (dilated_edges, edges, gray, rgb, sample):
            if buffer is not None:
                buffer.close()


def comparison_mask(
    image: Any, alpha: Any, transparent_fraction: float
) -> tuple[Any, str]:
    """Alpha bei Freistellern, Inhaltskanten bei nahezu opaken Bildern nutzen."""
    if transparent_fraction >= OPAQUE_BACKGROUND_LIMIT:
        return alpha.copy(), "alpha"
    return content_comparison_mask(image), "content_edges"


def scaled_mask_bbox(
    mask: Any, original_size: tuple[int, int]
) -> tuple[int, int, int, int] | None:
    bbox = mask.getbbox()
    if bbox is None:
        return None
    width, height = original_size
    scale_x = width / mask.width
    scale_y = height / mask.height
    return (
        max(0, math.floor(bbox[0] * scale_x)),
        max(0, math.floor(bbox[1] * scale_y)),
        min(width, math.ceil(bbox[2] * scale_x)),
        min(height, math.ceil(bbox[3] * scale_y)),
    )


def sprite_anchor(
    mask: Any, original_size: tuple[int, int]
) -> tuple[float | None, float | None, float | None, float | None, float]:
    """Robusten unteren Kontaktpunkt der Motivmaske in Canvas-Pixeln bestimmen."""
    width, height = mask.size
    binary = mask.point(
        [255 if value >= SILHOUETTE_ALPHA_THRESHOLD else 0 for value in range(256)]
    )
    try:
        bbox = binary.getbbox()
        if bbox is None and mask.getbbox() is not None:
            binary.close()
            binary = mask.point([0] + [255] * 255)
            bbox = binary.getbbox()
        if bbox is None:
            return None, None, None, None, 0.0

        def occupied_x(y: int) -> list[int]:
            row = binary.crop((0, y, width, y + 1))
            try:
                return [x for x, value in enumerate(row.tobytes()) if value]
            finally:
                row.close()

        selected_y = bbox[3] - 1
        selected_xs = occupied_x(selected_y)
        if len(selected_xs) == 1:
            lone_x = selected_xs[0]
            above_xs = occupied_x(selected_y - 1) if selected_y > 0 else []
            supported = any(abs(x - lone_x) <= 1 for x in above_xs)
            if not supported:
                # Ein isoliertes Streupixel unterhalb des eigentlichen Motivs darf
                # weder den Bodenkontakt noch dessen horizontale Mitte bestimmen.
                for candidate_y in range(selected_y - 1, bbox[1] - 1, -1):
                    candidate_xs = occupied_x(candidate_y)
                    if not candidate_xs:
                        continue
                    candidate_above = (
                        occupied_x(candidate_y - 1) if candidate_y > 0 else []
                    )
                    candidate_supported = len(candidate_xs) > 1 or any(
                        abs(x - candidate_xs[0]) <= 1 for x in candidate_above
                    )
                    if candidate_supported:
                        selected_y = candidate_y
                        selected_xs = candidate_xs
                        break

        above_xs = occupied_x(selected_y - 1) if selected_y > 0 else []
        contact_xs = [*selected_xs, *above_xs]
        anchor_x_mask = float(statistics.median(contact_xs))
        scale_y = original_size[1] / height
        anchor_x = clamp_unit((anchor_x_mask + 0.5) / width) * original_size[0] - 0.5
        anchor_y = min(
            original_size[1] - 1.0,
            max(0.0, (selected_y + 1) * scale_y - 1.0),
        )
        anchor_x = min(original_size[0] - 1.0, max(0.0, anchor_x))
        if len(selected_xs) >= 2 and above_xs:
            confidence = 1.0
        elif len(selected_xs) >= 2 or above_xs:
            confidence = 0.75
        else:
            confidence = 0.45
        return (
            anchor_x,
            anchor_y,
            original_size[1] - 1.0 - anchor_y,
            anchor_x,
            confidence,
        )
    finally:
        binary.close()


def alpha_layout_signature(alpha: Any) -> bytes:
    """Alpha innerhalb seiner sichtbaren Bounding-Box auf 32 x 32 normieren."""
    bbox = alpha.getbbox()
    if bbox is None:
        return bytes(ALPHA_LAYOUT_EDGE * ALPHA_LAYOUT_EDGE)
    cropped = alpha.crop(bbox)
    resized = None
    try:
        resized = cropped.resize(
            (ALPHA_LAYOUT_EDGE, ALPHA_LAYOUT_EDGE), Image.Resampling.LANCZOS
        )
        return resized.tobytes()
    finally:
        cropped.close()
        if resized is not None:
            resized.close()


def color_layout_signature(
    image: Any, subject_mask: Any
) -> tuple[tuple[float, float, float, float] | None, ...]:
    """Alpha-gewichtete mittlere Lab-Farbe in einer kleinen Motivkarte speichern."""
    sample = resized_for_analysis(image, COLOR_EDGE)
    mask_sample = None
    try:
        if subject_mask.size == sample.size:
            mask_sample = subject_mask.copy()
        else:
            mask_sample = subject_mask.resize(sample.size, Image.Resampling.NEAREST)
        bbox = mask_sample.getbbox()
        cell_count = COLOR_LAYOUT_EDGE * COLOR_LAYOUT_EDGE
        if bbox is None:
            return tuple(None for _ in range(cell_count))

        light_sums = [0.0] * cell_count
        green_red_sums = [0.0] * cell_count
        blue_yellow_sums = [0.0] * cell_count
        weights = [0.0] * cell_count
        pixels = list(flattened_pixels(sample))
        mask_values = list(flattened_pixels(mask_sample))
        left, top, right, bottom = bbox
        bbox_width = max(1, right - left)
        bbox_height = max(1, bottom - top)
        for y in range(top, bottom):
            cell_y = min(
                COLOR_LAYOUT_EDGE - 1, (y - top) * COLOR_LAYOUT_EDGE // bbox_height
            )
            for x in range(left, right):
                index = y * sample.width + x
                if mask_values[index] == 0:
                    continue
                red, green, blue, alpha_value = pixels[index]
                weight = alpha_value / 255.0
                if weight == 0.0:
                    continue
                cell_x = min(
                    COLOR_LAYOUT_EDGE - 1,
                    (x - left) * COLOR_LAYOUT_EDGE // bbox_width,
                )
                cell = cell_y * COLOR_LAYOUT_EDGE + cell_x
                lightness, green_red, blue_yellow = rgb_to_lab(red, green, blue)
                weights[cell] += weight
                light_sums[cell] += lightness * weight
                green_red_sums[cell] += green_red * weight
                blue_yellow_sums[cell] += blue_yellow * weight
        total_weight = sum(weights)
        if total_weight == 0.0:
            return tuple(None for _ in range(cell_count))
        return tuple(
            (
                light_sums[index] / weight,
                green_red_sums[index] / weight,
                blue_yellow_sums[index] / weight,
                weight / total_weight,
            )
            if weight > 0.0
            else None
            for index, weight in enumerate(weights)
        )
    finally:
        if mask_sample is not None:
            mask_sample.close()
        sample.close()


def color_signature(
    image: Any,
    subject_mask: Any | None = None,
) -> tuple[
    tuple[float, ...],
    tuple[float, float, float],
    tuple[tuple[float, float, float, float], ...],
    float,
    float,
    float,
]:
    """Gemeinsame Lab-Verteilung und dominante, alpha-gewichtete Palette."""
    sample = resized_for_analysis(image, COLOR_EDGE)
    mask_sample = None
    try:
        pixels = list(flattened_pixels(sample))
        mask_values: list[int] | None = None
        if subject_mask is not None:
            if subject_mask.size == sample.size:
                mask_sample = subject_mask.copy()
            else:
                mask_sample = subject_mask.resize(sample.size, Image.Resampling.NEAREST)
            mask_values = list(flattened_pixels(mask_sample))

        def collect(active_mask: Sequence[int] | None) -> tuple[Any, ...]:
            bin_count = LAB_HISTOGRAM_BINS**3
            weights = [0.0] * bin_count
            light_sums = [0.0] * bin_count
            green_red_sums = [0.0] * bin_count
            blue_yellow_sums = [0.0] * bin_count
            light_total = green_red_total = blue_yellow_total = chroma_total = 0.0
            total_weight = 0.0
            for index, (red, green, blue, alpha_value) in enumerate(pixels):
                weight = alpha_value / 255.0
                if active_mask is not None:
                    weight *= active_mask[index] / 255.0
                if weight == 0:
                    continue
                lightness, green_red, blue_yellow = rgb_to_lab(red, green, blue)
                histogram_index = lab_histogram_index(lightness, green_red, blue_yellow)
                weights[histogram_index] += weight
                light_sums[histogram_index] += lightness * weight
                green_red_sums[histogram_index] += green_red * weight
                blue_yellow_sums[histogram_index] += blue_yellow * weight
                light_total += lightness * weight
                green_red_total += green_red * weight
                blue_yellow_total += blue_yellow * weight
                chroma_total += math.hypot(green_red, blue_yellow) * weight
                total_weight += weight
            return (
                weights,
                light_sums,
                green_red_sums,
                blue_yellow_sums,
                light_total,
                green_red_total,
                blue_yellow_total,
                chroma_total,
                total_weight,
            )

        collected = collect(mask_values)
        if collected[-1] == 0 and mask_values is not None:
            # Ein völlig flaches opakes Bild besitzt keine Inhaltskante. Seine
            # Vollfarbe muss trotzdem vergleichbar bleiben.
            collected = collect(None)
        (
            weights,
            light_sums,
            green_red_sums,
            blue_yellow_sums,
            light_total,
            green_red_total,
            blue_yellow_total,
            chroma_total,
            total_weight,
        ) = collected
        if total_weight == 0:
            empty_histogram = tuple(0.0 for _ in range(LAB_HISTOGRAM_BINS**3))
            return empty_histogram, (0.0, 0.0, 0.0), (), 0.0, 0.0, 0.0

        normalized = tuple(weight / total_weight for weight in weights)
        dominant_indices = sorted(
            (index for index, weight in enumerate(weights) if weight > 0),
            key=lambda index: (-weights[index], index),
        )[:DOMINANT_PALETTE_SIZE]
        palette = tuple(
            (
                light_sums[index] / weights[index],
                green_red_sums[index] / weights[index],
                blue_yellow_sums[index] / weights[index],
                weights[index] / total_weight,
            )
            for index in dominant_indices
        )
        mean_lab = (
            light_total / total_weight,
            green_red_total / total_weight,
            blue_yellow_total / total_weight,
        )
        return (
            normalized,
            mean_lab,
            palette,
            mean_lab[0] / 100.0,
            min(1.0, chroma_total / total_weight / 140.0),
            total_weight,
        )
    finally:
        if mask_sample is not None:
            mask_sample.close()
        sample.close()


def binary_shape_stats(raw: bytes, edge: int) -> tuple[int, int]:
    """Kantenpixel und größere zusammenhängende Bereiche einer Binärmaske zählen."""
    occupied = {index for index, value in enumerate(raw) if value}
    edge_pixels = 0
    for index in occupied:
        x = index % edge
        y = index // edge
        neighbors = (
            index - 1 if x > 0 else -1,
            index + 1 if x + 1 < edge else -1,
            index - edge if y > 0 else -1,
            index + edge if y + 1 < edge else -1,
        )
        if any(neighbor not in occupied for neighbor in neighbors):
            edge_pixels += 1

    remaining = set(occupied)
    component_sizes: list[int] = []
    while remaining:
        start = remaining.pop()
        stack = [start]
        size = 0
        while stack:
            current = stack.pop()
            size += 1
            x = current % edge
            y = current // edge
            for neighbor in (
                current - 1 if x > 0 else -1,
                current + 1 if x + 1 < edge else -1,
                current - edge if y > 0 else -1,
                current + edge if y + 1 < edge else -1,
            ):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        component_sizes.append(size)
    # Einzelne Normalisierungs-/Antialiasing-Pixel gelten nicht als eigener
    # größerer Motivbereich.
    minimum_component = max(2, round(SHAPE_EDGE * SHAPE_EDGE * 0.001))
    components = sum(size >= minimum_component for size in component_sizes)
    return edge_pixels, components


def shape_signature(
    alpha: Any,
) -> tuple[bytes, bytes, int, float | None, int, int]:
    """Silhouette zentriert und maßstabsunabhängig auf 64 x 64 normalisieren."""
    threshold_table = [
        255 if value >= SILHOUETTE_ALPHA_THRESHOLD else 0 for value in range(256)
    ]
    binary = alpha.point(threshold_table)
    bbox = binary.getbbox()
    if bbox is None and alpha.getbbox() is not None:
        # Extrem schwache, aber sichtbare Bilder nicht als leer klassifizieren.
        binary.close()
        binary = alpha.point([0] + [255] * 255)
        bbox = binary.getbbox()
    if bbox is None:
        binary.close()
        empty = bytes(SHAPE_EDGE * SHAPE_EDGE)
        return empty, empty, 0, None, 0, 0

    cropped = binary.crop(bbox)
    inner = SHAPE_EDGE - 2 * SHAPE_PADDING
    scale = min(inner / cropped.width, inner / cropped.height)
    target = (
        max(1, round(cropped.width * scale)),
        max(1, round(cropped.height * scale)),
    )
    resized = cropped.resize(target, Image.Resampling.NEAREST)
    canvas = Image.new("L", (SHAPE_EDGE, SHAPE_EDGE), 0)
    offset = ((SHAPE_EDGE - target[0]) // 2, (SHAPE_EDGE - target[1]) // 2)
    canvas.paste(resized, offset)
    mirrored = ImageOps.mirror(canvas)
    try:
        raw = canvas.tobytes()
        mirror_raw = mirrored.tobytes()
        count = sum(1 for value in raw if value)
        aspect = cropped.width / cropped.height
        edge_pixels, components = binary_shape_stats(raw, SHAPE_EDGE)
        return raw, mirror_raw, count, aspect, edge_pixels, components
    finally:
        binary.close()
        cropped.close()
        resized.close()
        canvas.close()
        mirrored.close()


def analyze_image(path: Path) -> ImageFeatures:
    image = open_static_rgba(path)
    alpha = subject_mask = None
    try:
        raw_rgba = image.tobytes()
        rgba_sha256 = rgba_content_hash(image, raw_rgba)
        hidden_rgb_pixels = sum(
            1
            for index in range(0, len(raw_rgba), 4)
            if raw_rgba[index + 3] == 0
            and (raw_rgba[index] or raw_rgba[index + 1] or raw_rgba[index + 2])
        )
        alpha = image.getchannel("A")
        width, height = image.size
        total = width * height
        histogram = alpha.histogram()
        transparent = histogram[0]
        visible = total - transparent
        partial = sum(histogram[1:255])
        transparent_fraction = transparent / total
        mean_alpha = (
            sum(value * count for value, count in enumerate(histogram[1:], start=1))
            / (255.0 * visible)
            if visible
            else 0.0
        )
        subject_mask, mask_source = comparison_mask(image, alpha, transparent_fraction)
        subject_histogram = subject_mask.histogram()
        subject_pixels = sum(subject_histogram[1:])
        subject_fraction = subject_pixels / (subject_mask.width * subject_mask.height)
        comparison_pixels = round(subject_fraction * total)
        color_subject = subject_mask if mask_source == "content_edges" else None
        (
            color_hist,
            mean_lab,
            dominant_palette,
            luminance,
            saturation,
            color_weight,
        ) = color_signature(image, color_subject)
        color_layout = color_layout_signature(image, subject_mask)
        alpha_layout = alpha_layout_signature(alpha)
        (
            shape_mask,
            mirrored_mask,
            shape_pixels,
            shape_aspect,
            shape_edge_pixels,
            shape_components,
        ) = shape_signature(subject_mask)
        (
            anchor_x,
            anchor_y,
            bottom_margin,
            left_anchor_offset,
            anchor_confidence,
        ) = sprite_anchor(subject_mask, image.size)
        return ImageFeatures(
            path=path,
            logical_name=logical_name(path),
            rgba_sha256=rgba_sha256,
            width=width,
            height=height,
            total_pixels=total,
            visible_pixels=visible,
            transparent_pixels=transparent,
            partial_pixels=partial,
            visible_fraction=visible / total,
            transparent_fraction=transparent_fraction,
            comparison_pixels=comparison_pixels,
            comparison_fraction=subject_fraction,
            comparison_background_fraction=1.0 - subject_fraction,
            alpha_bbox=alpha.getbbox(),
            bbox=scaled_mask_bbox(subject_mask, image.size),
            centroid=alpha_centroid(subject_mask),
            mask_source=mask_source,
            mean_alpha=mean_alpha,
            soft_alpha_fraction=partial / visible if visible else 0.0,
            alpha_histogram=normalized_alpha_histogram(histogram, visible),
            alpha_layout=alpha_layout,
            color_histogram=color_hist,
            mean_lab=mean_lab,
            dominant_palette=dominant_palette,
            luminance=luminance,
            saturation=saturation,
            color_weight=color_weight,
            color_layout=color_layout,
            shape_mask=shape_mask,
            mirrored_shape_mask=mirrored_mask,
            shape_pixels=shape_pixels,
            shape_aspect=shape_aspect,
            shape_edge_pixels=shape_edge_pixels,
            shape_components=shape_components,
            anchor_x_px=anchor_x,
            anchor_y_px=anchor_y,
            bottom_margin_px=bottom_margin,
            left_anchor_offset_px=left_anchor_offset,
            anchor_confidence=anchor_confidence,
            hidden_rgb_pixels=hidden_rgb_pixels,
            direction=detect_direction(path.stem),
            action_group=detect_action_group(path.stem),
        )
    finally:
        for buffer in (subject_mask, alpha, image):
            if buffer is not None:
                buffer.close()


def clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def ratio_similarity(first: float, second: float) -> float:
    if first == 0 and second == 0:
        return 1.0
    if first <= 0 or second <= 0:
        return 0.0
    return min(first, second) / max(first, second)


def histogram_intersection(first: Sequence[float], second: Sequence[float]) -> float:
    return sum(min(left, right) for left, right in zip(first, second))


def size_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    return size_similarity_to_canvas(first, (second.width, second.height))


def size_similarity_to_canvas(item: ImageFeatures, canvas: tuple[int, int]) -> float:
    if item.width == canvas[0] and item.height == canvas[1]:
        return 100.0
    width = ratio_similarity(item.width, canvas[0])
    height = ratio_similarity(item.height, canvas[1])
    # Eine Verdopplung beider Canvas-Achsen ergibt damit nur noch 25 statt 50 %.
    return 100.0 * width * height


def coverage_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    absolute = 1.0 - abs(first.comparison_fraction - second.comparison_fraction)
    visible_ratio = ratio_similarity(
        first.comparison_fraction, second.comparison_fraction
    )
    # Verhältnis erkennt eine relativ verdoppelte Motivfläche; die absolute
    # Differenz verhindert zugleich eine harte Strafe bei 0 % gegenüber 1 %
    # Transparenz. Sichtbar und transparent sind komplementär, werden hier aber
    # bewusst beide ausgewiesen und gewichtet.
    visible = 0.65 * visible_ratio + 0.35 * absolute
    transparent = 1.0 - abs(
        first.comparison_background_fraction - second.comparison_background_fraction
    )
    return 100.0 * (0.75 * visible + 0.25 * transparent)


def position_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    if first.centroid is None and second.centroid is None:
        return 100.0
    if first.centroid is None or second.centroid is None:
        return 0.0

    centroid_distance = math.dist(first.centroid, second.centroid) / math.sqrt(2.0)
    assert first.bbox is not None and second.bbox is not None
    first_center = (
        (first.bbox[0] + first.bbox[2]) / (2.0 * first.width),
        (first.bbox[1] + first.bbox[3]) / (2.0 * first.height),
    )
    second_center = (
        (second.bbox[0] + second.bbox[2]) / (2.0 * second.width),
        (second.bbox[1] + second.bbox[3]) / (2.0 * second.height),
    )
    box_distance = math.dist(first_center, second_center) / math.sqrt(2.0)
    distance = 0.65 * centroid_distance + 0.35 * box_distance
    return 100.0 * math.exp(-3.5 * distance)


def comparison_orientation(first: ImageFeatures, second: ImageFeatures) -> str:
    """Formbeziehung ohne pauschale Spiegelgleichsetzung bestimmen."""
    if first.direction is None or second.direction is None:
        return "unknown"
    if first.direction == second.direction:
        return "normal"
    if MIRROR_DIRECTIONS.get(first.direction) == second.direction:
        return "mirror"
    return "neutral"


def directions_are_compatible(first: ImageFeatures, second: ImageFeatures) -> bool:
    orientation = comparison_orientation(first, second)
    return orientation in {"normal", "mirror"} or (
        first.direction is None and second.direction is None
    )


def mirrored_grid_index(index: int, edge: int) -> int:
    row, column = divmod(index, edge)
    return row * edge + (edge - 1 - column)


def alpha_layout_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    orientation = comparison_orientation(first, second)
    mirror = orientation == "mirror"
    total_difference = 0
    for index, left in enumerate(first.alpha_layout):
        target = mirrored_grid_index(index, ALPHA_LAYOUT_EDGE) if mirror else index
        total_difference += abs(left - second.alpha_layout[target])
    maximum = 255 * len(first.alpha_layout)
    return 100.0 * clamp_unit(1.0 - total_difference / maximum)


def alpha_distribution_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    if first.visible_pixels == 0 and second.visible_pixels == 0:
        return 100.0
    if first.visible_pixels == 0 or second.visible_pixels == 0:
        return 0.0
    histogram = histogram_intersection(first.alpha_histogram, second.alpha_histogram)
    opacity = 1.0 - abs(first.mean_alpha - second.mean_alpha)
    softness = 1.0 - abs(first.soft_alpha_fraction - second.soft_alpha_fraction)
    return 100.0 * (
        0.65 * clamp_unit(histogram)
        + 0.20 * clamp_unit(opacity)
        + 0.15 * clamp_unit(softness)
    )


def alpha_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    distribution = alpha_distribution_similarity(first, second)
    spatial = alpha_layout_similarity(first, second)
    return 0.65 * distribution + 0.35 * spatial


def delta_e_76(first: Sequence[float], second: Sequence[float]) -> float:
    return math.dist(first[:3], second[:3])


def palette_similarity(
    first: Sequence[tuple[float, float, float, float]],
    second: Sequence[tuple[float, float, float, float]],
) -> float:
    if not first and not second:
        return 1.0
    if not first or not second:
        return 0.0

    def directed(
        source: Sequence[tuple[float, float, float, float]],
        target: Sequence[tuple[float, float, float, float]],
    ) -> float:
        source_weight = sum(entry[3] for entry in source)
        if source_weight == 0:
            return 0.0
        similarity = 0.0
        for entry in source:
            nearest = min(delta_e_76(entry, candidate) for candidate in target)
            similarity += entry[3] * clamp_unit(1.0 - nearest / 60.0)
        return similarity / source_weight

    return (directed(first, second) + directed(second, first)) / 2.0


def color_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    if first.color_weight == 0 and second.color_weight == 0:
        return 100.0
    if first.color_weight == 0 or second.color_weight == 0:
        return 0.0
    histogram = histogram_intersection(first.color_histogram, second.color_histogram)
    palette = palette_similarity(first.dominant_palette, second.dominant_palette)
    mean_color = 1.0 - delta_e_76(first.mean_lab, second.mean_lab) / 100.0
    luminance = 1.0 - abs(first.luminance - second.luminance)
    return 100.0 * (
        0.15 * clamp_unit(histogram)
        + 0.60 * clamp_unit(palette)
        + 0.20 * clamp_unit(mean_color)
        + 0.05 * clamp_unit(luminance)
    )


def color_layout_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    orientation = comparison_orientation(first, second)
    mirror = orientation == "mirror"
    matched = 0.0
    union = 0.0
    for index, left in enumerate(first.color_layout):
        target = mirrored_grid_index(index, COLOR_LAYOUT_EDGE) if mirror else index
        right = second.color_layout[target]
        left_weight = left[3] if left is not None else 0.0
        right_weight = right[3] if right is not None else 0.0
        union += max(left_weight, right_weight)
        if left is not None and right is not None:
            color_match = clamp_unit(1.0 - delta_e_76(left, right) / 60.0)
            matched += min(left_weight, right_weight) * color_match
    if union == 0.0:
        return 100.0
    return 100.0 * clamp_unit(matched / union)


def anchor_score_for_difference(difference: float) -> float:
    points = ((0.0, 100.0), (1.0, 92.0), (2.0, 78.0), (3.0, 58.0), (5.0, 25.0))
    if difference <= 0.0:
        return 100.0
    for (left_x, left_score), (right_x, right_score) in pairwise(points):
        if difference <= right_x:
            fraction = (difference - left_x) / (right_x - left_x)
            return left_score + fraction * (right_score - left_score)
    return max(0.0, 25.0 - (difference - 5.0) * 8.0)


def subject_height(feature: ImageFeatures) -> float:
    if feature.bbox is not None:
        return float(max(1, feature.bbox[3] - feature.bbox[1]))
    return float(max(1, feature.height))


def anchor_pair_deltas(
    first: ImageFeatures, second: ImageFeatures
) -> dict[str, float | str]:
    assert first.anchor_x_px is not None and first.anchor_y_px is not None
    assert first.bottom_margin_px is not None
    assert second.anchor_x_px is not None and second.anchor_y_px is not None
    assert second.bottom_margin_px is not None
    orientation = comparison_orientation(first, second)
    second_x = second.anchor_x_px
    if orientation == "mirror":
        second_x = second.width - 1.0 - second_x
    normalization = ANCHOR_REFERENCE_HEIGHT / statistics.mean(
        (subject_height(first), subject_height(second))
    )
    horizontal_px = abs(first.anchor_x_px - second_x)
    vertical_px = abs(first.anchor_y_px - second.anchor_y_px)
    bottom_margin_px = abs(first.bottom_margin_px - second.bottom_margin_px)
    horizontal_normalized = horizontal_px * normalization
    vertical_normalized = bottom_margin_px * normalization
    return {
        "orientation": orientation,
        "delta_x_px": horizontal_px,
        "delta_y_px": vertical_px,
        "bottom_margin_delta_px": bottom_margin_px,
        "delta_x_normalized": horizontal_normalized,
        "delta_y_normalized": vertical_normalized,
        "distance_normalized": math.hypot(horizontal_normalized, vertical_normalized),
    }


def anchor_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    if first.anchor_x_px is None and second.anchor_x_px is None:
        return 100.0
    if first.anchor_x_px is None or second.anchor_x_px is None:
        return 0.0
    deltas = anchor_pair_deltas(first, second)
    vertical = anchor_score_for_difference(float(deltas["delta_y_normalized"]))
    if not directions_are_compatible(first, second):
        return vertical
    horizontal = anchor_score_for_difference(float(deltas["delta_x_normalized"]))
    return ANCHOR_VERTICAL_SHARE * vertical + ANCHOR_HORIZONTAL_SHARE * horizontal


def dice_coefficient(
    first: bytes, second: bytes, first_count: int, second_count: int
) -> float:
    if first_count == 0 and second_count == 0:
        return 1.0
    if first_count == 0 or second_count == 0:
        return 0.0
    intersection = sum(1 for left, right in zip(first, second) if left and right)
    return 2.0 * intersection / (first_count + second_count)


def neutral_shape_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    area = ratio_similarity(first.shape_pixels, second.shape_pixels)
    aspect = ratio_similarity(first.shape_aspect or 0.0, second.shape_aspect or 0.0)
    perimeter = ratio_similarity(first.shape_edge_pixels, second.shape_edge_pixels)
    components = ratio_similarity(first.shape_components, second.shape_components)
    return 100.0 * (0.35 * area + 0.30 * aspect + 0.20 * perimeter + 0.15 * components)


def shape_similarity(first: ImageFeatures, second: ImageFeatures) -> float:
    if first.shape_pixels == 0 and second.shape_pixels == 0:
        return 100.0
    if first.shape_pixels == 0 or second.shape_pixels == 0:
        return 0.0
    normal = dice_coefficient(
        first.shape_mask,
        second.shape_mask,
        first.shape_pixels,
        second.shape_pixels,
    )
    neutral = neutral_shape_similarity(first, second)
    orientation = comparison_orientation(first, second)
    if orientation == "neutral":
        return neutral
    if orientation == "mirror":
        directional = dice_coefficient(
            first.shape_mask,
            second.mirrored_shape_mask,
            first.shape_pixels,
            second.shape_pixels,
        )
        return 0.80 * (100.0 * directional) + 0.20 * neutral
    if orientation == "normal":
        return 0.80 * (100.0 * normal) + 0.20 * neutral
    # Bei unbekannter Richtung konservativ normal vergleichen und zusätzlich
    # richtungsneutrale Formmerkmale berücksichtigen.
    return 0.65 * (100.0 * normal) + 0.35 * neutral


def compare_pair(first: ImageFeatures, second: ImageFeatures) -> dict[str, float]:
    return {
        "size": size_similarity(first, second),
        "coverage": coverage_similarity(first, second),
        "position": position_similarity(first, second),
        "anchor": anchor_similarity(first, second),
        "alpha": alpha_similarity(first, second),
        "alpha_layout": alpha_layout_similarity(first, second),
        "color": color_similarity(first, second),
        "color_layout": color_layout_similarity(first, second),
        "shape": shape_similarity(first, second),
    }


def status_for(score: float) -> str:
    if score >= 90.0:
        return "very_good"
    if score >= 75.0:
        return "good"
    if score >= 50.0:
        return "warning"
    return "critical"


def most_common_size(features: Sequence[ImageFeatures]) -> tuple[int, int]:
    counts = Counter((item.width, item.height) for item in features)
    return min(counts, key=lambda size: (-counts[size], size[0] * size[1], size))


def median_optional(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return statistics.median(present) if present else None


def annotate_duplicates(features: Sequence[ImageFeatures]) -> list[ImageFeatures]:
    annotated = list(features)
    logical_groups: dict[str, list[int]] = {}
    for index, feature in enumerate(features):
        logical_groups.setdefault(feature.logical_name, []).append(index)
    for base_name, indices in logical_groups.items():
        if len(indices) < 2:
            continue
        for index in indices:
            exact_name = unicodedata.normalize("NFC", features[index].path.name)
            suffix = hashlib.sha256(exact_name.encode("utf-8")).hexdigest()[:12]
            annotated[index] = replace(
                annotated[index], logical_name=f"{base_name}#{suffix}"
            )

    clusters: dict[str, list[int]] = {}
    for index, feature in enumerate(annotated):
        clusters.setdefault(feature.rgba_sha256, []).append(index)
    for indices in clusters.values():
        original = annotated[indices[0]].path.name
        for position, index in enumerate(indices):
            annotated[index] = replace(
                annotated[index],
                duplicate_of=None if position == 0 else original,
                duplicate_cluster_size=len(indices),
            )
    return annotated


def unique_representative_indices(features: Sequence[ImageFeatures]) -> list[int]:
    seen: set[str] = set()
    result: list[int] = []
    for index, feature in enumerate(features):
        if feature.rgba_sha256 not in seen:
            seen.add(feature.rgba_sha256)
            result.append(index)
    return result


def confidence_for(features: Sequence[ImageFeatures]) -> str:
    effective_count = len({feature.rgba_sha256 for feature in features})
    if effective_count >= 5:
        return "high"
    if effective_count >= 3:
        return "medium"
    return "low"


def is_empty_feature(feature: ImageFeatures) -> bool:
    return (
        feature.comparison_pixels == 0
        or feature.bbox is None
        or feature.shape_pixels == 0
    )


def classify_features(features: Sequence[ImageFeatures]) -> dict[int, str]:
    representatives = unique_representative_indices(features)
    result: dict[int, str] = {}
    for index, feature in enumerate(features):
        if is_empty_feature(feature):
            result[index] = "empty"
            continue
        peers = [
            features[candidate]
            for candidate in representatives
            if features[candidate].action_group == feature.action_group
            and not is_empty_feature(features[candidate])
        ]
        if len(peers) < 2:
            peers = [
                features[candidate]
                for candidate in representatives
                if not is_empty_feature(features[candidate])
            ]
        median_pixels = (
            statistics.median(candidate.comparison_pixels for candidate in peers)
            if peers
            else feature.comparison_pixels
        )
        result[index] = (
            "nearly_empty"
            if median_pixels > 0
            and feature.comparison_pixels < median_pixels * NEARLY_EMPTY_MEDIAN_RATIO
            else "valid"
        )
    return result


def robust_mean(values: Sequence[float]) -> float:
    if not values:
        return 100.0
    ordered = sorted(values)
    if len(ordered) >= 5:
        ordered = ordered[1:-1]
    return statistics.mean(ordered)


def unique_peer_indices(
    features: Sequence[ImageFeatures], item_index: int, peers: Sequence[int]
) -> list[int]:
    own_hash = features[item_index].rgba_sha256
    different = [index for index in peers if features[index].rgba_sha256 != own_hash]
    candidates = different if different else list(peers)
    seen: set[str] = set()
    result: list[int] = []
    for index in candidates:
        digest = features[index].rgba_sha256
        if digest not in seen:
            seen.add(digest)
            result.append(index)
    return result


def directional_geometry_peers(
    features: Sequence[ImageFeatures], item_index: int, all_peers: Sequence[int]
) -> list[int]:
    """Nur tatsächlich richtungskompatible Partner liefern, nie fachfremd auffüllen."""
    item = features[item_index]
    action_peers = [
        index
        for index in all_peers
        if features[index].action_group == item.action_group
    ]
    candidates = action_peers if action_peers else list(all_peers)
    if item.direction is None:
        return [index for index in candidates if features[index].direction is None]
    same_direction = [
        index for index in candidates if features[index].direction == item.direction
    ]
    if same_direction:
        return same_direction
    mirror_direction = MIRROR_DIRECTIONS.get(item.direction)
    mirror_peers = [
        index for index in candidates if features[index].direction == mirror_direction
    ]
    return mirror_peers


def action_group_peers(
    features: Sequence[ImageFeatures], item_index: int, all_peers: Sequence[int]
) -> list[int]:
    item = features[item_index]
    matching = [
        index
        for index in all_peers
        if features[index].action_group == item.action_group
    ]
    # Unbekannte oder einzeln vorkommende Aktionsbezeichnungen sollen den
    # Gruppenvergleich nicht vollständig entwerten.
    return matching if matching else list(all_peers)


def renormalized_weighted_score(
    scores: Mapping[str, float | None],
) -> tuple[float, dict[str, float]]:
    available = {
        metric: weight
        for metric, weight in SCORE_WEIGHTS.items()
        if scores.get(metric) is not None
    }
    weight_sum = sum(available.values())
    if weight_sum <= 0.0:
        return 0.0, {}
    effective = {metric: weight / weight_sum for metric, weight in available.items()}
    total = sum(float(scores[metric]) * weight for metric, weight in effective.items())
    return max(0.0, min(100.0, total)), effective


def aggregate_anchor_score(
    features: Sequence[ImageFeatures],
    item_index: int,
    action_peers: Sequence[int],
    directional_peers: Sequence[int],
) -> tuple[float, dict[str, Any]]:
    item = features[item_index]
    if (
        item.anchor_x_px is None
        or item.anchor_y_px is None
        or item.bottom_margin_px is None
    ):
        return 0.0, {
            "available": False,
            "reason": "Kein belastbarer Bodenanker erkannt.",
            "reference_height_px": ANCHOR_REFERENCE_HEIGHT,
        }

    vertical_features = [
        feature
        for feature in [item, *(features[index] for index in action_peers)]
        if feature.bottom_margin_px is not None
    ]
    canonical_margins = [
        float(feature.bottom_margin_px)
        * ANCHOR_REFERENCE_HEIGHT
        / subject_height(feature)
        for feature in vertical_features
    ]
    raw_margins = [float(feature.bottom_margin_px) for feature in vertical_features]
    item_margin = item.bottom_margin_px * ANCHOR_REFERENCE_HEIGHT / subject_height(item)
    median_margin = statistics.median(canonical_margins)
    vertical_delta = item_margin - median_margin
    vertical_score = anchor_score_for_difference(abs(vertical_delta))

    horizontal_comparisons: list[tuple[float, int, Mapping[str, float | str]]] = []
    for peer_index in directional_peers:
        peer = features[peer_index]
        if peer.anchor_x_px is None or peer.anchor_y_px is None:
            continue
        deltas = anchor_pair_deltas(item, peer)
        horizontal_score = anchor_score_for_difference(
            float(deltas["delta_x_normalized"])
        )
        horizontal_comparisons.append((horizontal_score, peer_index, deltas))

    horizontal_score: float | None = None
    paired: dict[str, Any] | None = None
    if horizontal_comparisons:
        horizontal_score = robust_mean([entry[0] for entry in horizontal_comparisons])
        worst_score, worst_index, worst_deltas = min(
            horizontal_comparisons,
            key=lambda entry: (
                entry[0],
                features[entry[1]].path.name.casefold(),
                features[entry[1]].path.name,
            ),
        )
        paired = {
            "file": features[worst_index].path.name,
            "orientation": worst_deltas["orientation"],
            "delta_x_px": worst_deltas["delta_x_px"],
            "delta_y_px": worst_deltas["delta_y_px"],
            "bottom_margin_delta_px": worst_deltas["bottom_margin_delta_px"],
            "delta_x_normalized": worst_deltas["delta_x_normalized"],
            "delta_y_normalized": worst_deltas["delta_y_normalized"],
            "distance_normalized": worst_deltas["distance_normalized"],
            "horizontal_score": worst_score,
        }

    total = (
        vertical_score
        if horizontal_score is None
        else ANCHOR_VERTICAL_SHARE * vertical_score
        + ANCHOR_HORIZONTAL_SHARE * horizontal_score
    )
    return total, {
        "available": True,
        "reference_height_px": ANCHOR_REFERENCE_HEIGHT,
        "vertical_share": (1.0 if horizontal_score is None else ANCHOR_VERTICAL_SHARE),
        "horizontal_share": (
            0.0 if horizontal_score is None else ANCHOR_HORIZONTAL_SHARE
        ),
        "vertical_peer_count": max(0, len(vertical_features) - 1),
        "horizontal_peer_count": len(horizontal_comparisons),
        "group_median_bottom_margin_px": statistics.median(raw_margins),
        "group_median_bottom_margin_normalized": median_margin,
        "vertical_delta_px": item.bottom_margin_px - statistics.median(raw_margins),
        "vertical_delta_normalized": vertical_delta,
        "vertical_score": vertical_score,
        "horizontal_score": horizontal_score,
        "paired_comparison": paired,
    }


def score_findings(scores: Mapping[str, float | None]) -> tuple[ScoreFinding, ...]:
    findings: list[ScoreFinding] = []

    def add(metric: str, severity: str, threshold: float) -> None:
        value = scores.get(metric)
        if value is None:
            return
        label = METRIC_LABELS[metric]
        findings.append(
            ScoreFinding(
                metric=metric,
                severity=severity,
                value=value,
                threshold=threshold,
                message=(
                    f"{label} {value:.2f} % liegt unter {threshold:.0f} %; "
                    "der numerische Gesamtscore bleibt ungekürzt."
                ),
            )
        )

    size = scores.get("size")
    if size is not None and size < SIZE_WARNING_THRESHOLD:
        add("size", "warning", SIZE_WARNING_THRESHOLD)
    color = scores.get("color")
    if color is not None and color < COLOR_CRITICAL_THRESHOLD:
        add("color", "critical", COLOR_CRITICAL_THRESHOLD)
    elif color is not None and color < COLOR_WARNING_THRESHOLD:
        add("color", "warning", COLOR_WARNING_THRESHOLD)
    anchor = scores.get("anchor")
    if anchor is not None and anchor < ANCHOR_CRITICAL_THRESHOLD:
        add("anchor", "critical", ANCHOR_CRITICAL_THRESHOLD)
    elif anchor is not None and anchor < ANCHOR_WARNING_THRESHOLD:
        add("anchor", "warning", ANCHOR_WARNING_THRESHOLD)
    color_layout = scores.get("color_layout")
    if color_layout is not None and color_layout < COLOR_LAYOUT_WARNING_THRESHOLD:
        add("color_layout", "warning", COLOR_LAYOUT_WARNING_THRESHOLD)

    severity_rank = {"critical": 0, "warning": 1}
    metric_rank = {metric: index for index, metric in enumerate(SCORE_WEIGHTS)}
    return tuple(
        sorted(
            findings,
            key=lambda finding: (
                severity_rank[finding.severity],
                metric_rank[finding.metric],
            ),
        )
    )


def status_with_findings(score: float, findings: Sequence[ScoreFinding]) -> str:
    status = status_for(score)
    for finding in findings:
        finding_status = "critical" if finding.severity == "critical" else "warning"
        if STATUS_RANK[finding_status] > STATUS_RANK[status]:
            status = finding_status
    return status


def pair_total_score(
    first: ImageFeatures,
    second: ImageFeatures,
    scores: Mapping[str, float] | None = None,
) -> float:
    if is_empty_feature(first) or is_empty_feature(second):
        return 0.0
    pair_values = dict(scores if scores is not None else compare_pair(first, second))
    values: dict[str, float | None] = {
        metric: pair_values[metric] for metric in SCORE_WEIGHTS
    }
    if not directions_are_compatible(first, second):
        values["color_layout"] = None
    return renormalized_weighted_score(values)[0]


def make_hints(
    item: ImageFeatures,
    scores: Mapping[str, float | None],
    all_features: Sequence[ImageFeatures],
    geometry_features: Sequence[ImageFeatures],
    classification: str,
    anchor_diagnostics: Mapping[str, Any],
) -> tuple[str, ...]:
    hints: list[str] = []

    def below(metric: str, threshold: float) -> bool:
        value = scores.get(metric)
        return value is not None and value < threshold

    if classification == "empty":
        hints.append("Kein sichtbares Motiv erkannt.")
    elif classification == "nearly_empty":
        hints.append(
            "Extrem wenige Motivpixel im Verhältnis zum Median der passenden Gruppe."
        )
    if item.duplicate_of is not None:
        hints.append(f"Pixelinhalt ist identisch mit {item.duplicate_of}.")
    if item.hidden_rgb_pixels:
        hints.append(
            f"{item.hidden_rgb_pixels} vollständig transparente Pixel enthalten RGB-Daten; "
            "dies kann bei Texturfilterung Farbsäume erzeugen."
        )
    if classification == "empty":
        return tuple(hints)

    nonempty_all = [
        feature for feature in all_features if not is_empty_feature(feature)
    ]
    nonempty_geometry = [
        feature for feature in geometry_features if not is_empty_feature(feature)
    ]
    if not nonempty_all:
        nonempty_all = list(all_features)
    if not nonempty_geometry:
        nonempty_geometry = list(geometry_features)
    typical_size = most_common_size(nonempty_all)
    if below("size", 99.5) and (item.width, item.height) != typical_size:
        hints.append(
            f"Canvas {item.width} x {item.height} px; häufigste Gruppengröße "
            f"{typical_size[0]} x {typical_size[1]} px."
        )

    median_visible = statistics.median(
        feature.comparison_fraction for feature in nonempty_geometry
    )
    if (
        below("coverage", 85.0)
        and abs(item.comparison_fraction - median_visible) >= 0.01
    ):
        relation = "größer" if item.comparison_fraction > median_visible else "kleiner"
        hints.append(
            f"Erkannte Vergleichsfläche {item.comparison_fraction * 100:.2f} %; "
            f"damit {relation} als der Typ-Median von {median_visible * 100:.2f} %."
        )

    if item.centroid is not None and below("position", 90.0):
        median_x = median_optional(
            feature.centroid[0] if feature.centroid else None
            for feature in nonempty_geometry
        )
        median_y = median_optional(
            feature.centroid[1] if feature.centroid else None
            for feature in nonempty_geometry
        )
        assert median_x is not None and median_y is not None
        directions: list[str] = []
        if item.centroid[0] - median_x > 0.025:
            directions.append("rechts")
        elif median_x - item.centroid[0] > 0.025:
            directions.append("links")
        if item.centroid[1] - median_y > 0.025:
            directions.append("unten")
        elif median_y - item.centroid[1] > 0.025:
            directions.append("oben")
        if directions:
            hints.append(
                f"Erkanntes Motiv gegenüber dem Typ-Median nach {' und '.join(directions)} verschoben."
            )
        else:
            hints.append(
                "Motivposition weicht in der Paaranalyse von der restlichen Gruppe ab."
            )

    if item.anchor_y_px is not None and below("anchor", 99.5):
        vertical = anchor_diagnostics.get("vertical_delta_px")
        normalized = anchor_diagnostics.get("vertical_delta_normalized")
        if isinstance(vertical, (int, float)) and isinstance(normalized, (int, float)):
            relation = "mehr" if vertical > 0 else "weniger"
            hints.append(
                f"Bodenabstand liegt {abs(vertical):.2f} px ({abs(normalized):.2f} "
                f"bei 128 px Referenzhöhe) {relation} als der Gruppenmedian."
            )
        paired = anchor_diagnostics.get("paired_comparison")
        if isinstance(paired, Mapping):
            hints.append(
                "Richtungsanker gegen "
                f"{paired['file']}: Δx={paired['delta_x_px']:.2f} px, "
                f"Δy={paired['delta_y_px']:.2f} px, normierter Abstand "
                f"{paired['distance_normalized']:.2f}."
            )

    if below("alpha", 85.0):
        median_soft = statistics.median(
            feature.soft_alpha_fraction for feature in nonempty_all
        )
        difference = item.soft_alpha_fraction - median_soft
        if abs(difference) >= 0.01:
            relation = "mehr" if difference > 0 else "weniger"
            hints.append(
                f"Alpha enthält {relation} teiltransparente Kantenpixel als der Gruppenmedian."
            )
        else:
            hints.append(
                "Deckkraftverteilung und Alpha-Übergänge weichen von der Gruppe ab."
            )
    if below("alpha_layout", 80.0):
        hints.append("Teiltransparente Bereiche liegen an anderen Motivpositionen.")

    if below("color", 85.0):
        median_luminance = statistics.median(
            feature.luminance for feature in nonempty_all
        )
        median_saturation = statistics.median(
            feature.saturation for feature in nonempty_all
        )
        color_notes: list[str] = []
        if item.luminance - median_luminance > 0.06:
            color_notes.append("heller")
        elif median_luminance - item.luminance > 0.06:
            color_notes.append("dunkler")
        if item.saturation - median_saturation > 0.08:
            color_notes.append("stärker gesättigt")
        elif median_saturation - item.saturation > 0.08:
            color_notes.append("schwächer gesättigt")
        if color_notes:
            hints.append(
                f"Farbwirkung gegenüber dem Gruppenmedian: {', '.join(color_notes)}."
            )
        else:
            hints.append("Lab-Farbverteilung weicht von der restlichen Gruppe ab.")

    if scores.get("color_layout") is None:
        hints.append(
            "Räumliche Farbe nicht bewertet: kein Frame derselben oder horizontal "
            "gespiegelten Richtung vorhanden; Gewicht wurde neu verteilt."
        )
    elif below("color_layout", 80.0):
        hints.append("Dominante Farben befinden sich in anderen Motivbereichen.")

    if below("shape", 80.0):
        same_direction = [
            feature
            for feature in nonempty_geometry
            if feature.path != item.path
            and item.direction is not None
            and feature.direction == item.direction
        ]
        likely_mirrored = False
        for feature in same_direction:
            normal = dice_coefficient(
                item.shape_mask,
                feature.shape_mask,
                item.shape_pixels,
                feature.shape_pixels,
            )
            mirrored = dice_coefficient(
                item.shape_mask,
                feature.mirrored_shape_mask,
                item.shape_pixels,
                feature.shape_pixels,
            )
            if mirrored - normal >= 0.15:
                likely_mirrored = True
                break
        hints.append(
            "Silhouette wurde für dieselbe Blickrichtung wahrscheinlich gespiegelt."
            if likely_mirrored
            else "Normalisierte Form weicht von Bildern desselben Typs ab."
        )
    if item.mask_source == "content_edges":
        hints.append(
            "Nahezu opakes Bild: Form und Position wurden aus Bildinhalt/Kanten abgeleitet."
        )
    return tuple(hints)


def score_group(features: Sequence[ImageFeatures]) -> list[ScoredImage]:
    if len(features) < 2:
        raise ValueError(
            "Für den Gruppenvergleich sind mindestens zwei Bilder erforderlich."
        )
    features = annotate_duplicates(features)
    representative_indices = unique_representative_indices(features)
    nonempty_representatives = [
        index
        for index in representative_indices
        if not is_empty_feature(features[index])
    ]
    canvas_features = [
        features[index]
        for index in (nonempty_representatives or representative_indices)
    ]
    typical_canvas = most_common_size(canvas_features)
    classifications = classify_features(features)
    confidence = confidence_for(features)
    pair_cache: dict[tuple[int, int], Mapping[str, float]] = {}

    def pair_for(first_index: int, second_index: int) -> Mapping[str, float]:
        key = tuple(sorted((first_index, second_index)))
        if key not in pair_cache:
            pair_cache[key] = compare_pair(features[key[0]], features[key[1]])
        return pair_cache[key]

    results: list[ScoredImage] = []
    all_indices = list(range(len(features)))
    for item_index, item in enumerate(features):
        all_other_peers = [index for index in all_indices if index != item_index]
        nonempty_other_peers = [
            index for index in all_other_peers if not is_empty_feature(features[index])
        ]
        raw_global_peers = (
            nonempty_other_peers
            if not is_empty_feature(item) and nonempty_other_peers
            else all_other_peers
        )
        global_peers = unique_peer_indices(features, item_index, raw_global_peers)
        raw_action_peers = action_group_peers(features, item_index, global_peers)
        action_peers = unique_peer_indices(features, item_index, raw_action_peers)
        if not action_peers:
            action_peers = global_peers
        raw_directional_peers = directional_geometry_peers(
            features, item_index, action_peers
        )
        directional_peers = unique_peer_indices(
            features, item_index, raw_directional_peers
        )

        scores: dict[str, float | None] = {}
        metric_peer_counts: dict[str, int] = {}
        for metric in (*SCORE_WEIGHTS, "alpha_layout"):
            if metric == "size":
                scores[metric] = size_similarity_to_canvas(item, typical_canvas)
                metric_peer_counts[metric] = len(canvas_features)
                continue
            if metric == "anchor":
                continue
            if metric in GLOBAL_METRICS or metric == "alpha_layout":
                peers = global_peers
            elif metric in DIRECTIONAL_METRICS:
                peers = directional_peers
            else:
                peers = action_peers
            metric_peer_counts[metric] = len(peers)
            scores[metric] = (
                robust_mean([pair_for(item_index, peer)[metric] for peer in peers])
                if peers
                else None
            )

        anchor_score, anchor_diagnostics = aggregate_anchor_score(
            features,
            item_index,
            action_peers,
            directional_peers,
        )
        scores["anchor"] = anchor_score
        metric_peer_counts["anchor"] = int(
            anchor_diagnostics.get("vertical_peer_count", 0)
        )

        classification = classifications[item_index]
        if classification == "empty":
            scores = {metric: 0.0 for metric in scores}
            weighted_score = total_score = 0.0
            effective_weights = dict(SCORE_WEIGHTS)
            findings: tuple[ScoreFinding, ...] = ()
        else:
            weighted_score, effective_weights = renormalized_weighted_score(scores)
            total_score = weighted_score
            findings = score_findings(scores)

        score_status = status_for(total_score)
        result_status = status_with_findings(total_score, findings)

        pair_totals = [
            (
                features[peer].path.name,
                pair_total_score(item, features[peer], pair_for(item_index, peer)),
            )
            for peer in global_peers
        ]
        if pair_totals:
            worst_file, worst_score = min(
                pair_totals, key=lambda entry: (entry[1], entry[0].casefold(), entry[0])
            )
            total_values = [entry[1] for entry in pair_totals]
            group_median = statistics.median(total_values)
            group_stddev = statistics.pstdev(total_values)
        else:
            worst_file = None
            worst_score = group_median = 100.0
            group_stddev = 0.0
        geometry_features = [item, *(features[index] for index in action_peers)]
        results.append(
            ScoredImage(
                features=item,
                scores=scores,
                effective_weights=effective_weights,
                metric_peer_counts=metric_peer_counts,
                weighted_score=weighted_score,
                total_score=total_score,
                status=result_status,
                score_status=score_status,
                classification=classification,
                confidence=confidence,
                comparison_count=len(global_peers),
                group_median_score=group_median,
                group_score_stddev=group_stddev,
                worst_comparison_file=worst_file,
                worst_comparison_score=worst_score,
                findings=findings,
                anchor_diagnostics=anchor_diagnostics,
                hints=make_hints(
                    item,
                    scores,
                    features,
                    geometry_features,
                    classification,
                    anchor_diagnostics,
                ),
            )
        )
    return results


def group_average_score(scored: Sequence[ScoredImage]) -> float:
    """Jeden RGBA-Duplikatcluster im Gesamtmittel genau einmal gewichten."""
    representatives: dict[str, float] = {}
    for item in scored:
        representatives.setdefault(item.features.rgba_sha256, item.total_score)
    return statistics.mean(representatives.values())


def group_status(scored: Sequence[ScoredImage]) -> str:
    status = status_for(group_average_score(scored))
    for item in scored:
        if STATUS_RANK[item.status] > STATUS_RANK[status]:
            status = item.status
    return status


def detect_mixed_group(
    features: Sequence[ImageFeatures],
) -> tuple[bool, tuple[tuple[str, ...], ...]]:
    """Klar getrennte, intern konsistente Kompatibilitätscluster melden."""
    representatives = [
        index
        for index in unique_representative_indices(features)
        if not is_empty_feature(features[index])
    ]
    if len(representatives) < 4:
        return False, ()

    pair_scores: dict[tuple[int, int], float] = {}
    for left_position, left in enumerate(representatives):
        for right in representatives[left_position + 1 :]:
            pair_scores[(left, right)] = pair_total_score(
                features[left], features[right]
            )

    parent = {index: index for index in representatives}

    def root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        first_root = root(first)
        second_root = root(second)
        if first_root != second_root:
            parent[max(first_root, second_root)] = min(first_root, second_root)

    for (left, right), score in pair_scores.items():
        if score >= MIXED_CLUSTER_JOIN_THRESHOLD:
            union(left, right)
    groups: dict[int, list[int]] = {}
    for index in representatives:
        groups.setdefault(root(index), []).append(index)
    ordered_groups = sorted(
        groups.values(), key=lambda group: (-len(group), tuple(group))
    )
    substantial = [group for group in ordered_groups if len(group) >= 2]
    if len(substantial) < 2:
        return False, ()
    first_group, second_group = substantial[:2]
    if len(first_group) + len(second_group) < math.ceil(0.8 * len(representatives)):
        return False, ()

    def score_between(left: int, right: int) -> float:
        return pair_scores[tuple(sorted((left, right)))]

    within = [
        score_between(group[left], group[right])
        for group in (first_group, second_group)
        for left in range(len(group))
        for right in range(left + 1, len(group))
    ]
    across = [
        score_between(left, right) for left in first_group for right in second_group
    ]
    within_mean = statistics.mean(within)
    across_mean = statistics.mean(across)
    mixed = (
        within_mean >= MIXED_CLUSTER_JOIN_THRESHOLD
        and across_mean <= MIXED_ACROSS_MAXIMUM
        and within_mean - across_mean >= MIXED_MINIMUM_GAP
    )
    if not mixed:
        return False, ()
    cluster_names = tuple(
        tuple(features[index].path.name for index in group)
        for group in (first_group, second_group)
    )
    return True, cluster_names


def choose_layout(features: Sequence[ImageFeatures]) -> SheetLayout:
    directions = [
        feature.direction for feature in features if feature.direction is not None
    ]
    unique_directions = len(directions) == len(set(directions))
    enough_directions = len(directions) >= 3 and len(directions) * 2 >= len(features)
    if unique_directions and enough_directions:
        positions: dict[Path, tuple[int, int]] = {
            feature.path: DIRECTION_POSITIONS[feature.direction]
            for feature in features
            if feature.direction is not None
        }
        unplaced = [feature for feature in features if feature.direction is None]
        for index, feature in enumerate(unplaced):
            positions[feature.path] = (3 + index // 3, index % 3)
        return SheetLayout(
            kind="directions",
            columns=3,
            rows=3 + math.ceil(len(unplaced) / 3),
            positions=positions,
        )

    columns = math.ceil(math.sqrt(len(features)))
    rows = math.ceil(len(features) / columns)
    positions = {
        feature.path: (index // columns, index % columns)
        for index, feature in enumerate(features)
    }
    return SheetLayout(kind="compact", columns=columns, rows=rows, positions=positions)


def ensure_output_folder(folder: Path) -> Path:
    output = folder / OUTPUT_FOLDER
    if output.is_symlink():
        raise RuntimeError("Der Ausgabeordner .compare ist ein symbolischer Link.")
    if os.path.lexists(output) and not output.is_dir():
        raise RuntimeError("Der Ausgabepfad .compare ist kein Verzeichnis.")
    output.mkdir(exist_ok=True)
    return output


def allocate_report_paths(output: Path) -> ReportPaths:
    created = datetime.now(timezone.utc)
    base_id = created.strftime("%Y%m%dT%H%M%S_%fZ")
    created_text = created.isoformat(timespec="microseconds").replace("+00:00", "Z")
    for counter in range(1000):
        run_id = base_id if counter == 0 else f"{base_id}_{counter:02d}"
        paths = ReportPaths(
            run_id=run_id,
            created_at_utc=created_text,
            spritesheet=output / f"spritesheet_{run_id}.png",
            markdown=output / f"report_{run_id}.md",
            json=output / f"report_{run_id}.json",
        )
        if not any(
            os.path.lexists(path)
            for path in (paths.spritesheet, paths.markdown, paths.json)
        ):
            return paths
    raise RuntimeError("Keine freie UTC-ID für den neuen Report gefunden.")


def check_new_output_target(path: Path) -> None:
    if os.path.lexists(path):
        raise RuntimeError(
            f"Ausgabedatei existiert bereits und wird nicht ersetzt: {path.name}"
        )


def temporary_path(destination: Path, suffix: str) -> tuple[int, Path]:
    fd, name = tempfile.mkstemp(
        prefix=".pyimgcompare_", suffix=suffix, dir=destination.parent
    )
    return fd, Path(name)


def install_new_file(temporary: Path, destination: Path) -> None:
    """Eine fertige Datei veröffentlichen, aber niemals ein Ziel ersetzen."""
    check_new_output_target(destination)
    try:
        # Quelle und Ziel liegen absichtlich im selben Verzeichnis. Der Hardlink
        # erscheint atomar und schlägt fehl, falls das Ziel inzwischen existiert.
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise RuntimeError(
            f"Ausgabedatei existiert bereits und wird nicht ersetzt: {destination.name}"
        ) from exc
    except OSError as exc:
        unsupported_link_errors = {
            errno.EPERM,
            errno.EXDEV,
            errno.EOPNOTSUPP,
            getattr(errno, "ENOTSUP", errno.EOPNOTSUPP),
        }
        if exc.errno not in unsupported_link_errors:
            raise

        # FAT/exFAT sowie einige FUSE-/USB-Mounts unterstützen keine Hardlinks.
        # O_EXCL reserviert das neue Ziel ohne Überschreibungsrisiko. Erst nach
        # vollständig erfolgreichem Schreiben bleibt die Datei bestehen.
        try:
            destination_fd = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as target_exc:
            raise RuntimeError(
                "Ausgabedatei existiert bereits und wird nicht ersetzt: "
                f"{destination.name}"
            ) from target_exc

        completed = False
        try:
            with (
                temporary.open("rb") as source,
                os.fdopen(destination_fd, "wb") as target,
            ):
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            completed = True
        finally:
            if not completed:
                try:
                    destination.unlink()
                except OSError:
                    pass


def atomic_write_text(destination: Path, content: str) -> None:
    check_new_output_target(destination)
    fd, temporary = temporary_path(destination, ".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        install_new_file(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def create_spritesheet(
    features: Sequence[ImageFeatures],
    layout: SheetLayout,
    destination: Path,
) -> tuple[int, int]:
    cell_width = max(feature.width for feature in features)
    cell_height = max(feature.height for feature in features)
    sheet_width = cell_width * layout.columns
    sheet_height = cell_height * layout.rows
    if sheet_width * sheet_height > MAX_SHEET_PIXELS:
        raise RuntimeError(
            "Das Spritesheet würde die Sicherheitsgrenze von 64 Millionen Pixeln "
            f"überschreiten ({sheet_width} x {sheet_height} px)."
        )
    check_new_output_target(destination)
    sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
    try:
        for feature in features:
            image = open_static_rgba(feature.path)
            try:
                row, column = layout.positions[feature.path]
                x = column * cell_width + (cell_width - image.width) // 2
                y = row * cell_height + (cell_height - image.height) // 2
                sheet.alpha_composite(image, (x, y))
            finally:
                image.close()
        fd, temporary = temporary_path(destination, ".png")
        try:
            with os.fdopen(fd, "wb") as stream:
                sheet.save(stream, format="PNG", compress_level=6)
                stream.flush()
                os.fsync(stream.fileno())
            install_new_file(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    finally:
        sheet.close()
    return cell_width, cell_height


def report_created_timestamp(data: Mapping[str, Any], fallback: float) -> float:
    run = data.get("run")
    if not isinstance(run, Mapping):
        return fallback
    value = run.get("created_at_utc")
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def report_items_by_logical_name(
    items: Any,
) -> dict[str, Mapping[str, Any]] | None:
    if not isinstance(items, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            return None
        logical = item.get("logical_name")
        if not isinstance(logical, str) or logical in result:
            return None
        result[logical] = item
    return result


def logical_names_fingerprint(names: Iterable[str]) -> str:
    encoded = json.dumps(
        tuple(sorted(names)), ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def parse_previous_report(path: Path, folder: Path) -> PreviousReport | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        stat = path.stat()
        if stat.st_size > MAX_REPORT_HISTORY_BYTES:
            return None
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, Mapping) or data.get("tool") != "PyImgCompare":
        return None
    if data.get("folder") != folder.name:
        return None
    summary = data.get("summary")
    if not isinstance(summary, Mapping):
        return None
    score = summary.get("average_score")
    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(float(score))
        or not 0.0 <= float(score) <= 100.0
    ):
        return None

    schema = data.get("schema_version")
    model_fingerprint: str | None = None
    logical_names: tuple[str, ...] | None = None
    previous_items: Mapping[str, Mapping[str, Any]] = {}
    if schema == SCHEMA_VERSION:
        model = data.get("scoring_model")
        manifest = data.get("input_manifest")
        run = data.get("run")
        if (
            not isinstance(model, Mapping)
            or not isinstance(manifest, Mapping)
            or not isinstance(run, Mapping)
            or not isinstance(run.get("id"), str)
            or not isinstance(run.get("created_at_utc"), str)
        ):
            return None
        fingerprint = model.get("fingerprint")
        model_weights = model.get("weights")
        files = manifest.get("files")
        file_set_fingerprint = manifest.get("logical_file_set_fingerprint")
        if (
            not isinstance(fingerprint, str)
            or not isinstance(model_weights, Mapping)
            or not model_weights
            or not isinstance(file_set_fingerprint, str)
            or not isinstance(files, list)
        ):
            return None
        for metric, weight in model_weights.items():
            if (
                not isinstance(metric, str)
                or isinstance(weight, bool)
                or not isinstance(weight, (int, float))
                or not math.isfinite(float(weight))
                or float(weight) < 0.0
            ):
                return None
        names: list[str] = []
        for item in files:
            if not isinstance(item, Mapping) or not isinstance(
                item.get("logical_name"), str
            ):
                return None
            names.append(item["logical_name"])
        mapped_items = report_items_by_logical_name(data.get("items"))
        if (
            mapped_items is None
            or len(mapped_items) != len(files)
            or set(mapped_items) != set(names)
            or logical_names_fingerprint(names) != file_set_fingerprint
        ):
            return None
        for item in mapped_items.values():
            total = item.get("total_score")
            scores = item.get("scores")
            hints = item.get("hints")
            if (
                isinstance(total, bool)
                or not isinstance(total, (int, float))
                or not 0.0 <= float(total) <= 100.0
                or not isinstance(scores, Mapping)
                or not isinstance(hints, list)
                or not isinstance(item.get("status"), str)
            ):
                return None
            for metric in model_weights:
                value = scores.get(metric)
                if value is None:
                    continue
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or not 0.0 <= float(value) <= 100.0
                ):
                    return None
        model_fingerprint = fingerprint
        logical_names = tuple(sorted(names))
        previous_items = mapped_items
    elif not isinstance(schema, int) or schema < 1:
        return None

    return PreviousReport(
        path=path,
        average_score=float(score),
        scoring_model_fingerprint=model_fingerprint,
        logical_names=logical_names,
        items=previous_items,
    )


def find_previous_report(output: Path, folder: Path) -> PreviousReportSearch:
    candidates: list[tuple[float, int, str, PreviousReport]] = []
    invalid_seen = False
    try:
        entries = list(output.iterdir())
    except OSError:
        return PreviousReportSearch(None, False)
    for path in entries:
        if not (
            path.name == JSON_REPORT_NAME
            or (path.name.startswith("report_") and path.suffix.lower() == ".json")
        ):
            continue
        try:
            stat = path.stat()
        except OSError:
            invalid_seen = True
            continue
        previous = parse_previous_report(path, folder)
        if previous is None:
            invalid_seen = True
            continue
        try:
            with path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, UnicodeError, json.JSONDecodeError):
            invalid_seen = True
            continue
        candidates.append(
            (
                report_created_timestamp(data, stat.st_mtime),
                stat.st_mtime_ns,
                path.name,
                previous,
            )
        )
    if not candidates:
        return PreviousReportSearch(None, invalid_seen)
    return PreviousReportSearch(
        max(candidates, key=lambda candidate: candidate[:3])[3], invalid_seen
    )


def input_file_set(features: Sequence[ImageFeatures]) -> tuple[str, ...]:
    return tuple(sorted(feature.logical_name for feature in features))


def logical_file_set_fingerprint(features: Sequence[ImageFeatures]) -> str:
    return logical_names_fingerprint(input_file_set(features))


def score_mapping_from_item(item: Mapping[str, Any]) -> Mapping[str, Any]:
    scores = item.get("scores")
    return scores if isinstance(scores, Mapping) else {}


def make_history_result(
    search: PreviousReportSearch,
    features: Sequence[ImageFeatures],
    scored: Sequence[ScoredImage],
) -> HistoryResult:
    previous = search.report
    current_score = rounded(group_average_score(scored))
    if previous is None:
        if search.invalid_reports_seen:
            return HistoryResult(
                status="invalid_previous_report",
                reason="Kein vollständiger und gültiger vorheriger Report verwendbar.",
                current_average_score=current_score,
            )
        return HistoryResult(
            status="first_run",
            reason="Kein vorheriger Report vorhanden.",
            current_average_score=current_score,
        )
    previous_path = f"{OUTPUT_FOLDER}/{previous.path.name}"
    if previous.scoring_model_fingerprint != SCORING_MODEL_FINGERPRINT:
        return HistoryResult(
            status="model_changed",
            reason="Kein direkter Fortschrittsvergleich: Bewertungsmodell wurde geändert.",
            previous_report=previous_path,
            previous_average_score=rounded(previous.average_score),
            current_average_score=current_score,
        )
    if previous.logical_names != input_file_set(features):
        current_names = set(input_file_set(features))
        previous_names = set(previous.logical_names or ())
        added = len(current_names - previous_names)
        removed = len(previous_names - current_names)
        details: list[str] = []
        if added:
            details.append(f"{added} hinzugefügt")
        if removed:
            details.append(f"{removed} entfernt oder umbenannt")
        detail_text = f" ({', '.join(details)})" if details else ""
        return HistoryResult(
            status="file_set_changed",
            reason=(
                "Kein direkter Fortschrittsvergleich: Bildbestand wurde verändert"
                f"{detail_text}."
            ),
            previous_report=previous_path,
            previous_average_score=rounded(previous.average_score),
            current_average_score=current_score,
        )

    previous_score = rounded(previous.average_score)
    delta = rounded(current_score - previous_score)
    if delta > 0.0:
        direction = "improved"
    elif delta < 0.0:
        direction = "declined"
    else:
        direction = "unchanged"
    item_changes: dict[str, Mapping[str, Any]] = {}
    for result in scored:
        logical = result.features.logical_name
        old = previous.items.get(logical)
        if old is None:
            continue
        old_total = old.get("total_score")
        old_status = old.get("status")
        old_scores = score_mapping_from_item(old)
        score_changes: dict[str, float] = {}
        for metric, value in result.scores.items():
            old_value = old_scores.get(metric)
            if (
                value is not None
                and isinstance(old_value, (int, float))
                and not isinstance(old_value, bool)
            ):
                score_changes[metric] = rounded(value - float(old_value))
        old_hints = (
            {hint for hint in old.get("hints", []) if isinstance(hint, str)}
            if isinstance(old.get("hints"), list)
            else set()
        )
        new_hints = set(result.hints)
        item_changes[result.features.path.name] = {
            "total_score": (
                rounded(result.total_score - float(old_total))
                if isinstance(old_total, (int, float))
                and not isinstance(old_total, bool)
                else None
            ),
            "scores": score_changes,
            "previous_status": old_status if isinstance(old_status, str) else None,
            "current_status": result.status,
            "added_hints": sorted(new_hints - old_hints),
            "removed_hints": sorted(old_hints - new_hints),
        }
    return HistoryResult(
        status="comparable",
        reason="Direkter Fortschrittsvergleich ist zulässig.",
        previous_report=f"{OUTPUT_FOLDER}/{previous.path.name}",
        previous_average_score=previous_score,
        current_average_score=current_score,
        delta_percentage_points=delta,
        direction=direction,
        item_changes=item_changes,
    )


def rounded(value: float) -> float:
    return round(value + 1e-12, 2)


def clean_text(text: str) -> str:
    return "".join(
        char if char.isprintable() else f"\\u{ord(char):04x}" for char in text
    )


def markdown_escape(text: str) -> str:
    cleaned = clean_text(text)
    for character in "\\`*_{}[]<>#|":
        cleaned = cleaned.replace(character, f"\\{character}")
    return cleaned


def box_data(bbox: tuple[int, int, int, int] | None) -> dict[str, int] | None:
    if bbox is None:
        return None
    left, top, right, bottom = bbox
    return {
        "x": left,
        "y": top,
        "width": right - left,
        "height": bottom - top,
    }


def centroid_data(feature: ImageFeatures) -> dict[str, float] | None:
    if feature.centroid is None:
        return None
    return {
        "x": rounded(feature.centroid[0] * feature.width),
        "y": rounded(feature.centroid[1] * feature.height),
        "normalized_x": rounded(feature.centroid[0]),
        "normalized_y": rounded(feature.centroid[1]),
    }


def anchor_data(feature: ImageFeatures) -> dict[str, float] | None:
    if feature.anchor_x_px is None or feature.anchor_y_px is None:
        return None
    assert feature.bottom_margin_px is not None
    assert feature.left_anchor_offset_px is not None
    return {
        "anchor_x_px": rounded(feature.anchor_x_px),
        "anchor_y_px": rounded(feature.anchor_y_px),
        "bottom_margin_px": rounded(feature.bottom_margin_px),
        "left_anchor_offset_px": rounded(feature.left_anchor_offset_px),
        "confidence": rounded(feature.anchor_confidence),
    }


def rounded_report_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: rounded_report_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded_report_data(item) for item in value]
    if isinstance(value, float):
        return rounded(value)
    return value


def build_input_manifest(features: Sequence[ImageFeatures]) -> dict[str, Any]:
    return {
        "logical_file_set_fingerprint": logical_file_set_fingerprint(features),
        "files": [
            {
                "file": feature.path.name,
                "logical_name": feature.logical_name,
                "rgba_sha256": feature.rgba_sha256,
                "width": feature.width,
                "height": feature.height,
                "direction": feature.direction,
                "action_group": feature.action_group,
                "duplicate_of": feature.duplicate_of,
            }
            for feature in features
        ],
    }


def history_data(history: HistoryResult) -> dict[str, Any]:
    return {
        "status": history.status,
        "reason": history.reason,
        "previous_report": history.previous_report,
        "previous_average_score": history.previous_average_score,
        "current_average_score": history.current_average_score,
        "delta_percentage_points": history.delta_percentage_points,
        "direction": history.direction,
    }


def build_json_report(
    folder: Path,
    discovered_count: int,
    scored: Sequence[ScoredImage],
    skipped: Sequence[SkippedFile],
    layout: SheetLayout,
    cell_size: tuple[int, int],
    paths: ReportPaths,
    history: HistoryResult,
    mixed_group: bool,
    mixed_clusters: Sequence[Sequence[str]],
) -> dict[str, Any]:
    counts = Counter(item.status for item in scored)
    average = group_average_score(scored)
    features = [item.features for item in scored]
    empty_count = sum(item.classification == "empty" for item in scored)
    nearly_empty_count = sum(item.classification == "nearly_empty" for item in scored)
    duplicate_count = sum(item.features.duplicate_of is not None for item in scored)
    items = []
    for result in scored:
        feature = result.features
        row, column = layout.positions[feature.path]
        scores = {
            name: rounded(value) if value is not None else None
            for name, value in result.scores.items()
        }
        change = (
            history.item_changes.get(feature.path.name)
            if history.item_changes is not None
            else None
        )
        items.append(
            {
                "file": feature.path.name,
                "logical_name": feature.logical_name,
                "total_score": rounded(result.total_score),
                "weighted_score": rounded(result.weighted_score),
                "scores": scores,
                "effective_weights": {
                    metric: round(weight, 6)
                    for metric, weight in result.effective_weights.items()
                },
                "unavailable_metrics": [
                    metric
                    for metric in SCORE_WEIGHTS
                    if result.scores.get(metric) is None
                ],
                "metric_peer_counts": dict(result.metric_peer_counts),
                "status": result.status,
                "score_status": result.score_status,
                "state": (
                    "duplicate"
                    if feature.duplicate_of is not None
                    else result.classification
                ),
                "classification": result.classification,
                "findings": [
                    {
                        "metric": finding.metric,
                        "severity": finding.severity,
                        "value": rounded(finding.value),
                        "threshold": rounded(finding.threshold),
                        "message": finding.message,
                    }
                    for finding in result.findings
                ],
                "comparison_group": feature.action_group,
                "comparison_confidence": result.confidence,
                "comparison_statistics": {
                    "effective_peers": result.comparison_count,
                    "median_score": rounded(result.group_median_score),
                    "standard_deviation": rounded(result.group_score_stddev),
                    "worst_comparison": (
                        {
                            "file": result.worst_comparison_file,
                            "score": rounded(result.worst_comparison_score),
                        }
                        if result.worst_comparison_file is not None
                        else None
                    ),
                },
                "duplicate_of": feature.duplicate_of,
                "duplicate_cluster_size": feature.duplicate_cluster_size,
                "canvas": {"width": feature.width, "height": feature.height},
                "pixels": {
                    "total": feature.total_pixels,
                    "visible": feature.visible_pixels,
                    "transparent": feature.transparent_pixels,
                    "partially_transparent": feature.partial_pixels,
                    "comparison_mask": feature.comparison_pixels,
                    "hidden_rgb_while_transparent": feature.hidden_rgb_pixels,
                    "visible_percent": rounded(feature.visible_fraction * 100.0),
                    "transparent_percent": rounded(
                        feature.transparent_fraction * 100.0
                    ),
                },
                "visible_bounding_box": box_data(feature.alpha_bbox),
                "comparison_mask": {
                    "source": feature.mask_source,
                    "occupied_percent": rounded(feature.comparison_fraction * 100.0),
                    "bounding_box": box_data(feature.bbox),
                    "centroid": centroid_data(feature),
                },
                "sprite_anchor": anchor_data(feature),
                "anchor_comparison": rounded_report_data(result.anchor_diagnostics),
                "alpha_analysis": {
                    "mean_opacity": rounded(feature.mean_alpha),
                    "soft_pixel_percent": rounded(feature.soft_alpha_fraction * 100.0),
                    "spatial_score": scores["alpha_layout"],
                    "map_size": [ALPHA_LAYOUT_EDGE, ALPHA_LAYOUT_EDGE],
                },
                "color_analysis": {
                    "space": "CIELAB_D65",
                    "mean": {
                        "l": rounded(feature.mean_lab[0]),
                        "a": rounded(feature.mean_lab[1]),
                        "b": rounded(feature.mean_lab[2]),
                    },
                    "dominant_palette": [
                        {
                            "l": rounded(entry[0]),
                            "a": rounded(entry[1]),
                            "b": rounded(entry[2]),
                            "weight_percent": rounded(entry[3] * 100.0),
                        }
                        for entry in feature.dominant_palette
                    ],
                    "spatial_score": scores["color_layout"],
                    "map_size": [COLOR_LAYOUT_EDGE, COLOR_LAYOUT_EDGE],
                },
                "shape_analysis": {
                    "normalized_pixels": feature.shape_pixels,
                    "edge_pixels": feature.shape_edge_pixels,
                    "connected_components": feature.shape_components,
                    "aspect_ratio": (
                        rounded(feature.shape_aspect)
                        if feature.shape_aspect is not None
                        else None
                    ),
                },
                "direction": feature.direction,
                "sheet_position": {"row": row + 1, "column": column + 1},
                "hints": list(result.hints),
                "change_from_previous": change,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "PyImgCompare",
        "tool_version": VERSION,
        "scoring_model": {
            "id": SCORING_MODEL_ID,
            "version": SCORING_MODEL_VERSION,
            "fingerprint": SCORING_MODEL_FINGERPRINT,
            "weights": SCORE_WEIGHTS,
            "aggregation": SCORING_MODEL_DESCRIPTION["aggregation"],
            "thresholds": SCORING_MODEL_DESCRIPTION["thresholds"],
            "metric_versions": SCORING_MODEL_DESCRIPTION["metric_versions"],
            "layout": SCORING_MODEL_DESCRIPTION["layout"],
            "metric_scopes": SCORING_MODEL_DESCRIPTION["metric_scopes"],
            "anchor_curve": SCORING_MODEL_DESCRIPTION["anchor_curve"],
            "anchor_distance": SCORING_MODEL_DESCRIPTION["anchor_distance"],
            "mask_rule": SCORING_MODEL_DESCRIPTION["mask_rule"],
            "direction_rule": SCORING_MODEL_DESCRIPTION["direction_rule"],
        },
        "run": {
            "id": paths.run_id,
            "created_at_utc": paths.created_at_utc,
            "files": {
                "spritesheet": f"{OUTPUT_FOLDER}/{paths.spritesheet.name}",
                "markdown": f"{OUTPUT_FOLDER}/{paths.markdown.name}",
                "json": f"{OUTPUT_FOLDER}/{paths.json.name}",
            },
        },
        "folder": folder.name,
        "discovered_image_count": discovered_count,
        "image_count": len(scored),
        "input_manifest": build_input_manifest(features),
        "summary": {
            "average_score": rounded(average),
            "average_score_status": status_for(average),
            "overall_status": group_status(scored),
            "confidence": confidence_for(features),
            "effective_distinct_images": len(
                {feature.rgba_sha256 for feature in features}
            ),
            "empty_images": empty_count,
            "nearly_empty_images": nearly_empty_count,
            "duplicate_images": duplicate_count,
            "mixed_group": mixed_group,
            "very_good": counts["very_good"],
            "good": counts["good"],
            "warning": counts["warning"],
            "critical": counts["critical"],
            "skipped": len(skipped),
            "comparison_groups": dict(
                sorted(Counter(item.features.action_group for item in scored).items())
            ),
        },
        "comparison": {
            "mode": "group",
            "meaning": (
                "Gruppenkompatibilität/Konsistenz; keine künstlerische Qualitätsnote "
                "und ohne Referenz keine Aussage über fachliche Richtigkeit."
            ),
            "reference_rule": (
                "duplicate_normalized; global_style_metrics; action_group_geometry; "
                "directional_layout_only_with_same_or_horizontal_mirror_peer; "
                "robust_trimmed_mean_from_five_peers"
            ),
            "weights": SCORE_WEIGHTS,
            "aggregation": SCORING_MODEL_DESCRIPTION["aggregation"],
            "metric_scopes": {
                "canvas_consensus": ["size"],
                "global_pairwise": sorted(GLOBAL_METRICS),
                "action_group": sorted(ACTION_METRICS),
                "directional_pairwise": sorted(DIRECTIONAL_METRICS),
                "anchor": {
                    "vertical": "action_group_consensus",
                    "horizontal": "same_direction_or_horizontal_mirror",
                },
            },
            "hard_caps": {},
            "finding_policy": (
                "Teilwert-Schwellen ändern Warn-/Kritisch-Status, aber nicht den "
                "numerischen Gesamtscore."
            ),
            "color_method": "joint_CIELAB_histogram_and_dominant_palette_delta_E_76",
            "color_layout_method": "normalized_12x12_subject_CIELAB_map",
            "alpha_layout_method": "normalized_32x32_alpha_map",
            "anchor_method": (
                "robust_bottom_two_rows; canonical_128px_subject_height; "
                "vertical_group_consensus_80_percent; directional_horizontal_20_percent"
            ),
            "shape_direction_method": "same_direction_or_horizontal_mirror_pair_else_neutral",
            "opaque_shape_method": "border_color_foreground_and_content_edges",
            "status_thresholds": {
                "very_good": {"minimum": 90.0, "maximum": 100.0},
                "good": {"minimum": 75.0, "maximum_exclusive": 90.0},
                "warning": {"minimum": 50.0, "maximum_exclusive": 75.0},
                "critical": {"minimum": 0.0, "maximum_exclusive": 50.0},
            },
        },
        "history": history_data(history),
        "groups": {
            "actions": dict(
                sorted(Counter(feature.action_group for feature in features).items())
            ),
            "directions": dict(
                sorted(
                    Counter(
                        feature.direction or "unknown" for feature in features
                    ).items()
                )
            ),
            "mixed_clusters": [list(cluster) for cluster in mixed_clusters],
        },
        "spritesheet": {
            "path": f"{OUTPUT_FOLDER}/{paths.spritesheet.name}",
            "layout": layout.kind,
            "columns": layout.columns,
            "rows": layout.rows,
            "cell_width": cell_size[0],
            "cell_height": cell_size[1],
            "width": cell_size[0] * layout.columns,
            "height": cell_size[1] * layout.rows,
        },
        "items": items,
        "skipped_files": [
            {"file": item.path.name, "state": "unreadable", "reason": item.reason}
            for item in skipped
        ],
    }


def build_markdown_report(data: Mapping[str, Any]) -> str:
    summary = data["summary"]
    run = data["run"]
    history = data["history"]
    manifest = data["input_manifest"]
    sheet = data["spritesheet"]
    model = data["scoring_model"]
    groups = data["groups"]

    def score_text(value: float | None) -> str:
        return "nicht bewertet" if value is None else f"{value:.2f} %"

    lines = [
        "# PyImgCompare Report",
        "",
        "## Lauf",
        "",
        f"- ID: {run['id']}",
        f"- Erstellt (UTC): {run['created_at_utc']}",
        f"- Werkzeugversion: {data['tool_version']}",
        f"- JSON: {run['files']['json']}",
        f"- Markdown: {run['files']['markdown']}",
        "",
        "## Ordner",
        "",
        markdown_escape(str(data["folder"])),
        "",
        "## Zusammenfassung",
        "",
        f"- Durchschnittliche Gruppenkompatibilität: {summary['average_score']:.2f} %",
        f"- Gesamtstatus einschließlich Auffälligkeiten: {STATUS_DATA[summary['overall_status']][0]}",
        f"- Rein numerischer Gesamtstatus: {STATUS_DATA[summary['average_score_status']][0]}",
        f"- Bewertungsvertrauen: {summary['confidence']}",
        f"- Bilder erkannt / verglichen: {data['discovered_image_count']} / {data['image_count']}",
        f"- Effektiv unterschiedliche Bilder: {summary['effective_distinct_images']}",
        f"- Leer / nahezu leer: {summary['empty_images']} / {summary['nearly_empty_images']}",
        f"- Exakte Duplikate: {summary['duplicate_images']}",
        f"- Sehr gut / gut / Warnung / kritisch: {summary['very_good']} / {summary['good']} / {summary['warning']} / {summary['critical']}",
        f"- Übersprungen: {summary['skipped']}",
        "",
        "> Dieser Wert misst die Konsistenz innerhalb der Bildgruppe. Er ist keine",
        "> künstlerische Qualitätsnote und ohne Referenz keine Aussage darüber,",
        "> welcher Stil fachlich richtig ist.",
        "",
        "## Vergleichbarkeit / Verlauf",
        "",
        f"- Zustand: `{history['status']}`",
        f"- {markdown_escape(history['reason'])}",
    ]
    if history["previous_report"] is not None:
        lines.append(f"- Vorheriger Report: {history['previous_report']}")
    if history["status"] == "comparable":
        delta = history["delta_percentage_points"]
        delta_text = f"{delta:+.2f}" if delta else "±0.00"
        lines.extend(
            [
                f"- Vorher: {history['previous_average_score']:.2f} %",
                f"- Aktuell: {history['current_average_score']:.2f} %",
                f"- Änderung: {delta_text} Prozentpunkte",
            ]
        )
    lines.extend(
        [
            "",
            "## Eingabemanifest",
            "",
            f"- Logischer Dateisatz: `{manifest['logical_file_set_fingerprint']}`",
            "",
            "| Datei | Logischer Name | Canvas | Richtung | Gruppe | RGBA-SHA-256 | Duplikat von |",
            "| --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for item in manifest["files"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(item["file"]),
                    markdown_escape(item["logical_name"]),
                    f"{item['width']} × {item['height']}",
                    item["direction"] or "–",
                    markdown_escape(item["action_group"]),
                    f"`{item['rgba_sha256']}`",
                    markdown_escape(item["duplicate_of"])
                    if item["duplicate_of"]
                    else "–",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Gruppen und erkannte Richtungen",
            "",
            "- Aktionsgruppen: "
            + ", ".join(
                f"{name} ({count})" for name, count in groups["actions"].items()
            ),
            "- Richtungen: "
            + ", ".join(
                f"{name} ({count})" for name, count in groups["directions"].items()
            ),
            "",
            "## Raster / Spritesheet",
            "",
            f"- Datei: {sheet['path']}",
            f"- Layout: {'Richtungsraster' if sheet['layout'] == 'directions' else 'kompaktes Raster'}",
            f"- Raster: {sheet['columns']} Spalten × {sheet['rows']} Zeilen",
            f"- Zellengröße: {sheet['cell_width']} × {sheet['cell_height']} px",
            f"- Gesamtgröße: {sheet['width']} × {sheet['height']} px",
            "",
            "## Bewertungsmodell",
            "",
            f"- ID: `{model['id']}`",
            f"- Modellversion: {model['version']}",
            f"- Fingerprint: `{model['fingerprint']}`",
            "- Aggregation: gewichtetes Mittel aller verfügbaren Teilwerte",
            "- Fehlt ein zulässiger Richtungsvergleich, wird dessen Gewicht",
            "  proportional auf die übrigen verfügbaren Teilwerte verteilt.",
            "- Auffälligkeitsschwellen ändern den Status, deckeln aber nicht den Prozentwert.",
            "- Duplikatcluster haben zusammen Gruppengewicht 1; ab fünf effektiven",
            "  Vergleichspartnern wird ein getrimmtes Mittel verwendet.",
            "",
            "| Teilwert | Gewicht |",
            "| --- | ---: |",
        ]
    )
    for metric, weight in model["weights"].items():
        lines.append(f"| {METRIC_LABELS[metric]} | {weight * 100:.0f} % |")
    lines.extend(["", "## Gruppenauffälligkeiten", ""])
    if summary["mixed_group"]:
        lines.append(
            "- `mixed_group`: zwei klar getrennte, intern konsistente Teilgruppen erkannt."
        )
        for index, cluster in enumerate(groups["mixed_clusters"], start=1):
            lines.append(
                f"  - Cluster {index}: "
                + ", ".join(markdown_escape(name) for name in cluster)
            )
    else:
        lines.append("- Keine klar getrennten Stilcluster erkannt.")
    if summary["empty_images"]:
        lines.append(f"- Leere Bilder: {summary['empty_images']}")
    if summary["nearly_empty_images"]:
        lines.append(f"- Nahezu leere Bilder: {summary['nearly_empty_images']}")

    lines.extend(["", "## Duplikate", ""])
    duplicates = [item for item in data["items"] if item["duplicate_of"] is not None]
    if duplicates:
        for item in duplicates:
            lines.append(
                f"- {markdown_escape(item['file'])} → {markdown_escape(item['duplicate_of'])}"
            )
    else:
        lines.append("- Keine exakten RGBA-Duplikate erkannt.")

    lines.extend(["", "## Einzelanalyse", ""])
    classification_labels = {
        "valid": "gültig",
        "empty": "leer",
        "nearly_empty": "nahezu leer",
    }
    for item in data["items"]:
        scores = item["scores"]
        statistics_data = item["comparison_statistics"]
        worst = statistics_data["worst_comparison"]
        anchor = item["sprite_anchor"]
        lines.extend(
            [
                f"### {markdown_escape(item['file'])}",
                "",
                f"- Gesamt: {item['total_score']:.2f} % ({STATUS_DATA[item['status']][0]})",
                f"- Rein numerischer Status: {STATUS_DATA[item['score_status']][0]}",
                f"- Vorprüfstatus: {item['state']}",
                f"- Inhaltsklassifikation: {classification_labels[item['classification']]}",
                f"- Gewichtetes Mittel: {item['weighted_score']:.2f} %",
            ]
        )
        for metric in SCORE_WEIGHTS:
            value = scores[metric]
            effective_weight = item["effective_weights"].get(metric)
            weight_text = (
                "nicht verwendet"
                if effective_weight is None
                else f"effektives Gewicht {effective_weight * 100:.2f} %"
            )
            lines.append(
                f"- {METRIC_LABELS[metric]}: {score_text(value)} ({weight_text})"
            )
        lines.extend(
            [
                f"- Räumliches Alpha: {score_text(scores['alpha_layout'])}",
                f"- Vertrauen: {item['comparison_confidence']}",
                f"- Gruppenmedian / Streuung: {statistics_data['median_score']:.2f} % / {statistics_data['standard_deviation']:.2f}",
                (
                    f"- Schlechtester Vergleich: {markdown_escape(worst['file'])} ({worst['score']:.2f} %)"
                    if worst is not None
                    else "- Schlechtester Vergleich: nicht verfügbar"
                ),
                f"- Canvas: {item['canvas']['width']} × {item['canvas']['height']} px",
                f"- Richtung / Gruppe: {item['direction'] or 'unbekannt'} / {markdown_escape(item['comparison_group'])}",
            ]
        )
        if anchor is None:
            lines.append("- Sprite-Anker: nicht erkannt")
        else:
            lines.append(
                f"- Sprite-Anker: x={anchor['anchor_x_px']:.2f}, y={anchor['anchor_y_px']:.2f}, "
                f"unterer Rand={anchor['bottom_margin_px']:.2f} px, Vertrauen={anchor['confidence']:.2f}"
            )
        anchor_comparison = item["anchor_comparison"]
        if anchor_comparison.get("available"):
            lines.append(
                "- Anker-Gruppenbezug: "
                f"vertikal {anchor_comparison['vertical_score']:.2f} %, "
                + (
                    "horizontal nicht bewertet"
                    if anchor_comparison["horizontal_score"] is None
                    else f"horizontal {anchor_comparison['horizontal_score']:.2f} %"
                )
            )
            paired = anchor_comparison.get("paired_comparison")
            if paired is not None:
                lines.append(
                    f"- Ankerpaar {markdown_escape(paired['file'])}: "
                    f"Δx={paired['delta_x_px']:.2f} px, Δy={paired['delta_y_px']:.2f} px, "
                    f"normierter Abstand={paired['distance_normalized']:.2f}"
                )
        lines.append(
            f"- Vergleichsmaske: {item['comparison_mask']['source']} "
            f"({item['comparison_mask']['occupied_percent']:.2f} %)"
        )
        if item["duplicate_of"] is not None:
            lines.append(f"- Duplikat von: {markdown_escape(item['duplicate_of'])}")
        if item["findings"]:
            lines.append("- Statusrelevante Auffälligkeiten:")
            lines.extend(
                f"  - [{finding['severity']}] {markdown_escape(finding['message'])}"
                for finding in item["findings"]
            )
        if item["hints"]:
            lines.append("- Hinweise:")
            lines.extend(f"  - {markdown_escape(hint)}" for hint in item["hints"])
        else:
            lines.append("- Hinweise: keine auffällige Einzelabweichung.")
        lines.append("")

    lines.extend(["## Änderungen seit dem vorherigen Report", ""])
    changed_items = [
        item for item in data["items"] if item["change_from_previous"] is not None
    ]
    if history["status"] != "comparable":
        lines.append(f"- {markdown_escape(history['reason'])}")
    elif not changed_items:
        lines.append("- Keine auswertbaren Einzeländerungen vorhanden.")
    else:
        for item in changed_items:
            change = item["change_from_previous"]
            total = change["total_score"]
            delta_text = (
                f"{total:+.2f}" if total is not None and total != 0 else "±0.00"
            )
            lines.append(
                f"- {markdown_escape(item['file'])}: {delta_text} Prozentpunkte; "
                f"{change['previous_status'] or 'unbekannt'} → {change['current_status']}"
            )
            metric_changes = change["scores"]
            if metric_changes:
                formatted_metrics = []
                for metric in (*SCORE_WEIGHTS, "alpha_layout"):
                    if metric not in metric_changes:
                        continue
                    label = (
                        "Räumliches Alpha"
                        if metric == "alpha_layout"
                        else METRIC_LABELS[metric]
                    )
                    delta = metric_changes[metric]
                    formatted_metrics.append(
                        f"{label} {delta:+.2f}" if delta else f"{label} ±0.00"
                    )
                lines.append("  - Teilwerte: " + "; ".join(formatted_metrics))
            if change["added_hints"]:
                lines.append(
                    "  - Neue Hinweise: "
                    + "; ".join(markdown_escape(hint) for hint in change["added_hints"])
                )
            if change["removed_hints"]:
                lines.append(
                    "  - Entfallene Hinweise: "
                    + "; ".join(
                        markdown_escape(hint) for hint in change["removed_hints"]
                    )
                )
    lines.append("")

    lines.extend(["## Übersprungene Dateien", ""])
    if data["skipped_files"]:
        for item in data["skipped_files"]:
            lines.append(
                f"- {markdown_escape(item['file'])}: {markdown_escape(item['reason'])}"
            )
    else:
        lines.append("- Keine.")
    lines.append("")
    return "\n".join(lines)


def write_reports(paths: ReportPaths, data: Mapping[str, Any]) -> None:
    markdown = build_markdown_report(data)
    json_text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    atomic_write_text(paths.markdown, markdown)
    atomic_write_text(paths.json, json_text)


def terminal_safe_name(name: str) -> str:
    return clean_text(name).replace("\033", "?")


def display_percent(score: float) -> str:
    return f"{max(0.0, min(100.0, score)):.2f}"


def render_bar(score: float) -> str:
    filled = max(0, min(BAR_WIDTH, math.floor(score * BAR_WIDTH / 100.0 + 0.5)))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def overall_presentation(status: str) -> tuple[str, str, str]:
    label, emoji, color = STATUS_DATA[status]
    if status == "very_good":
        # Der Diamant und Türkis gelten bewusst nur für die Gesamtzeile.
        return label, "💎", "96"
    return label, emoji, color


def format_trend_line(history: HistoryResult) -> str:
    assert history.previous_average_score is not None
    assert history.current_average_score is not None
    assert history.delta_percentage_points is not None
    before = history.previous_average_score
    current = history.current_average_score
    delta = history.delta_percentage_points
    if history.direction == "improved":
        return (
            f"↗ Verbesserung zum vorherigen Report: +{delta:.2f} Prozentpunkte "
            f"({before:.2f} % → {current:.2f} %)"
        )
    if history.direction == "declined":
        return (
            f"↘ Rückgang zum vorherigen Report: {delta:.2f} Prozentpunkte "
            f"({before:.2f} % → {current:.2f} %)"
        )
    return (
        "◆ Unverändert zum vorherigen Report: ±0.00 Prozentpunkte "
        f"({before:.2f} % → {current:.2f} %)"
    )


def print_results(
    folder: Path,
    scored: Sequence[ScoredImage],
    skipped: Sequence[SkippedFile],
    theme: Theme,
    report_available: bool,
    history: HistoryResult | None,
    mixed_group: bool,
) -> None:
    names = [terminal_safe_name(item.features.path.name) for item in scored]
    name_width = max(len(name) for name in names)
    print("\n📊 PyImgCompare\n")
    print(f"Ordner: {terminal_safe_name(folder.name)}")
    print(f"Gefundene Bilder: {len(scored) + len(skipped)}\n")
    for result, name in zip(scored, names):
        label, emoji, color = STATUS_DATA[result.status]
        del label
        bar = theme.paint(f"[{render_bar(result.total_score)}]", color)
        finding_text = ""
        if result.findings:
            primary = result.findings[0]
            qualifier = "kritisch" if primary.severity == "critical" else "auffällig"
            additional = (
                f" +{len(result.findings) - 1}" if len(result.findings) > 1 else ""
            )
            finding_text = f"  {METRIC_LABELS[primary.metric]} {qualifier}{additional}"
        print(
            f"{name:<{name_width}}  {bar} "
            f"{display_percent(result.total_score):>6}% {emoji}{finding_text}"
        )

    average = group_average_score(scored)
    overall_status = group_status(scored)
    overall_label, overall_emoji, overall_color = overall_presentation(overall_status)
    counts = Counter(item.status for item in scored)
    print()
    print(
        theme.paint(
            f"{overall_emoji} Gesamt: {overall_label} ({average:.2f} %)",
            overall_color,
        )
    )
    if history is not None:
        if history.status == "comparable":
            print(format_trend_line(history))
        elif history.status not in {"first_run"}:
            print(f"◆ {history.reason}")
    empty_count = sum(item.classification == "empty" for item in scored)
    duplicate_count = sum(item.features.duplicate_of is not None for item in scored)
    if empty_count or duplicate_count:
        notices: list[str] = []
        if empty_count:
            notices.append(
                f"{empty_count} leeres Bild"
                if empty_count == 1
                else f"{empty_count} leere Bilder"
            )
        if duplicate_count:
            notices.append(
                f"{duplicate_count} Duplikat"
                if duplicate_count == 1
                else f"{duplicate_count} Duplikate"
            )
        print(theme.paint(f"⚠️ {' · '.join(notices)}", "33"))
    nearly_empty_count = sum(item.classification == "nearly_empty" for item in scored)
    if nearly_empty_count:
        print(
            theme.paint(
                f"⚠️ Nahezu leer: {nearly_empty_count} "
                f"{'Bild' if nearly_empty_count == 1 else 'Bilder'}",
                "33",
            )
        )
    if scored[0].confidence == "low":
        print(theme.paint("⚠️ Bewertungsvertrauen: niedrig", "33"))
    if mixed_group:
        print(theme.paint("⚠️ Gemischte Gruppe: getrennte Stilcluster erkannt", "33"))
    if counts["warning"]:
        noun = "Bild" if counts["warning"] == 1 else "Bildern"
        print(theme.paint(f"⚠️ Warnung bei {counts['warning']} {noun}", "33"))
    if counts["critical"]:
        noun = "Bild" if counts["critical"] == 1 else "Bildern"
        print(theme.paint(f"❌ Kritisch bei {counts['critical']} {noun}", "31"))
    if skipped:
        noun = "Datei" if len(skipped) == 1 else "Dateien"
        suffix = "; Details im Report" if report_available else ""
        print(theme.paint(f"⚠️ Übersprungen: {len(skipped)} {noun}{suffix}", "33"))


def run(no_color: bool = False, no_report: bool = False) -> int:
    folder = Path.cwd()  # Absichtlich nicht der Ordner dieser Skriptdatei.
    sources = find_images(folder)
    if len(sources) < 2:
        print(
            "FEHLER: Mindestens zwei unterstützte Bilder direkt im aktuellen "
            "Ordner sind erforderlich.",
            file=sys.stderr,
        )
        return 1

    features: list[ImageFeatures] = []
    skipped: list[SkippedFile] = []
    for source in sources:
        try:
            features.append(analyze_image(source))
        except MemoryError:
            skipped.append(
                SkippedFile(source, "MemoryError: nicht genügend Arbeitsspeicher")
            )
        except (
            SkipImage,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            EOFError,
            OSError,
            SyntaxError,
            ValueError,
        ) as exc:
            # Eine beschädigte oder vom installierten Codec nicht lesbare Datei
            # darf den Vergleich der übrigen Gruppe nicht abbrechen.
            skipped.append(SkippedFile(source, f"{type(exc).__name__}: {exc}"))

    if len(features) < 2:
        print(
            f"FEHLER: Nur {len(features)} von {len(sources)} Bilddateien konnten "
            "gelesen werden; mindestens zwei sind erforderlich.",
            file=sys.stderr,
        )
        for item in skipped:
            print(
                f"  - {terminal_safe_name(item.path.name)}: {item.reason}",
                file=sys.stderr,
            )
        return 1

    features = annotate_duplicates(features)
    layout = choose_layout(features)
    history: HistoryResult | None = None
    if no_report:
        with tempfile.TemporaryDirectory(prefix="pyimgcompare_") as temporary_name:
            temporary_sheet = Path(temporary_name) / SPRITESHEET_NAME
            create_spritesheet(features, layout, temporary_sheet)
            scored = score_group(features)
    else:
        scored = score_group(features)
        # score_group gibt die kanonisch annotierten Feature-Objekte zurück.
        features = [item.features for item in scored]
        output = ensure_output_folder(folder)
        history = make_history_result(
            find_previous_report(output, folder), features, scored
        )
        paths = allocate_report_paths(output)
        output_targets = (paths.spritesheet, paths.markdown, paths.json)
        for target in output_targets:
            check_new_output_target(target)
        cell_size = create_spritesheet(features, layout, paths.spritesheet)
        mixed_group, mixed_clusters = detect_mixed_group(features)
        data = build_json_report(
            folder,
            len(sources),
            scored,
            skipped,
            layout,
            cell_size,
            paths,
            history,
            mixed_group,
            mixed_clusters,
        )
        write_reports(paths, data)

    if no_report:
        features = [item.features for item in scored]
        mixed_group, _ = detect_mixed_group(features)

    color_enabled = (
        not no_color
        and sys.stdout.isatty()
        and "NO_COLOR" not in os.environ
        and os.environ.get("TERM", "") != "dumb"
    )
    print_results(
        folder,
        scored,
        skipped,
        Theme(color_enabled),
        report_available=not no_report,
        history=history,
        mixed_group=mixed_group,
    )
    return 1 if skipped else 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        options = parse_arguments(argv)
        load_pillow()
        return run(no_color=options.no_color, no_report=options.no_report)
    except KeyboardInterrupt:
        print("\nAbgebrochen. Quelldateien bleiben unverändert.", file=sys.stderr)
        return 130
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
