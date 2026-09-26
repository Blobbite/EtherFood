#!/usr/bin/env python3
"""PyImgH: PNG-Sprite-Sheets im aktuellen Arbeitsordner automatisch trennen.

Ohne Argumente verarbeitet das Programm alle PNG-Dateien im Verzeichnis, in
welchem der Befehl ausgeführt wird. Der Speicherort dieses Skripts ist dabei
unerheblich. Aus ``figur.png`` entsteht zum Beispiel::

    figur/
    ├── figur_001.png
    ├── figur_002.png
    └── export.json

Die Anzahl der Sprites wird automatisch über den Alphakanal erkannt. Ein
``expected count`` muss nicht angegeben werden.

python3 PyImgSplitA_korrigiert.py --padding 8
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

__version__ = "2.1.0"

# Abhängigkeiten werden erst nach dem Parsen der CLI geladen. Dadurch funktioniert
# ``PyImgH.py --help`` auch dann, wenn die Python-Pakete noch nicht installiert sind.
cv2: Any = None
np: Any = None
Image: Any = None


@dataclass(frozen=True)
class SpriteCore:
    """Eine zusammenhängende, solide Kernfläche eines erkannten Sprites."""

    source_label: int
    territory_label: int
    x: int
    y: int
    width: int
    height: int
    area: int
    center_x: float
    center_y: float


@dataclass(frozen=True)
class ThresholdSample:
    """Erkennungsergebnis für einen getesteten Alphawert."""

    threshold: int
    count: int
    total_area: int
    median_area: float


@dataclass(frozen=True)
class SpriteRegion:
    """Sichtbarer Quellbereich eines Sprites innerhalb einer erkannten Zeile."""

    core: SpriteCore
    column: int
    x0: int
    y0: int
    x1: int
    y1: int


class GermanArgumentParser(argparse.ArgumentParser):
    """Argparse-Fehler mit einer deutschen Bezeichnung ausgeben."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: Fehler: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = GermanArgumentParser(
        prog=Path(sys.argv[0]).name,
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Trennt automatisch alle PNG-Sprite-Sheets eines Verzeichnisses.\n"
            "Standardmäßig wird das aktuelle Arbeitsverzeichnis verarbeitet."
        ),
        epilog=(
            "Beispiele:\n"
            "  PyImgH.py\n"
            "  PyImgH.py /pfad/zu/den/png-dateien\n"
            "  PyImgH.py --padding 0\n"
            "  PyImgH.py --threshold 80 --min-area 20\n\n"
            "Aus walk.png entsteht der Ordner walk/ mit walk_001.png,\n"
            "walk_002.png usw. Die Exportanzahl steht zusätzlich in export.json."
        ),
    )
    parser._positionals.title = "Positionsargumente"
    parser._optionals.title = "Optionen"
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="diese Hilfe anzeigen und beenden",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=Path("."),
        metavar="VERZEICHNIS",
        help="PNG-Verzeichnis; Standard: aktuelles Arbeitsverzeichnis",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=4,
        metavar="PIXEL",
        help="transparenter Rand der gemeinsamen Zeilen-Leinwand; Standard: 4",
    )
    parser.add_argument(
        "--threshold",
        default="auto",
        metavar="AUTO|1-254",
        help="Alphawert für die Kernerkennung; Standard: auto",
    )
    parser.add_argument(
        "--min-area",
        default="auto",
        metavar="AUTO|PIXEL",
        help="kleinste Kernfläche; Standard: auto",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Programmversion anzeigen und beenden",
    )
    return parser


def load_dependencies() -> None:
    """Pillow, NumPy und OpenCV laden und bei Bedarf Installationshilfe zeigen."""

    global cv2, np, Image
    try:
        import cv2 as imported_cv2
        import numpy as imported_numpy
        from PIL import Image as imported_image
    except ImportError as exc:
        missing = getattr(exc, "name", "ein benötigtes Paket")
        raise RuntimeError(
            f"Python-Abhängigkeit fehlt: {missing}\n"
            "Installation im verwendeten Python/venv:\n"
            "  python3 -m pip install -r requirements.txt\n"
            "oder direkt:\n"
            "  python3 -m pip install Pillow numpy opencv-python-headless"
        ) from exc

    cv2 = imported_cv2
    np = imported_numpy
    Image = imported_image


