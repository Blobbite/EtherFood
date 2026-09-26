"""Tests for Godot discovery and command generation."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from g2dtool.godot import (
    FAIL,
    GODOT_RESOURCE_IMPORT_TIMEOUT_SECONDS,
    PASS,
    CommandResult,
    GodotTestConfigurationError,
    build_godot_editor_command,
    build_godot_import_command,
    build_godot_run_command,
    build_godot_test_command,
    discover_godot,
    run_godot_command,
)

from _source_path import add_source_root

add_source_root()

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class GodotTests(unittest.TestCase):
    def test_discovery_prefers_explicit_binary_over_env_and_candidates(self) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_finder(name: str) -> str | None:
            if name == "godot4":
                return "/opt/godot4"
            if name == "godot":
                return "/usr/local/bin/godot"
            return None

        def run_command(arguments):
            command = tuple(arguments)
            calls.append(command)
            return CommandResult(0, "4.4.stable\n", "")

        with tempfile.TemporaryDirectory() as temporary_directory:
            explicit = Path(temporary_directory) / "explicit-godot"
            explicit.write_text("", encoding="utf-8")
            result = discover_godot(
                REPOSITORY_ROOT,
                explicit_binary=str(explicit),
                find_tool=fake_finder,
                run_command=run_command,
            )
        self.assertEqual(result.status, PASS)
        self.assertEqual(calls[0][0], str(explicit))

    def test_discovery_uses_env_variables(self) -> None:
        def fake_finder(name: str) -> str | None:
            return {
                "godot4": "/godot4-env",
                "godot": "/godot-env",
            }.get(name)

        calls: list[tuple[str, ...]] = []

        def run_command(arguments):
            calls.append(tuple(arguments))
            return CommandResult(0, "4.4.stable\n", "")

        result = discover_godot(
            REPOSITORY_ROOT,
            find_tool=fake_finder,
            environment={"GODOT4_BIN": "/godot4-env", "GODOT_BIN": "/godot-env"},
            run_command=run_command,
        )
        self.assertEqual(result.status, PASS)
        self.assertEqual(calls[0][0], str(Path("/godot4-env")))

    def test_discovery_parses_prefixed_version_output(self) -> None:
        calls: list[tuple[str, ...]] = []

        def run_command(arguments):
            calls.append(tuple(arguments))
            return CommandResult(0, "Godot Engine v4.4.stable.official.0f4a4f8af2", "")

        with tempfile.TemporaryDirectory() as temporary_directory:
            fake_godot = Path(temporary_directory) / "godot4"
            fake_godot.write_text("", encoding="utf-8")
            result = discover_godot(
                REPOSITORY_ROOT,
                find_tool=lambda name: str(fake_godot) if name == "godot4" else None,
                run_command=run_command,
            )
        self.assertEqual(result.status, PASS)
        self.assertIn("4", result.version)

    def test_discovery_accepts_godot_version_on_non_zero_exit(self) -> None:
        calls: list[tuple[str, ...]] = []

        def run_command(arguments):
            calls.append(tuple(arguments))
            return CommandResult(1, "Godot Engine v4.7.2.stable", "")

        with tempfile.TemporaryDirectory() as temporary_directory:
            fake_godot = Path(temporary_directory) / "godot4"
            fake_godot.write_text("", encoding="utf-8")
            result = discover_godot(
                REPOSITORY_ROOT,
                find_tool=lambda name: str(fake_godot) if name == "godot4" else None,
                run_command=run_command,
            )

        self.assertEqual(result.status, PASS)
        self.assertEqual(result.version, "Godot Engine v4.7.2.stable")
        self.assertEqual(calls[0][0], str(fake_godot))

    def test_discovery_ignores_runtime_linker_noise_when_extracting_version(self) -> None:
        calls: list[tuple[str, ...]] = []

        def run_command(arguments):
            calls.append(tuple(arguments))
            return CommandResult(
                1,
                "",
                "/usr/bin/godot: /usr/lib/libm.so.6: version `GLIBC_2.44' "
                "not found (required by /usr/bin/godot)",
            )

        with tempfile.TemporaryDirectory() as temporary_directory:
            fake_godot = Path(temporary_directory) / "godot4"
            fake_godot.write_text("", encoding="utf-8")
            result = discover_godot(
                REPOSITORY_ROOT,
                find_tool=lambda name: str(fake_godot) if name == "godot4" else None,
                run_command=run_command,
            )

        self.assertEqual(result.status, FAIL)
        self.assertIsNone(result.version)
        self.assertIn("Godot 4 was not found", result.detail)
        self.assertIn("runtime library mismatch", result.detail.lower())
        self.assertEqual(calls[0][0], str(fake_godot))

    def test_detects_fallback_candidates(self) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_finder(name: str) -> str | None:
            return {
                "godot4": "/fallback/godot4",
                "godot": "/fallback/godot",
            }.get(name)

        def run_command(arguments):
            calls.append(tuple(arguments))
            return CommandResult(0, "4.3.stable\n", "")

        result = discover_godot(
            REPOSITORY_ROOT,
            find_tool=fake_finder,
            run_command=run_command,
        )
        self.assertEqual(result.status, PASS)
        self.assertEqual(calls[0][0], str(Path("/fallback/godot4")))

    def test_command_construction(self) -> None:
        game = REPOSITORY_ROOT / "game"
        executable = Path("/usr/bin/godot")
        test_runner = game / "test_scenes" / "helpers" / "bootstrap_integration_test.gd"

        self.assertEqual(
            build_godot_editor_command(executable, game),
            [str(executable), "--editor", "--path", str(game)],
        )
        self.assertEqual(
            build_godot_run_command(executable, game, ["--foo"]),
            [str(executable), "--path", str(game), "--", "--foo"],
        )
        self.assertEqual(
            build_godot_run_command(executable, game, ["--", "--foo"]),
            [str(executable), "--path", str(game), "--", "--foo"],
        )
        self.assertEqual(
            build_godot_test_command(executable, game, ["--foo"]),
            [
                str(executable),
                "--headless",
                "--path",
                str(game),
                "--script",
                str(test_runner),
                "--",
                "--foo",
            ],
        )

    def test_import_command_is_headless_exact_and_has_no_game_arguments(self) -> None:
        executable = Path("/opt/godot/bin/godot4")
        game = Path("/checkout/EtherFood/game")

        command = build_godot_import_command(executable, game)

        self.assertEqual(
            command,
            [
                str(executable),
                "--headless",
                "--path",
                str(game),
                "--import",
            ],
        )
        self.assertNotIn("--player-name", command)
        self.assertNotIn("--", command)

    def test_runner_preserves_import_exit_code_and_uses_bounded_timeout(self) -> None:
        command = ["/opt/godot4", "--headless", "--import"]
        completed = type("Completed", (), {"returncode": 23})()

        with patch("g2dtool.godot.subprocess.run", return_value=completed) as runner:
            exit_code = run_godot_command(
                command,
                timeout_seconds=GODOT_RESOURCE_IMPORT_TIMEOUT_SECONDS,
            )

        self.assertEqual(exit_code, 23)
        runner.assert_called_once_with(
            command,
            check=False,
            timeout=GODOT_RESOURCE_IMPORT_TIMEOUT_SECONDS,
        )

    def test_test_command_rejects_missing_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            game = Path(temporary_directory) / "game"
            game.mkdir()
            with self.assertRaisesRegex(GodotTestConfigurationError, "test runner is missing"):
                build_godot_test_command(Path("/usr/bin/godot"), game)
