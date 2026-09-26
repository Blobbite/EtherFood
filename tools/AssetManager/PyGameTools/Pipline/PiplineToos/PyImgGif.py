#!/usr/bin/env python3
"""Spritesheets oder Einzelbilder im aktuellen Arbeitsordner zu GIFs animieren.

    PyImageGif --fps 12
    PyImageGif --fps 8 --grid 16x1
    PyImageGif --solo --fps 8
    PyImageGif --html-only --overwrite --open-html

Standard: pro erkanntem Spritesheet ein GIF. Automatische Rastererkennung
fuer 3 bis 64 Zellen; Reihenfolge links nach rechts, dann oben nach unten.
Mit --grid SPALTENxZEILEN wird das Raster manuell vorgegeben (3 bis 64 Zellen).
Solo: alle statischen Bilder in natuerlicher Dateinamen-Reihenfolge in ein GIF.

Nur der aktuelle Arbeitsordner (Path.cwd()) wird gelesen, nie Unterordner.
Keine Wrapper-Installation, keine externen Programme. Abhaengigkeit: Pillow.
Python >= 3.10, Pillow >= 9.1.

Fehlende GIFs und gif-vergleich.html werden erstellt; vorhandene Ausgaben bleiben
erhalten. --overwrite erstellt sie neu, --dry-run prueft nur den Ablauf.
Ohne --files umfasst die Galerie alle GIFs im Arbeitsordner.
Offline-HTML mit verlinkten GIFs und vorhandenen
Spritesheets fuer genaue FPS-, Tempo-, Frame- und Vergleichsregler.
Die Regler veraendern nur die Vorschau.
--html-only erzeugt nur HTML; zum Aktualisieren --overwrite hinzufuegen.
--no-html deaktiviert den HTML-Export.
"""
from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import tempfile
from typing import Sequence
from urllib.parse import quote
import warnings
import webbrowser

import PyPipelineOutputs as output_policy

try:
    from PIL import Image, ImageChops, ImageStat
except ImportError:
    Image = ImageChops = ImageStat = None  # type: ignore[assignment]

FPS_CHOICES = (2, 4, 6, 8, 10, 12, 16, 18, 20, 22, 24)
MIN_SHEET_FRAMES = 3
MAX_SHEET_FRAMES = 64
EXTENSIONS = frozenset({".png", ".webp", ".bmp", ".tga", ".tif", ".tiff", ".jpg", ".jpeg"})
# Safety limits, not resizing settings. Source files are never modified.
MAX_SEQUENCE_PIXELS = 64_000_000
PALETTE_SAMPLE_PIXELS = 1_000_000
ALPHA_THRESHOLD = 128
GRID_PATTERN = re.compile(r"(?<![0-9])([0-9]{1,2})\s*[xX\u00d7]\s*([0-9]{1,2})(?![0-9])")


class ConversionError(ValueError):
    """A source cannot safely be converted with these fixed rules."""


@dataclass(frozen=True)
class Grid:
    columns: int
    rows: int
    source: str

    @property
    def count(self) -> int:
        return self.columns * self.rows


@dataclass(frozen=True)
class GifResult:
    source_frames: int
    stored_frames: int
    duration_ms: int


def parse_grid(value: str) -> Grid:
    """Parse an explicit layout, retaining the existing sheet size limits."""
    match = re.fullmatch(r"([1-9][0-9]*)\s*[xX\u00d7]\s*([1-9][0-9]*)", value.strip())
    if match is None:
        raise argparse.ArgumentTypeError(
            "Raster als SPALTENxZEILEN angeben, z.B. 16x1 oder 1x16.")
    columns, rows = map(int, match.groups())
    if not MIN_SHEET_FRAMES <= columns * rows <= MAX_SHEET_FRAMES:
        raise argparse.ArgumentTypeError("Das Raster muss 3 bis 64 Zellen enthalten.")
    return Grid(columns, rows, "manuell (--grid)")


def natural_key(path: Path) -> tuple:
    """Stable natural sort: frame1, frame2, frame10; independent of locale."""
    chunks = re.split(r"([0-9]+)", path.name.casefold())
    return (tuple((1, int(s)) if s.isascii() and s.isdigit() else (0, s)
                  for s in chunks), path.name)


def discover_images(directory: Path) -> list[Path]:
    """No recursion, no hidden entries, no symlinks, no GIF feedback loop."""
    return sorted(
        (p for p in directory.iterdir()
         if not p.name.startswith(".") and not p.is_symlink()
         and p.is_file() and p.suffix.casefold() in EXTENSIONS),
        key=natural_key,
    )


