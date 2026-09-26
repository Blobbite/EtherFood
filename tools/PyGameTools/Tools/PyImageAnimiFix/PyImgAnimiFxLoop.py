#!/usr/bin/env python3
"""PyFix Loop 2.1: folder-first sprite-loop inspection and position correction.

Python 3.10+. Runtime dependencies: numpy, Pillow, opencv-python-headless.
Run without arguments to process supported images in the current directory.
Use --help for copyable commands, --help-exam for the full parameter guide.

Default: keep every frame and smooth an automatically selected anchor.
This is a position-jitter tool, NOT a 16-frame pose/phase reconstruction tool.
Automatic grid/anchor selection is heuristic; review the PNGs and preview.
Original inputs and existing result directories are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import shlex
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Sequence

# Help must work even before optional runtime dependencies are installed.
_IMPORT_ERROR = None
try:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, __version__ as PIL_VERSION
except ImportError as exc:
    _IMPORT_ERROR = exc

VERSION = "2.1.0"
SUPPORTED_EXTENSIONS = frozenset({".png", ".apng", ".gif", ".webp"})
OUTPUT_MARKER = ".pyfix-output"


class NotAnimationError(ValueError):
    """An animation-named input contains no animation; never split it blindly."""


def command_name() -> str:
    """Show a runnable invocation, including renamed/installed entry points."""
    invoked = Path(sys.argv[0])
    if invoked.name == "__main__.py":
        return "python pyfix_loop.py"
    if invoked.suffix.lower() == ".py":
        return "python " + shlex.quote(sys.argv[0])
    return shlex.quote(sys.argv[0])


def rendered_help(text: str) -> str:
    return text.replace("python pyfix_loop.py", command_name())


def radius_arg(text: str) -> int | str:
    if text.lower() == "auto":
        return "auto"
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--radius braucht auto oder eine positive Ganzzahl.") from exc
    return value


def effective_tracking(args: argparse.Namespace, size: tuple[int, int]) -> dict:
    """Map optional reference coordinates to NATIVE pixels; never resize output."""
    w, h = size
    radius = max(8, round(8 * max(w, h) / 128)) if args.radius == "auto" else args.radius
    roi = None if args.roi == "auto" else args.roi
    base = args.roi_base
    if roi is not None and base is not None:
        x, y, rw, rh = roi
        if x + rw > base or y + rh > base:
            raise ValueError(f"ROI {roi} liegt ausserhalb der --roi-base {base}.")
        left, top = round(x * w / base), round(y * h / base)
        right, bottom = round((x + rw) * w / base), round((y + rh) * h / base)
        roi = (left, top, right - left, bottom - top)
        if min(roi[2:]) < 4:
            raise ValueError("Skalierte ROI ist kleiner als 4x4 Pixel. Groesseren Ausschnitt waehlen.")
    return {"radius_pixels": int(radius), "roi_xywh": roi,
            "roi_reference_size": base if roi is not None else None,
            "native_frame_size": [w, h]}


def patch_statistics(frame: Image.Image, roi: tuple[int, int, int, int]) -> dict:
    x, y, rw, rh = roi
    w, h = frame.size
    inside = x >= 0 and y >= 0 and rw >= 4 and rh >= 4 and x + rw <= w and y + rh <= h
    info = {"roi_xywh": list(roi), "inside_frame": inside,
            "frame_size": [w, h], "frame_alpha_bbox_xyxy": frame.getchannel("A").getbbox()}
    if inside:
        patch = feature(frame)[y:y + rh, x:x + rw]
        info.update(visible_pixels=int(np.count_nonzero(patch[..., 3] > 0.1)),
                    total_pixels=rw * rh,
                    alpha_sum=float(patch[..., 3].sum()),
                    mean_channel_variance=float(np.mean(np.var(patch, axis=(0, 1)))))
    return info



def read_frames(path: Path, columns: int | str | None, rows: int, count: int | None,
                fps: float | None) -> tuple[list[Image.Image], list[float]]:
    """Decode animated images or split a static, unpadded sheet row by row.

    Auto assumes square frames in a single horizontal strip. It cannot infer
    arbitrary multi-row grids, rectangular cells, outer margins or gutters.
    Grid flags intentionally do not affect animated files in mixed batches.
    """
    with Image.open(path) as source:
        n = getattr(source, "n_frames", 1)
        if n > 1:
            # APNG may contain a separate default/poster image, not a frame.
            start = 1 if source.info.get("default_image", False) else 0
            if not 2 <= n - start <= 256:
                raise ValueError("An animation must contain between 2 and 256 frames.")
            frames, durations = [], []
            for i in range(start, n):
                source.seek(i)
                frame = source.convert("RGBA").copy()
                duration = source.info.get("duration", 125)
                try:
                    duration = float(duration)
                except (ValueError, TypeError):
                    duration = 125.0
                if not math.isfinite(duration) or duration <= 0:
                    duration = 125.0
                frames.append(frame)
                durations.append(duration)
        else:
            looks_like_strip = source.width > source.height and source.width % source.height == 0
            if path.suffix.lower() in {".gif", ".apng"} and not looks_like_strip and rows == 1:
                raise NotAnimationError(
                    f"Dateiendung {path.suffix.lower()}, erkannter Inhalt {source.format}, "
                    f"{source.width}x{source.height}, nur 1 Bild: kein Animationsloop. "
                    "Nicht als Sheet zerschnitten. Eine echte Animation oder ein PNG-Sheet verwenden.")
            if columns is None or columns == "auto":
                if rows != 1:
                    raise ValueError("Mehrere Zeilen brauchen --columns N --rows M.")
                if source.width <= source.height or source.width % source.height:
                    raise ValueError(
                        "Raster nicht automatisch bestimmbar. Auto erwartet einen "
                        "horizontalen Streifen quadratischer Frames. "
                        "Raster mit --columns N --rows M angeben; ein Einzelbild ist kein Loop.")
                columns = source.width // source.height
            if columns < 1 or rows < 1:
                raise ValueError("Grid dimensions must be positive.")
            if source.width % columns or source.height % rows:
                raise ValueError("Image dimensions are not divisible by the requested grid.")
            total = columns * rows if count is None else count
            if not 2 <= total <= columns * rows or total > 256:
                raise ValueError("--count / Raster muss 2 bis 256 verwendete Frames ergeben.")
            w, h = source.width // columns, source.height // rows
            rgba = source.convert("RGBA")
            frames = []
            for i in range(total):
                x, y = (i % columns) * w, (i // columns) * h
                frames.append(rgba.crop((x, y, x + w, y + h)))
            durations = [125.0] * total
    if len(frames) < 2:
        raise ValueError("At least two frames are required.")
    if any(frame.size != frames[0].size for frame in frames):
        raise ValueError("All animation frames must have the same canvas size.")
    if fps is not None:
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("--fps must be a finite positive number.")
        durations = [1000.0 / fps] * len(frames)
    return frames, durations


def feature(frame: Image.Image, limit: int | None = None) -> np.ndarray:
    """Premultiplied RGB + alpha; invisible RGB must not influence a match."""
    if limit and max(frame.size) > limit:
        w, h = frame.size
        factor = limit / max(w, h)
        frame = frame.resize((max(1, round(w * factor)), max(1, round(h * factor))),
                             Image.Resampling.LANCZOS)
    a = np.asarray(frame, dtype=np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]
    return a


def distance_matrix(frames: Sequence[Image.Image]) -> np.ndarray:
    """Mean absolute premultiplied-RGBA error, on a 0..255 scale."""
    features = [feature(frame, 128) for frame in frames]
    d = np.zeros((len(frames), len(frames)), dtype=np.float64)
    for i in range(len(frames)):
        for j in range(i + 1, len(frames)):
            value = float(np.abs(features[i] - features[j]).mean() * 255.0)
            d[i, j] = d[j, i] = value
    return d


def repeat_diagnosis(d: np.ndarray) -> dict:
    """Find repeated appearance, not a universal semantic gait detector.

    A low repeat error must be supported by at least four pairs and be much
    smaller than an ordinary adjacent-frame difference. Thresholds are
    conservative heuristics, not probabilities or guarantees.
    """
    n = len(d)
    normal = float(np.median([d[i, i + 1] for i in range(n - 1)]))
    candidates = []
    for period in range(3, n // 2 + 1):
        errors = np.array([d[i, i + period] for i in range(n - period)])
        if len(errors) < 4:
            continue
        median_ratio = float(np.median(errors) / max(normal, 1e-9))
        q75_ratio = float(np.quantile(errors, 0.75) / max(normal, 1e-9))
        candidates.append({"period": period, "median_ratio": median_ratio,
                           "q75_ratio": q75_ratio})
    accepted = [c for c in candidates if normal > 0.5
                and c["median_ratio"] < 0.40 and c["q75_ratio"] < 0.65]
    # Prefer the shortest sufficiently clear period over a multiple of it.
    selected = min(accepted, key=lambda c: c["period"]) if accepted else None
    return {
        "median_internal_difference": normal,
        "last_to_first_difference": float(d[-1, 0]),
        "seam_to_internal_ratio": float(d[-1, 0] / max(normal, 1e-9)),
        "candidate_periods": candidates,
        "suggested_period": selected["period"] if selected else None,
        "method": "Repeated appearance heuristic; visual review is required.",
    }


def whole_cycle_indices(d: np.ndarray, period: int) -> list[int]:
    """Keep a contiguous window of complete repeated periods; never reorder."""
    n = len(d)
    if not 2 <= period <= n // 2:
        raise ValueError("A cycle period must allow at least two repeats.")
    length = (n // period) * period
    options = []
    for start in range(n - length + 1):
        end = start + length - 1
        repeat_error = float(np.mean([d[i, i + period]
                                      for i in range(start, end - period + 1)]))
        # The two ends must also agree with their equivalent internal phases.
        endpoint_error = float((d[start, start + period] + d[end, end - period]) / 2)
        options.append((repeat_error + 0.25 * endpoint_error, start))
    _, start = min(options)
    return list(range(start, start + length))


def parse_roi(text: str) -> tuple[int, int, int, int]:
    try:
        values = tuple(int(v.strip()) for v in text.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ROI must be x,y,width,height in pixels.") from exc
    if len(values) != 4 or min(values) < 0 or values[2] < 4 or values[3] < 4:
        raise argparse.ArgumentTypeError("ROI needs x,y >= 0 and width,height >= 4.")
    return values


def track_anchor(frames: Sequence[Image.Image], roi: tuple[int, int, int, int],
                 radius: int) -> tuple[np.ndarray, np.ndarray]:
    """Match one fixed reference patch in each frame, avoiding accumulated drift.

    Returns observed positions relative to frame 1, not correction shifts.
    Positive x/y means the matched anchor is further right/down.
    """
    x, y, rw, rh = roi
    w, h = frames[0].size
    if min(x, y) < 0 or min(rw, rh) < 4 or x + rw > w or y + rh > h:
        raise ValueError(
            f"ROI {x},{y},{rw},{rh} liegt ausserhalb des {w}x{h}-Einzelframes "
            "oder ist kleiner als 4x4. Raster und --roi-base pruefen; --inspect zeigt Frame 1.")
    first = feature(frames[0])
    template = np.ascontiguousarray(first[y:y + rh, x:x + rw])
    if float(template[..., 3].sum()) < 16 or float(np.mean(np.var(template, axis=(0, 1)))) < 0.0004:
        stats = patch_statistics(frames[0], roi)
        hint = (" Die Beispiel-ROI 42,8,38,30 stammt aus 128x128; bei entsprechend "
                "skalierten Sprites --roi-base 128 oder --preset example16 verwenden."
                if (w, h) != (128, 128) else "")
        raise ValueError(
            f"ROI contains too little visible structure to track. Frame 1: {w}x{h}; "
            f"ROI {x},{y},{rw},{rh}; sichtbare Pixel: {stats['visible_pixels']}/{rw * rh}; "
            f"Alpha-BBox: {stats['frame_alpha_bbox_xyxy']}." + hint +
            " --inspect exportiert Frame 1 und die eingezeichnete ROI.")
    sx, sy = max(0, x - radius), max(0, y - radius)
    ex, ey = min(w, x + rw + radius), min(h, y + rh + radius)
    positions, costs = [], []
    for i, frame in enumerate(frames):
        search = np.ascontiguousarray(feature(frame)[sy:ey, sx:ex])
        match = cv2.matchTemplate(search, template, cv2.TM_SQDIFF_NORMED)
        match = np.nan_to_num(match, nan=np.inf, posinf=np.inf, neginf=np.inf)
        iy, ix = np.unravel_index(int(np.argmin(match)), match.shape)
        positions.append((int(ix + sx - x), int(iy + sy - y)))
        costs.append(float(match[iy, ix]))
    return np.asarray(positions, dtype=np.float64), np.asarray(costs, dtype=np.float64)


def stabilization_offsets(positions: np.ndarray, mode: str,
                          strength: float, passes: int) -> np.ndarray:
    if mode == "lock":
        # Deliberate full anchor lock. This also removes intended body bob.
        target = np.broadcast_to(np.rint(np.median(positions, axis=0)), positions.shape)
    else:
        target = positions.copy()
        for _ in range(passes):
            # Circular boundary: frame N and frame 1 are neighbors.
            target = (np.roll(target, 1, axis=0) + 2.0 * target
                      + np.roll(target, -1, axis=0)) / 4.0
    return np.rint(strength * (target - positions)).astype(np.int32)


def move_frames(frames: Sequence[Image.Image], offsets: np.ndarray,
                padding: int) -> list[Image.Image]:
    """Integer placement, no interpolation, no wraparound, no double alpha."""
    w, h = frames[0].size
    results = []
    for i, (frame, offset) in enumerate(zip(frames, offsets)):
        dx, dy = (int(offset[0]), int(offset[1]))
        bbox = frame.getchannel("A").getbbox()
        if bbox:
            left, top, right, bottom = bbox
            if (left + dx + padding < 0 or top + dy + padding < 0
                    or right + dx + padding > w + 2 * padding
                    or bottom + dy + padding > h + 2 * padding):
                raise ValueError(f"Frame {i + 1}: correction would clip visible pixels. "
                                 "Increase --padding; no output was written.")
        out = Image.new("RGBA", (w + 2 * padding, h + 2 * padding), (0, 0, 0, 0))
        # No mask here: pasting an RGBA source copies its alpha unchanged.
        out.paste(frame, (padding + dx, padding + dy))
        results.append(out)
    return results


def gif_durations(durations: Sequence[float]) -> list[int]:
    """GIF uses 10-ms ticks. Cumulative rounding avoids systematic speed drift."""
    out, elapsed, assigned = [], 0.0, 0
    for duration in durations:
        elapsed += duration
        boundary = int(round(elapsed / 10.0) * 10)
        actual = max(10, boundary - assigned)
        out.append(actual)
        assigned += actual
    return out


def save_gif(frames: Sequence[Image.Image], durations: Sequence[float], path: Path,
             scale: int = 3) -> None:
    """Opaque preview only. The PNG sheet and individual PNGs retain RGBA."""
    flat = []
    for i, frame in enumerate(frames):
        width, height = frame.width * scale, frame.height * scale
        image = Image.new("RGB", (width, height + 28), (36, 36, 36))
        image.paste(frame.resize((width, height), Image.Resampling.NEAREST), (0, 28),
                    frame.getchannel("A").resize((width, height), Image.Resampling.NEAREST))
        ImageDraw.Draw(image).text((10, 7), f"Frame {i + 1}/{len(frames)}", fill=(240, 240, 240))
        flat.append(image)
    # One palette for all frames avoids a changing color quantization palette.
    atlas = Image.new("RGB", (flat[0].width, flat[0].height * len(flat)))
    for i, image in enumerate(flat):
        atlas.paste(image, (0, i * image.height))
    palette = atlas.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    paletted = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in flat]
    paletted[0].save(path, save_all=True, append_images=paletted[1:],
                     duration=gif_durations(durations), loop=0, disposal=2, optimize=False)


def export(frames: Sequence[Image.Image], durations: Sequence[float],
           output: Path, report: dict, preview: bool = True) -> None:
    output.mkdir(parents=True, exist_ok=True)
    w, h = frames[0].size
    sheet = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    png_folder = output / "frames"
    png_folder.mkdir(exist_ok=True)
    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * w, 0))
        frame.save(png_folder / f"frame_{i + 1:03d}.png")
    sheet.save(output / "sheet.png")
    if preview:
        save_gif(frames, durations, output / "preview.gif", scale=min(3, max(1, 512 // max(w, h))))
    report["output"] = {
        "frame_count": len(frames), "frame_width": w, "frame_height": h,
        "columns": len(frames), "rows": 1, "durations_ms": list(durations),
        "duration_total_ms": float(sum(durations)),
        "preview_gif_durations_ms": gif_durations(durations) if preview else None,
        "note": "Use the RGBA PNGs in-game. GIF is an opaque, palette-reduced preview.",
    }
    (output / OUTPUT_MARKER).write_text(VERSION + "\n", encoding="utf-8")
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def validate_matches(positions: np.ndarray, costs: np.ndarray,
                     radius: int, max_cost: float) -> None:
    bad = np.flatnonzero((costs > max_cost) | (~np.isfinite(costs)))
    if len(bad):
        raise ValueError(
            f"Unsicherer Anker in Frame(s) {(bad + 1).tolist()}. "
            "Einen stabileren Ausschnitt mit --roi x,y,breite,hoehe waehlen. "
            "Keine Korrektur exportiert.")
    if np.any(np.max(np.abs(positions), axis=1) >= radius):
        raise ValueError(
            "Anker erreicht den Suchradius. --radius erhoehen oder --roi verbessern. "
            "Keine Korrektur exportiert.")


def auto_anchor(frames: Sequence[Image.Image], radius: int,
                max_cost: float) -> tuple[tuple[int, int, int, int], dict]:
    """Rank structured patches in the upper half of the first visible sprite.

    This intentionally limited heuristic is meant for upright, in-place
    characters with a fairly stable head/torso. It is not anatomical detection.
    Each candidate must track acceptably through EVERY frame. Failure is explicit.
    """
    w, h = frames[0].size
    first = feature(frames[0])
    mask = first[..., 3] > 0.1
    ys, xs = np.nonzero(mask)
    if len(xs) < 32:
        raise ValueError("Zu wenig sichtbare Struktur fuer einen automatischen Anker.")
    top, bottom = int(ys.min()), int(ys.max()) + 1
    body_height = bottom - top
    upper_x = xs[ys < top + max(1, int(0.5 * body_height))]
    if not len(upper_x):
        raise ValueError("Kein automatischer Anker gefunden. --roi manuell angeben.")
    candidates = set()
    for sx, sy in ((0.30, 0.23), (0.23, 0.20)):
        rw, rh = min(w, max(8, round(w * sx))), min(h, max(8, round(h * sy)))
        if rw < 4 or rh < 4:
            continue
        for quantile in (0.25, 0.5, 0.75):
            cx = float(np.quantile(upper_x, quantile))
            for fraction in (0.16, 0.25, 0.34):
                cy = top + fraction * body_height
                x = min(w - rw, max(0, round(cx - rw / 2)))
                y = min(h - rh, max(0, round(cy - rh / 2)))
                candidates.add((x, y, rw, rh))
    valid = []
    for roi in sorted(candidates):
        x, y, rw, rh = roi
        patch = first[y:y + rh, x:x + rw]
        if float(np.mean(patch[..., 3] > 0.1)) < 0.30:
            continue
        try:
            positions, costs = track_anchor(frames, roi, radius)
            validate_matches(positions, costs, radius, max_cost)
        except (ValueError, cv2.error):
            continue
        # Prefer a consistently recognizable patch, then slightly prefer the top.
        score = float(np.quantile(costs, 0.90) + 0.5 * np.max(costs)
                      + 0.005 * (y - top) / max(1, body_height))
        valid.append((score, roi, float(np.max(costs))))
    if not valid:
        raise ValueError(
            "Kein ausreichend stabiler Auto-Anker gefunden. "
            "Mit --roi x,y,breite,hoehe einen Kopf-/Rumpfausschnitt setzen; "
            f"Framegroesse {w}x{h}, Suchradius {radius} Pixel. "
            "--inspect zeigt das Raster; --radius auto skaliert den Suchbereich. "
            "Keine Korrektur exportiert.")
    score, roi, worst_cost = min(valid)
    return roi, {
        "mode": "auto", "roi_xywh": list(roi),
        "tested_candidates": len(candidates), "accepted_candidates": len(valid),
        "ranking_score": score, "worst_match_cost": worst_cost,
        "note": "Appearance heuristic in the upper sprite region; not a verified body anchor.",
    }


HELP_EXAMPLES = r"""
KOPIERBARE BEISPIELE (im Terminal, im Ordner mit diesem Skript)

  Installation:
    python -m pip install -r requirements.txt

  Alle unterstuetzten Bilder im aktuellen Arbeitsordner bearbeiten:
    python pyfix_loop.py

  Alle Bilder aus einem bestimmten Ordner, ohne einzelne Dateinamen:
    python pyfix_loop.py "input"

  Auch Unterordner, Ergebnisse separat ablegen:
    python pyfix_loop.py "input" --recursive --out "fixed"

  Dein Beispiel und gleichartig skalierte Fassungen, 16 Frames, 8 fps:
    python pyfix_loop.py "input" --preset example16 --out "fixed_16"

  Dasselbe Beispiel mit ausgeschriebenen Werten (ROI aus 128x128-Referenz):
    python pyfix_loop.py "input" --columns 16 --roi 42,8,38,30 --roi-base 128 --radius auto --stabilize smooth --strength 0.6 --fps 8 --out "fixed_16_manual"

  Nur tatsaechliches Format, Raster und ROI pruefen, nichts korrigieren:
    python pyfix_loop.py --inspect --out "diagnose"

  Die alte absolute ROI einzeichnen; sichtbar, falls sie in Transparenz liegt:
    python pyfix_loop.py --inspect --columns 16 --roi 42,8,38,30 --out "diagnose_roi"

  Die skalierte Beispiel-ROI pruefen:
    python pyfix_loop.py --inspect --preset example16 --out "diagnose_scaled"

  4 Spalten x 4 Zeilen; 14 belegte Zellen; Rest am Ende leer:
    python pyfix_loop.py "input" --columns 4 --rows 4 --count 14 --out "fixed_grid"

  Nur analysieren und unveraendert exportieren, nichts verschieben:
    python pyfix_loop.py "input" --stabilize off --out "inspection"

  Optional: klare Wiederholungen zuschneiden. Kann Frames ENTFERNEN:
    python pyfix_loop.py "input" --repair-cycle --stabilize off --out "trimmed"

  Einzeldatei bleibt moeglich:
    python pyfix_loop.py "input/walk.png" --preset example16 --out "one_result"

  Jeder Parameter mit Bedeutung, Einheiten und Auswahlhilfe:
    python pyfix_loop.py --help-exam

