#!/usr/bin/env python3
"""PNG-Frames verlustfrei in beliebige Raster umordnen und gemeinsam beschneiden."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
import tempfile

import PyPipelineOutputs as outputs

Grid = tuple[int, int]
OUTPUT_PATTERN = re.compile(
    r"_(?P<solo>solo_)?(?P<columns>[1-9][0-9]*)x(?P<rows>[1-9][0-9]*)(?P<optimized>_o)?\.png$",
    re.IGNORECASE)


def validate_grid(grid: Grid, frame_count: int) -> None:
    if frame_count < 1:
        raise ValueError("Die Framezahl muss positiv sein.")
    columns, rows = grid
    if columns < 1 or rows < 1 or columns * rows != frame_count:
        raise ValueError(f"Raster {columns}x{rows} muss genau {frame_count} Zellen enthalten.")


def parse_grid(value: str) -> Grid:
    match = re.fullmatch(r"([1-9][0-9]*)[xX×]([1-9][0-9]*)", value)
    if match is None:
        raise argparse.ArgumentTypeError("Raster als SPALTENxZEILEN angeben, z.B. 1x8 oder 4x2.")
    return tuple(map(int, match.groups()))


def grid_name(grid: Grid) -> str:
    return f"{grid[0]}x{grid[1]}"


def validate_target(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Ausgabe ist ein Link oder keine reguläre Datei: {path}")


def get_common_content_box(frames):
    """Kleinster gemeinsamer Alpha-Rahmen; erhält die Position aller Animationsteile."""
    boxes = [box for frame in frames if (box := frame.getchannel("A").getbbox())]
    if not boxes:
        return None
    return (min(box[0] for box in boxes), min(box[1] for box in boxes),
            max(box[2] for box in boxes), max(box[3] for box in boxes))


def get_output_paths(png_path: Path, target_grid: Grid, solo: bool = False):
    suffix = f"{'_solo' if solo else ''}_{grid_name(target_grid)}"
    return (png_path.with_name(f"{png_path.stem}{suffix}.png"),
            png_path.with_name(f"{png_path.stem}{suffix}_o.png"))


def find_spritesheets(start_dir: Path, recursive: bool = False, *, source_grids: tuple[Grid, ...] = ()):
    """Ausgaben ausschließen; bekannte Quellstreifen dürfen einen passenden Rastersuffix tragen."""
    files = []
    for root, dirs, filenames in os.walk(start_dir, followlinks=False):
        dirs[:] = sorted(name for name in dirs if recursive and not name.startswith(".")
                         and name != "PixelEng" and not (Path(root) / name).is_symlink())
        for name in filenames:
            path = Path(root) / name
            generated = OUTPUT_PATTERN.search(name)
            if generated and (generated["solo"] or generated["optimized"]
                              or (int(generated["columns"]), int(generated["rows"])) not in source_grids):
                continue
            if (not name.startswith(".") and not path.is_symlink() and path.is_file()
                    and name.lower().endswith(".png")):
                files.append(path)
    return sorted(files)


def read_frames(png_path: Path, *, frame_count: int, source_grid: Grid | None = None,
                solo: bool = False):
    from PIL import Image

    if frame_count < 1:
        raise ValueError("Die Framezahl muss positiv sein.")
    if solo and source_grid is not None:
        raise ValueError("Einzelbild-Wiederholung (--solo) hat kein Quellraster.")
    if source_grid is not None:
        validate_grid(source_grid, frame_count)
    with Image.open(png_path) as source:
        if source.format != "PNG" or getattr(source, "n_frames", 1) != 1:
            raise ValueError(f"Nur statische PNGs sind erlaubt: {png_path}")
        image = source.convert("RGBA")
    if solo:
        return [image.copy() for _ in range(frame_count)], image.size, (1, 1)
    if source_grid is None:
        source_grid = (frame_count, 1) if image.width >= image.height else (1, frame_count)
    columns, rows = source_grid
    if image.width % columns or image.height % rows:
        raise ValueError(f"{png_path.name}: {image.width}x{image.height} passt nicht zu "
                         f"{grid_name(source_grid)}; Bildmaße müssen ohne Rest teilbar sein.")
    width, height = image.width // columns, image.height // rows
    frames = [image.crop((col * width, row * height, (col + 1) * width, (row + 1) * height))
              for row in range(rows) for col in range(columns)]
    return frames, image.size, source_grid


def reusable_output(output: Path, expected) -> bool:
    """Nur statische PNGs mit den erwarteten Maßen und exakt denselben RGBA-Pixeln behalten."""
    from PIL import Image

    try:
        with Image.open(output) as existing:
            return (existing.format == "PNG" and getattr(existing, "n_frames", 1) == 1
                    and existing.size == expected.size
                    and existing.convert("RGBA").tobytes() == expected.tobytes())
    except (OSError, ValueError, SyntaxError, EOFError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        return False


def pack_frames(frames, target_grid: Grid, *, optimize: bool = True):
    from PIL import Image

    validate_grid(target_grid, len(frames))
    if optimize:
        box = get_common_content_box(frames)
        if box is None:
            raise ValueError("Alle Frames sind transparent.")
        frames = [frame.crop(box) for frame in frames]
    width, height = frames[0].size
    columns, rows = target_grid
    atlas = Image.new("RGBA", (width * columns, height * rows))
    for index, frame in enumerate(frames):
        atlas.paste(frame, ((index % columns) * width, (index // columns) * height))
    return atlas


def convert_to_grid(png_path: Path, *, frame_count: int, target_grid: Grid,
                    source_grid: Grid | None = None, optimize: bool = True,
                    solo: bool = False, output_path: Path | None = None,
                    overwrite: bool = False) -> Path:
    from PIL import Image

    validate_grid(target_grid, frame_count)
    if source_grid is not None:
        validate_grid(source_grid, frame_count)
    output = output_path or get_output_paths(png_path, target_grid, solo)[int(optimize)]
    validate_target(output)
    if output.resolve() == png_path.resolve() or (output.exists() and output.samefile(png_path)):
        raise ValueError(f"Original darf nicht durch die Ausgabe ersetzt werden: {png_path}")
    frames, original_size, _ = read_frames(png_path, frame_count=frame_count,
                                          source_grid=source_grid, solo=solo)
    atlas = pack_frames(frames, target_grid, optimize=optimize)
    columns, rows = target_grid
    width, height = atlas.width // columns, atlas.height // rows
    if output.exists() and not overwrite:
        if reusable_output(output, atlas):
            print(f"[SKIP] {output.name}: Raster und Pixel stimmen mit der Quelle überein.", flush=True)
            return output
        raise ValueError(f"{output}: Vorhandenes PNG passt nicht zur Quelle oder zum Raster; "
                         "bleibt unverändert. Zum Neuerstellen --overwrite verwenden.")
    fd, temporary = tempfile.mkstemp(prefix=".pyimggrid-", suffix=".png", dir=output.parent)
    os.close(fd)
    try:
        atlas.save(temporary, "PNG", optimize=True, compress_level=9)
        os.replace(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(f"[OK] {png_path.name}: {original_size[0]}x{original_size[1]} → "
          f"{atlas.width}x{atlas.height}, {frame_count} Frames à {width}x{height} → {output}", flush=True)
    return output


def run(args) -> int:
    validate_grid(args.target_grid, args.frames)
    if args.source_grid is not None:
        validate_grid(args.source_grid, args.frames)
    if args.solo and args.source_grid is not None:
        raise ValueError("--solo und --source-grid können nicht gemeinsam verwendet werden.")
    source = args.source.expanduser().resolve()
    if source.is_file():
        files = [source]
    elif source.is_dir():
        files = find_spritesheets(source, args.recursive)
    else:
        raise ValueError(f"Quelle fehlt: {source}")
    if not files:
        raise ValueError(f"Keine PNG-Eingaben gefunden: {source}")
    output_dir = args.output_dir.expanduser().resolve() if args.output_dir else None
    if output_dir is not None and output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"Ausgabeordner ist kein Verzeichnis: {output_dir}")
    jobs = []
    destinations = set()
    for path in files:
        frames, _, grid = read_frames(path, frame_count=args.frames, source_grid=args.source_grid,
                                      solo=args.solo)
        if args.optimize and get_common_content_box(frames) is None:
            raise ValueError(f"Alle Frames sind transparent: {path}")
        output = get_output_paths(path, args.target_grid, args.solo)[int(args.optimize)]
        if output_dir is not None:
            output = output_dir / output.name
        validate_target(output)
        if output in destinations or output in files:
            raise ValueError(f"Mehrere Quellen oder eine Eingabe belegen das Ausgabeziel: {output}")
        destinations.add(output)
        if output.exists() and not args.overwrite:
            expected = pack_frames(frames, args.target_grid, optimize=args.optimize)
            if not reusable_output(output, expected):
                raise ValueError(f"Vorhandenes PNG passt nicht zur Quelle: {output}; bleibt unverändert. "
                                 "Zum Neuerstellen --overwrite verwenden.")
        jobs.append((path, output, grid))
        outputs.should_write(output, overwrite=args.overwrite, dry_run=True)
    if args.dry_run:
        print(f"Plan geprüft: {len(jobs)} Spritesheet(s); keine Dateien geschrieben.")
        return 0
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
    for path, output, grid in jobs:
        convert_to_grid(path, frame_count=args.frames, target_grid=args.target_grid,
                        source_grid=None if args.solo else grid, optimize=args.optimize,
                        solo=args.solo, output_path=output, overwrite=args.overwrite)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("source", nargs="?", type=Path, default=Path.cwd(),
                        help="PNG oder Ordner; Standard: aktueller Terminalordner")
    parser.add_argument("--frames", type=int, required=True, help="Anzahl der Frames")
    parser.add_argument("--source-grid", type=parse_grid,
                        help="Quellraster; sonst Streifen anhand der längeren Bildseite")
    parser.add_argument("--target-grid", type=parse_grid, required=True, help="Zielraster, z.B. 4x2")
    parser.add_argument("--output-dir", type=Path, help="Ausgabeordner; sonst neben jeder Quelle")
    parser.add_argument("--recursive", "--rc", action="store_true", help="Unterordner einbeziehen")
    parser.add_argument("--solo", action="store_true", help="Einzelbild in allen Zielzellen wiederholen")
    parser.add_argument("--optimize", action="store_true", help="Gemeinsamen transparenten Rand entfernen")
    parser.add_argument("--overwrite", action="store_true", help="Erzeugte Ausgaben ersetzen; Originale erhalten")
    parser.add_argument("--dry-run", action="store_true", help="Nur prüfen; nichts schreiben")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        return 130
    except (ImportError, OSError, ValueError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
