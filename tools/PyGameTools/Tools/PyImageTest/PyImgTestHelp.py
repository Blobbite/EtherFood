#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Farbiges Hilfeverzeichnis für die Python-Bildwerkzeuge dieses Ordners.

Das Programm importiert oder startet keines der aufgelisteten Skripte. Dadurch
funktioniert die Übersicht auch dann, wenn optionale Bildbibliotheken fehlen.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import difflib
import os
from pathlib import Path
import shlex
import shutil
import sys
import textwrap
from typing import Sequence, TextIO


@dataclass(frozen=True)
class ScriptInfo:
    """Von Hand geprüfte Kurzhilfe für ein Skript."""

    category: str
    icon: str
    description: str
    usage: str
    scope: str
    output: str
    dependencies: tuple[str, ...] = ()
    hint: str = ""


SCRIPT_DESCRIPTIONS = {'PyImgTestAll.py': 'Vorhandene Bildgruppen-Tests nacheinander im aktuellen Ordner ausführen.', 'PyImgTestBC.py': 'Helligkeit und Kontrast mehrerer Bilder als gemeinsame Gruppe prüfen.', 'PyImgTestCentral.py': 'Fußanker, Mittelachse, Kopf-/Oberkante und Positionssprünge prüfen.', 'PyImgTestCompare.py': 'Bildgruppen auf technische und visuelle Konsistenz prüfen', 'PyImgTestHelp.py': 'Hilfe zu den Werkzeugen und zum Auswahlmenü anzeigen', 'PyImgTestPalette.py': 'Farbpaletten mehrerer Bilder im aktuellen Ordner vergleichen.', 'PyImgTestVram.py': 'Texturspeicherbedarf von PNG-Spritesheets abschätzen', 'PyImgTuneColor.py': 'Eigenständiger, einmaliger Farbprofil-Abgleich für einen PNG-Bildsatz.', 'PyImageTest.py': 'dieses Menü; Werkzeuge auswählen und starten'}

MENU_HELP = 'Auswahlmenü PyImageTest\nStart: python3 /pfad/PyImageTest/PyImageTest.py\nPfeiltasten hoch/runter wählen, Enter startet, Q oder Escape beendet.\nDer eigene Menüeintrag aktualisiert die Auswahl. Lange Listen sind scrollbar.\nNach einem Lauf bleibt die Ausgabe stehen; Enter lädt die Auswahl neu.\n--plain: Nummernauswahl; --list: nur Liste; --dir ORDNER: anderer Skriptordner.\n--help: Bedienung. Ohne interaktive Eingabe erscheint nur die Liste,\naußer bei ausdrücklich gewähltem --plain. Bei einfachen Terminals Nummernauswahl.\nNeue .py-Dateien direkt im Skriptordner erscheinen automatisch, keine Unterordner.\nKurztexte stammen aus dieser Hilfe, sonst aus dem Modul-Docstring.\nDer Python-Interpreter, die Umgebung und der Arbeitsordner bleiben erhalten.\nDas Menü benötigt keine Zusatzpakete; die Werkzeuge haben eigene Abhängigkeiten.\nSkripte starten ohne zusätzliche Argumente. Für Werkzeuge mit Pflichtoptionen\n(z.B. PyImgGif --fps 8) den direkten Skriptaufruf mit den gewünschten Optionen nutzen.\n'



CATEGORIES = {
    "workflow": (10, "🪄", "Kombination & Automatisierung"),
    "background": (20, "🖼️", "Hintergrund & Zuschnitt"),
    "sprites": (30, "🧩", "Spritesheets"),
    "convert": (40, "🛠️", "Größe & Format"),
    "help": (50, "📚", "Dokumentation"),
    "other": (90, "🐍", "Weitere Python-Skripte"),
}


