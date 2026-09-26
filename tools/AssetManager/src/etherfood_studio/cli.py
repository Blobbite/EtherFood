"""Read-only diagnostics and explicit desktop launch."""

import argparse
import importlib
from pathlib import Path
import shutil
from typing import Sequence

from . import __version__
from .config import ALIASES, Configuration
from .domain.models import StudioError


def doctor(config: Configuration) -> list[tuple[str, bool, str]]:
    results = []
    for alias in ALIASES:
        path = config.roots.get(alias)
        available = path is not None and path.is_dir()
        detail = "verfügbar" if available else "nicht konfiguriert/verfügbar"
        results.append((alias, available, detail))
    tool = config.roots.get("TOOL_ROOT")
    installed = bool(tool and (tool / "PyGameTools.py").is_file())
    results.append(("Pipeline", installed, "vorhanden" if installed else "Installation fehlt"))
    results.append(("Godot", bool(shutil.which("godot4") or shutil.which("godot")), "optional"))
    try:
        importlib.import_module("PySide6.QtWidgets")
        results.append(("GUI", True, "Qt-Bibliotheken ladbar; Display noch nicht geprüft"))
    except ImportError:
        results.append(("GUI", False, "Qt-Paket oder Laufzeitbibliotheken fehlen (optional)"))
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EtherFood Asset Studio – lokale Verwaltung")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    diagnose = commands.add_parser("doctor", help="Nur lesen; keine Verarbeitung starten")
    diagnose.add_argument("--config", type=Path)
    gui = commands.add_parser("gui", help="Lokalen Desktop öffnen")
    gui.add_argument("--project", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            config = Configuration.load(args.config) if args.config else Configuration()
            results = doctor(config)
            for name, available, detail in results:
                print(f'{"OK" if available else "FEHLT"}: {name}: {detail}')
            return 0 if all(row[1] for row in results[:5]) else 1
        if args.command == "gui":
            try:
                from .ui.main_window import launch
            except ImportError as exc:
                raise StudioError("unavailable", "GUI-Paket fehlt oder ist noch nicht verfügbar.",
                                  str(exc)) from exc
            return launch(args.project)
        parser.print_help()
        return 0
    except StudioError as exc:
        print(f"{exc.code}: {exc}")
        if exc.detail:
            print(exc.detail)
        return 2
