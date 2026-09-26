#!/usr/bin/env python3
"""PyVram: recursive, header-based VRAM planning for static PNG spritesheets.

Python 3.10+; standard library only. Does not modify images, import textures,
read GPU counters, or infer Godot import settings. Estimates texture payloads,
not driver allocation or total application VRAM. See --help.

Sources:
https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_images.html
https://learn.microsoft.com/en-us/windows/win32/direct3d11/bc7-format
https://learn.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-block-compression
https://www.w3.org/TR/png-3/
"""
from __future__ import annotations

import argparse
import binascii
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import sys
import tempfile
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Callable, TextIO

VERSION = "1.0.0"
MIB = 1024 ** 2
GIB = 1024 ** 3
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
DEFAULT_EXCLUDES = {
    ".compare", ".git", ".godot", ".hg", ".svn", ".venv", "venv",
    "__pycache__", "node_modules",
}
SOURCES = [
    "https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_images.html",
    "https://learn.microsoft.com/en-us/windows/win32/direct3d11/bc7-format",
    "https://learn.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-block-compression",
    "https://www.w3.org/TR/png-3/",
]


@dataclass(frozen=True)
class PNGInfo:
    width: int
    height: int
    bit_depth: int
    color_type: int
    alpha_possible: bool
    disk_bytes: int


@dataclass
class ScanResult:
    candidates: list[Path] = field(default_factory=list)
    directories_visited: int = 0
    matching_directories: list[str] = field(default_factory=list)
    excluded_directories: int = 0
    skipped_symlinks: int = 0
    unmatched_pngs: int = 0
    other_files_in_scope: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)


def clean_text(value: object) -> str:
    """Prevent control characters from file names affecting the terminal."""
    out = []
    for character in str(value):
        if character.isprintable():
            out.append(character)
        else:
            number = ord(character)
            out.append(f"\\x{number:02x}" if number < 256 else f"\\u{number:04x}")
    return "".join(out)