def parse_auto_int(value: str, *, name: str, minimum: int, maximum: int | None) -> int | None:
    """``auto`` oder eine begrenzte Ganzzahl einlesen."""

    if value.strip().lower() == "auto":
        return None
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} muss 'auto' oder eine Ganzzahl sein") from exc

    if number < minimum:
        raise ValueError(f"{name} muss mindestens {minimum} sein")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name} darf höchstens {maximum} sein")
    return number


def find_png_files(directory: Path) -> list[Path]:
    """Alle PNG-Dateien direkt im Verzeichnis finden, nicht rekursiv."""

    return sorted(
        (
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".png"
        ),
        key=lambda path: path.name.casefold(),
    )


def load_rgba(path: Path) -> Any:
    """Bild als eigenständiges uint8-RGBA-Array laden."""

    try:
        with Image.open(path) as image:
            image.load()
            return np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"PNG konnte nicht geöffnet werden: {path.name}") from exc


def remove_flat_border_background(rgba: Any) -> tuple[Any, str]:
    """Bei vollständig deckenden PNGs einen einfachen Randhintergrund entfernen.

    Die Hintergrundfarbe wird aus der häufigsten quantisierten Farbe am Bildrand
    bestimmt. Nur farbähnliche Bereiche, die mit dem äußeren Rand verbunden sind,
    werden transparent. Bei komplexem oder uneinheitlichem Rand wird abgebrochen,
    statt Bildinhalt aggressiv zu löschen.
    """

    result = rgba.copy()
    rgb = result[..., :3].astype(np.int16)
    border = np.concatenate(
        (rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]),
        axis=0,
    )

    # 16 Stufen pro Farbkanal: robuste Erkennung eines dominanten, flachen Randes.
    quantized = np.clip(border // 16, 0, 15).astype(np.int32)
    keys = quantized[:, 0] * 256 + quantized[:, 1] * 16 + quantized[:, 2]
    unique_keys, counts = np.unique(keys, return_counts=True)
    dominant_key = int(unique_keys[int(np.argmax(counts))])
    dominant_pixels = border[keys == dominant_key]
    dominance = float(dominant_pixels.shape[0]) / float(max(1, border.shape[0]))

    if dominance < 0.45:
        raise RuntimeError(
            "kein nutzbarer Alphakanal und kein ausreichend gleichmäßiger "
            "Randhintergrund erkannt"
        )

    background = np.median(dominant_pixels, axis=0)
    cluster_distance = np.linalg.norm(dominant_pixels - background, axis=1)
    tolerance = float(np.clip(np.percentile(cluster_distance, 99) + 7.0, 8.0, 48.0))

    distance = np.linalg.norm(rgb - background, axis=2)
    candidate = (distance <= tolerance).astype(np.uint8)
    component_count, labels = cv2.connectedComponents(candidate, connectivity=8)
    if component_count <= 1:
        raise RuntimeError("der deckende Hintergrund konnte nicht getrennt werden")

    border_labels = np.unique(
        np.concatenate((labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]))
    )
    border_labels = border_labels[border_labels != 0]
    background_mask = np.isin(labels, border_labels)

    remaining = int((~background_mask).sum())
    total = int(background_mask.size)
    if remaining < 4 or remaining > int(total * 0.98):
        raise RuntimeError("automatische Hintergrundentfernung war nicht eindeutig")

    result[..., 3] = np.where(background_mask, 0, 255).astype(np.uint8)
    result[background_mask, :3] = 0
    return result, f"Randfarbe automatisch entfernt (Toleranz {tolerance:.1f})"


def prepare_transparency(rgba: Any) -> tuple[Any, str]:
    """Vorhandenen Alphakanal nutzen oder sicheren, flachen Rand entfernen."""

    alpha = rgba[..., 3]
    if int(alpha.min()) < 255:
        return rgba, "Alphakanal"
    return remove_flat_border_background(rgba)


def automatic_min_area(alpha: Any) -> int:
    """Konservative Mindestgröße passend zur Bild- und Vordergrundfläche wählen."""

    image_area = int(alpha.size)
    visible_area = int(np.count_nonzero(alpha))
    by_image = max(4, int(round(image_area * 0.00002)))
    by_visible = max(4, int(round(visible_area * 0.00010)))
    return max(4, min(by_image, by_visible))


