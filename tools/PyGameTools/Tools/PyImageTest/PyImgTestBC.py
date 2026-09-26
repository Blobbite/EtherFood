#!/usr/bin/env python3
"""Helligkeit und Kontrast mehrerer Bilder als gemeinsame Gruppe prüfen.

Das Werkzeug liest unterstützte, statische Rasterbilder direkt aus dem
aktuellen Terminalordner (ohne Unterordner). Sichtbare Pixel werden
alpha-gewichtet in CIE-L*-Helligkeit umgerechnet. Jedes Bild wird gegen die
robusten Gruppenmediane für Helligkeit und Kontrast bewertet.

Dateinamen und vermeintliche Blickrichtungen beeinflussen die Bewertung nicht.
Eine positive L*-Abweichung bedeutet ``heller``, eine negative ``dunkler``.
Als robuster Kontrast dient vor allem die Spanne zwischen dem 10. und 90.
Helligkeitsperzentil; die Standardabweichung ergänzt diesen Messwert.

Standardmäßig entstehen pro Lauf in ``.compare``:

* ``brightness_contrast_figure_<UTC-ID>.png``
* ``brightness_contrast_report_<UTC-ID>.md``
* ``brightness_contrast_report_<UTC-ID>.json``

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
import errno
import hashlib
import json
import math
import os
import statistics
import sys
import tempfile
import unicodedata
import warnings
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path
from typing import Any

VERSION = "1.1.0"
SCHEMA_VERSION = 2
SCORING_MODEL_ID = "brightness-contrast-consistency-v1"
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

ANALYSIS_EDGE = 256
BAR_WIDTH = 20
MAX_FIGURE_ITEMS = 60
MAX_FIGURE_PIXELS = 64_000_000

BRIGHTNESS_WEIGHT = 0.60
CONTRAST_WEIGHT = 0.40
BRIGHTNESS_CURVE = (
    (0.0, 100.0),
    (1.0, 98.0),
    (2.0, 93.0),
    (3.0, 86.0),
    (5.0, 70.0),
    (8.0, 45.0),
    (12.0, 15.0),
    (16.0, 0.0),
)
CONTRAST_CURVE = (
    (0.0, 100.0),
    (5.0, 97.0),
    (10.0, 90.0),
    (15.0, 80.0),
    (25.0, 60.0),
    (40.0, 30.0),
    (60.0, 0.0),
)

STATUS_DATA = {
    "very_good": ("Sehr gut abgestimmt", "✅", "32"),
    "good": ("Gut abgestimmt", "🟢", "32"),
    "warning": ("Helligkeit/Kontrast auffällig", "⚠️", "33"),
    "critical": ("Starke Helligkeits-/Kontrastabweichung", "❌", "31"),
}
STATUS_RANK = {"very_good": 0, "good": 1, "warning": 2, "critical": 3}


class SkipImage(Exception):
    """Eine Bilddatei kann bewusst nicht sicher ausgewertet werden."""


@dataclass(frozen=True)
class LightFeatures:
    path: Path
    width: int
    height: int
    visible_pixels: int
    visible_fraction: float
    rgba_sha256: str
    sample_weight: float
    mean_l: float | None
    robust_mean_l: float | None
    median_l: float | None
    percentile_10_l: float | None
    percentile_90_l: float | None
    contrast_span_l: float | None
    contrast_stddev_l: float | None


@dataclass(frozen=True)
class ReferenceStats:
    valid_images: int
    robust_mean_l: float
    median_l: float
    contrast_span_l: float
    contrast_stddev_l: float
    confidence: str


@dataclass(frozen=True)
class LightMetrics:
    total_score: float
    brightness_score: float
    contrast_score: float
    brightness_shift_l: float
    brightness_delta_l: float
    contrast_shift_percent: float
    contrast_delta_percent: float


@dataclass(frozen=True)
class ScoredLight:
    features: LightFeatures
    metrics: LightMetrics
    score_status: str
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
    RESET = "\033[0m"

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def paint(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}{self.RESET}"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="PyImgTestBrightnessContrast",
        description=(
            "Prüft Helligkeit und Kontrast aller unterstützten Bilder direkt "
            "im aktuellen Terminalordner als gemeinsame Gruppe."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Messung:
  Helligkeit wird als alpha-gewichtetes CIE L* gemessen. Der robuste Kontrast
  kombiniert die L*-Spanne vom 10. bis 90. Perzentil mit der gewichteten
  Standardabweichung. Referenz ist jeweils der Median aller lesbaren Bilder.

  Dateinamen, Richtungsangaben und Dateireihenfolge beeinflussen keinen Wert.
  Im Terminal steht pro Bild ausdrücklich, ob es heller/dunkler und
  kontrastreicher/kontrastärmer als die Gruppe ist.

Ausgabe pro Lauf:
  .compare/brightness_contrast_figure_<UTC-ID>.png
  .compare/brightness_contrast_report_<UTC-ID>.md
  .compare/brightness_contrast_report_<UTC-ID>.json

Bei gleichem Bildsatz und Bewertungsmodell zeigt jeder Reportlauf die
Verbesserung oder den Rückgang gegenüber dem letzten gültigen Report.

Mindestens zwei lesbare, statische Bilder sind erforderlich. Quelldateien
werden nie verändert. Mit --no-report bleibt ausschließlich die farbige
Terminalausgabe; .compare wird dann nicht gelesen, angelegt oder verändert.
""",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="ANSI-Farben im Terminal abschalten.",
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


