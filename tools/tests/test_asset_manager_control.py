"""Test central Studio commands without installing packages or touching user data."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import importlib.metadata
import json
import os
import subprocess
import sys

import pytest

from _source_path import add_source_root

add_source_root()

from g2dtool import asset_manager, asset_manager_probe
from g2dtool.cli import main


REPOSITORY = Path(__file__).resolve().parents[2]


def create_environment(root: Path) -> None:
    environment = asset_manager.StudioEnvironment(root)
    environment.python.parent.mkdir(parents=True)
    environment.python.write_text("test interpreter", encoding="utf-8")
    (environment.venv / "pyvenv.cfg").write_text("home = test\n", encoding="utf-8")


class FakeProcess:
    """Model setup and diagnostics while recording every would-be child process."""

    def __init__(self, root: Path, *, installed: bool = False) -> None:
        self.root = root
        self.installed = installed
        self.pip_available = True
        self.calls = []
        self.failures = {}
        self.probe_payload = None

    def __call__(self, command, root, **options):
        command = list(map(str, command))
        self.calls.append((command, root, options))
        key = "action"
        output = ""
        if command[1:3] == ["-m", "venv"]:
            key = "create"
            if not self.failures.get(key):
                create_environment(self.root)
        elif "asset_manager_probe.py" in command[2]:
            key = command[3]
            code = self.failures.get(key, 0)
            if key in {"environment", "pip"} and not self.pip_available:
                code = code or 1
            if key == "packages" and not self.installed:
                code = 1
            checks = [{"name": key, "ok": code == 0, "detail": "test diagnostic"}]
            output = json.dumps(checks) if self.probe_payload is None else self.probe_payload
            return subprocess.CompletedProcess(command, code, output, "probe stderr")
        elif command[1:3] == ["-m", "ensurepip"]:
            key = "ensurepip"
            if not self.failures.get(key):
                self.pip_available = True
        elif "pip" in command:
            key = "install" if "install" in command else "pip-check"
            if key == "install" and not self.failures.get(key):
                self.installed = True
        elif "pytest" in command:
            key = "pipeline" if "tools/AssetManager/PyGameTools/.tests" in command else "tests"
        return subprocess.CompletedProcess(command, self.failures.get(key, 0), output, "")


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "checkout with spaces"
    (root / ".git").mkdir(parents=True)
    studio = root / "tools" / "AssetManager"
    studio.mkdir(parents=True)
    (studio / "studio.py").write_text("# fixture\n", encoding="utf-8")
    (studio / "pyproject.toml").write_text(
        (REPOSITORY / "tools/AssetManager/pyproject.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return root


@pytest.fixture
def ready(checkout, monkeypatch):
    create_environment(checkout)
    process = FakeProcess(checkout, installed=True)
    monkeypatch.setattr(asset_manager, "_execute", process)
    return process


@pytest.mark.parametrize("family", ["asset-manager", "assetmanager"])
@pytest.mark.parametrize("mode", asset_manager.MODES)
def test_cli_dispatches_every_mode_without_loading_qt(monkeypatch, family, mode):
    observed = []

    def dispatch(selected, **options):
        observed.append((selected, options))
        return 17

    monkeypatch.setattr(asset_manager, "run_asset_manager", dispatch)
    assert main([family, mode]) == 17
    assert observed == [(mode, {"dry_run": False, "core": False, "project": None, "config": None})]


def test_default_mode_and_option_forwarding(monkeypatch):
    observed = []
    monkeypatch.setattr(
        asset_manager, "run_asset_manager", lambda mode, **kw: observed.append((mode, kw)) or 0
    )
    assert main(["asset-manager"]) == 0
    assert observed[-1][0] == "run"
    assert main(["asset-manager", "run", "--project", "my project", "--dry-run"]) == 0
    assert observed[-1][1]["project"] == Path("my project")
    assert observed[-1][1]["dry_run"] is True
    assert main(["asset-manager", "test", "--core"]) == 0
    assert observed[-1][1]["core"] is True
    assert main(["asset-manager", "doctor", "--config", "project.json"]) == 0
    assert observed[-1][1]["config"] == Path("project.json")


@pytest.mark.parametrize("arguments", [
    ["asset-manager", "unknown"],
    ["asset-manager", "doctor", "--dry-run"],
    ["asset-manager", "run", "--core"],
])
def test_cli_rejects_unsupported_options(arguments):
    with pytest.raises(SystemExit) as exc:
        main(arguments)
    assert exc.value.code == 2


def test_first_run_creates_venv_installs_then_launches(checkout, monkeypatch):
    process = FakeProcess(checkout)
    monkeypatch.setattr(asset_manager, "_execute", process)
    assert asset_manager.run_asset_manager("run", start=checkout) == 0
    commands = [call[0] for call in process.calls]
    assert commands[0] == [sys.executable, "-m", "venv", str(checkout / ".venv")]
    install = next(command for command in commands if "install" in command)
    assert install[0] == str(asset_manager.StudioEnvironment(checkout).python)
    assert "--require-virtualenv" in install and "--no-user" in install
    assert install[-1] == f"{checkout}/tools/AssetManager[test,gui]"
    assert commands[-1][-1] == "gui"
    assert all(call[1] == checkout for call in process.calls)
    assert not any("--clear" in command or "sudo" in command for command in commands)


def test_ready_run_reuses_packages_and_resolves_project_from_calling_directory(
    checkout, ready, monkeypatch, tmp_path,
):
    monkeypatch.chdir(tmp_path)
    assert asset_manager.run_asset_manager("run", start=checkout, project=Path("my studio")) == 0
    commands = [call[0] for call in ready.calls]
    assert not any("pip" in command or "ensurepip" in command or "venv" in command
                   for command in commands if "asset_manager_probe.py" not in command[2])
    assert commands[-1][-2:] == ["--project", str(tmp_path / "my studio")]


def test_changed_pins_trigger_one_install(checkout, ready):
    ready.installed = False
    assert asset_manager.run_asset_manager("install", start=checkout) == 0
    assert sum("install" in call[0] for call in ready.calls) == 1
    assert not any("gui" in call[0] for call in ready.calls)


@pytest.mark.parametrize("mode", [
    "run", "install", "upgrade", "import", "test", "pipeline-test", "check",
])
def test_missing_pip_is_repaired_before_install_or_launch(checkout, ready, mode):
    ready.pip_available = False
    ready.installed = False
    sentinel = checkout / ".venv" / "keep.txt"
    sentinel.write_text("existing environment", encoding="utf-8")

    assert asset_manager.run_asset_manager(mode, start=checkout) == 0

    commands = [call[0] for call in ready.calls]
    bootstrap = next(command for command in commands if "ensurepip" in command)
    install = next(command for command in commands if "install" in command)
    assert bootstrap == [str(asset_manager.StudioEnvironment(checkout).python),
                         "-m", "ensurepip", "--upgrade"]
    assert commands.index(bootstrap) < commands.index(install)
    assert not any("venv" in command for command in commands)
    assert sentinel.read_text(encoding="utf-8") == "existing environment"
    assert ready.pip_available and ready.installed


def test_upgrade_refreshes_ready_environment_without_launching_desktop(checkout, ready):
    assert asset_manager.run_asset_manager("upgrade", start=checkout) == 0
    commands = [call[0] for call in ready.calls]
    assert sum("ensurepip" in command for command in commands) == 1
    install = next(command for command in commands if "install" in command)
    assert "--upgrade" in install
    assert "--require-virtualenv" in install and "--no-user" in install
    assert f"{checkout}/tools/AssetManager[test,gui]" in install
    assert any(command[1:] == ["-m", "pip", "check"] for command in commands)
    assert not any("gui" in command or "pytest" in command for command in commands)


def test_upgrade_core_keeps_gui_dependencies_optional(checkout, ready):
    assert asset_manager.run_asset_manager("upgrade", start=checkout, core=True) == 0
    install = next(call[0] for call in ready.calls if "install" in call[0])
    assert f"{checkout}/tools/AssetManager[test]" in install
    probes = [call[0] for call in ready.calls if "asset_manager_probe.py" in call[0][2]]
    assert all("--core" in command for command in probes)
    assert not any("platform" in command for command in probes)


def test_failed_pip_bootstrap_stops_without_replacing_environment(checkout, ready):
    ready.pip_available = False
    ready.failures["ensurepip"] = 31
    assert asset_manager.run_asset_manager("install", start=checkout) == 31
    assert "ensurepip" in ready.calls[-1][0]
    assert not any("install" in call[0] or "gui" in call[0] for call in ready.calls)
    assert (checkout / ".venv/pyvenv.cfg").is_file()


def test_bootstrap_success_requires_pip_to_be_available(checkout, ready, capsys):
    ready.failures["pip"] = 1
    assert asset_manager.run_asset_manager("install", start=checkout) == 1
    assert any("ensurepip" in call[0] for call in ready.calls)
    assert not any("install" in call[0] or "gui" in call[0] for call in ready.calls)
    assert "still unavailable" in capsys.readouterr().out


def test_upgrade_rejects_wrong_interpreter_before_bootstrap(checkout, ready):
    ready.failures["interpreter"] = 1
    assert asset_manager.run_asset_manager("upgrade", start=checkout) == 1
    assert not any("ensurepip" in call[0] or "install" in call[0] for call in ready.calls)


@pytest.mark.parametrize("mode", ["install", "import"])
def test_preparation_never_imports_assets_or_launches_desktop(checkout, ready, mode):
    assert asset_manager.run_asset_manager(mode, start=checkout) == 0
    assert all("asset_manager_probe.py" in call[0][2] for call in ready.calls)
    assert not (checkout / "game").exists()


@pytest.mark.parametrize("mode", [
    "run", "install", "upgrade", "import", "test", "pipeline-test", "check",
])
@pytest.mark.parametrize("existing", [False, True])
def test_dry_run_never_starts_process_or_changes_environment(
    checkout, monkeypatch, mode, existing, capsys,
):
    if existing:
        create_environment(checkout)

    def forbidden(*args, **kwargs):
        raise AssertionError("Dry-run started a process")

    monkeypatch.setattr(asset_manager, "_execute", forbidden)
    assert asset_manager.run_asset_manager(mode, start=checkout, dry_run=True) == 0
    assert (checkout / ".venv").exists() == existing
    output = capsys.readouterr().out
    assert "DRY-RUN" in output
    assert "-m ensurepip --upgrade" in output
    assert ("If pip is missing:" in output) == (mode != "upgrade")


def test_missing_environment_doctor_never_installs(checkout, monkeypatch, capsys):
    process = FakeProcess(checkout)
    monkeypatch.setattr(asset_manager, "_execute", process)
    assert asset_manager.run_asset_manager("doctor", start=checkout) == 1
    assert process.calls == []
    assert not (checkout / ".venv").exists()
    assert "asset-manager install" in capsys.readouterr().out


def test_doctor_reports_missing_packages_without_installing(checkout, ready, capsys):
    ready.installed = False
    assert asset_manager.run_asset_manager("doctor", start=checkout) == 1
    assert not any("pip" in call[0] or "gui" in call[0] for call in ready.calls)
    assert "missing/mismatched" in capsys.readouterr().out


def test_doctor_reports_missing_pip_without_repairing(checkout, ready, capsys):
    ready.pip_available = False
    assert asset_manager.run_asset_manager("doctor", start=checkout) == 1
    assert not ready.pip_available
    assert not any("ensurepip" in call[0] or "install" in call[0] for call in ready.calls)
    assert "asset-manager install" in capsys.readouterr().out


def test_doctor_can_forward_explicit_project_configuration(checkout, ready, tmp_path):
    config = tmp_path / "project.studio-local.json"
    assert asset_manager.run_asset_manager("doctor", start=checkout, config=config) == 0
    assert ready.calls[-1][0][-3:] == ["doctor", "--config", str(config)]
    assert not config.exists()


def test_incomplete_environment_is_not_recreated(checkout, monkeypatch, capsys):
    sentinel = checkout / ".venv" / "keep.txt"
    sentinel.parent.mkdir()
    sentinel.write_text("do not delete", encoding="utf-8")
    process = FakeProcess(checkout)
    monkeypatch.setattr(asset_manager, "_execute", process)
    assert asset_manager.run_asset_manager("run", start=checkout) == 1
    assert process.calls == []
    assert sentinel.read_text(encoding="utf-8") == "do not delete"
    assert "nothing was removed" in capsys.readouterr().out


def test_symlink_environment_is_rejected(checkout, tmp_path, monkeypatch):
    outside = tmp_path / "external environment"
    outside.mkdir()
    try:
        (checkout / ".venv").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation unavailable")
    process = FakeProcess(checkout)
    monkeypatch.setattr(asset_manager, "_execute", process)
    assert asset_manager.run_asset_manager("run", start=checkout) == 1
    assert process.calls == [] and list(outside.iterdir()) == []


@pytest.mark.parametrize("failure", ["interpreter", "runtime", "platform"])
def test_preflight_failure_blocks_launch_without_reinstalling(checkout, ready, failure):
    ready.failures[failure] = 1
    assert asset_manager.run_asset_manager("run", start=checkout) == 1
    assert not any("install" in call[0] or "gui" in call[0] for call in ready.calls)


@pytest.mark.parametrize("mode", ["run", "upgrade"])
def test_failed_pip_install_preserves_environment_and_exit_code(checkout, ready, mode):
    ready.installed = False
    ready.failures["install"] = 42
    assert asset_manager.run_asset_manager(mode, start=checkout) == 42
    assert not any("gui" in call[0] for call in ready.calls)
    assert (checkout / ".venv/pyvenv.cfg").is_file()


def test_failed_venv_creation_stops_before_pip(checkout, monkeypatch):
    process = FakeProcess(checkout)
    process.failures["create"] = 3
    monkeypatch.setattr(asset_manager, "_execute", process)
    assert asset_manager.run_asset_manager("run", start=checkout) == 3
    assert len(process.calls) == 1


@pytest.mark.parametrize("payload", ["", "[]", "{}", '[{"ok": true}]', "null", "false"])
def test_malformed_probe_never_counts_as_success(checkout, ready, payload):
    ready.probe_payload = payload
    assert asset_manager.run_asset_manager("run", start=checkout) == 1
    assert not any("gui" in call[0] for call in ready.calls)


def test_gui_tests_use_offscreen_and_fail_when_platform_is_unavailable(checkout, ready):
    ready.failures["platform"] = -6
    assert asset_manager.run_asset_manager("test", start=checkout) == 1
    assert ready.calls[-1][2]["offscreen"] is True
    assert not any("pytest" in call[0] for call in ready.calls)


def test_core_tests_explicitly_omit_gui_and_qt_probe(checkout, ready):
    assert asset_manager.run_asset_manager("test", start=checkout, core=True) == 0
    assert "--ignore=tools/AssetManager/tests/gui" in ready.calls[-1][0]
    assert all("--core" in call[0] for call in ready.calls[:-1])
    assert not any("platform" in call[0] for call in ready.calls)


def test_check_runs_both_suites_and_preserves_a_failing_result(checkout, ready):
    ready.failures["tests"] = 5
    assert asset_manager.run_asset_manager("check", start=checkout) == 5
    suites = [call[0] for call in ready.calls if "pytest" in call[0]]
    assert len(suites) == 2
    assert suites[0][-1] == "tools/AssetManager/tests"
    assert "tools/AssetManager/PyGameTools/.tests" in suites[1]


def test_pipeline_tests_need_no_qt_or_godot(checkout, ready):
    assert asset_manager.run_asset_manager("pipeline-test", start=checkout) == 0
    assert not any("platform" in call[0] or "godot" in call[0] for call in ready.calls)
    assert "tools/AssetManager/PyGameTools/.tests" in ready.calls[-1][0]


@pytest.mark.parametrize("module", ["pip", "ensurepip"])
def test_execute_uses_checkout_env_timeout_and_disables_pip_redirection(
    monkeypatch, tmp_path, module,
):
    observed = []
    for name in ("PIP_TARGET", "PIP_PREFIX", "PIP_ROOT", "PIP_USER"):
        monkeypatch.setenv(name, "unsafe-redirect")
    monkeypatch.setenv("QT_QPA_PLATFORM", "xcb")

    def process(command, **options):
        observed.append(options)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", process)
    arguments = ["check"] if module == "pip" else ["--upgrade"]
    asset_manager._execute(["local-python", "-m", module, *arguments], tmp_path,
                           capture=True, offscreen=True, timeout=30)
    options = observed[0]
    assert options["cwd"] == tmp_path and options["timeout"] == 30
    assert options["capture_output"] and not options["check"]
    assert not options.get("shell", False)
    assert options["env"]["QT_QPA_PLATFORM"] == "offscreen"
    assert options["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert options["env"]["PIP_CONFIG_FILE"] == os.devnull
    assert all(name not in options["env"] for name in (
        "PIP_TARGET", "PIP_PREFIX", "PIP_ROOT", "PIP_USER",
    ))
    assert os.environ["PIP_TARGET"] == "unsafe-redirect"


@pytest.mark.parametrize("failure, code", [(OSError("unavailable"), 1),
                                         (subprocess.TimeoutExpired("test", 30), 124)])
def test_execute_reports_process_failures(monkeypatch, tmp_path, failure, code):
    def process(*args, **kwargs):
        raise failure

    monkeypatch.setattr(subprocess, "run", process)
    with pytest.raises(asset_manager.AssetManagerError) as exc:
        asset_manager._execute(["python"], tmp_path, timeout=30)
    assert exc.value.code == code


def test_probe_checks_exact_versions_and_checkout(checkout, monkeypatch):
    versions = {"etherfood-studio": "0.1.0", "pytest": "8.4.2", "jsonschema": "4.26.0",
                "Pillow": "12.1.1", "PySide6": "6.10.2", "markdown-it-py": "4.0.0"}
    monkeypatch.setattr(importlib.metadata, "version", lambda name: versions[name])
    studio = checkout / "tools/AssetManager"
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: SimpleNamespace(
        origin=str(studio / "src/etherfood_studio/__init__.py"),
    ))
    assert all(check["ok"] for check in asset_manager_probe.package_checks(studio, core=False))
    versions["Pillow"] = "0.0.1"
    checks = asset_manager_probe.package_checks(studio, core=False)
    assert not next(check for check in checks if check["name"] == "Pillow")["ok"]
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert asset_manager_probe.package_checks(studio, core=True)[-1]["ok"] is False


def test_probe_rejects_system_interpreter(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path))
    assert asset_manager_probe.environment_checks(tmp_path)[0]["ok"] is False


def test_probe_reports_native_error_and_core_omits_qt(monkeypatch):
    imports = []

    def import_module(name):
        imports.append(name)
        if name == "PySide6.QtWidgets":
            raise ImportError("libGL.so.1 missing")

    monkeypatch.setattr(importlib, "import_module", import_module)
    checks = asset_manager_probe.runtime_checks(core=False)
    assert checks[-1] == {"name": "PySide6.QtWidgets", "ok": False, "detail": "libGL.so.1 missing"}
    imports.clear()
    assert all(check["ok"] for check in asset_manager_probe.runtime_checks(core=True))
    assert "PySide6.QtWidgets" not in imports


def test_control_works_from_unrelated_directory_without_activating_venv(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPOSITORY / "tools/control.py"),
         "asset-manager", "run", "--dry-run", "--project", "local project"],
        cwd=tmp_path, text=True, capture_output=True, check=False, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert str(REPOSITORY / "tools/AssetManager/studio.py") in result.stdout
    assert str(tmp_path / "local project") in result.stdout


@pytest.mark.skipif(importlib.util.find_spec("ensurepip") is None, reason="ensurepip unavailable")
def test_install_repairs_real_venv_without_pip_and_reuses_it(checkout, monkeypatch):
    """Exercise the reported bootstrap failure offline with real venv and ensurepip."""

    environment = asset_manager.StudioEnvironment(checkout, core=True)
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(environment.venv)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    assert environment.probe("environment", report=False) == 1
    sentinel = environment.venv / "keep.txt"
    sentinel.write_text("preserve existing files", encoding="utf-8")
    execute = asset_manager._execute
    bootstraps = []

    def offline_execute(command, root, **options):
        # The unrelated Studio packages are fixtures; bootstrap and its probes are real.
        if "asset_manager_probe.py" in command[2] and command[3] in {"packages", "runtime"}:
            checks = [{"name": command[3], "ok": True, "detail": "Offline package fixture"}]
            return subprocess.CompletedProcess(command, 0, json.dumps(checks), "")
        if "ensurepip" in command:
            bootstraps.append(command)
        assert not ("pip" in command and "install" in command), "Unexpected network installation"
        return execute(command, root, **options)

    monkeypatch.setattr(asset_manager, "_execute", offline_execute)
    assert asset_manager.run_asset_manager("install", start=checkout, core=True) == 0
    assert environment.probe("environment", report=False) == 0
    assert asset_manager.run_asset_manager("install", start=checkout, core=True) == 0
    assert len(bootstraps) == 1
    assert sentinel.read_text(encoding="utf-8") == "preserve existing files"