def threshold_candidates(alpha: Any) -> list[int]:
    """Feste und aus dem Alphakanal abgeleitete Testwerte erzeugen."""

    nonzero = alpha[alpha > 0]
    if nonzero.size == 0:
        return []

    maximum = int(nonzero.max())
    fixed = {
        1,
        2,
        4,
        8,
        12,
        16,
        24,
        32,
        40,
        48,
        56,
        64,
        72,
        80,
        96,
        112,
        128,
        144,
        160,
        176,
        192,
        208,
        224,
        240,
        248,
        maximum,
    }
    for quantile in (5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95):
        fixed.add(int(round(float(np.percentile(nonzero, quantile)))))

    return sorted(value for value in fixed if 1 <= value <= min(254, maximum))


def sample_threshold(alpha: Any, threshold: int, min_area: int) -> ThresholdSample:
    """Anzahl und Fläche brauchbarer Komponenten für einen Alphawert messen."""

    mask = (alpha >= threshold).astype(np.uint8)
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        mask, connectivity=8
    )
    if count <= 1:
        return ThresholdSample(threshold, 0, 0, 0.0)

    areas = stats[1:, cv2.CC_STAT_AREA].astype(np.int64)
    kept = areas[areas >= min_area]
    if kept.size == 0:
        return ThresholdSample(threshold, 0, 0, 0.0)

    return ThresholdSample(
        threshold=threshold,
        count=int(kept.size),
        total_area=int(kept.sum()),
        median_area=float(np.median(kept)),
    )


def choose_automatic_threshold(alpha: Any, min_area: int) -> tuple[int, list[ThresholdSample]]:
    """Einen stabilen Alphawert wählen, ohne eine Sprite-Anzahl vorzugeben.

    Mehrere Alphawerte werden getestet. Bevorzugt wird ein längerer Bereich, in
    dem die erkannte Komponentenanzahl konstant bleibt und noch viel Kernfläche
    vorhanden ist. Innerhalb dieses Bereichs wird ein moderater Wert nahe 64
    gewählt. So werden schwache Alpha-Brücken meist getrennt, ohne transparente
    Sprites unnötig zu zerlegen.
    """

    candidates = threshold_candidates(alpha)
    samples = [sample_threshold(alpha, value, min_area) for value in candidates]
    valid = [sample for sample in samples if sample.count > 0]
    if not valid:
        raise RuntimeError(
            "keine Sprites erkannt; bei sehr kleinen Motiven --min-area verkleinern"
        )

    max_total_area = max(sample.total_area for sample in valid)

    # Läufe mit gleicher Komponentenanzahl bilden.
    runs: list[list[ThresholdSample]] = []
    for sample in valid:
        if not runs or runs[-1][-1].count != sample.count:
            runs.append([sample])
        else:
            runs[-1].append(sample)

    def run_score(run: list[ThresholdSample]) -> tuple[float, int, int]:
        low = run[0].threshold
        high = run[-1].threshold
        span = max(1, high - low + 1)
        coverage = float(np.median([item.total_area for item in run])) / float(
            max_total_area
        )
        # Stabilität dominiert. Flächenabdeckung bremst hochschwellige Fragmentierung.
        score = span * (0.30 + 0.70 * coverage)
        score += len(run) * 2.0
        score += math.log2(run[0].count + 1.0)
        return score, span, run[0].count

    best_run = max(runs, key=run_score)
    # Moderate 64 bevorzugen; ansonsten den nächstgelegenen Wert im stabilen Lauf.
    chosen = min(best_run, key=lambda item: (abs(item.threshold - 64), item.threshold))
    return chosen.threshold, samples


