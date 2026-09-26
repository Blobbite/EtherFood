#!/usr/bin/env python3
"""Auflösung von HD-PNGs und Spritesheets reduzieren; GIF/HTML erstellt PyImgGif.py.

Python >= 3.10, Pillow >= 10.3. Ohne Argumente im Aktionsordner starten,
der comic_high enthält, z.B. stand/ oder run/. Erst PNGs, dann GIF/HTML.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Sequence
import warnings


VARIANTS = {
    "comic_mid": "SComicMid",
    "comic_low": "SComicLow",
    "pixel_high": "SPixelHigh",
    "pixel_low": "SPixelLow",
}
DEFAULT_GRIDS = {8: (4, 2), 10: (5, 2), 12: (4, 3), 14: (7, 2), 16: (4, 4)}
MAX_SHEET_FRAMES = 64
FOLDER_PATTERN = re.compile(r"spritesheet-fram(?:e)?([0-9]+)", re.IGNORECASE)
GRID_PATTERN = re.compile(r"(?<![0-9])([0-9]+)[xX×]([0-9]+)(?![0-9])")
MAX_PIXELS = 64_000_000
SCRIPT_DIR = Path(__file__).resolve().parent
GIF_SCRIPT = SCRIPT_DIR.parent / "PiplineToos" / "PyImgGif.py"
sys.path.insert(0, str(SCRIPT_DIR.parent / "PiplineToos"))
import PyPipelineOutputs as output_policy
import PyImgGif as gif_tools


@dataclass(frozen=True)
class Profile:
    name: str
    scale: float | None = None
    size: int | None = None
    colors: int | None = None
    reference_size: int | None = None
    palette: tuple[tuple[int, int, int], ...] | None = None


@dataclass(frozen=True)
class Sheet:
    source: Path
    folder: str
    grid: tuple[int, int]
    size: tuple[int, int]

    @property
    def single(self) -> bool:
        return self.grid == (1, 1)


def scale_value(value: str) -> float:
    try:
        number = float(value.replace(",", "."))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Skalierungsfaktor muss eine Zahl sein.") from exc
    if not math.isfinite(number) or not 0 < number <= 1:
        raise argparse.ArgumentTypeError("Skalierungsfaktor muss > 0 und <= 1 sein, z.B. 0.5.")
    return number


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Eine positive ganze Zahl angeben.") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("Eine positive ganze Zahl angeben.")
    return number


def color_count(value: str) -> int:
    number = positive_int(value)
    if not 2 <= number <= 256:
        raise argparse.ArgumentTypeError("Die Farbzahl muss zwischen 2 und 256 liegen.")
    return number


def grid_value(value: str) -> tuple[int, int]:
    match = GRID_PATTERN.fullmatch(value.strip())
    if match is None:
        raise argparse.ArgumentTypeError("Raster als SPALTENxZEILEN angeben, z.B. 4x4.")
    grid = tuple(map(int, match.groups()))
    if min(grid) < 1 or not 3 <= math.prod(grid) <= MAX_SHEET_FRAMES:
        raise argparse.ArgumentTypeError("Das Raster muss 3 bis 64 Zellen enthalten, z.B. 4x4 oder 7x7.")
    return grid


def build_parser(only: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(f"Auflösung von HD-PNGs und Spritesheets für {only} reduzieren." if only else
                     "Auflösung von HD-PNGs und Spritesheets reduzieren: comic_mid, comic_low, pixel_high und pixel_low."),
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Beispiele: PyPiplineStart-SpritesheetResolution -s | PyPiplineStart-SpritesheetResolution -s-a /pfad/posen | "
               "PyPiplineStart-SpritesheetResolution -s-a --gif-only | PyPiplineStart-SpritesheetResolution -s-a --html-only. "
               "Größen gelten pro Einzelbild bzw. Frame. Texturverarbeitung folgt später.",
    )
    parser.add_argument("source", nargs="?", type=Path, default=Path.cwd(),
                        help="Pose mit comic_high; bei -s-a: Wurzel aller Posen; Standard: aktueller Ordner")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--spritesheet", "-s", dest="mode", action="store_const", const="single",
                      help="Eine Pose verarbeiten und gif-vergleich.html sowie aufloesungsvergleich.html erstellen (Standard)")
    mode.add_argument("--spritesheet-all", "-s-a", dest="mode", action="store_const", const="all",
                      help="Alle Posen rekursiv verarbeiten; zusätzlich positionsvergleich.html für Größe und Position")
    mode.add_argument("--Textur", "--textur", "-t", dest="mode", action="store_const", const="texture",
                      help="Für spätere Texturskalierung mit T-Modulen reserviert; noch nicht implementiert")
    parser.set_defaults(mode="single")
    parser.add_argument("--output-root", type=Path,
                        help="Zielwurzel für die vier Varianten; Standard: Elternordner von comic_high")
    parser.add_argument("--frames", nargs="+", type=positive_int, metavar="ANZAHL",
                        help="Nur diese Frame-Ordner bearbeiten, z.B. --frames 8 16; Einzelbilder bleiben enthalten")
    parser.add_argument("--grid", type=grid_value, metavar="SPALTENxZEILEN",
                        help="Raster für alle gewählten Sheets; sonst Dateiname, dann Ordnerzuordnung")
    parser.add_argument("--fps", "-f", type=int, choices=(2, 4, 6, 8, 10, 12, 16, 18, 20, 22, 24), default=8,
                        help="Bildrate für PyImgGif")
    parser.add_argument("--gif-script", type=Path,
                        help="Optionaler GIF-Programmpfad; Standard: internes PiplineToos/PyImgGif.py")
    phase = parser.add_mutually_exclusive_group()
    phase.add_argument("--no-gif", action="store_true", help="Nur PNGs; keine GIFs oder HTML-Seiten")
    phase.add_argument("--gif-only", action="store_true",
                       help="GIFs und HTML aus vorhandenen Varianten-PNGs; keine PNGs skalieren oder erzeugen")
    phase.add_argument("--html-only", action="store_true",
                       help="Fehlende Vergleichsseiten erstellen; mit --overwrite erneuern; Bilder unverändert")
    phase.add_argument("--compare-only", action="store_true",
                       help="Nur Vergleichsseiten erstellen; mit --overwrite erneuern")
    parser.add_argument("--overwrite", action="store_true",
                        help="Ausgaben der gewählten Phase ersetzen (PNG/GIF/HTML); Quellen erhalten")
    parser.add_argument("--dry-run", action="store_true", help="Quellen prüfen und Ziele zeigen; nichts schreiben")
    parser.add_argument("--palette-profile", type=Path,
                        help="reference-colors.json: gemeinsame feste Pixelpalette statt eigener Palette je Sheet")
    if only:
        if only.startswith("comic_"):
            parser.add_argument("--scale", type=scale_value, default=0.5 if only == "comic_mid" else 0.25,
                                help="Faktor pro Frame; 0.5 = 50 Prozent")
        else:
            parser.add_argument("--size", type=positive_int, default=128 if only == "pixel_high" else None,
                                help="Maximale Frame-Seite; Pixel Low ohne Angabe: 90 Prozent von High")
            parser.add_argument("--colors", type=color_count, default=64,
                                help="Maximale Farbzahl für das gesamte Sheet")
            if only == "pixel_low":
                parser.add_argument("--high-size", type=positive_int, default=128,
                                    help="Pixel-High-Referenzgröße für die 90-Prozent-Verkleinerung")
    else:
        parser.add_argument("--variants", nargs="+", choices=tuple(VARIANTS), default=list(VARIANTS),
                            help="Gewünschte Zielvarianten")
        parser.add_argument("--comic-mid-scale", type=scale_value, default=0.5, help="Frame-Skalierung comic_mid")
        parser.add_argument("--comic-low-scale", type=scale_value, default=0.25, help="Frame-Skalierung comic_low")
        parser.add_argument("--pixel-high-size", type=positive_int, default=128, help="Maximale Frame-Seite pixel_high")
        parser.add_argument("--pixel-low-size", type=positive_int,
                            help="Optional feste Low-Frame-Seite; sonst 90 Prozent der tatsächlichen High-Größe")
        parser.add_argument("--pixel-high-colors", type=color_count, default=64, help="Farbzahl pixel_high")
        parser.add_argument("--pixel-low-colors", type=color_count,
                            help="Optional eigene Low-Palette; sonst identische Palette wie Pixel High")
    return parser


def profiles_from_args(args: argparse.Namespace, only: str | None) -> list[Profile]:
    palette = None
    if args.palette_profile:
        from PyImgColorMatch import load_profile
        palette = tuple(tuple(c) for c in load_profile(args.palette_profile.expanduser())["pixel_palette"])
    if only:
        if only.startswith("comic_"):
            return [Profile(only, scale=args.scale)]
        return [Profile(only, size=args.size, colors=len(palette) if palette else args.colors,
                        reference_size=args.high_size if only == "pixel_low" else None, palette=palette)]
    profiles = []
    for name in dict.fromkeys(args.variants):
        if name.startswith("comic_"):
            profiles.append(Profile(name, scale=getattr(args, f"{name}_scale")))
        elif name == "pixel_low":
            profiles.append(Profile(name, size=args.pixel_low_size,
                                    colors=len(palette) if palette else args.pixel_low_colors or args.pixel_high_colors,
                                    reference_size=args.pixel_high_size, palette=palette))
        else:
            profiles.append(Profile(name, size=args.pixel_high_size,
                                    colors=len(palette) if palette else args.pixel_high_colors, palette=palette))
    return profiles


def load_pillow() -> None:
    global Image
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow fehlt im verwendeten Python. Die Pipeline benötigt Pillow ab 10.3.") from exc


def locate_source(source: Path, frames: list[int] | None) -> tuple[Path, list[Path]]:
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"Quellordner existiert nicht: {source}")
    high = source / "comic_high"
    if not high.is_dir():
        raise ValueError(f"In {source} fehlt comic_high. PyPiplineStart-SpritesheetResolution im Aktionsordner "
                         "starten, der comic_high enthält, z.B. stand/ oder run/.")
    folders = list(high.iterdir())
    selected = []
    for folder in folders:
        match = FOLDER_PATTERN.fullmatch(folder.name)
        if match and folder.is_dir() and not folder.is_symlink():
            count = int(match[1])
            if frames is None or count in frames:
                selected.append(folder)
    if frames:
        found = {int(FOLDER_PATTERN.fullmatch(p.name)[1]) for p in selected}
        missing = sorted(set(frames) - found)
        if missing:
            raise ValueError(f"Angeforderte Frame-Ordner fehlen: {missing}")
    return high, sorted(selected, key=lambda p: (-int(FOLDER_PATTERN.fullmatch(p.name)[1]), p.name))


def grid_from_name(source: Path) -> tuple[int, int] | None:
    # Auflösungsangaben wie 256x256 sind keine Rasterhinweise.
    hints = {tuple(map(int, m.groups())) for m in GRID_PATTERN.finditer(source.stem)
             if 1 <= int(m[1]) and 1 <= int(m[2])
             and int(m[1]) * int(m[2]) <= MAX_SHEET_FRAMES}
    if len(hints) > 1:
        raise ValueError(f"Widersprüchliche Raster im Dateinamen: {source.name}")
    return next(iter(hints)) if hints else None


def choose_grid(source: Path, manual: tuple[int, int] | None) -> tuple[int, int]:
    count = int(FOLDER_PATTERN.fullmatch(source.parent.name)[1])
    if manual:
        grid = manual
    else:
        square = math.isqrt(count)
        grid = grid_from_name(source) or DEFAULT_GRIDS.get(count)
        if grid is None and square * square == count:
            grid = (square, square)
    if grid is None:
        raise ValueError(f"Kein bekanntes Raster für {source.name}; --grid SPALTENxZEILEN angeben.")
    if not 3 <= math.prod(grid) <= MAX_SHEET_FRAMES or math.prod(grid) != count:
        raise ValueError(f"Raster {grid[0]}x{grid[1]} passt nicht zu {source.parent.name}: {source.name}")
    return grid


def read_sheet(source: Path):
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(source) as opened:
            if opened.format != "PNG" or getattr(opened, "n_frames", 1) != 1:
                raise ValueError(f"Nur statische PNG-Dateien werden verarbeitet: {source}")
            if opened.width * opened.height > MAX_PIXELS:
                raise ValueError(f"PNG überschreitet {MAX_PIXELS} Pixel: {source}")
            if opened.mode in {"I", "F"} or opened.mode.startswith("I;16"):
                raise ValueError(f"16-Bit-/HDR-Eingabe wird nicht automatisch reduziert: {source}")
            image = opened.convert("RGBA")
            image.info.clear()
            return image


def inspect_sheets(folders: list[Path], manual: tuple[int, int] | None,
                   singles_folder: Path | None = None) -> list[Sheet]:
    sheets = []
    for folder in [*folders, *([singles_folder] if singles_folder is not None else [])]:
        single = folder == singles_folder
        paths = sorted((p for p in folder.iterdir() if p.suffix.lower() == ".png"
                        and not p.name.startswith(".") and not p.is_symlink() and p.is_file()),
                       key=lambda p: (p.name.casefold(), p.name))
        names = set()
        for source in paths:
            if source.name.casefold() in names:
                raise ValueError(f"Mehrdeutige PNG-Dateinamen in {folder}: {source.name}")
            names.add(source.name.casefold())
            grid = (1, 1) if single else choose_grid(source, manual)
            with read_sheet(source) as image:
                if image.width % grid[0] or image.height % grid[1]:
                    raise ValueError(f"{source}: {image.width}x{image.height} ist nicht durch "
                                     f"Raster {grid[0]}x{grid[1]} teilbar.")
                sheets.append(Sheet(source, "" if single else folder.name, grid, image.size))
    if not sheets:
        raise ValueError("Keine PNG-Einzelbilder in comic_high oder PNG-Spritesheets "
                         "in den gewählten Frame-Ordnern gefunden.")
    return sheets


def high_frame_size(sheet: Sheet, maximum: int) -> tuple[int, int]:
    width, height = (sheet.size[i] // sheet.grid[i] for i in range(2))
    factor = min(1.0, maximum / max(width, height))
    return max(1, math.floor(width * factor + 0.5)), max(1, math.floor(height * factor + 0.5))


def frame_size(sheet: Sheet, profile: Profile) -> tuple[int, int]:
    width, height = (sheet.size[i] // sheet.grid[i] for i in range(2))
    if profile.reference_size is not None:
        width, height = high_frame_size(sheet, profile.reference_size)
        factor = 0.9 if profile.size is None else min(1.0, profile.size / max(width, height))
        return max(1, math.floor(width * factor + 0.5)), max(1, math.floor(height * factor + 0.5))
    factor = profile.scale if profile.scale is not None else min(1.0, profile.size / max(width, height))
    return max(1, math.floor(width * factor + 0.5)), max(1, math.floor(height * factor + 0.5))


def validate_output(path: Path, root: Path, high: Path) -> None:
    # Bestehende Verzeichnis-/Dateilinks dürfen die Ausgabe nicht in HD umleiten.
    relative = path.relative_to(root)
    if root.exists() and not root.is_dir():
        raise ValueError(f"Zielwurzel ist kein Verzeichnis: {root}")
    current = root
    for index, part in enumerate(relative.parts):
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symbolischer Link im Ausgabeweg: {current}")
        if index < len(relative.parts) - 1 and current.exists() and not current.is_dir():
            raise ValueError(f"Ausgabeordner ist kein Verzeichnis: {current}")
    resolved = path.resolve()
    if resolved == high or resolved.is_relative_to(high):
        raise ValueError(f"Ausgabe würde in comic_high schreiben: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"Ausgabepfad ist keine reguläre Datei: {path}")


def find_gif_program(explicit: Path | None) -> Path:
    if explicit is not None:
        path = explicit.expanduser().absolute()
        if not path.is_file():
            raise ValueError(f"GIF-Programm fehlt: {path}")
        return path
    if GIF_SCRIPT.is_file():
        return GIF_SCRIPT
    for directory in (SCRIPT_DIR, SCRIPT_DIR.parent):
        for name in ("PyImgGif.py", "PyGIF.py", "pyGIF.py"):
            path = directory / name
            if path.is_file():
                return path
    for name in ("PyGIF", "pyGIF", "PyImgGif", "PyImageGif", "PyImgGif.py"):
        path = shutil.which(name)
        if path:
            return Path(path).absolute()
    raise ValueError(f"GIF-Programm fehlt: {GIF_SCRIPT}. Pipeline vollständig installieren "
                     "oder --gif-script /pfad/PyImgGif.py angeben.")


def gif_grid(sheets: list[Sheet]) -> tuple[int, int] | None:
    grids = {sheet.grid for sheet in sheets}
    if len(grids) == 1:
        return next(iter(grids))
    if all(grid_from_name(sheet.source) == sheet.grid for sheet in sheets):
        return None  # PyImgGif liest das jeweilige Raster selbst aus dem Namen.
    raise ValueError(f"Gemischte Raster in {sheets[0].folder} benötigen Rasterangaben "
                     "in allen Dateinamen, z.B. _4x4_ und _8x2_.")


def run_gif(program: Path, directory: Path, grid: tuple[int, int] | None, fps: int,
            *, overwrite: bool = False, dry_run: bool = False, files: list[Path] | None = None) -> int:
    # Internes CLI mit Ausgabemodus, externe Skripte nur auf Arbeitskopien ausführen.
    command = [sys.executable, str(program)] if program.suffix.lower() == ".py" else [str(program)]
    command += ["--fps", str(fps)]
    if grid is not None:
        command += ["--grid", f"{grid[0]}x{grid[1]}"]
    files = files if files is not None else gif_tools.discover_images(directory)
    if program.resolve() == GIF_SCRIPT.resolve():
        if overwrite:
            command += ["--overwrite"]
        if dry_run:
            command += ["--dry-run"]
        command += ["--files", *[f"./{p.name}" for p in files]]
        return subprocess.run(command, cwd=directory, check=False).returncode
    # Fremde GIF-Programme erhalten nur Arbeitskopien. Nur geplante GIFs werden übernommen.
    planned = gif_tools.plan_sheet_outputs(files, fps)
    selected = [p for p, target in planned.items() if overwrite or not target.exists()]
    errors = 0
    for path, target in planned.items():
        output_policy.should_write(target, overwrite=overwrite, dry_run=True)
        if target.exists() and not overwrite and not gif_tools.reusable_gif(
                path, target, fps, gif_tools.Grid(*grid, "Pipeline") if grid else None):
            print(f"FEHLER: Vorhandenes GIF bleibt unverändert: {target}; --overwrite verwenden.", file=sys.stderr)
            errors += 1
    if dry_run:
        output_policy.should_write(directory / "gif-vergleich.html", overwrite=overwrite, dry_run=True)
        return 1 if errors else 0
    if selected:
        with tempfile.TemporaryDirectory(prefix=".pygraphics-gif-") as temporary:
            stage = Path(temporary)
            for path in selected:
                shutil.copy2(path, stage / path.name)
            code = subprocess.run(command, cwd=stage, check=False).returncode
            if code:
                return code
            for path in selected:
                generated = stage / planned[path].name
                output_policy.validate(planned[path])
                if not generated.is_file() or generated.is_symlink():
                    raise ValueError(f"GIF-Programm hat die geplante Ausgabe nicht erstellt: {generated.name}")
                gif_tools.read_gif_for_gallery(generated)
                # Ziel und temporäre Datei liegen im selben Dateisystem; Quellen bleiben geschützt.
                fd, name = tempfile.mkstemp(prefix=".pygraphics-gif-", dir=directory)
                os.close(fd)
                try:
                    shutil.copyfile(generated, name)
                    os.replace(name, planned[path])
                finally:
                    Path(name).unlink(missing_ok=True)
    gallery = gif_tools.build_html_gallery(directory, directory / "gif-vergleich.html",
                                           gif_tools.Grid(*grid, "Pipeline") if grid else None,
                                           overwrite=overwrite, gif_paths=list(planned.values()))
    return 1 if errors or gallery.skipped else 0


def convert_sheet(image, sheet: Sheet, profile: Profile, worker):
    if profile.reference_size is not None:
        return worker.convert_sheet(image, sheet.grid,
                                    high_frame_size(sheet, profile.reference_size),
                                    frame_size(sheet, profile), profile.colors, palette=profile.palette)
    columns, rows = sheet.grid
    old_w, old_h = sheet.size[0] // columns, sheet.size[1] // rows
    width, height = frame_size(sheet, profile)
    output = Image.new("RGBA", (columns * width, rows * height))
    for row in range(rows):
        for column in range(columns):
            with image.crop((column * old_w, row * old_h,
                             (column + 1) * old_w, (row + 1) * old_h)) as frame:
                with worker.resize_frame(frame, (width, height)) as resized:
                    # Ohne Alphamaske einsetzen: eine Maske würde Alpha zweimal anwenden.
                    output.paste(resized, (column * width, row * height))
    if profile.colors is not None:
        try:
            return worker.finish_sheet(output, profile.colors, palette=profile.palette)
        finally:
            output.close()
    return output


def save_png(image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pygraphics-", suffix=".png", dir=path.parent)
    os.close(fd)
    try:
        image.save(temporary, format="PNG")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def run(args: argparse.Namespace, profiles: list[Profile], *, preflight: bool = False) -> int:
    load_pillow()
    high, folders = locate_source(args.source, args.frames)
    high = high.resolve()
    root = (args.output_root.expanduser().resolve() if args.output_root else args.source.expanduser().resolve())
    if root == high or root.is_relative_to(high):
        raise ValueError("Die Zielwurzel muss außerhalb von comic_high liegen.")
    sheets = inspect_sheets(folders, args.grid, high)
    comparison_output = root / "aufloesungsvergleich.html"
    if not args.no_gif:
        validate_output(comparison_output, root, high)
    animated = [sheet for sheet in sheets if not sheet.single]
    gif = find_gif_program(args.gif_script) if animated and not args.no_gif else None
    jobs = []
    gif_folders = {}
    # Erst alle Eingaben/Zielpfade prüfen, bevor die erste Datei geschrieben wird.
    for profile in profiles:
        for sheet in sheets:
            output = root / profile.name / sheet.folder / sheet.source.name
            gif_output = output.with_name(f"{output.stem}_{args.fps}fps.gif")
            validate_output(output, root, high)
            if gif and not sheet.single:
                validate_output(gif_output, root, high)
                validate_output(output.parent / "gif-vergleich.html", root, high)
                gif_folders.setdefault(output.parent, []).append(sheet)
            jobs.append((profile, sheet, output))
    gif_grids = {directory: gif_grid(group) for directory, group in gif_folders.items()}
    for profile, sheet, output in jobs:
        if output.exists() and not args.overwrite:
            with read_sheet(output) as existing:
                if existing.width % sheet.grid[0] or existing.height % sheet.grid[1]:
                    raise ValueError(f"Vorhandenes PNG hat ein ungültiges Raster: {output}; "
                                     "bleibt unverändert. --overwrite verwenden.")
            animation = output.with_name(f"{output.stem}_{args.fps}fps.gif")
            if gif and not sheet.single and animation.exists() and not gif_tools.reusable_gif(
                    output, animation, args.fps, gif_tools.Grid(*sheet.grid, "Pipeline")):
                raise ValueError(f"Vorhandenes GIF ist ungültig oder veraltet: {animation}; "
                                 "bleibt unverändert. --overwrite verwenden.")
    if preflight:
        return 0
    print(f"Quelle: {high}\nZielwurzel: {root}\n"
          f"{len(animated)} Spritesheet(s), {len(sheets) - len(animated)} Einzelbild(er), "
          f"{len(profiles)} Variante(n).", flush=True)
    print("Schritt 1: PNGs für alle gewählten Varianten erstellen.", flush=True)
    workers = {}
    created = skipped = errors = 0
    failed_folders = set()
    for profile, sheet, output in jobs:
        target = frame_size(sheet, profile)
        exists = output.exists()
        label = output_policy.action(output, args.overwrite)
        detail = ("Einzelbild, Ziel" if sheet.single else
                  f"Raster {sheet.grid[0]}x{sheet.grid[1]}, Ziel-Frame")
        print(f"[{profile.name}] {Path(sheet.folder) / sheet.source.name}: "
              f"{detail} {target[0]}x{target[1]} px "
              f"({label}{'; Plan' if args.dry_run else ''})", flush=True)
        if args.dry_run:
            continue
        try:
            if exists and not args.overwrite:
                skipped += 1
            else:
                if profile.name not in workers:
                    prefix = f"{__package__}." if __package__ else ""
                    workers[profile.name] = importlib.import_module(prefix + VARIANTS[profile.name])
                with read_sheet(sheet.source) as image:
                    if image.size != sheet.size:
                        raise ValueError("Quelldatei wurde während der Verarbeitung verändert.")
                    with convert_sheet(image, sheet, profile, workers[profile.name]) as converted:
                        save_png(converted, output)
                created += 1
        except (OSError, ValueError, SyntaxError, MemoryError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as exc:
            errors += 1
            failed_folders.add(output.parent)
            print(f"FEHLER [{profile.name}] {sheet.source.name}: {exc}", file=sys.stderr)
    if gif:
        print("Schritt 2: Vorhandenes GIF-Programm erzeugt GIFs und HTML-Vergleichsseiten.", flush=True)
        for directory, grid in gif_grids.items():
            if directory in failed_folders:
                print(f"GIF/HTML ausgelassen: PNG-Fehler in {directory}", file=sys.stderr)
                continue
            print(f"[GIF/HTML] {directory.relative_to(root)}{' (Plan)' if args.dry_run else ''}", flush=True)
            files = [directory / sheet.source.name for sheet in gif_folders[directory]]
            if args.dry_run:
                for path in gif_tools.plan_sheet_outputs(files, args.fps).values():
                    output_policy.should_write(path, overwrite=args.overwrite, dry_run=True)
                output_policy.should_write(directory / "gif-vergleich.html", overwrite=args.overwrite, dry_run=True)
                continue
            try:
                code = run_gif(gif, directory, grid, args.fps, overwrite=args.overwrite, files=files)
                if code != 0:
                    raise ValueError(f"GIF-Programm mit Exit-Code {code} beendet")
            except (OSError, ValueError) as exc:
                errors += 1
                print(f"FEHLER GIF/HTML {directory}: {exc}", file=sys.stderr)
    if args.dry_run:
        if not args.no_gif:
            output_policy.should_write(comparison_output, overwrite=args.overwrite, dry_run=True)
        print(f"Plan geprüft: {len(jobs)} PNG-Ausgaben; keine Dateien geschrieben.")
    else:
        if not args.no_gif:
            print("Gemeinsamen Auflösungsvergleich erstellen.", flush=True)
            prefix = f"{__package__}." if __package__ else ""
            compare = importlib.import_module(prefix + "PyGraphicsCompare")
            errors += compare.build_comparison(root, high, sheets, args.fps, overwrite=args.overwrite)
        print(f"Fertig: {created} PNG(s) erzeugt, {skipped} behalten, {errors} Fehler.")
    return 1 if errors else 0


def discover_poses(source: Path, *, existing: bool = False, exclude: Path | None = None) -> list[Path]:
    """Find pose roots deterministically without following links or outputs."""
    if not source.is_dir():
        raise ValueError(f"Quellordner existiert nicht: {source}")
    poses = []
    variant_names = {"comic_high", *VARIANTS}
    for directory, children, _ in os.walk(source, followlinks=False):
        current = Path(directory)
        candidates = variant_names if existing else {"comic_high"}
        if any((current / name).is_dir() and not (current / name).is_symlink() for name in candidates):
            poses.append(current)
            children[:] = []
        else:
            children[:] = sorted(name for name in children
                                 if not name.startswith(".") and name not in variant_names
                                 and not (current / name).is_symlink()
                                 and (exclude is None or current / name != exclude))
    if not poses:
        raise ValueError(f"Keine Posen mit {'Variantenordnern' if existing else 'comic_high'} in {source} gefunden.")
    return poses


def run_existing(args: argparse.Namespace, profiles: list[Profile], *, preflight: bool = False) -> int:
    """Rebuild downstream artifacts from actual outputs, without converting PNGs."""
    load_pillow()
    prefix = f"{__package__}." if __package__ else ""
    pose_compare = importlib.import_module(prefix + "PyGraphicsPoseCompare")
    compare = importlib.import_module(prefix + "PyGraphicsCompare")
    high = args.source.expanduser().resolve() / "comic_high"
    root = (args.output_root or args.source).expanduser().resolve()
    if root == high or root.is_relative_to(high):
        raise ValueError("Die Zielwurzel muss außerhalb von comic_high liegen.")
    groups, errors = pose_compare.collect_pose(root, high, root / "aufloesungsvergleich.html",
                                               args.fps, args.frames, args.grid)
    if not groups:
        raise ValueError(f"Keine vorhandenen PNGs oder GIFs in {root} gefunden.")
    validate_output(root / "aufloesungsvergleich.html", root, high)
    directories = []
    gif = None
    if args.gif_only:
        for profile in profiles:
            variant = root / profile.name
            if not variant.is_dir():
                continue
            folders = pose_compare.frame_folders(variant, args.frames)
            for folder in folders:
                if not pose_compare.png_files(folder):
                    continue
                sheets = inspect_sheets([folder], args.grid)
                grid = gif_grid(sheets)
                validate_output(folder / "gif-vergleich.html", root, high)
                for sheet in sheets:
                    validate_output(sheet.source.with_name(f"{sheet.source.stem}_{args.fps}fps.gif"), root, high)
                directories.append((folder, grid))
        if not directories:
            raise ValueError("Keine vorhandenen Spritesheet-PNGs in den gewählten Zielvarianten; "
                             "zuerst -s ausführen oder bei fertigen GIFs --html-only verwenden.")
        gif = find_gif_program(args.gif_script)
    elif args.html_only:
        for name in VARIANTS:
            variant = root / name
            if variant.is_dir():
                for folder in pose_compare.frame_folders(variant, args.frames):
                    if pose_compare.gif_tools.discover_gifs(folder):
                        validate_output(folder / "gif-vergleich.html", root, high)
                        directories.append((folder, None))
    if preflight:
        if errors:
            raise ValueError(f"{errors} unlesbare Vergleichsdatei(en) in {root}.")
        return 0
    if args.dry_run:
        print(f"Plan: {root}: {len(directories)} GIF-/HTML-Ordner, Auflösungsvergleich; keine PNG-Erzeugung.")
        for directory, grid in directories:
            if args.gif_only:
                errors += bool(run_gif(gif, directory, grid, args.fps, overwrite=args.overwrite, dry_run=True))
            else:
                output_policy.should_write(directory / "gif-vergleich.html", overwrite=args.overwrite, dry_run=True)
        output_policy.should_write(root / "aufloesungsvergleich.html", overwrite=args.overwrite, dry_run=True)
        return 1 if errors else 0
    for directory, grid in directories:
        if args.gif_only:
            errors += bool(run_gif(gif, directory, grid, args.fps, overwrite=args.overwrite))
        else:
            result = pose_compare.gif_tools.build_html_gallery(directory, directory / "gif-vergleich.html",
                                                              overwrite=args.overwrite)
            errors += bool(result.skipped)
    # GIF links may have been added during the preceding phase.
    groups, read_errors = pose_compare.collect_pose(root, high, root / "aufloesungsvergleich.html",
                                                    args.fps, args.frames, args.grid)
    return compare.write_comparison(root, groups, args.fps, errors + read_errors, overwrite=args.overwrite)


def dispatch(args: argparse.Namespace, profiles: list[Profile]) -> int:
    existing = args.gif_only or args.html_only or args.compare_only
    runner = run_existing if existing else run
    if args.mode != "all":
        return runner(args, profiles)
    source = args.source.expanduser().resolve()
    root = (args.output_root or source).expanduser().resolve()
    poses = discover_poses(source, existing=existing, exclude=root if root != source else None)
    jobs = []
    for pose in poses:
        options = argparse.Namespace(**vars(args))
        options.source = pose
        options.output_root = root / pose.relative_to(source)
        jobs.append(options)
    output = root / "positionsvergleich.html"
    for job in jobs:
        validate_output(output, root, (job.source / "comic_high").resolve())
        # All poses must pass validation before the first output is written.
        runner(job, profiles, preflight=True)
    errors = 0
    for index, job in enumerate(jobs, 1):
        name = job.source.relative_to(source).as_posix() if job.source != source else source.name
        print(f"\nPose {index}/{len(jobs)}: {name}", flush=True)
        errors += bool(runner(job, profiles))
    if not args.no_gif:
        if args.dry_run:
            output_policy.should_write(output, overwrite=args.overwrite, dry_run=True)
        else:
            prefix = f"{__package__}." if __package__ else ""
            compare = importlib.import_module(prefix + "PyGraphicsPoseCompare")
            entries = [(job.source.relative_to(source).as_posix() if job.source != source else source.name,
                        job.output_root, job.source / "comic_high") for job in jobs]
            errors += compare.build_position_comparison(root, entries, args.fps, args.frames, args.grid,
                                                        overwrite=args.overwrite)
    return 1 if errors else 0


def main(argv: Sequence[str] | None = None, *, only: str | None = None) -> int:
    parser = build_parser(only)
    args = parser.parse_args(argv)
    if args.mode == "texture":
        parser.error("--Textur / -t ist für die spätere Texturskalierung mit TComicLow, "
                     "TComicMid, TPixelHigh und TPixelLow reserviert; noch nicht implementiert.")
    try:
        return dispatch(args, profiles_from_args(args, only))
    except KeyboardInterrupt:
        print("\nAbgebrochen. Bereits erzeugte Ausgaben bleiben erhalten.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