# Diese Angaben wurden anhand der Skripte in diesem Ordner geprüft. Dateien,
# die später hinzukommen, erscheinen ebenfalls und erhalten als Beschreibung
# automatisch den ersten Absatz ihres Modul-Docstrings.
SCRIPT_CATALOG = {
    "PyIMagic.py": ScriptInfo(
        category="workflow",
        icon="🪄",
        description=(
            "Verknüpft PyImgH (Motiv freistellen) und PyImgCut (auf sichtbaren "
            "Inhalt zuschneiden) zu einem wählbaren Stapel-Workflow."
        ),
        usage="python3 PyIMagic.py (--h | --cut | --h --cut) [-i ORDNER] [-o ORDNER]",
        scope="Wählbarer Eingabeordner; verarbeitet dessen Bilddateien ohne Unterordner.",
        output="Je nach Schritten nach Img, ImgCut oder in den mit --output gewählten Ordner.",
        dependencies=("Pillow", "NumPy", "OpenCV"),
        hint="Bei --h --cut wird zuerst freigestellt und danach zugeschnitten.",
    ),
    "PyImgAlpha.py": ScriptInfo(
        category="background",
        icon="🫥",
        description=(
            "Macht dunkle oder helle, mit dem Bildrand verbundene Hintergründe "
            "transparent; mit --all gilt die Farbschwelle für das gesamte Bild."
        ),
        usage="python3 PyImgAlpha.py (--dark | --bright) [-t 0-255] [--all]",
        scope="Unterstützte Bilder direkt im aktuellen Terminalordner; keine Unterordner.",
        output="Neue PNG-Dateien als <Name>_alpha.png neben den Originalen.",
        dependencies=("Pillow",),
        hint="Originale und vorhandene Ausgaben werden nicht überschrieben.",
    ),
    "PyImgCut.py": ScriptInfo(
        category="background",
        icon="✂️",
        description=(
            "Schneidet Bilder auf den erkannten sichtbaren Inhalt zu und entfernt "
            "dadurch überflüssige transparente Außenränder."
        ),
        usage="python3 PyImgCut.py",
        scope="Unterstützte Bilder direkt im aktuellen Terminalordner; keine Unterordner.",
        output="Zugeschnittene Bilder mit gleichem Namen im Unterordner ImgCut.",
        dependencies=("Pillow", "NumPy"),
        hint="Schwellwerte und Formate werden im SETTINGS-Block des Skripts eingestellt.",
    ),
    "PyImgD.py": ScriptInfo(
        category="background",
        icon="🌑",
        description=(
            "Erkennt größere dunkle Konturbereiche per Schwellenwert und Canny-Kanten "
            "und macht genau diese erkannten Bereiche transparent."
        ),
        usage="python3 PyImgD.py",
        scope="Unterstützte Bilder direkt im aktuellen Terminalordner; keine Unterordner.",
        output="Bearbeitete Bilder mit gleichem Namen im Unterordner Img.",
        dependencies=("Pillow", "NumPy", "OpenCV"),
        hint="Verarbeitungsparameter werden im SETTINGS-Block des Skripts eingestellt.",
    ),
    "PyImgH.py": ScriptInfo(
        category="background",
        icon="🎯",
        description=(
            "Extrahiert größere dunkle Konturbereiche per Schwellenwert und "
            "Canny-Kanten; alles außerhalb der erkannten Motive wird transparent."
        ),
        usage="python3 PyImgH.py",
        scope="Unterstützte Bilder direkt im aktuellen Terminalordner; keine Unterordner.",
        output="Freigestellte Bilder mit gleichem Namen im Unterordner Img.",
        dependencies=("Pillow", "NumPy", "OpenCV"),
        hint="Kann über PyIMagic mit PyImgCut kombiniert werden; Parameter stehen in SETTINGS.",
    ),
    "PyImg2x3.py": ScriptInfo(
        category="sprites",
        icon="6️⃣",
        description=(
            "Teilt sechs waagerecht angeordnete Frames und setzt sie als "
            "2×3-Spritesheet neu zusammen."
        ),
        usage="python3 PyImg2x3.py [--optimize]",
        scope=(
            "Sucht rekursiv ab dem Terminalordner nach *spritesheet.png; "
            "versteckte Ordner werden ignoriert."
        ),
        output="Neben der Quelle als <Name>_2x3.png bzw. mit Optimierung als <Name>_2x3_o.png.",
        dependencies=("Pillow",),
        hint="--optimize entfernt den gemeinsamen vollständig transparenten Außenrand.",
    ),
    "PyImgGrid.py": ScriptInfo(
        category="sprites",
        icon="🔢",
        description=(
            "Ordnet PNG-Frames in ein frei vorgegebenes Raster um und entfernt "
            "optional den gemeinsamen transparenten Außenrand."
        ),
        usage=("python3 Pipline/PiplineToos/PyImgGrid.py [QUELLE] --frames 8 "
               "--source-grid 1x8 --target-grid 4x2 --optimize"),
        scope=(
            "Gemeinsames Pipeline-Werkzeug: PNG oder Ordner; Unterordner mit --recursive. "
            "Raster-Ausgaben und versteckte Dateien werden bei der Ordnersuche ausgelassen."
        ),
        output="Neben der Quelle oder in --output-dir als <Name>_<Spalten>x<Zeilen>[_o].png.",
        dependencies=("Pillow",),
        hint="--optimize entfernt den gemeinsamen vollständig transparenten Außenrand.",
    ),
    "PyImgSplitA.py": ScriptInfo(
        category="sprites",
        icon="🧩",
        description=(
            "Erkennt einzelne Sprites in PNG-Sheets automatisch über den Alphakanal "
            "und exportiert sie in Zeilen- und Spaltenreihenfolge."
        ),
        usage=(
            "python3 PyImgSplitA.py [VERZEICHNIS] [--padding PIXEL] "
            "[--threshold auto|1-254] [--min-area auto|PIXEL]"
        ),
        scope="Alle PNG-Dateien direkt im angegebenen oder aktuellen Ordner.",
        output="Je Quelldatei ein gleichnamiger Ordner mit Einzelbildern und export.json.",
        dependencies=("Pillow", "NumPy", "OpenCV"),
        hint="Alpha-Schwelle und Mindestfläche werden standardmäßig automatisch ermittelt.",
    ),
    "PyImgConvert.py": ScriptInfo(
        category="convert",
        icon="🔄",
        description=(
            "Konvertiert Bilddateien stapelweise zwischen PNG, JPEG, WebP, BMP, "
            "TIFF und ICO."
        ),
        usage=(
            "python3 PyImgConvert.py --png --webp [--all] [--dry-run] "
            "[--outdir ORDNER]"
        ),
        scope="Aktueller Terminalordner; mit --all einschließlich Unterordnern.",
        output="Standardmäßig ein Ordner mit dem Namen des Zielformats.",
        dependencies=("Pillow",),
        hint="Alternativ Quell- und Zielformat mit --from FORMAT --to FORMAT angeben.",
    ),
    "PyImgScal.py": ScriptInfo(
        category="convert",
        icon="📐",
        description=(
            "Skaliert Bilder exakt auf eine Zielgröße und verbessert danach optional "
            "lokalen Kontrast und Schärfe."
        ),
        usage="python3 PyImgScal.py --256 --256 [-c 0-10] [--overwrite]",
        scope="Unterstützte Bilder direkt im aktuellen Terminalordner; keine Unterordner.",
        output="8-Bit-PNGs in einem Zielordner wie _scal_256x256_c3.",
        dependencies=("Python ≥ 3.10", "Pillow ≥ 10.3"),
        hint="Die Zielgröße ist exakt; abweichende Seitenverhältnisse werden verzerrt.",
    ),
    "PyImgHelp.py": ScriptInfo(
        category="help",
        icon="📖",
        description=(
            "Zeigt diese automatisch vervollständigte, farbige Übersicht aller "
            "Python-Skripte im eigenen Ordner."
        ),
        usage="python3 PyImgHelp.py [SKRIPT] [-v | --compact] [--color | --no-color]",
        scope="Alle .py-Dateien direkt im Ordner von PyImgHelp.py.",
        output="Nur Terminalausgabe; keine Dateien werden verändert.",
        hint="Ein Skriptname, auch ohne .py, zeigt gezielt dessen ausführliche Hilfe.",
    ),
}