def detect_sprite_cores(alpha: Any, threshold: int, min_area: int) -> tuple[list[SpriteCore], Any]:
    """Sprite-Kerne erkennen und jedes Bildpixel seinem nächsten Kern zuweisen."""

    core_mask = (alpha >= threshold).astype(np.uint8)
    component_count, component_labels, stats, centroids = (
        cv2.connectedComponentsWithStats(core_mask, connectivity=8)
    )

    kept_ids = [
        component_id
        for component_id in range(1, component_count)
        if int(stats[component_id, cv2.CC_STAT_AREA]) >= min_area
    ]
    if not kept_ids:
        raise RuntimeError(
            "keine Sprites erkannt; --threshold oder --min-area verkleinern"
        )

    retained_seed = np.zeros_like(core_mask, dtype=np.uint8)
    for component_id in kept_ids:
        retained_seed[component_labels == component_id] = 1

    distance_input = np.where(retained_seed != 0, 0, 255).astype(np.uint8)
    _distance, territory_labels = cv2.distanceTransformWithLabels(
        distance_input,
        cv2.DIST_L2,
        5,
        labelType=cv2.DIST_LABEL_CCOMP,
    )

    cores: list[SpriteCore] = []
    for component_id in kept_ids:
        territory_values = territory_labels[component_labels == component_id]
        if territory_values.size == 0:
            continue
        territory_id = int(np.bincount(territory_values.ravel()).argmax())

        x = int(stats[component_id, cv2.CC_STAT_LEFT])
        y = int(stats[component_id, cv2.CC_STAT_TOP])
        width = int(stats[component_id, cv2.CC_STAT_WIDTH])
        height = int(stats[component_id, cv2.CC_STAT_HEIGHT])
        area = int(stats[component_id, cv2.CC_STAT_AREA])
        center_x, center_y = centroids[component_id]

        cores.append(
            SpriteCore(
                source_label=component_id,
                territory_label=territory_id,
                x=x,
                y=y,
                width=width,
                height=height,
                area=area,
                center_x=float(center_x),
                center_y=float(center_y),
            )
        )

    if not cores:
        raise RuntimeError("die erkannten Kernflächen konnten nicht zugeordnet werden")
    return cores, territory_labels


def group_row_major(cores: Iterable[SpriteCore]) -> list[list[SpriteCore]]:
    """Erkannte Sprites zeilenweise von oben links nach unten rechts sortieren."""

    ordered = sorted(cores, key=lambda item: (item.center_y, item.center_x))
    if not ordered:
        return []

    median_height = float(np.median([item.height for item in ordered]))
    tolerance = max(3.0, median_height * 0.45)
    rows: list[list[SpriteCore]] = []

    for item in ordered:
        best_index: int | None = None
        best_distance = float("inf")
        for row_index, row in enumerate(rows):
            row_center = float(np.mean([member.center_y for member in row]))
            distance = abs(item.center_y - row_center)
            if distance <= tolerance and distance < best_distance:
                best_index = row_index
                best_distance = distance

        if best_index is None:
            rows.append([item])
        else:
            rows[best_index].append(item)

    rows.sort(key=lambda row: float(np.mean([member.center_y for member in row])))
    for row in rows:
        row.sort(key=lambda item: item.center_x)
    return rows


def find_sprite_region(
    *,
    alpha: Any,
    territory_labels: Any,
    core: SpriteCore,
    column: int,
) -> SpriteRegion | None:
    """Den vollständigen sichtbaren Bereich eines zugeordneten Sprites bestimmen."""

    owned_pixels = (territory_labels == core.territory_label) & (alpha > 0)
    ys, xs = np.nonzero(owned_pixels)
    if xs.size == 0 or ys.size == 0:
        return None

    return SpriteRegion(
        core=core,
        column=column,
        x0=int(xs.min()),
        y0=int(ys.min()),
        x1=int(xs.max()) + 1,
        y1=int(ys.max()) + 1,
    )


def round_pixel(value: float) -> int:
    """Positive Pixelkoordinaten konsistent zur nächsten Ganzzahl runden."""

    return int(math.floor(value + 0.5))


