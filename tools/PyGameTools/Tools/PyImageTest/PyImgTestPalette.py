#!/usr/bin/env python3
"""Farbpaletten mehrerer Bilder im aktuellen Ordner vergleichen.

PyImgTestPalette ist die farbspezifische Ergänzung zu PyImgTestCompare.py.
Das Werkzeug liest unterstützte, statische Rasterbilder direkt aus dem
aktuellen Terminalordner (ohne Unterordner), bestimmt pro Bild eine
alpha-gewichtete CIELAB-Palette und bewertet deren Übereinstimmung mit der
Mehrheit des Bildsatzes.

Zusätzlich prüft das Werkzeug das gewählte Farblimit gegen die tatsächlich
vorkommenden sichtbaren RGB-Werte der Quelldatei. Bei einer Überschreitung
erscheint eine score-neutrale Warnung; vollständig transparente Pixel zählen
nicht.

Standardmäßig entstehen in ``.compare`` drei neue, niemals überschriebene
Dateien pro Lauf:

* ``palette_figure_<UTC-ID>.png`` – Farbtafel, bei passenden Namen als
  Kompass mit acht Richtungen
* ``palette_report_<UTC-ID>.md`` – lesbarer Bericht
* ``palette_report_<UTC-ID>.json`` – strukturierte Messwerte

Bei aktiviertem Report wird der neue Lauf mit dem letzten gültigen Report
desselben Ordners verglichen. Ein Fortschritt wird nur bei gleichem Bildsatz
und identischem Bewertungsmodell ausgewiesen.

Mit ``--no-report`` bleibt die Ausgabe ausschließlich im Terminal und
``.compare`` wird weder gelesen noch verändert.

Abhängigkeit: Python >= 3.10 und Pillow >= 9.1
Installation: python3 -m pip install --upgrade Pillow
"""

from __future__ import annotations

import argparse
import colorsys
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
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "1.4.0"
SCHEMA_VERSION = 4
SCORING_MODEL_ID = "palette-majority-consistency-v3"
OUTPUT_FOLDER = ".compare"
MAX_REPORT_HISTORY_BYTES = 16 * 1024 * 1024

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

ANALYSIS_EDGE = 192
PALETTE_COVERAGE_TARGET = 0.95
PALETTE_COLOR_CHOICES = (64, 48, 32, 24, 20, 16, 12, 8)
DEFAULT_PALETTE_COLOR_LIMIT = 64
LAB_LIGHTNESS_BINS = 12
LAB_COLOR_BINS = 16
GLOBAL_CLUSTER_DELTA_E = 14.0
DEVIATION_DELTA_E = 22.0
BAR_WIDTH = 20
PALETTE_BAR_WIDTH = 12
MAX_FIGURE_ITEMS = 60
MAX_FIGURE_PIXELS = 64_000_000

STATUS_DATA = {
    "very_good": ("Sehr gut abgestimmt", "✅", "32"),
    "good": ("Gut abgestimmt", "🟢", "32"),
    "warning": ("Farbabweichung", "⚠️", "33"),
    "critical": ("Starke Farbabweichung", "❌", "31"),
}
STATUS_RANK = {"very_good": 0, "good": 1, "warning": 2, "critical": 3}

