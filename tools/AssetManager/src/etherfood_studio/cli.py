"""Read-only diagnostics and explicit desktop launch."""

import argparse
import importlib
import json
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
    jobs = commands.add_parser("jobs", help="Aufträge anzeigen oder sichere Diagnose starten")
    jobs.add_argument("--project", type=Path, required=True)
    jobs.add_argument("--run", choices=("diagnostic", "framreduce-help"))
    jobs.add_argument("--mode", choices=("success", "exit7", "missing", "slow", "child"),
                      default="success")
    jobs.add_argument("--timeout", type=float, default=30)
    build = commands.add_parser("build-plan",
                                 help="Lesender Buildplan oder explizite Cache-Diagnose")
    build.add_argument("--project", type=Path, required=True)
    build.add_argument("--asset", help="Asset-ID für echte Anforderungen, ohne Bildausführung")
    build.add_argument("--diagnostic", action="store_true", help="Synthetischen Graph planen")
    build.add_argument("--execute-diagnostic", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "build-plan":
            from .application.build_graphs import asset_graph, diagnostic_graph
            from .application.build_planner import BuildPlanner
            from .application.project_service import ProjectService

            if bool(args.asset) == bool(args.diagnostic) or \
                    args.execute_diagnostic and not args.diagnostic:
                raise StudioError("validation", "Entweder --asset ID oder --diagnostic wählen.")
            project = ProjectService.open(args.project, read_only=not args.execute_diagnostic)
            try:
                owner = args.asset or project.project().id
                graph = diagnostic_graph() if args.diagnostic else asset_graph(project, owner)
                planner = BuildPlanner(project)
                plan = planner.plan(owner, graph)
                value = planner.execute(plan) if args.execute_diagnostic else plan.to_data()
                print(json.dumps(value, ensure_ascii=False, indent=2))
                return 1 if value.get("status") == "incomplete" else 0
            finally:
                project.catalog.close()
        if args.command == "jobs":
            from .application.job_service import JobService
            from .application.project_service import ProjectService

            project = ProjectService.open(args.project)
            try:
                service = JobService(project)
                if args.run:
                    parameters = {"mode": args.mode} if args.run == "diagnostic" else {}
                    request = service.prepare(project.project().id, args.run, parameters,
                                               timeout=args.timeout)
                    result = service.run(request, on_event=lambda event: print(json.dumps(event)))
                    print(json.dumps(result))
                    return 0 if result["status"] == "succeeded" else 1
                print(json.dumps(service.store.rows(), ensure_ascii=False, indent=2))
                return 0
            finally:
                project.catalog.close()
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