def rgba_content_hash(image: Any) -> str:
    digest = hashlib.sha256()
    digest.update(b"PyImgTestBrightnessContrast-RGBA-v1\0")
    digest.update(image.width.to_bytes(8, "big"))
    digest.update(image.height.to_bytes(8, "big"))
    digest.update(image.tobytes())
    return digest.hexdigest()


def rgb_to_lightness(red: int, green: int, blue: int) -> float:
    def linear(channel: int) -> float:
        value = channel / 255.0
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    luminance = (
        0.2126729 * linear(red) + 0.7151522 * linear(green) + 0.0721750 * linear(blue)
    )
    delta = 6.0 / 29.0
    pivot = (
        luminance ** (1.0 / 3.0)
        if luminance > delta**3
        else luminance / (3.0 * delta**2) + 4.0 / 29.0
    )
    return 116.0 * pivot - 16.0


def weighted_quantile(values: Sequence[tuple[float, float]], quantile: float) -> float:
    if not values:
        raise ValueError("Gewichtetes Quantil benötigt mindestens einen Wert.")
    total = sum(weight for _value, weight in values)
    target = max(0.0, min(1.0, quantile)) * total
    accumulated = 0.0
    for value, weight in values:
        accumulated += weight
        if accumulated >= target:
            return value
    return values[-1][0]


def analyze_image(path: Path) -> LightFeatures:
    image = open_static_rgba(path)
    sample = alpha = None
    try:
        alpha = image.getchannel("A")
        alpha_histogram = alpha.histogram()
        total_pixels = image.width * image.height
        visible_pixels = total_pixels - alpha_histogram[0]
        visible_fraction = visible_pixels / total_pixels if total_pixels else 0.0
        content_hash = rgba_content_hash(image)
        sample = resized_for_analysis(image, ANALYSIS_EDGE)

        values = sorted(
            (
                (rgb_to_lightness(red, green, blue), alpha_value / 255.0)
                for red, green, blue, alpha_value in flattened_pixels(sample)
                if alpha_value > 0
            ),
            key=lambda item: item[0],
        )
        total_weight = sum(weight for _value, weight in values)
        if total_weight <= 0.0:
            return LightFeatures(
                path,
                image.width,
                image.height,
                visible_pixels,
                visible_fraction,
                content_hash,
                0.0,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )

        mean_l = sum(value * weight for value, weight in values) / total_weight
        p05 = weighted_quantile(values, 0.05)
        p10 = weighted_quantile(values, 0.10)
        median_l = weighted_quantile(values, 0.50)
        p90 = weighted_quantile(values, 0.90)
        p95 = weighted_quantile(values, 0.95)
        trimmed = [item for item in values if p05 <= item[0] <= p95]
        trimmed_weight = sum(weight for _value, weight in trimmed)
        robust_mean_l = (
            sum(value * weight for value, weight in trimmed) / trimmed_weight
            if trimmed_weight > 0.0
            else mean_l
        )
        variance = (
            sum(weight * (value - mean_l) ** 2 for value, weight in values)
            / total_weight
        )
        return LightFeatures(
            path=path,
            width=image.width,
            height=image.height,
            visible_pixels=visible_pixels,
            visible_fraction=visible_fraction,
            rgba_sha256=content_hash,
            sample_weight=total_weight,
            mean_l=mean_l,
            robust_mean_l=robust_mean_l,
            median_l=median_l,
            percentile_10_l=p10,
            percentile_90_l=p90,
            contrast_span_l=max(0.0, p90 - p10),
            contrast_stddev_l=math.sqrt(max(0.0, variance)),
        )
    finally:
        if alpha is not None:
            alpha.close()
        if sample is not None:
            sample.close()
        image.close()


