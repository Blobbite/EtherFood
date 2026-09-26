#!/usr/bin/env python3
"""Vorhandene Bildgruppen-Tests nacheinander im aktuellen Ordner ausführen.

Die Tests werden im Ordner dieses Starters gesucht. Reihenfolge:

1. PyImgTestCompare.py – allgemeine technische und visuelle Konsistenz
2. PyImgTestPalette.py – gemeinsame und abweichende Farbpaletten
3. PyImgTestBC.py – Helligkeit und Kontrast
4. PyImgTestColorInt.py – Farbintensität anhand der Originalpixel
5. PyImgTestCentral.py – Fußanker, Mittelachse und Positionssprünge

Nur vorhandene Testskripte werden ausgeführt und angezeigt.

Jeder Test bleibt ein eigenständiges Werkzeug und schreibt seine eigenen,
eindeutig benannten Dateien in ``.compare``. Mit ``--no-report`` wird diese
Option an alle vorhandenen Tests weitergereicht, sodass kein Reportordner verändert
wird. Bei Reports zeigt jeder Einzeltest seinen Vergleich zum vorherigen,
vergleichbaren Lauf. Ein fehlgeschlagener Test verhindert die übrigen
Läufe nicht.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

VERSION = "1.5.0"
PALETTE_COLOR_CHOICES = (64, 48, 32, 24, 20, 16, 12, 8)
DEFAULT_PALETTE_COLOR_LIMIT = 64


@dataclass(frozen=True)
class TestProgram:
    filename: str
    label: str
    emoji: str


TEST_PROGRAMS = (
    TestProgram(
        "PyImgTestCompare.py",
        "Allgemeine Bildkonsistenz",
        "🧩",
    ),
    TestProgram(
        "PyImgTestPalette.py",
        "Farbpaletten",
        "🎨",
    ),
    TestProgram(
        "PyImgTestBC.py",
        "Helligkeit und Kontrast",
        "☀️",
    ),
    TestProgram(
        "PyImgTestColorInt.py",
        "Farbintensität",
        "🌈",
    ),
    TestProgram(
        "PyImgTestCentral.py",
        "Fußanker und Zentrierung",
        "📐",
    ),
)


def available_programs(folder: Path) -> tuple[TestProgram, ...]:
    """Nur vorhandene, reguläre Bildtestskripte berücksichtigen."""
    return tuple(
        program
        for program in TEST_PROGRAMS
        if (folder / program.filename).is_file()
        and not (folder / program.filename).is_symlink()
    )


class Theme:
    RESET = "\033[0m"

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def paint(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}{self.RESET}"


def make_parser() -> argparse.ArgumentParser:
    programs = available_programs(Path(__file__).resolve().parent)
    order = "\n".join(
        f"  {index}. {program.filename}"
        for index, program in enumerate(programs, start=1)
    ) or "  Keine Bildtestskripte vorhanden."
    has_palette = any(
        program.filename == "PyImgTestPalette.py" for program in programs
    )
    palette_help = (
        "\n--palette-colors wird ausschließlich an PyImgTestPalette.py weitergereicht.\n"
        "Erlaubt sind 64, 48, 32, 24, 20, 16, 12 und 8; Standard ist 64.\n"
        if has_palette else ""
    )
    has_central = any(program.filename == "PyImgTestCentral.py" for program in programs)
    parser = argparse.ArgumentParser(
        prog="PyImgTestAll",
        description=(
            "Führt die im Skriptordner vorhandenen Bildtests nacheinander "
            "für die Bilder im aktuellen Terminalordner aus."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""Vorhandene Bildtests in Ausführungsreihenfolge:
{order}

Alle aufgeführten Werkzeuge prüfen dieselben Bilddateien direkt im aktuellen Ordner.
Die Tests bleiben unabhängig voneinander. Ein Fehler wird gesammelt gemeldet;
die nachfolgenden Tests werden trotzdem ausgeführt.

Mit Reports vergleicht jeder Einzeltest sein Ergebnis mit seinem letzten
gültigen Lauf. --no-report deaktiviert diese Verlaufsanzeige vollständig.
{palette_help}

Ohne --no-report legen die Einzeltests ihre zeitgestempelten PNG-, Markdown-
und JSON-Ergebnisse gemeinsam in .compare ab. Mit --no-report bleibt nur die
Terminalausgabe und .compare wird von keinem Test verändert.
""",
    )
    parser.add_argument(
        "--palette-colors",
        type=int,
        choices=PALETTE_COLOR_CHOICES,
        default=DEFAULT_PALETTE_COLOR_LIMIT,
        metavar="{64,48,32,24,20,16,12,8}",
        help=(
            "Maximale Palettengröße für PyImgTestPalette.py (Standard: %(default)s)."
            if has_palette else argparse.SUPPRESS
        ),
    )
    parser.add_argument(
        "--central-grid",
        default=None,
        metavar="SPALTENxZEILEN",
        help="Raster nur für Central (sonst Dateiname oder 1x1)." if has_central else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--central-tolerance",
        type=float,
        default=2.0,
        metavar="PIXEL",
        help="Pixeltoleranz nur für Central (Standard: 2)." if has_central else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--central-pivot",
        metavar="X,Y",
        help="Gemeinsamer Zielanker nur für Central." if has_central else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--central-anchors",
        type=Path,
        metavar="DATEI.json",
        help="Manuelle Quellanker nur für Central." if has_central else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--central-strict",
        action="store_true",
        help="Positionsabweichungen als fehlgeschlagenen Test zählen." if has_central else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="ANSI-Farben in diesem Starter und allen Einzeltests abschalten.",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help=(
            "Bei allen vorhandenen Tests ausschließlich im Terminal ausgeben und "
            "keinen Verlauf laden."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return make_parser().parse_args(argv)


def color_enabled(no_color: bool) -> bool:
    return (
        not no_color
        and sys.stdout.isatty()
        and "NO_COLOR" not in os.environ
        and os.environ.get("TERM", "") != "dumb"
    )


def child_arguments(no_color: bool, no_report: bool) -> list[str]:
    result: list[str] = []
    if no_color:
        result.append("--no-color")
    if no_report:
        result.append("--no-report")
    return result


def run(
    no_color: bool = False,
    no_report: bool = False,
    palette_colors: int = DEFAULT_PALETTE_COLOR_LIMIT,
    central_grid: str | None = None,
    central_tolerance: float = 2.0,
    central_pivot: str | None = None,
    central_anchors: Path | None = None,
    central_strict: bool = False,
) -> int:
    if palette_colors not in PALETTE_COLOR_CHOICES:
        allowed = ", ".join(str(value) for value in PALETTE_COLOR_CHOICES)
        raise ValueError(f"Ungültiges Palettenlimit. Erlaubt sind: {allowed}.")
    if not math.isfinite(central_tolerance) or central_tolerance <= 0:
        raise ValueError("Central-Toleranz muss eine positive, endliche Pixelzahl sein.")
    script_folder = Path(__file__).resolve().parent
    programs = available_programs(script_folder)
    folder = Path.cwd()
    theme = Theme(color_enabled(no_color))
    forwarded = child_arguments(no_color, no_report)
    results: list[tuple[TestProgram, int]] = []

    if not programs:
        print(
            theme.paint(
                f"❌ Keine Bildtestskripte im Skriptordner gefunden: {script_folder}",
                "31",
            ),
            file=sys.stderr,
            flush=True,
        )
        return 1

    print("\n🧪 PyImgTestAll\n", flush=True)
    print(f"📁 Bildordner: {folder.name}", flush=True)
    print(f"🔁 Einzeltests: {len(programs)}\n", flush=True)

    for index, program in enumerate(programs, start=1):
        script = script_folder / program.filename
        program_arguments = list(forwarded)
        if program.filename == "PyImgTestPalette.py":
            program_arguments.extend(["--palette-colors", str(palette_colors)])
        if program.filename == "PyImgTestCentral.py":
            program_arguments.extend(["--tolerance", str(central_tolerance)])
            if central_grid is not None:
                program_arguments.extend(["--grid", central_grid])
            if central_pivot is not None:
                program_arguments.extend(["--pivot", central_pivot])
            if central_anchors is not None:
                program_arguments.extend(["--anchors", str(central_anchors)])
            if central_strict:
                program_arguments.append("--strict")
        print(
            theme.paint(
                f"{program.emoji} Test {index}/{len(programs)}: {program.label}",
                "96",
            ),
            flush=True,
        )
        print(f"   {program.filename}", flush=True)
        if not script.is_file() or script.is_symlink():
            print(
                theme.paint(
                    f"❌ FEHLER: Skript fehlt oder ist ein symbolischer Link: {script}",
                    "31",
                ),
                file=sys.stderr,
                flush=True,
            )
            results.append((program, 1))
            continue
        try:
            completed = subprocess.run(
                [sys.executable, str(script), *program_arguments],
                cwd=folder,
                check=False,
            )
            return_code = completed.returncode
        except OSError as exc:
            print(
                theme.paint(f"❌ Start fehlgeschlagen: {exc}", "31"),
                file=sys.stderr,
                flush=True,
            )
            return_code = 1
        results.append((program, return_code))
        print(flush=True)

    print("🏁 Ergebnis der Testreihe\n", flush=True)
    for program, return_code in results:
        if return_code == 0:
            print(theme.paint(f"✅ {program.label}: abgeschlossen", "32"))
        else:
            print(
                theme.paint(
                    f"❌ {program.label}: Rückgabecode {return_code}",
                    "31",
                )
            )
    failures = sum(return_code != 0 for _program, return_code in results)
    if failures:
        noun = "Test" if failures == 1 else "Tests"
        print(
            theme.paint(
                f"\n❌ Testreihe mit {failures} fehlgeschlagenen {noun} beendet.",
                "31",
            )
        )
        return 1
    noun = "Test" if len(results) == 1 else "Tests"
    print(theme.paint(f"\n💎 {len(results)} {noun} erfolgreich abgeschlossen.", "96"))
    if not no_report:
        print("📄 Gemeinsamer Reportordner: .compare")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        options = parse_arguments(argv)
        return run(
            no_color=options.no_color,
            no_report=options.no_report,
            palette_colors=options.palette_colors,
            central_grid=options.central_grid,
            central_tolerance=options.central_tolerance,
            central_pivot=options.central_pivot,
            central_anchors=options.central_anchors,
            central_strict=options.central_strict,
        )
    except KeyboardInterrupt:
        print("\nAbgebrochen. Quelldateien bleiben unverändert.", file=sys.stderr)
        return 130
    except (OSError, ValueError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
