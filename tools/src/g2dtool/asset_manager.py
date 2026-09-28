"""Control Asset Studio with a safe, repository-local Python environment."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

from g2dtool.logger import (
    error,
    info,
    join_command,
    print_dry_run,
    print_help_line,
    print_status_line,
    success,
)
from g2dtool.repository import discover_repository_layout


SETUP_TIMEOUT_SECONDS = 900
PROBE_TIMEOUT_SECONDS = 30
TEST_TIMEOUT_SECONDS = 900
MODES = ("run", "install", "import", "doctor", "test", "pipeline-test", "check")
SETUP_HELP = "python tools/control.py asset-manager install"
NATIVE_HELP = (
    "Check the reported Qt/GL/EGL/XKB/D-Bus library or display/plugin error. "
    "See docs/system/development/asset-studio/DEVELOPMENT.md. "
    "System packages are never installed automatically."
)


class AssetManagerError(RuntimeError):
    """Report an expected launch/setup failure with its process exit code."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code if code > 0 else 1


@dataclass(frozen=True)
class StudioEnvironment:
    """Keep the checkout, local environment and selected dependency scope together."""

    root: Path
    core: bool = False

    @property
    def studio(self) -> Path:
        return self.root / "tools" / "AssetManager"

    @property
    def venv(self) -> Path:
        return self.root / ".venv"

    @property
    def python(self) -> Path:
        folder, binary = ("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")
        return self.venv / folder / binary

    @property
    def install_command(self) -> list[str]:
        extras = "test" if self.core else "test,gui"
        return [
            str(self.python), "-m", "pip", "--disable-pip-version-check",
            "--require-virtualenv", "install", "--no-user", "--editable",
            f"{self.studio}[{extras}]",
        ]

    def validate(self) -> None:
        """Refuse external or incomplete environments without deleting anything."""

        for path in (self.studio / "studio.py", self.studio / "pyproject.toml"):
            if not path.is_file() or not path.resolve().is_relative_to(self.root):
                raise AssetManagerError(f"Missing or external Studio source: {path}")
        if self.venv.is_symlink() or self.venv.resolve() != self.venv:
            raise AssetManagerError("The repository .venv must not point outside the checkout.")
        if self.venv.exists() and not (
            self.venv.is_dir() and (self.venv / "pyvenv.cfg").is_file() and self.python.is_file()
        ):
            raise AssetManagerError(
                "The existing .venv is incomplete. Repair it explicitly; nothing was removed. "
                "If creation failed, check Python venv/ensurepip support (e.g. python3-venv)."
            )

    def probe(self, mode: str, *, report: bool = True, offscreen: bool = False) -> int:
        """Run read-only diagnostics with the actual environment interpreter."""

        command = [
            str(self.python), "-B", str(Path(__file__).with_name("asset_manager_probe.py")),
            mode, "--venv", str(self.venv), "--studio", str(self.studio),
        ]
        if self.core:
            command.append("--core")
        result = _execute(command, self.root, capture=True, offscreen=offscreen,
                          timeout=PROBE_TIMEOUT_SECONDS)
        try:
            checks = json.loads(result.stdout)
            if not isinstance(checks, list) or not checks or not all(
                isinstance(check, dict) and isinstance(check.get("ok"), bool)
                and isinstance(check.get("name"), str) and isinstance(check.get("detail"), str)
                for check in checks
            ):
                raise ValueError("Invalid diagnostic response")
            code = result.returncode or int(any(not check["ok"] for check in checks))
            if report:
                for check in checks:
                    print_status_line(
                        "pass" if check["ok"] else "fail", check["name"], check["detail"]
                    )
        except (ValueError, TypeError):
            code = result.returncode or 1
            if report:
                error(f"{mode} probe failed: {(result.stderr or result.stdout).strip()[-2000:]}")
        if report and code and mode in {"runtime", "platform"}:
            print_help_line(NATIVE_HELP)
        return code

    def prepare(self, *, dry_run: bool) -> None:
        """Create only a missing venv and install only missing/mismatched dependencies."""

        create_command = [sys.executable, "-m", "venv", str(self.venv)]
        if dry_run:
            if not self.venv.exists():
                print_dry_run(join_command(create_command))
            print_dry_run("If packages are missing/outdated: " + join_command(self.install_command))
            print_dry_run("Verify interpreter, package pins and module imports; no commands run.")
            return
        if not self.venv.exists():
            _require_success(create_command, self.root, "Create repository .venv")
        if self.probe("environment"):
            raise AssetManagerError(
                "Repair the reported .venv/Python/pip problem explicitly. "
                "Use Python >= 3.11 with venv/ensurepip; no environment was replaced."
            )
        if self.probe("packages", report=False):
            self.probe("packages")
            _require_success(self.install_command, self.root, "Install Asset Studio in .venv")
            if self.probe("packages"):
                raise AssetManagerError("Package verification failed after installation.")
            _require_success(
                [str(self.python), "-m", "pip", "check"], self.root, "Verify pip dependencies"
            )
        else:
            success("Asset Studio packages already match this checkout; no installation needed.")