DIRECTION_ORDER = ("nw", "n", "ne", "w", "e", "sw", "s", "se")
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
DIRECTION_SHORT_LABELS = {
    "nw": "NW",
    "n": "N",
    "ne": "NO",
    "w": "W",
    "e": "O",
    "sw": "SW",
    "s": "S",
    "se": "SO",
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


class SkipImage(Exception):
    """Eine Bilddatei kann bewusst nicht sicher ausgewertet werden."""


@dataclass(frozen=True)
class PaletteColor:
    rgb: tuple[int, int, int]
    lab: tuple[float, float, float]
    weight: float

    @property
    def hex(self) -> str:
        return "#{:02X}{:02X}{:02X}".format(*self.rgb)


@dataclass(frozen=True)
class ImagePalette:
    path: Path
    width: int
    height: int
    visible_pixels: int
    visible_fraction: float
    sampled_color_weight: float
    rgba_sha256: str
    direction: str | None
    colors: tuple[PaletteColor, ...]
    all_colors: tuple[PaletteColor, ...]
    palette_coverage: float
    palette_color_limit: int
    visible_rgb_color_count: int
    visible_rgb_color_count_exact: bool


@dataclass(frozen=True)
class GlobalPaletteColor:
    rgb: tuple[int, int, int]
    lab: tuple[float, float, float]
    average_share: float
    image_count: int
    image_shares: Mapping[int, float]

    @property
    def hex(self) -> str:
        return "#{:02X}{:02X}{:02X}".format(*self.rgb)


@dataclass(frozen=True)
class ReferencePalette:
    colors: tuple[PaletteColor, ...]
    strategy: str
    source_file: str | None
    majority_threshold: int
    stable_coverage: float
    dominant_support: int


@dataclass(frozen=True)
class ComparisonMetrics:
    score: float
    palette_match: float
    distribution_match: float
    dominant_match: float
    deviation_share: float
    dominant_delta_e: float


@dataclass(frozen=True)
class ScoredPalette:
    profile: ImagePalette
    metrics: ComparisonMetrics
    status: str
    hints: tuple[str, ...]


@dataclass(frozen=True)
class SkippedFile:
    path: Path
    reason: str


@dataclass(frozen=True)
class ReportPaths:
    run_id: str
    created_at_utc: str
    figure: Path
    markdown: Path
    json: Path


@dataclass(frozen=True)
class PreviousReport:
    path: Path
    created_timestamp: float
    average_score: float
    scoring_model_fingerprint: str
    logical_names: tuple[str, ...]
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
    """ANSI- und Truecolor-Ausgabe zentral und abschaltbar verwalten."""

    RESET = "\033[0m"

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def paint(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}{self.RESET}"

    def swatch(self, rgb: tuple[int, int, int]) -> str:
        if not self.enabled:
            return "██"
        red, green, blue = rgb
        return f"\033[38;2;{red};{green};{blue}m██{self.RESET}"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="PyImgTestPalette",
        description=(
            "Vergleicht die Farbpaletten aller unterstützten Bilder direkt im "
            "aktuellen Terminalordner. Keine Unterordner und keine Rekursion."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Bewertung:
  Jedes Bild zählt gleich viel. Die Palette wird pro Bild dynamisch bis zu
  mindestens 95 Prozent Farbdeckung erweitert (standardmäßig höchstens 64
  Farben). Das Limit kann mit --palette-colors geändert werden.
  Zusätzlich wird gewarnt, wenn eine Quelldatei tatsächlich mehr sichtbare
  RGB-Farben als dieses Limit enthält. Diese Warnung verändert den
  Konsistenz-Score nicht.
  Mehrheitsfarben bilden den Kern; weitere Farben aus mindestens zwei Bildern
  ergänzen die gemeinsame Referenzpalette. Einzelne Fremdfarben werden klar
  gewichtet. Gibt es keine stabile Mehrheit, wird fair paarweise bewertet.

Optionale Richtungsdarstellung:
  Dateinamen mit n, no/ne, o/e, so/se, s, sw, w oder nw können die Farbtafel
  als Kompass anordnen. Diese Namen beeinflussen ausschließlich das Layout;
  bewertet werden immer alle Bilder gemeinsam als eine Gruppe.

Ausgabe pro Lauf:
  .compare/palette_figure_<UTC-ID>.png
  .compare/palette_report_<UTC-ID>.md
  .compare/palette_report_<UTC-ID>.json

Bei gleichem Bildsatz und Bewertungsmodell zeigt jeder Reportlauf die
Verbesserung oder den Rückgang gegenüber dem letzten gültigen Report.

Mindestens zwei lesbare, statische Bilder sind erforderlich. Quelldateien
werden nie verändert. Mit --no-report bleibt ausschließlich die farbige
Terminalausgabe; .compare wird dann nicht gelesen, angelegt oder verändert.
""",
    )
    parser.add_argument(
        "--palette-colors",
        type=int,
        choices=PALETTE_COLOR_CHOICES,
        default=DEFAULT_PALETTE_COLOR_LIMIT,
        metavar="{64,48,32,24,20,16,12,8}",
        help=(
            "Maximale Palettengröße je Bild; die Auswahl endet früher, sobald "
            "mindestens 95 %% Abdeckung erreicht sind (Standard: %(default)s)."
        ),
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="ANSI- und Truecolor-Farben im Terminal abschalten.",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Nur im Terminal ausgeben, keinen Verlauf laden und .compare nicht verändern.",
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
    global Image, ImageDraw, ImageFont, ImageOps
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps
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


def logical_name(path: Path) -> str:
    """Dateinamen nur für die Vergleichbarkeit zweier Reportläufe normieren."""
    return unicodedata.normalize("NFC", path.name)


def normalized_name_tokens(stem: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", stem.casefold())
    ascii_like = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", ascii_like)


def detect_direction(stem: str) -> str | None:
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


def open_static_rgba(path: Path) -> Any:
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
    getter = getattr(image, "get_flattened_data", None)
    return getter() if getter is not None else image.getdata()


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


def lab_bin_index(lab: Sequence[float]) -> int:
    lightness, green_red, blue_yellow = lab
    light_bin = min(
        LAB_LIGHTNESS_BINS - 1,
        max(0, int(lightness / 100.0 * LAB_LIGHTNESS_BINS)),
    )
    green_red_bin = min(
        LAB_COLOR_BINS - 1,
        max(0, int((green_red + 128.0) / 256.0 * LAB_COLOR_BINS)),
    )
    blue_yellow_bin = min(
        LAB_COLOR_BINS - 1,
        max(0, int((blue_yellow + 128.0) / 256.0 * LAB_COLOR_BINS)),
    )
    return (
        light_bin * LAB_COLOR_BINS + green_red_bin
    ) * LAB_COLOR_BINS + blue_yellow_bin


def delta_e(first: Sequence[float], second: Sequence[float]) -> float:
    return math.dist(first[:3], second[:3])


def rgba_content_hash(image: Any) -> str:
    digest = hashlib.sha256()
    digest.update(b"PyImgTestPalette-RGBA-v1\0")
    digest.update(image.width.to_bytes(8, "big"))
    digest.update(image.height.to_bytes(8, "big"))
    digest.update(image.tobytes())
    return digest.hexdigest()


def count_visible_rgb_colors(image: Any, limit: int) -> tuple[int, bool]:
    """Quellfarben bis zur sicheren Feststellung einer Limitüberschreitung zählen.

    Vollständig transparente Pixel zählen nicht. Sobald ``limit + 1`` Farben
    gefunden wurden, ist die gewünschte Warnentscheidung eindeutig und die
    potenziell teure Suche nach sämtlichen weiteren Farben endet.
    """
    colors: set[tuple[int, int, int]] = set()
    for red, green, blue, alpha_value in flattened_pixels(image):
        if alpha_value <= 0:
            continue
        colors.add((red, green, blue))
        if len(colors) > limit:
            return len(colors), False
    return len(colors), True


def analyze_image(
    path: Path,
    palette_color_limit: int = DEFAULT_PALETTE_COLOR_LIMIT,
) -> ImagePalette:
    image = open_static_rgba(path)
    sample = None
    alpha = None
    try:
        alpha = image.getchannel("A")
        histogram = alpha.histogram()
        total_pixels = image.width * image.height
        visible_pixels = total_pixels - histogram[0]
        visible_fraction = visible_pixels / total_pixels if total_pixels else 0.0
        content_hash = rgba_content_hash(image)
        visible_rgb_color_count, visible_rgb_color_count_exact = (
            count_visible_rgb_colors(image, palette_color_limit)
        )
        sample = resized_for_analysis(image, ANALYSIS_EDGE)

        # Wert, Lab-Summen und RGB-Summen je Wahrnehmungs-Bin. Alpha ist das
        # Pixelgewicht; vollständig transparente versteckte RGB-Werte zählen nie.
        bins: dict[int, list[float]] = {}
        total_weight = 0.0
        for red, green, blue, alpha_value in flattened_pixels(sample):
            weight = alpha_value / 255.0
            if weight <= 0.0:
                continue
            lab = rgb_to_lab(red, green, blue)
            index = lab_bin_index(lab)
            values = bins.setdefault(index, [0.0] * 7)
            values[0] += weight
            values[1] += lab[0] * weight
            values[2] += lab[1] * weight
            values[3] += lab[2] * weight
            values[4] += red * weight
            values[5] += green * weight
            values[6] += blue * weight
            total_weight += weight

        all_colors: list[PaletteColor] = []
        if total_weight > 0.0:
            for values in bins.values():
                weight = values[0]
                all_colors.append(
                    PaletteColor(
                        rgb=(
                            round(values[4] / weight),
                            round(values[5] / weight),
                            round(values[6] / weight),
                        ),
                        lab=(
                            values[1] / weight,
                            values[2] / weight,
                            values[3] / weight,
                        ),
                        weight=weight / total_weight,
                    )
                )
        all_colors.sort(key=lambda color: (-color.weight, color.rgb))
        # Nicht eine starre Anzahl Farben verwenden: Gerade bei Pixel-Art mit
        # vielen Schattierungen deckten acht Einträge teilweise nur die Hälfte
        # des Motivs ab. Stattdessen so lange erweitern, bis mindestens 95 %
        # der sichtbaren Farbmenge vertreten sind (mit einer Sicherheitsgrenze).
        selected: list[PaletteColor] = []
        selected_coverage = 0.0
        for color in all_colors:
            if len(selected) >= palette_color_limit:
                break
            selected.append(color)
            selected_coverage += color.weight
            if selected_coverage >= PALETTE_COVERAGE_TARGET:
                break
        palette = tuple(selected)
        return ImagePalette(
            path=path,
            width=image.width,
            height=image.height,
            visible_pixels=visible_pixels,
            visible_fraction=visible_fraction,
            sampled_color_weight=total_weight,
            rgba_sha256=content_hash,
            direction=detect_direction(path.stem),
            colors=palette,
            all_colors=tuple(all_colors),
            palette_coverage=selected_coverage,
            palette_color_limit=palette_color_limit,
            visible_rgb_color_count=visible_rgb_color_count,
            visible_rgb_color_count_exact=visible_rgb_color_count_exact,
        )
    finally:
        if alpha is not None:
            alpha.close()
        if sample is not None:
            sample.close()
        image.close()


class _ColorCluster:
    def __init__(self, image_index: int, color: PaletteColor) -> None:
        self.total_weight = 0.0
        self.lab_sums = [0.0, 0.0, 0.0]
        self.rgb_sums = [0.0, 0.0, 0.0]
        self.image_shares: dict[int, float] = defaultdict(float)
        self.add(image_index, color)

    @property
    def lab(self) -> tuple[float, float, float]:
        return tuple(value / self.total_weight for value in self.lab_sums)  # type: ignore[return-value]

    @property
    def rgb(self) -> tuple[int, int, int]:
        return tuple(round(value / self.total_weight) for value in self.rgb_sums)  # type: ignore[return-value]

    def add(self, image_index: int, color: PaletteColor) -> None:
        self.total_weight += color.weight
        for channel in range(3):
            self.lab_sums[channel] += color.lab[channel] * color.weight
            self.rgb_sums[channel] += color.rgb[channel] * color.weight
        self.image_shares[image_index] += color.weight


def build_global_palette(
    profiles: Sequence[ImagePalette],
) -> tuple[GlobalPaletteColor, ...]:
    clusters: list[_ColorCluster] = []
    entries = sorted(
        (
            (image_index, color)
            for image_index, profile in enumerate(profiles)
            for color in profile.colors
        ),
        key=lambda item: (-item[1].weight, item[0], item[1].rgb),
    )
    for image_index, color in entries:
        nearest: _ColorCluster | None = None
        nearest_distance = math.inf
        for cluster in clusters:
            distance = delta_e(color.lab, cluster.lab)
            if distance < nearest_distance:
                nearest = cluster
                nearest_distance = distance
        if nearest is not None and nearest_distance <= GLOBAL_CLUSTER_DELTA_E:
            nearest.add(image_index, color)
        else:
            clusters.append(_ColorCluster(image_index, color))

    divisor = max(1, len(profiles))
    result = [
        GlobalPaletteColor(
            rgb=cluster.rgb,
            lab=cluster.lab,
            average_share=cluster.total_weight / divisor,
            image_count=len(cluster.image_shares),
            image_shares=dict(cluster.image_shares),
        )
        for cluster in clusters
    ]
    result.sort(key=lambda color: (-color.average_share, -color.image_count, color.rgb))
    return tuple(result)


def perceptual_similarity(distance: float) -> float:
    adjusted = max(0.0, distance - 2.0)
    return math.exp(-((adjusted / 22.0) ** 1.35))


def directed_palette_match(
    source: Sequence[PaletteColor], target: Sequence[PaletteColor]
) -> float:
    if not source and not target:
        return 1.0
    if not source or not target:
        return 0.0
    source_weight = sum(color.weight for color in source)
    if source_weight <= 0.0:
        return 0.0
    return (
        sum(
            color.weight
            * perceptual_similarity(
                min(delta_e(color.lab, candidate.lab) for candidate in target)
            )
            for color in source
        )
        / source_weight
    )


def simple_pair_similarity(first: ImagePalette, second: ImagePalette) -> float:
    return 0.5 * (
        directed_palette_match(first.all_colors, second.colors)
        + directed_palette_match(second.all_colors, first.colors)
    )


def choose_medoid(profiles: Sequence[ImagePalette]) -> ImagePalette:
    nonempty = [profile for profile in profiles if profile.colors]
    if not nonempty:
        return profiles[0]
    if len(nonempty) == 1:
        return nonempty[0]
    ranked: list[tuple[float, ImagePalette]] = []
    for profile in nonempty:
        similarities = [
            simple_pair_similarity(profile, peer)
            for peer in nonempty
            if peer.path != profile.path
        ]
        ranked.append((statistics.mean(similarities), profile))
    # Der Name ist nur der stabile Tie-Breaker und beeinflusst keine Messung.
    best_score = max(item[0] for item in ranked)
    candidates = [item[1] for item in ranked if item[0] == best_score]
    return min(
        candidates,
        key=lambda profile: (profile.path.name.casefold(), profile.path.name),
    )


def build_reference_palette(
    profiles: Sequence[ImagePalette],
    global_palette: Sequence[GlobalPaletteColor],
) -> ReferencePalette:
    nonempty = [profile for profile in profiles if profile.colors]
    majority_threshold = len(profiles) // 2 + 1
    stable = [
        color for color in global_palette if color.image_count >= majority_threshold
    ]
    stable_coverage = sum(color.average_share for color in stable)
    if stable and stable_coverage >= 0.25:
        # Kernfarben müssen in einer echten Mehrheit vorkommen. Ergänzende
        # Farben aus wenigstens zwei Bildern gehören ebenfalls zur erlaubten
        # Gruppenpalette, damit blickwinkelabhängig sichtbare Details nicht als
        # Fremdfarbe gelten. Ein nur einmal auftretender Ton bleibt auffällig.
        stable_ids = {id(color) for color in stable}
        shared = [
            color
            for color in global_palette
            if color.image_count >= 2 and id(color) not in stable_ids
        ]
        reference_colors = [*stable, *shared]
        total = sum(color.average_share for color in reference_colors)
        colors = tuple(
            PaletteColor(color.rgb, color.lab, color.average_share / total)
            for color in reference_colors
        )
        return ReferencePalette(
            colors=colors,
            strategy="strict_majority",
            source_file=None,
            majority_threshold=majority_threshold,
            stable_coverage=stable_coverage,
            dominant_support=stable[0].image_count,
        )

    if len(nonempty) < 2:
        only = nonempty[0] if nonempty else profiles[0]
        total = sum(color.weight for color in only.colors)
        colors = (
            tuple(
                PaletteColor(color.rgb, color.lab, color.weight / total)
                for color in only.colors
            )
            if total
            else ()
        )
        return ReferencePalette(
            colors=colors,
            strategy="insufficient_visible_palettes",
            source_file=only.path.name if colors else None,
            majority_threshold=majority_threshold,
            stable_coverage=stable_coverage,
            dominant_support=1 if colors else 0,
        )

    medoid = choose_medoid(profiles)
    total = sum(color.weight for color in medoid.colors)
    colors = (
        tuple(
            PaletteColor(color.rgb, color.lab, color.weight / total)
            for color in medoid.colors
        )
        if total
        else ()
    )
    return ReferencePalette(
        colors=colors,
        strategy="pairwise_no_majority",
        source_file=medoid.path.name,
        majority_threshold=majority_threshold,
        stable_coverage=stable_coverage,
        dominant_support=1 if colors else 0,
    )


def compare_with_colors(
    profile: ImagePalette, reference_colors: Sequence[PaletteColor]
) -> ComparisonMetrics:
    if not profile.colors or not reference_colors:
        return ComparisonMetrics(0.0, 0.0, 0.0, 0.0, 1.0, 100.0)

    source_to_reference = directed_palette_match(profile.all_colors, reference_colors)
    reference_to_source = directed_palette_match(reference_colors, profile.all_colors)
    # Entscheidend ist, ob die Farben des Bildes zur Gruppenpalette gehören.
    # Fehlende Referenzfarben zählen nur schwach, weil eine Blickrichtung nicht
    # zwangsläufig jede Fläche der Figur zeigt.
    palette_match = 0.85 * source_to_reference + 0.15 * reference_to_source

    assigned_weights = [0.0] * len(reference_colors)
    foreign_share = 0.0
    for color in profile.all_colors:
        distances = [delta_e(color.lab, target.lab) for target in reference_colors]
        nearest_index = min(range(len(distances)), key=distances.__getitem__)
        if distances[nearest_index] <= DEVIATION_DELTA_E:
            assigned_weights[nearest_index] += color.weight
        else:
            foreign_share += color.weight
    total_variation = 0.5 * (
        sum(
            abs(observed - target.weight)
            for observed, target in zip(assigned_weights, reference_colors)
        )
        + foreign_share
    )
    distribution_match = max(0.0, 1.0 - total_variation)

    source_dominant = profile.colors[0]
    reference_dominant = reference_colors[0]
    source_delta = min(
        delta_e(source_dominant.lab, target.lab) for target in reference_colors
    )
    reference_delta = min(
        delta_e(reference_dominant.lab, target.lab) for target in profile.colors
    )
    dominant_delta = max(source_delta, reference_delta)
    dominant_match = 0.5 * (
        perceptual_similarity(source_delta) + perceptual_similarity(reference_delta)
    )

    raw_score = 100.0 * (
        0.70 * palette_match + 0.10 * distribution_match + 0.20 * dominant_match
    )
    # Ein eigener, nichtlinearer Malus macht auch einen kleineren, klar fremden
    # Farbanteil sichtbar. Die regulären Teilwerte bestrafen ihn zusätzlich.
    score = raw_score - 35.0 * (foreign_share**0.80)
    if foreign_share >= 0.35 and dominant_delta >= 25.0:
        score = min(score, 49.0)
    elif foreign_share >= 0.15 and dominant_delta >= 18.0:
        score = min(score, 74.0)
    score = max(0.0, min(100.0, score))
    return ComparisonMetrics(
        score=score,
        palette_match=100.0 * palette_match,
        distribution_match=100.0 * distribution_match,
        dominant_match=100.0 * dominant_match,
        deviation_share=foreign_share,
        dominant_delta_e=dominant_delta,
    )


def mean_metrics(values: Sequence[ComparisonMetrics]) -> ComparisonMetrics:
    if not values:
        return ComparisonMetrics(0.0, 0.0, 0.0, 0.0, 1.0, 100.0)
    return ComparisonMetrics(
        score=statistics.mean(value.score for value in values),
        palette_match=statistics.mean(value.palette_match for value in values),
        distribution_match=statistics.mean(
            value.distribution_match for value in values
        ),
        dominant_match=statistics.mean(value.dominant_match for value in values),
        deviation_share=statistics.mean(value.deviation_share for value in values),
        dominant_delta_e=statistics.mean(value.dominant_delta_e for value in values),
    )


def symmetric_pair_metrics(
    first: ImagePalette, second: ImagePalette
) -> ComparisonMetrics:
    forward = compare_with_colors(first, second.colors)
    backward = compare_with_colors(second, first.colors)
    return mean_metrics((forward, backward))


def status_for(score: float) -> str:
    if score >= 90.0:
        return "very_good"
    if score >= 75.0:
        return "good"
    if score >= 50.0:
        return "warning"
    return "critical"


def hints_for(
    profile: ImagePalette,
    metrics: ComparisonMetrics,
    reference: ReferencePalette,
) -> tuple[str, ...]:
    hints: list[str] = []
    if not profile.colors:
        return ("Keine sichtbare Farbe erkannt; das Bild ist vollständig transparent.",)
    if profile.visible_rgb_color_count > profile.palette_color_limit:
        hints.append(
            f"Mehr als {profile.palette_color_limit} sichtbare RGB-Quellfarben "
            "erkannt; das gewählte Farblimit ist überschritten."
        )
    if metrics.deviation_share >= 0.20:
        hints.append(
            f"{metrics.deviation_share * 100.0:.1f} % der Farbmenge liegen klar "
            "außerhalb der Referenzpalette."
        )
    elif metrics.deviation_share >= 0.08:
        hints.append(
            f"{metrics.deviation_share * 100.0:.1f} % abweichender Farbanteil erkannt."
        )
    if metrics.dominant_delta_e >= 25.0:
        hints.append(
            f"Dominanter Ton weicht stark ab (ΔE {metrics.dominant_delta_e:.1f})."
        )
    elif metrics.dominant_delta_e >= 15.0:
        hints.append(
            f"Dominanter Ton ist sichtbar verschoben (ΔE {metrics.dominant_delta_e:.1f})."
        )
    if profile.palette_coverage < PALETTE_COVERAGE_TARGET:
        hints.append(
            f"Selbst {profile.palette_color_limit} Palettenfarben decken nur "
            f"{profile.palette_coverage * 100.0:.1f} % ab; sehr hohe "
            "Farbvielfalt erkannt."
        )
    if reference.strategy == "pairwise_no_majority":
        hints.append(
            "Keine stabile Mehrheitspalette; Ergebnis basiert auf Paarvergleichen."
        )
    elif reference.strategy == "insufficient_visible_palettes":
        hints.append(
            "Weniger als zwei Bilder besitzen sichtbare Farben; kein belastbarer "
            "Gruppenvergleich möglich."
        )
    return tuple(hints)


def score_profiles(
    profiles: Sequence[ImagePalette], reference: ReferencePalette
) -> list[ScoredPalette]:
    scored: list[ScoredPalette] = []
    if reference.strategy in {"strict_majority", "insufficient_visible_palettes"}:
        metrics_by_profile = [
            compare_with_colors(profile, reference.colors) for profile in profiles
        ]
    else:
        metrics_by_profile = []
        for index, profile in enumerate(profiles):
            comparisons = [
                symmetric_pair_metrics(profile, peer)
                for peer_index, peer in enumerate(profiles)
                if peer_index != index
            ]
            metrics_by_profile.append(mean_metrics(comparisons))

    for profile, metrics in zip(profiles, metrics_by_profile):
        status = status_for(metrics.score)
        scored.append(
            ScoredPalette(
                profile=profile,
                metrics=metrics,
                status=status,
                hints=hints_for(profile, metrics, reference),
            )
        )
    return scored


def overall_status(scored: Sequence[ScoredPalette]) -> str:
    return max((item.status for item in scored), key=STATUS_RANK.__getitem__)


def direction_summary(profiles: Sequence[ImagePalette]) -> dict[str, Any]:
    counts = Counter(
        profile.direction for profile in profiles if profile.direction is not None
    )
    missing = [direction for direction in DIRECTION_ORDER if counts[direction] == 0]
    duplicates = {direction: count for direction, count in counts.items() if count > 1}
    unknown = sum(profile.direction is None for profile in profiles)
    return {
        "recognized_unique": len(counts),
        "complete": len(counts) == 8,
        "exact_set": len(counts) == 8 and not duplicates and unknown == 0,
        "counts": {
            direction: counts[direction]
            for direction in DIRECTION_ORDER
            if counts[direction]
        },
        "missing": missing,
        "duplicates": dict(sorted(duplicates.items())),
        "unknown": unknown,
    }


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
            figure=output / f"palette_figure_{run_id}.png",
            markdown=output / f"palette_report_{run_id}.md",
            json=output / f"palette_report_{run_id}.json",
        )
        if not any(
            os.path.lexists(path) for path in (paths.figure, paths.markdown, paths.json)
        ):
            return paths
    raise RuntimeError("Keine freie UTC-ID für den neuen Report gefunden.")


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


def scoring_model_fingerprint(model: Mapping[str, Any]) -> str:
    comparable_model = {
        key: value for key, value in model.items() if key != "fingerprint"
    }
    encoded = json.dumps(
        comparable_model,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def report_items_by_logical_name(
    items: Any,
) -> dict[str, Mapping[str, Any]] | None:
    if not isinstance(items, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            return None
        filename = item.get("file")
        if (
            not isinstance(filename, str)
            or not filename
            or "/" in filename
            or "\\" in filename
        ):
            return None
        name = item.get("logical_name")
        if name is None:
            name = logical_name(Path(filename))
        score = item.get("score")
        if (
            not isinstance(name, str)
            or name in result
            or isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
            or not 0.0 <= float(score) <= 100.0
            or not isinstance(item.get("status"), str)
            or not isinstance(item.get("metrics"), Mapping)
        ):
            return None
        result[name] = item
    return result


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
    if (
        not isinstance(data, Mapping)
        or data.get("tool") != "PyImgTestPalette"
        or data.get("folder") != str(folder)
    ):
        return None
    summary = data.get("summary")
    model = data.get("scoring_model")
    run = data.get("run")
    if (
        not isinstance(summary, Mapping)
        or not isinstance(model, Mapping)
        or not isinstance(run, Mapping)
        or not isinstance(run.get("id"), str)
        or not isinstance(run.get("created_at_utc"), str)
    ):
        return None
    score = summary.get("average_score")
    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(float(score))
        or not 0.0 <= float(score) <= 100.0
    ):
        return None
    calculated_fingerprint = scoring_model_fingerprint(model)
    reported_fingerprint = model.get("fingerprint")
    if (
        reported_fingerprint is not None
        and reported_fingerprint != calculated_fingerprint
    ):
        return None
    mapped_items = report_items_by_logical_name(data.get("images"))
    if mapped_items is None or len(mapped_items) != data.get("image_count"):
        return None
    return PreviousReport(
        path=path,
        created_timestamp=report_created_timestamp(data, stat.st_mtime),
        average_score=float(score),
        scoring_model_fingerprint=calculated_fingerprint,
        logical_names=tuple(sorted(mapped_items)),
        items=mapped_items,
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
            path.name.startswith("palette_report_") and path.suffix.lower() == ".json"
        ):
            continue
        try:
            modified_ns = path.stat().st_mtime_ns
        except OSError:
            invalid_seen = True
            continue
        previous = parse_previous_report(path, folder)
        if previous is None:
            invalid_seen = True
            continue
        candidates.append(
            (
                previous.created_timestamp,
                modified_ns,
                path.name,
                previous,
            )
        )
    if not candidates:
        return PreviousReportSearch(None, invalid_seen)
    return PreviousReportSearch(
        max(candidates, key=lambda candidate: candidate[:3])[3], invalid_seen
    )


def check_new_output_target(path: Path) -> None:
    if os.path.lexists(path):
        raise RuntimeError(
            f"Ausgabedatei existiert bereits und wird nicht ersetzt: {path.name}"
        )


def temporary_path(destination: Path, suffix: str) -> tuple[int, Path]:
    fd, name = tempfile.mkstemp(
        prefix=".pyimgpalette_", suffix=suffix, dir=destination.parent
    )
    return fd, Path(name)


def install_new_file(temporary: Path, destination: Path) -> None:
    check_new_output_target(destination)
    try:
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise RuntimeError(
            f"Ausgabedatei existiert bereits und wird nicht ersetzt: {destination.name}"
        ) from exc
    except OSError as exc:
        unsupported = {
            errno.EPERM,
            errno.EXDEV,
            errno.EOPNOTSUPP,
            getattr(errno, "ENOTSUP", errno.EOPNOTSUPP),
        }
        if exc.errno not in unsupported:
            raise
        try:
            destination_fd = os.open(
                destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
        except FileExistsError as target_exc:
            raise RuntimeError(
                f"Ausgabedatei existiert bereits und wird nicht ersetzt: {destination.name}"
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


def save_png(destination: Path, image: Any) -> None:
    check_new_output_target(destination)
    fd, temporary = temporary_path(destination, ".png")
    try:
        with os.fdopen(fd, "wb") as stream:
            image.save(stream, format="PNG", compress_level=6)
            stream.flush()
            os.fsync(stream.fileno())
        install_new_file(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def load_font(size: int, bold: bool = False) -> Any:
    names = (
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        )
        if bold
        else (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        )
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def truncate_for_drawing(draw: Any, text: str, font: Any, width: int) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    suffix = "..."
    candidate = text
    while candidate and draw.textlength(candidate + suffix, font=font) > width:
        candidate = candidate[:-1]
    return candidate + suffix


def draw_palette_strip(
    draw: Any,
    colors: Sequence[PaletteColor],
    box: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = box
    if not colors:
        draw.rectangle(box, fill=(55, 59, 67), outline=(95, 101, 112))
        return
    total = sum(color.weight for color in colors)
    cursor = left
    for index, color in enumerate(colors):
        color_right = (
            right
            if index == len(colors) - 1
            else cursor + round((right - left) * color.weight / total)
        )
        color_right = max(cursor + 1, min(right, color_right))
        draw.rectangle((cursor, top, color_right, bottom), fill=color.rgb)
        cursor = color_right
    draw.rectangle(box, outline=(215, 218, 224), width=1)


def checkerboard(size: tuple[int, int], square: int = 10) -> Any:
    board = Image.new("RGBA", size, (225, 227, 231, 255))
    draw = ImageDraw.Draw(board)
    for y in range(0, size[1], square):
        for x in range(0, size[0], square):
            if (x // square + y // square) % 2:
                draw.rectangle(
                    (x, y, min(size[0], x + square), min(size[1], y + square)),
                    fill=(192, 196, 204, 255),
                )
    return board


def draw_profile_card(
    canvas: Any,
    draw: Any,
    scored: ScoredPalette,
    bounds: tuple[int, int, int, int],
    heading: str,
    duplicate_count: int = 1,
) -> None:
    left, top, right, bottom = bounds
    status_color = {
        "very_good": (42, 171, 92),
        "good": (54, 181, 105),
        "warning": (222, 165, 45),
        "critical": (218, 75, 75),
    }[scored.status]
    draw.rounded_rectangle(
        bounds,
        radius=14,
        fill=(35, 39, 47),
        outline=status_color,
        width=4,
    )
    title_font = load_font(22, bold=True)
    body_font = load_font(15)
    score_font = load_font(18, bold=True)
    draw.text((left + 14, top + 10), heading, font=title_font, fill=(240, 242, 246))
    score_text = f"{scored.metrics.score:.1f} %"
    score_width = draw.textlength(score_text, font=score_font)
    draw.text(
        (right - 14 - score_width, top + 13),
        score_text,
        font=score_font,
        fill=status_color,
    )
    filename = truncate_for_drawing(
        draw, scored.profile.path.name, body_font, right - left - 28
    )
    draw.text((left + 14, top + 42), filename, font=body_font, fill=(196, 201, 211))

    preview_box = (left + 14, top + 70, right - 14, bottom - 60)
    preview_size = (preview_box[2] - preview_box[0], preview_box[3] - preview_box[1])
    board = checkerboard(preview_size)
    source = open_static_rgba(scored.profile.path)
    try:
        source.thumbnail(
            (max(1, preview_size[0] - 12), max(1, preview_size[1] - 12)),
            Image.Resampling.NEAREST,
        )
        x = (preview_size[0] - source.width) // 2
        y = (preview_size[1] - source.height) // 2
        board.alpha_composite(source, (x, y))
        rendered_board = board.convert("RGB")
        try:
            canvas.paste(rendered_board, (preview_box[0], preview_box[1]))
        finally:
            rendered_board.close()
    finally:
        source.close()
        board.close()

    draw_palette_strip(
        draw,
        scored.profile.colors,
        (left + 14, bottom - 48, right - 14, bottom - 24),
    )
    count_text = analysis_tone_count_text(len(scored.profile.colors))
    source_limit_exceeded = (
        scored.profile.visible_rgb_color_count > scored.profile.palette_color_limit
    )
    if source_limit_exceeded:
        count_text += f" · WARN: >{scored.profile.palette_color_limit} RGB"
        count_color = (239, 183, 74)
    else:
        count_text += f" · {scored.profile.visible_rgb_color_count} RGB"
        count_color = (170, 176, 187)
    if duplicate_count > 1:
        count_text += f" · {duplicate_count} Bilder"
    count_text = truncate_for_drawing(draw, count_text, body_font, right - left - 28)
    draw.text((left + 14, bottom - 21), count_text, font=body_font, fill=count_color)


def draw_reference_card(
    draw: Any,
    reference: ReferencePalette,
    bounds: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = bounds
    draw.rounded_rectangle(
        bounds,
        radius=14,
        fill=(25, 29, 36),
        outline=(71, 188, 205),
        width=4,
    )
    title_font = load_font(19, bold=True)
    body_font = load_font(14)
    if reference.strategy == "strict_majority":
        label = "MEHRHEITSPALETTE"
    elif reference.strategy == "pairwise_no_majority":
        label = "GRUPPENMITTE"
    else:
        label = "EINZELPALETTE"
    draw.text((left + 12, top + 12), label, font=title_font, fill=(105, 213, 225))
    if reference.colors:
        dominant = reference.colors[0]
        draw.rectangle(
            (left + 12, top + 52, right - 12, top + 132),
            fill=dominant.rgb,
            outline=(230, 232, 236),
            width=2,
        )
        text_color = (
            (15, 18, 22) if relative_luminance(dominant.rgb) > 0.5 else (250, 250, 250)
        )
        draw.text(
            (left + 22, top + 78),
            dominant.hex,
            font=title_font,
            fill=text_color,
        )
        draw_palette_strip(
            draw,
            reference.colors,
            (left + 12, bottom - 58, right - 12, bottom - 32),
        )
    if reference.strategy == "strict_majority":
        strategy_text = f"Mehrheit ab {reference.majority_threshold} Bildern"
    elif reference.strategy == "pairwise_no_majority":
        strategy_text = "Keine stabile Farbmehrheit"
    else:
        strategy_text = "Zu wenig sichtbare Paletten"
    draw.text(
        (left + 12, bottom - 25), strategy_text, font=body_font, fill=(178, 184, 195)
    )


def create_palette_figure(
    scored: Sequence[ScoredPalette],
    reference: ReferencePalette,
    destination: Path,
) -> dict[str, Any]:
    by_direction: dict[str, list[ScoredPalette]] = defaultdict(list)
    for item in scored:
        if item.profile.direction is not None:
            by_direction[item.profile.direction].append(item)
    directional = len(by_direction) >= 3

    if directional:
        width = height = 960
        margin = 18
        gap = 12
        cell = (width - 2 * margin - 2 * gap) // 3
        canvas = Image.new("RGB", (width, height), (18, 21, 27))
        draw = ImageDraw.Draw(canvas)
        for direction, (row, column) in DIRECTION_POSITIONS.items():
            left = margin + column * (cell + gap)
            top = margin + row * (cell + gap)
            bounds = (left, top, left + cell, top + cell)
            candidates = by_direction.get(direction, [])
            if candidates:
                representative = min(candidates, key=lambda item: item.metrics.score)
                draw_profile_card(
                    canvas,
                    draw,
                    representative,
                    bounds,
                    DIRECTION_SHORT_LABELS[direction],
                    duplicate_count=len(candidates),
                )
            else:
                draw.rounded_rectangle(
                    bounds,
                    radius=14,
                    fill=(31, 34, 41),
                    outline=(103, 108, 119),
                    width=2,
                )
                title_font = load_font(24, bold=True)
                body_font = load_font(16)
                draw.text(
                    (left + 16, top + 14),
                    DIRECTION_SHORT_LABELS[direction],
                    font=title_font,
                    fill=(170, 176, 187),
                )
                draw.text(
                    (left + 16, top + 58),
                    "Kein Bild erkannt",
                    font=body_font,
                    fill=(125, 131, 142),
                )
        center_left = margin + cell + gap
        center_top = margin + cell + gap
        draw_reference_card(
            draw,
            reference,
            (center_left, center_top, center_left + cell, center_top + cell),
        )
        unknown_count = sum(item.profile.direction is None for item in scored)
        if unknown_count:
            footer_font = load_font(14)
            draw.text(
                (24, height - 22),
                f"Zusätzlich ohne eindeutige Richtung: {unknown_count}",
                font=footer_font,
                fill=(185, 190, 200),
            )
        layout = "directions"
        shown = sum(bool(items) for items in by_direction.values())
    else:
        shown_items = list(scored[:MAX_FIGURE_ITEMS])
        columns = min(3, len(shown_items))
        rows = math.ceil(len(shown_items) / columns)
        width = 960
        header_height = 190
        margin = 18
        gap = 12
        cell_width = (width - 2 * margin - (columns - 1) * gap) // columns
        cell_height = 280
        height = (
            header_height
            + margin
            + rows * cell_height
            + max(0, rows - 1) * gap
            + margin
        )
        if width * height > MAX_FIGURE_PIXELS:
            raise RuntimeError(
                "Die Paletten-Farbtafel würde die Sicherheitsgrenze überschreiten."
            )
        canvas = Image.new("RGB", (width, height), (18, 21, 27))
        draw = ImageDraw.Draw(canvas)
        title_font = load_font(27, bold=True)
        body_font = load_font(16)
        draw.text((24, 18), "PyImgTestPalette", font=title_font, fill=(236, 239, 244))
        if reference.strategy == "strict_majority":
            strategy = "Mehrheitspalette"
        elif reference.strategy == "pairwise_no_majority":
            strategy = "Keine stabile Mehrheit"
        else:
            strategy = "Zu wenig sichtbare Paletten"
        draw.text((24, 58), strategy, font=body_font, fill=(166, 173, 185))
        if reference.colors:
            draw_palette_strip(draw, reference.colors, (24, 92, width - 24, 140))
            draw.text(
                (24, 148),
                f"Dominanter Referenzton: {reference.colors[0].hex}",
                font=body_font,
                fill=(190, 196, 207),
            )
        for index, item in enumerate(shown_items):
            row, column = divmod(index, columns)
            left = margin + column * (cell_width + gap)
            top = header_height + row * (cell_height + gap)
            draw_profile_card(
                canvas,
                draw,
                item,
                (left, top, left + cell_width, top + cell_height),
                item.profile.direction.upper() if item.profile.direction else "BILD",
            )
        layout = "compact"
        shown = len(shown_items)

    try:
        save_png(destination, canvas)
    finally:
        canvas.close()
    return {
        "path": f"{OUTPUT_FOLDER}/{destination.name}",
        "layout": layout,
        "width": width,
        "height": height,
        "shown_images": shown,
        "omitted_images": max(0, len(scored) - shown),
    }


def rounded(value: float) -> float:
    return round(value + 0.0, 4)


def group_average_score(scored: Sequence[ScoredPalette]) -> float:
    return statistics.mean(item.metrics.score for item in scored)


def palette_metrics_data(item: ScoredPalette) -> dict[str, float]:
    return {
        "palette_match": rounded(item.metrics.palette_match),
        "distribution_match": rounded(item.metrics.distribution_match),
        "dominant_match": rounded(item.metrics.dominant_match),
        "deviation_percent": rounded(item.metrics.deviation_share * 100.0),
        "dominant_delta_e": rounded(item.metrics.dominant_delta_e),
    }


def source_color_data(profile: ImagePalette) -> dict[str, Any]:
    exceeded = profile.visible_rgb_color_count > profile.palette_color_limit
    return {
        "visible_rgb_count": profile.visible_rgb_color_count,
        "count_is_exact": profile.visible_rgb_color_count_exact,
        "limit": profile.palette_color_limit,
        "limit_exceeded": exceeded,
        "count_display": (
            str(profile.visible_rgb_color_count)
            if profile.visible_rgb_color_count_exact
            else f">{profile.palette_color_limit}"
        ),
        "fully_transparent_pixels_ignored": True,
    }


def scoring_model_data(palette_color_limit: int) -> dict[str, Any]:
    model: dict[str, Any] = {
        "id": SCORING_MODEL_ID,
        "color_space": "CIELAB_D65",
        "image_weighting": "equal_per_image",
        "palette_selection": {
            "coverage_target": PALETTE_COVERAGE_TARGET,
            "maximum_colors": palette_color_limit,
        },
        "shared_reference_minimum_images": 2,
        "direction_names_affect_scoring": False,
        "global_cluster_delta_e": GLOBAL_CLUSTER_DELTA_E,
        "deviation_delta_e": DEVIATION_DELTA_E,
        "weights": {
            "palette_match": 0.70,
            "distribution_match": 0.10,
            "dominant_match": 0.20,
        },
        "deviation_penalty": "35 * deviation_share ** 0.80",
        "meaning": (
            "Konsistenz mit der Farbmehrheit des Bildsatzes; keine "
            "künstlerische Qualitätsnote und ohne externe Referenz keine "
            "Aussage darüber, welche Farbe fachlich richtig ist."
        ),
    }
    model["fingerprint"] = scoring_model_fingerprint(model)
    return model


def input_file_set(scored: Sequence[ScoredPalette]) -> tuple[str, ...]:
    return tuple(sorted(logical_name(item.profile.path) for item in scored))


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


def make_history_result(
    search: PreviousReportSearch,
    scored: Sequence[ScoredPalette],
    current_model_fingerprint: str,
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
            reason="Kein vorheriger Palettenreport vorhanden.",
            current_average_score=current_score,
        )

    previous_path = f"{OUTPUT_FOLDER}/{previous.path.name}"
    if previous.scoring_model_fingerprint != current_model_fingerprint:
        return HistoryResult(
            status="model_changed",
            reason=(
                "Kein direkter Fortschrittsvergleich: Bewertungsmodell oder "
                "Palettenlimit wurde geändert."
            ),
            previous_report=previous_path,
            previous_average_score=rounded(previous.average_score),
            current_average_score=current_score,
        )

    current_names = input_file_set(scored)
    if previous.logical_names != current_names:
        current_set = set(current_names)
        previous_set = set(previous.logical_names)
        added = len(current_set - previous_set)
        removed = len(previous_set - current_set)
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
    delta = round(current_score - previous_score, 2)
    direction = (
        "improved" if delta > 0.0 else "declined" if delta < 0.0 else "unchanged"
    )
    item_changes: dict[str, Mapping[str, Any]] = {}
    for item in scored:
        old = previous.items.get(logical_name(item.profile.path))
        if old is None:
            continue
        old_score = float(old["score"])
        old_metrics = old.get("metrics")
        current_metrics = palette_metrics_data(item)
        metric_changes: dict[str, float] = {}
        if isinstance(old_metrics, Mapping):
            for metric, value in current_metrics.items():
                old_value = old_metrics.get(metric)
                if (
                    isinstance(old_value, (int, float))
                    and not isinstance(old_value, bool)
                    and math.isfinite(float(old_value))
                ):
                    metric_changes[metric] = rounded(value - float(old_value))
        old_hints = (
            {hint for hint in old.get("hints", []) if isinstance(hint, str)}
            if isinstance(old.get("hints"), list)
            else set()
        )
        new_hints = set(item.hints)
        item_changes[item.profile.path.name] = {
            "score_delta_percentage_points": rounded(item.metrics.score - old_score),
            "previous_score": rounded(old_score),
            "current_score": rounded(item.metrics.score),
            "metric_deltas": metric_changes,
            "previous_status": old.get("status"),
            "current_status": item.status,
            "added_hints": sorted(new_hints - old_hints),
            "removed_hints": sorted(old_hints - new_hints),
        }
    return HistoryResult(
        status="comparable",
        reason="Direkter Fortschrittsvergleich ist zulässig.",
        previous_report=previous_path,
        previous_average_score=previous_score,
        current_average_score=current_score,
        delta_percentage_points=delta,
        direction=direction,
        item_changes=item_changes,
    )


def palette_color_data(color: PaletteColor) -> dict[str, Any]:
    return {
        "hex": color.hex,
        "rgb": list(color.rgb),
        "lab": {
            "l": rounded(color.lab[0]),
            "a": rounded(color.lab[1]),
            "b": rounded(color.lab[2]),
        },
        "weight_percent": rounded(color.weight * 100.0),
    }


def global_color_data(color: GlobalPaletteColor, image_count: int) -> dict[str, Any]:
    return {
        "hex": color.hex,
        "rgb": list(color.rgb),
        "lab": {
            "l": rounded(color.lab[0]),
            "a": rounded(color.lab[1]),
            "b": rounded(color.lab[2]),
        },
        "average_share_percent": rounded(color.average_share * 100.0),
        "image_count": color.image_count,
        "image_total": image_count,
    }


def build_report_data(
    folder: Path,
    discovered_count: int,
    scored: Sequence[ScoredPalette],
    skipped: Sequence[SkippedFile],
    global_palette: Sequence[GlobalPaletteColor],
    reference: ReferencePalette,
    directions: Mapping[str, Any],
    paths: ReportPaths,
    figure: Mapping[str, Any],
    history: HistoryResult,
    scoring_model: Mapping[str, Any],
) -> dict[str, Any]:
    average = group_average_score(scored)
    statuses = Counter(item.status for item in scored)
    duplicate_count = len(scored) - len({item.profile.rgba_sha256 for item in scored})
    color_limit_warnings = sum(
        item.profile.visible_rgb_color_count > item.profile.palette_color_limit
        for item in scored
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "PyImgTestPalette",
        "tool_version": VERSION,
        "run": {
            "id": paths.run_id,
            "created_at_utc": paths.created_at_utc,
            "files": {
                "figure": f"{OUTPUT_FOLDER}/{paths.figure.name}",
                "markdown": f"{OUTPUT_FOLDER}/{paths.markdown.name}",
                "json": f"{OUTPUT_FOLDER}/{paths.json.name}",
            },
        },
        "folder": str(folder),
        "discovered_image_count": discovered_count,
        "image_count": len(scored),
        "summary": {
            "average_score": rounded(average),
            "overall_status": overall_status(scored),
            "very_good": statuses["very_good"],
            "good": statuses["good"],
            "warning": statuses["warning"],
            "critical": statuses["critical"],
            "skipped": len(skipped),
            "exact_rgba_duplicates": duplicate_count,
            "global_palette_color_count": len(global_palette),
            "source_color_limit_exceeded_images": color_limit_warnings,
        },
        "history": history_data(history),
        "scoring_model": dict(scoring_model),
        "reference": {
            "strategy": reference.strategy,
            "source_file": reference.source_file,
            "majority_threshold": reference.majority_threshold,
            "stable_coverage_percent": rounded(reference.stable_coverage * 100.0),
            "dominant_support": reference.dominant_support,
            "colors": [palette_color_data(color) for color in reference.colors],
        },
        "directions": dict(directions),
        "palette_figure": dict(figure),
        "global_palette": [
            global_color_data(color, len(scored)) for color in global_palette
        ],
        "images": [
            {
                "file": item.profile.path.name,
                "logical_name": logical_name(item.profile.path),
                "direction": item.profile.direction,
                "canvas": {
                    "width": item.profile.width,
                    "height": item.profile.height,
                },
                "rgba_sha256": item.profile.rgba_sha256,
                "visible_pixels": item.profile.visible_pixels,
                "visible_percent": rounded(item.profile.visible_fraction * 100.0),
                "palette_color_count": len(item.profile.colors),
                "source_colors": source_color_data(item.profile),
                "palette_coverage_percent": rounded(
                    item.profile.palette_coverage * 100.0
                ),
                "palette": [palette_color_data(color) for color in item.profile.colors],
                "score": rounded(item.metrics.score),
                "status": item.status,
                "metrics": palette_metrics_data(item),
                "hints": list(item.hints),
                "change_from_previous": (
                    history.item_changes.get(item.profile.path.name)
                    if history.item_changes is not None
                    else None
                ),
            }
            for item in scored
        ],
        "skipped_files": [
            {"file": item.path.name, "reason": item.reason} for item in skipped
        ],
    }


def markdown_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("`", "\\`")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_markdown_report(data: Mapping[str, Any]) -> str:
    summary = data["summary"]
    reference = data["reference"]
    directions = data["directions"]
    figure = data["palette_figure"]
    history = data["history"]
    palette_selection = data["scoring_model"]["palette_selection"]
    color_limit_warnings = summary["source_color_limit_exceeded_images"]
    color_limit_warning_noun = "Bild" if color_limit_warnings == 1 else "Bilder"
    status_label = STATUS_DATA[summary["overall_status"]][0]
    lines = [
        "# PyImgTestPalette Report",
        "",
        f"![Paletten-Farbtafel]({Path(figure['path']).name})",
        "",
        "## Zusammenfassung",
        "",
        f"- Ordner: {markdown_escape(data['folder'])}",
        f"- Erstellt (UTC): {data['run']['created_at_utc']}",
        f"- Bilder erkannt / bewertet: {data['discovered_image_count']} / {data['image_count']}",
        "- Vergleichsgruppe: alle Bilder gemeinsam; Richtungsnamen beeinflussen den Score nicht",
        f"- Zielabdeckung je Bild: {palette_selection['coverage_target'] * 100.0:.0f} % (maximal {palette_selection['maximum_colors']} Farben)",
        f"- Durchschnittliche Farbabstimmung: {summary['average_score']:.2f} %",
        f"- Gesamtstatus: {status_label}",
        f"- Sehr gut / gut / Warnung / kritisch: {summary['very_good']} / {summary['good']} / {summary['warning']} / {summary['critical']}",
        f"- Zusammengefasste Palettenfarben: {summary['global_palette_color_count']}",
        f"- Quellfarblimit überschritten: {color_limit_warnings} {color_limit_warning_noun}",
        f"- Übersprungen: {summary['skipped']}",
        "",
        "> Die Prozentzahl misst die Farbkonsistenz innerhalb dieses Bildsatzes.",
        "> Ohne Referenzbild kann sie nicht entscheiden, welcher Stil fachlich richtig ist.",
        "",
        "## Vergleich zum vorherigen Report",
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
            "## Mehrheitsreferenz",
            "",
            f"- Strategie: `{reference['strategy']}`",
            f"- Mehrheitsschwelle: {reference['majority_threshold']} Bilder",
            f"- Stabil abgedeckter Farbanteil: {reference['stable_coverage_percent']:.2f} %",
        ]
    )
    if reference["source_file"] and reference["strategy"] == "pairwise_no_majority":
        lines.append(
            f"- Repräsentative Gruppenmitte: {markdown_escape(reference['source_file'])}"
        )
    elif reference["source_file"]:
        lines.append(
            f"- Einzige sichtbare Palette: {markdown_escape(reference['source_file'])}"
        )
    if reference["colors"]:
        lines.append(f"- Dominanter Referenzton: `{reference['colors'][0]['hex']}`")
    if reference["strategy"] == "pairwise_no_majority":
        lines.append(
            "- Hinweis: Keine Palette deckt eine stabile Mehrheit ab; die Bilder "
            "wurden deshalb symmetrisch paarweise bewertet."
        )
    elif reference["strategy"] == "insufficient_visible_palettes":
        lines.append(
            "- Hinweis: Weniger als zwei Bilder besitzen sichtbare Farben; ein "
            "belastbarer Gruppenvergleich ist nicht möglich."
        )
    lines.extend(
        [
            "",
            "## Optionale Richtungsdarstellung",
            "",
            f"- Eindeutig erkannt: {directions['recognized_unique']} / 8",
            f"- Vollständiger Satz: {'ja' if directions['complete'] else 'nein'}",
            f"- Exakt ein Bild je Richtung: {'ja' if directions['exact_set'] else 'nein'}",
            "- Fehlend: "
            + (
                ", ".join(
                    DIRECTION_SHORT_LABELS[item] for item in directions["missing"]
                )
                if directions["missing"]
                else "keine"
            ),
            f"- Ohne eindeutige Richtung: {directions['unknown']}",
            "",
            "## Palettenfarben im Ordner",
            "",
            "| Nr. | Farbe | Mittlerer Anteil | Bilder |",
            "| ---: | --- | ---: | ---: |",
        ]
    )
    for index, color in enumerate(data["global_palette"], start=1):
        lines.append(
            f"| {index} | `{color['hex']}` | {color['average_share_percent']:.2f} % | "
            f"{color['image_count']} / {color['image_total']} |"
        )
    lines.extend(
        [
            "",
            "## Bewertung je Bild",
            "",
            "| Bild | Richtung | Analysetöne | Quellfarben / Limit | Score | Abweichender Anteil | Dominantes ΔE | Status |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for item in data["images"]:
        source_colors = item["source_colors"]
        source_color_text = (
            f"{source_colors['count_display']} / {source_colors['limit']}"
            + (" ⚠️" if source_colors["limit_exceeded"] else "")
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(item["file"]),
                    item["direction"] or "–",
                    str(item["palette_color_count"]),
                    source_color_text,
                    f"{item['score']:.2f} %",
                    f"{item['metrics']['deviation_percent']:.2f} %",
                    f"{item['metrics']['dominant_delta_e']:.2f}",
                    STATUS_DATA[item["status"]][0],
                ]
            )
            + " |"
        )
    lines.extend(["", "## Änderungen seit dem vorherigen Report", ""])
    if history["status"] != "comparable":
        lines.append(f"- {markdown_escape(history['reason'])}")
    else:
        lines.extend(
            [
                "| Bild | Vorher | Aktuell | Änderung | Status |",
                "| --- | ---: | ---: | ---: | --- |",
            ]
        )
        for item in data["images"]:
            change = item["change_from_previous"]
            if change is None:
                continue
            delta = change["score_delta_percentage_points"]
            delta_text = f"{delta:+.2f}" if delta else "±0.00"
            old_status = change["previous_status"]
            old_label = (
                STATUS_DATA[old_status][0]
                if old_status in STATUS_DATA
                else str(old_status or "unbekannt")
            )
            lines.append(
                f"| {markdown_escape(item['file'])} | "
                f"{change['previous_score']:.2f} % | "
                f"{change['current_score']:.2f} % | {delta_text} | "
                f"{old_label} → {STATUS_DATA[item['status']][0]} |"
            )
    lines.extend(["", "## Einzelpaletten", ""])
    for item in data["images"]:
        lines.extend(
            [
                f"### {markdown_escape(item['file'])}",
                "",
                f"- Score: {item['score']:.2f} %",
                f"- Palettenabgleich: {item['metrics']['palette_match']:.2f} %",
                f"- Mengenverteilung: {item['metrics']['distribution_match']:.2f} %",
                f"- Dominante Töne: {item['metrics']['dominant_match']:.2f} %",
                f"- Abweichender Farbanteil: {item['metrics']['deviation_percent']:.2f} %",
                f"- Palettenabdeckung: {item['palette_coverage_percent']:.2f} %",
                f"- Sichtbare RGB-Quellfarben: {item['source_colors']['count_display']} (Limit {item['source_colors']['limit']})"
                + (
                    " – ⚠️ überschritten"
                    if item["source_colors"]["limit_exceeded"]
                    else " – eingehalten"
                ),
                "- Farben: "
                + (
                    ", ".join(
                        f"`{color['hex']}` ({color['weight_percent']:.2f} %)"
                        for color in item["palette"]
                    )
                    if item["palette"]
                    else "keine sichtbare Farbe"
                ),
            ]
        )
        if item["hints"]:
            lines.append("- Hinweise:")
            lines.extend(f"  - {markdown_escape(hint)}" for hint in item["hints"])
        else:
            lines.append("- Hinweise: keine auffällige Farbabweichung.")
        lines.append("")
    lines.extend(["## Übersprungene Dateien", ""])
    if data["skipped_files"]:
        lines.extend(
            f"- {markdown_escape(item['file'])}: {markdown_escape(item['reason'])}"
            for item in data["skipped_files"]
        )
    else:
        lines.append("- Keine.")
    lines.append("")
    return "\n".join(lines)


def write_reports(paths: ReportPaths, data: Mapping[str, Any]) -> None:
    markdown = build_markdown_report(data)
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(paths.markdown, markdown)
    atomic_write_text(paths.json, json_text)


def clean_text(text: str) -> str:
    return "".join(
        "?" if unicodedata.category(char).startswith("C") else char for char in text
    )


def terminal_safe_name(name: str) -> str:
    return clean_text(name).replace("\033", "?")


def render_bar(score: float, width: int = BAR_WIDTH) -> str:
    filled = max(0, min(width, math.floor(score * width / 100.0 + 0.5)))
    return "█" * filled + "░" * (width - filled)


def analysis_tone_count_text(count: int) -> str:
    return f"{count} {'Analyseton' if count == 1 else 'Analysetöne'}"


def source_color_count_text(profile: ImagePalette) -> str:
    if profile.visible_rgb_color_count_exact:
        return str(profile.visible_rgb_color_count)
    return f">{profile.palette_color_limit}"


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    channels = []
    for channel in rgb:
        value = channel / 255.0
        channels.append(
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def color_emoji(rgb: tuple[int, int, int]) -> str:
    red, green, blue = (channel / 255.0 for channel in rgb)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    if value < 0.18:
        return "⬛"
    if saturation < 0.13:
        return "⬜" if value > 0.78 else "◻️"
    degrees = hue * 360.0
    if degrees < 18 or degrees >= 345:
        return "🟥"
    if degrees < 48:
        return "🟧"
    if degrees < 72:
        return "🟨"
    if degrees < 165:
        return "🟩"
    if degrees < 255:
        return "🟦"
    if degrees < 330:
        return "🟪"
    return "🟫"


def format_trend_line(history: HistoryResult) -> tuple[str, str]:
    assert history.previous_average_score is not None
    assert history.current_average_score is not None
    assert history.delta_percentage_points is not None
    before = history.previous_average_score
    current = history.current_average_score
    delta = history.delta_percentage_points
    if history.direction == "improved":
        return (
            (
                f"📈 Verbesserung zum vorherigen Report: +{delta:.2f} Prozentpunkte "
                f"({before:.2f} % → {current:.2f} %)"
            ),
            "32",
        )
    if history.direction == "declined":
        return (
            (
                f"📉 Rückgang zum vorherigen Report: {delta:.2f} Prozentpunkte "
                f"({before:.2f} % → {current:.2f} %)"
            ),
            "31",
        )
    return (
        (
            "➡️ Unverändert zum vorherigen Report: ±0.00 Prozentpunkte "
            f"({before:.2f} % → {current:.2f} %)"
        ),
        "36",
    )


def print_results(
    folder: Path,
    scored: Sequence[ScoredPalette],
    skipped: Sequence[SkippedFile],
    global_palette: Sequence[GlobalPaletteColor],
    reference: ReferencePalette,
    directions: Mapping[str, Any],
    theme: Theme,
    paths: ReportPaths | None,
    history: HistoryResult | None,
) -> None:
    names = [terminal_safe_name(item.profile.path.name) for item in scored]
    name_width = max(len(name) for name in names)
    print("\n🎨 PyImgTestPalette\n")
    print(f"📁 Ordner: {terminal_safe_name(folder.name)}")
    print(f"🖼️  Bilder: {len(scored)} bewertet · {len(skipped)} übersprungen")
    print(f"🔗 Vergleichsgruppe: alle {len(scored)} Bilder gemeinsam")
    print(
        f"🎛️  Palettenlimit: {scored[0].profile.palette_color_limit} Farben · "
        f"Zielabdeckung mindestens {PALETTE_COVERAGE_TARGET * 100.0:.0f} %"
    )
    present = directions["recognized_unique"]
    if present:
        direction_color = "32" if directions["complete"] else "33"
        print(
            theme.paint(
                f"🧭 Optionales Layout: {present}/8 Richtungen erkannt"
                + (" · vollständig" if directions["complete"] else ""),
                direction_color,
            )
        )
    if reference.colors:
        dominant = reference.colors[0]
        if reference.strategy == "strict_majority":
            reference_text = (
                f"🎯 Mehrheits-Ton: {color_emoji(dominant.rgb)} "
                f"{theme.swatch(dominant.rgb)} {dominant.hex} · "
                f"in {reference.dominant_support}/{len(scored)} Bildern"
            )
        elif reference.strategy == "pairwise_no_majority":
            reference_text = (
                f"🎯 Gruppenmitte: {color_emoji(dominant.rgb)} "
                f"{theme.swatch(dominant.rgb)} {dominant.hex} · keine stabile Mehrheit"
            )
        else:
            reference_text = (
                f"🎯 Einzelpalette: {color_emoji(dominant.rgb)} "
                f"{theme.swatch(dominant.rgb)} {dominant.hex} · kein Gruppenvergleich"
            )
        print(reference_text)
    print()

    for item, name in zip(scored, names):
        _label, emoji, color = STATUS_DATA[item.status]
        bar = theme.paint(f"[{render_bar(item.metrics.score)}]", color)
        palette_count = len(item.profile.colors)
        print(
            f"{name:<{name_width}}  {bar} {item.metrics.score:6.2f}% "
            f"{emoji}  🎨 {palette_count}"
        )

    print("\n🎨 Palettenfarben im Ordner")
    palette_noun = (
        "zusammengefasster Farbton"
        if len(global_palette) == 1
        else "zusammengefasste Farbtöne"
    )
    print(f"   {len(global_palette)} {palette_noun} aus {len(scored)} Bildern")
    maximum_share = max((color.average_share for color in global_palette), default=1.0)
    for index, color in enumerate(global_palette, start=1):
        relative = 100.0 * color.average_share / maximum_share if maximum_share else 0.0
        bar = theme.paint(
            render_bar(relative, PALETTE_BAR_WIDTH),
            f"38;2;{color.rgb[0]};{color.rgb[1]};{color.rgb[2]}",
        )
        print(
            f"   {index:>2}. {color_emoji(color.rgb)} {theme.swatch(color.rgb)} "
            f"{color.hex} [{bar}] {color.average_share * 100.0:6.2f}% · "
            f"{color.image_count}/{len(scored)} Bilder"
        )

    print("\n📦 Analyse- und Quellfarben je Bild")
    for item, name in zip(scored, names):
        profile = item.profile
        limit_exceeded = profile.visible_rgb_color_count > profile.palette_color_limit
        source_text = (
            f"⚠️ {source_color_count_text(profile)} RGB-Quellfarben"
            if limit_exceeded
            else f"✅ {source_color_count_text(profile)} RGB-Quellfarben"
        )
        source_color = "33" if limit_exceeded else "32"
        print(
            f"   {name:<{name_width}}  "
            f"🎨 {analysis_tone_count_text(len(profile.colors)):<13} · "
            f"{theme.paint(source_text, source_color)} · "
            f"{profile.palette_coverage * 100.0:6.2f}% Abdeckung"
        )

    average = statistics.mean(item.metrics.score for item in scored)
    group_status = overall_status(scored)
    label, emoji, color = STATUS_DATA[group_status]
    if group_status == "very_good":
        emoji, color = "💎", "96"
    counts = Counter(item.status for item in scored)
    print()
    print(theme.paint(f"{emoji} Gesamt: {label} ({average:.2f} %)", color))
    if history is not None:
        if history.status == "comparable":
            trend_text, trend_color = format_trend_line(history)
            print(theme.paint(trend_text, trend_color))
        elif history.status != "first_run":
            print(theme.paint(f"ℹ️ {history.reason}", "33"))
    print(
        f"✅ {counts['very_good']} sehr gut · 🟢 {counts['good']} gut · "
        f"⚠️ {counts['warning']} auffällig · ❌ {counts['critical']} kritisch"
    )
    color_limit_warnings = sum(
        item.profile.visible_rgb_color_count > item.profile.palette_color_limit
        for item in scored
    )
    if color_limit_warnings:
        group_noun = "Bild" if len(scored) == 1 else "Bildern"
        warning_verb = "enthält" if color_limit_warnings == 1 else "enthalten"
        print(
            theme.paint(
                f"⚠️ Farblimit überschritten: {color_limit_warnings} von "
                f"{len(scored)} {group_noun} {warning_verb} mehr als "
                f"{scored[0].profile.palette_color_limit} sichtbare RGB-Quellfarben "
                "(score-neutral).",
                "33",
            )
        )
    color_limit_warnings = sum(
        item.profile.visible_rgb_color_count > item.profile.palette_color_limit
        for item in scored
    )
    if color_limit_warnings:
        limit = scored[0].profile.palette_color_limit
        print(
            theme.paint(
                f"⚠️ Quellfarblimit überschritten: {color_limit_warnings}/"
                f"{len(scored)} Bilder enthalten mehr als {limit} sichtbare "
                "RGB-Farben (score-neutrale Warnung).",
                "33",
            )
        )
    if reference.strategy == "pairwise_no_majority":
        print(
            theme.paint("⚠️ Keine stabile Mehrheitspalette; paarweise Bewertung.", "33")
        )
    elif reference.strategy == "insufficient_visible_palettes":
        print(
            theme.paint(
                "⚠️ Zu wenig sichtbare Paletten für einen belastbaren Gruppenvergleich.",
                "33",
            )
        )
    if present and directions["missing"]:
        missing = ", ".join(
            DIRECTION_SHORT_LABELS[item] for item in directions["missing"]
        )
        print(theme.paint(f"⚠️ Fehlende Richtungen: {missing}", "33"))
    if directions["duplicates"]:
        duplicates = ", ".join(
            f"{DIRECTION_SHORT_LABELS[key]} ({value})"
            for key, value in directions["duplicates"].items()
        )
        print(theme.paint(f"⚠️ Mehrfach belegte Richtungen: {duplicates}", "33"))
    if present and directions["unknown"]:
        print(theme.paint(f"⚠️ Ohne eindeutige Richtung: {directions['unknown']}", "33"))
    if skipped:
        print(theme.paint(f"⚠️ Übersprungene Dateien: {len(skipped)}", "33"))
    if paths is not None:
        print(f"\n📄 Report: {OUTPUT_FOLDER}/{paths.markdown.name}")
        print(f"🧾 JSON:   {OUTPUT_FOLDER}/{paths.json.name}")
        print(f"🧭 Figur:  {OUTPUT_FOLDER}/{paths.figure.name}")


def run(
    no_color: bool = False,
    no_report: bool = False,
    palette_colors: int = DEFAULT_PALETTE_COLOR_LIMIT,
) -> int:
    if palette_colors not in PALETTE_COLOR_CHOICES:
        allowed = ", ".join(str(value) for value in PALETTE_COLOR_CHOICES)
        raise ValueError(f"Ungültiges Palettenlimit. Erlaubt sind: {allowed}.")
    folder = Path.cwd()
    sources = find_images(folder)
    if len(sources) < 2:
        print(
            "FEHLER: Mindestens zwei unterstützte Bilder direkt im aktuellen "
            "Ordner sind erforderlich.",
            file=sys.stderr,
        )
        return 1

    profiles: list[ImagePalette] = []
    skipped: list[SkippedFile] = []
    for source in sources:
        try:
            profiles.append(analyze_image(source, palette_colors))
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
            skipped.append(SkippedFile(source, f"{type(exc).__name__}: {exc}"))

    if len(profiles) < 2:
        print(
            f"FEHLER: Nur {len(profiles)} von {len(sources)} Bilddateien konnten "
            "gelesen werden; mindestens zwei sind erforderlich.",
            file=sys.stderr,
        )
        for item in skipped:
            print(
                f"  - {terminal_safe_name(item.path.name)}: {item.reason}",
                file=sys.stderr,
            )
        return 1

    global_palette = build_global_palette(profiles)
    reference = build_reference_palette(profiles, global_palette)
    scored = score_profiles(profiles, reference)
    directions = direction_summary(profiles)
    paths: ReportPaths | None = None
    history: HistoryResult | None = None
    if not no_report:
        output = ensure_output_folder(folder)
        scoring_model = scoring_model_data(palette_colors)
        history = make_history_result(
            find_previous_report(output, folder),
            scored,
            str(scoring_model["fingerprint"]),
        )
        paths = allocate_report_paths(output)
        figure = create_palette_figure(scored, reference, paths.figure)
        data = build_report_data(
            folder,
            len(sources),
            scored,
            skipped,
            global_palette,
            reference,
            directions,
            paths,
            figure,
            history,
            scoring_model,
        )
        write_reports(paths, data)

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
        global_palette,
        reference,
        directions,
        Theme(color_enabled),
        paths,
        history,
    )
    return 1 if skipped else 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        options = parse_arguments(argv)
        load_pillow()
        return run(
            no_color=options.no_color,
            no_report=options.no_report,
            palette_colors=options.palette_colors,
        )
    except KeyboardInterrupt:
        print("\nAbgebrochen. Quelldateien bleiben unverändert.", file=sys.stderr)
        return 130
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