def relative_name(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def normalized_name(name: str) -> str:
    return "".join(character for character in name.casefold() if character.isalnum())


def matches_name(name: str, keywords: list[str]) -> bool:
    normalized = normalized_name(name)
    return any(keyword in normalized for keyword in keywords)


def scan_files(
    root: Path, keywords: list[str], all_png: bool, excludes: set[str],
    progress: Callable[[int, int], None] | None = None,
) -> ScanResult:
    """Traverse once; inherit matching folder scope; never follow symlinks."""
    result = ScanResult()
    stack: list[tuple[Path, bool]] = [(root, False)]
    while stack:
        directory, inherited_scope = stack.pop()
        own_match = matches_name(directory.name, keywords)
        in_scope = all_png or inherited_scope or own_match
        result.directories_visited += 1
        if own_match:
            result.matching_directories.append(relative_name(directory, root))
        child_directories = []
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    try:
                        if entry.is_symlink():
                            result.skipped_symlinks += 1
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name.casefold() in excludes:
                                result.excluded_directories += 1
                            else:
                                child_directories.append((path, in_scope))
                        elif entry.is_file(follow_symlinks=False):
                            if path.suffix.casefold() == ".png":
                                if in_scope or matches_name(path.stem, keywords):
                                    result.candidates.append(path)
                                else:
                                    result.unmatched_pngs += 1
                            elif in_scope:
                                result.other_files_in_scope += 1
                    except OSError as exc:
                        result.errors.append({"path": relative_name(path, root), "error": str(exc)})
        except OSError as exc:
            result.errors.append({"path": relative_name(directory, root), "error": str(exc)})
        # One branch per path prevents nested spritesheet folders being counted twice.
        stack.extend(sorted(child_directories, key=lambda item: str(item[0]).casefold(), reverse=True))
        if progress:
            progress(result.directories_visited, len(result.candidates))
    result.candidates.sort(key=lambda path: relative_name(path, root).casefold())
    result.matching_directories.sort(key=str.casefold)
    return result


def read_png_info(path: Path) -> PNGInfo:
    """Read IHDR and pre-IDAT metadata, never decompress the image pixels.

    IHDR CRC, basic fields, and chunk bounds are checked. This is deliberately
    NOT a full image integrity test. APNG is rejected to avoid undercounting it.
    On platforms providing O_NOFOLLOW, reject newly introduced symlinks too.
    """
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as handle:
        file_stat = os.fstat(handle.fileno())
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("Keine reguläre Datei.")
        header = handle.read(33)
        if len(header) != 33 or header[:8] != PNG_SIGNATURE:
            raise ValueError("Keine gültige PNG-Signatur oder unvollständiger PNG-Header.")
        length, chunk_type = struct.unpack(">I4s", header[8:16])
        if length != 13 or chunk_type != b"IHDR":
            raise ValueError("IHDR fehlt oder hat eine ungültige Länge.")
        expected_crc = struct.unpack(">I", header[29:33])[0]
        if (binascii.crc32(header[12:29]) & 0xFFFFFFFF) != expected_crc:
            raise ValueError("Die IHDR-Prüfsumme ist falsch.")
        width, height, depth, kind, compression, filtering, interlace = struct.unpack(">IIBBBBB", header[16:29])
        allowed_depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
        if not (1 <= width <= 2**31 - 1 and 1 <= height <= 2**31 - 1):
            raise ValueError("Ungültige PNG-Abmessungen.")
        if depth not in allowed_depths.get(kind, set()):
            raise ValueError("Ungültige PNG-Farbtiefe oder ungültiger Farbtyp.")
        if compression != 0 or filtering != 0 or interlace not in (0, 1):
            raise ValueError("Ungültige PNG-Kompressions-, Filter- oder Interlace-Methode.")
        alpha = kind in (4, 6)
        while True:
            chunk_header = handle.read(8)
            if len(chunk_header) != 8:
                raise ValueError("PNG enthält keinen lesbaren IDAT-Bilddatenblock.")
            chunk_size, chunk_type = struct.unpack(">I4s", chunk_header)
            if chunk_size > 2**31 - 1 or handle.tell() + chunk_size + 4 > file_stat.st_size:
                raise ValueError("PNG-Block endet außerhalb der Datei.")
            if chunk_type == b"acTL":
                raise ValueError("APNG erkannt: Animation statt statischem Spritesheet; nicht mitgerechnet.")
            if chunk_type == b"tRNS":
                alpha = True
            if chunk_type == b"IDAT":
                return PNGInfo(width, height, depth, kind, alpha, file_stat.st_size)
            if chunk_type in (b"IEND", b"IHDR"):
                raise ValueError("Unerwarteter PNG-Block vor den Bilddaten.")
            handle.seek(chunk_size + 4, os.SEEK_CUR)


def texture_bytes(width: int, height: int, texture_format: str = "rgba8", mipmaps: bool = False) -> int:
    """Texture data payload, including block rounding separately at each mip."""
    if width < 1 or height < 1:
        raise ValueError("Texture dimensions must be positive.")
    if texture_format not in {"rgba8", "bc1", "bc3", "bc7"}:
        raise ValueError("Unknown texture format.")
    total = 0
    while True:
        if texture_format == "rgba8":
            total += width * height * 4
        else:
            bytes_per_block = 8 if texture_format == "bc1" else 16
            total += ((width + 3) // 4) * ((height + 3) // 4) * bytes_per_block
        if not mipmaps or (width == 1 and height == 1):
            return total
        width, height = max(1, width // 2), max(1, height // 2)


def scaled_dimension(value: int, factor: float) -> int:
    return max(1, math.floor(value * factor + 0.5))


def metrics(width: int, height: int) -> dict[str, int]:
    return {
        "rgba8": texture_bytes(width, height),
        "rgba8_mipmaps": texture_bytes(width, height, "rgba8", True),
        "bc3_bc7": texture_bytes(width, height, "bc7"),
        "bc3_bc7_mipmaps": texture_bytes(width, height, "bc7", True),
        "bc1": texture_bytes(width, height, "bc1"),
        "bc1_mipmaps": texture_bytes(width, height, "bc1", True),
    }


def chosen_metric(texture_format: str, mipmaps: bool) -> str:
    key = "bc3_bc7" if texture_format in {"bc3", "bc7"} else texture_format
    return key + ("_mipmaps" if mipmaps else "")


def human_bytes(value: int) -> str:
    sign = "-" if value < 0 else ""
    number = abs(value)
    if number < 1024:
        return f"{sign}{number} B"
    for unit, divisor in (("TiB", 1024**4), ("GiB", GIB), ("MiB", MIB), ("KiB", 1024)):
        if number >= divisor:
            return f"{sign}{number / divisor:.2f} {unit}"
    raise AssertionError("unreachable")


def load_status(percent: float) -> tuple[str, str, str]:
    if percent > 100:
        return "ÜBER BUDGET", "red", "🔴"
    if percent >= 90:
        return "KNAPP", "red", "🔴"
    if percent >= 70:
        return "BEACHTEN", "yellow", "🟡"
    return "IM BUDGET", "green", "🟢"


class Terminal:
    def __init__(self, stream: TextIO, color: str = "auto", ascii_only: bool = False):
        self.stream = stream
        self.color = color == "always" or (
            color == "auto" and stream.isatty() and "NO_COLOR" not in os.environ
            and os.environ.get("TERM") != "dumb"
        )
        encoding = stream.encoding or "utf-8"
        try:
            "🧮█░".encode(encoding)
            unicode_supported = True
        except (UnicodeError, LookupError):
            unicode_supported = False
        self.ascii = ascii_only or not unicode_supported

    def paint(self, text: str, color: str) -> str:
        codes = {"green": "32", "yellow": "33", "red": "31", "cyan": "36", "bold": "1"}
        return f"\033[{codes[color]}m{text}\033[0m" if self.color else text

    def icon(self, text: str, fallback: str = "*") -> str:
        return fallback if self.ascii else text

    def bar(self, percent: float, width: int = 20, color: str | None = None) -> str:
        fill = min(width, max(0, math.floor(min(100.0, max(0.0, percent)) / 100 * width + 0.5)))
        full, empty = ("#", "-") if self.ascii else ("█", "░")
        result = f"[{full * fill}{empty * (width - fill)}]"
        return self.paint(result, color or load_status(percent)[1])

    def line(self, text: str = "") -> None:
        if self.ascii:
            text = text.translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}))
            text = unicodedata.normalize("NFKD", text).encode("ascii", "backslashreplace").decode("ascii")
        self.stream.write(text + "\n")