WICHTIG
  Standardmaessig bleiben alle Frames erhalten. Die Positionskorrektur erzeugt
  KEINE neuen Posen und repariert keine falsche Schrittphase automatisch.
  Auto-Raster nimmt quadratische Frames in EINER horizontalen Reihe an.
  Auto-ROI ist eine Heuristik; Vorschau kontrollieren. Unsichere Dateien werden
  als Fehler gemeldet, die restlichen Dateien laufen weiter.
  PNG/APNG/GIF/WebP werden gesucht; andere Dateien werden ignoriert.
"""

HELP_EXAM = r"""
PYFIX LOOP 2.1 - HELP-EXAM / PARAMETER IM DETAIL
==============================================

1. DER AUFRUF
-------------
  python pyfix_loop.py [INPUT] [OPTIONEN]

  INPUT ist jetzt OPTIONAL und darf ein ORDNER sein.
  Ohne INPUT wird der aktuelle Arbeitsordner benutzt, nicht automatisch der
  Speicherort des Skripts. Mit `cd` wechselst du vorher in den gewuenschten Ordner.
  Eine einzelne Datei ist weiterhin erlaubt. Pfade mit Leerzeichen in "..." setzen.

  Beispiel:
    python pyfix_loop.py "C:/Game Art/Sprites" --out "C:/Game Art/Fixed"

  Windows: Falls der Python-Befehl bei dir `py` heisst, ersetze `python` durch `py`.
  Linux/macOS: Gegebenenfalls `python3` statt `python` benutzen.
  Ist das Programm bei dir als PyImgAnimiFxLoop eingerichtet, lautet der Aufruf:
    PyImgAnimiFxLoop --help
    PyImgAnimiFxLoop --help-exam
    PyImgAnimiFxLoop --version
  Der Befehl python ./pyfix_loop.py benoetigt dagegen eine vorhandene Datei an
  diesem Pfad. Ein funktionierender Alias erzeugt keine solche lokale Datei.
  Mit `type -a PyImgAnimiFxLoop` den Launcher pruefen. Nach einem Update muss
  --version 2.1.0 ausgeben; 2.0.0 bedeutet, dass noch der alte Code startet.

