"""Tests for the release gate orchestration."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest
from unittest.mock import patch

from _source_path import add_source_root

add_source_root()

from g2dtool.check import (
    GODOT_INTEGRATION_IMPORT_SKIP_MESSAGE,
    GODOT_TEST_SUCCESS_MARKER,
    _run_godot_integration_test,
    run_check,
)
from g2dtool.doctor import DoctorReport, DoctorCheck
from g2dtool.repository import RepositoryLayout


class CheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repository"
        (self.root / ".git").mkdir(parents=True)
        (self.root / "tools" / "tests").mkdir(parents=True)
        (self.root / "tools" / "src").mkdir(parents=True)
        (self.root / "game").mkdir()
        (self.root / "game" / "project.godot").write_text("", encoding="utf-8")
        self.test_runner = (
            self.root / "game" / "test_scenes" / "helpers" / "bootstrap_integration_test.gd"
        )
        self.test_runner.parent.mkdir(parents=True)
        self.test_runner.write_text(
            "extends SceneTree\n",
            encoding="utf-8",
            newline="\n",
        )
        self.layout = RepositoryLayout(
            repository_root=self.root,
            pyproject_toml=self.root / "pyproject.toml",
            project_config=self.root / "config" / "project.toml",
            toolchain_config=self.root / "config" / "toolchain.toml",
            tools_directory=self.root / "tools",
            tools_source_directory=self.root / "tools" / "src",
            game_directory=self.root / "game",
            venv_directory=self.root / ".venv",
        )

    def test_runs_all_gate_steps_when_available(self) -> None:
        executed: list[tuple[str, ...]] = []

        def runner(command, _cwd):
            executed.append(tuple(command))
            return 0

        with (
            patch("g2dtool.check.discover_repository_layout", return_value=self.layout),
            patch(
                "g2dtool.check.collect_doctor_report",
                return_value=DoctorReport((DoctorCheck("repository", "pass", "ok"),)),
            ),
            patch(
                "g2dtool.check.discover_godot",
                return_value=type(
                    "GodotResult",
                    (),
                    {"status": "pass", "executable": Path("/fake/godot4")},
                )(),
            ),
        ):
            code = run_check(start=self.root, run_process=runner)

        self.assertEqual(code, 0)
        self.assertTrue(any(command[1:3] == ("-m", "pytest") for command in executed))
        import_index = next(
            index for index, command in enumerate(executed) if "--import" in command
        )
        test_index = next(
            index for index, command in enumerate(executed) if "--script" in command
        )
        self.assertLess(import_index, test_index)
        self.assertNotIn("--script", executed[import_index])
        self.assertNotIn("--import", executed[test_index])
        self.assertIn(str(self.test_runner), executed[test_index])
        self.assertNotIn("--test-mode", executed[test_index])

    def test_returns_failure_after_running_python_tests_when_godot_is_missing(self) -> None:
        executed: list[tuple[str, ...]] = []

        def runner(command, _cwd):
            executed.append(tuple(command))
            return 0

        with (
            patch("g2dtool.check.discover_repository_layout", return_value=self.layout),
            patch(
                "g2dtool.check.collect_doctor_report",
                return_value=DoctorReport((DoctorCheck("repository", "pass", "ok"),)),
            ),
            patch(
                "g2dtool.check.discover_godot",
                return_value=type(
                    "GodotResult",
                    (),
                    {"status": "fail", "executable": None, "detail": "missing"},
                )(),
            ),
        ):
            code = run_check(start=self.root, run_process=runner)

        self.assertEqual(code, 1)
        self.assertTrue(any(command[1:3] == ("-m", "pytest") for command in executed))
        self.assertFalse(any("--headless" in command for command in executed))

    def test_returns_failure_when_doctor_fails(self) -> None:
        executed: list[tuple[str, ...]] = []

        def runner(command, _cwd):
            executed.append(tuple(command))
            return 0

        with (
            patch("g2dtool.check.discover_repository_layout", return_value=self.layout),
            patch(
                "g2dtool.check.collect_doctor_report",
                return_value=DoctorReport((DoctorCheck("repository", "fail", "broken"),)),
            ),
            patch(
                "g2dtool.check.discover_godot",
                return_value=type(
                    "GodotResult",
                    (),
                    {"status": "pass", "executable": Path("/fake/godot4")},
                )(),
            ),
        ):
            code = run_check(start=self.root, run_process=runner)

        self.assertEqual(code, 1)
        self.assertTrue(any(command[1:3] == ("-m", "pytest") for command in executed))
        self.assertTrue(any("--import" in command for command in executed))
        self.assertTrue(any("--script" in command for command in executed))

    def test_returns_failure_when_python_tests_fail(self) -> None:
        executed: list[tuple[str, ...]] = []

        def runner(command, _cwd):
            executed.append(tuple(command))
            return 3 if tuple(command[1:3]) == ("-m", "pytest") else 0

        with (
            patch("g2dtool.check.discover_repository_layout", return_value=self.layout),
            patch(
                "g2dtool.check.collect_doctor_report",
                return_value=DoctorReport((DoctorCheck("repository", "pass", "ok"),)),
            ),
            patch(
                "g2dtool.check.discover_godot",
                return_value=type(
                    "GodotResult",
                    (),
                    {"status": "pass", "executable": Path("/fake/godot4")},
                )(),
            ),
        ):
            code = run_check(start=self.root, run_process=runner)

        self.assertEqual(code, 1)
        self.assertTrue(any("--import" in command for command in executed))
        self.assertTrue(any("--script" in command for command in executed))

    def test_returns_failure_after_running_remaining_steps_when_style_fails(self) -> None:
        executed: list[tuple[str, ...]] = []

        def runner(command, _cwd):
            executed.append(tuple(command))
            return 0

        with (
            patch("g2dtool.check.discover_repository_layout", return_value=self.layout),
            patch(
                "g2dtool.check.collect_doctor_report",
                return_value=DoctorReport((DoctorCheck("repository", "pass", "ok"),)),
            ),
            patch("g2dtool.check.run_style", return_value=5) as source_style,
            patch(
                "g2dtool.check.discover_godot",
                return_value=type(
                    "GodotResult",
                    (),
                    {"status": "pass", "executable": Path("/fake/godot4")},
                )(),
            ),
        ):
            code = run_check(start=self.root, run_process=runner)

        self.assertEqual(code, 1)
        source_style.assert_called_once_with(start=self.root)
        self.assertTrue(any(command[1:3] == ("-m", "pytest") for command in executed))
        self.assertTrue(any("--import" in command for command in executed))
        self.assertTrue(any("--script" in command for command in executed))

    def test_returns_failure_when_godot_integration_test_fails(self) -> None:
        executed: list[tuple[str, ...]] = []

        def runner(command, _cwd):
            executed.append(tuple(command))
            return 7 if "--script" in command else 0

        with (
            patch("g2dtool.check.discover_repository_layout", return_value=self.layout),
            patch(
                "g2dtool.check.collect_doctor_report",
                return_value=DoctorReport((DoctorCheck("repository", "pass", "ok"),)),
            ),
            patch(
                "g2dtool.check.discover_godot",
                return_value=type(
                    "GodotResult",
                    (),
                    {"status": "pass", "executable": Path("/fake/godot4")},
                )(),
            ),
        ):
            code = run_check(start=self.root, run_process=runner)

        self.assertEqual(code, 1)
        self.assertTrue(any("--import" in command for command in executed))
        self.assertTrue(any("--script" in command for command in executed))

    def test_failed_import_skips_script_and_fails_once_at_the_dependency(self) -> None:
        executed: list[tuple[str, ...]] = []

        def runner(command, _cwd):
            executed.append(tuple(command))
            return 17 if "--import" in command else 0

        output = StringIO()
        with (
            patch("g2dtool.check.discover_repository_layout", return_value=self.layout),
            patch(
                "g2dtool.check.collect_doctor_report",
                return_value=DoctorReport((DoctorCheck("repository", "pass", "ok"),)),
            ),
            patch(
                "g2dtool.check.discover_godot",
                return_value=type(
                    "GodotResult",
                    (),
                    {"status": "pass", "executable": Path("/fake/godot4")},
                )(),
            ),
            redirect_stdout(output),
        ):
            code = run_check(start=self.root, run_process=runner)

        self.assertEqual(code, 1)
        self.assertTrue(any("--import" in command for command in executed))
        self.assertFalse(any("--script" in command for command in executed))
        self.assertEqual(output.getvalue().count(GODOT_INTEGRATION_IMPORT_SKIP_MESSAGE), 1)
        self.assertIn("Godot resource import failed with exit code 17", output.getvalue())

    def test_returns_failure_when_godot_test_runner_is_missing(self) -> None:
        self.test_runner.unlink()
        executed: list[tuple[str, ...]] = []

        def runner(command, _cwd):
            executed.append(tuple(command))
            return 0

        with (
            patch("g2dtool.check.discover_repository_layout", return_value=self.layout),
            patch(
                "g2dtool.check.collect_doctor_report",
                return_value=DoctorReport((DoctorCheck("repository", "pass", "ok"),)),
            ),
            patch(
                "g2dtool.check.discover_godot",
                return_value=type(
                    "GodotResult",
                    (),
                    {"status": "pass", "executable": Path("/fake/godot4")},
                )(),
            ),
        ):
            code = run_check(start=self.root, run_process=runner)

        self.assertEqual(code, 1)
        self.assertTrue(any(command[1:3] == ("-m", "pytest") for command in executed))
        self.assertTrue(any("--import" in command for command in executed))
        self.assertFalse(any("--script" in command for command in executed))

    def test_godot_runner_requires_explicit_success_marker(self) -> None:
        command = ["/fake/godot4", "--headless"]
        completed = subprocess.CompletedProcess(command, 0, "", "SCRIPT ERROR: Parse Error")

        with patch("g2dtool.check.subprocess.run", return_value=completed):
            code = _run_godot_integration_test(command, self.root)

        self.assertEqual(code, 1)

    def test_godot_runner_accepts_explicit_success_marker(self) -> None:
        command = ["/fake/godot4", "--headless"]
        completed = subprocess.CompletedProcess(
            command,
            0,
            f"{GODOT_TEST_SUCCESS_MARKER}\n",
            "",
        )

        with patch("g2dtool.check.subprocess.run", return_value=completed):
            code = _run_godot_integration_test(command, self.root)

        self.assertEqual(code, 0)

    def test_release_gate_uses_marker_validating_runner_by_default(self) -> None:
        with (
            patch("g2dtool.check.discover_repository_layout", return_value=self.layout),
            patch(
                "g2dtool.check.collect_doctor_report",
                return_value=DoctorReport((DoctorCheck("repository", "pass", "ok"),)),
            ),
            patch("g2dtool.check._run_process", return_value=0),
            patch(
                "g2dtool.check.discover_godot",
                return_value=type(
                    "GodotResult",
                    (),
                    {"status": "pass", "executable": Path("/fake/godot4")},
                )(),
            ),
            patch(
                "g2dtool.check._run_godot_integration_test",
                return_value=1,
            ) as godot_runner,
        ):
            code = run_check(start=self.root)

        self.assertEqual(code, 1)
        godot_runner.assert_called_once()


if __name__ == "__main__":
    unittest.main()
