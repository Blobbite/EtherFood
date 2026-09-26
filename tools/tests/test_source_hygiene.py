"""Tests for machine-independent paths in repository source."""

from pathlib import Path
import re
import subprocess
import unittest
from urllib.parse import unquote


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    REPOSITORY_ROOT / "config",
    REPOSITORY_ROOT / "game",
    REPOSITORY_ROOT / "tools" / "src",
)
SOURCE_SUFFIXES = {".gd", ".godot", ".py", ".toml", ".tscn"}
USER_PATH_PATTERNS = (
    re.compile("/" + r"home/[A-Za-z0-9._-]+/"),
    re.compile("/" + r"Users/[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
)
RUNTIME_PATHS = (
    REPOSITORY_ROOT / "game" / "features",
    REPOSITORY_ROOT / "game" / "scenes",
    REPOSITORY_ROOT / "game" / "services",
    REPOSITORY_ROOT / "game" / "shared",
    REPOSITORY_ROOT / "game" / "src",
    REPOSITORY_ROOT / "game" / "test_scenes" / "characters",
    REPOSITORY_ROOT / "game" / "test_scenes" / "environment",
    REPOSITORY_ROOT / "game" / "test_scenes" / "visual_lab",
)
DOCUMENTATION_ENTRY_POINTS = (
    REPOSITORY_ROOT / "README.md",
    REPOSITORY_ROOT / "AGENTS.md",
    REPOSITORY_ROOT / "CONTRIBUTING.md",
)


class SourceHygieneTests(unittest.TestCase):
    def test_source_and_configuration_have_no_hard_coded_user_paths(self) -> None:
        violations: list[str] = []
        files = [REPOSITORY_ROOT / "pyproject.toml"]
        for source_path in SOURCE_PATHS:
            if source_path.exists():
                files.extend(
                    path
                    for path in source_path.rglob("*")
                    if path.is_file() and path.suffix in SOURCE_SUFFIXES
                )

        for path in files:
            contents = path.read_text(encoding="utf-8")
            if any(pattern.search(contents) for pattern in USER_PATH_PATTERNS):
                violations.append(path.relative_to(REPOSITORY_ROOT).as_posix())

        self.assertEqual(violations, [])

    def test_source_does_not_use_shell_true(self) -> None:
        targets = (
            REPOSITORY_ROOT / "tools" / "src" / "g2dtool" / "cli.py",
            REPOSITORY_ROOT / "tools" / "src" / "g2dtool" / "doctor.py",
            REPOSITORY_ROOT / "tools" / "src" / "g2dtool" / "install.py",
            REPOSITORY_ROOT / "tools" / "src" / "g2dtool" / "godot.py",
            REPOSITORY_ROOT / "tools" / "src" / "g2dtool" / "export.py",
            REPOSITORY_ROOT / "tools" / "src" / "g2dtool" / "release.py",
        )
        for target in targets:
            self.assertNotIn("shell=True", target.read_text(encoding="utf-8"))

    def test_source_does_not_use_break_system_packages(self) -> None:
        targets = (
            REPOSITORY_ROOT / "tools" / "src" / "g2dtool" / "install.py",
            REPOSITORY_ROOT / "tools" / "src" / "g2dtool" / "cli.py",
            REPOSITORY_ROOT / "tools" / "src" / "g2dtool" / "doctor.py",
        )
        for target in targets:
            self.assertNotIn("--break-system-packages", target.read_text(encoding="utf-8"))

    def test_godot_generated_cache_stays_untracked_and_ignored(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "--", "game/.godot/**", "*.ctex"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(tracked.returncode, 0, tracked.stderr)
        self.assertEqual(tracked.stdout, "")

        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", "game/.godot/imported/probe.ctex"],
            cwd=REPOSITORY_ROOT,
            check=False,
        )
        self.assertEqual(ignored.returncode, 0)
        ignore_file = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("\n.godot/\n", f"\n{ignore_file}")

    def test_runtime_has_no_direct_global_scene_changes(self) -> None:
        violations = self._gdscript_violations(
            re.compile(r"\bchange_scene_(?:to_file|to_packed)\s*\(")
        )
        self.assertEqual(violations, [])

    def test_runtime_has_no_physical_input_codes(self) -> None:
        patterns = (
            re.compile(r"\bInput\.is_(?:key|physical_key)_pressed\s*\("),
            re.compile(r"\bInput\.is_mouse_button_pressed\s*\("),
            re.compile(
                r"\bInputEvent(?:Key|JoypadButton|JoypadMotion|MouseButton|"
                r"MouseMotion|ScreenTouch|ScreenDrag|MagnifyGesture|PanGesture)\b"
            ),
            re.compile(
                r"\b(?:KEY|JOY_BUTTON|JOY_AXIS|MOUSE_BUTTON)_[A-Z0-9_]+\b"
            ),
        )
        violations: list[str] = []
        for pattern in patterns:
            violations.extend(self._gdscript_violations(pattern))
        self.assertEqual(sorted(set(violations)), [])

    def test_runtime_has_no_fixed_viewport_constants(self) -> None:
        violations = self._gdscript_violations(
            re.compile(r"(?<![0-9])(?:960|540)(?![0-9])")
        )
        self.assertEqual(violations, [])

    def test_runtime_has_no_forbidden_global_service_types(self) -> None:
        forbidden = re.compile(
            r"\b(?:class_name\s+)?(?:EventBus|ServiceLocator|GameState)\b"
        )
        violations = self._gdscript_violations(forbidden)
        self.assertEqual(violations, [])

    def test_features_do_not_import_other_features(self) -> None:
        features_root = REPOSITORY_ROOT / "game" / "features"
        violations: list[str] = []
        if features_root.exists():
            for path in features_root.rglob("*.gd"):
                feature_name = path.relative_to(features_root).parts[0]
                contents = path.read_text(encoding="utf-8")
                for imported_feature in re.findall(
                    r'res://features/([^/"\']+)/', contents
                ):
                    if imported_feature != feature_name:
                        violations.append(path.relative_to(REPOSITORY_ROOT).as_posix())
        self.assertEqual(violations, [])

    def test_documentation_relative_links_resolve(self) -> None:
        violations: list[str] = []
        docs_root = REPOSITORY_ROOT / "docs"
        markdown_link_pattern = re.compile(r"!?\[[^]]+\]\(([^)]+)\)")
        html_source_pattern = re.compile(r"<(?:img|source)\b[^>]*\bsrc=\"([^\"]+)\"")
        paths = sorted(
            path
            for path in docs_root.rglob("*.md")
            if ".summary" not in path.parts
        ) + [
            path for path in DOCUMENTATION_ENTRY_POINTS if path.exists()
        ]
        for path in paths:
            contents = path.read_text(encoding="utf-8")
            targets = markdown_link_pattern.findall(contents)
            targets.extend(html_source_pattern.findall(contents))
            for target in targets:
                target = target.strip().strip("<>").split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (path.parent / unquote(target)).resolve()
                if not resolved.exists():
                    relative_path = path.relative_to(REPOSITORY_ROOT).as_posix()
                    violations.append(f"{relative_path} -> {target}")
        self.assertEqual(violations, [])

    def test_documentation_architecture_has_three_top_level_areas(self) -> None:
        required_paths = (
            "docs/index.md",
            "docs/system/index.md",
            "docs/system/.forge2d-template/index.md",
            "docs/system/.forge2d-template/forge2d-template.md",
            "docs/system/.forge2d-template/tooling/installation.md",
            "docs/system/.forge2d-template/tooling/gdscript-style-guide.md",
            "docs/system/.forge2d-template/tooling/python-style-guide.md",
            "docs/system/.forge2d-template/architecture/runtime-overview.md",
            "docs/system/development/index.md",
            "docs/system/development/documentation-architecture.md",
            "docs/system/development/project-identity.md",
            "docs/system/development/plans/dokumentationsstruktur-system-game-release.md",
            "docs/system/development/plans/godot-resource-import-pipeline.md",
            "docs/system/development/features/_feature-template.md",
            "docs/system/development/decisions/_adr-template.md",
            "docs/system/development/plans/_execplan-template.md",
            "docs/system/development/tooling/index.md",
            "docs/system/development/tooling/godot-resource-imports.md",
            "docs/game/index.md",
            "docs/game/canon/index.md",
            "docs/game/canon/grundlagen/kanon-und-offene-fragen.md",
            "docs/game/canon/welt/zeit/zeitrechnung-auf-era.md",
            "docs/game/canon/welt/zeit/zeitzyklen-und-konvektion.md",
            "docs/game/canon/handlung/ratgeber-im-heldenraum.md",
            "docs/game/canon/handlung/talisman.md",
            "docs/game/design/index.md",
            "docs/game/design/spielvision.md",
            "docs/game/design/zeitdarstellung-im-spiel.md",
            "docs/game/design/inhalte/spielablauf-und-abschnittsstruktur.md",
            "docs/game/concept/index.md",
            "docs/game/decisions/index.md",
            "docs/game/decisions/ADR-0008-achtteiliger-spielablauf.md",
            "docs/game/reference/index.md",
            "docs/game/reference/animations/index.md",
            "docs/release/index.md",
            "docs/release/roadmap.md",
            "docs/release/player-guide/index.md",
            "docs/release/player-guide/_topic-template.md",
            "docs/release/studies/index.md",
        )
        missing = [
            path for path in required_paths if not (REPOSITORY_ROOT / path).is_file()
        ]
        self.assertEqual(missing, [])

        developer_index = (
            REPOSITORY_ROOT / "docs" / "system" / "development" / "index.md"
        )
        self.assertIn(
            "../.forge2d-template/index.md",
            developer_index.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "Forge2D-Grundlage",
            developer_index.read_text(encoding="utf-8"),
        )

        root_readme = (REPOSITORY_ROOT / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "[System – Technik und Entwicklung](docs/system/index.md)",
            root_readme,
        )
        self.assertIn("[EtherFood – Spiel](docs/game/index.md)", root_readme)
        self.assertIn("[Release](docs/release/index.md)", root_readme)

        docs_root = REPOSITORY_ROOT / "docs"
        top_level_directories = {
            path.name for path in docs_root.iterdir() if path.is_dir()
        }
        self.assertEqual(top_level_directories, {"game", "release", "system"})

        legacy_areas = (
            "assets",
            "concept",
            "developer",
            "player-guide",
            "reference",
            ".case-studies",
            ".forge2d-template",
        )
        self.assertFalse(any((docs_root / name).exists() for name in legacy_areas))

        legacy_entry_points = (
            docs_root / "README.md",
            docs_root / "system" / "development" / "developer.md",
            docs_root / "release" / "player-guide" / "player-guide.md",
        )
        self.assertFalse(any(path.exists() for path in legacy_entry_points))

    def test_active_tooling_area_has_one_index_entry_point(self) -> None:
        tooling_root = (
            REPOSITORY_ROOT / "docs" / "system" / "development" / "tooling"
        )
        index_pages = sorted(
            path.relative_to(tooling_root) for path in tooling_root.rglob("index.md")
        )

        self.assertEqual(index_pages, [Path("index.md")])
        self.assertFalse((tooling_root / "tooling.md").exists())
        contents = (tooling_root / "index.md").read_text(encoding="utf-8")
        self.assertEqual(contents.count("<!-- PYGINDEX:NAVIGATION START -->"), 1)
        self.assertEqual(contents.count("<!-- PYGINDEX:NAVIGATION END -->"), 1)

    def test_game_directories_with_markdown_have_pygindex_pages(self) -> None:
        game_root = REPOSITORY_ROOT / "docs" / "game"
        directories = {game_root}
        for markdown_path in game_root.rglob("*.md"):
            directory = markdown_path.parent
            while directory == game_root or game_root in directory.parents:
                directories.add(directory)
                if directory == game_root:
                    break
                directory = directory.parent

        for directory in sorted(directories):
            with self.subTest(directory=directory.relative_to(REPOSITORY_ROOT)):
                overview = directory / "index.md"
                self.assertTrue(overview.is_file())
                contents = overview.read_text(encoding="utf-8")
                self.assertEqual(
                    contents.count("<!-- PYGINDEX:NAVIGATION START -->"),
                    1,
                )
                self.assertEqual(
                    contents.count("<!-- PYGINDEX:NAVIGATION END -->"),
                    1,
                )
                legacy_overview = directory / f"{directory.name}.md"
                self.assertFalse(legacy_overview.exists())

    def test_game_declares_binding_sources_and_nonbinding_concepts(self) -> None:
        game_index = (
            REPOSITORY_ROOT / "docs" / "game" / "index.md"
        ).read_text(encoding="utf-8")
        concept_index = (
            REPOSITORY_ROOT / "docs" / "game" / "concept" / "index.md"
        ).read_text(encoding="utf-8")
        architecture = (
            REPOSITORY_ROOT
            / "docs"
            / "system"
            / "development"
            / "documentation-architecture.md"
        ).read_text(encoding="utf-8")

        self.assertIn("einzigen aktuellen Quellen", game_index)
        self.assertIn("weder Kanon noch geltendes Gamedesign", concept_index)
        self.assertIn("aktive Projektdokumentation ist deutsch", architecture)
        self.assertNotIn("translation_status", game_index)

    def test_installer_completion_report_is_indexed_and_traceable(self) -> None:
        reports_root = (
            REPOSITORY_ROOT
            / "docs"
            / "system"
            / ".forge2d-template"
            / "reports"
        )
        report_path = reports_root / "M06_cross_platform_installer.md"
        report = report_path.read_text(encoding="utf-8")
        reports_index = (reports_root / "reports.md").read_text(encoding="utf-8")
        template_index = (
            REPOSITORY_ROOT
            / "docs"
            / "system"
            / ".forge2d-template"
            / "forge2d-template.md"
        ).read_text(encoding="utf-8")

        self.assertIn("(M06_cross_platform_installer.md)", reports_index)
        self.assertIn(
            "(reports/M06_cross_platform_installer.md)",
            template_index,
        )
        self.assertIn("../plans/M06_cross_platform_installer.md", report)
        self.assertIn("../tooling/installation.md", report)
        self.assertIn("33161920298", report)
        self.assertIn("## Remaining Limitations and Follow-up", report)

    def test_mermaid_fences_are_balanced(self) -> None:
        violations: list[str] = []
        docs_root = REPOSITORY_ROOT / "docs"
        for path in docs_root.rglob("*.md"):
            in_mermaid = False
            for line in path.read_text(encoding="utf-8").splitlines():
                marker = line.strip()
                if marker == "```mermaid":
                    if in_mermaid:
                        violations.append(path.relative_to(REPOSITORY_ROOT).as_posix())
                    in_mermaid = True
                elif marker == "```" and in_mermaid:
                    in_mermaid = False
            if in_mermaid:
                violations.append(path.relative_to(REPOSITORY_ROOT).as_posix())
        self.assertEqual(sorted(set(violations)), [])

    @staticmethod
    def _gdscript_violations(pattern: re.Pattern[str]) -> list[str]:
        violations: list[str] = []
        for runtime_path in RUNTIME_PATHS:
            if not runtime_path.exists():
                continue
            for path in runtime_path.rglob("*.gd"):
                if pattern.search(path.read_text(encoding="utf-8")):
                    violations.append(path.relative_to(REPOSITORY_ROOT).as_posix())
        return violations


if __name__ == "__main__":
    unittest.main()
