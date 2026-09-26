#!/usr/bin/env python3
"""Separater Notfall-Fix: doppelte Schlussposen entfernen und die Framezahl reduzieren.

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
    parser = argparse.ArgumentParser(description="Notfall-Fix: doppelte Schlussposen entfernen. 16→15, 12→11, 10→9, 8→7. Übrige Bildpixel bleiben erhalten.")
    add_common_arguments(parser)
    parser.set_defaults(suffix="_dropend_loopfix")
    parser.add_argument("--output-grid", default="auto", help="Neues Raster: auto, horizontal, vertical oder SpaltenxZeilen mit genau einem Platz je verbleibendem Frame")
    parser.add_argument("--keep-duration", action="store_true", help="Bekannte Gesamtspielzeit durch Skalierung der verbleibenden Framezeiten erhalten; erfordert FPS/Framezeiten")
    return parser.parse_args(argv)


def validate_specific_args(args):
    if args.output_grid not in {"auto", "horizontal", "vertical"}:
        parse_grid(args.output_grid)


def fallback_hint(args):
    pass


def reduced_layout(animation, count, mode):
    if mode == "horizontal":
        return count, 1
    if mode == "vertical":
        return 1, count
    if mode != "auto":
        cols, rows = parse_grid(mode)
        if cols*rows != count:
            raise ValueError("--output-grid muss genau einen Platz je verbleibendem Frame enthalten.")
        return cols, rows
    ratio = animation.cols/animation.rows
    candidates = [(abs(math.log((cols/(count//cols))/ratio)), abs(cols-count//cols), -cols, cols, count//cols)
                  for cols in range(1, count+1) if count % cols == 0]
    return min(candidates)[-2:]


def make_plan(animation, args):
    duplicates = closing_duplicates(animation.frames, args.end_is_duplicate)
    if not duplicates:
        print("   Kein pixelgleicher Schlussframe gefunden; keine Korrektur.")
        print("   Nur bei visuell bestätigter doppelter Pose: --end-is-duplicate verwenden.")
        return None
    count = len(animation.frames)-len(duplicates)
    if count < MIN_FRAMES:
        raise CannotFix("Es würden weniger als drei Frames übrig bleiben.")
    durations = animation.durations[:count] if animation.durations is not None else None
    if args.keep_duration:
        if durations is None:
            raise ValueError("--keep-duration erfordert bekannte Zeiten über --fps, --durations oder .anim.json.")
        scale = sum(animation.durations)/sum(durations)
        durations = [v*scale for v in durations]
    cols, rows = reduced_layout(animation, count, args.output_grid)
    print("   Notfallvariante: Schlussframe(s) "+", ".join(map(str, duplicates))+" entfernen.")
    print(f"   Der Player muss anschließend {count} Frames und das Raster {cols}x{rows} verwenden.")
    return FixPlan(animation.frames[:count], cols, rows, durations, "drop-duplicate-end",
                   {"removed_frames": duplicates, "end_confirmed": args.end_is_duplicate,
                    "keep_duration": args.keep_duration, "retained_pixels_unchanged": True})


if __name__ == "__main__":
    raise SystemExit(main())