class Progress:
    def __init__(self, terminal: Terminal, disabled: bool):
        self.terminal = terminal
        self.enabled = terminal.stream.isatty() and not disabled
        self.last_update = 0.0
        self.active = False

    def update(self, message: str, force: bool = False) -> None:
        now = time.monotonic()
        if not self.enabled or (not force and now - self.last_update < 0.12):
            return
        self.last_update = now
        self.active = True
        width = max(20, shutil.get_terminal_size((100, 24)).columns - 1)
        self.terminal.stream.write("\r" + message[:width].ljust(width))
        self.terminal.stream.flush()

    def scan(self, directories: int, candidates: int) -> None:
        self.update(f"Suche: {directories} Ordner | {candidates} passende PNG-Dateien")

    def analyze(self, done: int, total: int) -> None:
        percent = 100 * done / total if total else 100.0
        # No ANSI in this line: truncation must not cut an escape sequence.
        fill = min(20, round(percent / 5))
        full, empty = ("#", "-") if self.terminal.ascii else ("█", "░")
        self.update(f"Analyse [{full * fill}{empty * (20 - fill)}] {percent:5.1f}% | {done}/{total}", done == total)

    def finish(self) -> None:
        if self.active:
            self.terminal.stream.write("\n")
            self.terminal.stream.flush()
        self.active = False