2. ORDNER UND AUSGABE
--------------------
  --recursive, -r          Standard: aus
    Durchsucht auch Unterordner. Ohne diese Option nur den gewaehlten Ordner.
    Versteckte Ordner und symbolische Links werden nicht verfolgt.
    Der Zielordner sowie durch PyFix markierte Ergebnisordner werden ausgelassen.
    Jeder Fund ist eine EIGENE Animation. Einzelne PNG-Frames werden NICHT zu
    einer gemeinsamen Animation zusammengesetzt.

  --out PFAD              Standard bei Ordnern: INPUT/pyfix_output
    Fuer einen Eingabeordner ist dies der gemeinsame Ergebnisordner.
    Jede Quelldatei bekommt einen eigenen Unterordner. Ihre Endung bleibt Teil
    des Ordnernamens: walk.png und walk.gif kollidieren deshalb nicht.
    Bei --recursive bleiben die relativen Unterordner erhalten.

    input/walk.png            -> fixed/walk.png/sheet.png
    input/enemy/idle.gif      -> fixed/enemy/idle.gif/sheet.png

    Fuer EINE Eingabedatei ist ein explizites --out direkt ihr Ergebnisordner:
    python pyfix_loop.py "input/walk.png" --out "one_result"
    Das Ergebnis liegt dann unter one_result/sheet.png.
    Ohne --out: Eingabedatei-Ordner/pyfix_output/DATEINAME.MIT.ENDUNG/.

    Originale werden nie ersetzt. Vorhandene Ergebnisordner werden uebersprungen,
    auch wenn du die Eingabe oder Parameter inzwischen geaendert hast. Fuer einen
    neuen Versuch einen anderen --out-Ordner waehlen.
    Der Zielordner darf NICHT der Eingabeordner oder dessen Oberordner sein.

  --no-preview            Standard: aus
    Schreibt keine preview.gif. Spart beim Stapellauf Zeit und Speicher.
    sheet.png, Einzelbilder und report.json werden weiterhin geschrieben.

  --inspect               Standard: aus
    Kopierbarer Aufruf:
      python pyfix_loop.py --inspect --out "diagnose"
    Alte Pixel-ROI pruefen:
      python pyfix_loop.py --inspect --columns 16 --roi 42,8,38,30 --out "diagnose_roi"
    Referenzkoordinaten pruefen:
      python pyfix_loop.py --inspect --preset example16 --out "diagnose_scaled"
    Reiner Diagnosemodus, keine Korrektur, kein Matching, kein Zykluszuschnitt.
    Standardausgabe ohne --out: INPUT/pyfix_inspect (statt pyfix_output).
    inspection.json: erkannter Inhalt/Dateiendung, Dateigroesse, SHA-256,
      Python-/Pillow-/OpenCV-/NumPy-Version, Skriptpfad, Raster und ROI-Statistik.
    first_frame.png: erster dekodierter Einzelframe in ORIGINALGROESSE.
    roi_overlay.png: blau = Alpha-Begrenzung, rot = ausdruecklich gesetzte ROI.
      Bei --roi auto gibt es noch keine ausgewaehlte ROI und kein rotes Rechteck.
    Kann das Raster nicht gelesen werden, heisst das Bild source_first_image.png;
      es ist dann KEIN bestaetigter Animationsframe. Der Fehler steht im JSON.
    Eine ROI mit sichtbare Pixel = 0 liegt komplett in Transparenz.
    --inspect --roi 42,8,38,30 prueft native Pixel, ohne versteckte Skalierung.
    --inspect --preset example16 prueft dieselben Werte in der 128er-Basis.
    Ein fertig geschriebener Diagnosebericht ist kein erfolgreich reparierter Loop.