class Theme:
    """Kleine ANSI-Farbpalette ohne externe Abhängigkeiten."""

    RESET = "\033[0m"

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def paint(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}{self.RESET}"

    def title(self, text: str) -> str:
        return self.paint(text, "1;96")

    def category(self, text: str) -> str:
        return self.paint(text, "1;95")

    def filename(self, text: str) -> str:
        return self.paint(text, "1;93")

    def label(self, text: str) -> str:
        return self.paint(text, "1;36")

    def success(self, text: str) -> str:
        return self.paint(text, "1;92")

    def warning(self, text: str) -> str:
        return self.paint(text, "1;91")

    def muted(self, text: str) -> str:
        return self.paint(text, "2")


def read_docstring(path: Path) -> str:
    """Ersten Docstring-Absatz lesen, ohne das fremde Skript zu importieren."""

    try:
        source = path.read_text(encoding="utf-8-sig", errors="replace")
        docstring = ast.get_docstring(ast.parse(source), clean=True) or ""
    except (OSError, SyntaxError, UnicodeError):
        return ""

    paragraphs = [part.strip() for part in docstring.split("\n\n") if part.strip()]
    if not paragraphs:
        return ""
    return " ".join(paragraphs[0].split())


def fallback_info(path: Path) -> ScriptInfo:
    """Sinnvolle Standardangaben für neu hinzugekommene Python-Dateien."""

    description = read_docstring(path)
    if not description:
        description = "Für dieses Skript ist noch keine Kurzbeschreibung hinterlegt."
    return ScriptInfo(
        category="other",
        icon="🐍",
        description=description,
        usage=f"python3 {shlex.quote(path.name)} [ARGUMENTE]",
        scope="Siehe Hilfe oder Quelltext dieses Skripts.",
        output="Siehe Hilfe oder Quelltext dieses Skripts.",
        hint=(
            "Automatisch aus dem Ordner ergänzt; Angaben bei Bedarf im Katalog "
            "vervollständigen."
        ),
    )