def add_asset_manager_parser(commands: argparse._SubParsersAction) -> None:
    """Register the central command family without importing Qt into Control."""

    parser = commands.add_parser(
        "asset-manager", aliases=["assetmanager"], help="run, diagnose and test Asset Studio"
    )
    parser.set_defaults(handler=_dispatch, mode="run", dry_run=False, core=False,
                        project=None, config=None)
    actions = parser.add_subparsers(dest="mode")
    descriptions = {
        "run": "prepare the local .venv if needed and open the desktop",
        "install": "prepare the local .venv and verify Python module imports",
        "import": "alias for install: prepare tool modules, not game assets",
        "doctor": "diagnose .venv, packages and native Qt libraries without installing",
        "test": "run Studio tests, including Qt offscreen tests",
        "pipeline-test": "test the existing image pipelines using synthetic fixtures",
        "check": "run diagnostics, Studio tests and existing pipeline tests",
    }
    for mode, description in descriptions.items():
        action = actions.add_parser(mode, help=description, description=description)
        if mode != "doctor":
            action.add_argument(
                "--dry-run", action="store_true", help="show commands without changes"
            )
        if mode not in {"run", "pipeline-test"}:
            action.add_argument("--core", action="store_true", help="explicitly omit Qt/GUI checks")
        if mode == "run":
            action.add_argument("--project", type=Path, help="open an existing Studio project")
        if mode == "doctor":
            action.add_argument(
                "--config", type=Path, help="also diagnose local Studio project roots"
            )
        action.set_defaults(handler=_dispatch, mode=mode)


def _dispatch(options: argparse.Namespace) -> int:
    return run_asset_manager(
        options.mode or "run", dry_run=options.dry_run, core=options.core,
        project=options.project, config=options.config,
    )


def run_asset_manager(
    mode: str,
    *,
    start: Path | None = None,
    dry_run: bool = False,
    core: bool = False,
    project: Path | None = None,
    config: Path | None = None,
) -> int:
    """Execute an explicit Studio action; never install during doctor or dry-run."""

    try:
        if mode not in MODES:
            raise AssetManagerError(f"Unknown Asset Manager mode: {mode}", 2)
        root = discover_repository_layout(start or Path(__file__)).repository_root
        environment = StudioEnvironment(root, core=core or mode == "pipeline-test")
        environment.validate()
        if mode == "doctor":
            return _doctor(environment, config=config)
        environment.prepare(dry_run=dry_run)
        commands = _action_commands(environment, mode, project=project)
        if dry_run:
            for command in commands:
                prefix = "QT_QPA_PLATFORM=offscreen " if mode in {"test", "check"} else ""
                print_dry_run(prefix + join_command(command))
            return 0
        if environment.probe("runtime"):
            return 1
        if mode in {"install", "import"}:
            success("Asset Studio environment ready. No assets were imported or generated.")
            return 0
        offscreen = mode in {"test", "check"}
        if not environment.core and environment.probe("platform", offscreen=offscreen):
            return 1
        exit_code = 0
        for command in commands:
            print_status_line("running", f"Asset Manager {mode}", join_command(command))
            # An interactive desktop must not be killed by a background test/setup deadline.
            result = _execute(command, root, offscreen=offscreen,
                              timeout=None if mode == "run" else TEST_TIMEOUT_SECONDS)
            if result.returncode:
                exit_code = result.returncode if result.returncode > 0 else 1
        return exit_code
    except AssetManagerError as exc:
        error(str(exc))
        return exc.code