3. DATEIFORMAT UND RASTER
------------------------
  Unterstuetzte Endungen: .png, .apng, .gif, .webp (auch Grossbuchstaben).
  Der Decoder liest den echten Dateiinhalt. Eine Datei namens walk.gif, die
  tatsaechlich ein statisches PNG enthaelt, wird als solches erkannt.
  Dateien mit .gif/.apng und nur einem Bild werden ohne Korrektur uebersprungen,
  wenn kein horizontaler Streifen quadratischer Frames erkennbar ist und keine
  mehreren Zeilen angegeben sind. --columns 16 allein zerschneidet also NICHT
  ein quadratisches .gif-Standbild. Ein klar erkennbarer PNG-Streifen mit falscher
  .gif-Endung bleibt als Sheet lesbar. Fuer andere statische Layouts PNG verwenden.
  Animierte GIF/APNG/WebP-Dateien liefern ihre Frames selbst; Rasteroptionen
  --columns, --rows und --count werden fuer sie IGNORIERT. So ist ein gemischter
  Ordner moeglich. Ein APNG-Posterbild zaehlt nicht als Animationsframe.

  --columns auto|N        Standard: auto
    Anzahl der Spalten im STATISCHEN Sheet, NICHT Breite eines Frames in Pixeln.
    Auto ist eine ANNAHME: eine horizontale Reihe quadratischer Frames.
    Es gilt dann: Spaltenzahl = Bildbreite / Bildhoehe.

    Dein Sheet: 2048 x 128 Pixel.
    2048 / 128 = 16 Spalten, also 16 Frames mit 128 x 128 Pixeln.
    Deshalb brauchst du fuer dieses Sheet --columns 16 nicht mehr zwingend.

    Achtung: 2048 x 128 koennte auch 32 rechteckige Frames mit 64 x 128 enthalten.
    Das kann man aus den Aussenmassen allein NICHT eindeutig entscheiden.
    Dann --columns 32 ausdruecklich angeben. Es findet keine intelligente
    Erkennung von Zellgrenzen, Raendern oder Abstaenden statt.

  --rows N                Standard: 1
    Anzahl der Zeilen. Fuer mehrere Zeilen --columns ebenfalls angeben.
    Beispiel: --columns 4 --rows 4 bedeutet 16 Rasterzellen.
    Ein vertikaler 16er-Streifen: --columns 1 --rows 16.
    Reihenfolge: zuerst links nach rechts, dann die naechste Zeile von oben.
    Breite muss durch Spalten, Hoehe durch Zeilen ohne Rest teilbar sein.

  --count N               Standard: alle Rasterzellen
    Anzahl verwendeter Frames ab der ersten Zelle, in Leserichtung.
    Beispiel: --columns 4 --rows 4 --count 14 verwendet die ersten 14 Zellen.
    Es duerfen also nur AM ENDE Zellen frei bleiben. Luecken mitten im Sheet
    werden nicht automatisch erkannt. Mindestens 2, hoechstens 256 Frames.
    Fuer --columns 16 --rows 1 ist --count 16 normalerweise unnoetig.

  Rastergrenzen muessen direkt aneinanderliegen: keine Zwischenraeume (Gutter)
  und keine Aussenraender. Bei unterschiedlichen rechteckigen Rastern Dateien
  gruppieren und je Gruppe einen eigenen Aufruf verwenden.
  Das ausgegebene sheet.png hat IMMER eine horizontale Reihe, auch wenn die
  Eingabe mehrere Zeilen hatte. Die Frame-Anzahl bleibt ohne --repair-cycle gleich.

4. ROI: DIE VIER ZAHLEN VERSTEHEN
--------------------------------
  --roi auto|X,Y,BREITE,HOEHE       Standard: auto
    ROI bedeutet der Bildausschnitt, an dem die Position verfolgt wird.
    Ohne --roi-base sind alle Werte GANZE PIXEL im ERSTEN EINZELFRAME, NICHT im ganzen Sheet
    und NICHT in der vergroesserten GIF-Vorschau.
    Ursprung (0,0): links oben. X waechst nach rechts, Y nach unten.

    Fuer dein Beispiel: --roi 42,8,38,30

      42 = X: linke Kante, 42 Pixel vom linken Frame-Rand entfernt.
       8 = Y: obere Kante, 8 Pixel vom oberen Frame-Rand entfernt.
      38 = Breite: der Ausschnitt ist 38 Pixel breit.
      30 = Hoehe: der Ausschnitt ist 30 Pixel hoch.

    Das Rechteck beginnt bei (42,8) und reicht bis (80,38), rechte/untere Kante
    EXKLUSIVE: X-Pixel 42 bis 79, Y-Pixel 8 bis 37. Es liegt im Kopfbereich dieses
    konkreten Sprites. Die letzten beiden Zahlen sind NICHT Endkoordinaten.

    Fuer einen 128x128-Frame muss X + Breite <= 128 und Y + Hoehe <= 128 sein.
    X/Y duerfen 0 sein; Breite und Hoehe muessen mindestens 4 Pixel betragen.

    Auswahl: ein wiedererkennbarer Kopf-/Rumpfbereich mit sichtbarer Struktur.
    Keine leere Transparenz, moeglichst nicht Beine, Arme oder flatternder Umhang.
    Bei Drehungen oder starken Posewechseln kann auch ein Kopf ungeeignet sein.

    auto: prueft mehrere strukturierte Ausschnitte im oberen Teil der sichtbaren
    Figur und waehlt einen anhand seiner Wiedererkennbarkeit in ALLEN Frames.
    Das ist KEINE sichere Erkennung des Koerpers. Geeignet als Versuch fuer
    aufrechte, auf der Stelle laufende Figuren. Fuer Effekte, Vierbeiner oder
    stark wechselnde Perspektiven besser einen passenden Ausschnitt manuell setzen.
    Wenn kein Kandidat die Pruefungen besteht, entsteht ein Dateifehler statt
    einer geratenen Korrektur. Andere Eingabedateien werden weiter verarbeitet.

    Eine manuelle ROI gilt fuer ALLE Dateien dieses Aufrufs. Unterschiedlich
    positionierte Figuren brauchen auto oder getrennte Ordner/Aufrufe.

  --roi-base N            Standard: nicht gesetzt (native Pixel)
    Setzt eine quadratische NxN-KOORDINATENREFERENZ fuer eine manuelle ROI.
    Beispiel: --roi 42,8,38,30 --roi-base 128
      Im 128x128-Frame bleibt das Rechteck 42,8,38,30.
      Im 512x512-Frame wird daraus 168,32,152,120.
      Im 640x640-Frame wird daraus 210,40,190,150.
    Umrechnung: X/Breite mit Framebreite/N, Y/Hoehe mit Framehoehe/N.
    Linke/obere und rechte/untere Kante werden auf ganze Pixel gerundet.
    Das skaliert NUR die Koordinaten, NICHT deine Bilder. Keine Interpolation.
    Ohne diese Option bleibt 42 auch in einem 640er-Frame genau 42 Pixel.
    Diese Umrechnung passt nur bei gleichartig skaliertem Motiv/gleicher Platzierung;
    sie erkennt weder andere Figuren noch verschobene Motive oder zusaetzliche Raender.
    Bei --roi auto ohne Wirkung. Mindestwert: 4; ROI muss in die Basis passen.