def build_reference(features: Sequence[LightFeatures]) -> ReferenceStats:
    valid = [item for item in features if item.robust_mean_l is not None]
    count = len(valid)
    if count == 0:
        return ReferenceStats(0, 0.0, 0.0, 0.0, 0.0, "none")
    confidence = "high" if count >= 5 else "medium" if count >= 3 else "low"
    return ReferenceStats(
        valid_images=count,
        robust_mean_l=statistics.median(
            item.robust_mean_l for item in valid if item.robust_mean_l is not None
        ),
        median_l=statistics.median(
            item.median_l for item in valid if item.median_l is not None
        ),
        contrast_span_l=statistics.median(
            item.contrast_span_l for item in valid if item.contrast_span_l is not None
        ),
        contrast_stddev_l=statistics.median(
            item.contrast_stddev_l
            for item in valid
            if item.contrast_stddev_l is not None
        ),
        confidence=confidence,
    )


def curve_score(value: float, curve: Sequence[tuple[float, float]]) -> float:
    value = max(0.0, value)
    if value <= curve[0][0]:
        return curve[0][1]
    for (left_x, left_y), (right_x, right_y) in pairwise(curve):
        if value <= right_x:
            share = (value - left_x) / (right_x - left_x)
            return left_y + share * (right_y - left_y)
    return curve[-1][1]


def status_for(score: float) -> str:
    if score >= 90.0:
        return "very_good"
    if score >= 75.0:
        return "good"
    if score >= 50.0:
        return "warning"
    return "critical"


def compare_feature(feature: LightFeatures, reference: ReferenceStats) -> LightMetrics:
    if feature.robust_mean_l is None or feature.median_l is None:
        return LightMetrics(0.0, 0.0, 0.0, 0.0, 100.0, 0.0, 100.0)
    assert feature.contrast_span_l is not None
    assert feature.contrast_stddev_l is not None

    # Helligkeit und Kontrast bewusst trennen: Für den Helligkeits-Score zählt
    # nur das an P05/P95 getrimmte L*-Mittel. Der Median bleibt im Report ein
    # Diagnosewert, kann bei diskreten Pixelpaletten aber sprunghaft wechseln.
    brightness_shift = feature.robust_mean_l - reference.robust_mean_l
    brightness_delta = abs(brightness_shift)
    brightness_score = curve_score(brightness_delta, BRIGHTNESS_CURVE)

    span_denominator = max(5.0, reference.contrast_span_l)
    stddev_denominator = max(3.0, reference.contrast_stddev_l)
    span_shift = (
        (feature.contrast_span_l - reference.contrast_span_l) / span_denominator * 100.0
    )
    stddev_shift = (
        (feature.contrast_stddev_l - reference.contrast_stddev_l)
        / stddev_denominator
        * 100.0
    )
    contrast_shift = 0.70 * span_shift + 0.30 * stddev_shift
    contrast_delta = 0.70 * abs(span_shift) + 0.30 * abs(stddev_shift)
    contrast_score = curve_score(contrast_delta, CONTRAST_CURVE)
    total = BRIGHTNESS_WEIGHT * brightness_score + CONTRAST_WEIGHT * contrast_score
    return LightMetrics(
        total_score=max(0.0, min(100.0, total)),
        brightness_score=brightness_score,
        contrast_score=contrast_score,
        brightness_shift_l=brightness_shift,
        brightness_delta_l=brightness_delta,
        contrast_shift_percent=contrast_shift,
        contrast_delta_percent=contrast_delta,
    )


