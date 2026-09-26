"""Verify Godot test boundaries and release resource exclusions."""

from configparser import ConfigParser
from fnmatch import fnmatchcase
from pathlib import Path
import re
import unittest


GAME_ROOT = Path(__file__).resolve().parents[2] / "game"
ASSET_CATEGORIES = {
    "characters", "environment", "props", "items", "effects", "ui", "audio",
    "fonts", "shaders", "materials", "lighting", "cinematics",
}


class AssetLayoutTests(unittest.TestCase):
    def test_final_and_test_assets_share_the_prepared_categories(self) -> None:
        for area in ("assets", "test_assets"):
            with self.subTest(area=area):
                root = GAME_ROOT / area
                self.assertEqual({path.name for path in root.iterdir()}, ASSET_CATEGORIES)
                for kind in ("sprites", "spritesheets"):
                    for action in ("idle", "walk", "run", "sprint", "jump"):
                        self.assertTrue(
                            (root / "characters/heroes/greenhero" / kind / action).is_dir(),
                        )

    def test_test_content_stays_importable_and_has_no_raw_source_archives(self) -> None:
        self.assertFalse((GAME_ROOT / "tests").exists())
        for area in ("test_assets", "test_scenes"):
            root = GAME_ROOT / area
            self.assertEqual(list(root.rglob(".gdignore")), [])
            self.assertEqual(list(root.rglob("sources")), [])

    def test_resource_references_resolve_after_migration(self) -> None:
        for path in GAME_ROOT.rglob("*"):
            if ".godot" in path.parts or path.suffix not in {".tscn", ".tres", ".import"}:
                continue
            contents = path.read_text(encoding="utf-8")
            references = re.findall(r'(?:path|source_file)="res://([^\"]+)"', contents)
            for reference in references:
                if reference.startswith(".godot/"):
                    continue
                with self.subTest(file=path.relative_to(GAME_ROOT), reference=reference):
                    self.assertTrue((GAME_ROOT / reference).is_file())

    def test_production_resources_do_not_load_test_dependencies(self) -> None:
        pattern = re.compile(
            r'(?:\bpath\s*=\s*|\b(?:preload|load)\s*\(\s*)'
            r'"res://(?:test_assets|test_scenes|tests)/',
        )
        for area in ("assets", "scenes", "services", "shared", "src"):
            for path in (GAME_ROOT / area).rglob("*"):
                if path.suffix not in {".gd", ".tscn", ".tres"}:
                    continue
                with self.subTest(file=path.relative_to(GAME_ROOT)):
                    self.assertIsNone(pattern.search(path.read_text(encoding="utf-8")))

    def test_all_release_presets_exclude_current_and_future_test_content(self) -> None:
        config = ConfigParser(interpolation=None)
        config.read(GAME_ROOT / "export_presets.cfg", encoding="utf-8")
        presets = [section for section in config if re.fullmatch(r"preset\.\d+", section)]
        self.assertEqual(len(presets), 3)
        excluded_paths = [
            path.relative_to(GAME_ROOT).as_posix()
            for area in ("test_assets", "test_scenes", "tools")
            for path in (GAME_ROOT / area).rglob("*") if path.is_file()
        ]
        excluded_paths.extend((
            "test_assets/environment/new/future.png",
            "test_scenes/audio/new/future.tscn",
            "tests/future_test.gd",
            "PERSOENLICHE_ASSET_UMSTELLUNG.md",
        ))
        for preset in presets:
            filters = config[preset]["exclude_filter"].strip('"').split(",")
            for relative in excluded_paths:
                with self.subTest(preset=preset, excluded=relative):
                    self.assertTrue(any(fnmatchcase(relative, item) for item in filters))
            for relative in ("scenes/bootstrap.tscn", "assets/environment/future.png"):
                with self.subTest(preset=preset, included=relative):
                    self.assertFalse(any(fnmatchcase(relative, item) for item in filters))


if __name__ == "__main__":
    unittest.main()