def _doctor(environment: StudioEnvironment, *, config: Path | None) -> int:
    info("Asset Manager doctor: read-only; no setup or project creation")
    if not environment.python.is_file():
        error(f"Repository .venv is missing. Run: {SETUP_HELP}")
        return 1
    if environment.probe("environment"):
        print_help_line("Repair this .venv explicitly; Control will not delete it.")
        return 1
    packages = environment.probe("packages")
    runtime = environment.probe("runtime")
    if packages:
        print_help_line(f"Install the missing/mismatched packages with: {SETUP_HELP}")
    config_code = 0
    if config is not None:
        command = [str(environment.python), "-B", str(environment.studio / "studio.py"),
                   "doctor", "--config", str(config.expanduser().resolve())]
        config_code = _execute(command, environment.root, timeout=PROBE_TIMEOUT_SECONDS).returncode
    info("Display availability is verified on run; GUI tests use the offscreen platform.")
    return 1 if packages or runtime or config_code else 0


def _action_commands(
    environment: StudioEnvironment, mode: str, *, project: Path | None,
) -> list[list[str]]:
    if mode == "run":
        command = [str(environment.python), str(environment.studio / "studio.py"), "gui"]
        if project is not None:
            command.extend(("--project", str(project.expanduser().resolve())))
        return [command]
    prefix = [str(environment.python), "-m", "pytest", "-q"]
    studio = [*prefix, "tools/AssetManager/tests"]
    if environment.core:
        studio.append("--ignore=tools/AssetManager/tests/gui")
    pipeline = [
        *prefix, "tools/AssetManager/PyGameTools/.tests",
        "tools/AssetManager/PyGameTools/Pipline/2-SpritesheetResolution-Pipline/tests",
    ]
    if mode == "check":
        return [studio, pipeline]
    if mode == "test":
        return [studio]
    return [pipeline] if mode == "pipeline-test" else []


def _require_success(command: Sequence[str], root: Path, label: str) -> None:
    print_status_line("running", label, join_command(command))
    result = _execute(command, root, timeout=SETUP_TIMEOUT_SECONDS)
    if result.returncode:
        raise AssetManagerError(
            f"{label} failed. No desktop/tests were started. "
            "Check the error above (venv/ensurepip, package index or write access), then retry.",
            result.returncode,
        )


def _execute(
    command: Sequence[str],
    root: Path,
    *,
    capture: bool = False,
    offscreen: bool = False,
    timeout: int | None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if offscreen:
        env["QT_QPA_PLATFORM"] = "offscreen"
    if "pip" in command:
        # Prevent user-level pip settings from redirecting writes out of the verified .venv.
        for key in ("PIP_TARGET", "PIP_PREFIX", "PIP_ROOT", "PIP_USER"):
            env.pop(key, None)
        env["PIP_CONFIG_FILE"] = os.devnull
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        return subprocess.run(
            list(command), cwd=root, env=env, check=False, capture_output=capture,
            text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssetManagerError(f"Asset Manager command timed out after {timeout}s.", 124) from exc
    except OSError as exc:
        raise AssetManagerError(f"Cannot start Asset Manager command: {exc}") from exc