def findings_for(feature: LightFeatures, metrics: LightMetrics) -> tuple[str, ...]:
    if feature.robust_mean_l is None:
        return ("Keine sichtbaren Pixel; Helligkeit und Kontrast nicht messbar.",)
    findings: list[str] = []
    brightness = metrics.brightness_shift_l
    if abs(brightness) >= 6.0:
        findings.append(
            f"Stark {'heller' if brightness > 0 else 'dunkler'} als die Gruppe "
            f"({brightness:+.2f} L*)."
        )
    elif abs(brightness) >= 3.0:
        findings.append(
            f"Sichtbar {'heller' if brightness > 0 else 'dunkler'} als die Gruppe "
            f"({brightness:+.2f} L*)."
        )
    elif abs(brightness) >= 1.0:
        findings.append(
            f"Leicht {'heller' if brightness > 0 else 'dunkler'} als die Gruppe "
            f"({brightness:+.2f} L*)."
        )

    contrast = metrics.contrast_shift_percent
    if abs(contrast) >= 30.0:
        findings.append(
            f"Kontrast stark {'höher' if contrast > 0 else 'niedriger'} als der "
            f"Gruppenmedian ({contrast:+.2f} %)."
        )
    elif abs(contrast) >= 15.0:
        findings.append(
            f"Kontrast sichtbar {'höher' if contrast > 0 else 'niedriger'} als der "
            f"Gruppenmedian ({contrast:+.2f} %)."
        )
    elif abs(contrast) >= 5.0:
        findings.append(
            f"Kontrast leicht {'höher' if contrast > 0 else 'niedriger'} als der "
            f"Gruppenmedian ({contrast:+.2f} %)."
        )
    return tuple(findings)


def status_with_findings(metrics: LightMetrics, score_status: str) -> str:
    result = score_status
    if metrics.brightness_delta_l >= 6.0 or metrics.contrast_delta_percent >= 30.0:
        result = max((result, "critical"), key=STATUS_RANK.__getitem__)
    elif metrics.brightness_delta_l >= 3.0 or metrics.contrast_delta_percent >= 15.0:
        result = max((result, "warning"), key=STATUS_RANK.__getitem__)
    return result


def score_group(
    features: Sequence[LightFeatures], reference: ReferenceStats
) -> list[ScoredLight]:
    result: list[ScoredLight] = []
    for feature in features:
        metrics = compare_feature(feature, reference)
        score_status = status_for(metrics.total_score)
        status = (
            "critical"
            if feature.robust_mean_l is None
            else status_with_findings(metrics, score_status)
        )
        result.append(
            ScoredLight(
                features=feature,
                metrics=metrics,
                score_status=score_status,
                status=status,
                hints=findings_for(feature, metrics),
            )
        )
    return result


def overall_status(scored: Sequence[ScoredLight]) -> str:
    return max((item.status for item in scored), key=STATUS_RANK.__getitem__)


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
            figure=output / f"brightness_contrast_figure_{run_id}.png",
            markdown=output / f"brightness_contrast_report_{run_id}.md",
            json=output / f"brightness_contrast_report_{run_id}.json",
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
        or data.get("tool") != "PyImgTestBrightnessContrast"
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
            path.name.startswith("brightness_contrast_report_")
            and path.suffix.lower() == ".json"
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
        prefix=".pyimglight_", suffix=suffix, dir=destination.parent
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


