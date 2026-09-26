#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyImgScal: Bilder im aktuellen Arbeitsordner exakt skalieren und klären.

Python >= 3.10, Pillow >= 10.3 (einzige externe Abhängigkeit).
Installation: python3 -m pip install --upgrade Pillow

Beispiele:
    python3 PyImgScal.py --256 --256
    python3 PyImgScal.py -56 -56 -c 5
    python3 PyImgScal.py 256 128 --clarity 3.5
    python3 PyImgScal.py --256 --256 --pxart -c 0
    python3 PyImgScal.py --help

Keine Rekursion. Originale bleiben unverändert. Ausgabe: 8-Bit-PNG.
Die Zielgröße gilt für das GESAMTE Bild, nicht für einzelne Atlas-Frames.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import warnings
from typing import Sequence

# Pillow wird erst nach der Argumentprüfung geladen. --help funktioniert auch
# dann, wenn Pillow noch nicht installiert wurde.
DEFAULT_CLARITY = 3.0
MAX_TARGET_PIXELS = 64_000_000
EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".jpe", ".jfif", ".webp", ".avif",
    ".bmp", ".dib", ".tif", ".tiff", ".gif", ".tga", ".icb",
    ".vda", ".vst", ".ppm", ".pgm", ".pbm", ".pnm",
})
SIZE_TOKEN = re.compile(r"^(?:--?)?([0-9]+)$")


class SkipImage(Exception):
    """Datei bewusst überspringen, ohne den restlichen Stapel abzubrechen."""


@dataclass(frozen=True)
class Settings:
    width: int
    height: int
    clarity: float
    overwrite: bool = False
    pxart: bool = False

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height

    @property
    def output_folder(self) -> str:
        level = format(self.clarity, ".12g").replace(".", "p")
        mode = "_pxart" if self.pxart else ""
        return f"_scal_{self.width}x{self.height}_c{level}{mode}"


