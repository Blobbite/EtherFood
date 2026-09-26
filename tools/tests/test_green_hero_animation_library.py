"""Validate the five-variant Green Hero animation source matrix."""

from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = (
    REPOSITORY_ROOT
    / "game/test_assets/characters/heroes/greenhero/spritesheets"
)
LIBRARY_PATH = (
    REPOSITORY_ROOT
    / "game/test_scenes/characters/heroes/greenhero/green_hero_animation_library.gd"
)
VARIANTS = ("comic_high", "comic_mid", "comic_low", "pixel_high", "pixel_low")
FPS_VALUES = (8, 10, 12, 14, 16)
ACTIONS = ("stand", "slowwalk", "walk", "sneak", "run")
DIRECTIONS = ("N", "NO", "O", "SO", "S", "SW", "W", "NW")
GRID_BY_FPS = {8: "4x2", 10: "5x2", 12: "4x3", 14: "7x2", 16: "4x4"}


class GreenHeroAnimationLibraryTests(unittest.TestCase):
    def test_source_matrix_contains_every_variant_action_fps_and_direction(self) -> None:
        for action in ACTIONS:
            for variant in VARIANTS:
                for fps in FPS_VALUES:
                    folder = SOURCE_ROOT / action / variant / f"spritesheet-fram{fps}"
                    files = sorted(folder.glob("*.png"))
                    with self.subTest(action=action, variant=variant, fps=fps):
                        self.assertEqual(len(files), 8)
                        for direction in DIRECTIONS:
                            expected = re.compile(
                                rf"greenhero_hd_{action}_spritesheet_{direction}_"
                                rf"{GRID_BY_FPS[fps]}_o\.png"
                            )
                            self.assertTrue(
                                any(expected.fullmatch(path.name) for path in files),
                                f"missing {action}/{variant}/{fps}/{direction}",
                            )

    def test_jump_is_one_stand_pose_per_variant_and_direction(self) -> None:
        for variant in VARIANTS:
            files = sorted((SOURCE_ROOT / "jump" / variant).glob("*.png"))
            with self.subTest(variant=variant):
                self.assertEqual(len(files), 8)
                self.assertEqual(
                    {path.stem for path in files},
                    {f"greenhero_hd_jump_{direction}" for direction in DIRECTIONS},
                )

    def test_sprint_is_declared_as_run_at_twelve_fps_without_duplicate_sheets(self) -> None:
        library = LIBRARY_PATH.read_text(encoding="utf-8")
        self.assertIn('"run" if action == "sprint" else action', library)
        self.assertIn('12 if action == "sprint" else normalized_frames', library)
        self.assertIn('source_paths[animation_name] = _source_path(', library)
        self.assertIn(
            '"%s/%s/%s/spritesheet-fram%d/greenhero_hd_%s_spritesheet_%s_%dx%d_o.png"',
            library,
        )
        self.assertIn("playback_fps", library)
        self.assertIn('"hero_frames"', library)
        self.assertIn('"hero_fps"', library)


if __name__ == "__main__":
    unittest.main()