def discover_scripts(folder: Path) -> list[tuple[Path, ScriptInfo]]:
    """Alle Python-Dateien direkt im angegebenen Ordner finden."""

    try:
        paths = [
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.casefold() == ".py"
        ]
    except OSError as exc:
        raise RuntimeError(f"Der Skriptordner kann nicht gelesen werden: {exc}") from exc

    catalog_casefold = {name.casefold(): info for name, info in SCRIPT_CATALOG.items()}
    entries = [
        (path, catalog_casefold.get(path.name.casefold()) or fallback_info(path))
        for path in paths
    ]
    return sorted(
        entries,
        key=lambda item: (
            CATEGORIES.get(item[1].category, CATEGORIES["other"])[0],
            item[0].name.casefold(),
        ),
    )


def stream_supports(stream: TextIO, text: str) -> bool:
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


def colors_enabled(mode: str, stream: TextIO) -> bool:
    """ANSI-Farben anhand von Option, Terminal und Standardvariablen wählen."""

    if mode == "always":
        return True
    if mode == "never":
        return False
    if "NO_COLOR" in os.environ or os.environ.get("TERM", "").casefold() == "dumb":
        return False
    if os.environ.get("FORCE_COLOR", "") not in {"", "0"}:
        return True
    return bool(getattr(stream, "isatty", lambda: False)())


def terminal_width(requested: int | None) -> int:
    columns = requested or shutil.get_terminal_size(fallback=(96, 24)).columns
    return max(44, min(columns, 140))


def symbol(emoji_enabled: bool, emoji: str, plain: str) -> str:
    return emoji if emoji_enabled else plain


