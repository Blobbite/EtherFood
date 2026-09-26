#!/usr/bin/env python3
"""Gemeinsamer Ablauf für Streifen-Pipelines: Originale, Grid-Optimierung und Vorschauen."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import PyImgGif as gif
import PyImgGrid as raster
import PyPipelineOutputs as output_policy


def build_parser(frame_count: int, target_grid: raster.Grid,
                 source_grid: raster.Grid | None = None):
    target_name = raster.grid_name(target_grid)
    parser = argparse.ArgumentParser(
        description=f"{frame_count}er-Streifen: Original-GIF/HTML → optimiertes {target_name}-PNG → GIF/HTML.",
        allow_abbrev=False)
    parser.add_argument("source", nargs="?", type=Path, default=Path.cwd(),
                        help=f"Ordner mit {frame_count}er-PNG-Streifen; Standard: aktueller Terminalordner")
    parser.add_argument("--fps", "-f", type=int, choices=gif.FPS_CHOICES, default=8)
    choices = ((raster.grid_name(source_grid),) if source_grid is not None
               else (f"{frame_count}x1", f"1x{frame_count}"))
    parser.add_argument("--grid", choices=choices,
                        default=raster.grid_name(source_grid) if source_grid is not None else None,
                        help=("Quellraster Spalten x Zeilen; "
                              + (f"fest {raster.grid_name(source_grid)}" if source_grid is not None
                                 else "sonst anhand der längeren Bildseite")))
    parser.add_argument("--overwrite", action="store_true", help="Erzeugte PNGs, GIFs und HTML ersetzen; Originale erhalten")
    parser.add_argument("--dry-run", action="store_true", help="Eingaben und Ziele prüfen; nichts schreiben")
    return parser


def run(args, *, frame_count: int, target_grid: raster.Grid):
    raster.validate_grid(target_grid, frame_count)
    root = args.source.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Quellordner fehlt: {root}")
    archive = root / "PixelEng"
    if archive.is_symlink() or (archive.exists() and not archive.is_dir()):
        raise ValueError(f"PixelEng ist ein Link oder kein Ordner: {archive}")
    manual_grid = raster.parse_grid(args.grid) if args.grid else None
    source_grids = (manual_grid,) if manual_grid else ((frame_count, 1), (1, frame_count))
    pending = raster.find_spritesheets(root, source_grids=source_grids)
    archived = raster.find_spritesheets(archive, source_grids=source_grids) if archive.exists() else []
    if not pending and not archived:
        raise ValueError(f"Keine {frame_count}er-PNG-Streifen in {root} oder PixelEng gefunden.")
    jobs = []
    moves = []
    destinations = set()
    # Vor dem Verschieben alle Quellen, Namenskonflikte und Ausgaben prüfen.
    for source in sorted([*pending, *archived]):
        original = archive / source.name
        if source.parent == root:
            if original.exists() or original.is_symlink():
                raise ValueError(f"Original existiert bereits in PixelEng: {source.name}. "
                                 "Namenskonflikt zuerst auflösen; Originale werden nicht überschrieben.")
            moves.append((source, original))
        frames, original_size, grid = raster.read_frames(source, frame_count=frame_count, source_grid=manual_grid)
        if raster.get_common_content_box(frames) is None:
            raise ValueError(f"Alle Frames sind transparent: {source}")
        output = root / raster.get_output_paths(source, target_grid)[1].name
        if output in destinations:
            raise ValueError(f"Mehrere Quellen würden dieselbe Ausgabe erzeugen: {output.name}")
        destinations.add(output)
        for target in (output, output.with_name(f"{output.stem}_{args.fps}fps.gif"),
                       original.with_name(f"{original.stem}_{args.fps}fps.gif")):
            output_policy.should_write(target, overwrite=args.overwrite, dry_run=True)
        if output.exists() and not args.overwrite:
            expected = raster.pack_frames(frames, target_grid)
            if not raster.reusable_output(output, expected):
                raise ValueError(f"Vorhandenes PNG passt nicht zur Quelle: {output}; bleibt unverändert. "
                                 "Zum Neuerstellen --overwrite verwenden.")
        if not args.overwrite:
            for png, animation, layout in (
                    (source, original.with_name(f"{original.stem}_{args.fps}fps.gif"), grid),
                    (output, output.with_name(f"{output.stem}_{args.fps}fps.gif"), target_grid)):
                if animation.exists() and png.exists() and not gif.reusable_gif(
                        png, animation, args.fps, gif.Grid(*layout, "Pipeline"), keep_empty=True):
                    raise ValueError(f"Vorhandenes GIF ist ungültig oder veraltet: {animation}; "
                                     "bleibt unverändert. Zum Neuerstellen --overwrite verwenden.")
        jobs.append((original, output, grid))
        frame_width, frame_height = frames[0].size
        print(f"{source.name}: {raster.grid_name(grid)} "
              f"({original_size[0]}x{original_size[1]} px; "
              f"{frame_count} Frames à {frame_width}x{frame_height} px)"
              f" → PixelEng/{source.name} + {output.name}", flush=True)
    for folder in (root, archive):
        output_policy.should_write(folder / "gif-vergleich.html", overwrite=args.overwrite, dry_run=True)
    for source, target in moves:
        print(f"[ARCHIV; Plan] {source} → {target}", flush=True)
    if args.dry_run:
        print(f"Plan geprüft: {len(jobs)} Spritesheet(s); keine Dateien geschrieben.")
        return 0
    archive.mkdir(exist_ok=True)
    for source, target in moves:
        source.rename(target)

    print("Schritt 1/3: Original-GIFs und HTML in PixelEng erstellen.", flush=True)
    errors = 0
    for original, _, grid in jobs:
        errors += gif.run_sheets([original], args.fps, gif.Grid(*grid, f"Fram{frame_count}-Quelle"),
                                 overwrite=args.overwrite, keep_empty=True)
    gallery = gif.build_html_gallery(archive, archive / "gif-vergleich.html", overwrite=args.overwrite,
                                    gif_paths=[p.with_name(f"{p.stem}_{args.fps}fps.gif") for p, _, _ in jobs])
    if errors or gallery.skipped:
        return 1

    target_name = raster.grid_name(target_grid)
    print(f"Schritt 2/3: Gemeinsamen transparenten Rand entfernen und {target_name}-PNGs erstellen.", flush=True)
    outputs = [raster.convert_to_grid(original, frame_count=frame_count, target_grid=target_grid,
                                      source_grid=grid, output_path=output, overwrite=args.overwrite)
               for original, output, grid in jobs]

    print(f"Schritt 3/3: GIFs und HTML der optimierten {target_name}-Sheets erstellen.", flush=True)
    errors = gif.run_sheets(outputs, args.fps, gif.Grid(*target_grid, f"Fram{frame_count}-Ausgabe"),
                            overwrite=args.overwrite, keep_empty=True)
    # Das HTML leitet jedes Raster aus Sheet- und GIF-Framegröße ab, auch bei älteren Ausgaben.
    gallery = gif.build_html_gallery(root, root / "gif-vergleich.html", overwrite=args.overwrite,
                                    gif_paths=[p.with_name(f"{p.stem}_{args.fps}fps.gif") for p in outputs])
    if errors or gallery.skipped:
        return 1
    print(f"Fertig: {len(outputs)} optimierte Spritesheet(s); Originale in {archive}.")
    return 0


def main(argv=None, *, frame_count: int, target_grid: raster.Grid,
         source_grid: raster.Grid | None = None):
    args = build_parser(frame_count, target_grid, source_grid).parse_args(argv)
    try:
        return run(args, frame_count=frame_count, target_grid=target_grid)
    except KeyboardInterrupt:
        print("\nAbgebrochen. Originale bleiben im Quellordner bzw. in PixelEng erhalten.", file=sys.stderr)
        return 130
    except ImportError as exc:
        print(f"FEHLER: Pipeline unvollständig oder Pillow fehlt: {exc}. "
              "PyGameTools.py --install ausführen.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1