def infer_row_column_anchors(
    regions: list[SpriteRegion],
) -> tuple[list[int], float | None, str]:
    """Quellanker für gleich ausgerichtete Frames einer Zeile bestimmen.

    Ab drei Frames wird aus den erkannten horizontalen Mittelpunkten ein robustes,
    gleichmäßiges Spaltenraster geschätzt. Kleine Lageunterschiede durch Arm- oder
    Beinbewegungen verändern dadurch nicht den Ursprung des Einzelbildes. Falls
    die Anordnung kein plausibles Raster bildet, werden die erkannten Kernzentren
    selbst als Anker verwendet.
    """

    centers = np.asarray([region.core.center_x for region in regions], dtype=float)
    count = int(centers.size)
    if count == 0:
        return [], None, "none"
    if count < 3:
        return [round_pixel(float(value)) for value in centers], None, "core-centers"

    # Theil-Sen-artige robuste Steigung: Median aller paarweisen Spaltenabstände.
    pitches: list[float] = []
    for left_index in range(count - 1):
        for right_index in range(left_index + 1, count):
            column_distance = right_index - left_index
            pitches.append(
                float(centers[right_index] - centers[left_index])
                / float(column_distance)
            )

    raw_pitch = float(np.median(np.asarray(pitches, dtype=float)))
    if not math.isfinite(raw_pitch) or raw_pitch <= 0.0:
        return [round_pixel(float(value)) for value in centers], None, "core-centers"

    # Ein Sprite-Sheet besitzt ein ganzzahliges Pixelraster. Eine ganzzahlige
    # Spaltenbreite verhindert wechselnde Rundungsfehler von einem Frame zum
    # nächsten, besonders bei Mittelpunkten auf halben Pixelkoordinaten.
    pitch = float(max(1, round_pixel(raw_pitch)))

    indices = np.arange(count, dtype=float)
    origin = float(np.median(centers - indices * pitch))
    fitted = origin + indices * pitch
    residuals = np.abs(centers - fitted)

    median_width = float(
        np.median([region.x1 - region.x0 for region in regions])
    )
    tolerance = max(2.0, min(pitch * 0.12, median_width * 0.20))
    if float(residuals.max()) > tolerance:
        return [round_pixel(float(value)) for value in centers], None, "core-centers"

    anchors = [round_pixel(float(value)) for value in fitted]
    if any(anchors[index] >= anchors[index + 1] for index in range(count - 1)):
        return [round_pixel(float(value)) for value in centers], None, "core-centers"

    return anchors, pitch, "inferred-grid"


def output_is_managed(output_dir: Path, source_name: str) -> bool:
    """Prüfen, ob ein vorhandener Ausgabeordner sicher von PyImgH stammt."""

    marker = output_dir / ".pyimgh-output"
    if not marker.is_file():
        return False
    try:
        return marker.read_text(encoding="utf-8").strip() == source_name
    except OSError:
        return False


def validate_output_target(output_dir: Path, source_name: str) -> None:
    """Nicht von PyImgH verwaltete, gleichnamige Ordner vor Überschreiben schützen."""

    if not output_dir.exists():
        return
    if not output_dir.is_dir():
        raise RuntimeError(f"Ausgabeziel ist kein Ordner: {output_dir.name}")
    if not any(output_dir.iterdir()):
        return
    if not output_is_managed(output_dir, source_name):
        raise RuntimeError(
            f"Ordner '{output_dir.name}' existiert bereits und stammt nicht von PyImgH"
        )


