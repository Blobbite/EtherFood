#!/usr/bin/env python3
"""16-Frame-Originale → 8/10/12/14 Frames; belegte Varianten nur mit --overwrite ersetzen."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PiplineToos"))
import PyImgFrameSelect as select
import PyImgGif as gif
import PyImgGrid as raster
import PyPipelineOutputs as output_policy

SOURCE_COUNT = 16
FPS = 8
TARGET_GRIDS = {8: (4, 2), 10: (5, 2), 12: (4, 3), 14: (7, 2)}


@dataclass(frozen=True)
class SourceSheet:
    path: Path
    sha256: str
    grid: raster.Grid
    size: tuple[int, int]
    frame_size: tuple[int, int]


@dataclass(frozen=True)
class Variant:
    count: int
    root: Path

    @property
    def archive(self) -> Path:
        return self.root / "PixelEng"

    @property
    def grid(self) -> raster.Grid:
        return TARGET_GRIDS[self.count]

    def reduced(self, source: SourceSheet) -> Path:
        return self.archive / source.path.name

    def optimized(self, source: SourceSheet) -> Path:
        return self.root / raster.get_output_paths(source.path, self.grid)[1].name


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def occupied(path: Path) -> bool:
    """Nur fehlende Ordner oder vollständig leere Verzeichnisbäume verwenden."""
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        return True

    def fail(exc):
        raise exc

    if path.exists():
        for directory, dirs, files in os.walk(path, followlinks=False, onerror=fail):
            if files or any((Path(directory) / name).is_symlink() for name in dirs):
                return True
    return False


def require_new(paths):
    for path in paths:
        if path.exists() or path.is_symlink():
            raise ValueError(f"Vorhandene Datei wird nicht überschrieben: {path}")


def read_sources(root: Path, variants: list[Variant], manual_grid) -> list[SourceSheet]:
    directory = root / "spritesheet-fram16" / "PixelEng"
    if not directory.is_dir():
        raise ValueError(f"Quellordner fehlt: {directory}")
    paths = raster.find_spritesheets(directory, source_grids=((16, 1), (1, 16)))
    if not paths:
        raise ValueError(f"Keine 16-Frame-Original-PNGs in {directory}")
    sources, stems = [], set()
    for path in paths:
        if path.stem.casefold() in stems:
            raise ValueError(f"Mehrdeutige Ausgabenamen für {path.name}; Dateistämme müssen eindeutig sein.")
        stems.add(path.stem.casefold())
        digest = sha256(path)
        frames, size, grid = raster.read_frames(path, frame_count=SOURCE_COUNT, source_grid=manual_grid)
        width, height = frames[0].size
        if size[0] * size[1] > gif.MAX_SEQUENCE_PIXELS or max(width, height) > 65535:
            raise ValueError(f"Quelle überschreitet die GIF-/Vorschau-Größenlimits: {path.name}")
        for variant in variants:
            selected = [frames[i] for i in select.uniform_indices(SOURCE_COUNT, variant.count)]
            if raster.get_common_content_box(selected) is None:
                raise ValueError(f"{path.name}: Auswahl für Fram{variant.count} ist vollständig transparent.")
        sources.append(SourceSheet(path, digest, grid, size, (width, height)))
        print(f"Quelle: {path.name} | {raster.grid_name(grid)} | 16 Frames à {width}x{height} px", flush=True)
    return sources


def record(calls: list, phase: int, tool: str, **arguments):
    calls.append({"phase": phase, "tool": tool, "arguments": arguments})


def copy_original(source: SourceSheet, destination: Path, *, overwrite: bool = False):
    output_policy.validate(destination)
    if overwrite:
        fd, temporary = tempfile.mkstemp(prefix=".framreduce-copy-", dir=destination.parent)
        try:
            with source.path.open("rb") as src, os.fdopen(fd, "wb") as dst:
                shutil.copyfileobj(src, dst)
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return
    # Exklusiv anlegen: auch zwischen Vorprüfung und Kopie nichts überschreiben.
    with source.path.open("rb") as src, destination.open("xb") as dst:
        shutil.copyfileobj(src, dst)


def make_previews(paths: list[Path], grid: raster.Grid, directory: Path, calls: list, phase: int, *,
                   overwrite: bool = False):
    layout = gif.Grid(*grid, "FramReduce")
    html = directory / "gif-vergleich.html"
    planned_gifs = list(gif.plan_sheet_outputs(paths, FPS).values())
    if not overwrite:
        require_new([*planned_gifs, html])
    if gif.run_sheets(paths, FPS, layout, keep_empty=True, overwrite=overwrite):
        raise ValueError(f"GIF-Erstellung fehlgeschlagen: {directory}")
    record(calls, phase, "PyImgGif.run_sheets", files=list(map(str, paths)), fps=FPS,
           manual_grid=list(grid), keep_empty=True, overwrite=overwrite)
    result = gif.build_html_gallery(directory, html, layout, overwrite=overwrite, gif_paths=planned_gifs)
    if result.skipped or result.included != len(paths):
        raise ValueError(f"HTML-Galerie unvollständig: {html}")
    record(calls, phase, "PyImgGif.build_html_gallery", directory=str(directory),
           output=str(html), grid=list(grid), overwrite=overwrite, gif_paths=list(map(str, planned_gifs)))


def verify_gif(path: Path, frames) -> dict:
    """Tatsächlich gespeicherte Bilder und Zeitachse einschließlich zusammengefasster Frames prüfen."""
    from PIL import Image

    metadata = gif.read_gif_for_gallery(path)
    count = len(frames)
    duration = sum(gif.frame_durations(count, FPS))
    if (metadata["logicalFrames"] != count or metadata["exportFps"] != FPS
            or metadata["durationMs"] != duration
            or (metadata["width"], metadata["height"]) != frames[0].size):
        raise ValueError(f"GIF-Framezahl, Größe oder Laufzeit falsch: {path}")
    palette, _ = gif.shared_palette(frames)
    with Image.open(path) as animation:
        if animation.info.get("loop") != 0:
            raise ValueError(f"GIF hat keine Endlosschleife: {path}")
        for index, frame in enumerate(frames):
            animation.seek(metadata["frameMap"][index])
            actual = animation.convert("RGBA")
            alpha = frame.getchannel("A").point([0] * gif.ALPHA_THRESHOLD
                                                + [255] * (256 - gif.ALPHA_THRESHOLD))
            if actual.getchannel("A").tobytes() != alpha.tobytes():
                raise ValueError(f"GIF-Transparenz falsch, Frame {index}: {path}")
            # Gegen dieselbe Palette prüfen, nicht gegen die verlustfreien PNG-Farben.
            expected = frame.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE).convert("RGB")
            black = Image.new("RGB", frame.size)
            expected = Image.composite(expected, black, alpha)
            actual_rgb = Image.composite(actual.convert("RGB"), black, alpha)
            if actual_rgb.tobytes() != expected.tobytes():
                raise ValueError(f"GIF-Inhalt oder Reihenfolge falsch, Frame {index}: {path}")
    return {"logical_frames": count, "stored_frames": metadata["storedFrames"],
            "fps": FPS, "duration_ms": duration, "loop": 0,
            "frame_order_and_pixels": True, "transparency_threshold": gif.ALPHA_THRESHOLD}


def verify_html(directory: Path, paths: list[Path], grid: raster.Grid):
    html = directory / "gif-vergleich.html"
    match = re.search(r'<script id="gif-data" type="application/json">(.*?)</script>',
                      html.read_text(encoding="utf-8"), re.S)
    if match is None:
        raise ValueError(f"HTML-Vorschaudaten fehlen: {html}")
    data = json.loads(match[1])
    items = {item["gifName"]: item for item in data["items"]}
    outputs = gif.plan_sheet_outputs(paths, FPS)
    if (data["skipped"] or len(data["items"]) != len(paths)
            or set(items) != {output.name for output in outputs.values()}):
        raise ValueError(f"HTML unvollständig: {html}")
    for path, output in outputs.items():
        item = items[output.name]
        if (item.get("sheet") != gif.relative_url(path, html)
                or item.get("gif") != gif.relative_url(output, html)
                or (item.get("columns"), item.get("rows")) != grid
                or item["logicalFrames"] != grid[0] * grid[1]
                or item["exportFps"] != FPS
                or item["durationMs"] != grid[0] * grid[1] * 1000 // FPS):
            raise ValueError(f"HTML-Raster oder Animation falsch: {path.name}")


def verify_variant(variant: Variant, sources: list[SourceSheet]) -> list[dict]:
    indices = select.uniform_indices(SOURCE_COUNT, variant.count)
    results = []
    for source in sources:
        if sha256(source.path) != source.sha256:
            raise ValueError(f"16-Frame-Quelle hat sich geändert: {source.path}")
        original, _, _ = raster.read_frames(source.path, frame_count=SOURCE_COUNT, source_grid=source.grid)
        selected = [original[i] for i in indices]
        box = raster.get_common_content_box(selected)
        cropped = [frame.crop(box) for frame in selected]
        reduced, optimized = variant.reduced(source), variant.optimized(source)
        animations = []
        for path, grid, expected in ((reduced, (variant.count, 1), selected),
                                      (optimized, variant.grid, cropped)):
            actual, _, _ = raster.read_frames(path, frame_count=variant.count, source_grid=grid)
            if any(a.size != b.size or a.tobytes() != b.tobytes() for a, b in zip(actual, expected)):
                raise ValueError(f"PNG-Pixel, Reihenfolge oder Zuschnitt falsch: {path}")
            animation = path.with_name(f"{path.stem}_{FPS}fps.gif")
            animations.append({"png": str(path.relative_to(variant.root)),
                               "gif": str(animation.relative_to(variant.root)),
                               "grid": list(grid), "frame_size": list(expected[0].size),
                               "png_pixels_exact": True, "gif_check": verify_gif(animation, expected)})
        results.append({"source": str(source.path), "source_sha256": source.sha256,
                        "copy_sha256": source.sha256, "copy_verified_before_reduction": True,
                        "source_unchanged": True, "source_grid": list(source.grid),
                        "source_size": list(source.size), "frame_size": list(source.frame_size),
                        "source_frame_indices": indices, "crop_box": list(box), "outputs": animations})
    verify_html(variant.archive, [variant.reduced(s) for s in sources], (variant.count, 1))
    verify_html(variant.root, [variant.optimized(s) for s in sources], variant.grid)
    return results


def document(variant: Variant, results: list[dict], calls: list, skipped: list[int], *, overwrite: bool = False):
    indices = select.uniform_indices(SOURCE_COUNT, variant.count)
    layout = raster.grid_name(variant.grid)
    info = {"schema": 1, "pipeline": "SpritesheetFramReduce", "created": datetime.now(timezone.utc).isoformat(),
            "source_frame_count": SOURCE_COUNT, "frame_count": variant.count, "fps": FPS,
            "duration_ms": variant.count * 1000 // FPS, "source_frame_indices": indices,
            "selection": "floor(k * 16 / N), k=0..N-1", "reduced_grid": [variant.count, 1],
            "optimized_grid": list(variant.grid), "skipped_variants": skipped, "files": results,
            "tool_calls": calls}
    checks = {"schema": 1, "passed": True, "files_checked": len(results),
              "copies_complete_before_reduction": True, "source_originals_unchanged": True,
              "png_pixels_and_order": True, "gif_pixels_order_transparency_timing": True,
              "html_galleries": True, "visual_loop_review": "Nicht automatisch bewertet; HTML ansehen.",
              "files": results}
    readme = (f"# Spritesheet mit {variant.count} Frames\n\n"
              f"Direkt aus `spritesheet-fram16/PixelEng/` erstellt; Originale unverändert.\n\n"
              f"Quellindizes (ab 0): `{', '.join(map(str, indices))}`.\n"
              f"PixelEng: `{variant.count}x1`; optimiert: `{layout}`.\n"
              f"8 FPS, Endlosschleife, Zyklusdauer {variant.count / FPS:g} s.\n\n"
              "Alle Originalkopien wurden vor der Reduktion geprüft. Ein gemeinsamer transparenter "
              "Rand wurde pro Sheet entfernt; Frames wurden nicht einzeln verschoben.\n\n"
              "`build-info.json` enthält Quellen, Prüfsummen, Indizes, Raster, Zuschnitt und die "
              "tatsächlich ausgeführten Python-Toolaufrufe. `pruefung.json` enthält die technischen Prüfungen.\n\n"
              "Beide `gif-vergleich.html` öffnen und die Bewegungsqualität visuell beurteilen. "
              "PNG ist verlustfrei; GIF verwendet eine Farbpalette und binäre Transparenz.\n\n"
              "Normal überspringt Reduce diesen Ordner. Mit `--overwrite` werden die zugehörigen "
              "Ausgaben erneut aus Fram16 erzeugt; Originalquellen und fremde Dateien bleiben erhalten.\n")
    for name, content in (("build-info.json", json.dumps(info, ensure_ascii=False, indent=2) + "\n"),
                           ("pruefung.json", json.dumps(checks, ensure_ascii=False, indent=2) + "\n"),
                           ("README.md", readme)):
        output_policy.write_text(variant.root / name, content, overwrite=overwrite)


def phase(number: int, title: str):
    print(f"Schritt {number}/7: {title}", flush=True)


def run(args) -> int:
    root = args.source.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Projektordner fehlt: {root}")
    variants, skipped = [], []
    for count in sorted(set(args.frames)):
        variant = Variant(count, root / f"spritesheet-fram{count}")
        if occupied(variant.root) and not args.overwrite:
            print(f"[SKIP] {variant.root.name}: bereits belegt; bleibt vollständig unverändert.", flush=True)
            skipped.append(count)
        else:
            variants.append(variant)
    if not variants:
        print("Fertig: Alle angeforderten Varianten vorhanden; nichts geändert.")
        return 0
    if gif.Image is None:
        raise ImportError("Pillow fehlt; PyGameTools.py --install ausführen.")
    manual_grid = raster.parse_grid(args.grid) if args.grid else None
    sources = read_sources(root, variants, manual_grid)
    for variant in variants:
        print(f"[PLAN] {variant.root.name}: 16 → {variant.count}x1 → {raster.grid_name(variant.grid)}; "
              f"Indizes {select.uniform_indices(SOURCE_COUNT, variant.count)}", flush=True)
        planned = [variant.root / name for name in ("gif-vergleich.html", "README.md", "build-info.json", "pruefung.json")]
        planned.append(variant.archive / "gif-vergleich.html")
        for source in sources:
            for png in (variant.reduced(source), variant.optimized(source)):
                planned.extend((png, png.with_name(f"{png.stem}_{FPS}fps.gif")))
        for path in planned:
            output_policy.should_write(path, overwrite=args.overwrite, dry_run=True)
    if args.dry_run:
        print(f"Plan geprüft: {len(variants)} Variante(n) erstellen, {len(skipped)} übersprungen; nichts geschrieben.")
        return 0
    # Eine zwischenzeitlich belegte Variante ebenfalls in Ruhe lassen.
    for variant in variants[:]:
        if occupied(variant.root) and not args.overwrite:
            print(f"[SKIP] {variant.root.name}: inzwischen belegt.", flush=True)
            skipped.append(variant.count)
            variants.remove(variant)
    if not variants:
        print("Fertig: Alle Ziele inzwischen belegt; nichts geändert.")
        return 0
    calls = {variant.count: [] for variant in variants}

    phase(1, "Alle Zielordner und PixelEng anlegen oder weiterverwenden.")
    for variant in variants:
        variant.archive.mkdir(parents=True, exist_ok=True)

    phase(2, "Alle 16-Frame-Originale in alle neuen Varianten kopieren und prüfen.")
    for variant in variants:
        for source in sources:
            copy_original(source, variant.reduced(source), overwrite=args.overwrite)
    # Globale Schranke: erst nach Prüfung sämtlicher Kopien irgendein Sheet reduzieren.
    for variant in variants:
        for source in sources:
            destination = variant.reduced(source)
            if sha256(destination) != source.sha256 or sha256(source.path) != source.sha256:
                raise ValueError(f"Originalkopie stimmt nicht mit der Quelle überein: {destination}")
            record(calls[variant.count], 2, "shutil.copyfileobj", source=str(source.path),
                   destination=str(destination), verified_sha256=source.sha256)

    phase(3, "Alle Kopien gleichmäßig reduzieren und horizontal als Nx1 speichern.")
    for variant in variants:
        for source in sources:
            destination = variant.reduced(source)
            if sha256(destination) != source.sha256:
                raise ValueError(f"Arbeitskopie hat sich vor der Reduktion geändert: {destination}")
            select.reduce_copy(destination, source_count=SOURCE_COUNT, target_count=variant.count,
                               source_grid=source.grid)
            record(calls[variant.count], 3, "PyImgFrameSelect.reduce_copy", path=str(destination),
                   source_count=SOURCE_COUNT, target_count=variant.count, source_grid=list(source.grid))

    phase(4, "GIFs mit 8 FPS und HTML in allen neuen PixelEng-Ordnern erstellen.")
    for variant in variants:
        make_previews([variant.reduced(s) for s in sources], (variant.count, 1),
                      variant.archive, calls[variant.count], 4, overwrite=args.overwrite)

    phase(5, "Alle reduzierten PNGs gemeinsam beschneiden und ins Zielraster packen.")
    for variant in variants:
        for source in sources:
            destination = variant.optimized(source)
            if not args.overwrite:
                require_new([destination])
            raster.convert_to_grid(variant.reduced(source), frame_count=variant.count,
                                   source_grid=(variant.count, 1), target_grid=variant.grid,
                                   optimize=True, output_path=destination, overwrite=args.overwrite)
            record(calls[variant.count], 5, "PyImgGrid.convert_to_grid", png_path=str(variant.reduced(source)),
                   frame_count=variant.count, source_grid=[variant.count, 1], target_grid=list(variant.grid),
                   optimize=True, output_path=str(destination), overwrite=args.overwrite)

    phase(6, "GIFs mit 8 FPS und HTML neben allen optimierten PNGs erstellen.")
    for variant in variants:
        make_previews([variant.optimized(s) for s in sources], variant.grid, variant.root,
                      calls[variant.count], 6, overwrite=args.overwrite)

    phase(7, "PNG-Pixel, GIF-Frames, Transparenz, Loop und HTML prüfen; Ergebnisse dokumentieren.")
    for variant in variants:
        results = verify_variant(variant, sources)
        document(variant, results, calls[variant.count], skipped, overwrite=args.overwrite)
        print(f"[OK] {variant.root.name}: {len(results)} Sheet(s) geprüft und dokumentiert.", flush=True)
    print(f"Fertig: {len(variants)} Variante(n) erstellt, {len(skipped)} übersprungen; "
          "16-Frame-Originale unverändert.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("source", nargs="?", type=Path, default=Path.cwd(),
                        help="Projektordner mit spritesheet-fram16/PixelEng; Standard: aktueller Ordner")
    parser.add_argument("--frames", nargs="+", type=int, choices=tuple(TARGET_GRIDS), default=list(TARGET_GRIDS),
                        help="Gewünschte Varianten; Standard: 8 10 12 14. Normal: belegte Varianten überspringen.")
    parser.add_argument("--grid", choices=("16x1", "1x16"),
                        help="Quellraster (Spalten x Zeilen); sonst längere Bildseite pro Datei")
    parser.add_argument("--dry-run", action="store_true", help="Plan und Quellen prüfen, nichts schreiben")
    parser.add_argument("--overwrite", action="store_true", help="Zugehörige PNGs/GIFs/HTML/Berichte aus Fram16 neu erzeugen")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except KeyboardInterrupt:
        print("\nAbgebrochen. Bereits belegte Zielordner werden im Normalmodus übersprungen.", file=sys.stderr)
        return 130
    except (ImportError, OSError, ValueError, SyntaxError) as exc:
        print(f"FEHLER: {exc}\nBereits geschriebene Zielordner bleiben erhalten und werden im Normalmodus "
              "übersprungen. Nach Prüfung mit --overwrite bewusst neu erstellen.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
