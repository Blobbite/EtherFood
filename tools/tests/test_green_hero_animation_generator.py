"""Tests for the deterministic Green Hero animation package generator."""

from importlib import util
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GAME_ROOT = REPOSITORY_ROOT / "game"
GENERATOR_PATH = GAME_ROOT / "tools" / "generate_green_hero_animations.py"
PACKAGE_ROOT = (
    GAME_ROOT
    / "test_assets"
    / "characters"
    / "heroes"
    / "greenhero"
    / "ultra"
)
MANIFEST_PATH = PACKAGE_ROOT / "stand_walk_manifest.json"
RESOURCE_PATH = PACKAGE_ROOT / "green_hero_stand_walk_ultra.tres"


def _load_generator() -> ModuleType:
    spec = util.spec_from_file_location("green_hero_generator_under_test", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load generator at {GENERATOR_PATH}")
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(
    MANIFEST_PATH.is_file(),
    "legacy stand/walk package is not part of the five-variant animation matrix",
)
class GreenHeroAnimationGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = _load_generator()

    def test_manifest_defines_exact_stand_walk_direction_contract(self) -> None:
        package = self.generator.load_package(MANIFEST_PATH)
        actual = tuple(
            (animation.name, animation.source_key)
            for animation in package.animations
        )
        expected = (
            ("stand_N", "N"),
            ("stand_NO", "NO"),
            ("stand_O", "O"),
            ("stand_SO", "SO"),
            ("stand_S", "S"),
            ("stand_SW", "SW"),
            ("stand_W", "W"),
            ("stand_NW", "NW"),
            ("walk_N", "N"),
            ("walk_NO", "NO"),
            ("walk_O", "O"),
            ("walk_SO", "SO"),
            ("walk_S", "S"),
            ("walk_SW", "SW"),
            ("walk_W", "W"),
            ("walk_NW", "NW"),
        )

        self.assertEqual(actual, expected)
        self.assertEqual(sum(item.frame_count for item in package.animations), 256)
        self.assertTrue(
            all(
                (item.columns, item.rows, item.frame_order)
                == (4, 4, tuple(range(16)))
                for item in package.animations
            )
        )
        self.assertTrue(all(item.loop for item in package.animations))
        self.assertTrue(
            all(
                item.frame_durations_ms == (120,) * 16
                for item in package.animations
            )
        )
        self.assertEqual(package.source_canvas, (1254, 1254))
        self.assertEqual(package.reference_pose.animation, "stand_S")
        self.assertEqual(package.reference_pose.frame, 0)
        self.assertEqual(package.reference_pose.alpha_bounds, (171, 19, 911, 1205))
        self.assertEqual(package.reference_pose.foot_anchor, (627, 1224))
        self.assertEqual(package.reference_pose.height_pixels, 1205)
        self.assertEqual(package.reference_pose.world_height, 80)

    def test_stand_and_walk_use_the_supplied_ultra_sheets(self) -> None:
        package = self.generator.load_package(MANIFEST_PATH)
        expected_stand_crops = {
            "N": (266, 19, 721, 1205),
            "NO": (167, 19, 919, 1205),
            "O": (152, 19, 949, 1205),
            "SO": (150, 19, 954, 1205),
            "S": (171, 19, 911, 1205),
            "SW": (150, 19, 954, 1205),
            "W": (153, 19, 949, 1205),
            "NW": (168, 19, 919, 1205),
        }
        for animation in package.animations:
            with self.subTest(animation=animation.name):
                self.assertEqual(animation.source_canvas, (1254, 1254))
                self.assertEqual(animation.height_pixels, 1205)
                self.assertEqual(animation.foot_anchor, (627, 1224))
                self.assertEqual(animation.crop_rect, expected_stand_crops[animation.direction])
                self.assertIsNone(animation.reference_image)
                self.assertIsNotNone(animation.input_sheet)
                self.assertIsNone(animation.reference_sheet)
                self.assertIsNone(animation.timing_gif)
                stand = next(
                    item for item in package.animations
                    if item.name == f"stand_{animation.direction}"
                )
                self.assertEqual(animation.input_sheet.sha256, stand.input_sheet.sha256)
                self.assertEqual(
                    (PACKAGE_ROOT / animation.runtime_file).read_bytes(),
                    (PACKAGE_ROOT / stand.runtime_file).read_bytes(),
                )

    def test_runtime_assets_and_generated_resource_are_current(self) -> None:
        for variant in ("ultra", "hd", "test"):
            with self.subTest(variant=variant):
                root = PACKAGE_ROOT.parent / variant
                package = self.generator.load_package(root / "stand_walk_manifest.json")
                self.generator.validate_runtime_assets(package, root)
                generated = self.generator.generate_resource(package)
                self.assertEqual((root / package.resource_file).read_text(), generated)
                self.assertEqual(
                    generated.count('[sub_resource type="AtlasTexture"'),
                    48 if variant == "test" else 256,
                )
                self.assertEqual(
                    generated.count('[ext_resource type="Texture2D"'),
                    48 if variant == "test" else 16,
                )

    def test_test_package_retains_audited_still_poses_without_raw_copies(self) -> None:
        root = PACKAGE_ROOT.parent / "test"
        package = self.generator.load_package(root / "stand_walk_manifest.json")
        self.assertEqual(package.variant, "test")
        self.assertEqual(package.actions, ("stand", "walk", "run", "sneak", "sprint", "jump"))
        self.assertEqual(len(package.animations), 48)
        for animation in package.animations:
            with self.subTest(animation=animation.name):
                payload = (root / animation.runtime_file).read_bytes()
                self.assertEqual(
                    hashlib.sha256(payload).hexdigest(), animation.optimized_source.sha256,
                )
                self.assertEqual(animation.frame_order, (0,))
                self.assertEqual((animation.columns, animation.rows), (1, 1))
                self.assertFalse(animation.loop)
                self.assertEqual(animation.source_canvas, (1436, 1254))
                self.assertEqual(animation.crop_rect, (0, 0, 1436, 1254))
                self.assertEqual(animation.height_pixels, 1205)
                self.assertEqual(animation.foot_anchor, (718, 1224))
        self.assertFalse((root / "sources").exists())

    def test_declared_test_actions_require_complete_directions_and_base_actions(self) -> None:
        path = PACKAGE_ROOT.parent / "test/stand_walk_manifest.json"
        manifest = json.loads(path.read_text())
        cases = (
            ({"actions": ["stand", "walk", "fly"]}, "supported variant actions"),
            ({"actions": ["stand", "jump"]}, "supported variant actions"),
            ({"animations": manifest["animations"][:-1]}, "all 48"),
            ({"variant": "hd"}, "supported variant actions"),
        )
        with TemporaryDirectory() as directory:
            invalid = Path(directory) / "manifest.json"
            for update, message in cases:
                with self.subTest(update=list(update)):
                    invalid.write_text(json.dumps(manifest | update))
                    with self.assertRaisesRegex(self.generator.AnimationPackageError, message):
                        self.generator.load_package(invalid)

    def test_local_sheet_hash_mismatch_is_rejected(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text())
        manifest["animations"][0]["source"]["input_sheet"][1] = "0" * 64
        with TemporaryDirectory() as temporary_directory:
            invalid_manifest = Path(temporary_directory) / "manifest.json"
            invalid_manifest.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(
                self.generator.AnimationPackageError, "input_sheet hash differs",
            ):
                self.generator.load_package(invalid_manifest)

    def test_all_runtime_textures_use_lossless_import_without_mipmaps(self) -> None:
        package = self.generator.load_package(MANIFEST_PATH)

        for animation in package.animations:
            with self.subTest(animation=animation.name):
                import_path = PACKAGE_ROOT / f"{animation.runtime_file}.import"
                settings = import_path.read_text(encoding="utf-8")
                self.assertIn("compress/mode=0", settings)
                self.assertIn("mipmaps/generate=false", settings)
                self.assertIn("process/size_limit=0", settings)

    def test_invalid_direction_source_mapping_is_rejected(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        manifest["animations"][0]["source_key"] = "W"
        with TemporaryDirectory() as temporary_directory:
            invalid_manifest = Path(temporary_directory) / "manifest.json"
            invalid_manifest.write_text(
                json.dumps(manifest),
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaisesRegex(
                self.generator.AnimationPackageError,
                "wrong source_key for stand_N",
            ):
                self.generator.load_package(invalid_manifest)


if __name__ == "__main__":
    unittest.main()