5. POSITIONSKORREKTUR
--------------------
  --stabilize smooth|lock|off       Standard: smooth
    smooth: glaettet die Position kreisfoermig; letzter und erster Frame gelten
      als Nachbarn. Gewolltes Wippen kann dabei ebenfalls abgeschwaecht werden.
    lock: richtet den Anker auf seine mittlere Position (auf ganze Pixel gerundeter Median) aus. Bei
      --strength 1 wird auch gewolltes Auf-und-ab weitgehend entfernt.
    off: keine Positionsverschiebung. Zusammen mit ausgeschaltetem
      --repair-cycle und --padding 0 bleiben die RGBA-Pixel unveraendert.
      Dateikodierung und Sheet-Anordnung koennen trotzdem anders sein.
      Ohne manuelle ROI wird in diesem Modus kein Auto-Anker gesucht.

  --strength WERT          Standard: 0.6; erlaubt: 0 bis 1
    Anteil der berechneten Korrektur. 0 = nichts, 1 = volle Korrektur.
    0.6 bedeutet 60 Prozent, NICHT 0.6 Pixel. --strength 0.4 ist vorsichtiger,
    --strength 1 staerker. Dezimalpunkt verwenden, nicht Dezimalkomma.
    Ergebnisse werden auf ganze Pixel gerundet. Deshalb koennen kleine Werte
    zu keiner sichtbaren Verschiebung fuehren. Mehr ist nicht automatisch besser.

  --passes N              Standard: 1; mindestens 1
    Wie oft der kreisfoermige Glaettungsfilter angewendet wird (nur smooth).
    Ein Durchgang mischt den vorigen, aktuellen und naechsten Anker mit
    Gewichten 1/4, 1/2, 1/4. Mehr Durchgaenge glaetten breiter und koennen
    absichtliche Bewegung staerker veraendern. Bei lock/off ohne Wirkung.

  --radius auto|N         Standard: auto
    Suchbereich in JEDER Richtung, relativ zum Anker in Frame 1.
    auto: max(8, round(8 * max(Framebreite, Framehoehe) / 128)).
      128x128 -> 8 Pixel, 512x512 -> 32 Pixel, 640x640 -> 40 Pixel.
    --radius 8 bedeutet dagegen IMMER genau 8 NATIVE Pixel, nicht 8 Frames.
    Der Radius ist NICHT die maximale Korrekturstaerke. Er ist die Suchweite.
    Ein Treffer direkt am Suchrand wird vorsichtshalber abgelehnt.
    Beispiel: --radius 48. Groessere Bereiche koennen aehnliche, falsche Stellen
    einschliessen. Die Qualitaetsgrenze --max-cost bleibt unveraendert.

  --max-cost WERT          Standard: 0.25; groesser als 0, maximal 1
    Obergrenze des normierten Template-Matching-Fehlers. Kleiner ist strenger.
    0 ist eine sehr gute Uebereinstimmung. 0.25 ist KEINE 75%-Sicherheit und
    KEINE Wahrscheinlichkeit. Ueberschreitet ein Frame die Grenze, wird diese
    manuelle ROI / dieser automatische Kandidat abgelehnt.
    Bei Problemen zuerst eine bessere ROI waehlen, nicht blind die Grenze erhoehen.

  --padding N             Standard: 0 Pixel; mindestens 0
    Transparenter Zusatzrand auf JEDER Seite, fuer alle Frames gleich.
    Beispiel: --padding 2 macht aus 128x128 einen 132x132-Frame.
    Der zusaetzliche Rand kann Platz fuer Verschiebungen schaffen.
    Reicht der Platz nicht, wird abgebrochen statt sichtbare Pixel abzuschneiden.
    Padding veraendert Frame-Groesse und Ursprung: Engine-Slicing/Pivot pruefen.
    Wer exakt 128x128 braucht, bleibt bei 0 und prueft eine passende Korrektur.

6. ZEIT UND SCHRITTPHASE
-----------------------
  --fps WERT              Standard: Quelldauer; statische Sheets 8 fps
    Frames pro Sekunde. --fps 8 gibt jedem Frame 125 Millisekunden.
    16 Frames bei 8 fps = 2 Sekunden. 14 Frames bei 8 fps = 1.75 Sekunden.
    Ohne diese Option behaelt eine Animation ihre gespeicherten Frame-Zeiten.
    Fehlende, ungueltige oder null Frame-Zeiten fallen auf 125 ms zurueck.
    --fps ueberschreibt auch variable Animationstaktung mit konstanten Werten.
    Das veraendert KEINE Pose und erzeugt KEINE neuen Zwischenbilder.
    Die PNG-Dateien speichern keine Abspielgeschwindigkeit: FPS/Dauern in der
    Engine setzen. report.json enthaelt die genauen Millisekunden pro Frame.
    GIF kann Zeiten nur in 10-ms-Schritten speichern (mindestens 10 ms im Export).
    Sehr hohe FPS lassen sich deshalb in der Vorschau nicht exakt wiedergeben.

  --repair-cycle          Standard: aus; ausdruecklich optional
    Sucht nach deutlichen Wiederholungen. Bei hinreichend klarer Wiederholung
    wird ein zusammenhaengender Abschnitt vollstaendiger Perioden behalten.
    Kann Frame-Anzahl und Dauer VERKUERZEN. Bei unsicherem Ergebnis oder stark
    wechselnden Quelldauern wird nicht zugeschnitten.
    Im bisherigen Beispiel wurden so Frames 2 bis 15 ausgewaehlt: 14 statt 16.
    Wer 16 behalten muss, benutzt diese Option NICHT.
    Sie ist kein allgemeiner Gangphasen-Detektor; Vorschau pruefen.

  WICHTIGE GRENZE
    16 Frames bleiben standardmaessig 16. Das Skript korrigiert Positionszittern,
    aber rekonstruiert keinen falsch getakteten 16-Frame-Bewegungsablauf.
    Ein Phasensprung kann trotz Positionskorrektur bestehen bleiben.
    Frame 16 muss nicht identisch mit Frame 1 sein; der Uebergang soll einen
    normalen Bewegungsschritt darstellen. Es werden keine Posen erfunden.

7. VOREINSTELLUNG FUER DEIN BEISPIEL
-----------------------------------
  --preset example16      Standard: keine spezielle Voreinstellung
    Setzt folgende Werte, sofern du sie nicht ausdruecklich ueberschreibst:
      --columns 16 --rows 1 --roi 42,8,38,30 --roi-base 128
      --stabilize smooth --strength 0.6 --fps 8
    --radius bleibt standardmaessig auto. --repair-cycle bleibt AUS.
    Diese Vorlage ist fuer deinen Sprite und gleichartig skalierte Fassungen
    gedacht. Quadratische Frames sind erforderlich; ihre native Groesse bleibt
    erhalten. Ein anderer Inhalt/anderer Rand wird nicht automatisch ausgeglichen.
    Sie ist KEINE universelle Vorlage fuer jeden beliebigen 16-Frame-Sprite.

    Kurzer Aufruf fuer einen Ordner gleich aufgebauter Dateien:
      python pyfix_loop.py "input" --preset example16 --out "fixed_16"

    Gleiche Vorlage, aber Anker pro Datei automatisch suchen:
      python pyfix_loop.py "input" --preset example16 --roi auto --out "fixed_auto"

    Gleiche Vorlage mit groesserem Suchbereich:
      python pyfix_loop.py "input" --preset example16 --radius 48 --out "fixed_r48"

