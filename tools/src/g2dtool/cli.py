"""Provide the command-line interface for Forge2D Template repository tooling."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import argparse
import subprocess
import textwrap

from g2dtool import __version__
from g2dtool.asset_manager import add_asset_manager_parser
from g2dtool.check import run_check
from g2dtool.config import ProjectConfigError
from g2dtool.doctor import collect_doctor_report, format_doctor_report
from g2dtool.export import EXPORT_TARGETS, run_export
from g2dtool.godot import (
    GODOT_RESOURCE_IMPORT_TIMEOUT_SECONDS,
    PASS,
    build_godot_editor_command,
    build_godot_import_command,
    build_godot_run_command,
    build_godot_test_command,
    discover_godot,
    run_godot_command,
)
from g2dtool.install import run_install
from g2dtool.logger import (
    error,
    join_command,
    print_help_line,
    print_status_line,
    success,
)
from g2dtool.release import run_release_prepare
from g2dtool.repository import discover_repository_layout
from g2dtool.style import run_style

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_REQUIREMENT_MISSING = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130

WELCOME_TEXT = textwrap.dedent(
    """\
    🧭 Forge2D Template developer entry point

    🔍 Inspect the repository
      python tools/control.py --help
      python tools/control.py doctor
      python tools/control.py install
      python tools/control.py style
      python tools/control.py check
      python tools/control.py export linux --dry-run
      python tools/control.py release prepare --dry-run

    🎮 Run or test the project
      python tools/control.py godot4
      python tools/control.py godot4 import
      python tools/control.py godot4 test
      python tools/control.py forge2d-template run
      python tools/control.py Forge2D-Template run

    🧩 Run or test Asset Studio
      python tools/control.py asset-manager run
      python tools/control.py asset-manager install
      python tools/control.py asset-manager upgrade
      python tools/control.py asset-manager doctor
      python tools/control.py asset-manager test
      python tools/control.py asset-manager check
    """
)


def build_parser(prog: str = "g2d") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Inspect and maintain a Forge2D Template repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              python tools/control.py doctor
              python tools/control.py install
              python tools/control.py install --dry-run
              python tools/control.py style
              python tools/control.py check
              python tools/control.py export linux --dry-run
              python tools/control.py release prepare --dry-run
              python tools/control.py godot4 import
              python tools/control.py godot4 test
              python tools/control.py forge2d-template run
              python tools/control.py Forge2D-Template run
              python tools/control.py asset-manager run
              python tools/control.py asset-manager install
              python tools/control.py asset-manager upgrade
              python tools/control.py asset-manager doctor
              python tools/control.py asset-manager test
            """
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    add_asset_manager_parser(commands)

    version_parser = commands.add_parser("version", help="show the tooling version")
    version_parser.set_defaults(handler=_show_version)

    doctor_parser = commands.add_parser(
        "doctor", help="diagnose the Forge2D Template local and external tooling"
    )
    doctor_parser.set_defaults(handler=_run_doctor)

    check_parser = commands.add_parser(
        "check", help="run doctor, source style, tests, and Godot integration"
    )
    check_parser.set_defaults(handler=_run_check)

    style_parser = commands.add_parser(
        "style", help="validate mandatory Python and GDScript coding standards"
    )
    style_parser.set_defaults(handler=_run_style)

    install_parser = commands.add_parser(
        "install", help="validate and prepare a local development environment"
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and show planned commands without making changes",
    )
    install_parser.add_argument(
        "--yes",
        action="store_true",
        help="accept installer confirmations for unattended setup",
    )
    install_parser.set_defaults(handler=_run_install)

    export_parser = commands.add_parser(
        "export", help="create a validated Godot release export"
    )
    export_parser.add_argument(
        "target",
        choices=tuple(EXPORT_TARGETS),
        help="release target",
    )
    export_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate inputs and show the command without making changes",
    )
    export_parser.set_defaults(handler=_run_export)

    release_parser = commands.add_parser(
        "release", help="prepare verified assets for a reviewed GitHub release"
    )
    release_commands = release_parser.add_subparsers(
        dest="release_command",
        required=True,
    )
    release_prepare_parser = release_commands.add_parser(
        "prepare", help="verify downloaded CI exports and create checksums"
    )
    release_prepare_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate inputs and show fixed outputs without making changes",
    )
    release_prepare_parser.set_defaults(handler=_run_release_prepare)

    godot_parser = commands.add_parser(
        "godot4", aliases=["godot"], help="run godot commands for this repository"
    )
    godot_parser.add_argument(
        "mode",
        nargs="?",
        choices=("editor", "import", "run", "test"),
        default="editor",
        help="godot4 command mode",
    )
    godot_parser.add_argument("args", nargs=argparse.REMAINDER)
    godot_parser.set_defaults(handler=_run_godot_command)

    template_parser = commands.add_parser(
        "forge2d-template",
        aliases=["Forge2D-Template"],
        help="alias for running the template project",
    )
    template_parser.add_argument(
        "mode",
        nargs="?",
        choices=("run",),
        default="run",
        help="run mode",
    )
    template_parser.add_argument("args", nargs=argparse.REMAINDER)
    template_parser.set_defaults(handler=_run_template_project)

    return parser


