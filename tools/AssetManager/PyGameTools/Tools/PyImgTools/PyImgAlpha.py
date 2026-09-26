#!/usr/bin/env python3
"""PyImgAlpha: helle, dunkle oder graue Hintergründe transparent machen.

Nur Dateien direkt im aktuellen Terminalordner; keine rekursive Suche.
Originale bleiben unverändert. Neue Dateien landen als <Name>_alpha.png
im automatisch angelegten Unterordner ImgAlpha.
Automatische Randkorrektur: zusätzlich 1 Pixel am angrenzenden Motivrand entfernen.

Beispiele:
    PyImgAlpha -d
    PyImgAlpha --bright
    PyImgAlpha -g
    PyImgAlpha -g 7f7f7f -t 0  # Exakte Farbauswahl, plus 1 Pixel Randkorrektur
    PyImgAlpha -g 7f7f7f -t 12 --all  # Auch größere eingeschlossene Flächen entfernen
    PyImgAlpha -g a0a0a0 -t 0
    PyImgAlpha -d --tolerance 40
    PyImgAlpha -b --all
    PyImgAlpha --help

Abhängigkeit: Pillow (python3 -m pip install Pillow)

Standard: Nur passende, mit dem Bildrand verbundene Flächen als Hintergrund
auswählen (4er-Nachbarschaft). --all wählt zusätzlich eingeschlossene passende
Farbflächen ab 6 sichtbaren Pixeln. Kleine Innenflächen mit 1 bis 5 Pixeln
bleiben geschützt. Die Größe wird vor der Randkorrektur bestimmt.
Danach den ausgewählten Hintergrund um 1 Pixel erweitern, auch diagonal;
geschützte Innenflächen bleiben dabei erhalten. Diese Randkorrektur gilt
automatisch für alle Modi und auch bei -t 0. Sehr feine Konturen können entfallen.
Dies ist eine Farbschwellwert-Methode, keine Motiverkennung. Gleichfarbige
Konturen können mit entfernt werden; Farbsäume werden nicht entmischt.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
OUTPUT_SUFFIX = "_alpha"
OUTPUT_FOLDER = "ImgAlpha"
DEFAULT_TOLERANCE = 20
DEFAULT_GRAY = 0x7F
MAX_PROTECTED_INTERIOR_PIXELS = 5


class SkipImage(Exception):
    """Eine Datei wird absichtlich nicht verarbeitet."""


def tolerance_value(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Eine ganze Zahl von 0 bis 255 angeben.") from exc
    if not 0 <= value <= 255:
        raise argparse.ArgumentTypeError("Die Toleranz muss zwischen 0 und 255 liegen.")
    return value


def gray_value(text: str) -> int:
    value = text.removeprefix("#")
    if len(value) != 6 or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise argparse.ArgumentTypeError(
            "Einen Grauton als sechsstellige Hexfarbe angeben, z. B. 7f7f7f."
        )
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    if not red == green == blue:
        raise argparse.ArgumentTypeError(
            "Für einen Grauton müssen alle RGB-Kanäle gleich sein, z. B. 7f7f7f."
        )
    return red


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="PyImgAlpha",
        description=(
            "Macht schwarze/dunkle, weiße/helle oder graue Hintergründe transparent. "
            "Entfernt anschließend automatisch 1 Pixel am angrenzenden Motivrand. "
            "Verarbeitet nur Bilder direkt im aktuellen Terminalordner, "
            "keine Unterordner. Ergebnisse landen im Unterordner ImgAlpha. "
            "Originale werden nicht überschrieben."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  PyImgAlpha -d                    Dunklen Hintergrund entfernen\n"
            "  PyImgAlpha --bright              Hellen Hintergrund entfernen\n"
            "  PyImgAlpha -g                    Grauen Hintergrund (7f7f7f) entfernen\n"
            "  PyImgAlpha -g a0a0a0             Anderen Grauton entfernen\n"
            "  PyImgAlpha -g 7f7f7f -t 0        Exakt 7f7f7f wählen (Toleranz 0)\n"
            "                                  Danach zusätzlich 1 Pixel Rand entfernen\n"
            "  PyImgAlpha -g 7f7f7f -t 12 --all\n"
            "                                  Auch größere Innenflächen entfernen; kleine schützen\n"
            "  PyImgAlpha -d -t 40              Größere Abweichungen zulassen\n"
            "  PyImgAlpha -b -t 0               Exakt Weiß wählen, plus Randkorrektur\n"
            "  PyImgAlpha -b --all              Größere passende Innenflächen entfernen\n"
            "\n"
            "Dateien: PNG, JPG/JPEG, WEBP und BMP (nur Einzelbilder).\n"
            "Ausgabe: ImgAlpha/<Name>_alpha.png im aktuellen Terminalordner.\n"
            "Der Unterordner ImgAlpha wird automatisch angelegt.\n"
            "Vorhandene Ausgaben und *_alpha-Dateien werden übersprungen.\n"
            "Versteckte Dateien und symbolische Links werden ignoriert.\n"
            "Standardmäßig werden eingeschlossene Farbflächen nicht als Hintergrund gewählt.\n"
            f"Mit --all: Innenflächen mit 1 bis {MAX_PROTECTED_INTERIOR_PIXELS} passenden Pixeln schützen,\n"
            f"größere ab {MAX_PROTECTED_INTERIOR_PIXELS + 1} Pixeln entfernen (über Pixelkanten verbunden).\n"
            "Mit dem Bildrand verbundener Hintergrund wird unabhängig von der Größe entfernt.\n"
            "Randkorrektur: Zusätzlich 1 Pixel am angrenzenden Motivrand entfernen,\n"
            "automatisch für -g, -b und -d, auch bei -t 0 und mit --all.\n"
            "Geschützte kleine Innenflächen bleiben auch bei der Randkorrektur erhalten.\n"
            "Sehr feine Konturen können durch die Randkorrektur entfallen.\n"
            "Gleichfarbige Konturen am Hintergrund können dennoch entfernt werden.\n"
            "Farbsäume/komplexe Hintergründe werden nicht automatisch rekonstruiert."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "-d", "--dark", action="store_const", dest="mode", const="dark",
        help="Schwarze bzw. nahezu schwarze Hintergrundpixel entfernen.",
    )
    mode.add_argument(
        "-b", "--bright", action="store_const", dest="mode", const="bright",
        help="Weiße bzw. nahezu weiße Hintergrundpixel entfernen.",
    )
    mode.add_argument(
        "-g", "--gray", nargs="?", const=DEFAULT_GRAY, type=gray_value,
        metavar="HEX",
        help=(
            "Graue Hintergrundpixel entfernen (Standard: 7f7f7f). "
            "Optional einen Grauton als RRGGBB angeben, z. B. a0a0a0 "
            "oder mit # in Anführungszeichen: '#a0a0a0'."
        ),
    )
    parser.add_argument(
        "-t", "--tolerance", type=tolerance_value, default=DEFAULT_TOLERANCE,
        metavar="0-255",
        help=(
            "Abweichung von der Zielfarbe pro RGB-Kanal "
            f"(Standard: {DEFAULT_TOLERANCE}). "
            "0 = nur exakt die Zielfarbe erkennen; höher = mehr Farben erkennen. "
            "Anschließend immer 1 Pixel Randkorrektur."
        ),
    )
    parser.add_argument(
        "--all", dest="all_pixels", action="store_true",
        help=(
            f"Auch eingeschlossene passende Farbflächen ab {MAX_PROTECTED_INTERIOR_PIXELS + 1} "
            f"Pixeln entfernen; kleine Innenflächen mit 1 bis {MAX_PROTECTED_INTERIOR_PIXELS} "
            "Pixeln bleiben geschützt. Größere gleichfarbige Motivdetails können entfallen."
        ),
    )
    return parser


def find_images(folder: Path) -> list[Path]:
    """Nur eine Verzeichnisebene lesen, keine Unterordner betreten."""
    return sorted(
        (
            path for path in folder.iterdir()
            if not path.name.startswith(".")
            and not path.is_symlink()
            and path.is_file()
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
            and not path.stem.lower().endswith(OUTPUT_SUFFIX)
        ),
        key=lambda path: path.name.casefold(),
    )


def connected_to_border(mask: Image.Image) -> Image.Image:
    """255-Flächen auswählen, die über Kanten mit einem Bildrand verbunden sind.

    Iterative Füllung ganzer Zeilenabschnitte statt rekursiver Pixelaufrufe.
    0 = blockiert, 255 = noch nicht besucht, 128 = vom Rand erreichbar.
    Alle vier Bildränder werden berücksichtigt, nicht nur die Ecken.
    """
    from PIL import Image

    if mask.mode != "L":
        raise ValueError("Die Hintergrundmaske muss den Bildmodus L haben.")
    width, height = mask.size
    pixels = bytearray(mask.tobytes())
    stack: list[tuple[int, int, int]] = []

    def mark_run(index: int) -> int:
        """Hintergrundabschnitt markieren; exklusives rechtes Ende zurückgeben."""
        y = index // width
        row_start = y * width
        row_end = row_start + width
        left = index
        right = index + 1
        while left > row_start and pixels[left - 1] == 255:
            left -= 1
        while right < row_end and pixels[right] == 255:
            right += 1
        pixels[left:right] = b"\x80" * (right - left)
        stack.append((y, left - row_start, right - row_start))
        return right

    # Obere/untere Zeile vollständig prüfen, auch bei getrennten Flächen.
    edge_rows = (0,) if height == 1 else (0, height - 1)
    for y in edge_rows:
        row_end = (y + 1) * width
        index = pixels.find(b"\xff", y * width, row_end)
        while index != -1:
            end = mark_run(index)
            index = pixels.find(b"\xff", end, row_end)

    # Linker/rechter Rand aller übrigen Zeilen.
    for y in range(1, height - 1):
        left = y * width
        right = left + width - 1
        if pixels[left] == 255:
            mark_run(left)
        if pixels[right] == 255:
            mark_run(right)

    while stack:
        y, left, right = stack.pop()
        for neighbor_y in (y - 1, y + 1):
            if not 0 <= neighbor_y < height:
                continue
            row_start = neighbor_y * width
            search_end = row_start + right
            index = pixels.find(b"\xff", row_start + left, search_end)
            while index != -1:
                end = mark_run(index)
                index = pixels.find(b"\xff", end, search_end)

    result = Image.frombytes("L", (width, height), bytes(pixels))
    return result.point([255 if value == 128 else 0 for value in range(256)])


def small_regions(mask: Image.Image, max_pixels: int) -> Image.Image:
    """255-Flächen bis max_pixels auswählen; verbunden über Pixelkanten.

    Ganze Zeilenabschnitte besuchen. Nur für kleine Flächen Abschnitte merken,
    damit große Innenflächen keine vollständige Liste ihrer Pixel benötigen.
    """
    from PIL import Image

    if mask.mode != "L":
        raise ValueError("Die Flächenmaske muss den Bildmodus L haben.")
    if max_pixels < 1:
        raise ValueError("Die maximale Flächengröße muss mindestens 1 sein.")

    width, height = mask.size
    pixels = bytearray(mask.tobytes())
    selected = bytearray(len(pixels))
    stack: list[tuple[int, int, int]] = []
    runs: list[tuple[int, int]] = []
    region_size = 0

    def mark_run(index: int) -> int:
        nonlocal region_size
        y = index // width
        row_start = y * width
        row_end = row_start + width
        left = index
        right = index + 1
        while left > row_start and pixels[left - 1] == 255:
            left -= 1
        while right < row_end and pixels[right] == 255:
            right += 1
        pixels[left:right] = b"\x00" * (right - left)
        stack.append((y, left - row_start, right - row_start))
        region_size += right - left
        if region_size <= max_pixels:
            runs.append((left, right))
        else:
            runs.clear()
        return right

    seed = pixels.find(b"\xff")
    while seed != -1:
        region_size = 0
        runs.clear()
        mark_run(seed)
        while stack:
            y, left, right = stack.pop()
            for neighbor_y in (y - 1, y + 1):
                if not 0 <= neighbor_y < height:
                    continue
                row_start = neighbor_y * width
                search_end = row_start + right
                index = pixels.find(b"\xff", row_start + left, search_end)
                while index != -1:
                    end = mark_run(index)
                    index = pixels.find(b"\xff", end, search_end)
        if region_size <= max_pixels:
            for left, right in runs:
                selected[left:right] = b"\xff" * (right - left)
        seed = pixels.find(b"\xff", seed + 1)

    return Image.frombytes("L", (width, height), bytes(selected))


def remove_background(
    image: Image.Image,
    mode: str,
    tolerance: int,
    all_pixels: bool = False,
    gray_level: int = DEFAULT_GRAY,
) -> tuple[Image.Image, int]:
    """Hintergrund samt 1 Pixel Rand entfernen; kleine Innenflächen schützen."""
    from PIL import ImageChops, ImageFilter

    if mode not in {"dark", "bright", "gray"} or not 0 <= tolerance <= 255:
        raise ValueError("Ungültiger Modus oder Toleranzwert.")
    if mode == "gray" and not 0 <= gray_level <= 255:
        raise ValueError("Der Grauwert muss zwischen 0 und 255 liegen.")

    result = image.convert("RGBA")
    red, green, blue, alpha = result.split()

    # Alle drei Farbkanäle müssen innerhalb der Toleranz liegen.
    target = {"dark": 0, "bright": 255, "gray": gray_level}[mode]
    lut = [255 if abs(value - target) <= tolerance else 0 for value in range(256)]
    matches = ImageChops.darker(
        ImageChops.darker(red.point(lut), green.point(lut)), blue.point(lut)
    )

    # Bereits transparente Pixel sind als Verbindung durchquerbar.
    # Ihr RGB-Wert darf die Hintergrundsuche nicht blockieren.
    transparent = alpha.point([255] + [0] * 255)
    traversable = ImageChops.lighter(matches, transparent)
    border_background = connected_to_border(traversable)
    protected = None
    if all_pixels:
        # Nur sichtbare, eingeschlossene Farbpixel zählen. Unsichtbare RGB-Werte
        # dürfen aus einem kleinen Motivdetail keine große Farbfläche machen.
        inner_matches = ImageChops.subtract(
            matches, ImageChops.lighter(border_background, transparent)
        )
        protected = small_regions(inner_matches, MAX_PROTECTED_INTERIOR_PIXELS)
        removal_mask = ImageChops.lighter(
            border_background, ImageChops.subtract(inner_matches, protected)
        )
    else:
        removal_mask = border_background

    # Genau einen Pixel erweitern, auch diagonal. Geschützte Innenflächen
    # anschließend ausnehmen, falls die Korrektur einer Nachbarfläche sie berührt.
    removal_mask = removal_mask.filter(ImageFilter.MaxFilter(3))
    if protected is not None:
        removal_mask = ImageChops.subtract(removal_mask, protected)

    old_transparent = alpha.histogram()[0]
    new_alpha = alpha.copy()
    new_alpha.paste(0, mask=removal_mask)
    removed = new_alpha.histogram()[0] - old_transparent
    result.putalpha(new_alpha)
    return result, removed


def save_new_png(image: Image.Image, output: Path, options: dict) -> None:
    """Nie überschreiben; bei Schreibfehler/Abbruch unfertige Ausgabe entfernen."""
    created = False
    try:
        with output.open("xb") as stream:
            created = True
            image.save(stream, format="PNG", compress_level=9, optimize=True, **options)
    except BaseException:
        if created:
            try:
                output.unlink()
            except OSError:
                pass
        raise


def convert_image(
    path: Path,
    mode: str,
    tolerance: int,
    all_pixels: bool,
    gray_level: int = DEFAULT_GRAY,
) -> str:
    from PIL import Image, ImageOps

    output = path.parent / OUTPUT_FOLDER / f"{path.stem}{OUTPUT_SUFFIX}.png"
    output_label = output.relative_to(path.parent)
    # lexists erkennt auch kaputte symbolische Links am Ausgabeort.
    if os.path.lexists(output):
        print(f"[SKIP] {path.name} -> Ausgabe existiert: {output_label}")
        return "skipped"

    print(f"[RUN] {path.name}", flush=True)
    result = None
    try:
        with Image.open(path) as source:
            if getattr(source, "n_frames", 1) != 1:
                raise SkipImage("Animierte Dateien werden nicht in Einzelbilder umgewandelt.")
            if source.mode not in {"1", "L", "LA", "P", "RGB", "RGBA", "RGBX"}:
                raise SkipImage(
                    f"Bildmodus {source.mode} wird nicht unterstützt; bitte als 8-Bit-RGB/RGBA exportieren."
                )
            options = {}
            if source.info.get("icc_profile") and source.mode in {"RGB", "RGBA", "RGBX"}:
                options["icc_profile"] = source.info["icc_profile"]
            if source.info.get("dpi"):
                options["dpi"] = source.info["dpi"]
            # EXIF-Anzeigeorientierung übernehmen, nicht skalieren/zuschneiden.
            with ImageOps.exif_transpose(source) as oriented:
                result, removed = remove_background(
                    oriented, mode, tolerance, all_pixels, gray_level
                )

        if removed == 0:
            print("[SKIP] Keine passenden sichtbaren Hintergrundpixel gefunden.")
            return "skipped"

        output.parent.mkdir(exist_ok=True)
        try:
            save_new_png(result, output, options)
        except FileExistsError:
            print(f"[SKIP] Ausgabe wurde inzwischen angelegt: {output_label}")
            return "skipped"
        pixels = result.width * result.height
        print(f"[OK] {path.name} -> {output_label}")
        print(f"     Größe: {result.width} x {result.height} px (keine Skalierung)")
        print(f"     Neu transparent: {removed:,} Pixel ({removed / pixels:.1%})")
        if result.getchannel("A").getbbox() is None:
            print(
                "[WARN] Das Ergebnis ist vollständig transparent. "
                "Modus, Toleranz und 1-Pixel-Randkorrektur prüfen."
            )
        return "created"
    except SkipImage as exc:
        print(f"[SKIP] {path.name}: {exc}")
        return "skipped"
    except (OSError, ValueError, MemoryError, Image.DecompressionBombError) as exc:
        print(f"[ERROR] {path.name}: {exc}")
        return "errors"
    finally:
        if result is not None:
            result.close()


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    mode = "gray" if args.gray is not None else args.mode
    gray_level = DEFAULT_GRAY if args.gray is None else args.gray
    # Hilfe bleibt auch ohne installiertes Pillow verfügbar.
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("[ERROR] Pillow fehlt. Installation: python3 -m pip install Pillow", file=sys.stderr)
        return 1

    try:
        folder = Path.cwd()
        files = find_images(folder)
    except OSError as exc:
        print(f"[ERROR] Ordner kann nicht gelesen werden: {exc}", file=sys.stderr)
        return 1

    print(f"[INFO] Ordner: {folder}")
    print("[INFO] Nur dieser Ordner. Keine Unterordner.")
    print(f"[INFO] Ausgabeordner: {folder / OUTPUT_FOLDER}")
    print(f"[INFO] Modus: {mode} | Toleranz: {args.tolerance}")
    if mode == "gray":
        print("[INFO] Grauton: #" + f"{gray_level:02x}" * 3)
    print("[INFO] Bereich: " + ("gesamtes Bild" if args.all_pixels else "vom Bildrand aus"))
    if args.all_pixels:
        print(
            f"[INFO] Innenschutz: Flächen mit 1 bis {MAX_PROTECTED_INTERIOR_PIXELS} Pixeln erhalten; "
            f"ab {MAX_PROTECTED_INTERIOR_PIXELS + 1} Pixeln entfernen"
        )
    print("[INFO] Randkorrektur: automatisch 1 Pixel am angrenzenden Motivrand")
    print(f"[INFO] {len(files)} mögliche Quelldatei(en).\n")
    if not files:
        print("[DONE] Keine passenden Bilddateien gefunden.")
        return 0

    counts = {"created": 0, "skipped": 0, "errors": 0}
    for path in files:
        status = convert_image(path, mode, args.tolerance, args.all_pixels, gray_level)
        counts[status] += 1
        print()

    print(
        f"[DONE] Erstellt: {counts['created']} | "
        f"Übersprungen: {counts['skipped']} | Fehler: {counts['errors']}"
    )
    return 1 if counts["errors"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[ABORT] Abgebrochen. Originaldateien bleiben unverändert.", file=sys.stderr)
        raise SystemExit(130)