def build_report(root: Path, args: argparse.Namespace, scan: ScanResult, progress: Progress) -> dict:
    files = []
    failures = list(scan.errors)
    totals = dict.fromkeys(metrics(1, 1), 0)
    folders: dict[str, dict] = {}
    source_selected_bytes = 0
    disk_bytes = 0
    selected_key = chosen_metric(args.texture_format, args.mipmaps)
    for index, path in enumerate(scan.candidates, 1):
        try:
            info = read_png_info(path)
            width = scaled_dimension(info.width, args.scale)
            height = scaled_dimension(info.height, args.scale)
            sizes = metrics(width, height)
            source_size = texture_bytes(info.width, info.height, args.texture_format, args.mipmaps)
            selected_size = sizes[selected_key]
            folder_name = relative_name(path.parent, root)
            record = {
                "path": relative_name(path, root), "folder": folder_name,
                "source_width": info.width, "source_height": info.height,
                "estimated_width": width, "estimated_height": height,
                "source_bit_depth": info.bit_depth, "source_color_type": info.color_type,
                "source_alpha_possible": info.alpha_possible,
                "disk_bytes": info.disk_bytes, "scenario_bytes": sizes,
                "selected_bytes": selected_size, "source_selected_bytes": source_size,
                "over_dimension_threshold": max(width, height) > args.max_texture_size,
            }
            files.append(record)
            disk_bytes += info.disk_bytes
            source_selected_bytes += source_size
            for key in totals:
                totals[key] += sizes[key]
            folder = folders.setdefault(folder_name, {"path": folder_name, "file_count": 0, "disk_bytes": 0, "selected_bytes": 0})
            folder["file_count"] += 1
            folder["disk_bytes"] += info.disk_bytes
            folder["selected_bytes"] += selected_size
        except (OSError, ValueError, struct.error) as exc:
            failures.append({"path": relative_name(path, root), "error": str(exc)})
        finally:
            progress.analyze(index, len(scan.candidates))
    progress.finish()
    selected_bytes = totals[selected_key]
    budget_bytes, reserve_bytes = round(args.budget * GIB), round(args.reserve * GIB)
    planned_bytes = selected_bytes + reserve_bytes
    percent = planned_bytes / budget_bytes * 100
    state = "KEINE DATEN" if not files else load_status(percent)[0]
    notes = [
        "Schätzung der Textur-Nutzdaten, keine Messung der Grafikkarte und keine vollständige Godot-Speicherbilanz.",
        "Annahme: Alle erfolgreich erfassten PNG-Dateien werden gleichzeitig als separate Texturen geladen, jeweils einmal pro Dateipfad.",
        "Spritesheets werden nach Ordner-/Dateinamen erkannt, nicht anhand des Bildinhalts. Nur statische PNG-Dateien werden ausgewertet.",
        "Die eingestellte RGBA8- oder BC-Variante gilt einheitlich für alle Dateien. Godot-Importdateien und tatsächliche GPU-Formate werden nicht ausgelesen.",
        "PNG-Dateigröße ist getrennt von VRAM. Transparente Flächen und leere Rasterfelder zählen zur vollständigen Texturfläche.",
        "Die Frames sind bereits in den Sheet-Abmessungen enthalten: keine zusätzliche Multiplikation mit Frames, Richtungen, FPS oder NPC-Instanzen.",
        "RGBA8 rechnet mit 4 Byte pro Pixel, auch bei RGB-, Graustufen-, Paletten- oder 16-Bit-PNGs. Der echte Import kann abweichen.",
        "BC3/BC7: 16 Byte je 4x4-Block; BC1: 8 Byte je 4x4-Block. Jeder Mipmap-Level wird separat auf ganze Blöcke aufgerundet.",
        "BC1 unterstützt keinen weichen Alphaverlauf. GPU-Kompression kann Pixel-Art-Artefakte erzeugen; Formatunterstützung hängt von Zielgerät und Renderer ab.",
        "Mipmaps werden als vollständige Kette bis 1x1 berechnet. Keine automatische Mipmap-Aktivierung oder Größenanpassung in Godot.",
        "Treiber-Alignment, Render-Targets, Fenster/Editor, sonstige Assets, andere Programme und Lade-Spitzen sind nicht enthalten. --reserve ist nur ein selbst gewählter Zuschlag.",
        "Kleinere Darstellung im Spiel spart nicht automatisch Texturspeicher. --scale simuliert kleinere importierte Texturabmessungen und verändert keine Datei.",
        "Identische Dateikopien und Hardlinks unter verschiedenen Pfaden zählen separat; gemeinsame Textur-Nutzung mehrerer Spielobjekte wird nicht vervielfacht.",
        "PNG-Header, IHDR-Prüfsumme und Metadaten vor IDAT werden geprüft, nicht die vollständigen Bilddaten. APNG wird als nicht unterstützt gemeldet.",
        "Budget-Ampel ist eine Planungshilfe: unter 70% grün, ab 70% gelb, ab 90% rot, über 100% über Budget. Kein Leistungstest.",
        "Das Standardbudget von 4 GiB und die Dimensions-Warnschwelle sind Vergleichswerte, keine erkannten Hardwaredaten oder Mindestanforderungen.",
        "1 MiB = 1048576 Byte; 1 GiB = 1073741824 Byte. Report-Dateien desselben Namens werden bei weiteren Läufen ersetzt.",
    ]
    warnings = []
    if failures:
        warnings.append(f"UNVOLLSTÄNDIG: {len(failures)} Lese-/Formatfehler; nicht lesbare Inhalte fehlen in den Summen.")
    if not files:
        warnings.append("Keine auswertbaren PNG-Spritesheets gefunden. Ordnernamen prüfen oder --all-png verwenden.")
    over_limit = sum(record["over_dimension_threshold"] for record in files)
    if over_limit:
        warnings.append(f"{over_limit} Textur(en) überschreiten die konfigurierte Kanten-Warnschwelle von {args.max_texture_size} px. Zielgerät prüfen; dies erkennt keine GPU-Grenze.")
    if args.texture_format == "bc1":
        warnings.append("BC1 ist kein geeignetes Szenario für weiche Transparenz. Das Skript untersucht dafür nicht jeden Pixel.")
    if args.reserve >= args.budget:
        warnings.append("Die gewählte Reserve belegt bereits das gesamte Budget oder mehr.")
    if args.scale != 1:
        warnings.append("Skalierung ist nur simuliert: Sheet-Raster und Frame-Rechtecke müssen bei einer tatsächlichen Skalierung passend angepasst werden.")
    if scan.other_files_in_scope:
        warnings.append(f"{scan.other_files_in_scope} andere Datei(en) im passenden Ordnerbereich nicht berechnet; z. B. Metadaten oder Nicht-PNG-Texturen.")
    return {
        "schema_version": 1, "tool": "PyVram", "tool_version": VERSION,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": str(root), "status": state, "complete": not failures and bool(files),
        "settings": {
            "format": args.texture_format, "mipmaps": args.mipmaps, "scale": args.scale,
            "budget_gib": args.budget, "reserve_gib": args.reserve,
            "budget_bytes": budget_bytes, "reserve_bytes": reserve_bytes,
            "all_png": args.all_png, "name_keywords": ["spritesheet"] + (args.match or []),
            "excluded_directory_names": sorted(DEFAULT_EXCLUDES | {name.casefold() for name in args.exclude}),
            "max_texture_size_warning": args.max_texture_size, "top_terminal": args.top,
        },
        "scan": {
            "directories_visited": scan.directories_visited,
            "matching_directories": scan.matching_directories,
            "candidate_files": len(scan.candidates), "valid_files": len(files),
            "error_count": len(failures), "excluded_directories": scan.excluded_directories,
            "skipped_symlinks": scan.skipped_symlinks, "unmatched_pngs": scan.unmatched_pngs,
            "other_files_in_scope": scan.other_files_in_scope,
        },
        "totals": {
            "disk_bytes": disk_bytes, "scenario_bytes": totals,
            "selected_texture_bytes": selected_bytes,
            "source_selected_texture_bytes": source_selected_bytes,
            "planned_bytes_with_reserve": planned_bytes,
            "budget_used_percent": percent, "budget_remaining_bytes": budget_bytes - planned_bytes,
        },
        "folders": sorted(folders.values(), key=lambda row: (-row["selected_bytes"], row["path"])),
        "files": sorted(files, key=lambda row: (-row["selected_bytes"], row["path"])),
        "warnings": warnings, "errors": failures, "assumptions": notes, "sources": SOURCES,
    }