def load_image(path: Path) -> Image.Image:
    """Load one static image, retaining its original canvas and orientation."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ConversionError("Animierte oder mehrseitige Eingabe; erwartet wird ein statisches Bild.")
            if image.width * image.height > MAX_SEQUENCE_PIXELS:
                raise ConversionError(f"Bild zu gross: Schutzgrenze {MAX_SEQUENCE_PIXELS:,} Pixel.")
            rgba = image.convert("RGBA")
            rgba.info.clear()  # Do not inherit unrelated durations/transparency tags.
            return rgba


def grid_from_name(path: Path, size: tuple[int, int]) -> Grid | None:
    """An explicit 4x4 / 2x3 / 16x1 token is authoritative layout metadata.

    Large dimension tokens such as 256x256 are deliberately not grid hints.
    An ambiguous or non-divisible hint is an error, never a silent fallback.
    """
    hints = {(int(m[1]), int(m[2])) for m in GRID_PATTERN.finditer(path.stem)
             if 1 <= int(m[1]) and 1 <= int(m[2])
             and int(m[1]) * int(m[2]) <= MAX_SHEET_FRAMES}
    if not hints:
        return None
    if len(hints) != 1:
        raise ConversionError("Widerspruechliche Rasterangaben im Dateinamen.")
    columns, rows = hints.pop()
    if not MIN_SHEET_FRAMES <= columns * rows <= MAX_SHEET_FRAMES:
        raise ConversionError(f"Raster {columns}x{rows} liegt ausserhalb von 3 bis 64 Zellen.")
    width, height = size
    if width % columns or height % rows:
        raise ConversionError(
            f"Dateiname nennt {columns}x{rows}, aber {width}x{height} Pixel sind nicht passend teilbar.")
    return Grid(columns, rows, "Dateiname")


def foreground_mask(image: Image.Image) -> tuple[Image.Image, str]:
    """Build a mask for analysis only; never remove an opaque background."""
    alpha = image.getchannel("A")
    hist = alpha.histogram()
    total = image.width * image.height
    if sum(hist[:16]) >= max(1, total * 0.005):
        mask = alpha.point([0] * 16 + [255] * 240)
        if mask.getbbox() is None:
            raise ConversionError("Kein sichtbarer Bildinhalt fuer die Rastererkennung.")
        return mask, "Transparenz"

    # Read a bounded number of border samples, allowing small JPEG deviations.
    rgb = image.convert("RGB")
    pixels = rgb.load()
    width, height = rgb.size
    sx, sy = max(1, width // 256), max(1, height // 256)
    samples = ([pixels[x, 0] for x in range(0, width, sx)]
               + [pixels[x, height - 1] for x in range(0, width, sx)]
               + [pixels[0, y] for y in range(0, height, sy)]
               + [pixels[width - 1, y] for y in range(0, height, sy)])
    groups = Counter(tuple(channel // 8 for channel in color) for color in samples)
    key, _ = groups.most_common(1)[0]
    group = [c for c in samples if tuple(v // 8 for v in c) == key]
    background = tuple(int(statistics.median(c[i] for c in group)) for i in range(3))
    matching = sum(max(abs(c[i] - background[i]) for i in range(3)) <= 20 for c in samples)
    if matching / len(samples) < 0.75:
        raise ConversionError("Kein ausreichend gleichmaessiger Hintergrund fuer die Rastererkennung.")
    difference = ImageChops.difference(rgb, Image.new("RGB", rgb.size, background))
    red, green, blue = difference.split()
    maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    mask = maximum.point([0] * 21 + [255] * 235)
    if mask.getbbox() is None:
        raise ConversionError("Einfarbiges Bild: kein Raster aus dem Bildinhalt erkennbar.")
    return mask, "Hintergrundabstaende"


def boundary_scores(values: Sequence[int], parts: int) -> list[float] | None:
    """Check whether internal cell boundaries are mostly background.

    This allows intentionally empty cells inside a valid grid, as long as the
    actual cut lines remain clean. A tiny 3-pixel window tolerates minor edge
    bleed from anti-aliasing or loose particles.
    """
    length = len(values)
    if parts < 1 or length % parts:
        return None
    if parts == 1:
        return []
    peak = max(values, default=0)
    if peak <= 0:
        return None
    cell = length // parts
    threshold = max(2.0, peak * 0.03)
    scores: list[float] = []
    for index in range(1, parts):
        cut = index * cell
        window = values[max(0, cut - 1):min(length, cut + 2)]
        boundary = max(window, default=0)
        if boundary > threshold:
            return None
        scores.append(max(0.0, 1.0 - (boundary / peak)))
    return scores


def cell_occupancies(mask: Image.Image, columns: int, rows: int) -> list[float] | None:
    """Mean foreground occupancy per grid cell, normalized to 0..1."""
    if mask.width % columns or mask.height % rows:
        return None
    cell_w = mask.width // columns
    cell_h = mask.height // rows
    occupancies: list[float] = []
    for row in range(rows):
        for column in range(columns):
            cell = mask.crop((column * cell_w, row * cell_h,
                              (column + 1) * cell_w, (row + 1) * cell_h))
            occupancies.append(ImageStat.Stat(cell).mean[0] / 255)
    return occupancies


def evaluate_grid(mask: Image.Image, columns: int, rows: int) -> tuple[float, int] | None:
    """Score one regular grid candidate conservatively.

    A valid candidate needs clean internal cut lines plus enough occupied cells.
    Some empty cells are allowed so that sparse or padded sheets are still
    accepted, but grids with too many blanks are rejected as likely false hits.
    Higher scores are better.
    """
    if not MIN_SHEET_FRAMES <= columns * rows <= MAX_SHEET_FRAMES:
        return None
    if mask.width % columns or mask.height % rows:
        return None

    x_values = list(mask.resize((mask.width, 1), Image.Resampling.BOX).tobytes())
    y_values = list(mask.resize((1, mask.height), Image.Resampling.BOX).tobytes())
    x_scores = boundary_scores(x_values, columns)
    y_scores = boundary_scores(y_values, rows)
    if x_scores is None or y_scores is None:
        return None

    occupancies = cell_occupancies(mask, columns, rows)
    if not occupancies:
        return None
    maximum = max(occupancies)
    if maximum <= 0:
        return None
    occupied_threshold = max(0.005, maximum * 0.04)
    occupied = [value for value in occupancies if value >= occupied_threshold]
    blank_cells = len(occupancies) - len(occupied)
    if len(occupied) < MIN_SHEET_FRAMES:
        return None
    if blank_cells > max(2, len(occupancies) // 3):
        return None

    # Prefer grids with more confirmed cuts/cells, while penalizing excess blanks.
    score = (sum(x_scores) + sum(y_scores)
             + len(occupancies) * 0.15
             - blank_cells * 0.4)
    return score, blank_cells


def detect_grid(image: Image.Image, path: Path) -> Grid:
    """Use explicit name metadata first, otherwise conservative image analysis.

    Pixel data alone cannot determine every possible sheet layout. Ambiguous
    sheets are deliberately rejected. An explicit suffix such as _4x4 provides
    a deterministic, non-CLI fallback, including sheets with intentional blanks.
    Content-based detection also permits a small number of empty cells when the
    regular cut lines are still clear.
    """
    named = grid_from_name(path, image.size)
    if named is not None:
        return named
    try:
        mask, method = foreground_mask(image)
        candidates: list[tuple[float, int, Grid]] = []
        for columns in range(1, MAX_SHEET_FRAMES + 1):
            if image.width % columns:
                continue
            for rows in range(1, MAX_SHEET_FRAMES + 1):
                if image.height % rows:
                    continue
                result = evaluate_grid(mask, columns, rows)
                if result is None:
                    continue
                score, blank_cells = result
                candidates.append((score, blank_cells, Grid(columns, rows, f"Bildanalyse: {method}")))

        if not candidates:
            raise ConversionError("Kein eindeutig passendes, gleichmaessiges Raster mit 3 bis 64 Zellen.")

        candidates.sort(key=lambda item: (item[0], item[2].count, -item[1], item[2].columns, item[2].rows),
                        reverse=True)
        best_score, best_blanks, best_grid = candidates[0]
        if len(candidates) > 1:
            second_score = candidates[1][0]
            if best_score - second_score < 0.40:
                names = ", ".join(f"{g.columns}x{g.rows}" for _, _, g in candidates[:6])
                raise ConversionError(f"Mehrere plausible Raster: {names}.")
        return best_grid
    except ConversionError as exc:
        raise ConversionError(
            f"{exc} Datei uebersprungen. Bei bekanntem Raster z.B. --grid 4x4 verwenden "
            "oder _4x4 / _2x3 im Namen ergaenzen.") from exc


def split_sheet(image: Image.Image, grid: Grid) -> list[Image.Image]:
    """Split the sheet into equal cells; later filtering may drop blank padding cells."""
    if image.width % grid.columns or image.height % grid.rows:
        raise ConversionError("Bildmasse sind nicht durch das erkannte Raster teilbar.")
    width, height = image.width // grid.columns, image.height // grid.rows
    return [image.crop(((i % grid.columns) * width, (i // grid.columns) * height,
                        (i % grid.columns + 1) * width, (i // grid.columns + 1) * height))
            for i in range(grid.count)]


def frame_has_visible_content(frame: Image.Image) -> bool:
    """Treat fully transparent cells as padding, not animation frames."""
    alpha = frame.getchannel("A")
    mask = alpha.point([0] * ALPHA_THRESHOLD + [255] * (256 - ALPHA_THRESHOLD))
    return mask.getbbox() is not None


def prune_empty_frames(frames: Sequence[Image.Image]) -> list[Image.Image]:
    """Drop fully transparent padding cells, but never return an empty list."""
    kept = [frame for frame in frames if frame_has_visible_content(frame)]
    return kept or list(frames)


def frame_durations(count: int, fps: int) -> list[int]:
    """Distribute GIF's 10-ms timing error instead of rounding every frame.

    The cumulative timeline differs from the ideal by at most 5 ms. For very
    short loops an exactly matching average FPS is not always representable.
    """
    if fps not in FPS_CHOICES or count < 1:
        raise ConversionError("Ungueltige Framezahl oder FPS.")
    endpoints = [(100 * i + fps // 2) // fps for i in range(count + 1)]
    return [(endpoints[i + 1] - endpoints[i]) * 10 for i in range(count)]


def shared_palette(frames: Sequence[Image.Image]) -> tuple[Image.Image, list[int]]:
    """Use one palette for the whole animation; bounded sampling avoids a huge atlas."""
    per_frame = max(1, PALETTE_SAMPLE_PIXELS // len(frames))
    samples: list[Image.Image] = []
    for frame in frames:
        factor = min(1.0, math.sqrt(per_frame / (frame.width * frame.height)))
        size = (max(1, int(frame.width * factor)), max(1, int(frame.height * factor)))
        sample = frame.resize(size, Image.Resampling.NEAREST)
        rgb = sample.convert("RGB")
        invisible = sample.getchannel("A").point([255] * ALPHA_THRESHOLD + [0] * (256 - ALPHA_THRESHOLD))
        rgb.paste((0, 0, 0), (0, 0), invisible)
        samples.append(rgb)
    # Frames always share a canvas, so sampled dimensions match too.
    sample_w, sample_h = samples[0].size
    columns = max(1, math.ceil(math.sqrt(len(samples))))
    rows = math.ceil(len(samples) / columns)
    atlas = Image.new("RGB", (columns * sample_w, rows * sample_h))
    for i, sample in enumerate(samples):
        atlas.paste(sample, ((i % columns) * sample_w, (i // columns) * sample_h))
    palette = atlas.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    colors = list((palette.getpalette() or [])[:765])
    colors.extend([0] * (765 - len(colors)))
    colors.extend(colors[:3])  # Index 255 is reserved exclusively for transparency.
    palette.putpalette(colors)
    return palette, colors


def save_gif(frames: Sequence[Image.Image], output: Path, fps: int) -> GifResult:
    """Atomic write: an old result survives any conversion/validation error."""
    if not frames:
        raise ConversionError("Keine Frames vorhanden.")
    if len({frame.size for frame in frames}) != 1:
        raise ConversionError("Alle Einzelbilder muessen dieselbe Bildgroesse haben.")
    width, height = frames[0].size
    if width > 65535 or height > 65535:
        raise ConversionError("GIF unterstuetzt hoechstens 65535 Pixel pro Bildachse.")
    if width * height * len(frames) > MAX_SEQUENCE_PIXELS:
        raise ConversionError(f"Animation zu gross: Schutzgrenze {MAX_SEQUENCE_PIXELS:,} Quellpixel.")
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ConversionError("Ausgabe ist ein Link oder kein regulaerer Dateipfad; wird nicht ersetzt.")
    durations = frame_durations(len(frames), fps)
    palette, colors = shared_palette(frames)
    indexed: list[Image.Image] = []
    for frame in frames:
        rgb = frame.convert("RGB")
        image = rgb.quantize(palette=palette, dither=Image.Dither.NONE)
        image = image.point([*range(255), 0])
        image.putpalette(colors)
        invisible = frame.getchannel("A").point(
            [255] * ALPHA_THRESHOLD + [0] * (256 - ALPHA_THRESHOLD))
        image.paste(255, (0, 0), invisible)
        image.info.clear()
        indexed.append(image)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".pyimagegif_", suffix=".tmp",
                                         dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
        indexed[0].save(temporary, format="GIF", save_all=True,
                        append_images=indexed[1:], duration=durations,
                        loop=0, disposal=2, optimize=False,
                        transparency=255, background=255,
                        comment=json.dumps({"pyimagegif": 1, "source_frames": len(frames),
                                            "fps": fps}, separators=(",", ":")).encode("ascii"))
        # Pillow may combine identical adjacent frames; their duration must remain.
        with Image.open(temporary) as check:
            stored_frames = getattr(check, "n_frames", 1)
            stored_duration = 0
            if check.size != (width, height) or check.info.get("loop") != 0:
                raise ConversionError("GIF-Pruefung fehlgeschlagen: Bildgroesse oder Schleife.")
            for i in range(stored_frames):
                check.seek(i)
                check.load()
                stored_duration += check.info.get("duration", 0)
            if stored_duration != sum(durations):
                raise ConversionError("GIF-Pruefung fehlgeschlagen: Abspieldauer stimmt nicht.")
        os.replace(temporary, output)
        temporary = None
        return GifResult(len(frames), stored_frames, stored_duration)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def plan_sheet_outputs(files: Sequence[Path], fps: int) -> dict[Path, Path]:
    """Resolve equal stems across formats; refuse residual naming collisions."""
    counts = Counter(path.stem for path in files)
    outputs: dict[Path, Path] = {}
    used: set[Path] = set()
    for path in files:
        stem = path.stem if counts[path.stem] == 1 else f"{path.stem}_{path.suffix[1:].lower()}"
        output = path.with_name(f"{stem}_{fps}fps.gif")
        if output in used:
            raise ConversionError(f"Ausgabenamen kollidieren: {output.name}. Quelldateien eindeutig benennen.")
        used.add(output)
        outputs[path] = output
    return outputs


def result_text(result: GifResult, fps: int) -> str:
    text = f"{result.source_frames} Quellframes | {fps} FPS | {result.duration_ms} ms"
    if result.stored_frames != result.source_frames:
        text += f" | {result.stored_frames} GIF-Bilder (identische Frames zeitlich zusammengefasst)"
    return text


def convert_sheet(path: Path, output: Path, fps: int,
                  manual_grid: Grid | None = None, *, keep_empty: bool = False) -> tuple[Grid, GifResult]:
    """Keep image allocations local, including when a file raises an error."""
    image = load_image(path)
    grid = manual_grid if manual_grid is not None else detect_grid(image, path)
    if manual_grid is not None and (image.width % grid.columns or image.height % grid.rows):
        raise ConversionError(
            f"--grid {grid.columns}x{grid.rows} passt nicht zu {image.width}x{image.height} Pixeln: "
            "Bildmasse muessen ohne Rest durch Spalten und Zeilen teilbar sein.")
    frames = split_sheet(image, grid)
    if not keep_empty:
        frames = prune_empty_frames(frames)
    del image
    return grid, save_gif(frames, output, fps)


def reusable_gif(source: Path, output: Path, fps: int, grid: Grid | None,
                 *, keep_empty: bool = False) -> bool:
    """Reuse only readable, current exports with matching dimensions and FPS."""
    if output.is_symlink() or not output.is_file() or output.stat().st_mtime_ns < source.stat().st_mtime_ns:
        return False
    try:
        metadata = read_gif_for_gallery(output)
        with load_image(source) as image:
            grid = grid or detect_grid(image, source)
            expected = (image.width // grid.columns, image.height // grid.rows)
            if image.width % grid.columns or image.height % grid.rows:
                return False
        with Image.open(output) as image:
            for index in range(image.n_frames):
                image.seek(index)
                image.load()
        return (metadata["exportFps"] == fps
                and (not keep_empty or metadata["logicalFrames"] == grid.count)
                and expected == (metadata["width"], metadata["height"]))
    except (OSError, ValueError, SyntaxError, EOFError, Image.DecompressionBombError,
            Image.DecompressionBombWarning):
        return False


def run_sheets(files: Sequence[Path], fps: int, manual_grid: Grid | None = None,
               *, skip_existing: bool = False, keep_empty: bool = False,
               overwrite: bool = False, dry_run: bool = False) -> int:
    outputs = plan_sheet_outputs(files, fps)
    ok, failed = 0, 0
    for i, path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {path.name}", flush=True)
        try:
            output_policy.validate(outputs[path])
            if outputs[path].exists() and not overwrite:
                output_policy.should_write(outputs[path], dry_run=dry_run)
                if not reusable_gif(path, outputs[path], fps, manual_grid, keep_empty=keep_empty):
                    raise ConversionError("Vorhandenes GIF ist ungültig, veraltet oder passt nicht zur Quelle; "
                                          "bleibt unverändert. Zum Neuerstellen --overwrite verwenden.")
                ok += 1
                continue
            if dry_run:
                with load_image(path) as source:
                    grid = manual_grid or detect_grid(source, path)
                    split_sheet(source, grid)
                output_policy.should_write(outputs[path], overwrite=overwrite, dry_run=True)
                ok += 1
                continue
            grid, result = convert_sheet(path, outputs[path], fps, manual_grid, keep_empty=keep_empty)
            print(f"  OK: {grid.columns}x{grid.rows} | {grid.source} | {result_text(result, fps)}")
            print(f"  -> {outputs[path].name}", flush=True)
            ok += 1
        except (OSError, ValueError, SyntaxError, MemoryError,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            print(f"  WARNUNG: {exc}", flush=True)
            failed += 1
    print(f"\nErgebnis: {ok} GIF(s) {'geprüft' if dry_run else 'erstellt oder behalten'}, "
          f"{failed} Datei(en) nicht verarbeitet.")
    return 1 if failed else 0


def run_solo(files: Sequence[Path], directory: Path, fps: int, *, overwrite: bool = False,
             dry_run: bool = False) -> int:
    if len(files) < 2:
        raise ConversionError("Solo benoetigt mindestens zwei statische Einzelbilder.")
    # Preflight every header first, rather than silently dropping invalid frames.
    expected_size: tuple[int, int] | None = None
    first_name = ""
    for path in files:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                if getattr(image, "n_frames", 1) != 1:
                    raise ConversionError(f"Solo abgebrochen: {path.name} ist animiert oder mehrseitig.")
                if expected_size is None:
                    expected_size, first_name = image.size, path.name
                elif image.size != expected_size:
                    raise ConversionError(
                        f"Solo abgebrochen: {path.name} hat {image.width}x{image.height} Pixel; "
                        f"{first_name} hat {expected_size[0]}x{expected_size[1]}. Keine automatische Skalierung.")
    assert expected_size is not None
    if expected_size[0] * expected_size[1] * len(files) > MAX_SEQUENCE_PIXELS:
        raise ConversionError(f"Solo zu gross: Schutzgrenze {MAX_SEQUENCE_PIXELS:,} Quellpixel.")
    print("Solo-Reihenfolge (natuerlich nach Dateiname aufsteigend):", flush=True)
    frames = []
    for i, path in enumerate(files, 1):
        print(f"  {i:>4}. {path.name}", flush=True)
        frames.append(load_image(path))
    folder = directory.name or "root"
    output = directory / f"{folder}_solo_{fps}fps.gif"
    if not output_policy.should_write(output, overwrite=overwrite, dry_run=dry_run):
        return 0
    result = save_gif(frames, output, fps)
    print(f"\nOK: {result_text(result, fps)}\n-> {output.name}")
    return 0


# --------------------------- Offline HTML comparison ---------------------------

HTML_DEFAULT = "gif-vergleich.html"
MAX_HTML_FRAMES = 4096
MAX_HTML_GIF_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class GalleryResult:
    included: int
    skipped: int
    size_bytes: int


def discover_gifs(directory: Path) -> list[Path]:
    """Read finished GIFs, including earlier runs; never recurse or follow links."""
    return sorted(
        (p for p in directory.iterdir()
         if not p.name.startswith(".") and not p.is_symlink()
         and p.is_file() and p.suffix.casefold() == ".gif"),
        key=natural_key,
    )


def relative_url(path: Path, output: Path) -> str:
    return quote(Path(os.path.relpath(path.absolute(), output.parent.absolute())).as_posix(), safe="/")


def cleanup_legacy_html_assets(output: Path) -> None:
    """Remove only unchanged content-addressed images from the old HTML cache.

    Never recurse or follow links; preserve unrelated files and changed contents.
    Call only after the replacement HTML has been successfully published.
    """
    directory = output.with_name(output.stem + "-bilder")
    if directory.is_symlink() or not directory.is_dir():
        return
    removed = 0
    try:
        for path in directory.iterdir():
            if (path.is_symlink() or not path.is_file()
                    or re.fullmatch(r"[0-9a-f]{64}\.(?:png|gif)", path.name) is None):
                continue
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() == path.stem:
                path.unlink()
                removed += 1
        if not any(directory.iterdir()):
            directory.rmdir()
        if removed:
            print(f"HTML: {removed} alte Bildkopie(n) entfernt: {directory}", flush=True)
    except OSError as exc:
        print(f"HTML-HINWEIS: Alte Bildkopien nicht vollstaendig bereinigt: {exc}", file=sys.stderr)


def read_sheet_preview(path: Path, output: Path, fps: int = 8,
                       grid: Grid | None = None, gif_path: Path | None = None,
                       *, single_image: bool = False) -> dict:
    """Describe existing sprite cells or a whole single image without copying it."""
    if path.is_symlink() or not path.is_file():
        raise ConversionError(f"Keine regulaere Bilddatei: {path}")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if image.format not in {"PNG", "JPEG", "WEBP", "BMP"} or getattr(image, "n_frames", 1) != 1:
                raise ConversionError("Die Browser-Vorschau benoetigt ein statisches PNG, JPEG, WebP oder BMP.")
            width, height = image.size
            if width * height > MAX_SEQUENCE_PIXELS:
                raise ConversionError("Bild ueberschreitet das Pixelbudget der Vorschau.")
            grid = Grid(1, 1, "Einzelbild") if single_image else grid or grid_from_name(path, image.size)
            if grid is None:
                match = re.fullmatch(r"spritesheet-frame?([0-9]+)", path.parent.name, re.IGNORECASE)
                layouts = {8: (4, 2), 10: (5, 2), 12: (4, 3), 14: (7, 2), 16: (4, 4)}
                layout = layouts.get(int(match[1])) if match else None
                if layout is None and match:
                    side = math.isqrt(int(match[1]))
                    if side * side == int(match[1]):
                        layout = (side, side)
                if layout:
                    grid = Grid(*layout, "Frame-Ordner")
            if grid is None:
                with load_image(path) as pixels:
                    grid = detect_grid(pixels, path)
            if ((not single_image and not MIN_SHEET_FRAMES <= grid.count <= MAX_SHEET_FRAMES)
                    or width % grid.columns or height % grid.rows):
                raise ConversionError(f"Raster {grid.columns}x{grid.rows} passt nicht zum Spritesheet: {path.name}")
            image.verify()
    if fps not in FPS_CHOICES:
        raise ConversionError("Ungueltige Vorschau-FPS.")
    has_gif = not single_image and gif_path is not None and not gif_path.is_symlink() and gif_path.is_file()
    durations = [1000 / fps] * grid.count
    return {
        "name": path.name, "width": width // grid.columns, "height": height // grid.rows,
        "bytes": path.stat().st_size, "sheet": relative_url(path, output),
        "columns": grid.columns, "rows": grid.rows,
        "gif": relative_url(gif_path, output) if has_gif else None,
        "gifName": gif_path.name if has_gif else None,
        "durations": durations, "frameMap": list(range(grid.count)),
        "storedFrames": grid.count, "logicalFrames": grid.count,
        "durationMs": sum(durations), "exportFps": None, "previewFps": fps,
        "filenameFps": None, "notes": [],
    }


def recover_source_timeline(comment: object, stored_durations: list[int]) -> tuple[list[int], list[int], int | None]:
    """Recover logical frames only from validated metadata written by this script.

    Pillow can merge adjacent equal frames. Each stored frame boundary must match
    a source boundary; otherwise use the actual GIF frames and timings instead.
    A filename is never treated as verified timing metadata.
    """
    fallback = (stored_durations, list(range(len(stored_durations))), None)
    if not isinstance(comment, bytes) or len(comment) > 4096:
        return fallback
    try:
        metadata = json.loads(comment.decode("ascii"))
    except (ValueError, UnicodeError):
        return fallback
    if not isinstance(metadata, dict) or metadata.get("pyimagegif") != 1:
        return fallback
    count, fps = metadata.get("source_frames"), metadata.get("fps")
    if (type(count) is not int or not 1 <= count <= 100_000
            or type(fps) is not int or fps not in FPS_CHOICES):
        return fallback
    durations = frame_durations(count, fps)
    if sum(durations) != sum(stored_durations):
        return fallback
    frame_map: list[int] = []
    cursor = 0
    for stored_index, target in enumerate(stored_durations):
        elapsed = 0
        while cursor < count and elapsed < target:
            elapsed += durations[cursor]
            frame_map.append(stored_index)
            cursor += 1
        if elapsed != target:
            return fallback
    if cursor != count:
        return fallback
    return durations, frame_map, fps


def read_gif_for_gallery(path: Path, output: Path | None = None) -> dict:
    """Read GIF timing metadata and link the existing file; never export frames."""
    if path.is_symlink() or not path.is_file():
        raise ConversionError(f"Kein regulaeres GIF: {path}")
    size_bytes = path.stat().st_size
    if size_bytes > MAX_HTML_GIF_BYTES:
        raise ConversionError("GIF zu gross fuer die HTML-Vorschau (max. 64 MiB pro GIF).")
    stored_durations: list[int] = []
    notes: list[str] = []
    fallback_count = 0
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as gif:
            if gif.format != "GIF":
                raise ConversionError("Dateiendung .gif, aber der Inhalt ist kein GIF.")
            width, height = gif.size
            comment = gif.info.get("comment")
            for index in range(MAX_HTML_FRAMES + 1):
                try:
                    gif.seek(index)
                except EOFError:
                    break
                if index == MAX_HTML_FRAMES:
                    raise ConversionError(f"Mehr als {MAX_HTML_FRAMES} gespeicherte GIF-Bilder.")
                if width * height * (index + 1) > MAX_SEQUENCE_PIXELS:
                    raise ConversionError("GIF ueberschreitet das Pixelbudget der HTML-Vorschau.")
                if gif.size != (width, height):
                    raise ConversionError("Wechselnde GIF-Leinwandgroesse wird nicht unterstuetzt.")
                duration = gif.info.get("duration", 0)
                if not isinstance(duration, (int, float)) or duration <= 0:
                    duration = 100
                    fallback_count += 1
                stored_durations.append(int(duration))
    if not stored_durations:
        raise ConversionError("Keine lesbaren GIF-Bilder.")
    if fallback_count:
        notes.append(f"{fallback_count} Bild(er) ohne positive Dauer: Zeitangabe verwendet jeweils 100 ms.")
    durations, frame_map, export_fps = recover_source_timeline(comment, stored_durations)
    if fallback_count:
        durations, frame_map, export_fps = stored_durations, list(range(len(stored_durations))), None
    filename_match = re.search(r"_([0-9]+)fps$", path.stem, re.IGNORECASE)
    filename_fps = int(filename_match[1]) if filename_match and len(filename_match[1]) <= 4 else None
    return {
        "name": path.name, "width": width, "height": height,
        "bytes": size_bytes, "sheet": None, "gif": relative_url(path, output or path),
        "gifName": path.name, "durations": durations, "frameMap": frame_map,
        "storedFrames": len(stored_durations), "logicalFrames": len(durations),
        "durationMs": sum(durations), "exportFps": export_fps,
        "filenameFps": filename_fps, "notes": notes,
    }


def gallery_preview(path: Path, output: Path, grid: Grid | None = None) -> dict:
    """Use the matching source sheet when available, otherwise link a native GIF."""
    metadata = read_gif_for_gallery(path, output)
    stem = re.sub(r"_[0-9]+fps$", "", path.stem, flags=re.IGNORECASE)
    sources = [p for p in path.parent.iterdir() if p.is_file() and not p.is_symlink()
               and p.stem == stem and p.suffix.lower() in EXTENSIONS]
    if len(sources) == 1:
        try:
            if grid is None:
                with Image.open(sources[0]) as source:
                    columns, column_rest = divmod(source.width, metadata["width"])
                    rows, row_rest = divmod(source.height, metadata["height"])
                if not column_rest and not row_rest and MIN_SHEET_FRAMES <= columns * rows <= MAX_SHEET_FRAMES:
                    grid = Grid(columns, rows, "GIF-Framegroesse")
            fps = metadata["exportFps"] or metadata["filenameFps"]
            item = read_sheet_preview(sources[0], output, fps if fps in FPS_CHOICES else 8, grid, path)
            if (item["width"], item["height"]) != (metadata["width"], metadata["height"]):
                raise ConversionError("Spritesheet und GIF haben unterschiedliche Frame-Groessen.")
            item.update({key: metadata[key] for key in ("name", "exportFps", "filenameFps", "storedFrames")})
            if metadata["exportFps"] and item["logicalFrames"] == metadata["logicalFrames"]:
                item["durations"] = metadata["durations"]
                item["durationMs"] = metadata["durationMs"]
            elif item["logicalFrames"] != metadata["logicalFrames"]:
                item["notes"].append("Die Spritesheet-Vorschau zeigt alle Rasterzellen, auch im GIF ausgelassene Leerzellen.")
            return item
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as exc:
            metadata["notes"].append(f"Spritesheet-Vorschau nicht verfuegbar: {exc}")
    metadata["notes"].append("Ohne passendes Spritesheet spielt der Browser das Original-GIF ab; FPS- und Einzelbildregler gelten dafuer nicht.")
    return metadata


def validate_html_output(output: Path) -> None:
    if output.suffix.casefold() not in {".html", ".htm"}:
        raise ConversionError("HTML-Ausgabe muss auf .html oder .htm enden; andere Dateien werden nicht ersetzt.")
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ConversionError("HTML-Ausgabe ist ein Link oder kein regulaerer Dateipfad.")
    if not output.parent.is_dir():
        raise ConversionError(f"HTML-Ausgabeordner existiert nicht: {output.parent}")


def script_safe_json(value: object) -> str:
    """A filename such as </script> must never escape the JSON script element."""
    return (json.dumps(value, ensure_ascii=True, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def build_html_gallery(directory: Path, output: Path, grid: Grid | None = None, *,
                       overwrite: bool = False, dry_run: bool = False,
                       gif_paths: Sequence[Path] | None = None) -> GalleryResult:
    """Refresh an offline HTML snapshot linking existing spritesheets and GIFs."""
    if not output_policy.should_write(output, overwrite=overwrite, dry_run=dry_run):
        return GalleryResult(0, 0, output.stat().st_size if output.exists() else 0)
    validate_html_output(output)
    paths = discover_gifs(directory) if gif_paths is None else list(gif_paths)
    if not paths:
        raise ConversionError("Keine GIFs im aktuellen Ordner fuer die HTML-Vergleichsansicht gefunden.")
    items: list[dict] = []
    skipped: list[dict] = []
    for i, path in enumerate(paths, 1):
        print(f"[HTML {i}/{len(paths)}] {path.name}", flush=True)
        try:
            item = gallery_preview(path, output, grid)
            items.append(item)
        except (OSError, ValueError, SyntaxError, MemoryError,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            skipped.append({"name": path.name, "reason": str(exc)})
            print(f"  HTML-WARNUNG: {exc}", flush=True)
    if not items:
        raise ConversionError("Keine GIFs konnten gelesen werden; vorhandene HTML-Datei bleibt erhalten.")
    payload = {"schema": 1, "folder": directory.name or "root",
               "created": datetime.now().astimezone().isoformat(timespec="seconds"),
               "items": items, "skipped": skipped, "fpsChoices": FPS_CHOICES}
    html_text = HTML_TEMPLATE.replace("__PYIMAGEGIF_DATA__", script_safe_json(payload))
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         prefix=".pyimagegif_html_", suffix=".tmp",
                                         dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(html_text)
        validate_html_output(output)
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    result = GalleryResult(len(items), len(skipped), output.stat().st_size)
    print(f"\nHTML: {result.included} GIF(s), {result.skipped} uebersprungen "
          f"| {result.size_bytes / 1024 / 1024:.2f} MiB\n-> {output}", flush=True)
    if overwrite:
        cleanup_legacy_html_assets(output)
    return result


HTML_TEMPLATE = r'''
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' file: data: blob:; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>PyImgGif · GIF-Vergleich</title>
<style>
:root{color-scheme:dark;--page:#101316;--panel:#191e23;--line:#303840;--muted:#a7b2bc;--text:#eef3f7;--accent:#b8ed88;--accent-ink:#182510;--radius:16px;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--text);font-size:14px;line-height:1.5}button,input,select{font:inherit}button,select,input[type=number],input[type=search]{border:1px solid var(--line);border-radius:8px;background:#232a30;color:var(--text);min-height:38px;padding:7px 10px}button{cursor:pointer;font-weight:600}button:hover:not(:disabled),select:hover{border-color:#8b9aab}button:disabled{opacity:.45;cursor:default}button.primary{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}input[type=range],input[type=checkbox]{accent-color:var(--accent)}input[type=range]{min-width:0;width:100%;cursor:pointer}input[type=checkbox]{width:17px;height:17px}input[type=number]{width:78px}input[type=search]{width:100%;min-width:160px}label{display:flex;gap:7px;align-items:center}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:3px}[hidden]{display:none!important}
.shell{max-width:1536px;margin:auto;padding:28px 36px 38px}.topline{display:flex;align-items:center;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);padding-bottom:18px}.brand{font-weight:750;letter-spacing:-.5px;font-size:20px}.brand em{font-style:normal;color:var(--accent)}.micro{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;color:var(--muted);font-weight:650}.offline{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:12px}.dot{width:7px;height:7px;border-radius:50%;background:var(--accent)}header{display:flex;justify-content:space-between;align-items:end;gap:24px;padding:30px 0 24px}h1{font-size:clamp(29px,3.4vw,44px);letter-spacing:-1.7px;line-height:1.1;margin:8px 0 12px}header p{margin:0;color:var(--muted);max-width:690px}.countbox{text-align:right;white-space:nowrap}.countbox strong{font-size:38px;line-height:1;letter-spacing:-1px}.countbox span{display:block;color:var(--muted);font-size:12px;margin-top:8px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius)}.transport{padding:20px}.section-title{display:flex;justify-content:space-between;gap:14px;align-items:center;margin-bottom:14px}.section-title .micro{color:var(--accent)}.status{color:var(--muted);font-size:12px}.transport-grid{display:grid;grid-template-columns:auto minmax(250px,1fr) minmax(250px,1fr);gap:24px;align-items:end}.buttons{display:flex;gap:8px;flex-wrap:wrap}.field-title{display:block;font-size:12px;color:var(--muted);margin-bottom:7px}.inline{display:flex;gap:8px;align-items:center}.inline select{flex:1;min-width:0}.speed-line{display:flex;gap:14px;align-items:center;min-height:38px}.readout{color:var(--accent);font-variant-numeric:tabular-nums;font-weight:700;min-width:47px;text-align:right}.transport-foot{display:flex;justify-content:space-between;gap:16px;padding-top:15px;margin-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}.transport-foot p{margin:0}.reset{padding:0;min-height:auto;border:0;background:none;color:var(--muted);white-space:nowrap}.toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:24px 0 16px}.search{flex:1;min-width:180px}.toolbar label{font-size:12px;color:var(--muted);white-space:nowrap}.toolbar select{max-width:170px}.selection-row{display:flex;justify-content:space-between;gap:15px;align-items:center;margin-bottom:14px;color:var(--muted);font-size:12px}.selection-row button{min-height:28px;font-size:12px;padding:3px 9px;font-weight:500}.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,350px),1fr));gap:18px;align-items:start}.card{overflow:hidden;min-width:0}.card-head{padding:15px 17px 13px}.card-title{display:flex;align-items:start;gap:10px;justify-content:space-between}.card-title label{min-width:0;align-items:start}.card-title input{flex:none;margin-top:4px}.card h2{font-size:14px;font-weight:650;line-height:1.6;margin:0;overflow-wrap:anywhere}.badge{flex:none;border:1px solid #49633b;background:#283821;color:var(--accent);border-radius:5px;padding:3px 7px;font-size:10px;font-weight:700;letter-spacing:.4px}.meta{color:var(--muted);font-size:11px;margin:8px 0 0 27px;font-variant-numeric:tabular-nums}.stage{position:relative;height:228px;display:flex;overflow:auto;border-top:1px solid var(--line);border-bottom:1px solid var(--line);background-color:#252c32;background-image:linear-gradient(45deg,#2e363d 25%,transparent 25%),linear-gradient(-45deg,#2e363d 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#2e363d 75%),linear-gradient(-45deg,transparent 75%,#2e363d 75%);background-size:24px 24px;background-position:0 0,0 12px,12px -12px,-12px 0}.canvas-wrap{margin:auto;padding:16px;flex:none;display:flex}.stage canvas{display:block;image-rendering:pixelated}.stage-label{position:absolute;left:12px;top:10px;font-size:10px;letter-spacing:1px;color:#bec7cf;background:#14191ed9;border-radius:4px;padding:3px 6px;pointer-events:none}.stage-loading{position:absolute;inset:0;display:grid;place-items:center;color:var(--muted);background:#15191ed9}.card-body{padding:14px 17px 16px}.fps-row{display:flex;gap:12px;justify-content:space-between;font-size:12px;font-variant-numeric:tabular-nums}.fps-row .actual{font-weight:650;color:var(--accent)}.fps-row .original{color:var(--muted)}.frame-row{display:flex;align-items:center;gap:9px;margin:10px 0 13px}.card-play{font-size:11px;min-height:29px;padding:3px 8px;min-width:52px}.frame-state{white-space:nowrap;color:var(--muted);font-size:11px;min-width:49px;text-align:right;font-variant-numeric:tabular-nums}.card-settings{display:grid;grid-template-columns:1fr 65px 70px;gap:8px}.card-settings label{display:block;font-size:10px;color:var(--muted)}.card-settings input,.card-settings select{width:100%;min-height:33px;font-size:12px;margin-top:5px;padding:5px 6px}.card-settings input:disabled{opacity:.45}.card-footer{display:flex;justify-content:space-between;gap:14px;align-items:center;margin-top:14px;font-size:11px}.info-details{border-top:1px solid var(--line);margin-top:12px;padding-top:10px;font-size:11px;color:var(--muted)}summary{cursor:pointer}.info-details p{margin:8px 0}.native img{display:block;max-width:100%;max-height:220px;image-rendering:pixelated;margin:10px auto}.warning{color:#f0c27c;font-size:12px}.empty{padding:40px;text-align:center;color:var(--muted)}.overlay-panel{overflow:hidden;margin-bottom:18px}.overlay-head{padding:18px 20px;display:flex;justify-content:space-between;gap:16px;align-items:center}.overlay-head h2{margin:0;font-size:16px}.overlay-head p{margin:4px 0 0;font-size:12px;color:var(--muted)}.overlay-head label{min-width:220px;font-size:12px;color:var(--muted)}.overlay-stage{height:370px}.overlay-foot{padding:12px 20px;color:var(--muted);font-size:12px}.footer{margin-top:25px;border-top:1px solid var(--line);padding-top:18px;display:flex;justify-content:space-between;gap:18px;color:var(--muted);font-size:11px}.footer p{margin:0;max-width:950px}.help{margin-top:17px;color:var(--muted);font-size:12px}.help p{max-width:1000px}.skip-box{padding:16px 20px;margin-bottom:18px}body[data-background=light] .stage{background:#edf0f2}body[data-background=dark] .stage{background:#101316}body[data-pixel=false] canvas{image-rendering:auto}kbd{padding:1px 4px;border:1px solid var(--line);border-radius:4px;font:10px ui-monospace,monospace}.load-error{opacity:.7}
@media(min-width:1350px){.gallery{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:1120px){.transport-grid{grid-template-columns:1fr 1fr}.transport-grid>.buttons{grid-column:1/-1}.toolbar{gap:9px}.toolbar .search{flex-basis:100%}}@media(max-width:620px){.shell{padding:18px 16px 26px}header{align-items:start;padding:24px 0}.countbox{display:none}h1{letter-spacing:-1px}.transport{padding:16px}.transport-grid{grid-template-columns:1fr;gap:16px}.transport-foot,.footer{flex-direction:column}.toolbar label{flex:1}.toolbar select{width:100%;max-width:none}.selection-row{align-items:start;flex-wrap:wrap}.overlay-head{align-items:start;flex-direction:column}.offline{font-size:10px}.topline{gap:8px}.micro{font-size:10px}.card-settings{grid-template-columns:1fr 65px 70px}}
</style>
</head>
<body data-background="checker" data-pixel="true">
<div class="shell">
<div class="topline"><div class="brand">PyImgGif<em> / </em><span class="micro">Motion Lab</span></div><div class="offline"><span class="dot"></span>Offline · Vorhandene Bilddateien</div></div>
<header><div><div class="micro">GIF-Vergleich / <span id="folder"></span></div><h1>Animationen. Im Vergleich.</h1><p>Vorhandene Spritesheets abspielen, FPS angleichen und Bewegungen nebeneinander vergleichen. Original-GIFs lassen sich in den Details öffnen.</p></div><div class="countbox"><strong id="totalCount">0</strong><span>GIFs in dieser Ansicht</span></div></header>
<section class="panel transport" aria-label="Gemeinsame Wiedergabesteuerung">
<div class="section-title"><span class="micro">Gemeinsame Steuerung</span><span id="loadStatus" class="status" role="status">Bilder werden geladen …</span></div>
<div class="transport-grid">
<div class="buttons"><button id="play" class="primary" disabled>Alle abspielen</button><button id="sync" disabled title="Alle Animationen gleichzeitig bei Frame 1 starten">Synchron starten</button><button id="prev" disabled title="Alle Animationen ein Frame zurück" aria-label="Alle ein Frame zurück">←</button><button id="next" disabled title="Alle Animationen ein Frame weiter" aria-label="Alle ein Frame weiter">→</button></div>
<div><label class="field-title" for="globalMode">Timing für alle · einzeln überschreibbar</label><div class="inline"><select id="globalMode"><option value="original">Vorgabe</option><option value="fixed">Feste FPS</option></select><select id="globalFps" disabled aria-label="Gemeinsame Vorschau-FPS"></select></div></div>
<div><label class="field-title" for="globalSpeed">Gemeinsames Tempo</label><div class="speed-line"><input id="globalSpeed" type="range" min="0.1" max="4" step="0.1" value="1"><output id="globalSpeedValue" class="readout" for="globalSpeed">1.0×</output></div></div>
</div><div class="transport-foot"><p>Nur die Vorschau wird verändert. Die GIF-Dateien bleiben unverändert.</p><button id="reset" class="reset">Einstellungen zurücksetzen ↺</button></div>
</section>
<div class="toolbar" aria-label="Ansicht und Filter">
<label class="search"><input id="search" type="search" placeholder="GIFs nach Dateinamen filtern …" aria-label="GIFs nach Dateinamen filtern"></label>
<label>Ansicht <select id="view"><option value="grid">Nebeneinander</option><option value="overlay">Overlay A/B</option></select></label>
<label>Zoom <select id="zoom"><option value="fit">Einpassen</option><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option><option value="8">8×</option></select></label>
<label>Hintergrund <select id="background"><option value="checker">Schachbrett</option><option value="dark">Dunkel</option><option value="light">Hell</option></select></label>
<label><input id="pixel" type="checkbox" checked>Pixelscharf</label>
</div>
<div class="selection-row"><span id="visibleCount">0 GIFs</span><div class="inline"><label><input id="selectedOnly" type="checkbox">Nur Auswahl</label><button id="selectAll">Alle wählen</button><button id="selectNone">Auswahl leeren</button></div></div>
<div id="skipped" class="panel skip-box" hidden></div>
<section id="overlayPanel" class="panel overlay-panel" hidden aria-label="Overlay-Vergleich">
<div class="overlay-head"><div><h2>Overlay A/B</h2><p id="overlayNames">Zwei GIFs über die Checkboxen auswählen.</p></div><label for="overlayAlpha">Anteil B <input id="overlayAlpha" type="range" min="0" max="100" step="1" value="50"><output id="overlayAlphaValue">50%</output></label></div>
<div class="stage overlay-stage"><span class="stage-label">A + B · ZENTRIERT · GLEICHER PIXELMASSSTAB</span><div class="canvas-wrap"><canvas id="overlayCanvas" width="1" height="1" aria-label="Überlagerung der ersten zwei ausgewählten GIFs"></canvas></div></div>
<div class="overlay-foot">Die ersten zwei ausgewählten, geladenen GIFs werden überlagert. Ihre Regler bleiben unten erreichbar. Gleicher Start bedeutet nicht gleiche Zykluslänge.</div>
</section>
<div id="empty" class="panel empty" hidden>Keine GIFs für diesen Filter. Suche oder Auswahl ändern.</div>
<main id="gallery" class="gallery" aria-label="GIF-Vergleichskarten"></main>
<details class="help"><summary>Wie Timing, FPS und Synchronisation funktionieren</summary>
<p>Die steuerbare Vorschau zeigt die Rasterzellen der vorhandenen Spritesheets einschließlich Leerzellen. Farbänderungen durch den GIF-Export sind darin nicht sichtbar. <strong>Vorgabe</strong> verwendet bei passender Framezahl das geprüfte GIF-Quellframe-Timing; sonst die Export-FPS, die FPS aus dem Dateinamen oder 8 FPS. <strong>Feste FPS</strong> gibt jeder Rasterzelle dieselbe Dauer. Ohne passendes Spritesheet wird nur das Original-GIF ohne diese Regler angezeigt.</p>
<p><strong>Vorschau Ø FPS</strong> ist die berechnete Soll-Bildrate, keine Messung der Bildschirmfrequenz. Sie enthält das gemeinsame Tempo und den einzelnen Tempo-Faktor. Hohe Werte können mehr Bildwechsel verlangen, als der Bildschirm darstellen kann. Ein Frame-Schritt bleibt unabhängig davon exakt ein logischer Frame.</p>
<p><strong>Synchron starten</strong> setzt alle GIFs auf Frame 1 und startet sie mit demselben Zeitgeber. Unterschiedliche Bildraten, Framezahlen und Tempo-Faktoren führen weiterhin zu unterschiedlichen Zykluslängen. Für einen direkten Taktvergleich: gleiche Vorschau-FPS wählen, einzelne Regler auf „Global“ und Faktor 1 setzen, dann synchron starten.</p>
<p>Der globale Play-Button startet alle GIFs. Ein einzelner Play-Button startet bei globalem Stillstand nur diese Karte. Ziehen am Frame-Regler pausiert diese Karte. Versteckte Browser-Tabs halten die Zeit an. Bei reduzierter Bewegung im System startet die Seite pausiert. Die Original-GIF-Vorschau in den Details wird vom Browser selbst abgespielt und nicht durch diese Regler gesteuert.</p>
<p>Diese HTML-Datei ist eine Momentaufnahme. Nach weiteren Konvertierungen oder einem Aufruf mit <code>--html-only</code> die neu erzeugte Datei öffnen beziehungsweise die Seite neu laden. Es gibt keine Netzwerkzugriffe und keinen Live-Ordner-Wächter.</p>
</details>
<footer class="footer"><p>Offline nutzbar. Beim Kopieren HTML, Spritesheets und GIFs zusammenhalten. <span id="created"></span><br><span>Bedienung außerhalb der Eingabefelder: <kbd>Leertaste</kbd> Play/Pause · <kbd>←</kbd> <kbd>→</kbd> Frame-Schritt · <kbd>R</kbd> Synchron starten.</span></p><span>PyImgGif / HTML Pipeline</span></footer>
<noscript><p class="warning">JavaScript muss für die steuerbare Vergleichsansicht aktiviert sein.</p></noscript>
</div>
<script id="gif-data" type="application/json">__PYIMAGEGIF_DATA__</script>
<script>
"use strict";
(() => {
  const payload = JSON.parse(document.getElementById("gif-data").textContent);
  const $ = id => document.getElementById(id);
  const tracks = [];
  const state = {playing:false, ready:false, speed:1, mode:"original", fps:12,
    zoom:"fit", lastTimestamp:null, uiTimestamp:0, overlayKey:""};
  const number = (value, fallback, minimum, maximum) => {
    const parsed = Number(value);
    return value !== "" && Number.isFinite(parsed) ? Math.min(maximum, Math.max(minimum, parsed)) : fallback;
  };
  const format = (value, digits=2) => Number(value).toLocaleString("de-DE", {
    minimumFractionDigits:digits, maximumFractionDigits:digits});
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function selector(options, className, label) {
    const node = element("select", className);
    node.setAttribute("aria-label", label);
    options.forEach(([value, text]) => {
      const option = element("option", "", text); option.value = value; node.append(option);
    });
    return node;
  }
  function numeric(className, label, value, min, max, step) {
    const node = element("input", className); node.type="number"; node.value=value;
    node.min=min; node.max=max; node.step=step; node.setAttribute("aria-label", label);
    return node;
  }
  function labelled(text, control) {
    const label = element("label", "", text); label.append(control); return label;
  }
  function effectiveMode(track) { return track.mode === "inherit" ? state.mode : track.mode; }
  function effectiveFps(track) { return track.mode === "inherit" ? state.fps : track.fps; }
  function configure(track, preserve=true) {
    const progress = preserve && track.total ? track.position / track.total : 0;
    track.starts = [];
    let total = 0;
    const fixed = effectiveMode(track) === "fixed";
    const fps = effectiveFps(track);
    for (const [index,duration] of track.item.durations.entries()) {
      // Multiplication before division avoids accumulating per-frame roundoff.
      track.starts.push(fixed ? index * 1000 / fps : total);
      if (!fixed) total += duration;
    }
    if (fixed) total = track.item.durations.length * 1000 / fps;
    track.total = total;
    track.position = Math.min(progress * total, Math.max(0,total - 0.00001));
    track.fpsInput.disabled = track.native || track.mode !== "fixed";
    track.lastFrame = -1;
  }
  function frameIndex(track) {
    // Upper bound on cumulative start times; exact boundaries select the next frame.
    let low=0, high=track.starts.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (track.starts[middle] <= track.position + 1e-7) low=middle+1;
      else high=middle;
    }
    return Math.max(0,low-1);
  }
  function fitCanvas(canvas, stage, width, height) {
    const scale = state.zoom === "fit"
      ? Math.min(Math.max(1,stage.clientWidth-34)/width,Math.max(1,stage.clientHeight-34)/height)
      : Number(state.zoom);
    canvas.style.width = `${Math.max(1,width*scale)}px`;
    canvas.style.height = `${Math.max(1,height*scale)}px`;
  }
  function resizeAll() {
    tracks.forEach(t => { if (!t.node.hidden) fitCanvas(t.canvas,t.stage,t.item.width,t.item.height); });
    const c = $("overlayCanvas");
    if (!$("overlayPanel").hidden) fitCanvas(c,c.closest(".stage"),c.width,c.height);
  }
  function draw(track, force=false) {
    if (!track.loaded) return;
    const index = frameIndex(track);
    if (index !== track.lastFrame || force) {
      track.lastFrame = index;
      const ctx = track.context;
      ctx.clearRect(0,0,track.canvas.width,track.canvas.height);
      drawCell(track,ctx,index,0,0);
      track.seek.value = index;
      track.frameState.textContent = `${index+1} / ${track.starts.length}`;
      track.node.dataset.frame = String(index);
    }
  }
  function drawCell(track,ctx,index,x,y) {
    const {width,height,columns}=track.item,cell=track.item.frameMap[index];
    ctx.drawImage(track.picture,(cell%columns)*width,Math.floor(cell/columns)*height,width,height,x,y,width,height);
  }
  function metrics(track) {
    if(track.native)return;
    const fps = track.item.logicalFrames*1000/track.total*state.speed*track.speed;
    track.actual.textContent = `Vorschau Ø ${format(fps)} FPS`;
    const running = state.playing && !track.paused;
    track.play.textContent = running ? "Pause" : "Play";
    track.play.setAttribute("aria-label",`${running ? "Pausieren" : "Abspielen"}: ${track.item.name}`);
    track.node.dataset.playing = String(running && track.loaded);
    track.node.dataset.fps = String(fps);
  }
  function render(force=false) {
    tracks.forEach(t => {draw(t,force);metrics(t);});
    $("play").textContent = state.playing ? "Alle pausieren" : "Alle abspielen";
    $("play").setAttribute("aria-pressed",String(state.playing));
    drawOverlay(force);
  }
  function playAll() {
    if (!state.ready) return;
    state.playing = !state.playing;
    if (state.playing) tracks.forEach(t => {t.paused=false;});
    state.lastTimestamp=null;
    render();
  }
  function synchronize() {
    if (!state.ready) return;
    tracks.forEach(t => {t.position=0;t.paused=false;t.lastFrame=-1;});
    state.playing=true; state.lastTimestamp=null;
    render(true);
  }
  function stepAll(direction) {
    if (!state.ready) return;
    state.playing=false; state.lastTimestamp=null;
    tracks.forEach(t => {
      const index = (frameIndex(t)+direction+t.starts.length)%t.starts.length;
      t.position=t.starts[index]; t.paused=false;
    });
    render(true);
  }
  function createTrack(item,index) {
    const track = {item,mode:"inherit",fps:12,speed:1,position:0,total:0,starts:[],
      loaded:false,paused:false,picture:null,lastFrame:-1,native:!item.sheet};
    const node = element("article","panel card"); track.node=node; node.dataset.index=index;
    const head = element("div","card-head"), title=element("div","card-title");
    const titleLabel=element("label");
    const selected=element("input","select-gif"); selected.type="checkbox"; selected.checked=index<2;
    selected.setAttribute("aria-label",`Auswählen: ${item.name}`); track.selected=selected;
    titleLabel.append(selected,element("h2","",item.name)); title.append(titleLabel);
    const badge=element("span","badge",item.exportFps ? `${item.exportFps} FPS` : "GIF");
    badge.title=item.exportFps ? "Export-FPS aus geprüften PyImgGif-Metadaten" : "Keine geprüften Export-FPS vorhanden";
    title.append(badge); head.append(title);
    head.append(element("div","meta",`${item.width} × ${item.height} px · ${item.logicalFrames} Frames · ${format(item.durationMs/1000)} s · ${format(item.bytes/1024,1)} KiB`));
    const stage=element("div","stage"), wrap=element("div","canvas-wrap"), canvas=element("canvas");
    canvas.width=item.width; canvas.height=item.height; canvas.setAttribute("role","img");
    canvas.setAttribute("aria-label",`Steuerbare GIF-Vorschau: ${item.name}`);
    track.canvas=canvas; track.stage=stage; track.context=canvas.getContext("2d");
    wrap.append(canvas); stage.append(element("span","stage-label",`ANIMATION ${String(index+1).padStart(2,"0")}`),wrap);
    const loading=element("div","stage-loading","Frames werden geladen …"); stage.append(loading); track.loading=loading;
    const body=element("div","card-body"), fpsRow=element("div","fps-row");
    track.actual=element("span","actual");track.actual.title="Berechnete Soll-Bildrate inklusive beider Tempo-Faktoren; keine gemessene Bildschirm-FPS";
    fpsRow.append(track.actual,element("span","original",`Vorgabe Ø ${format(item.logicalFrames*1000/item.durationMs)}`));
    const frameRow=element("div","frame-row"); track.play=element("button","card-play","Play"); track.play.disabled=true;
    const seek=element("input","frame-seek");seek.type="range";seek.min=0;seek.max=item.logicalFrames-1;seek.step=1;seek.value=0;
    seek.setAttribute("aria-label",`Frame auswählen: ${item.name}`); track.seek=seek;
    track.frameState=element("span","frame-state",`1 / ${item.logicalFrames}`);
    frameRow.append(track.play,seek,track.frameState);
    const settings=element("div","card-settings");
    track.modeInput=selector([["inherit","Global"],["original","Vorgabe"],["fixed","Feste FPS"]],"card-mode",`Timing: ${item.name}`);
    track.fpsInput=selector(payload.fpsChoices.map(fps=>[fps,String(fps)]),"card-fps",`Eigene Vorschau-FPS: ${item.name}`);track.fpsInput.value=12;
    track.speedInput=numeric("card-speed",`Eigener Tempo-Faktor: ${item.name}`,1,0.1,4,0.1);
    settings.append(labelled("Timing",track.modeInput),labelled("FPS",track.fpsInput),labelled("Tempo ×",track.speedInput));
    const footer=element("div","card-footer");const download=element("a","","GIF speichern ↓");
    download.href=item.gif;download.download=item.name;download.title="Das vorhandene Original-GIF unverändert speichern";
    const cycle=element("span","status",`${item.storedFrames} GIF-Bilder`);
    footer.append(download,cycle);
    const details=element("details","info-details");details.append(element("summary","","Timing & Original-GIF"));
    details.append(element("p","",`${item.storedFrames} gespeicherte GIF-Bilder${item.exportFps?` · ${item.exportFps} Export-FPS`:""}. ${item.sheet?`Vorschau aus ${item.logicalFrames} Spritesheet-Zellen.`:"Original-GIF ohne steuerbare Vorschau."}`));
    if (!item.exportFps && item.filenameFps) details.append(element("p","",`${item.filenameFps} FPS im Dateinamen sind nur ein unbestätigter Hinweis.`));
    item.notes.forEach(note => details.append(element("p","warning",note)));
    const native=element("details","native");native.append(element("summary","","Original im Browser abspielen (ohne Regler)"));
    const nativeImage=element("img");nativeImage.alt=`Original-GIF: ${item.name}`;native.append(nativeImage);
    native.addEventListener("toggle",()=>{if(native.open) nativeImage.src=item.gif;else nativeImage.removeAttribute("src");});
    details.addEventListener("toggle",()=>{if(!details.open) native.open=false;});
    details.append(native);body.append(fpsRow,frameRow,settings,footer,details);node.append(head,stage,body);
    if(track.native){
      node.dataset.native="true";selected.checked=false;selected.disabled=true;
      const original=element("img");original.alt=item.name;original.loading="lazy";original.src=item.gif;
      original.style.maxWidth="100%";original.style.maxHeight="100%";original.style.imageRendering="pixelated";
      wrap.replaceChildren(original);loading.hidden=true;frameRow.remove();settings.remove();fpsRow.remove();
      body.prepend(element("p","warning","Original-GIF ohne passendes Spritesheet: Wiedergabe ohne FPS- und Einzelbildsteuerung."));
    }
    selected.addEventListener("change",applyFilter);
    track.play.addEventListener("click",()=>{
      if(!state.ready || !track.loaded)return;
      if(!state.playing){tracks.forEach(t=>{t.paused=true;});state.playing=true;track.paused=false;state.lastTimestamp=null;}
      else track.paused=!track.paused;
      if(tracks.filter(t=>t.loaded).every(t=>t.paused))state.playing=false;
      render();
    });
    seek.addEventListener("input",()=>{
      track.position=track.starts[Number(seek.value)];track.paused=true;
      if(tracks.filter(t=>t.loaded).every(t=>t.paused))state.playing=false;
      render(true);
    });
    track.modeInput.addEventListener("change",()=>{track.mode=track.modeInput.value;configure(track);render(true);});
    track.fpsInput.addEventListener("change",()=>{track.fps=number(track.fpsInput.value,12,1,60);track.fpsInput.value=track.fps;configure(track);render(true);});
    track.speedInput.addEventListener("change",()=>{track.speed=number(track.speedInput.value,1,0.1,4);track.speedInput.value=track.speed;render();});
    configure(track,false);
    return track;
  }
  function applyFilter() {
    const query=$("search").value.trim().toLocaleLowerCase("de");
    let visible=0,selected=0;
    tracks.forEach(t=>{
      if(t.selected.checked)selected++;
      t.node.hidden=!t.item.name.toLocaleLowerCase("de").includes(query)||($("selectedOnly").checked&&!t.selected.checked);
      if(!t.node.hidden)visible++;
    });
    $("visibleCount").textContent=`${visible} von ${tracks.length} GIFs sichtbar · ${selected} ausgewählt`;
    $("empty").hidden=visible>0;
    $("overlayPanel").hidden=$("view").value!=="overlay";
    state.overlayKey="";
    resizeAll();render(true);
  }
  function drawOverlay(force=false) {
    if($("overlayPanel").hidden)return;
    const pair=tracks.filter(t=>t.selected.checked&&t.loaded).slice(0,2);
    const canvas=$("overlayCanvas"),ctx=canvas.getContext("2d");
    if(pair.length<2){ctx.clearRect(0,0,canvas.width,canvas.height);$("overlayNames").textContent="Zwei geladene GIFs über die Checkboxen auswählen.";return;}
    const [a,b]=pair;
    const alpha=Number($("overlayAlpha").value)/100;
    const width=Math.max(a.item.width,b.item.width),height=Math.max(a.item.height,b.item.height);
    const key=`${a.node.dataset.index}:${a.lastFrame}|${b.node.dataset.index}:${b.lastFrame}|${alpha}`;
    if(!force&&key===state.overlayKey)return;
    state.overlayKey=key;
    if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
    fitCanvas(canvas,canvas.closest(".stage"),width,height);
    ctx.clearRect(0,0,width,height);
    ctx.imageSmoothingEnabled=$("pixel").checked===false;
    // Add premultiplied contributions: endpoints show only A or only B.
    ctx.globalCompositeOperation="source-over";ctx.globalAlpha=1-alpha;
    drawCell(a,ctx,frameIndex(a),Math.floor((width-a.item.width)/2),Math.floor((height-a.item.height)/2));
    ctx.globalCompositeOperation="lighter";ctx.globalAlpha=alpha;
    drawCell(b,ctx,frameIndex(b),Math.floor((width-b.item.width)/2),Math.floor((height-b.item.height)/2));
    ctx.globalAlpha=1;ctx.globalCompositeOperation="source-over";
    $("overlayNames").textContent=`A: ${a.item.name}  /  B: ${b.item.name}`;
  }
  function tick(timestamp) {
    if(state.lastTimestamp===null)state.lastTimestamp=timestamp;
    const elapsed=Math.max(0,timestamp-state.lastTimestamp);
    state.lastTimestamp=timestamp;
    if(state.playing&&!document.hidden){
      tracks.forEach(t=>{
        if(t.loaded&&!t.paused){
          t.position=(t.position+elapsed*state.speed*t.speed)%t.total;
          // Treat sub-nanosecond floating-point residue at a loop boundary as zero.
          if(t.total-t.position<1e-7 || t.position<1e-7)t.position=0;
          draw(t);
        }
      });
      drawOverlay();
    }
    if(timestamp-state.uiTimestamp>200){tracks.forEach(metrics);state.uiTimestamp=timestamp;}
    requestAnimationFrame(tick);
  }
  async function loadTrack(track) {
    if(track.native)return;
    try{
      if(!track.context)throw new Error("Canvas wird von diesem Browser nicht unterstützt.");
      track.picture=await new Promise((resolve,reject)=>{
        const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(new Error("Spritesheet konnte nicht geladen werden."));img.src=track.item.sheet;
      });
      if(track.picture.naturalWidth!==track.item.width*track.item.columns||track.picture.naturalHeight!==track.item.height*track.item.rows)throw Error("Spritesheet wurde geändert. HTML-Vorschau neu erstellen.");
      track.loaded=true;track.loading.hidden=true;track.node.dataset.loaded="true";
      draw(track,true);
    }catch(error){
      track.node.classList.add("load-error");track.loading.textContent=`Vorschaufehler: ${error.message}`;
    }
  }
  function reset() {
    state.speed=1;state.mode="original";state.fps=12;state.zoom="fit";state.playing=false;state.lastTimestamp=null;
    $("globalMode").value="original";$("globalFps").value=12;$("globalFps").disabled=true;
    $("globalSpeed").value=1;$("globalSpeedValue").textContent="1.0×";
    $("search").value="";$("view").value="grid";$("zoom").value="fit";$("background").value="checker";
    $("pixel").checked=true;$("selectedOnly").checked=false;$("overlayAlpha").value=50;$("overlayAlphaValue").textContent="50%";
    document.body.dataset.background="checker";document.body.dataset.pixel="true";
    tracks.forEach((t,i)=>{t.mode="inherit";t.fps=12;t.speed=1;t.paused=false;t.position=0;t.modeInput.value="inherit";t.fpsInput.value=12;t.speedInput.value=1;t.selected.checked=!t.native&&i<2;configure(t,false);});
    applyFilter();render(true);
  }
  $("folder").textContent=payload.folder;$("totalCount").textContent=payload.items.length;
  for(const fps of payload.fpsChoices){const option=element("option","",`${fps} FPS`);option.value=fps;$("globalFps").append(option);}$("globalFps").value=state.fps;
  $("created").textContent=`Erstellt: ${new Date(payload.created).toLocaleString("de-DE")}.`;
  for(const [index,item] of payload.items.entries()){
    const track=createTrack(item,index);tracks.push(track);$("gallery").append(track.node);
  }
  if(payload.skipped.length){
    $("skipped").hidden=false;
    const details=element("details");details.append(element("summary","warning",`${payload.skipped.length} GIF(s) konnten nicht gelesen werden`));
    payload.skipped.forEach(s=>details.append(element("p","warning",`${s.name}: ${s.reason}`)));
    $("skipped").append(details);
  }
  $("play").addEventListener("click",playAll);$("sync").addEventListener("click",synchronize);
  $("prev").addEventListener("click",()=>stepAll(-1));$("next").addEventListener("click",()=>stepAll(1));
  $("globalMode").addEventListener("change",()=>{state.mode=$("globalMode").value;$("globalFps").disabled=state.mode!=="fixed";tracks.forEach(t=>configure(t));render(true);});
  $("globalFps").addEventListener("change",()=>{state.fps=number($("globalFps").value,12,1,60);$("globalFps").value=state.fps;tracks.forEach(t=>configure(t));render(true);});
  $("globalSpeed").addEventListener("input",()=>{state.speed=Number($("globalSpeed").value);$("globalSpeedValue").textContent=`${state.speed.toFixed(1)}×`;render();});
  $("search").addEventListener("input",applyFilter);$("selectedOnly").addEventListener("change",applyFilter);
  $("selectAll").addEventListener("click",()=>{tracks.forEach(t=>{t.selected.checked=!t.native;});applyFilter();});
  $("selectNone").addEventListener("click",()=>{tracks.forEach(t=>{t.selected.checked=false;});applyFilter();});
  $("view").addEventListener("change",applyFilter);
  $("zoom").addEventListener("change",()=>{state.zoom=$("zoom").value;resizeAll();});
  $("background").addEventListener("change",()=>{document.body.dataset.background=$("background").value;});
  $("pixel").addEventListener("change",()=>{document.body.dataset.pixel=String($("pixel").checked);render(true);});
  $("overlayAlpha").addEventListener("input",()=>{$("overlayAlphaValue").textContent=`${$("overlayAlpha").value}%`;drawOverlay(true);});
  $("reset").addEventListener("click",reset);
  document.addEventListener("visibilitychange",()=>{state.lastTimestamp=null;});
  document.addEventListener("keydown",event=>{
    if(event.ctrlKey||event.metaKey||event.altKey||event.target.closest("input,select,textarea,button,a,summary,[contenteditable]"))return;
    if(event.code==="Space"){event.preventDefault();playAll();}
    else if(event.code==="ArrowLeft"){event.preventDefault();stepAll(-1);}
    else if(event.code==="ArrowRight"){event.preventDefault();stepAll(1);}
    else if(event.code==="KeyR"){event.preventDefault();synchronize();}
  });
  window.addEventListener("resize",resizeAll);
  applyFilter();
  async function initialize() {
    let cursor=0,finished=0;
    async function worker(){
      while(cursor<tracks.length){const t=tracks[cursor++];await loadTrack(t);finished++;$("loadStatus").textContent=`${finished} / ${tracks.length} GIFs geladen`;}
    }
    await Promise.all(Array.from({length:Math.min(4,tracks.length)},worker));
    const loaded=tracks.filter(t=>t.loaded).length;
    state.ready=loaded>0;state.playing=state.ready&&!window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    ["play","sync","prev","next"].forEach(id=>{$(id).disabled=!state.ready;});
    tracks.forEach(t=>{t.play.disabled=!t.loaded;});
    $("loadStatus").textContent=`${loaded} steuerbare Vorschauen · ${tracks.filter(t=>t.native).length} Original-GIFs ohne Regler`;
    document.body.dataset.ready="true";
    resizeAll();render(true);requestAnimationFrame(tick);
  }
  initialize().catch(error=>{$("loadStatus").textContent=`Fehler beim Start: ${error.message}`;});
})();
</script>
</body>
</html>
'''


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="PyImageGif", allow_abbrev=False,
        description="Animiert Bilder direkt im aktuellen Terminal-Arbeitsordner. Keine Unterordner.",
        epilog=("Standard: pro Spritesheet ein GIF, Raster automatisch (3-64 Zellen).\n"
                "--grid SPALTENxZEILEN: manuelles Raster fuer alle Spritesheets im Ordner;\n"
                "hat Vorrang vor Dateiname und Bildanalyse. 16x1 = nebeneinander, 1x16 = untereinander.\n"
                "Ohne --grid haben Namenshinweise wie _4x4, _2x3 oder _16x1 Vorrang vor der Bildanalyse.\n"
                "Ohne Hinweis: konservative Bildanalyse; unklare Raster werden uebersprungen.\n"
                "Solo: alle statischen Bilder natuerlich nach Dateiname in EIN GIF; gleiche Bildgroesse erforderlich.\n"
                "Ausgabe: NAME_12fps.gif bzw. ORDNER_solo_12fps.gif, jeweils im Arbeitsordner.\n"
                "Erneuter Aufruf ersetzt gleichnamige GIFs erst nach erfolgreicher Erstellung.\n"
                "GIF-Konvertierung: GIFs, versteckte Dateien, Links und Unterordner werden nicht eingelesen.\n"
                "Formate: PNG, WebP, BMP, TGA, TIFF, JPG/JPEG (statisch).\n"
                "GIF: Endlosschleife, gemeinsame Palette, binaere Transparenz; keine Skalierung.\n"
                "HTML: automatisch alle GIFs im Arbeitsordner, inklusive frueherer Durchlaeufe.\n"
                "HTML-Datei ist offline nutzbar; FPS/Tempo wirken nur auf die Vorschau.\n"
                "Mit --html-only ohne Bildkonvertierung aktualisieren, danach im Browser neu laden.\n\n"
                "Beispiele:\n  PyImageGif --fps 12\n  PyImageGif -f8 --grid 16x1\n"
                "  PyImageGif -f8 --grid 1x16\n  PyImageGif --solo --fps 8\n  PyImageGif -s -f 24\n"
                "  PyImageGif --html-only --open-html\n  PyImageGif -f 12 --no-html"),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-f", "--fps", type=int, choices=FPS_CHOICES,
                        help="Export-FPS; fuer Spritesheets und --solo Pflicht, nicht mit --html-only.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-s", "--solo", action="store_true",
                      help="Alle Einzelbilder im Arbeitsordner zu einer Animation verbinden.")
    mode.add_argument("--grid", type=parse_grid, metavar="SPALTENxZEILEN",
                      help="Raster manuell festlegen, z.B. 16x1 oder 1x16 (3-64 Zellen; ohne --solo).")
    mode.add_argument("--html-only", action="store_true",
                      help="HTML mit vorhandenen GIFs und Spritesheets aktualisieren; keine --fps erforderlich.")
    html_options = parser.add_mutually_exclusive_group()
    html_options.add_argument("--html", type=Path, metavar="DATEI", default=Path(HTML_DEFAULT),
                              help="HTML-Ausgabepfad (Standard: gif-vergleich.html). Elternordner muss existieren.")
    html_options.add_argument("--no-html", action="store_true",
                              help="Nur GIFs erzeugen, keine HTML-Vergleichsansicht.")
    parser.add_argument("--open-html", action="store_true",
                        help="Die erzeugte HTML-Datei im Standardbrowser oeffnen.")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Kompatibilitätsoption: vorhandene Ausgaben behalten (bereits Standard).")
    parser.add_argument("--overwrite", action="store_true", help="GIFs und HTML-Ausgaben neu erstellen")
    parser.add_argument("--dry-run", action="store_true", help="Nur prüfen und geplante Ausgaben anzeigen")
    parser.add_argument("--files", nargs="+", type=Path, help="Nur diese Bilddateien im Arbeitsordner verarbeiten")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.html_only and args.fps is None:
        parser.error("--fps ist fuer die Konvertierung erforderlich; fuer vorhandene GIFs --html-only verwenden.")
    if args.html_only and args.fps is not None:
        parser.error("--html-only liest fertige GIFs; --fps ist nur fuer die Konvertierung vorgesehen.")
    if args.no_html and (args.html_only or args.open_html):
        parser.error("--no-html kann nicht mit --html-only oder --open-html kombiniert werden.")
    if args.skip_existing and (args.html_only or args.solo):
        parser.error("--skip-existing gilt nur fuer die Spritesheet-Konvertierung.")
    if args.skip_existing and args.overwrite:
        parser.error("--skip-existing und --overwrite widersprechen sich.")
    if args.files and (args.html_only or args.solo):
        parser.error("--files gilt nur für Spritesheets.")
    if Image is None:
        print("FEHLER: Pillow fehlt. Im Python-Environment Pillow installieren: python -m pip install Pillow",
              file=sys.stderr)
        return 1
    try:
        directory = Path.cwd()
        html_output = args.html if args.html.is_absolute() else directory / args.html
        if not args.no_html:
            validate_html_output(html_output)
        exit_code = 0
        if not args.html_only:
            files = discover_images(directory) if args.files is None else [directory / p for p in args.files]
            if any(p.is_symlink() or p.parent != directory or not p.is_file() for p in files):
                raise ConversionError("--files darf nur reguläre Bilddateien im Arbeitsordner enthalten.")
            if not files:
                raise ConversionError("Keine unterstuetzten statischen Bilddateien im aktuellen Ordner gefunden. "
                                      "Fuer vorhandene GIFs --html-only verwenden.")
            print(f"Ordner: {directory}\nModus: {'Solo' if args.solo else 'Spritesheets'} | FPS: {args.fps}\n",
                  flush=True)
            exit_code = (run_solo(files, directory, args.fps, overwrite=args.overwrite, dry_run=args.dry_run)
                         if args.solo else run_sheets(files, args.fps, args.grid,
                             overwrite=args.overwrite, dry_run=args.dry_run))
        if not args.no_html:
            selected_gifs = list(plan_sheet_outputs(files, args.fps).values()) if args.files else None
            gallery = build_html_gallery(directory, html_output, args.grid, overwrite=args.overwrite,
                                         dry_run=args.dry_run, gif_paths=selected_gifs)
            if gallery.skipped:
                exit_code = 1
            if args.open_html and not args.dry_run:
                try:
                    if not webbrowser.open(html_output.absolute().as_uri()):
                        print("HINWEIS: Kein Browser gestartet. HTML-Datei manuell oeffnen.", file=sys.stderr)
                except (OSError, webbrowser.Error) as exc:
                    print(f"HINWEIS: Browser konnte nicht gestartet werden: {exc}", file=sys.stderr)
        return exit_code
    except KeyboardInterrupt:
        print("\nAbgebrochen. Bereits erfolgreich erstellte GIFs bleiben erhalten.", file=sys.stderr)
        return 130
    except (OSError, ValueError, SyntaxError, MemoryError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
