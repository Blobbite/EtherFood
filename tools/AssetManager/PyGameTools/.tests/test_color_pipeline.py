"""Referenzfarben, zeitlich stabile Abbildung, PNG-Erhalt und Ausgabemodi."""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageCms, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Pipline/PiplineToos"))
import PyImgColorMatch as color

STARTER = ROOT / "Pipline/3-SpritesheetColor-Pipline/PyPiplineStart-SpritesheetColor.py"
spec = importlib.util.spec_from_file_location("color_pipeline", STARTER)
pipeline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pipeline
spec.loader.exec_module(pipeline)


def snapshot(root):
    return {str(p.relative_to(root)): (color.sha256(p), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def make_sheet(path, shifted=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (16*12, 12), (123, 45, 67, 0))
    draw = ImageDraw.Draw(image)
    for i in range(16):
        draw.rectangle((i*12+2, 3, i*12+6, 9), fill=(70, 122, 48, 255) if shifted else (80, 120, 40, 255))
        draw.point((i*12+2, 2), fill=(70, 122, 48, 127) if shifted else (80, 120, 40, 127))
        draw.point((i*12+8, 4+i%5), fill=(100+i*3, 70, 45, 255))
    image.save(path)
    image.close()


class ColorMathTests(unittest.TestCase):
    def test_icc_srgb_preserves_alpha_and_invisible_rgb(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "icc.png"
            icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
            with Image.new("RGBA", (3, 1)) as original:
                original.putdata([(80, 120, 40, 255), (80, 120, 40, 127), (200, 31, 99, 0)])
                original.save(path, icc_profile=icc)
                with color.load_png(path) as normalized:
                    self.assertEqual(normalized.tobytes(), original.tobytes())
                    self.assertEqual(normalized.info["color_management"], "ICC_to_sRGB_relative_colorimetric")

    def test_lab_conversion_roundtrip_and_known_white(self):
        for rgb in ((0, 0, 0), (1, 1, 1), (1, 0, 0), (.12, .5, .3)):
            for expected, actual in zip(rgb, color.lab_to_rgb(color.rgb_to_lab(rgb))):
                self.assertAlmostEqual(expected, actual, places=5)
        self.assertAlmostEqual(color.rgb_to_lab((1, 1, 1))[0], 100, places=4)

    def test_sampling_equal_frames_ignores_transparent_rgb_and_weights_alpha(self):
        with Image.new("RGBA", (20, 10), (0, 255, 0, 0)) as sheet:
            draw = ImageDraw.Draw(sheet)
            draw.point((2, 2), fill=(220, 30, 10, 255))
            draw.rectangle((10, 0, 19, 9), fill=(20, 40, 210, 255))
            sample = color.balanced_samples(sheet, (2, 1), count=20)
            self.assertEqual(sample.count((220, 30, 10)), 20)
            self.assertEqual(sample.count((20, 40, 210)), 20)
        with Image.new("RGBA", (2, 1)) as sample:
            sample.putdata([(220, 30, 10, 255), (20, 40, 210, 85)])
            weighted = color.balanced_samples(sample, (1, 1), count=40)
            self.assertEqual(weighted.count((220, 30, 10)), 30)
            self.assertEqual(weighted.count((20, 40, 210)), 10)

    def test_color_moves_towards_reference_with_same_mapping_across_frames(self):
        matcher = color.ColorMatcher({"colors": [[80, 120, 40]]}, strength=1)
        original = (70, 122, 48)
        target_lab = color.rgb_to_lab(tuple(c/255 for c in (80, 120, 40)))
        with Image.new("RGBA", (32, 2), (*original, 255)) as before:
            before.putpixel((0, 0), (210, 41, 160, 0))
            before.putpixel((1, 0), (*original, 127))
            with matcher.apply(before) as after:
                record = color.verify_pixels(before, after)
                self.assertGreater(record["changed_pixels"], 0)
                self.assertEqual(after.getpixel((1, 0))[3], 127)
                self.assertEqual(after.getpixel((0, 0)), before.getpixel((0, 0)))
                self.assertEqual(after.getpixel((2, 0)), after.getpixel((29, 1)))
                actual = color.rgb_to_lab(tuple(c/255 for c in after.getpixel((2, 0))[:3]))
                initial = color.rgb_to_lab(tuple(c/255 for c in original))
                self.assertLess(math.dist(actual[1:], target_lab[1:]), math.dist(initial[1:], target_lab[1:]))
                self.assertLess(abs(actual[0]-initial[0]), .6)

    def test_zero_strength_and_remote_colors_are_unchanged(self):
        matcher = color.ColorMatcher({"colors": [[80, 120, 40]]}, strength=0)
        with Image.new("RGBA", (3, 1)) as before:
            before.putdata([(255, 0, 255, 255), (130, 130, 130, 64), (123, 70, 1, 0)])
            with matcher.apply(before) as after:
                self.assertEqual(before.tobytes(), after.tobytes())
        matcher = color.ColorMatcher({"colors": [[80, 120, 40]]})
        self.assertEqual(matcher.transform(1, 0, 1), (1, 0, 1))
        self.assertEqual(matcher.transform(.5, .5, .5), (.5, .5, .5))


class ColorPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="color # test ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "sources"
        self.output = self.base / "sources-color"
        for direction in color.DIRECTIONS:
            make_sheet(self.source / f"hero_stand_spritesheet_{direction}.png")
        self.run_png = self.source / "hero_run_spritesheet_N.png"
        make_sheet(self.run_png, shifted=True)

    def call(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(STARTER), str(self.source), *map(str, args)],
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_dry_run_normal_overwrite_and_sources_are_preserved(self):
        original = snapshot(self.source)
        for flags in (("--dry-run",), ("--dry-run", "--overwrite")):
            self.call(*flags)
            self.assertFalse(self.output.exists())
            self.assertEqual(snapshot(self.source), original)
        self.call()
        profile = color.load_profile(self.output / ".color_profile/reference-colors.json")
        self.assertEqual([r["direction"] for r in profile["references"]], list(color.DIRECTIONS))
        self.assertTrue(all(r["frames"] == 16 for r in profile["references"]))
        self.assertTrue((self.output / "farbvergleich.html").is_file())
        for direction in color.DIRECTIONS:
            name = f"hero_stand_spritesheet_{direction}.png"
            self.assertEqual((self.output / name).read_bytes(), (self.source / name).read_bytes())
        target = self.output / self.run_png.name
        with color.load_png(self.run_png) as before, color.load_png(target) as after:
            self.assertGreater(color.verify_pixels(before, after)["changed_pixels"], 0)
        with Image.open(target.with_suffix(".gif").with_name(target.stem+"_8fps.gif")) as animation:
            self.assertEqual(animation.info["loop"], 0)
            self.assertEqual(json.loads(animation.info["comment"])["source_frames"], 16)
        before = snapshot(self.output)
        self.call()
        self.call("--dry-run", "--overwrite")
        self.assertEqual(snapshot(self.output), before)
        self.call("--strength", ".2", expected=1)
        self.assertEqual(snapshot(self.output), before)
        target.write_bytes(b"broken PNG")
        foreign = self.output / "keep.txt"
        foreign.write_text("keep")
        damaged = snapshot(self.output)
        self.call(expected=1)
        self.assertEqual(snapshot(self.output), damaged)
        self.call("--overwrite")
        self.assertEqual(foreign.read_text(), "keep")
        self.assertEqual(snapshot(self.source), original)
        with color.load_png(target) as restored:
            self.assertEqual(restored.size, (192, 12))

    def test_missing_direction_invalid_grid_and_overlapping_output_write_nothing(self):
        before = snapshot(self.base)
        self.call("--grid", "10x1", expected=1)
        self.call("--strength", "nan", expected=1)
        self.call("--output-dir", self.source / "result", "--overwrite", expected=1)
        self.call("--output-dir", self.source, "--overwrite", expected=1)
        self.assertEqual(snapshot(self.base), before)
        (self.source / "hero_stand_spritesheet_NW.png").unlink()
        self.call(expected=1)
        self.assertFalse(self.output.exists())

    def test_source_discovery_ignores_archives_derived_data_and_variants(self):
        hd = self.base / "hd"
        wanted = hd / "run/comic_high/spritesheet-fram8/PixelEng/hero_run_spritesheet_N.png"
        for path in (wanted, hd / ".archive/run/comic_high/old.png", hd / "run/comic_low/low.png",
                     hd / "run/comic_high/tools/helper.png", hd / "run/comic_high/hero_4x4_o.png",
                     hd / "run/comic_high/greenhero_varianten/pose.png"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"discovery only")
        self.assertEqual(pipeline.discover(hd), [wanted])
        self.assertEqual(pipeline.infer_grid(wanted, (640, 80)), (8, 1))

    def test_output_link_and_old_profile_are_rejected(self):
        other = self.base / "other"
        other.mkdir()
        self.output.symlink_to(other, target_is_directory=True)
        self.call("--overwrite", expected=1)
        self.assertFalse(list(other.iterdir()))
        old = self.base / "old.json"
        old.write_text('{"schema_version": 3}')
        self.assertRaises(ValueError, color.load_profile, old)

    def test_resolution_uses_same_fixed_palette_for_both_pixel_variants(self):
        refs = pipeline.reference_files(self.source, None, None)
        profile = color.make_profile(refs)
        profile_path = self.base / "reference.json"
        profile_path.write_text(json.dumps(profile))
        pose = self.base / "pose"
        high = pose / "comic_high"
        high.mkdir(parents=True)
        for name, fill in (("hero_N", (74, 121, 45, 255)), ("hero_S", (96, 75, 52, 255))):
            Image.new("RGBA", (32, 32), fill).save(high / (name+".png"))
        starter = ROOT / (
            "Pipline/2-SpritesheetResolution-Pipline/PyPiplineStart-SpritesheetResolution.py"
        )
        result = subprocess.run([sys.executable, str(starter),
                                 str(pose), "--variants", "pixel_high", "pixel_low", "--no-gif",
                                 "--palette-profile", str(profile_path)], text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        palette = {tuple(c) for c in profile["pixel_palette"]}
        for variant in ("pixel_high", "pixel_low"):
            for path in (pose / variant).glob("*.png"):
                with Image.open(path) as image:
                    self.assertTrue({c[:3] for _, c in image.getcolors(1024) if c[3]} <= palette)


if __name__ == "__main__":
    unittest.main()
