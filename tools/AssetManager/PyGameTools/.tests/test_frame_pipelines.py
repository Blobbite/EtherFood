"""Integrationstests mit synthetischen Streifen; keine Spielgrafiken erforderlich."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def snapshot(root):
    return {str(path.relative_to(root)): (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
            for path in root.rglob("*") if path.is_file()}


class PipelineChecks:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=f"fram{self.count}-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "spritesheet # 100% mit Leerzeichen"
        self.root.mkdir()

    @property
    def starter(self):
        return ROOT / (f"Pipline/0-SpritesheetFram{self.count}-Pipline/"
                       f"PyPiplineStart-SpritesheetFram{self.count}.py")

    @property
    def output_stem(self):
        return f"hero_N_{self.columns}x{self.rows}_o"

    def strip(self, name="hero_N.png", vertical=None):
        if vertical is None:
            vertical = self.count == 8
        frames = []
        for index in range(self.count):
            frame = Image.new("RGBA", (12, 10))
            if index != 5:  # Auch ein leerer Frame muss erhalten bleiben.
                draw = ImageDraw.Draw(frame)
                draw.rectangle((2 + index % 3, 2, 8, 6), fill=(30 + index * 9, 180, 70, 255))
            if index == 2:
                frame.putpixel((9, 7), (100, 170, 40, 128))
            if index == 3:
                frame.putpixel((9, 7), (81, 120, 210, 1))
            frames.append(frame)
        image = Image.new("RGBA", (12, 10 * self.count) if vertical else (12 * self.count, 10))
        for index, frame in enumerate(frames):
            image.paste(frame, (0, index * 10) if vertical else (index * 12, 0))
        path = self.root / name
        image.save(path)
        return path, frames

    def call(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(self.starter), *map(str, args)], cwd=self.root,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_strip_directions_preserve_pixels_frames_and_layout(self):
        for index, vertical in enumerate(self.directions):
            name = f"hero_{index}.png"
            source, frames = self.strip(name, vertical)
            before = source.read_bytes()
            self.call("--overwrite")
            archived = self.root / "PixelEng" / name
            self.assertFalse(source.exists())
            self.assertEqual(archived.read_bytes(), before)
            output = self.root / f"{source.stem}_{self.columns}x{self.rows}_o.png"
            with Image.open(output) as atlas:
                self.assertEqual(atlas.size, (self.columns * 8, self.rows * 6))
                for index, original in enumerate(frames):
                    x, y = index % self.columns * 8, index // self.columns * 6
                    actual = atlas.crop((x, y, x + 8, y + 6))
                    self.assertEqual(actual.tobytes(), original.crop((2, 2, 10, 8)).tobytes())
            for png, size in ((archived, (12, 10)), (output, (8, 6))):
                gif = png.with_name(f"{png.stem}_8fps.gif")
                with Image.open(gif) as animation:
                    self.assertEqual(animation.size, size)
                    self.assertEqual(json.loads(animation.info["comment"])["source_frames"], self.count)
                html = (png.parent / "gif-vergleich.html").read_text()
                self.assertIn(png.name, html)
                self.assertIn(gif.name, html)
                payload = json.loads(re.search(
                    r'<script id="gif-data" type="application/json">(.*?)</script>', html, re.S).group(1))
                item = next(item for item in payload["items"] if item["gifName"] == gif.name)
                self.assertEqual(item["logicalFrames"], self.count)
                self.assertEqual((item["width"], item["height"]), size)
        self.assertEqual(len(list(self.root.glob("*.png"))), len(self.directions))

    def test_rerun_reuses_images_and_overwrite_regenerates_outputs(self):
        self.strip()
        self.call()
        before = {name: value for name, value in snapshot(self.root).items() if not name.endswith(".html")}
        self.call()
        self.assertEqual(before, {name: value for name, value in snapshot(self.root).items()
                                 if not name.endswith(".html")})
        target = self.root / f"{self.output_stem}.png"
        target.write_bytes(b"broken")
        self.call("--overwrite", "--fps", "12")
        with Image.open(target) as repaired:
            self.assertEqual(repaired.size, (self.columns * 8, self.rows * 6))
        self.assertTrue((self.root / f"{self.output_stem}_12fps.gif").exists())
        self.assertTrue((self.root / "PixelEng/hero_N_12fps.gif").exists())

    def test_invalid_input_and_dry_run_do_not_move_originals(self):
        self.strip()
        before = snapshot(self.root)
        self.call("--dry-run")
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse((self.root / "PixelEng").exists())
        Image.new("RGBA", (17, 3), "red").save(self.root / "invalid.png")
        before = snapshot(self.root)
        self.call(expected=1)
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse((self.root / "PixelEng").exists())

    def test_archive_conflict_and_symlink_output_fail_before_moves(self):
        source, _ = self.strip()
        archive = self.root / "PixelEng"
        archive.mkdir()
        shutil.copy2(source, archive / source.name)
        before = snapshot(self.root)
        self.call(expected=1)
        self.assertEqual(snapshot(self.root), before)
        (archive / source.name).unlink()
        external = Path(self.temp.name) / "unrelated.txt"
        external.write_text("behalten")
        (self.root / "gif-vergleich.html").symlink_to(external)
        self.call(expected=1)
        self.assertTrue(source.exists())
        self.assertEqual(external.read_text(), "behalten")

    def test_same_stem_fails_before_moves(self):
        source, _ = self.strip()
        shutil.copy2(source, source.with_suffix(".PNG"))
        before = snapshot(self.root)
        self.call(expected=1)
        self.assertEqual(snapshot(self.root), before)

    def test_existing_original_gif_is_preserved_at_original_path(self):
        source, _ = self.strip()
        original_gif = source.with_name(f"{source.stem}_8fps.gif")
        Image.new("RGBA", (12, 10), "red").save(original_gif, "GIF")
        before = (original_gif.read_bytes(), original_gif.stat().st_mtime_ns)
        self.call()
        self.assertEqual((original_gif.read_bytes(), original_gif.stat().st_mtime_ns), before)
        with Image.open(self.root / "PixelEng" / original_gif.name) as animation:
            self.assertEqual(json.loads(animation.info["comment"])["source_frames"], self.count)

    def test_help_without_pillow_and_invalid_grid(self):
        help_result = subprocess.run([sys.executable, "-S", str(self.starter), "--help"],
                                     capture_output=True, text=True, timeout=10)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn(f"{self.count}er-Streifen", help_result.stdout)
        self.strip()
        self.call("--grid", "4x4", expected=2)
        self.assertFalse((self.root / "PixelEng").exists())

    def test_all_transparent_input_fails_before_any_moves(self):
        self.strip()
        Image.new("RGBA", (12, 10 * self.count)).save(self.root / "empty.png")
        before = snapshot(self.root)
        self.call(expected=1)
        self.assertEqual(snapshot(self.root), before)

    def test_source_strip_names_with_grid_suffix_are_accepted(self):
        for vertical in self.directions:
            suffix = f"1x{self.count}" if vertical else f"{self.count}x1"
            source, _ = self.strip(f"hero_{suffix}.png", vertical)
            original = source.read_bytes()
            self.call()
            self.call()
            self.assertEqual((self.root / "PixelEng" / source.name).read_bytes(), original)
            self.assertTrue((self.root / f"hero_{suffix}_{self.columns}x{self.rows}_o.png").is_file())

    def test_other_grid_outputs_are_not_processed_again(self):
        self.strip()
        for name in ("previous_2x4_o.png", "previous_5x2.png", "previous_solo_3x2_o.PNG"):
            Image.new("RGBA", (1, 1), "red").save(self.root / name)
        before = {path.name: path.read_bytes() for path in self.root.glob("previous*")}
        self.call()
        self.call()
        for name, content in before.items():
            self.assertEqual((self.root / name).read_bytes(), content)
            self.assertFalse((self.root / "PixelEng" / name).exists())
        self.assertEqual(len(list((self.root / "PixelEng").glob("*.png"))), 1)


class Fram16Tests(PipelineChecks, unittest.TestCase):
    count, columns, rows = 16, 4, 4
    directions = (False, True)

    def test_manual_grid_overrides_longer_side_for_wide_vertical_frames(self):
        Image.new("RGBA", (200, 128), "red").save(self.root / "wide.png")
        self.call("--grid", "1x16")
        with Image.open(self.root / "wide_4x4_o.png") as result:
            self.assertEqual(result.size, (800, 32))


class Fram8Tests(PipelineChecks, unittest.TestCase):
    count, columns, rows = 8, 4, 2
    directions = (False, True)

    def test_manual_grid_keeps_wide_frames_as_1x8(self):
        sheet = Image.new("RGBA", (100, 64))
        for index in range(8):
            sheet.paste((index * 30, 50, 100, 255), (0, index * 8, 100, (index + 1) * 8))
        sheet.save(self.root / "wide.png")
        self.call("--grid", "1x8")
        with Image.open(self.root / "wide_4x2_o.png") as result:
            self.assertEqual(result.size, (400, 16))
            for index in range(8):
                self.assertEqual(result.getpixel((index % 4 * 100, index // 4 * 8)),
                                 (index * 30, 50, 100, 255))

    def test_horizontal_grid_can_be_selected_explicitly(self):
        self.strip(vertical=False)
        self.call("--grid", "8x1")
        with Image.open(self.root / f"{self.output_stem}.png") as result:
            self.assertEqual(result.size, (32, 12))

    def test_5120x640_sheet_repairs_wrong_1x8_outputs_and_previews(self):
        # Genau die Eingabegröße aus dem Fehlerbericht: acht 640x640-Frames nebeneinander.
        frames = []
        strip = Image.new("RGBA", (5120, 640))
        for index in range(8):
            frame = Image.new("RGBA", (640, 640))
            ImageDraw.Draw(frame).rectangle((200 + index * 4, 120, 299 + index * 4, 519),
                                           fill=(30 + index * 20, 180, 70, 255))
            if index == 7:
                frame.putpixel((360, 530), (90, 80, 70, 128))
            strip.paste(frame, (index * 640, 0))
            frames.append(frame)
        source = self.root / "hero_N.png"
        strip.save(source)
        original = source.read_bytes()

        # Alten Fehler samt zwischengespeicherten PNGs/GIFs/HTML nachstellen.
        self.call("--grid", "1x8")
        output = self.root / f"{self.output_stem}.png"
        with Image.open(output) as wrong:
            self.assertGreater(wrong.width, 16000)
        before = snapshot(self.root)
        self.call("--dry-run", "--overwrite")
        self.assertEqual(snapshot(self.root), before)
        self.call(expected=1)
        self.assertEqual(snapshot(self.root), before)
        repaired = self.call("--overwrite")
        self.assertIn("8x1", repaired.stdout)
        archived = self.root / "PixelEng/hero_N.png"
        self.assertEqual(archived.read_bytes(), original)
        with Image.open(output) as atlas:
            self.assertEqual(atlas.size, (644, 822))
            for index, frame in enumerate(frames):
                x, y = index % 4 * 161, index // 4 * 411
                self.assertEqual(atlas.crop((x, y, x + 161, y + 411)).tobytes(),
                                 frame.crop((200, 120, 361, 531)).tobytes())

        for png, size, layout, point in (
            (archived, (640, 640), (8, 1), (250, 200)),
            (output, (161, 411), (4, 2), (50, 80)),
        ):
            gif = png.with_name(f"{png.stem}_8fps.gif")
            with Image.open(gif) as animation:
                self.assertEqual(animation.size, size)
                self.assertEqual(animation.n_frames, 8)
                for index in range(8):
                    animation.seek(index)
                    self.assertEqual(animation.convert("RGBA").getpixel(point),
                                     (30 + index * 20, 180, 70, 255))
            html = (png.parent / "gif-vergleich.html").read_text()
            payload = json.loads(re.search(
                r'<script id="gif-data" type="application/json">(.*?)</script>', html, re.S).group(1))
            item = next(item for item in payload["items"] if item["gifName"] == gif.name)
            self.assertEqual((item["columns"], item["rows"]), layout)
            self.assertEqual((item["width"], item["height"]), size)
            self.assertEqual(item["logicalFrames"], 8)

        before = {name: state for name, state in snapshot(self.root).items() if not name.endswith(".html")}
        self.call()
        self.assertEqual(before, {name: state for name, state in snapshot(self.root).items()
                                  if not name.endswith(".html")})


if __name__ == "__main__":
    unittest.main()