def wrapped_lines(text: str, width: int, indent: str = "   ") -> list[str]:
    usable = max(20, width - len(indent))
    lines = textwrap.wrap(
        " ".join(text.split()),
        width=usable,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [""]
    return [f"{indent}{line}" for line in lines]


def print_field(
    label_icon: str,
    label: str,
    value: str,
    *,
    width: int,
    theme: Theme,
    emoji_enabled: bool,
) -> None:
    shown_icon = symbol(emoji_enabled, label_icon, ">")
    plain_prefix = f"   {shown_icon} {label}: "
    continuation = " " * len(plain_prefix)
    value_width = max(20, width - len(plain_prefix))
    parts = textwrap.wrap(
        " ".join(value.split()),
        width=value_width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [""]
    styled_prefix = f"   {shown_icon} {theme.label(label)}: "
    print(styled_prefix + parts[0])
    for part in parts[1:]:
        print(continuation + part)


def print_entry(
    path: Path,
    info: ScriptInfo,
    *,
    width: int,
    theme: Theme,
    emoji_enabled: bool,
    detailed: bool,
) -> None:
    entry_icon = symbol(emoji_enabled, info.icon, "•")
    print(f"{entry_icon} {theme.filename(path.name)}")
    for line in wrapped_lines(info.description, width):
        print(line)
    print_field(
        "▶️", "Aufruf", info.usage,
        width=width, theme=theme, emoji_enabled=emoji_enabled,
    )

    if detailed:
        print_field(
            "📍", "Bereich", info.scope,
            width=width, theme=theme, emoji_enabled=emoji_enabled,
        )
        print_field(
            "💾", "Ausgabe", info.output,
            width=width, theme=theme, emoji_enabled=emoji_enabled,
        )
        dependencies = (
            ", ".join(info.dependencies)
            if info.dependencies
            else "nur Python-Standardbibliothek"
        )
        print_field(
            "📦", "Benötigt", dependencies,
            width=width, theme=theme, emoji_enabled=emoji_enabled,
        )
        if info.hint:
            print_field(
                "💡", "Hinweis", info.hint,
                width=width, theme=theme, emoji_enabled=emoji_enabled,
            )


def print_compact(
    entries: Sequence[tuple[Path, ScriptInfo]],
    *,
    width: int,
    theme: Theme,
    emoji_enabled: bool,
) -> None:
    name_width = min(24, max((len(path.name) for path, _info in entries), default=8))
    for path, info in entries:
        entry_icon = symbol(emoji_enabled, info.icon, "•")
        prefix_length = len(entry_icon) + 1 + name_width + 2
        available = max(12, width - prefix_length)
        description = textwrap.shorten(
            " ".join(info.description.split()),
            width=available,
            placeholder="…",
        )
        padded_name = path.name.ljust(name_width)
        print(f"{entry_icon} {theme.filename(padded_name)}  {description}")


def select_entries(
    entries: Sequence[tuple[Path, ScriptInfo]], query: str | None
) -> list[tuple[Path, ScriptInfo]]:
    if not query:
        return list(entries)

    needle = Path(query).name.casefold()
    needle_stem = needle[:-3] if needle.endswith(".py") else needle
    exact = [
        item
        for item in entries
        if item[0].name.casefold() == needle
        or item[0].stem.casefold() == needle_stem
    ]
    if exact:
        return exact

    partial = [
        item
        for item in entries
        if needle_stem in item[0].stem.casefold()
    ]
    return partial


def suggestions(entries: Sequence[tuple[Path, ScriptInfo]], query: str) -> list[str]:
    names = [path.name for path, _info in entries]
    stem_to_name = {path.stem.casefold(): path.name for path, _info in entries}
    matches = difflib.get_close_matches(
        Path(query).stem.casefold(), list(stem_to_name), n=3, cutoff=0.35
    )
    return [stem_to_name[match] for match in matches] or names[:3]


def print_header(
    folder: Path,
    count: int,
    *,
    width: int,
    theme: Theme,
    emoji_enabled: bool,
    unicode_enabled: bool,
) -> None:
    rule_char = "━" if unicode_enabled else "="
    rule = rule_char * width
    logo = symbol(emoji_enabled, "🎨 ", "")
    folder_icon = symbol(emoji_enabled, "📁 ", "")
    scripts_icon = symbol(emoji_enabled, "🐍 ", "")
    noun = "Python-Skript" if count == 1 else "Python-Skripte"

    print(theme.title(rule))
    print(theme.title(f"{logo}PyImg-Werkzeughilfe"))
    print(theme.muted(f"{folder_icon}{folder}"))
    print(f"{scripts_icon}{theme.success(str(count))} {noun} gefunden")
    print(theme.title(rule))


def print_catalog(
    folder: Path,
    entries: Sequence[tuple[Path, ScriptInfo]],
    *,
    width: int,
    theme: Theme,
    emoji_enabled: bool,
    unicode_enabled: bool,
    compact: bool,
    detailed: bool,
    filtered: bool,
) -> None:
    print_header(
        folder,
        len(entries),
        width=width,
        theme=theme,
        emoji_enabled=emoji_enabled,
        unicode_enabled=unicode_enabled,
    )

    if compact:
        print()
        print_compact(
            entries, width=width, theme=theme, emoji_enabled=emoji_enabled
        )
    else:
        previous_category: str | None = None
        for path, info in entries:
            if info.category != previous_category:
                _order, category_icon, category_name = CATEGORIES.get(
                    info.category, CATEGORIES["other"]
                )
                shown_icon = symbol(emoji_enabled, category_icon, "#")
                separator = "─" if unicode_enabled else "-"
                print()
                print(theme.category(f"{shown_icon} {category_name}"))
                print(theme.muted(separator * min(width, len(category_name) + 8)))
                previous_category = info.category
            elif previous_category is not None:
                print()
            print_entry(
                path,
                info,
                width=width,
                theme=theme,
                emoji_enabled=emoji_enabled,
                detailed=detailed,
            )

    print()
    if filtered:
        note = (
            "Die Originalskripte besitzen zusätzlich ihre eigene --help-Ausgabe, "
            "sofern unterstützt."
        )
        for line in wrapped_lines(note, width, indent=""):
            print(theme.muted(line))
    else:
        help_name = Path(__file__).name
        footer_icon = symbol(emoji_enabled, "💡", "i")
        print(f"{footer_icon} {theme.label('Weitere Ansichten')}")
        print_field(
            "🔎", "Einzelhilfe", f"python3 {help_name} SKRIPT",
            width=width, theme=theme, emoji_enabled=emoji_enabled,
        )
        print_field(
            "📋", "Alle Details", f"python3 {help_name} -v",
            width=width, theme=theme, emoji_enabled=emoji_enabled,
        )
        print_field(
            "⚡", "Kurzliste", f"python3 {help_name} --compact",
            width=width, theme=theme, emoji_enabled=emoji_enabled,
        )
    color_note = "Farben: automatisch im Terminal · --color erzwingt · --no-color deaktiviert"
    for line in wrapped_lines(color_note, width, indent=""):
        print(theme.muted(line))


def width_value(value: str) -> int:
    try:
        width = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("eine ganze Zahl angeben") from exc
    if not 44 <= width <= 140:
        raise argparse.ArgumentTypeError("Breite muss zwischen 44 und 140 liegen")
    return width


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=Path(__file__).stem,
        add_help=False,
        description=(
            "Zeigt eine gut lesbare Kurzhilfe für jede Python-Datei im Ordner "
            "dieses Skripts. Ohne SKRIPT wird die vollständige Übersicht angezeigt."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  python3 PyImgHelp.py\n"
            "  python3 PyImgHelp.py PyImgScal\n"
            "  python3 PyImgHelp.py -v --color\n"
            "  python3 PyImgHelp.py --compact --no-color"
        ),
    )
    parser.add_argument(
        "-h", "--help", action="help",
        help="diese Hilfe anzeigen und beenden",
    )
    parser.add_argument(
        "script",
        nargs="?",
        metavar="SKRIPT",
        help="nur passende Skripte anzeigen; .py darf weggelassen werden",
    )
    view = parser.add_mutually_exclusive_group()
    view.add_argument(
        "-v", "--details", action="store_true",
        help="Bereich, Ausgabe, Abhängigkeiten und Hinweise für alle Skripte anzeigen",
    )
    view.add_argument(
        "--compact", action="store_true",
        help="platzsparende Liste mit einer Zeile pro Skript anzeigen",
    )
    colors = parser.add_mutually_exclusive_group()
    colors.add_argument(
        "--color", dest="color_mode", action="store_const", const="always",
        help="ANSI-Farben auch bei umgeleiteter Ausgabe erzwingen",
    )
    colors.add_argument(
        "--no-color", dest="color_mode", action="store_const", const="never",
        help="ANSI-Farben vollständig deaktivieren",
    )
    parser.set_defaults(color_mode="auto")
    parser.add_argument(
        "--no-emoji", action="store_true",
        help="Emojis durch schlichte Textzeichen ersetzen",
    )
    parser.add_argument(
        "--width", type=width_value, metavar="44-140",
        help="Ausgabebreite festlegen (Standard: aktuelle Terminalbreite)",
    )
    # Kompatibel mit der bisherigen Version, die Deutsch über --de aktivierte.
    parser.add_argument("--de", action="store_true", help=argparse.SUPPRESS)
    parser._positionals.title = "Positionsargumente"
    parser._optionals.title = "Optionen"
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(MENU_HELP)
    folder = Path(__file__).resolve().parent
    theme = Theme(colors_enabled(args.color_mode, sys.stdout))
    unicode_enabled = stream_supports(sys.stdout, "äöüß×≥━─")
    emoji_enabled = not args.no_emoji and stream_supports(sys.stdout, "🎨🐍🧩📁")
    width = terminal_width(args.width)

    try:
        all_entries = discover_scripts(folder)
    except RuntimeError as exc:
        print(theme.warning(f"Fehler: {exc}"), file=sys.stderr)
        return 1

    entries = select_entries(all_entries, args.script)
    if args.script and not entries:
        message = f"Kein Python-Skript passend zu „{args.script}“ gefunden."
        print(theme.warning(message), file=sys.stderr)
        print(
            "Meintest du: " + ", ".join(suggestions(all_entries, args.script)),
            file=sys.stderr,
        )
        return 2

    if not entries:
        print(theme.warning(f"Keine Python-Skripte in {folder} gefunden."))
        return 0

    filtered = args.script is not None
    print_catalog(
        folder,
        entries,
        width=width,
        theme=theme,
        emoji_enabled=emoji_enabled,
        unicode_enabled=unicode_enabled,
        compact=args.compact,
        detailed=args.details or filtered,
        filtered=filtered,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # Beispielsweise bei: PyImgHelp.py | head
        raise SystemExit(0)