def save_sprites_to_temp(
    *,
    source: Path,
    rgba: Any,
    territory_labels: Any,
    rows: list[list[SpriteCore]],
    temp_dir: Path,
    padding: int,
    threshold: int,
    min_area: int,
    transparency_mode: str,
) -> list[dict[str, Any]]:
    """Sprites auf gemeinsam ausgerichteten Zeilen-Leinwänden speichern.

    Alle Frames derselben erkannten Zeile erhalten exakt dieselbe Bildgröße.
    Die vertikale Lage wird aus dem gemeinsamen Quellkoordinatensystem der Zeile
    übernommen. Horizontal wird jeder Frame auf denselben Spaltenanker versetzt.
    So ändert ein unterschiedlich enger sichtbarer Rahmen nicht mehr den Ursprung
    der exportierten PNG-Dateien.
    """

    temp_dir.mkdir(parents=False, exist_ok=False)
    alpha = rgba[..., 3]
    ordered = [core for row in rows for core in row]
    number_width = max(3, len(str(len(ordered))))
    entries: list[dict[str, Any]] = []
    row_reports: list[dict[str, Any]] = []
    sequential_index = 0

    for row_index, row in enumerate(rows, start=1):
        regions: list[SpriteRegion] = []
        for column_index, core in enumerate(row, start=1):
            region = find_sprite_region(
                alpha=alpha,
                territory_labels=territory_labels,
                core=core,
                column=column_index,
            )
            if region is not None:
                regions.append(region)

        if not regions:
            continue

        source_anchors_x, inferred_pitch, anchor_mode = infer_row_column_anchors(
            regions
        )

        # Gemeinsame vertikale Quellkoordinaten bewahren Höhenunterschiede und
        # verhindern, dass jeder Frame separat an seine obere Kante springt.
        row_source_top = min(region.y0 for region in regions)
        row_source_bottom = max(region.y1 for region in regions)
        canvas_height = (row_source_bottom - row_source_top) + 2 * padding

        # Links und rechts vom gemeinsamen Anker wird jeweils die größte benötigte
        # Ausdehnung aller Frames reserviert. Kein Sprite kann dadurch abgeschnitten
        # werden, obwohl alle PNGs derselben Zeile dieselbe Breite erhalten.
        left_extent = max(
            0,
            max(
                source_anchor_x - region.x0
                for region, source_anchor_x in zip(regions, source_anchors_x)
            ),
        )
        right_extent = max(
            0,
            max(
                region.x1 - source_anchor_x
                for region, source_anchor_x in zip(regions, source_anchors_x)
            ),
        )
        canvas_width = left_extent + right_extent + 2 * padding
        canvas_anchor_x = padding + left_extent

        row_export_count = 0
        for region, source_anchor_x in zip(regions, source_anchors_x):
            crop = rgba[region.y0 : region.y1, region.x0 : region.x1].copy()
            local_owner = (
                territory_labels[
                    region.y0 : region.y1,
                    region.x0 : region.x1,
                ]
                == region.core.territory_label
            )
            crop[~local_owner, 3] = 0
            crop[crop[..., 3] == 0, :3] = 0

            destination_x = canvas_anchor_x + (region.x0 - source_anchor_x)
            destination_y = padding + (region.y0 - row_source_top)
            destination_x1 = destination_x + (region.x1 - region.x0)
            destination_y1 = destination_y + (region.y1 - region.y0)

            if (
                destination_x < 0
                or destination_y < 0
                or destination_x1 > canvas_width
                or destination_y1 > canvas_height
            ):
                raise RuntimeError(
                    "interner Ausrichtungsfehler: Sprite passt nicht auf die "
                    "gemeinsame Zeilen-Leinwand"
                )

            canvas = np.zeros((canvas_height, canvas_width, 4), dtype=np.uint8)
            canvas[
                destination_y:destination_y1,
                destination_x:destination_x1,
            ] = crop

            sequential_index += 1
            row_export_count += 1
            filename = f"{source.stem}_{sequential_index:0{number_width}d}.png"
            destination = temp_dir / filename
            Image.fromarray(canvas).save(destination, format="PNG", optimize=True)

            entries.append(
                {
                    "index": sequential_index,
                    "row": row_index,
                    "column": region.column,
                    "file": filename,
                    "source_bbox": {
                        "x": region.x0,
                        "y": region.y0,
                        "width": region.x1 - region.x0,
                        "height": region.y1 - region.y0,
                    },
                    "output_bbox": {
                        "x": destination_x,
                        "y": destination_y,
                        "width": region.x1 - region.x0,
                        "height": region.y1 - region.y0,
                    },
                    "canvas": {
                        "width": canvas_width,
                        "height": canvas_height,
                    },
                    "alignment": {
                        "mode": anchor_mode,
                        "source_anchor_x": source_anchor_x,
                        "canvas_anchor_x": canvas_anchor_x,
                        "source_row_top": row_source_top,
                        "canvas_row_top": padding,
                    },
                    "core_area": region.core.area,
                }
            )

        row_reports.append(
            {
                "row": row_index,
                "export_count": row_export_count,
                "canvas_width": canvas_width,
                "canvas_height": canvas_height,
                "canvas_anchor_x": canvas_anchor_x,
                "anchor_mode": anchor_mode,
                "inferred_column_pitch": (
                    round(float(inferred_pitch), 4)
                    if inferred_pitch is not None
                    else None
                ),
            }
        )

    if not entries:
        raise RuntimeError("keine sichtbaren Sprite-Bereiche zum Speichern gefunden")

    report = {
        "generator": "PyImgH",
        "generator_version": __version__,
        "source_file": source.name,
        "source_width": int(rgba.shape[1]),
        "source_height": int(rgba.shape[0]),
        "export_count": len(entries),
        "row_count": len(row_reports),
        "padding": padding,
        "alignment_mode": "shared-row-canvas",
        "alpha_threshold": threshold,
        "min_core_area": min_area,
        "transparency_mode": transparency_mode,
        "rows": row_reports,
        "files": entries,
    }
    (temp_dir / "export.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (temp_dir / ".pyimgh-output").write_text(source.name + "\n", encoding="utf-8")
    return entries


def replace_output_directory(temp_dir: Path, output_dir: Path) -> None:
    """Temporäre Ausgabe einsetzen; bei Fehlern die vorige Ausgabe wiederherstellen."""

    backup_dir: Path | None = None
    if output_dir.exists():
        if any(output_dir.iterdir()):
            backup_dir = output_dir.with_name(
                f".{output_dir.name}.pyimgh-old-{uuid.uuid4().hex[:8]}"
            )
            output_dir.rename(backup_dir)
        else:
            output_dir.rmdir()

    try:
        temp_dir.rename(output_dir)
    except OSError:
        if backup_dir is not None and backup_dir.exists() and not output_dir.exists():
            backup_dir.rename(output_dir)
        raise
    else:
        if backup_dir is not None:
            shutil.rmtree(backup_dir)


def process_png(
    source: Path,
    *,
    padding: int,
    requested_threshold: int | None,
    requested_min_area: int | None,
) -> dict[str, Any]:
    """Eine PNG-Datei erkennen, trennen und im gleichnamigen Ordner speichern."""

    output_dir = source.parent / source.stem
    validate_output_target(output_dir, source.name)

    rgba = load_rgba(source)
    rgba, transparency_mode = prepare_transparency(rgba)
    alpha = rgba[..., 3]
    if int(np.count_nonzero(alpha)) == 0:
        raise RuntimeError("das Bild enthält keine sichtbaren Pixel")

    min_area = requested_min_area or automatic_min_area(alpha)
    if requested_threshold is None:
        threshold, _samples = choose_automatic_threshold(alpha, min_area)
    else:
        threshold = requested_threshold

    cores, territory_labels = detect_sprite_cores(alpha, threshold, min_area)
    rows = group_row_major(cores)

    temp_dir = source.parent / (
        f".{source.stem}.pyimgh-tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    )
    try:
        entries = save_sprites_to_temp(
            source=source,
            rgba=rgba,
            territory_labels=territory_labels,
            rows=rows,
            temp_dir=temp_dir,
            padding=padding,
            threshold=threshold,
            min_area=min_area,
            transparency_mode=transparency_mode,
        )
        replace_output_directory(temp_dir, output_dir)
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return {
        "source": source,
        "output": output_dir,
        "count": len(entries),
        "rows": len(rows),
        "threshold": threshold,
        "min_area": min_area,
        "transparency_mode": transparency_mode,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        directory = args.directory.expanduser().resolve()
        if not directory.is_dir():
            raise ValueError(f"Verzeichnis nicht gefunden: {directory}")
        if args.padding < 0:
            raise ValueError("--padding darf nicht negativ sein")

        requested_threshold = parse_auto_int(
            args.threshold,
            name="--threshold",
            minimum=1,
            maximum=254,
        )
        requested_min_area = parse_auto_int(
            args.min_area,
            name="--min-area",
            minimum=1,
            maximum=None,
        )
        load_dependencies()
        png_files = find_png_files(directory)
        if not png_files:
            print(f"Keine PNG-Dateien gefunden: {directory}", file=sys.stderr)
            return 1
    except (RuntimeError, ValueError, OSError) as exc:
        parser.error(str(exc))
        return 2

    print(f"Verzeichnis: {directory}")
    print(f"PNG-Dateien: {len(png_files)}\n")

    successes: list[dict[str, Any]] = []
    failures: list[tuple[Path, str]] = []

    for source in png_files:
        try:
            result = process_png(
                source,
                padding=args.padding,
                requested_threshold=requested_threshold,
                requested_min_area=requested_min_area,
            )
            successes.append(result)
            print(
                f"[OK] {source.name}: {result['count']} Bilder -> "
                f"{result['output'].name}/ "
                f"(Alpha {result['threshold']}, MinArea {result['min_area']})"
            )
        except (RuntimeError, OSError, ValueError) as exc:
            failures.append((source, str(exc)))
            print(f"[FEHLER] {source.name}: {exc}", file=sys.stderr)

    exported_total = sum(int(item["count"]) for item in successes)
    print("\nZusammenfassung")
    print(f"  Erfolgreiche PNG-Dateien: {len(successes)}")
    print(f"  Exportierte Einzelbilder: {exported_total}")
    print(f"  Fehler: {len(failures)}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
