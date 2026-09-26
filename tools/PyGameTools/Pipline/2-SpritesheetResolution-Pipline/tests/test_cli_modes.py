"""CLI integration tests: multiple poses, reuse and independent downstream phases."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote

from PIL import Image, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
VARIANTS = ("comic_mid", "comic_low", "pixel_high", "pixel_low")
DIRECTIONS = ("N", "NO", "O", "SO", "S", "SW", "W", "NW")


def make_pose(root, name, layouts=((4, 2),), directions=("N",), size=(32, 24)):
    pose = root / name
    for columns, rows in layouts:
        folder = pose / "comic_high" / f"spritesheet-fram{columns * rows}"
        folder.mkdir(parents=True, exist_ok=True)
        for direction in directions:
            with Image.new("RGBA", (size[0] * columns, size[1] * rows)) as image:
                draw = ImageDraw.Draw(image)
                for index in range(columns * rows):
                    x, y = index % columns * size[0], index // columns * size[1]
                    draw.rectangle((x + 5 + index % 3, y + 4, x + size[0] - 5, y + size[1] - 3),
                                   fill=(40 + index * 3, 170, 70 + index * 2, 255))
                image.save(folder / f"hero_{direction}_{columns}x{rows}_o.png")
    return pose


def assets(root):
    return {path.relative_to(root).as_posix(): (hashlib.sha256(path.read_bytes()).hexdigest(),
                                             path.stat().st_mtime_ns)
            for path in root.rglob("*") if path.suffix.lower() in {".png", ".gif"}}


def data_file(path, identifier="pose-data"):
    match = re.search(rf'<script id="{identifier}" type="application/json">(.*?)</script>', path.read_text(), re.S)
    return json.loads(match[1])


class CLIModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pygraphics-cli-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Posen # 100%"
        self.root.mkdir()

    def call(self, *arguments, expected=0, cwd=None):
        result = subprocess.run([sys.executable, str(SCRIPTS / "PyPiplineStart-SpritesheetResolution.py"), *map(str, arguments)],
                                cwd=cwd or self.root, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_all_poses_layouts_directions_and_linked_assets(self):
        first = make_pose(self.root, "jump # 100%", ((4, 2), (4, 4)), DIRECTIONS)
        second = make_pose(self.root, "actor/walk", ((7, 7),), DIRECTIONS)
        before = assets(self.root)
        self.call("--spritesheet-all")
        payload = data_file(self.root / "positionsvergleich.html")
        self.assertEqual([p["name"] for p in payload["poses"]], ["actor/walk", "jump # 100%"])
        self.assertEqual(tuple(payload["directions"]), DIRECTIONS)
        for pose in (first, second):
            self.assertTrue((pose / "aufloesungsvergleich.html").is_file())
            for variant in VARIANTS:
                for folder in (pose / variant).iterdir():
                    self.assertEqual(len(list(folder.glob("*.gif"))), 8)
                    self.assertTrue((folder / "gif-vergleich.html").is_file())
        for pose in payload["poses"]:
            self.assertTrue((self.root / unquote(pose["comparison"])).is_file())
            for group in pose["sets"]:
                self.assertEqual(set(group["directions"]), set(DIRECTIONS))
                for tracks in group["directions"].values():
                    for variant, item in tracks.items():
                        self.assertFalse(item.get("missing"))
                        self.assertTrue((self.root / unquote(item["sheet"])).is_file())
                        self.assertEqual(len(item["bounds"]), item["logicalFrames"])
                        self.assertTrue(item["hasHDReference"])
                        if variant != "comic_high":
                            self.assertTrue((self.root / unquote(item["gif"])).is_file())
        for path, value in before.items():
            self.assertEqual(assets(self.root)[path], value)
        html = (self.root / "positionsvergleich.html").read_text()
        self.assertNotIn("data:image/", html)
        self.assertNotIn("base64", html)
        self.assertFalse(list(self.root.rglob("*-bilder")))

    def test_all_output_root_and_recursive_discovery_skip_links(self):
        make_pose(self.root, "A/jump")
        make_pose(self.root, "B/jump")
        (self.root / "link").symlink_to(self.root / "A", target_is_directory=True)
        output = self.root / "Ergebnisse"
        self.call("-s-a", "--output-root", output)
        self.assertEqual([p["name"] for p in data_file(output / "positionsvergleich.html")["poses"]],
                         ["A/jump", "B/jump"])
        self.assertFalse((self.root / "A/jump/comic_mid").exists())
        self.call("-s-a", "--output-root", output)
        self.assertFalse((output / "Ergebnisse").exists())

    def test_single_image_pose_keeps_resolution_page_and_is_not_an_animation_choice(self):
        single = self.root / "jump" / "comic_high"
        single.mkdir(parents=True)
        with Image.new("RGBA", (32, 24), (40, 170, 70, 255)) as image:
            image.save(single / "hero_N.png")
        make_pose(self.root, "walk")
        self.call("--spritesheet-all")
        payload = data_file(self.root / "positionsvergleich.html")
        self.assertEqual([pose["name"] for pose in payload["poses"]], ["walk"])
        stills = data_file(self.root / "jump" / "aufloesungsvergleich.html", "comparison-data")
        self.assertTrue(stills["sets"][0]["single"])
        self.assertEqual(set(stills["sets"][0]["directions"]["N"]), {"comic_high", *VARIANTS})

    def test_dry_run_validates_all_poses_and_writes_nothing(self):
        make_pose(self.root, "jump")
        make_pose(self.root, "walk")
        before = set(self.root.rglob("*"))
        result = self.call("-s-a", "--dry-run")
        self.assertIn("positionsvergleich.html", result.stdout)
        self.assertEqual(set(self.root.rglob("*")), before)

    def test_bad_second_pose_fails_before_first_pose_is_written(self):
        make_pose(self.root, "A")
        bad = make_pose(self.root, "B")
        next(bad.rglob("*.png")).write_bytes(b"broken")
        before = set(self.root.rglob("*"))
        self.call("-s-a", expected=1)
        self.assertEqual(set(self.root.rglob("*")), before)

    def test_invalid_or_stale_gifs_require_overwrite(self):
        pose = make_pose(self.root, "walk")
        self.call("-s", pose)
        before = assets(pose)
        self.call("--spritesheet", pose)
        self.assertEqual(before, assets(pose))
        gif = next((pose / "comic_mid").rglob("*.gif"))
        gif.write_bytes(b"broken")
        self.call("-s", pose, expected=1)
        self.assertEqual(gif.read_bytes(), b"broken")
        self.call("-s", pose, "--overwrite")
        with Image.open(gif) as image:
            self.assertEqual(image.format, "GIF")
        os.utime(gif, (1, 1))
        self.call("-s", pose, expected=1)
        self.assertEqual(gif.stat().st_mtime_ns, 1_000_000_000)
        self.call("-s", pose, "--overwrite")
        self.assertGreater(gif.stat().st_mtime_ns, 1_000_000_000)

    def test_gif_only_does_not_create_or_modify_pngs_even_with_overwrite(self):
        pose = make_pose(self.root, "walk")
        self.call("-s", pose, "--no-gif")
        missing = next((pose / "comic_low").rglob("*.png"))
        missing.unlink()
        shutil.rmtree(pose / "comic_high")
        before = assets(pose)
        self.call("-s", pose, "--gif-only", "--overwrite", "--fps", "12")
        self.assertFalse(missing.exists())
        after = assets(pose)
        self.assertEqual(before, {key: value for key, value in after.items() if key.endswith(".png")})
        self.assertEqual(len(list(pose.rglob("*_12fps.gif"))), 3)
        self.assertFalse((pose / "comic_high").exists())

    def test_html_only_all_reuses_images_and_supports_gifs_without_sources(self):
        pose = make_pose(self.root, "jump")
        self.call("-s-a")
        before = assets(self.root)
        self.call("-s-a", "--html-only")
        self.assertEqual(before, assets(self.root))
        shutil.rmtree(pose / "comic_high")
        for png in pose.rglob("*.png"):
            png.unlink()
        before = assets(self.root)
        self.call("-s-a", "--html-only", "--overwrite")
        self.assertEqual(before, assets(self.root))
        payload = data_file(self.root / "positionsvergleich.html")
        track = payload["poses"][0]["sets"][0]["directions"]["N"]["comic_mid"]
        self.assertIsNone(track["sheet"])
        self.assertTrue(track["gif"])

    def test_gif_only_and_html_only_dry_run(self):
        pose = make_pose(self.root, "jump")
        self.call("-s", pose, "--no-gif")
        before = set(self.root.rglob("*"))
        for mode in ("--gif-only", "--html-only"):
            self.call("-s-a", mode, "--dry-run")
            self.assertEqual(set(self.root.rglob("*")), before)

    def test_seven_by_seven_without_filename_hint(self):
        pose = make_pose(self.root, "jump", ((7, 7),))
        source = next(pose.rglob("*.png"))
        source.rename(source.with_name("hero_N.png"))
        self.call("-s", pose)
        self.call("-s-a", "--html-only")
        track = data_file(self.root / "positionsvergleich.html")["poses"][0]["sets"][0]["directions"]["N"]["comic_mid"]
        self.assertEqual((track["columns"], track["rows"], track["logicalFrames"]), (7, 7, 49))

    def test_resolution_tokens_are_not_mistaken_for_larger_grids(self):
        pose = make_pose(self.root, "jump")
        source = next(pose.rglob("*.png"))
        source.rename(source.with_name("hero_32x32_N_4x2_o.png"))
        self.call("-s", pose)
        self.assertEqual(len(list(pose.rglob("*.gif"))), 4)

    def test_measurements_preserve_blank_frames_and_detect_shift(self):
        from PyGraphicsPoseCompare import collect_pose
        pose = make_pose(self.root, "jump")
        self.call("-s", pose, "--no-gif")
        path = next((pose / "comic_mid").rglob("*.png"))
        with Image.open(path) as image:
            edited = image.convert("RGBA")
        edited.paste((0, 0, 0, 0), (0, 0, 16, 12))
        edited.save(path)
        edited.close()
        groups, errors = collect_pose(pose, pose / "comic_high", self.root / "positionsvergleich.html", 8, measure=True)
        tracks = groups[0]["directions"]["N"]
        self.assertEqual(errors, 0)
        self.assertEqual(tracks["comic_high"]["bounds"][0], [5, 4, 28, 22])
        self.assertIsNone(tracks["comic_mid"]["bounds"][0])
        self.assertEqual(len(tracks["comic_mid"]["bounds"]), 8)

    def test_symlink_comparison_target_fails_before_conversion(self):
        make_pose(self.root, "jump")
        target = Path(self.temp.name) / "outside.html"
        target.write_text("behalten")
        (self.root / "positionsvergleich.html").symlink_to(target)
        self.call("-s-a", expected=1)
        self.assertEqual(target.read_text(), "behalten")
        self.assertFalse((self.root / "jump/comic_mid").exists())

    def test_help_modes_conflicts_and_reserved_textures(self):
        pose = make_pose(self.root, "jump")
        help_text = self.call("-h").stdout
        for option in ("--spritesheet", "--spritesheet-all", "-s-a", "--gif-only", "--html-only", "--Textur"):
            self.assertIn(option, help_text)
        for args in (("-s", "-s-a"), ("--gif-only", "--no-gif"),
                     ("--gif-only", "--html-only"), ("--grid", "9x9")):
            self.call(pose, *args, expected=2)
        for flag in ("--Textur", "--textur", "-t"):
            result = self.call(pose, flag, expected=2)
            self.assertIn("noch nicht implementiert", result.stderr)
        self.assertEqual(set(pose.iterdir()), {pose / "comic_high"})

    def test_empty_all_and_missing_gif_inputs_report_errors(self):
        self.call("-s-a", expected=1)
        pose = make_pose(self.root, "jump")
        self.call(pose, "--gif-only", expected=1)
        self.assertFalse((pose / "comic_mid").exists())


if __name__ == "__main__":
    unittest.main()