def render_summary(report: dict, terminal: Terminal, top: int = 10) -> None:
    settings, totals, scan = report["settings"], report["totals"], report["scan"]
    budget = settings["budget_bytes"]
    selected = totals["selected_texture_bytes"]
    percent = totals["budget_used_percent"]
    terminal.line(terminal.paint(f"{terminal.icon('🧮')} PyVram {VERSION} | VRAM-SCHÄTZUNG", "bold"))
    terminal.line("=" * 66)
    terminal.line(f"{terminal.icon('📁')} Startordner: {clean_text(report['root'])}")
    terminal.line(f"{terminal.icon('🔎')} Rekursiv: {scan['directories_visited']} Ordner | {scan['valid_files']}/{scan['candidate_files']} PNGs ausgewertet")
    terminal.line(f"   Namensfilter: {'alle PNGs' if settings['all_png'] else ', '.join(clean_text(x) for x in settings['name_keywords'])}")
    terminal.line(f"   Übersprungen: {scan['excluded_directories']} ausgeschlossene Ordner, {scan['skipped_symlinks']} Links, {scan['unmatched_pngs']} PNGs außerhalb des Filters")
    terminal.line(f"{terminal.icon('💾')} PNG-Dateigrößen: {human_bytes(totals['disk_bytes'])}  (NICHT der VRAM)")
    terminal.line(f"{terminal.icon('🎮')} Modell: {settings['format'].upper()} | Mipmaps {'an' if settings['mipmaps'] else 'aus'} | Skalierung {settings['scale']:g}x")
    terminal.line("   Alle erfassten Texturen gleichzeitig geladen; jede Datei einmal.")
    terminal.line()
    terminal.line(terminal.paint("BUDGET-TEST", "bold"))
    terminal.line(f"   Texturen:       {human_bytes(selected)}")
    terminal.line(f"   Eigene Reserve: {human_bytes(settings['reserve_bytes'])}")
    terminal.line(f"   Geplant:        {human_bytes(totals['planned_bytes_with_reserve'])} / {human_bytes(budget)}")
    state, color, icon = load_status(percent)
    if not scan["valid_files"]:
        state, color, icon = "KEINE DATEN", "yellow", "⚠️"
    elif not report["complete"]:
        state, color, icon = "UNVOLLSTÄNDIG - " + state, "yellow", "⚠️"
    terminal.line(f"   {terminal.bar(percent, color=color)} {percent:6.1f}% {terminal.icon(icon, '!')} {terminal.paint(state, color)}")
    remaining = totals["budget_remaining_bytes"]
    terminal.line(f"   {'Verbleibend' if remaining >= 0 else 'Über Budget'}: {human_bytes(abs(remaining))}")
    terminal.line("   Ampel: <70% grün | 70-<90% gelb | ab 90% rot.")
    terminal.line()
    terminal.line(terminal.paint("TEXTUR-SZENARIEN (ohne Reserve; Balken relativ zum Budget)", "bold"))
    scenarios = [
        ("RGBA8, ohne Mipmaps", "rgba8"), ("RGBA8, mit Mipmaps", "rgba8_mipmaps"),
        ("BC3/BC7, ohne Mipmaps", "bc3_bc7"), ("BC3/BC7, mit Mipmaps", "bc3_bc7_mipmaps"),
    ]
    if settings["format"] == "bc1":
        scenarios.extend([("BC1, ohne Mipmaps", "bc1"), ("BC1, mit Mipmaps", "bc1_mipmaps")])
    for title, key in scenarios:
        value = totals["scenario_bytes"][key]
        ratio = value / budget * 100
        terminal.line(f"   {title:<24} {human_bytes(value):>12}  {terminal.bar(ratio)} {ratio:6.1f}%")
    if settings["scale"] != 1:
        source = totals["source_selected_texture_bytes"]
        delta = source - selected
        terminal.line(f"   Modell vor Skalierung: {human_bytes(source)} | {'Ersparnis' if delta >= 0 else 'Mehrbedarf'}: {human_bytes(abs(delta))}")
    terminal.line()
    folder_rows = report["folders"] if top == 0 else report["folders"][:top]
    terminal.line(terminal.paint(f"{terminal.icon('📂')} ORDNER ({len(folder_rows)} von {len(report['folders'])}; nach Speicher)", "bold"))
    for folder in folder_rows:
        share = folder["selected_bytes"] / selected * 100 if selected else 0
        terminal.line(f"   {terminal.bar(share, color='cyan')} {human_bytes(folder['selected_bytes']):>12} | {folder['file_count']} PNG | {share:5.1f}% Anteil")
        terminal.line(f"      {clean_text(folder['path'])}")
    file_rows = report["files"] if top == 0 else report["files"][:top]
    terminal.line()
    terminal.line(terminal.paint(f"{terminal.icon('🖼️')} GRÖSSTE TEXTUREN ({len(file_rows)} von {len(report['files'])})", "bold"))
    for record in file_rows:
        share = record["selected_bytes"] / selected * 100 if selected else 0
        terminal.line(f"   {terminal.bar(share, color='cyan')} {human_bytes(record['selected_bytes']):>12} | {record['estimated_width']}x{record['estimated_height']} px")
        terminal.line(f"      {clean_text(record['path'])}")
    if top and (len(report["files"]) > top or len(report["folders"]) > top):
        terminal.line("   Alle Einträge stehen im Bericht. --top 0 zeigt alle im Terminal.")
    if report["warnings"]:
        terminal.line()
        terminal.line(terminal.paint(f"{terminal.icon('⚠️', '!')} HINWEISE", "yellow"))
        for warning in report["warnings"]:
            terminal.line("   " + clean_text(warning))
    if report["errors"]:
        terminal.line()
        terminal.line(terminal.paint("LESE-/FORMATFEHLER", "red"))
        for error in report["errors"][:10]:
            terminal.line(f"   {clean_text(error['path'])}: {clean_text(error['error'])}")
        if len(report["errors"]) > 10:
            terminal.line(f"   Weitere {len(report['errors']) - 10} Fehler im Bericht.")
    terminal.line()
    terminal.line(f"{terminal.icon('ℹ️', 'i')} Nur Textur-Nutzdaten. Keine Live-Messung; keine automatische Godot-Importanalyse.")
    terminal.line("   Transparente/leere Flächen zählen mit. Frames/FPS nicht erneut multiplizieren.")
    terminal.line("   GPU-Kompression ist nur ein Szenario und kann die Bildqualität verändern.")
    terminal.line("   Reserve und Budget sind selbst gewählte Planwerte; sonstiger VRAM fehlt ohne Reserve.")
    terminal.line("   Nur PNG-Header geprüft; Bilddaten werden nicht vollständig validiert.")