def main(arguments: Sequence[str] | None = None, prog: str = "g2d") -> int:
    """Run the CLI and return a stable process exit code."""

    try:
        options = build_parser(prog=prog).parse_args(arguments)
        return int(options.handler(options))
    except SystemExit as system_exit_error:
        raise
    except ProjectConfigError as config_error:
        error(f"Error: {config_error}")
        return EXIT_USAGE
    except KeyboardInterrupt:
        error("Aborted.")
        return EXIT_INTERRUPTED
    except Exception as exc:
        error(f"Internal error: {exc}")
        return EXIT_FAILURE


def welcome() -> int:
    """Print the concise developer onboarding screen."""

    print(WELCOME_TEXT)
    return EXIT_OK


def _show_version(_options: argparse.Namespace) -> int:
    print(f"g2d {__version__}")
    return EXIT_OK


def _run_doctor(_options: argparse.Namespace) -> int:
    report = collect_doctor_report()
    print(format_doctor_report(report))
    return report.exit_code


def _run_check(_options: argparse.Namespace) -> int:
    return run_check()


def _run_style(_options: argparse.Namespace) -> int:
    return run_style()


def _run_install(options: argparse.Namespace) -> int:
    return run_install(
        dry_run=options.dry_run,
        yes=options.yes,
    )


def _run_export(options: argparse.Namespace) -> int:
    return run_export(options.target, dry_run=options.dry_run)


def _run_release_prepare(options: argparse.Namespace) -> int:
    return run_release_prepare(dry_run=options.dry_run)


def _run_godot_command(options: argparse.Namespace) -> int:
    layout = discover_repository_layout()
    user_arguments = _normalize_arguments(options.args)

    result = discover_godot(layout.repository_root)
    if result.status != PASS:
        error("Godot 4 wurde nicht gefunden.")
        print()
        print_help_line("Prüfen:")
        print_help_line("  python tools/control.py doctor")
        print()
        print_help_line("Installieren:")
        print_help_line("  python tools/control.py install")
        return EXIT_REQUIREMENT_MISSING
    if result.executable is None:
        return EXIT_REQUIREMENT_MISSING

    if options.mode == "editor":
        return _run_external_command(
            build_godot_editor_command(
                result.executable,
                layout.game_directory,
                user_arguments,
            )
        )

    import_exit_code = _run_godot_resource_import(
        result.executable,
        layout.game_directory,
    )
    if import_exit_code != EXIT_OK or options.mode == "import":
        return import_exit_code

    if options.mode == "run":
        command = build_godot_run_command(
            result.executable, layout.game_directory, user_arguments
        )
    elif options.mode == "test":
        command = build_godot_test_command(
            result.executable, layout.game_directory, user_arguments
        )
    else:
        raise RuntimeError(f"Unsupported godot mode: {options.mode}")

    return _run_external_command(command)


def _run_template_project(options: argparse.Namespace) -> int:
    options.mode = "run"
    return _run_godot_command(options)


def _run_godot_resource_import(executable: Path, game_directory: Path) -> int:
    command = build_godot_import_command(executable, game_directory)
    print_status_line("running", "Godot resource import", join_command(command))
    exit_code = _run_external_command(
        command,
        timeout_seconds=GODOT_RESOURCE_IMPORT_TIMEOUT_SECONDS,
    )
    if exit_code == EXIT_OK:
        success("Godot-Ressourcenimport abgeschlossen.")
    else:
        error(f"Godot-Ressourcenimport mit Exit-Code {exit_code} fehlgeschlagen.")
    return exit_code


def _run_external_command(
    command: Sequence[str],
    *,
    timeout_seconds: int | None = None,
) -> int:
    try:
        if timeout_seconds is None:
            return run_godot_command(command)
        return run_godot_command(command, timeout_seconds=timeout_seconds)
    except FileNotFoundError:
        error("Godot executable not found.")
        return EXIT_REQUIREMENT_MISSING
    except subprocess.TimeoutExpired:
        error(
            "Godot command timed out after "
            f"{timeout_seconds} seconds: {join_command(command)}"
        )
        return EXIT_FAILURE
    except KeyboardInterrupt:
        error("Aborted.")
        return EXIT_INTERRUPTED


def _normalize_arguments(arguments: Sequence[str]) -> tuple[str, ...]:
    if arguments and arguments[0] == "--":
        return tuple(arguments[1:])
    return tuple(arguments)