8. HILFE, ERGEBNISSE UND FEHLER
------------------------------
  -h, --help              Zeigt Optionen und direkt kopierbare Beispiele.
  --help-exam             Zeigt diese ausfuehrliche Parameter-Erklaerung.
  --version               Zeigt die Versionsnummer.
  Auch erlaubt: python pyfix_loop.py help
                python pyfix_loop.py help-exam
  Hilfe benoetigt keine installierten Bildbibliotheken.

  Pro erfolgreich bearbeiteter Datei:
    sheet.png              Transparente RGBA-Frames in EINER horizontalen Reihe.
    frames/frame_001.png   Einzelbilder, beginnend bei 001.
    preview.gif            Vergroesserte Vorschau mit Frame-Nummern; optional.
    report.json            Raster/Timing, gewaehlte ROI, Verschiebungen, Warnungen.
    .pyfix-output          Markierung, damit Ergebnisse nicht erneut eingescannt werden.

  GIF ist nur eine undurchsichtige, farbreduzierte Vorschau, NICHT das Game-Asset.
  Fuer die Engine sheet.png oder frames/*.png verwenden.
  Report-Koordinaten: positives dx/dy = nach rechts/unten verschieben.
  Pixel werden ohne Interpolation kopiert; keine Weichzeichnung beim Verschieben.

  batch_report.json fasst den Lauf zusammen, auch Dateifehler und uebersprungene
  Ergebnisse. Bei weiteren Laeufen entsteht batch_report_002.json usw.; vorhandene
  Berichte werden nicht ersetzt. Dateifehler stoppen nicht den ganzen Stapel.
  Bei einem Einzeldatei-Aufruf ohne Batch gibt es nur report.json.

  Status GEANDERT: mindestens ein berechneter Versatz, Padding oder Zuschnitt.
  Status UNVERAENDERT: kein Eingriff in die RGBA-Frames noetig/berechnet.
  Das ist KEIN Qualitaetssiegel: Eine geaenderte Datei kann visuell schlechter sein.
  Status UEBERSPRUNGEN: Ergebnis existiert oder .gif/.apng ist ein nicht als Sheet erkennbares Einzelbild.
  Status DIAGNOSE: inspection.json/Bilder exportiert, KEINE Reparatur behauptet.
  Status FEHLER: Datei konnte nicht sicher verarbeitet werden; Details im Bericht.

  Rueckgabecode 0: Lauf beendet, keine Dateifehler (ggf. nur uebersprungen/leer).
  Rueckgabecode 1: mindestens eine Datei fehlgeschlagen; andere Ergebnisse existieren.
  Rueckgabecode 2: Aufruf-, Eingabe-/Zielordner-, Bibliotheks- oder globaler Schreibfehler.

  Unsicheres Auto-Raster -> --columns/--rows explizit angeben.
  Unsicherer Auto-Anker -> passende --roi setzen; --help-exam Abschnitt 4.
  Abschneiden am Rand -> --padding testen oder Korrektur/ROI ueberpruefen.
  Neue Parameter, aber Ergebnis existiert -> einen frischen --out-Ordner benutzen.
  Bei Dateifehlern entstehen Diagnosebilder/JSON unter AUSGABE/_diagnostics/DATEI/.
  Es entsteht KEIN als repariert ausgegebenes sheet.png, wenn Matching fehlschlaegt.
  Diagnoseordner sind getrennt von Ergebnissen; fehlgeschlagene Dateien koennen
  im selben --out erneut versucht werden. Erfolgreiche Ergebnisse bleiben geschuetzt.
  .gif mit PNG-Inhalt und einem Bild -> echte Animationsdatei besorgen/exportieren;
  blosses Umbenennen erzeugt keine zusaetzlichen Frames.
"""


def columns_arg(text: str) -> int | str:
    if text.lower() == "auto":
        return "auto"
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--columns braucht auto oder eine positive Zahl.") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("--columns muss mindestens 1 sein.")
    return value


def roi_arg(text: str) -> tuple[int, int, int, int] | str:
    return "auto" if text.lower() == "auto" else parse_roi(text)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=command_name(),
        description=("PyFix Loop 2.1 - Ordnerweise Sprite-Positionskorrektur.\n"
                     "Ohne Dateinamen: aktueller Ordner. Standard: alle Frames behalten,\n"
                     "Auto-Raster, Auto-Anker, sanfte Positionsglaettung. Originale bleiben erhalten."),
        epilog=rendered_help(HELP_EXAMPLES),
        formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog, width=96),
    )
    parser.add_argument("input", nargs="?", type=Path, default=Path("."), metavar="INPUT",
                        help="Ordner oder einzelne Datei; Standard: aktueller Arbeitsordner.")
    parser.add_argument("--help-exam", action="store_true", help="Jeden Parameter mit Einheiten und Auswahlhilfe erklaeren.")
    parser.add_argument("--version", action="version", version=f"PyFix Loop {VERSION}")
    io = parser.add_argument_group("Ordner und Ausgabe")
    io.add_argument("--recursive", "-r", action="store_true", help="Unterordner mitverarbeiten; Standard: aus.")
    io.add_argument("--out", type=Path, metavar="PFAD", help="Ergebnisordner; Standard: INPUT/pyfix_output (Details: --help-exam).")
    io.add_argument("--no-preview", action="store_true", help="Keine GIF-Vorschau exportieren.")
    io.add_argument("--inspect", action="store_true", help="Nur Format, Raster und ROI pruefen; Diagnosebilder/JSON, keine Korrektur.")
    grid = parser.add_argument_group("Raster und Zeit")
    grid.add_argument("--columns", type=columns_arg, metavar="auto|N", help="Spalten statischer Sheets; Standard: auto, quadratische Frames in einer Reihe.")
    grid.add_argument("--rows", type=int, metavar="N", help="Zeilen statischer Sheets; Standard: 1.")
    grid.add_argument("--count", type=int, metavar="N", help="Belegte Rasterzellen ab Zelle 1; Standard: alle; 2 bis 256.")
    grid.add_argument("--fps", type=float, metavar="WERT", help="Timing ueberschreiben; Standard: Quelldauern bzw. 8 fps bei Sheets.")
    correction = parser.add_argument_group("Korrektur")
    correction.add_argument("--preset", choices=("example16",), help="Vorlage fuer dein Sprite und gleichartig skalierte Fassungen; ROI-Basis 128.")
    correction.add_argument("--roi", type=roi_arg, metavar="auto|X,Y,B,H", help="Anker im ersten Frame, in Pixeln; Standard: auto.")
    correction.add_argument("--roi-base", type=int, metavar="N", help="ROI-Koordinaten aus einer NxN-Referenz umrechnen; ohne diese Option native Pixel.")
    correction.add_argument("--stabilize", choices=("smooth", "lock", "off"), help="Glaetten, festhalten, nur analysieren; Standard: smooth.")
    correction.add_argument("--strength", type=float, metavar="WERT", help="Korrekturanteil 0..1; Standard: 0.6.")
    correction.add_argument("--radius", type=radius_arg, default="auto", metavar="auto|N", help="Ankersuche in nativen Pixeln; auto: 8 bei 128x128, 40 bei 640x640.")
    correction.add_argument("--passes", type=int, default=1, metavar="N", help="Kreisfoermige Glaettungsdurchgaenge; Standard: 1.")
    correction.add_argument("--max-cost", type=float, default=0.25, metavar="WERT", help="Maximaler Matching-Fehler; Standard: 0.25; kleiner ist strenger.")
    correction.add_argument("--padding", type=int, default=0, metavar="N", help="Transparenter Rand je Seite, in Pixeln; Standard: 0.")
    correction.add_argument("--repair-cycle", action="store_true", help="Optionaler Wiederholungszuschnitt: kann Frames ENTFERNEN; Standard: aus.")
    return parser


def finalize_args(args: argparse.Namespace) -> argparse.Namespace:
    defaults = {"columns": "auto", "rows": 1, "roi": "auto",
                "stabilize": "smooth", "strength": 0.6}
    if args.preset == "example16":
        defaults.update(columns=16, rows=1, roi=(42, 8, 38, 30), roi_base=128, fps=8.0)
    for name, value in defaults.items():
        if getattr(args, name) is None:
            setattr(args, name, value)
    if args.roi_base is not None and args.roi_base < 4:
        raise ValueError("--roi-base muss mindestens 4 sein.")
    if args.rows < 1 or (args.radius != "auto" and args.radius < 1) or args.passes < 1 or args.padding < 0:
        raise ValueError("--rows/--radius/--passes muessen positiv, --padding nichtnegativ sein.")
    if args.columns == "auto" and args.rows != 1:
        raise ValueError("Bei --rows groesser als 1 auch --columns angeben.")
    if args.count is not None and not 2 <= args.count <= 256:
        raise ValueError("--count muss zwischen 2 und 256 liegen.")
    if (isinstance(args.columns, int) and args.count is not None
            and args.count > args.columns * args.rows):
        raise ValueError("--count ist groesser als --columns * --rows.")
    if not math.isfinite(args.strength) or not 0 <= args.strength <= 1:
        raise ValueError("--strength muss zwischen 0 und 1 liegen.")
    if not math.isfinite(args.max_cost) or not 0 < args.max_cost <= 1:
        raise ValueError("--max-cost muss groesser als 0 und maximal 1 sein.")
    if args.fps is not None and (not math.isfinite(args.fps) or args.fps <= 0):
        raise ValueError("--fps muss endlich und positiv sein.")
    return args


def settings_dict(args: argparse.Namespace) -> dict:
    names = ("columns", "rows", "count", "fps", "preset", "roi", "stabilize",
             "strength", "radius", "roi_base", "passes", "max_cost", "padding", "repair_cycle", "no_preview", "inspect")
    return {name: getattr(args, name) for name in names}


def process_file(path: Path, output: Path, args: argparse.Namespace) -> dict:
    """Compute first, then publish into an exclusively created result directory."""
    original, durations = read_frames(path, args.columns, args.rows, args.count, args.fps)
    if args.preset == "example16" and original[0].width != original[0].height:
        raise ValueError("--preset example16 erwartet quadratische Frames wie die 128x128-Referenz. Raster pruefen.")
    tracking = effective_tracking(args, original[0].size)
    radius = tracking["radius_pixels"]
    w, h = original[0].size
    print(f"    Dekodiert: {len(original)} Frames, je {w}x{h}; Suchradius {radius} px ({args.radius}).", flush=True)
    with Image.open(path) as source:
        animated = getattr(source, "n_frames", 1) > 1
        source_size = list(source.size)
        actual_format = source.format
    d = distance_matrix(original)
    diagnosis = repeat_diagnosis(d)
    report = {
        "tool": "PyFix Loop", "version": VERSION,
        "input_name": path.name, "input_format": actual_format,
        "input_animated": animated, "input_image_size": source_size,
        "input_frame_count": len(original), "input_frame_size": list(original[0].size),
        "input_durations_ms": durations, "input_duration_total_ms": float(sum(durations)),
        "settings": settings_dict(args), "effective_tracking": tracking,
        "diagnosis_before": diagnosis, "warnings": [],
    }
    if not animated and args.columns == "auto":
        report["warnings"].append("Auto-Raster: quadratische Frames in einer horizontalen Reihe angenommen; Zellgrenzen pruefen.")
    if animated and (args.columns != "auto" or args.rows != 1 or args.count is not None):
        report["warnings"].append("Animierte Quelle: --columns/--rows/--count nicht angewendet.")
    roi = tracking["roi_xywh"]
    if roi is not None:
        print(f"    ROI in nativen Pixeln: {','.join(map(str, roi))}"
              + (f" (Basis {args.roi_base})" if args.roi_base else ""), flush=True)
    if roi is None and args.stabilize != "off":
        roi, selection = auto_anchor(original, radius, args.max_cost)
        report["anchor_selection"] = selection
        report["warnings"].append("Auto-ROI ist eine Erscheinungsheuristik, kein sicherer Koerperanker; Ergebnis ansehen.")
    elif roi is not None:
        report["anchor_selection"] = {"mode": "manual", "roi_xywh": list(roi)}
    if roi is not None:
        positions, costs = track_anchor(original, roi, radius)
        if not np.all(np.isfinite(costs)):
            raise ValueError("Nicht endlicher Matching-Fehler. Einen anderen Anker waehlen.")
        report["anchor_before"] = {
            "roi_xywh": list(roi), "positions_relative_to_first_xy": positions.tolist(),
            "normalized_match_costs": costs.tolist(),
            "last_relative_to_first_xy": positions[-1].tolist(),
            "note": "Patch estimates, not ground-truth body/root coordinates.",
        }
    indices = list(range(len(original)))
    if args.repair_cycle:
        period = diagnosis["suggested_period"]
        if max(durations) / min(durations) > 1.15:
            report["warnings"].append("Variable Frame-Zeiten: automatischer Zykluszuschnitt ausgelassen.")
        elif period is None:
            report["warnings"].append("Keine ausreichend klare Wiederholung; keine Frames entfernt.")
        else:
            indices = whole_cycle_indices(d, period)
    selected = [original[i] for i in indices]
    selected_durations = [durations[i] for i in indices]
    offsets = np.zeros((len(selected), 2), dtype=np.int32)
    if args.stabilize != "off":
        assert roi is not None
        # Keep the reference patch in ORIGINAL frame 1, even after a cycle crop.
        # Shifts for the kept frames are indexed from the original tracking result.
        tracked = np.asarray(report["anchor_before"]["positions_relative_to_first_xy"])[indices]
        selected_costs = np.asarray(report["anchor_before"]["normalized_match_costs"])[indices]
        validate_matches(tracked, selected_costs, radius, args.max_cost)
        offsets = stabilization_offsets(tracked, args.stabilize, args.strength, args.passes)
        report["warnings"].append("Positionsglaettung kann gewolltes Wippen veraendern; falsche Schrittphasen werden nicht rekonstruiert.")
    corrected = move_frames(selected, offsets, args.padding)
    report["kept_source_frames_1_based"] = [i + 1 for i in indices]
    report["removed_source_frames_1_based"] = [i + 1 for i in range(len(original)) if i not in indices]
    report["correction_offsets_xy"] = offsets.tolist()
    report["common_padding_each_side"] = args.padding
    report["stabilization_mode"] = args.stabilize
    changed = bool(np.any(offsets) or args.padding or len(indices) != len(original))
    report["frames_changed"] = changed
    report["diagnosis_after"] = repeat_diagnosis(distance_matrix(corrected)) if changed else diagnosis
    if len(indices) != len(original):
        report["warnings"].append("Frame-Anzahl und Dauer veraendert; Engine-Einstellungen anpassen.")
    if args.fps is not None:
        report["warnings"].append("Timing durch --fps gesetzt; PNG-Dateien speichern keine Abspielgeschwindigkeit.")
    if args.fps is not None and args.fps > 100 and not args.no_preview:
        report["warnings"].append("GIF-Vorschau auf mindestens 10 ms/Frame begrenzt; report.json enthaelt das Soll-Timing.")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Work in a temporary sibling. Never reuse/delete a pre-existing result.
    with tempfile.TemporaryDirectory(prefix=".pyfix-tmp-", dir=output.parent) as folder:
        temporary = Path(folder)
        export(corrected, selected_durations, temporary, report, preview=not args.no_preview)
        output.mkdir(exist_ok=False)
        try:
            for item in temporary.iterdir():
                shutil.move(str(item), str(output / item.name))
        except BaseException:
            # This directory was created exclusively by this invocation.
            shutil.rmtree(output, ignore_errors=True)
            raise
    return report


def source_metadata(path: Path, checksum: bool = False) -> dict:
    """Inspect decoded content, not a file extension's promise."""
    info = {"input_name": path.name, "file_bytes": path.stat().st_size,
            "suffix": path.suffix.lower()}
    if checksum:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        info["sha256"] = digest.hexdigest()
    with Image.open(path) as source:
        info.update(format=source.format, mode=source.mode, image_size=list(source.size),
                    stored_image_count=int(getattr(source, "n_frames", 1)),
                    default_image=bool(source.info.get("default_image", False)))
    expected = {".png": "PNG", ".apng": "PNG", ".gif": "GIF", ".webp": "WEBP"}
    info["extension_matches_format"] = expected.get(path.suffix.lower()) == info["format"]
    return info


def runtime_metadata() -> dict:
    return {"python": sys.version.split()[0], "python_executable": sys.executable,
            "script_path": str(Path(__file__).resolve()), "pillow": PIL_VERSION,
            "numpy": np.__version__, "opencv": cv2.__version__}


def inspection_data(path: Path, args: argparse.Namespace,
                    error: str | None = None) -> tuple[dict, Image.Image | None]:
    """Read-only diagnostics. No matching, stabilization or cycle trimming."""
    record = {"tool": "PyFix Loop", "version": VERSION, "runtime": runtime_metadata(),
              "settings": settings_dict(args), "processing_error": error,
              "note": "Inspection only: no correction, no auto-anchor search, no success claim."}
    frame = None
    try:
        record["source"] = source_metadata(path, checksum=True)
        try:
            frames, durations = read_frames(path, args.columns, args.rows, args.count, args.fps)
            frame = frames[0]
            record.update(decoded_frame_count=len(frames), frame_size=list(frame.size),
                          durations_ms=durations, image_kind="decoded_frame_1")
        except (ValueError, OSError, EOFError, SyntaxError, OverflowError) as exc:
            record["decode_error"] = str(exc)
            # A screenshot/static image may still be useful diagnostically, but
            # never call its whole canvas an animation frame or a repaired loop.
            with Image.open(path) as source:
                source.seek(1 if source.info.get("default_image", False) else 0)
                frame = source.convert("RGBA").copy()
            record.update(decoded_frame_count=None, frame_size=None,
                          image_kind="source_first_image_NOT_decoded_frame")
        record["diagnostic_image_size"] = list(frame.size)
        record["alpha_bbox_xyxy"] = frame.getchannel("A").getbbox()
        if record["decoded_frame_count"] is not None:
            try:
                tracking = effective_tracking(args, frame.size)
                record["effective_tracking"] = tracking
                if tracking["roi_xywh"] is not None:
                    record["roi_statistics"] = patch_statistics(frame, tracking["roi_xywh"])
                else:
                    record["roi_note"] = "Auto-ROI: no patch selected in inspection mode."
            except ValueError as exc:
                record["roi_error"] = str(exc)
    except (ValueError, OSError, EOFError, SyntaxError, OverflowError) as exc:
        record["inspection_error"] = str(exc)
    return record, frame


def write_inspection(path: Path, output: Path, args: argparse.Namespace,
                     error: str | None = None) -> dict:
    """Export first image, native-pixel ROI outline and facts even for bad inputs."""
    record, frame = inspection_data(path, args, error)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pyfix-tmp-", dir=output.parent) as folder:
        temporary = Path(folder)
        if frame is not None:
            name = "first_frame.png" if record.get("decoded_frame_count") else "source_first_image.png"
            frame.save(temporary / name)
            # Annotated diagnostic only; NEVER used as a correction source.
            overlay = Image.new("RGBA", frame.size, (45, 45, 45, 255))
            overlay.alpha_composite(frame)
            draw = ImageDraw.Draw(overlay)
            bbox = record.get("alpha_bbox_xyxy")
            if bbox:
                l, t, r, b = bbox
                draw.rectangle((l, t, r - 1, b - 1), outline=(100, 200, 255, 255), width=max(1, frame.width // 200))
            roi = record.get("effective_tracking", {}).get("roi_xywh")
            if roi:
                x, y, rw, rh = roi
                draw.rectangle((x, y, x + rw - 1, y + rh - 1), outline=(255, 80, 80, 255), width=max(1, frame.width // 200))
            overlay.save(temporary / "roi_overlay.png")
            record["diagnostic_images"] = {
                "first_image": name, "overlay": "roi_overlay.png",
                "legend": "Blue: alpha bbox. Red: requested ROI in native pixels, only when explicitly set. No red box with ROI auto."}
        (temporary / OUTPUT_MARKER).write_text(VERSION + "\n", encoding="utf-8")
        (temporary / "inspection.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        output.mkdir(exist_ok=False)
        try:
            for entry in temporary.iterdir():
                shutil.move(str(entry), str(output / entry.name))
        except BaseException:
            shutil.rmtree(output, ignore_errors=True)
            raise
    return record


def save_failure_diagnostics(path: Path, root: Path, relative: Path,
                             args: argparse.Namespace, error: str) -> Path:
    """Keep diagnostics separate from successful results so retry is possible."""
    parent = root / "_diagnostics" / relative.parent
    if not is_within(parent.resolve(), root.resolve()):
        raise OSError("Diagnoseziel fuehrt ueber einen Link aus dem Ausgabeordner heraus.")
    parent.mkdir(parents=True, exist_ok=True)
    (parent / OUTPUT_MARKER).touch(exist_ok=True)
    for n in range(1, 10000):
        destination = parent / (relative.name if n == 1 else f"{relative.name}_{n:03d}")
        if destination.exists() or destination.is_symlink():
            continue
        try:
            write_inspection(path, destination, args, error)
            return destination
        except FileExistsError:
            continue
    raise OSError("Zu viele Diagnoseordner; frischen --out-Ordner verwenden.")


def is_within(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def collect_inputs(source: Path, output: Path, recursive: bool) -> list[Path]:
    if source.is_file():
        return [source]
    found = []
    def walk_error(exc: OSError) -> None:
        raise exc
    for current_text, dirs, files in os.walk(source, followlinks=False, onerror=walk_error):
        current = Path(current_text)
        if is_within(current, output) or (current / OUTPUT_MARKER).exists():
            dirs[:] = []
            continue
        dirs[:] = sorted(
            name for name in dirs
            if not name.startswith(".") and name != "__pycache__"
            and not (current / name).is_symlink()
            and not is_within(current / name, output)
            and not (current / name / OUTPUT_MARKER).exists()
        ) if recursive else []
        for name in sorted(files):
            path = current / name
            if (not name.startswith(".") and not path.is_symlink()
                    and path.suffix.lower() in SUPPORTED_EXTENSIONS):
                found.append(path)
    return sorted(found)


def write_batch_report(output: Path, report: dict) -> Path:
    text = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    for index in range(1, 100000):
        name = "batch_report.json" if index == 1 else f"batch_report_{index:03d}.json"
        target = output / name
        try:
            with target.open("x", encoding="utf-8") as handle:
                handle.write(text)
            return target
        except FileExistsError:
            continue
    raise OSError("Zu viele vorhandene Batch-Berichte; anderen --out-Ordner verwenden.")


def run(args: argparse.Namespace) -> int:
    source = args.input.expanduser().resolve()
    if not source.exists() or not (source.is_file() or source.is_dir()):
        raise ValueError(f"Eingabe nicht gefunden: {source}")
    is_batch = source.is_dir()
    if is_batch and (source / OUTPUT_MARKER).exists():
        raise ValueError("Der Eingabeordner ist als PyFix-Ergebnisordner markiert. Originalordner waehlen.")
    if not is_batch and source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unterstuetzte Dateiendungen: .png, .apng, .gif, .webp.")
    folder_name = "pyfix_inspect" if args.inspect else "pyfix_output"
    if args.out is None:
        output = (source / folder_name) if is_batch else (source.parent / folder_name / source.name)
    else:
        output = args.out.expanduser().resolve()
    if is_within(source, output):
        raise ValueError("--out darf weder Eingabe noch deren Oberordner sein. Separaten Zielordner verwenden.")
    if output.exists() and not output.is_dir():
        raise ValueError(f"Ziel ist kein Ordner: {output}")
    files = collect_inputs(source, output, args.recursive)
    if not files:
        print("Keine PNG/APNG/GIF/WebP-Eingaben gefunden. Nichts geschrieben.")
        return 0
    if is_batch:
        output.mkdir(parents=True, exist_ok=True)
        try:
            with (output / OUTPUT_MARKER).open("x", encoding="utf-8") as handle:
                handle.write(VERSION + "\n")
        except FileExistsError:
            pass
    results = []
    counts = {"changed": 0, "unchanged": 0, "inspected": 0, "skipped": 0, "error": 0}
    mode = "DIAGNOSE, keine Korrektur" if args.inspect else "KORREKTUR"
    print(f"PyFix Loop {VERSION} | {len(files)} Datei(en) | {mode} | Frames behalten: {'NEIN, Zuschnitt erlaubt' if args.repair_cycle else 'JA'}", flush=True)
    for number, path in enumerate(files, 1):
        relative = path.relative_to(source) if is_batch else Path(path.name)
        destination = output / relative if is_batch else output
        item = {"input": relative.as_posix(), "output": str(destination)}
        if destination.exists():
            item.update(status="skipped", reason="Ergebnis existiert; unveraendert belassen. Neuer Versuch: anderen --out-Ordner waehlen.")
            print(f"[{number}/{len(files)}] UEBERSPRUNGEN {relative}: Ergebnis existiert.", flush=True)
        elif is_batch and not is_within(destination.resolve(), output.resolve()):
            item.update(status="error", error="Zielpfad fuehrt ueber einen symbolischen Link aus dem Ausgabeordner heraus.")
            print(f"[{number}/{len(files)}] FEHLER {relative}: {item['error']}", flush=True)
        else:
            print(f"[{number}/{len(files)}] DATEI {relative}", flush=True)
            try:
                try:
                    meta = source_metadata(path)
                except (ValueError, OSError, EOFError, SyntaxError, OverflowError):
                    if not args.inspect:
                        raise
                    meta = None  # --inspect still writes an explicit error report.
                if meta is not None:
                    item["source"] = meta
                    width, height = meta["image_size"]
                    print(f"    Inhalt: {meta['format']} {width}x{height}, {meta['stored_image_count']} gespeicherte(s) Bild(er).", flush=True)
                    if not meta["extension_matches_format"]:
                        print(f"    HINWEIS: Dateiendung {meta['suffix']} passt nicht zum erkannten Format {meta['format']}.", flush=True)
                if args.inspect:
                    record = write_inspection(path, destination, args)
                    problems = [record[k] for k in ("inspection_error", "decode_error", "roi_error") if k in record]
                    item.update(status="inspected", diagnostic_notes=problems)
                    if record.get("frame_size"):
                        w, h = record["frame_size"]
                        print(f"    Raster: {record['decoded_frame_count']} Frames, je {w}x{h}.", flush=True)
                    if "effective_tracking" in record:
                        print(f"    Suchradius: {record['effective_tracking']['radius_pixels']} px.", flush=True)
                    if "roi_statistics" in record:
                        stats = record["roi_statistics"]
                        print(f"    ROI {stats['roi_xywh']}; im Frame: {stats['inside_frame']}; sichtbare Pixel: {stats.get('visible_pixels', 'n/a')}.", flush=True)
                    for problem in problems:
                        print(f"    DIAGNOSE-HINWEIS: {problem}", flush=True)
                    print(f"    DIAGNOSE exportiert: {destination}", flush=True)
                else:
                    report = process_file(path, destination, args)
                    status = "changed" if report["frames_changed"] else "unchanged"
                    item.update(status=status, input_frames=report["input_frame_count"],
                                output_frames=report["output"]["frame_count"], warnings=report["warnings"])
                    label = "GEANDERT" if status == "changed" else "UNVERAENDERT"
                    print(f"    {label}: {item['input_frames']} -> {item['output_frames']} Frames", flush=True)
                    if "anchor_selection" in report:
                        a = report["anchor_selection"]
                        print(f"    ROI ({a['mode']}): {','.join(str(v) for v in a['roi_xywh'])}", flush=True)
                    for warning in report["warnings"]:
                        print(f"    HINWEIS: {warning}", flush=True)
            except (ValueError, OSError, cv2.error, EOFError, SyntaxError, OverflowError) as exc:
                status = "skipped" if isinstance(exc, NotAnimationError) else "error"
                item.update(status=status)
                item["reason" if status == "skipped" else "error"] = str(exc)
                print(f"    {'UEBERSPRUNGEN' if status == 'skipped' else 'FEHLER'}: {exc}", flush=True)
                if not args.inspect:
                    try:
                        diagnostic_root = output if is_batch else output.parent
                        diagnostic_path = save_failure_diagnostics(path, diagnostic_root, relative, args, str(exc))
                        item["diagnostics"] = str(diagnostic_path)
                        print(f"    Diagnosebilder/JSON: {diagnostic_path}", flush=True)
                    except (ValueError, OSError, cv2.error, EOFError, SyntaxError, OverflowError) as diagnostic_exc:
                        item["diagnostic_error"] = str(diagnostic_exc)
                        print(f"    Diagnose konnte nicht geschrieben werden: {diagnostic_exc}", flush=True)
        counts[item["status"]] += 1
        results.append(item)
    if is_batch:
        summary = {"tool": "PyFix Loop", "version": VERSION, "runtime": runtime_metadata(),
                   "input_folder": str(source), "output_folder": str(output),
                   "settings": settings_dict(args), "recursive": args.recursive,
                   "counts": counts, "files": results}
        summary_path = write_batch_report(output, summary)
        print(f"Batch-Bericht: {summary_path}")
    print(f"Fertig: {counts['changed']} geaendert, {counts['unchanged']} unveraendert, "
          f"{counts['inspected']} diagnostiziert, {counts['skipped']} uebersprungen, {counts['error']} Fehler.")
    print(f"Ergebnis: {output}")
    return 1 if counts["error"] else 0


def main(argv: Sequence[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if values and values[0] in ("help", "help-exam"):
        values[0] = "--" + values[0]
    parser = make_parser()
    # Extended help is available independently of optional dependency loading.
    if "--help-exam" in values:
        print(rendered_help(HELP_EXAM).strip())
        return 0
    args = parser.parse_args(values)
    try:
        finalize_args(args)
        if _IMPORT_ERROR is not None:
            raise ValueError(
                f"Bildbibliothek fehlt: {_IMPORT_ERROR}. Installation: "
                "python -m pip install numpy Pillow opencv-python-headless")
        return run(args)
    except (ValueError, OSError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nAbgebrochen. Bereits abgeschlossene Ergebnisse bleiben erhalten.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