def clarity_value(text: str) -> float:
    try:
        value = float(text.replace(",", "."))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Klarheit muss eine Zahl von 0 bis 10 sein.") from exc
    if not math.isfinite(value) or not 0 <= value <= 10:
        raise argparse.ArgumentTypeError("Klarheit muss zwischen 0 und 10 liegen.")
    # Nicht zwischen 0 und -0 bei Ordnernamen unterscheiden.
    return 0.0 if value == 0 else value


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="PyImgScal",
        add_help=False,
        allow_abbrev=False,
        usage="%(prog)s --BREITE --HÖHE [-c STÄRKE] [--pxart] [--overwrite]",
        description=(
            "Skaliert Bilddateien direkt im aktuellen Terminalordner auf exakt\n"
            "BREITE x HÖHE Pixel und verbessert danach ihre Klarheit.\n"
            "Unterordner werden NICHT durchsucht. Originale bleiben unverändert."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Beispiele:
  PyImgScal --256 --256                  256 x 256 px, Klarheit 3 (Standard)
  PyImgScal -256 -256                    dieselbe Wirkung
  PyImgScal --56 --56 --clarity 5         56 x 56 px, Klarheit 5
  PyImgScal -56 -56 -c 5                 dieselbe Wirkung
  PyImgScal 256 128 -c 3.5               256 x 128 px, Klarheit 3.5
  PyImgScal --256 --256 -c 0             nur skalieren, keine Klarheit
  PyImgScal --256 --256 --pxart -c 0     Pixel-Art-Skalierung ohne Mischfarben
  PyImgScal --256 --256 --overwrite      vorhandene Ausgaben neu erzeugen
  python3 /pfad/PyImgScal.py --256 --256  bearbeitet den TERMINALORDNER

Klarheit (0 bis 10, Dezimalzahlen und Dezimalkomma sind erlaubt):
  0      ausgeschaltet; nur skalieren
  1-2    sehr dezent
  3      leicht: Standard
  4-6    mittel bis deutlich
  7-8    stark
  9-10   sehr stark; kann Bildrauschen oder Kontursäume betonen

Verarbeitung:
  Standard: Lanczos-Skalierung + lokaler Kontrast + feine Nachschärfung.
  --pxart verwendet stattdessen Nächster-Nachbar-Skalierung: harte Pixelkanten,
  keine durch die Skalierung erzeugten Mischfarben und keine Kantenglättung.
  Die gewählte Klarheit wird auch mit --pxart danach angewendet; mit -c 0
  bleiben die von der Skalierung ausgewählten Farbwerte unverändert.
  Transparenz wird beim Filtern berücksichtigt. Der bereits skalierte
  Alphakanal wird durch die Klarheitsstufe nicht verändert.
  Es gibt keine KI-Rekonstruktion oder automatische Frame-Erkennung.

Dateien und Ausgabe:
  PNG, JPG/JPEG, WebP, AVIF*, BMP, TIFF, statisches GIF, TGA, PPM/PGM/PBM.
  * AVIF/WebP usw. benötigen den passenden Codec in deiner Pillow-Installation.
  Ausgabe immer als 8-Bit-PNG: _scal_256x256_c3/NAME.png
  Mit --pxart: _scal_256x256_c3_pxart/NAME.png
  Größe, Klarheit und Modus bestimmen den Ausgabeordner; 3.5 wird zu 3p5.
  Bestehende Ausgaben werden übersprungen, außer mit --overwrite.
  Bei gleichen Basisnamen werden unterscheidbare Dateinamen verwendet.
  Versteckte Dateien, symbolische Links und alle Unterordner werden ignoriert.
  Animierte/mehrseitige Dateien und HDR-/16-Bit-Graubilder werden mit Hinweis
  übersprungen, statt unbemerkt Frames oder Tonwerte zu verlieren.

Wichtig:
  Die erste Zahl ist die BREITE, die zweite die HÖHE.
  Ein anderes Seitenverhältnis VERZERRT das Bild; kein Beschnitt, kein Rand.
  Kleinere Bilder werden vergrößert, damit die Zielgröße immer exakt stimmt.
  Für gleichmäßige Pixelblöcke mit --pxart ganzzahlige Größenfaktoren verwenden.
  Bei Atlanten gilt die Größe für das GESAMTE Spritesheet, nicht pro Frame.
  Framegrenzen und externe Atlas-/Godot-Metadaten werden nicht angepasst.
  Sicherheitsgrenze: maximal 64 Millionen Zielpixel; Pillow schützt zusätzlich
  vor außergewöhnlich großen Quelldateien. Viel RAM kann trotzdem nötig sein.

Exit-Codes: 0 = fertig/übersprungen; 1 = Datei-/Laufzeitfehler;
            2 = ungültige Argumente; 130 = mit Strg+C abgebrochen.
""",
    )
    parser._optionals.title = "Optionen"
    parser.add_argument("-h", "--help", action="help", help="Diese Hilfe anzeigen und beenden.")
    parser.add_argument(
        "-c", "--clarity", type=clarity_value, default=DEFAULT_CLARITY,
        metavar="STÄRKE", help="Klarheit von 0 bis 10 (Standard: 3).",
    )
    parser.add_argument(
        "--pxart", action="store_true",
        help="Pixel-Art-Modus: Nächster-Nachbar statt Lanczos verwenden.",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Nur vorhandene Ausgaben dieser Einstellungen ersetzen, nie Originale.",
    )
    parser.add_argument("width", metavar="BREITE", type=int, help=argparse.SUPPRESS)
    parser.add_argument("height", metavar="HÖHE", type=int, help=argparse.SUPPRESS)
    return parser


def normalize_size_arguments(argv: Sequence[str]) -> list[str]:
    """--256 und -256 als Größen lesen, NICHT einen Wert nach -c verändern.

    Beispiel: -c -5 muss ungültig bleiben und darf nicht zu Klarheit 5 werden.
    Auch --clarity=5 und -c5 werden regulär von argparse verarbeitet.
    """
    result: list[str] = []
    expecting_clarity = False
    after_separator = False
    for token in argv:
        if expecting_clarity:
            result.append(token)
            expecting_clarity = False
        elif token in ("-c", "--clarity") and not after_separator:
            result.append(token)
            expecting_clarity = True
        elif token == "--":
            result.append(token)
            after_separator = True
        elif (match := SIZE_TOKEN.fullmatch(token)) and not after_separator:
            result.append(match.group(1))
        else:
            result.append(token)
    return result


def parse_arguments(argv: Sequence[str] | None = None) -> Settings:
    parser = make_parser()
    args = sys.argv[1:] if argv is None else list(argv)
    if not args:
        parser.print_help()
        parser.exit(2, "\nEs fehlen Breite und Höhe, z. B. --256 --256.\n")
    normalized = normalize_size_arguments(args)
    options = parser.parse_intermixed_args(normalized)
    if options.width <= 0 or options.height <= 0:
        parser.error("Breite und Höhe müssen positive ganze Pixelzahlen sein.")
    if options.width * options.height > MAX_TARGET_PIXELS:
        parser.error("Die Zielgröße überschreitet die Grenze von 64 Millionen Pixeln.")
    return Settings(
        options.width,
        options.height,
        options.clarity,
        overwrite=options.overwrite,
        pxart=options.pxart,
    )


def load_pillow() -> None:
    global Image, ImageChops, ImageFilter, ImageMath, ImageOps
    try:
        from PIL import Image, ImageChops, ImageFilter, ImageMath, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "Pillow fehlt oder ist unvollständig. Installieren mit:\n"
            "  python3 -m pip install --upgrade Pillow"
        ) from exc
    if not hasattr(Image, "Resampling") or not hasattr(ImageMath, "lambda_eval"):
        raise RuntimeError(
            "Pillow ist zu alt (mindestens 10.3 erforderlich). Aktualisieren mit:\n"
            "  python3 -m pip install --upgrade Pillow"
        )
    # Schutz nicht ausschalten: Zu große Einzeldateien melden und weitermachen.
    warnings.simplefilter("error", Image.DecompressionBombWarning)


def find_images(folder: Path) -> list[Path]:
    return sorted(
        (
            path for path in folder.iterdir()
            if not path.name.startswith(".")
            and not path.is_symlink()
            and path.is_file()
            and path.suffix.lower() in EXTENSIONS
        ),
        key=lambda path: (path.name.casefold(), path.name),
    )


def output_names(sources: Sequence[Path]) -> dict[Path, str]:
    """Normale Namen kurz halten; Kollisionen nicht gegenseitig überschreiben."""
    counts = Counter(path.stem.casefold() for path in sources)
    # Reserviert auch natürliche Namen, damit generierte Namen diese nicht belegen.
    reserved = {f"{path.stem}.png".casefold() for path in sources}
    used: set[str] = set()
    names: dict[Path, str] = {}
    for source in sources:
        candidate = f"{source.stem}.png"
        if counts[source.stem.casefold()] > 1:
            candidate = f"{source.name}.png"
            serial = 0
            while candidate.casefold() in reserved or candidate.casefold() in used:
                digest = hashlib.sha256(
                    os.fsencode(source.name) + str(serial).encode("ascii")
                ).hexdigest()[:10]
                candidate = f"{source.stem}_{digest}.png"
                serial += 1
        if candidate.casefold() in used:
            raise RuntimeError(f"Nicht auflösbare Namenskollision: {source.name}")
        used.add(candidate.casefold())
        names[source] = candidate
    return names


def read_image(source: Path):
    """Ein Standbild laden, EXIF-Drehung anwenden, RGB/RGBA vorbereiten."""
    with Image.open(source) as opened:
        if getattr(opened, "is_animated", False) or getattr(opened, "n_frames", 1) > 1:
            raise SkipImage("Animation/mehrseitige Datei; keine Frames verworfen")
        if opened.mode in {"I", "F"} or opened.mode.startswith("I;16"):
            raise SkipImage("HDR-/16-Bit-Graubild; keine automatische 8-Bit-Reduktion")
        opened.load()
        oriented = ImageOps.exif_transpose(opened)
        has_alpha = (
            "A" in oriented.getbands() or "a" in oriented.getbands()
            or "transparency" in oriented.info
            or (oriented.palette is not None and oriented.palette.mode == "RGBA")
        )
        # Ein RGB-Profil bleibt bei RGB->RGB/RGBA gültig; ein CMYK-/Grauprofil
        # darf dagegen nicht fälschlich an eine RGB-Ausgabe angehängt werden.
        profile = (
            oriented.info.get("icc_profile")
            if oriented.mode in {"RGB", "RGBA", "P", "PA", "RGBX"} else None
        )
        image = oriented.convert("RGBA" if has_alpha else "RGB")
        image.info.clear()  # Keine veralteten EXIF-Größen/Orientierungen übernehmen.
        return image, profile


def resize_exact(image, size: tuple[int, int], pixel_art: bool = False):
    if image.size == size:
        return image.copy()
    if pixel_art:
        # Nächster Nachbar übernimmt ausschließlich vorhandene Pixelwerte und
        # erzeugt weder Mischfarben noch weichgezeichnete Pixelkanten.
        return image.resize(size, Image.Resampling.NEAREST)
    if image.mode == "RGBA":
        # Sichtbare Farben mit Alpha gewichten. Dadurch werden unsichtbare RGB-
        # Werte transparenter Pixel beim Verkleinern nicht als Hintergrund gemischt.
        return (
            image.convert("RGBa")
            .resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0)
            .convert("RGBA")
        )
    return image.resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0)


def weighted_blur(rgb, alpha, radius: float):
    """Farbmittelwert ohne Beimischung eines schwarzen/weißen Alpha-Hintergrunds."""
    if alpha is None:
        return rgb.filter(ImageFilter.GaussianBlur(radius))
    rgba = rgb.copy()
    rgba.putalpha(alpha)
    return (
        rgba.convert("RGBa")
        .filter(ImageFilter.GaussianBlur(radius))
        .convert("RGBA")
        .convert("RGB")
    )


def enhance_detail(rgb, alpha, amount: float, radius: float, limit: float):
    """Alpha-gewichtete, begrenzte Unscharfmaskierung auf RGB-Kanälen.

    Kleine Radien betonen feine Kanten; größere Radien den lokalen Kontrast.
    Die Änderung wird begrenzt und unterhalb kleiner Unterschiede ausgeblendet.
    Es wird kein frei formulierter Code/String ausgewertet (nur feste Lambda).
    """
    blurred = weighted_blur(rgb, alpha, radius)
    bands = []
    for original, smooth in zip(rgb.split(), blurred.split()):
        # Float-Rechnung verhindert Über-/Unterlauf beim Bildkanal-Abzug.
        sharpened = ImageMath.lambda_eval(
            lambda p: p["convert"](
                p["original"]
                + p["min"](
                    p["max"]((p["original"] - p["smooth"]) * amount, -limit),
                    limit,
                )
                + 0.5,
                "L",
            ),
            original=original.convert("F"),
            smooth=smooth.convert("F"),
        )
        bands.append(sharpened)
    enhanced = Image.merge("RGB", bands)
    differences = ImageChops.difference(rgb, blurred).split()
    difference = ImageChops.lighter(ImageChops.lighter(*differences[:2]), differences[2])
    # 0-2 Tonwertstufen nicht verstärken; 3-6 weich einblenden. Das dämpft
    # Rundungsfehler und sehr schwaches Rauschen, ohne vorher Details weichzuzeichnen.
    mask = difference.point([max(0, min(255, (value - 2) * 64)) for value in range(256)])
    if alpha is not None:
        edge_protection = alpha.point([round(value * value / 255) for value in range(256)])
        mask = ImageChops.multiply(mask, edge_protection)
    return Image.composite(enhanced, rgb, mask)


def improve_clarity(image, strength: float):
    if strength == 0:
        return image.copy()
    alpha = image.getchannel("A") if image.mode == "RGBA" else None
    rgb = image.convert("RGB")
    # Gleiche Radien für jede Stufe: Die Stärke ändert sich nachvollziehbar.
    # Kleine Zielbilder brauchen kleinere Radien für den lokalen Kontrast.
    local_radius = max(1.2, min(4.0, min(image.size) / 64.0))
    rgb = enhance_detail(
        rgb, alpha, amount=0.025 * strength, radius=local_radius,
        limit=2.0 * strength,
    )
    rgb = enhance_detail(
        rgb, alpha, amount=0.18 * strength, radius=0.7,
        limit=4.0 * strength,
    )
    if alpha is not None:
        rgb.putalpha(alpha)  # Exakt derselbe Alphakanal wie nach resize_exact.
    return rgb


def save_png(image, destination: Path, profile: bytes | None, overwrite: bool) -> None:
    """Erst vollständig codieren. Bestehende Dateien standardmäßig schützen."""
    fd, temp_name = tempfile.mkstemp(prefix=".pyimgscal_", suffix=".tmp", dir=destination.parent)
    temporary = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            image.save(stream, format="PNG", compress_level=6, icc_profile=profile)
        if overwrite:
            # Austausch erst, wenn das neue Bild vollständig gespeichert wurde.
            os.replace(temporary, destination)
        else:
            # Exklusiv öffnen: Auch ein zeitgleich gestarteter zweiter Lauf kann
            # eine bereits vorhandene Ausgabe nicht versehentlich überschreiben.
            with destination.open("xb") as output:
                try:
                    with temporary.open("rb") as encoded:
                        shutil.copyfileobj(encoded, output, length=1024 * 1024)
                except BaseException:
                    output.close()
                    destination.unlink(missing_ok=True)
                    raise
    finally:
        temporary.unlink(missing_ok=True)


def run(settings: Settings) -> int:
    folder = Path.cwd()  # Absichtlich NICHT Path(__file__).parent!
    sources = find_images(folder)
    destination_folder = folder / settings.output_folder
    print(f"\nPyImgScal | Ziel: {settings.width} x {settings.height} px | Klarheit: {settings.clarity:g}/10")
    print(f"Skalierung: {'Pixel-Art (Nächster Nachbar)' if settings.pxart else 'Lanczos'}")
    print(f"Eingabe : {folder}")
    print(f"Ausgabe : {destination_folder}")
    print("Nur dieser Terminalordner, keine Unterordner. Originale bleiben unverändert.")
    print("Exakte Zielgröße: Abweichende Seitenverhältnisse werden verzerrt.\n")
    if not sources:
        print("Keine unterstützten Bilddateien gefunden.")
        return 0
    if destination_folder.is_symlink():
        raise RuntimeError("Der Ausgabeordner ist ein symbolischer Link. Aus Sicherheitsgründen abgebrochen.")
    destination_folder.mkdir(exist_ok=True)
    names = output_names(sources)
    done = skipped = errors = 0
    for number, source in enumerate(sources, 1):
        destination = destination_folder / names[source]
        prefix = f"[{number}/{len(sources)}]"
        image = scaled = result = None
        try:
            if destination.is_symlink():
                raise SkipImage("Ausgabe ist ein symbolischer Link")
            if os.path.lexists(destination) and not settings.overwrite:
                raise SkipImage("Ausgabe vorhanden; zum Ersetzen --overwrite verwenden")
            if destination.exists() and not destination.is_file():
                raise SkipImage("Ausgabepfad ist keine normale Datei")
            image, profile = read_image(source)
            original_size = image.size
            scaled = resize_exact(image, settings.size, pixel_art=settings.pxart)
            result = improve_clarity(scaled, settings.clarity)
            save_png(result, destination, profile, settings.overwrite)
            done += 1
            notes: list[str] = []
            if settings.width > original_size[0] or settings.height > original_size[1]:
                notes.append("mindestens eine Achse vergrößert")
            if original_size[0] * settings.height != original_size[1] * settings.width:
                notes.append("Seitenverhältnis geändert")
            note = f" ({'; '.join(notes)})" if notes else ""
            print(
                f"{prefix} OK   {source.name}: {original_size[0]} x {original_size[1]}"
                f" -> {settings.width} x {settings.height} -> {destination.name}{note}",
                flush=True,
            )
        except (SkipImage, FileExistsError) as exc:
            skipped += 1
            print(f"{prefix} SKIP {source.name}: {exc}", flush=True)
        except MemoryError:
            errors += 1
            print(f"{prefix} FEHLER {source.name}: Nicht genügend Arbeitsspeicher.", flush=True)
        except Exception as exc:
            # Eine beschädigte/unsupported Datei darf andere Bilder nicht stoppen.
            errors += 1
            print(f"{prefix} FEHLER {source.name}: {type(exc).__name__}: {exc}", flush=True)
        finally:
            # Große Quellbilder nicht bis zum nächsten vollständigen Laden halten.
            for buffer in (image, scaled, result):
                if buffer is not None:
                    buffer.close()
    print(f"\nFertig: {done} erstellt | {skipped} übersprungen | {errors} Fehler")
    return 1 if errors else 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        settings = parse_arguments(argv)
        load_pillow()
        return run(settings)
    except KeyboardInterrupt:
        print("\nAbgebrochen. Originale bleiben unverändert.", file=sys.stderr)
        return 130
    except (OSError, RuntimeError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