def markdown_cell(value: object) -> str:
    return clean_text(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("`", "&#96;")


def markdown_report(report: dict) -> str:
    from io import StringIO
    buffer = StringIO()
    render_summary(report, Terminal(buffer, "never"), top=10)
    # All file/folder records are also provided below, not limited by --top.
    lines = ["# PyVram – VRAM-Schätzung", "", f"Erstellt: {report['created_at']}", "", "## Zusammenfassung", "", "```text", buffer.getvalue().replace("```", "'''"), "```", "", "## Alle Ordner", "", "| Ordner | PNGs | PNG-Dateigrößen | Modell-VRAM |", "|---|---:|---:|---:|"]
    for row in report["folders"]:
        lines.append(f"| {markdown_cell(row['path'])} | {row['file_count']} | {human_bytes(row['disk_bytes'])} | {human_bytes(row['selected_bytes'])} |")
    lines.extend(["", "## Alle Texturen", "", "| Datei | Quelle px | Modell px | PNG-Dateigröße | RGBA8 | RGBA8 + Mips | BC3/BC7 | BC3/BC7 + Mips | Gewähltes Modell |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|",])
    for row in report["files"]:
        sizes = row["scenario_bytes"]
        lines.append(f"| {markdown_cell(row['path'])} | {row['source_width']}x{row['source_height']} | {row['estimated_width']}x{row['estimated_height']} | {human_bytes(row['disk_bytes'])} | {human_bytes(sizes['rgba8'])} | {human_bytes(sizes['rgba8_mipmaps'])} | {human_bytes(sizes['bc3_bc7'])} | {human_bytes(sizes['bc3_bc7_mipmaps'])} | {human_bytes(row['selected_bytes'])} |")
    if report["errors"]:
        lines.extend(["", "## Nicht berechnete Dateien / Lesefehler", "", "| Pfad | Fehler |", "|---|---|"])
        lines.extend(f"| {markdown_cell(error['path'])} | {markdown_cell(error['error'])} |" for error in report["errors"])
    lines.extend(["", "## Annahmen und Grenzen", ""])
    lines.extend(f"- {note}" for note in report["assumptions"])
    lines.extend(["", "## Technische Quellen", ""])
    lines.extend(f"- <{source}>" for source in report["sources"])
    return "\n".join(lines) + "\n"


def write_atomic(destination: Path, content: str) -> None:
    """Replace this tool's report only; avoid partial files and symlink targets."""
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", errors="backslashreplace", newline="\n", dir=destination.parent, prefix=".pyvram-", suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            handle.write(content)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def save_reports(root: Path, report: dict) -> list[Path]:
    from io import StringIO
    destination = root / ".compare"
    if destination.is_symlink():
        raise OSError(".compare ist ein symbolischer Link; Bericht wird dort nicht gespeichert.")
    destination.mkdir(exist_ok=True)
    plain = StringIO()
    render_summary(report, Terminal(plain, "never"), top=0)
    plain.write("\nANNAHMEN UND GRENZEN\n")
    for note in report["assumptions"]:
        plain.write("- " + note + "\n")
    if report["errors"]:
        plain.write("\nALLE FEHLER\n")
        for error in report["errors"]:
            plain.write(f"- {clean_text(error['path'])}: {clean_text(error['error'])}\n")
    plain.write("\nQUELLEN\n" + "\n".join(report["sources"]) + "\n")
    content = {
        "vram_report.txt": plain.getvalue(),
        "vram_report.md": markdown_report(report),
        "vram_report.json": json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + "\n",
    }
    paths = []
    for name, data in content.items():
        path = destination / name
        write_atomic(path, data)
        paths.append(path)
    return paths


def finite_number(value: str) -> float:
    try:
        number = float(value.replace(",", "."))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Bitte eine Zahl angeben, z. B. 4 oder 0.5.") from exc
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("Die Zahl muss endlich sein.")
    return number


def positive_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Bitte eine ganze Zahl angeben.") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("Die Zahl muss mindestens 1 sein.")
    return number


def parser_for_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="VRAM-Schätzung für PNG-Spritesheets: rekursiv ab aktuellem Terminal-Ordner; ohne Zusatzpakete.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Namenssuche:
  Standard: PNGs in Ordnern mit 'spritesheet' im Namen, inklusive
  Unterordnern; zusätzlich PNGs mit 'spritesheet' im Dateinamen.
  Groß-/Kleinschreibung, Bindestriche und Unterstriche sind egal.
  Beispiele: spritesheets, _sprite_sheet, HD-SpriteSheets.
  Nur die Namen werden erkannt, nicht der Bildinhalt.

Beispiele:
  PyVram
  PyVram --budget 4 --reserve 0.5
  PyVram --no-report
  PyVram --all-png --scale 0.5 --mipmaps
  PyVram --format bc7 --budget 8
  PyVram --match atlas --exclude masters
  PyVram --top 0 --no-color

Berichte: .compare/vram_report.txt, .md und .json im Startordner.
--no-report legt nichts an und verändert keine vorhandenen Berichte.
Gleichnamige Berichte werden sonst ersetzt; PNG-Dateien bleiben unberührt.
RGBA8 ist ein Rechenmodell, keine Erkennung des tatsächlichen GPU-Formats.
Rückgabecodes: 0=ausgewertet, 1=unvollständig/Schreibfehler,
              2=Aufruffehler/keine Daten, 130=abgebrochen.
Ein überschrittenes VRAM-Budget allein ist kein Programmfehler.
""",
    )
    parser.add_argument("path", nargs="?", default=".", help="Optionaler Startordner (Standard: aktueller Arbeitsordner, nicht Skriptordner).")
    parser.add_argument("--budget", "--vram", type=finite_number, default=4.0, metavar="GiB", help="Vergleichsbudget in GiB (Standard: 4; keine Hardwareerkennung).")
    parser.add_argument("--reserve", type=finite_number, default=0.0, metavar="GiB", help="Selbst gewählter Zuschlag für sonstigen VRAM (Standard: 0).")
    parser.add_argument("--format", "--compression", dest="texture_format", choices=("rgba8", "bc7", "bc3", "bc1"), default="rgba8", help="Einheitliches GPU-Rechenmodell (Standard: rgba8).")
    parser.add_argument("--mipmaps", action="store_true", help="Vollständige Mipmap-Kette im gewählten Modell mitrechnen.")
    parser.add_argument("--scale", type=finite_number, default=1.0, metavar="FAKTOR", help="Import-Skalierung nur simulieren; 0.5 halbiert beide Kanten (Standard: 1).")
    parser.add_argument("--all-png", action="store_true", help="Alle PNGs rekursiv berechnen, auch außerhalb von Spritesheet-Ordnern.")
    parser.add_argument("--match", action="append", metavar="TEXT", help="Zusätzlicher Suchbegriff für Ordner-/Dateinamen; mehrfach nutzbar.")
    parser.add_argument("--exclude", action="append", default=[], metavar="ORDNERNAME", help="Zusätzlichen Ordnernamen überall ausschließen; mehrfach nutzbar.")
    parser.add_argument("--top", type=int, default=10, metavar="N", help="Größte N Ordner und Dateien im Terminal; 0=alle (Standard: 10). Berichte enthalten immer alle.")
    parser.add_argument("--max-texture-size", type=positive_integer, default=16384, metavar="PX", help="Konfigurierbare Kanten-Warnschwelle (Standard: 16384, kein erkanntes GPU-Limit).")
    parser.add_argument("--no-report", action="store_true", help="Keine Berichte schreiben und keinen .compare-Ordner anlegen.")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto", help="ANSI-Farben (Standard: auto; beachtet NO_COLOR).")
    parser.add_argument("--no-color", dest="color", action="store_const", const="never", help="ANSI-Farben ausschalten.")
    parser.add_argument("--ascii", action="store_true", help="ASCII-Ausgabe statt Emojis und Unicode-Balken.")
    parser.add_argument("--no-progress", action="store_true", help="Live-Fortschritt ausschalten; Ergebnisbalken bleiben sichtbar.")
    parser.add_argument("--version", action="version", version=f"PyVram {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = parser_for_cli()
    args = parser.parse_args(argv)
    # Upper bounds also keep all floating-point-to-byte conversions finite.
    if not (1 / GIB <= args.budget <= 1048576):
        parser.error("--budget muss mindestens 1 Byte und höchstens 1048576 GiB sein.")
    if not (0 <= args.reserve <= 1048576):
        parser.error("--reserve muss zwischen 0 und 1048576 GiB liegen.")
    if not (0 < args.scale <= 16):
        parser.error("--scale muss größer als 0 und höchstens 16 sein.")
    if args.top < 0:
        parser.error("--top muss mindestens 0 sein.")
    if any(not normalized_name(keyword) for keyword in (args.match or [])):
        parser.error("--match muss mindestens einen Buchstaben oder eine Ziffer enthalten.")
    if any(not name or name in {".", ".."} or "/" in name or "\\" in name for name in args.exclude):
        parser.error("--exclude erwartet einen Ordnernamen, keinen Pfad.")
    try:
        root = Path(args.path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        parser.error(f"Startordner kann nicht geöffnet werden: {exc}")
    if not root.is_dir():
        parser.error("Der Startpfad muss ein Ordner sein.")
    terminal = Terminal(sys.stdout, args.color, args.ascii)
    progress = Progress(Terminal(sys.stderr, args.color, args.ascii), args.no_progress)
    keywords = [normalized_name(name) for name in ["spritesheet"] + (args.match or [])]
    excludes = DEFAULT_EXCLUDES | {name.casefold() for name in args.exclude}
    try:
        scan = scan_files(root, keywords, args.all_png, excludes, progress.scan)
        report = build_report(root, args, scan, progress)
    finally:
        progress.finish()
    render_summary(report, terminal, top=args.top)
    terminal.line()
    report_failed = False
    if args.no_report:
        terminal.line(f"{terminal.icon('🚫', '-')} --no-report: Keine Berichte geschrieben; .compare bleibt unverändert.")
    else:
        try:
            paths = save_reports(root, report)
            terminal.line(f"{terminal.icon('📝')} Berichte gespeichert (vorhandene gleichnamige Berichte ersetzt):")
            for path in paths:
                terminal.line("   " + clean_text(relative_name(path, root)))
        except (OSError, ValueError) as exc:
            report_failed = True
            terminal.line(terminal.paint(f"{terminal.icon('⚠️', '!')} Bericht konnte nicht vollständig gespeichert werden: {clean_text(exc)}", "red"))
    if report_failed or report["errors"]:
        return 1
    return 0 if report["files"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nAbgebrochen. PNG-Dateien wurden nicht verändert.", file=sys.stderr)
        raise SystemExit(130)
    except BrokenPipeError:
        # A closed pager/pipe is not a scan failure. Avoid a second error on exit.
        try:
            sys.stdout = open(os.devnull, "w")
        except OSError:
            pass
        raise SystemExit(0)