def draw_contrast_scale(
    draw: Any,
    feature: LightFeatures,
    bounds: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = bounds
    width = right - left
    for offset in range(width):
        level = round(255 * offset / max(1, width - 1))
        draw.line(
            (left + offset, top, left + offset, bottom), fill=(level, level, level)
        )
    if feature.percentile_10_l is not None and feature.percentile_90_l is not None:
        low = left + round(width * feature.percentile_10_l / 100.0)
        high = left + round(width * feature.percentile_90_l / 100.0)
        draw.rectangle(
            (low, top - 2, high, bottom + 2), outline=(75, 205, 220), width=3
        )
    draw.rectangle(bounds, outline=(215, 218, 224), width=1)


def draw_card(
    canvas: Any,
    draw: Any,
    item: ScoredLight,
    bounds: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = bounds
    status_color = {
        "very_good": (42, 171, 92),
        "good": (54, 181, 105),
        "warning": (222, 165, 45),
        "critical": (218, 75, 75),
    }[item.status]
    draw.rounded_rectangle(
        bounds,
        radius=14,
        fill=(35, 39, 47),
        outline=status_color,
        width=4,
    )
    title_font = load_font(16, bold=True)
    score_font = load_font(17, bold=True)
    body_font = load_font(14)
    filename = truncate_for_drawing(
        draw, item.features.path.name, title_font, right - left - 100
    )
    draw.text((left + 13, top + 11), filename, font=title_font, fill=(238, 241, 246))
    score_text = f"{item.metrics.total_score:.1f} %"
    score_width = draw.textlength(score_text, font=score_font)
    draw.text(
        (right - 13 - score_width, top + 10),
        score_text,
        font=score_font,
        fill=status_color,
    )

    preview_box = (left + 13, top + 43, right - 13, top + 177)
    preview_size = (preview_box[2] - preview_box[0], preview_box[3] - preview_box[1])
    board = checkerboard(preview_size)
    source = open_static_rgba(item.features.path)
    try:
        source.thumbnail(
            (max(1, preview_size[0] - 10), max(1, preview_size[1] - 10)),
            Image.Resampling.NEAREST,
        )
        board.alpha_composite(
            source,
            (
                (preview_size[0] - source.width) // 2,
                (preview_size[1] - source.height) // 2,
            ),
        )
        rendered = board.convert("RGB")
        try:
            canvas.paste(rendered, (preview_box[0], preview_box[1]))
        finally:
            rendered.close()
    finally:
        source.close()
        board.close()

    if item.features.robust_mean_l is None:
        draw.text(
            (left + 13, top + 190),
            "Keine sichtbaren Pixel",
            font=body_font,
            fill=(224, 100, 100),
        )
        return
    brightness = item.metrics.brightness_shift_l
    contrast = item.metrics.contrast_shift_percent
    draw.text(
        (left + 13, top + 186),
        f"L*: {item.features.robust_mean_l:.2f} ({brightness:+.2f})",
        font=body_font,
        fill=(203, 208, 217),
    )
    draw.text(
        (left + 13, top + 207),
        f"Kontrast: {item.features.contrast_span_l:.2f} ({contrast:+.1f} %)",
        font=body_font,
        fill=(203, 208, 217),
    )
    draw_contrast_scale(
        draw,
        item.features,
        (left + 13, bottom - 35, right - 13, bottom - 17),
    )


def create_figure(
    scored: Sequence[ScoredLight],
    reference: ReferenceStats,
    destination: Path,
) -> dict[str, Any]:
    shown_items = list(scored[:MAX_FIGURE_ITEMS])
    columns = min(3, len(shown_items))
    rows = math.ceil(len(shown_items) / columns)
    width = 960
    header_height = 145
    margin = 18
    gap = 12
    cell_width = (width - 2 * margin - (columns - 1) * gap) // columns
    cell_height = 275
    height = (
        header_height + margin + rows * cell_height + max(0, rows - 1) * gap + margin
    )
    if width * height > MAX_FIGURE_PIXELS:
        raise RuntimeError(
            "Die Helligkeits-Farbtafel würde die Sicherheitsgrenze überschreiten."
        )
    canvas = Image.new("RGB", (width, height), (18, 21, 27))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(28, bold=True)
    body_font = load_font(17)
    draw.text(
        (24, 18),
        "PyImgTestBrightnessContrast",
        font=title_font,
        fill=(238, 241, 246),
    )
    draw.text(
        (24, 61),
        f"Gruppenmedian: L* {reference.robust_mean_l:.2f} · "
        f"Kontrastspanne {reference.contrast_span_l:.2f}",
        font=body_font,
        fill=(176, 183, 195),
    )
    draw.text(
        (24, 91),
        "Alle Bilder gemeinsam · Dateinamen beeinflussen die Bewertung nicht",
        font=body_font,
        fill=(125, 201, 214),
    )
    for index, item in enumerate(shown_items):
        row, column = divmod(index, columns)
        left = margin + column * (cell_width + gap)
        top = header_height + row * (cell_height + gap)
        draw_card(
            canvas,
            draw,
            item,
            (left, top, left + cell_width, top + cell_height),
        )
    try:
        save_png(destination, canvas)
    finally:
        canvas.close()
    return {
        "path": f"{OUTPUT_FOLDER}/{destination.name}",
        "layout": "compact_all_images",
        "width": width,
        "height": height,
        "shown_images": len(shown_items),
        "omitted_images": max(0, len(scored) - len(shown_items)),
    }


def rounded(value: float) -> float:
    return round(value + 0.0, 4)


def optional_rounded(value: float | None) -> float | None:
    return None if value is None else rounded(value)


def group_average_score(scored: Sequence[ScoredLight]) -> float:
    return statistics.mean(item.metrics.total_score for item in scored)


def light_metrics_data(item: ScoredLight) -> dict[str, float]:
    return {
        "brightness_score": rounded(item.metrics.brightness_score),
        "contrast_score": rounded(item.metrics.contrast_score),
        "brightness_shift_l": rounded(item.metrics.brightness_shift_l),
        "brightness_delta_l": rounded(item.metrics.brightness_delta_l),
        "contrast_shift_percent": rounded(item.metrics.contrast_shift_percent),
        "contrast_delta_percent": rounded(item.metrics.contrast_delta_percent),
    }


def scoring_model_data() -> dict[str, Any]:
    model: dict[str, Any] = {
        "id": SCORING_MODEL_ID,
        "color_space": "CIE_Lstar_D65",
        "group_reference": "median_equal_weight_per_image",
        "direction_or_filename_grouping": False,
        "weights": {
            "brightness": BRIGHTNESS_WEIGHT,
            "contrast": CONTRAST_WEIGHT,
        },
        "brightness_method": "alpha_weighted_P05_P95_trimmed_mean_Lstar",
        "brightness_curve": [list(point) for point in BRIGHTNESS_CURVE],
        "contrast_curve": [list(point) for point in CONTRAST_CURVE],
        "contrast_method": "70_percent_P90_minus_P10_and_30_percent_stddev",
        "meaning": (
            "Konsistenz von Helligkeit und Kontrast innerhalb der Gruppe; "
            "keine künstlerische Qualitätsnote."
        ),
    }
    model["fingerprint"] = scoring_model_fingerprint(model)
    return model


def input_file_set(scored: Sequence[ScoredLight]) -> tuple[str, ...]:
    return tuple(sorted(logical_name(item.features.path) for item in scored))


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
    scored: Sequence[ScoredLight],
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
            reason="Kein vorheriger Helligkeits-/Kontrastreport vorhanden.",
            current_average_score=current_score,
        )

    previous_path = f"{OUTPUT_FOLDER}/{previous.path.name}"
    if previous.scoring_model_fingerprint != current_model_fingerprint:
        return HistoryResult(
            status="model_changed",
            reason="Kein direkter Fortschrittsvergleich: Bewertungsmodell wurde geändert.",
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
        old = previous.items.get(logical_name(item.features.path))
        if old is None:
            continue
        old_score = float(old["score"])
        old_metrics = old.get("metrics")
        current_metrics = light_metrics_data(item)
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
        item_changes[item.features.path.name] = {
            "score_delta_percentage_points": rounded(
                item.metrics.total_score - old_score
            ),
            "previous_score": rounded(old_score),
            "current_score": rounded(item.metrics.total_score),
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


def build_report_data(
    folder: Path,
    discovered_count: int,
    scored: Sequence[ScoredLight],
    skipped: Sequence[SkippedFile],
    reference: ReferenceStats,
    paths: ReportPaths,
    figure: Mapping[str, Any],
    history: HistoryResult,
    scoring_model: Mapping[str, Any],
) -> dict[str, Any]:
    average = group_average_score(scored)
    statuses = Counter(item.status for item in scored)
    duplicate_count = len(scored) - len({item.features.rgba_sha256 for item in scored})
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "PyImgTestBrightnessContrast",
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
        },
        "history": history_data(history),
        "reference": {
            "valid_images": reference.valid_images,
            "confidence": reference.confidence,
            "robust_mean_l": rounded(reference.robust_mean_l),
            "median_l": rounded(reference.median_l),
            "contrast_span_l": rounded(reference.contrast_span_l),
            "contrast_stddev_l": rounded(reference.contrast_stddev_l),
        },
        "scoring_model": dict(scoring_model),
        "figure": dict(figure),
        "images": [
            {
                "file": item.features.path.name,
                "logical_name": logical_name(item.features.path),
                "canvas": {
                    "width": item.features.width,
                    "height": item.features.height,
                },
                "rgba_sha256": item.features.rgba_sha256,
                "visible_pixels": item.features.visible_pixels,
                "visible_percent": rounded(item.features.visible_fraction * 100.0),
                "measurements": {
                    "mean_l": optional_rounded(item.features.mean_l),
                    "robust_mean_l": optional_rounded(item.features.robust_mean_l),
                    "median_l": optional_rounded(item.features.median_l),
                    "percentile_10_l": optional_rounded(item.features.percentile_10_l),
                    "percentile_90_l": optional_rounded(item.features.percentile_90_l),
                    "contrast_span_l": optional_rounded(item.features.contrast_span_l),
                    "contrast_stddev_l": optional_rounded(
                        item.features.contrast_stddev_l
                    ),
                },
                "score": rounded(item.metrics.total_score),
                "score_status": item.score_status,
                "status": item.status,
                "metrics": light_metrics_data(item),
                "hints": list(item.hints),
                "change_from_previous": (
                    history.item_changes.get(item.features.path.name)
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
    figure = data["figure"]
    history = data["history"]
    lines = [
        "# PyImgTestBrightnessContrast Report",
        "",
        f"![Helligkeits- und Kontrasttafel]({Path(figure['path']).name})",
        "",
        "## Zusammenfassung",
        "",
        f"- Ordner: {markdown_escape(data['folder'])}",
        f"- Erstellt (UTC): {data['run']['created_at_utc']}",
        f"- Bilder erkannt / bewertet: {data['discovered_image_count']} / {data['image_count']}",
        "- Vergleichsgruppe: alle Bilder gemeinsam; Dateinamen beeinflussen keinen Wert",
        f"- Durchschnitt: {summary['average_score']:.2f} %",
        f"- Gesamtstatus: {STATUS_DATA[summary['overall_status']][0]}",
        f"- Sehr gut / gut / Warnung / kritisch: {summary['very_good']} / {summary['good']} / {summary['warning']} / {summary['critical']}",
        f"- Übersprungen: {summary['skipped']}",
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
            "## Gruppenreferenz",
            "",
            f"- Robuste mittlere Helligkeit: L* {reference['robust_mean_l']:.2f}",
            f"- Median-Helligkeit: L* {reference['median_l']:.2f}",
            f"- Robuste Kontrastspanne P90−P10: {reference['contrast_span_l']:.2f} L*",
            f"- Helligkeits-Standardabweichung: {reference['contrast_stddev_l']:.2f} L*",
            f"- Vertrauen: {reference['confidence']}",
            "",
            "> Positive Helligkeitswerte bedeuten heller, negative dunkler.",
            "> Positive Kontrastwerte bedeuten kontrastreicher, negative kontrastärmer.",
            "",
            "## Bewertung je Bild",
            "",
            "| Bild | Score | Helligkeit | ΔL* | Kontrastspanne | Kontrast-Δ | Status |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for item in data["images"]:
        measurements = item["measurements"]
        metrics = item["metrics"]
        lightness = measurements["robust_mean_l"]
        contrast = measurements["contrast_span_l"]
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(item["file"]),
                    f"{item['score']:.2f} %",
                    "–" if lightness is None else f"L* {lightness:.2f}",
                    f"{metrics['brightness_shift_l']:+.2f}",
                    "–" if contrast is None else f"{contrast:.2f} L*",
                    f"{metrics['contrast_shift_percent']:+.2f} %",
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
    lines.extend(["", "## Einzelanalyse", ""])
    for item in data["images"]:
        metrics = item["metrics"]
        measurements = item["measurements"]
        lines.extend(
            [
                f"### {markdown_escape(item['file'])}",
                "",
                f"- Gesamt: {item['score']:.2f} %",
                f"- Helligkeits-Teilwert: {metrics['brightness_score']:.2f} %",
                f"- Kontrast-Teilwert: {metrics['contrast_score']:.2f} %",
                f"- Helligkeitsverschiebung: {metrics['brightness_shift_l']:+.2f} L*",
                f"- Kontrastverschiebung: {metrics['contrast_shift_percent']:+.2f} %",
                f"- Mittel / robustes Mittel / Median: {measurements['mean_l']} / {measurements['robust_mean_l']} / {measurements['median_l']}",
                f"- P10 / P90: {measurements['percentile_10_l']} / {measurements['percentile_90_l']}",
                f"- Kontrastspanne / Standardabweichung: {measurements['contrast_span_l']} / {measurements['contrast_stddev_l']}",
            ]
        )
        if item["hints"]:
            lines.append("- Hinweise:")
            lines.extend(f"  - {markdown_escape(hint)}" for hint in item["hints"])
        else:
            lines.append("- Hinweise: keine auffällige Abweichung.")
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


def render_bar(score: float) -> str:
    filled = max(0, min(BAR_WIDTH, math.floor(score * BAR_WIDTH / 100.0 + 0.5)))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def brightness_text(shift: float) -> str:
    if abs(shift) < 0.5:
        return f"◼ ±{abs(shift):.2f} L* gleich"
    if shift > 0:
        return f"☀️ {shift:+.2f} L* heller"
    return f"🌑 {shift:+.2f} L* dunkler"


def contrast_text(shift: float) -> str:
    if abs(shift) < 2.0:
        return f"◒ ±{abs(shift):.1f}% gleich"
    if shift > 0:
        return f"◑ {shift:+.1f}% stärker"
    return f"◐ {shift:+.1f}% schwächer"


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
    scored: Sequence[ScoredLight],
    skipped: Sequence[SkippedFile],
    reference: ReferenceStats,
    theme: Theme,
    paths: ReportPaths | None,
    history: HistoryResult | None,
) -> None:
    names = [terminal_safe_name(item.features.path.name) for item in scored]
    name_width = max(len(name) for name in names)
    print("\n☀️  PyImgTestBrightnessContrast\n")
    print(f"📁 Ordner: {terminal_safe_name(folder.name)}")
    print(f"🖼️  Bilder: {len(scored)} bewertet · {len(skipped)} übersprungen")
    print(f"🔗 Vergleichsgruppe: alle {len(scored)} Bilder gemeinsam")
    print(
        f"🎯 Gruppenmedian: L* {reference.robust_mean_l:.2f} · "
        f"Kontrast {reference.contrast_span_l:.2f} L*"
    )
    print()
    for item, name in zip(scored, names):
        _label, emoji, color = STATUS_DATA[item.status]
        bar = theme.paint(f"[{render_bar(item.metrics.total_score)}]", color)
        print(
            f"{name:<{name_width}}  {bar} {item.metrics.total_score:6.2f}% {emoji}  "
            f"{brightness_text(item.metrics.brightness_shift_l)} · "
            f"{contrast_text(item.metrics.contrast_shift_percent)}"
        )

    valid = [item for item in scored if item.features.robust_mean_l is not None]
    if valid:
        min_light = min(item.features.robust_mean_l for item in valid)
        max_light = max(item.features.robust_mean_l for item in valid)
        min_contrast = min(item.features.contrast_span_l for item in valid)
        max_contrast = max(item.features.contrast_span_l for item in valid)
        print("\n📏 Gruppenspanne")
        print(
            f"   Helligkeit: L* {min_light:.2f} bis {max_light:.2f} "
            f"(Spanne {max_light - min_light:.2f})"
        )
        print(
            f"   Kontrast:   {min_contrast:.2f} bis {max_contrast:.2f} L* "
            f"(Spanne {max_contrast - min_contrast:.2f})"
        )

    average = statistics.mean(item.metrics.total_score for item in scored)
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
    if reference.confidence == "low":
        print(
            theme.paint(
                "⚠️ Bewertungsvertrauen niedrig: nur zwei sichtbare Bilder.", "33"
            )
        )
    if skipped:
        print(theme.paint(f"⚠️ Übersprungene Dateien: {len(skipped)}", "33"))
    if paths is not None:
        print(f"\n📄 Report: {OUTPUT_FOLDER}/{paths.markdown.name}")
        print(f"🧾 JSON:   {OUTPUT_FOLDER}/{paths.json.name}")
        print(f"📊 Figur:  {OUTPUT_FOLDER}/{paths.figure.name}")


def run(no_color: bool = False, no_report: bool = False) -> int:
    folder = Path.cwd()
    sources = find_images(folder)
    if len(sources) < 2:
        print(
            "FEHLER: Mindestens zwei unterstützte Bilder direkt im aktuellen "
            "Ordner sind erforderlich.",
            file=sys.stderr,
        )
        return 1

    features: list[LightFeatures] = []
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

    reference = build_reference(features)
    scored = score_group(features, reference)
    paths: ReportPaths | None = None
    history: HistoryResult | None = None
    if not no_report:
        output = ensure_output_folder(folder)
        scoring_model = scoring_model_data()
        history = make_history_result(
            find_previous_report(output, folder),
            scored,
            str(scoring_model["fingerprint"]),
        )
        paths = allocate_report_paths(output)
        figure = create_figure(scored, reference, paths.figure)
        data = build_report_data(
            folder,
            len(sources),
            scored,
            skipped,
            reference,
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
        reference,
        Theme(color_enabled),
        paths,
        history,
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
