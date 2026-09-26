#!/usr/bin/env python3
"""Gezielte Loop-Fixes mit unveränderter Framezahl, einschließlich 16, 12, 10 und 8 Frames.

Vollständig eigenständiges Programm. Pakete stehen in der lokalen venv.txt.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile

try:
    import numpy as np
    from PIL import Image
except ImportError as exc:
    print(f"Fehlendes Paket: {exc}. Benötigt werden numpy und pillow aus venv.txt.", file=sys.stderr)
    raise SystemExit(1)

VERSION = "2.0.0"
MIN_FRAMES, MAX_FRAMES = 3, 24
GRID_PATTERN = r"(?<!\d)([1-9]\d*)[xX]([1-9]\d*)(?!\d)"


class CannotFix(ValueError):
    """Gültige Eingabe, aber keine verlässliche Korrektur mit dieser Methode."""


@dataclass
class Animation:
    path: Path
    frames: list
    cols: int
    rows: int
    durations: list | None
    metadata: dict
    png_options: dict
    source_sha256: str


@dataclass
class FixPlan:
    frames: list
    cols: int
    rows: int
    durations: list | None
    method: str
    info: dict


def add_common_arguments(parser):
    parser.add_argument("files", nargs="*", type=Path, help="Einzelne PNGs; sonst PNGs im aktuellen Arbeitsordner")
    parser.add_argument("-f", "--frame", type=int, help="Framezahl 3..24; alternativ aus Raster oder .anim.json")
    parser.add_argument("--grid", default="auto", help="auto, horizontal, vertical oder z.B. 4x4, 4x3, 5x2, 4x2")
    parser.add_argument("--metadata", type=Path, help="Metadaten für genau eine Datei; sonst <Dateistamm>.anim.json")
    parser.add_argument("--trust-grid", action="store_true", help="Veralteten Rasterhinweis im Dateinamen mit explizitem Raster übergehen")
    parser.add_argument("--end-is-duplicate", action="store_true", help="Schlussframe ausdrücklich als doppelte Pose bestätigen, auch wenn die Pixel leicht abweichen")
    timing = parser.add_mutually_exclusive_group()
    timing.add_argument("--fps", type=float, help="Bekannte Wiedergabe-FPS; ohne Zeitangabe wird keine FPS erfunden")
    timing.add_argument("--durations", help="Bekannte Framezeiten in ms, kommagetrennt")
    parser.add_argument("--apply", action="store_true", help="Geprüften Fix als neue PNG und .anim.json speichern; sonst nur Vorschau im Terminal")
    parser.add_argument("--output-dir", type=Path, help="Zielordner; Standard: neben dem jeweiligen Original")
    parser.add_argument("--suffix", default="_loopfix", help="Zusatz für Ausgabedateien, Standard _loopfix")
    parser.add_argument("--replace-output", action="store_true", help="Vorhandene Fix-Ausgaben ersetzen")
    parser.add_argument("--version", action="version", version=VERSION)


def validate_args(args):
    if args.frame is not None and not MIN_FRAMES <= args.frame <= MAX_FRAMES:
        raise ValueError("--frame muss zwischen 3 und 24 liegen.")
    if not args.suffix or any(c in args.suffix for c in "/\\") or args.suffix in {".", ".."}:
        raise ValueError("--suffix muss ein nichtleerer Dateinamenzusatz ohne Verzeichnisse sein.")
    if args.fps is not None and (not math.isfinite(args.fps) or not 0 < args.fps <= 240):
        raise ValueError("--fps muss endlich und größer als 0, höchstens 240 sein.")
    if args.trust_grid and args.grid == "auto":
        raise ValueError("--trust-grid verlangt ein explizites --grid.")


def parse_grid(value):
    if isinstance(value, str) and re.fullmatch(r"[1-9]\d*[xX][1-9]\d*", value):
        return tuple(map(int, value.lower().split("x")))
    if isinstance(value, dict):
        values = (value.get("cols", value.get("columns")), value.get("rows"))
        if all(type(v) is int and v > 0 for v in values):
            return values
    raise ValueError("Raster erwartet SpaltenxZeilen oder ein Objekt mit cols/rows.")


def choose_layout(size, count, mode):
    width, height = size
    if mode == "horizontal":
        cols, rows = count, 1
    elif mode == "vertical":
        cols, rows = 1, count
    elif mode == "auto":
        candidates = []
        for cols in range(1, count+1):
            if count % cols:
                continue
            rows = count//cols
            if width % cols == 0 and height % rows == 0:
                score = abs(math.log((width/cols)/(height/rows)))+.12*abs(cols-rows)
                candidates.append((score, cols, rows))
        if not candidates:
            raise ValueError("Kein gleichmäßiges Raster gefunden; --grid explizit angeben.")
        _, cols, rows = min(candidates)
    else:
        cols, rows = parse_grid(mode)
    if cols*rows != count:
        raise ValueError("Framezahl und Raster widersprechen sich.")
    if width < cols or height < rows or width % cols or height % rows:
        raise ValueError("Bildgröße ist nicht ohne Rest durch das Raster teilbar.")
    return cols, rows


def resolve_timing(args, metadata, count):
    if args.durations is not None:
        values = [float(v.strip()) for v in args.durations.split(",")]
    elif args.fps is not None:
        values = [1000./args.fps]*count
    elif "durations_ms" in metadata:
        values = metadata["durations_ms"]
    elif "fps" in metadata:
        fps = metadata["fps"]
        if type(fps) not in (int, float) or not math.isfinite(fps) or not 0 < fps <= 240:
            raise ValueError("Metadaten-FPS müssen endlich und in 0..240 liegen.")
        values = [1000./fps]*count
    else:
        return None
    if not isinstance(values, list) or len(values) != count or any(
            type(v) not in (int, float) or not math.isfinite(v) or not 0 < v <= 30000 for v in values):
        raise ValueError("Für jeden Frame ist eine endliche Dauer größer 0, höchstens 30000 ms nötig.")
    return [float(v) for v in values]


def load_animation(path, args):
    metadata_path = args.metadata or path.with_suffix(".anim.json")
    if args.metadata and not metadata_path.is_file():
        raise ValueError(f"Metadaten fehlen: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    if not isinstance(metadata, dict):
        raise ValueError("Animations-Metadaten müssen ein JSON-Objekt sein.")
    meta_grid = parse_grid(metadata["grid"]) if "grid" in metadata else None
    explicit = parse_grid(args.grid) if args.grid not in {"auto", "horizontal", "vertical"} else None
    hints = list(re.finditer(GRID_PATTERN, path.stem))
    name_grid = tuple(map(int, hints[-1].groups())) if hints and not args.trust_grid else None
    counts = [v for v in (args.frame, metadata.get("frames"),
                          math.prod(meta_grid) if meta_grid else None,
                          math.prod(explicit) if explicit else None,
                          math.prod(name_grid) if name_grid else None) if v is not None]
    if not counts:
        raise ValueError("Framezahl unbekannt: -f, --grid oder .anim.json angeben.")
    if any(type(v) is not int or not MIN_FRAMES <= v <= MAX_FRAMES for v in counts):
        raise ValueError("Framezahlen müssen ganze Zahlen von 3 bis 24 sein.")
    if len(set(counts)) != 1:
        raise ValueError(f"Framezahl/Raster widersprechen sich: {counts}.")
    count = counts[0]
    grids = [v for v in (explicit, meta_grid, name_grid) if v is not None]
    if len(set(grids)) > 1:
        raise ValueError("Rasterangaben in Dateiname, Metadaten und --grid widersprechen sich.")
    mode = args.grid
    if mode == "auto" and grids:
        mode = f"{grids[0][0]}x{grids[0][1]}"
    data = path.read_bytes()
    with Image.open(io.BytesIO(data)) as source:
        if source.format != "PNG" or getattr(source, "n_frames", 1) != 1:
            raise ValueError("Erwartet wird ein statisches PNG-Spritesheet.")
        cols, rows = choose_layout(source.size, count, mode)
        if grids and (cols, rows) != grids[0]:
            raise ValueError("--grid widerspricht dem Rasterhinweis.")
        fw, fh = source.width//cols, source.height//rows
        frames = [source.crop((i % cols*fw, i//cols*fh, (i % cols+1)*fw, (i//cols+1)*fh)).convert("RGBA")
                  for i in range(count)]
        options = {key: source.info[key] for key in ("icc_profile", "dpi") if key in source.info}
    return Animation(path, frames, cols, rows, resolve_timing(args, metadata, count),
                     metadata, options, hashlib.sha256(data).hexdigest())


def visible_equal(a, b):
    """Exakter Vergleich sichtbarer RGBA-Werte; unsichtbares RGB zählt nicht."""
    aa, bb = np.asarray(a), np.asarray(b)
    if aa.shape != bb.shape or not np.array_equal(aa[..., 3], bb[..., 3]):
        return False
    visible = aa[..., 3] > 0
    return np.array_equal(aa[..., :3][visible], bb[..., :3][visible])


def closing_duplicates(frames, confirmed=False):
    if not np.asarray(frames[0])[..., 3].any():
        raise CannotFix("Der erste Frame ist vollständig transparent; keine verlässliche Schlussposen-Korrektur.")
    if all(visible_equal(frames[0], frame) for frame in frames[1:]):
        raise CannotFix("Die gesamte Folge ist statisch. Ein doppelter Schlussframe ist damit nicht als Loop-Fehler bestimmbar.")
    end = len(frames)
    while end > 1 and visible_equal(frames[0], frames[end-1]):
        end -= 1
    return list(range(end+1, len(frames)+1)) or ([len(frames)] if confirmed else [])


def rebuild(frames, cols, rows):
    if len(frames) != cols*rows:
        raise ValueError("Ausgaberaster muss genau einen Platz je Frame enthalten.")
    width, height = frames[0].size
    sheet = Image.new("RGBA", (cols*width, rows*height))
    for index, frame in enumerate(frames):
        if frame.size != (width, height):
            raise ValueError("Frames haben unterschiedliche Zellgrößen.")
        # Kopieren statt Überblenden erhält auch halbtransparente und unsichtbare RGB-Werte.
        sheet.paste(frame, (index % cols*width, index//cols*height))
    return sheet


def output_paths(animation, plan, args):
    stem = animation.path.stem
    if (plan.cols, plan.rows) != (animation.cols, animation.rows):
        hints = list(re.finditer(GRID_PATTERN, stem))
        grid = f"{plan.cols}x{plan.rows}"
        if hints:
            match = hints[-1]
            stem = stem[:match.start()]+grid+stem[match.end():]
        else:
            stem += "_"+grid
    directory = args.output_dir if args.output_dir is not None else animation.path.parent
    image_path = directory/(stem+args.suffix+".png")
    return image_path, image_path.with_suffix(".anim.json")


def output_metadata(animation, plan):
    metadata = {"frames": len(plan.frames), "grid": {"cols": plan.cols, "rows": plan.rows},
                "fix": {"tool": Path(__file__).stem, "version": VERSION, "method": plan.method,
                        "source": animation.path.name, "source_sha256": animation.source_sha256,
                        "source_frames": len(animation.frames), "output_frames": len(plan.frames), **plan.info}}
    if plan.durations is not None:
        metadata["durations_ms"] = plan.durations
        if max(plan.durations)-min(plan.durations) < 1e-9:
            metadata["fps"] = 1000./plan.durations[0]
    if "regions_profile" in animation.metadata:
        metadata["regions_profile"] = animation.metadata["regions_profile"]
    return metadata


def save_output(animation, plan, args, paths):
    image_path, metadata_path = paths
    if image_path.resolve() == animation.path.resolve():
        raise ValueError("Die Ausgabedatei darf nicht das Original sein.")
    original_metadata = args.metadata or animation.path.with_suffix(".anim.json")
    if metadata_path.resolve() == original_metadata.resolve():
        raise ValueError("Die Ausgabemetadaten dürfen nicht die Original-Metadaten ersetzen.")
    for path in paths:
        if path.exists() and (not args.replace_output or not path.is_file()):
            raise ValueError(f"Ausgabe existiert bereits: {path}; bei Bedarf --replace-output verwenden.")
    image_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pyimgfix-", dir=image_path.parent) as stage_name:
        stage = Path(stage_name)
        staged = (stage/"result.png", stage/"result.anim.json")
        rebuild(plan.frames, plan.cols, plan.rows).save(staged[0], **animation.png_options)
        staged[1].write_text(json.dumps(output_metadata(animation, plan), ensure_ascii=False,
                                        indent=2, allow_nan=False)+"\n", encoding="utf-8")
        backups, installed = {}, []
        for index, path in enumerate(paths):
            if path.exists():
                backups[path] = stage/f"backup-{index}"
                shutil.copy2(path, backups[path])
        try:
            for source, target in zip(staged, paths):
                if args.replace_output:
                    source.replace(target)
                else:
                    # Hardlink im selben Dateisystem verhindert versehentliches Überschreiben bei Kollisionen.
                    import os
                    os.link(source, target)
                installed.append(target)
        except OSError:
            for target in reversed(installed):
                if target in backups:
                    backups[target].replace(target)
                else:
                    target.unlink(missing_ok=True)
            raise


def selected_files(args):
    if args.files:
        files = args.files
    else:
        files = [p for p in sorted(Path.cwd().glob("*.png"))
                 if not p.stem.endswith((args.suffix, "_loopfix", "_dropend_loopfix"))]
    if not files:
        raise ValueError("Keine PNG-Dateien ausgewählt.")
    if args.metadata and len(files) != 1:
        raise ValueError("--metadata gehört zu genau einer PNG-Datei.")
    if len({p.resolve() for p in files}) != len(files):
        raise ValueError("Eine Eingabedatei wurde mehrfach ausgewählt.")
    return files


def run(args):
    validate_args(args)
    validate_specific_args(args)
    files = selected_files(args)
    outcomes, reserved = [], set()
    inputs = {path.resolve() for path in files}
    for path in files:
        try:
            animation = load_animation(path, args)
            print(f"\n📄 {path.name} | {len(animation.frames)} Frames | {animation.cols}x{animation.rows}")
            plan = make_plan(animation, args)
            if plan is None:
                outcomes.append(0)
                continue
            paths = output_paths(animation, plan, args)
            if paths[0].resolve() in inputs or any(p.resolve() in reserved for p in paths):
                raise ValueError("Ausgabe kollidiert mit einer Eingabe oder einem anderen Ergebnis dieses Laufs.")
            reserved.update(p.resolve() for p in paths)
            print(f"   {plan.method}: {len(animation.frames)} → {len(plan.frames)} Frames | Raster {plan.cols}x{plan.rows}")
            if animation.durations is None:
                print("   FPS unbekannt: In den neuen Metadaten wird keine Wiedergabegeschwindigkeit vorgegeben.")
            else:
                print(f"   Loopdauer: {sum(animation.durations):g} → {sum(plan.durations):g} ms")
            print(f"   Ausgabe: {paths[0]} und {paths[1].name}")
            if args.apply:
                save_output(animation, plan, args, paths)
                print("   ✓ Fix als neue Dateien gespeichert.")
            else:
                print("   Vorschau: keine Dateien geschrieben. Speichern mit --apply.")
            outcomes.append(0)
        except CannotFix as exc:
            print(f"   Keine verlässliche Korrektur: {exc}")
            fallback_hint(args)
            outcomes.append(3)
        except (OSError, ValueError, TypeError) as exc:
            print(f"   Fehler bei {path.name}: {exc}", file=sys.stderr)
            outcomes.append(2)
    print("\nFertig. Original-PNGs und Original-Metadaten bleiben erhalten.")
    return 2 if 2 in outcomes else 3 if 3 in outcomes else 0


def main(argv=None):
    args = parse_args(argv)
    try:
        return run(args)
    except (OSError, ValueError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Abbruch durch Benutzer.", file=sys.stderr)
        return 130


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Gezielte Sprite-Loop-Korrektur. Framezahl bleibt erhalten: 16→16, 12→12, 10→10, 8→8 (3..24).")
    add_common_arguments(parser)
    parser.add_argument("--fix", choices=("inspect", "duplicate-end", "position"), default="inspect",
                        help="inspect: Befund; duplicate-end: Loop neu interpolieren; position: gezielte Zonenverschiebung")
    parser.add_argument("--sampling", choices=("linear", "nearest"), default="linear",
                        help="Zwischenbilder: linear für weiche Bewegung; nearest für harte Pixelkanten")
    parser.add_argument("--max-warp-error", type=float, default=.20,
                        help="Höchster erlaubter sichtbarer Rekonstruktionsfehler (0..1), Standard 0.20")
    parser.add_argument("--alpha-threshold", type=int, default=8)
    parser.add_argument("--region", choices=("auto", "full", "top", "middle", "bottom"), default="auto")
    parser.add_argument("-s", "--strength", type=float, default=1.)
    parser.add_argument("--max-shift", type=float, default=32.)
    parser.add_argument("--min-suspicion", type=float, default=1.25)
    return parser.parse_args(argv)


def validate_specific_args(args):
    if args.apply and args.fix == "inspect":
        raise ValueError("Zum Speichern eine Korrektur mit --fix duplicate-end oder --fix position auswählen.")
    for name, value, low, high in (("max-warp-error", args.max_warp_error, 0, 1),
                                   ("strength", args.strength, 0, 1),
                                   ("max-shift", args.max_shift, 0, 10000),
                                   ("min-suspicion", args.min_suspicion, 0, 10000)):
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"--{name} muss endlich und zwischen {low} und {high} sein.")
    if not 0 <= args.alpha_threshold <= 254:
        raise ValueError("--alpha-threshold muss 0..254 sein.")


def fallback_hint(args):
    if args.fix == "duplicate-end":
        print("   Notfallvariante separat: PyImgAnimFixDropEnd.py entfernt den Schlussframe und reduziert die Framezahl.")


def require_opencv():
    try:
        import cv2
    except ImportError as exc:
        raise ValueError("Für Zwischenbilder fehlt opencv-python-headless. Pakete aus der lokalen venv.txt installieren.") from exc
    return cv2


def premultiplied(frame):
    rgba = np.asarray(frame, dtype=np.float32)/255.
    rgba[..., :3] *= rgba[..., 3:4]
    return rgba


def optical_flow_pair(a, b, args, cv):
    aa, bb = premultiplied(a), premultiplied(b)
    # Alpha trägt auch bei schwarzem Motiv auf transparentem Grund sichtbare Konturen.
    def gray(rgba):
        light = np.sum(rgba[..., :3]*np.asarray([.299, .587, .114], dtype=np.float32), axis=2)
        return np.rint(np.clip(.8*light+.2*rgba[..., 3], 0, 1)*255).astype(np.uint8)
    ga, gb = gray(aa), gray(bb)
    forward = cv.calcOpticalFlowFarneback(ga, gb, None, .5, 4, 21, 5, 7, 1.5, 0)
    backward = cv.calcOpticalFlowFarneback(gb, ga, None, .5, 4, 21, 5, 7, 1.5, 0)
    if not np.isfinite(forward).all() or not np.isfinite(backward).all():
        raise CannotFix("Bewegungsschätzung enthält ungültige Werte.")
    height, width = aa.shape[:2]
    xx, yy = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    errors, consistency = [], []
    subject_heights = []
    for source, target, movement, reverse in ((aa, bb, forward, backward), (bb, aa, backward, forward)):
        visible = source[..., 3] > args.alpha_threshold/255.
        ys, xs = np.where(visible)
        if len(xs) < 16:
            raise CannotFix("Zu wenig sichtbare Pixel für verlässliche Zwischenbilder.")
        subject_heights.append(int(ys.max()-ys.min()+1))
        mx, my = xx+movement[..., 0], yy+movement[..., 1]
        reconstructed = cv.remap(target, mx, my, cv.INTER_LINEAR, borderMode=cv.BORDER_CONSTANT)
        delta = np.abs(reconstructed-source)[visible]
        errors.append(float(max(delta[:, 3].mean(), delta[:, :3].mean())))
        reverse_here = cv.remap(reverse, mx, my, cv.INTER_LINEAR, borderMode=cv.BORDER_REPLICATE)
        consistency.append(float(np.quantile(np.linalg.norm(movement+reverse_here, axis=2)[visible], .90)))
    limit = max(2., max(subject_heights)*.05)
    if max(errors) > args.max_warp_error or max(consistency) > limit:
        raise CannotFix(f"Bewegung zwischen zwei Posen nicht verlässlich: Bildfehler {max(errors):.3f} "
                        f"(Grenze {args.max_warp_error:.3f}), Gegenprüfung {max(consistency):.2f}px (Grenze {limit:.2f}px).")
    return aa, bb, forward, backward, xx, yy, max(errors)


def interpolate_pair(pair, fraction, sampling, cv):
    aa, bb, forward, backward, xx, yy, _ = pair
    interpolation = cv.INTER_NEAREST if sampling == "nearest" else cv.INTER_LINEAR
    def warp(source, flow, amount):
        # Rückwärtsabbildung des vorwärts geschätzten Flusses iterativ bestimmen.
        mx, my = xx.copy(), yy.copy()
        for _ in range(4):
            local = cv.remap(flow, mx, my, cv.INTER_LINEAR, borderMode=cv.BORDER_REPLICATE)
            mx, my = xx-amount*local[..., 0], yy-amount*local[..., 1]
        return cv.remap(source, mx, my, interpolation, borderMode=cv.BORDER_CONSTANT)
    left, right = warp(aa, forward, fraction), warp(bb, backward, 1-fraction)
    mixed = (1-fraction)*left+fraction*right
    alpha = np.clip(mixed[..., 3:4], 0, 1)
    rgb = np.divide(mixed[..., :3], alpha, out=np.zeros_like(mixed[..., :3]), where=alpha > 1e-8)
    rgba = np.rint(np.clip(np.concatenate((rgb, alpha), axis=2), 0, 1)*255).astype(np.uint8)
    rgba[rgba[..., 3] == 0, :3] = 0
    return Image.fromarray(rgba)


def keep_count_plan(animation, args, duplicates):
    count = len(animation.frames)
    source_count = count-len(duplicates)
    if source_count < 3:
        raise CannotFix("Nach Abzug der Schlusskopien bleiben weniger als drei Posen für eine Bewegungsschätzung.")
    base = animation.frames[:source_count]
    weights = np.asarray(animation.durations if animation.durations is not None else [1.]*count, dtype=float)
    source_times = np.concatenate(([0.], np.cumsum(weights[:source_count])))
    # Den verkürzten, zyklischen Bewegungsablauf auf die ursprünglichen Framezeiten abbilden.
    target_times = np.concatenate(([0.], np.cumsum(weights[:-1])))/weights.sum()*source_times[-1]
    cv = require_opencv()
    output, mapping, max_error = [], [], 0.
    # Paare werden nur für den aktuellen Übergang gehalten; große Sheets vervielfachen den Speicher nicht pro Frame.
    cached_index, pair = None, None
    try:
        for index, time in enumerate(target_times):
            start = min(source_count-1, int(np.searchsorted(source_times, time, side="right")-1))
            fraction = float((time-source_times[start])/(source_times[start+1]-source_times[start]))
            end = (start+1) % source_count
            if fraction < 1e-9 or visible_equal(base[start], base[end]):
                frame = base[start].copy()
            else:
                if cached_index != start:
                    pair = optical_flow_pair(base[start], base[end], args, cv)
                    cached_index = start
                frame = interpolate_pair(pair, fraction, args.sampling, cv)
                max_error = max(max_error, pair[-1])
                mass = float(np.asarray(frame)[..., 3].sum())
                reference_mass = min(float(np.asarray(base[i])[..., 3].sum()) for i in (start, end))
                if mass < .7*reference_mass:
                    raise CannotFix("Ein Zwischenbild verliert zu viel sichtbare Fläche.")
            output.append(frame)
            mapping.append({"frame": index+1, "from": start+1, "to": end+1, "fraction": fraction})
    except cv.error as exc:
        raise CannotFix(f"OpenCV konnte diese Bildfolge nicht interpolieren: {exc}") from exc
    if visible_equal(output[-1], output[0]):
        raise CannotFix("Nach der Interpolation wären Schluss- und Startframe weiterhin gleich.")
    def holds(frames):
        return sum(visible_equal(frame, frames[(i+1) % len(frames)]) for i, frame in enumerate(frames))
    # Die bereinigte Folge ist die Vergleichsbasis, auch bei manuell bestätigten Schlussposen.
    if holds(output) > holds(base):
        raise CannotFix("Die Interpolation würde die Doppelbilder nur an eine andere Stelle verschieben.")
    print(f"   {len(duplicates)} Schlusskopie(n) erkannt; Bewegung auf {count} Frames verteilt, maximaler Bildfehler {max_error:.3f}.")
    print("   Zwischenbilder sind geschätzt. Konturen und Details am Ergebnis visuell prüfen.")
    return FixPlan(output, animation.cols, animation.rows, animation.durations,
                   "duplicate-end-keep-count", {"closing_copies": duplicates, "end_confirmed": args.end_is_duplicate,
                   "interpolation": "bidirectional Farneback flow, premultiplied RGBA, cyclic time resampling",
                   "sampling": args.sampling, "max_warp_error": max_error, "frame_mapping": mapping})


def position_diagnostics(frames, threshold):
    boxes = []
    for frame in frames:
        ys, xs = np.where(np.asarray(frame)[..., 3] > threshold)
        if len(xs):
            boxes.append((xs.min(), ys.min(), xs.max()+1, ys.max()+1))
    if not boxes:
        raise CannotFix("Keine sichtbare Figur für eine Positionskorrektur.")
    y0, y1 = min(b[1] for b in boxes), max(b[3] for b in boxes)
    height = max(1, y1-y0)
    a, b = y0+round(height*.36), y0+round(height*.64)
    regions = {"top": (y0, a), "middle": (a, b), "bottom": (b, y1), "full": (y0, y1)}
    result = {}
    for name, (low, high) in regions.items():
        centers = []
        for frame in frames:
            ys, xs = np.where(np.asarray(frame)[..., 3] > threshold)
            selected = (ys >= low) & (ys < high)
            if not selected.any():
                break
            centers.append((float(xs[selected].mean()), float(ys[selected].mean())))
        if len(centers) != len(frames):
            continue
        centers = np.asarray(centers)
        steps = np.diff(centers, axis=0)
        error = centers[0]-(centers[-1]+np.median(steps, axis=0))
        typical = float(np.median(np.linalg.norm(steps, axis=1)))
        result[name] = {"error_x": float(error[0]), "error_y": float(error[1]),
                        "score": float(np.linalg.norm(error))/max(1., typical),
                        "bounds": [int(low), int(high)]}
    return result


def position_plan(animation, args):
    diagnostics = position_diagnostics(animation.frames, args.alpha_threshold)
    if args.region == "auto":
        choices = [name for name in ("top", "bottom", "middle") if name in diagnostics]
        if not choices:
            raise CannotFix("Keine über alle Frames messbare Zone.")
        region = max(choices, key=lambda name: diagnostics[name]["score"])
        if diagnostics[region]["score"] < args.min_suspicion:
            print("   Kein ausreichend auffälliger Positionssprung; keine Korrektur.")
            return None
    else:
        region = args.region
    if region not in diagnostics:
        raise CannotFix(f"Zone {region} ist nicht in allen Frames messbar.")
    info = diagnostics[region]
    ex, ey = info["error_x"], info["error_y"]
    if max(abs(ex), abs(ey)) > args.max_shift:
        raise CannotFix(f"Verschiebung überschreitet --max-shift: {ex:+.2f}, {ey:+.2f}px.")
    output, shifts = [], []
    for index, frame in enumerate(animation.frames):
        t = index/(len(animation.frames)-1)
        smooth = t*t*(3-2*t)
        dx, dy = round(ex*smooth*args.strength), round(ey*smooth*args.strength)
        if not dx and not dy:
            output.append(frame.copy())
        else:
            pixels = np.array(frame, copy=True)
            selected = pixels.copy() if region == "full" else np.zeros_like(pixels)
            if region == "full":
                pixels[:] = 0
            else:
                low, high = info["bounds"]
                selected[low:high] = pixels[low:high]
                pixels[low:high] = 0
            image = Image.fromarray(pixels)
            image.alpha_composite(Image.fromarray(selected), (dx, dy))
            output.append(image)
        shifts.append([dx, dy])
    print(f"   Positionsheuristik, Zone {region}: {ex:+.2f}px / {ey:+.2f}px. Keine Korrektur doppelter Posen.")
    return FixPlan(output, animation.cols, animation.rows, animation.durations,
                   "position", {"region": region, "strength": args.strength, "shifts": shifts})


def make_plan(animation, args):
    if args.fix == "position":
        return position_plan(animation, args)
    duplicates = closing_duplicates(animation.frames, args.end_is_duplicate)
    if not duplicates:
        print("   Kein pixelgleicher Schlussframe gefunden; keine Korrektur.")
        print("   Nur bei visuell bestätigter doppelter Pose: --end-is-duplicate verwenden.")
        return None
    print("   Doppelte Schlussposen: Frame "+", ".join(map(str, duplicates))+" entspricht Frame 1"+
          (" (vom Nutzer bestätigt)." if args.end_is_duplicate else " (sichtbare Pixel identisch)."))
    if args.fix == "inspect":
        print("   Gezielter Hauptfix: --fix duplicate-end. Framezahl und Raster bleiben erhalten.")
        return None
    return keep_count_plan(animation, args, duplicates)


if __name__ == "__main__":
    raise SystemExit(main())
