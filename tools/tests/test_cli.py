"""Tests for CLI behavior and command dispatch."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

from _source_path import add_source_root

add_source_root()

from g2dtool.cli import WELCOME_TEXT, main
from g2dtool.godot import GODOT_RESOURCE_IMPORT_TIMEOUT_SECONDS
from g2dtool import __version__
from g2dtool.repository import RepositoryLayout


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class CliTests(unittest.TestCase):
    def test_help_contains_control_examples(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as context:
                main(["--help"], prog="python tools/control.py")

        self.assertEqual(context.exception.code, 0)
        text = output.getvalue()
        self.assertIn("python tools/control.py doctor", text)
        self.assertIn("python tools/control.py style", text)
        self.assertIn("python tools/control.py export linux --dry-run", text)
        self.assertIn("python tools/control.py release prepare --dry-run", text)
        self.assertIn("python tools/control.py godot4 import", text)
        self.assertIn("python tools/control.py godot4 test", text)
        self.assertIn("python tools/control.py Forge2D-Template run", text)

    def test_welcome_text_contains_resource_import_command(self) -> None:
        self.assertIn("python tools/control.py godot4 import", WELCOME_TEXT)

    def test_version_has_stable_output(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["version"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue().strip(), f"g2d {__version__}")

    def test_install_help_describes_dry_run_and_unattended_confirmation(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as context:
                main(["install", "--help"])

        self.assertEqual(context.exception.code, 0)
        text = output.getvalue()
        self.assertIn("without making changes", text)
        self.assertIn("unattended setup", text)

    def test_export_help_lists_targets_and_side_effect_free_dry_run(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as context:
                main(["export", "--help"])

        self.assertEqual(context.exception.code, 0)
        text = " ".join(output.getvalue().split())
        self.assertIn("{linux,windows,macos}", text)
        self.assertIn("without making changes", text)

    def test_invalid_command_uses_cli_error_code(self) -> None:
        with self.assertRaises(SystemExit) as context:
            main(["unknown"])
        self.assertEqual(context.exception.code, 2)

    def test_doctor_output_is_printed_and_exit_code_is_reported(self) -> None:
        with (
            patch(
                "g2dtool.cli.collect_doctor_report",
                return_value=type(
                    "report",
                    (),
                    {"exit_code": 1, "checks": ()},
                )(),
            ),
            patch("g2dtool.cli.format_doctor_report", return_value="DONE"),
            redirect_stdout(StringIO()) as output,
        ):
            exit_code = main(["doctor"])
            self.assertEqual(output.getvalue(), "DONE\n")

        self.assertEqual(exit_code, 1)

    def test_check_dispatches_release_gate(self) -> None:
        with patch("g2dtool.cli.run_check", return_value=0) as run_gate:
            exit_code = main(["check"])

        self.assertEqual(exit_code, 0)
        run_gate.assert_called_once_with()

    def test_style_dispatches_source_gate(self) -> None:
        with patch("g2dtool.cli.run_style", return_value=1) as run_source_style:
            exit_code = main(["style"])

        self.assertEqual(exit_code, 1)
        run_source_style.assert_called_once_with()

    def test_export_dispatches_selected_target_and_dry_run(self) -> None:
        with patch("g2dtool.cli.run_export", return_value=1) as export_command:
            exit_code = main(["export", "macos", "--dry-run"])

        self.assertEqual(exit_code, 1)
        export_command.assert_called_once_with("macos", dry_run=True)

    def test_export_rejects_unknown_target_as_usage_error(self) -> None:
        with self.assertRaises(SystemExit) as context:
            main(["export", "android"])

        self.assertEqual(context.exception.code, 2)

    def test_release_prepare_help_describes_side_effect_free_dry_run(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as context:
                main(["release", "prepare", "--help"])

        self.assertEqual(context.exception.code, 0)
        self.assertIn("without making changes", output.getvalue())

    def test_release_prepare_dispatches_dry_run(self) -> None:
        with patch(
            "g2dtool.cli.run_release_prepare",
            return_value=1,
        ) as release_prepare:
            exit_code = main(["release", "prepare", "--dry-run"])

        self.assertEqual(exit_code, 1)
        release_prepare.assert_called_once_with(dry_run=True)

    def test_release_requires_a_subcommand(self) -> None:
        with self.assertRaises(SystemExit) as context:
            main(["release"])

        self.assertEqual(context.exception.code, 2)

    def test_template_aliases_run_the_same_mode(self) -> None:
        layout = RepositoryLayout(
            repository_root=REPOSITORY_ROOT,
            pyproject_toml=REPOSITORY_ROOT / "pyproject.toml",
            project_config=REPOSITORY_ROOT / "config" / "project.toml",
            toolchain_config=REPOSITORY_ROOT / "config" / "toolchain.toml",
            tools_directory=REPOSITORY_ROOT / "tools",
            tools_source_directory=REPOSITORY_ROOT / "tools" / "src",
            game_directory=REPOSITORY_ROOT / "game",
            venv_directory=REPOSITORY_ROOT / ".venv",
        )
        with (
            patch("g2dtool.cli.discover_repository_layout", return_value=layout),
            patch(
                "g2dtool.cli.discover_godot",
                return_value=type(
                    "Result",
                    (),
                    {
                        "status": "pass",
                        "executable": Path("/fake/godot"),
                        "version": "4.3",
                    },
                )(),
            ),
            patch("g2dtool.cli.run_godot_command", return_value=0) as runner,
        ):
            exit_lower = main(["forge2d-template", "run"])
            exit_upper = main(["Forge2D-Template", "run"])

        self.assertEqual(exit_lower, 0)
        self.assertEqual(exit_upper, 0)
        self.assertEqual(runner.call_count, 4)
        for import_call, run_call in zip(runner.call_args_list[::2], runner.call_args_list[1::2]):
            self.assertIn("--import", import_call.args[0])
            self.assertEqual(
                import_call.kwargs,
                {"timeout_seconds": GODOT_RESOURCE_IMPORT_TIMEOUT_SECONDS},
            )
            self.assertNotIn("--import", run_call.args[0])
            self.assertNotIn("--script", run_call.args[0])

    def test_godot_import_dispatches_only_the_bounded_import_command(self) -> None:
        layout = self._layout()
        with (
            patch("g2dtool.cli.discover_repository_layout", return_value=layout),
            patch("g2dtool.cli.discover_godot", return_value=self._godot_result()),
            patch("g2dtool.cli.run_godot_command", return_value=0) as runner,
        ):
            exit_code = main(["godot4", "import"])

        self.assertEqual(exit_code, 0)
        runner.assert_called_once_with(
            [
                "/fake/godot",
                "--headless",
                "--path",
                str(layout.game_directory),
                "--import",
            ],
            timeout_seconds=GODOT_RESOURCE_IMPORT_TIMEOUT_SECONDS,
        )

    def test_godot_run_imports_first_and_preserves_game_arguments(self) -> None:
        layout = self._layout()
        with (
            patch("g2dtool.cli.discover_repository_layout", return_value=layout),
            patch("g2dtool.cli.discover_godot", return_value=self._godot_result()),
            patch("g2dtool.cli.run_godot_command", return_value=0) as runner,
        ):
            exit_code = main(["godot4", "run", "--", "--player-name", "Ada"])

        self.assertEqual(exit_code, 0)
        import_call, run_call = runner.call_args_list
        self.assertIn("--import", import_call.args[0])
        self.assertNotIn("--player-name", import_call.args[0])
        self.assertEqual(
            run_call,
            call(
                [
                    "/fake/godot",
                    "--path",
                    str(layout.game_directory),
                    "--",
                    "--player-name",
                    "Ada",
                ]
            ),
        )

    def test_godot_test_imports_first_and_preserves_test_arguments(self) -> None:
        layout = self._layout()
        test_runner = (
            layout.game_directory / "test_scenes" / "helpers" / "bootstrap_integration_test.gd"
        )
        with (
            patch("g2dtool.cli.discover_repository_layout", return_value=layout),
            patch("g2dtool.cli.discover_godot", return_value=self._godot_result()),
            patch("g2dtool.cli.run_godot_command", return_value=0) as runner,
        ):
            exit_code = main(["godot4", "test", "--", "--case", "bootstrap"])

        self.assertEqual(exit_code, 0)
        import_call, test_call = runner.call_args_list
        self.assertIn("--import", import_call.args[0])
        self.assertNotIn("--case", import_call.args[0])
        self.assertEqual(
            test_call,
            call(
                [
                    "/fake/godot",
                    "--headless",
                    "--path",
                    str(layout.game_directory),
                    "--script",
                    str(test_runner),
                    "--",
                    "--case",
                    "bootstrap",
                ]
            ),
        )

    def test_failed_import_returns_godot_code_and_prevents_target_process(self) -> None:
        layout = self._layout()
        with (
            patch("g2dtool.cli.discover_repository_layout", return_value=layout),
            patch("g2dtool.cli.discover_godot", return_value=self._godot_result()),
            patch("g2dtool.cli.run_godot_command", return_value=19) as runner,
        ):
            exit_code = main(["godot4", "test"])

        self.assertEqual(exit_code, 19)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("--import", runner.call_args.args[0])

    def test_editor_starts_once_without_a_preparatory_import(self) -> None:
        layout = self._layout()
        with (
            patch("g2dtool.cli.discover_repository_layout", return_value=layout),
            patch("g2dtool.cli.discover_godot", return_value=self._godot_result()),
            patch("g2dtool.cli.run_godot_command", return_value=0) as runner,
        ):
            exit_code = main(["godot4", "editor", "--", "--editor-pseudolocalization"])

        self.assertEqual(exit_code, 0)
        runner.assert_called_once()
        command = runner.call_args.args[0]
        self.assertIn("--editor", command)
        self.assertNotIn("--import", command)
        self.assertIn("--editor-pseudolocalization", command)

    def test_missing_godot_prints_install_guidance(self) -> None:
        layout = RepositoryLayout(
            repository_root=REPOSITORY_ROOT,
            pyproject_toml=REPOSITORY_ROOT / "pyproject.toml",
            project_config=REPOSITORY_ROOT / "config" / "project.toml",
            toolchain_config=REPOSITORY_ROOT / "config" / "toolchain.toml",
            tools_directory=REPOSITORY_ROOT / "tools",
            tools_source_directory=REPOSITORY_ROOT / "tools" / "src",
            game_directory=REPOSITORY_ROOT / "game",
            venv_directory=REPOSITORY_ROOT / ".venv",
        )
        with (
            patch("g2dtool.cli.discover_repository_layout", return_value=layout),
            patch(
                "g2dtool.cli.discover_godot",
                return_value=type(
                    "Result",
                    (),
                    {
                        "status": "fail",
                        "executable": None,
                        "version": None,
                    },
                )(),
            ),
        ):
            from io import StringIO
            from contextlib import redirect_stdout
            output = StringIO()

            with redirect_stdout(output):
                exit_code = main(["godot4", "run"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Godot 4 wurde nicht gefunden.", output.getvalue())
        self.assertIn("python tools/control.py install", output.getvalue())

    def test_generic_exception_is_logged(self) -> None:
        def handler(_options: object) -> int:
            raise RuntimeError("unexpected internal failure")

        class FakeParser:
            def parse_args(
                self,
                _arguments: list[str] | None = None,
                _prog: str | None = None,
            ) -> SimpleNamespace:
                return SimpleNamespace(handler=handler)

        with (
            patch("g2dtool.cli.build_parser", return_value=FakeParser()),
            patch("g2dtool.cli.error") as log_error,
        ):
            exit_code = main(["version"])

        log_error.assert_called_once_with(
            "Internal error: unexpected internal failure"
        )
        self.assertEqual(exit_code, 1)

    @staticmethod
    def _layout() -> RepositoryLayout:
        return RepositoryLayout(
            repository_root=REPOSITORY_ROOT,
            pyproject_toml=REPOSITORY_ROOT / "pyproject.toml",
            project_config=REPOSITORY_ROOT / "config" / "project.toml",
            toolchain_config=REPOSITORY_ROOT / "config" / "toolchain.toml",
            tools_directory=REPOSITORY_ROOT / "tools",
            tools_source_directory=REPOSITORY_ROOT / "tools" / "src",
            game_directory=REPOSITORY_ROOT / "game",
            venv_directory=REPOSITORY_ROOT / ".venv",
        )

    @staticmethod
    def _godot_result() -> object:
        return type(
            "Result",
            (),
            {
                "status": "pass",
                "executable": Path("/fake/godot"),
                "version": "4.3",
            },
        )()
