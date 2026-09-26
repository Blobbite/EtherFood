"""Rasterübergreifende Pixel- und CLI-Prüfungen des gemeinsamen Optimierers."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "Pipline/PiplineToos/PyImgGrid.py"
sys.path.insert(0, str(SCRIPT.parent))
import PyImgGrid as grid


class GridTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="img-grid-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def sheet(self, count, source_grid, name="hero.png"):
        frames = []
        for index in range(count):
            frame = Image.new("RGBA", (12, 10))
            if index != 2:
                ImageDraw.Draw(frame).rectangle((2 + index % 3, 2, 8, 6),
                                               fill=(index * 7 % 256, 110, 50, 255))
            if index == 0:
                frame.putpixel((9, 7), (80, 70, 60, 1))
                frame.putpixel((3, 3), (10, 20, 30, 128))
                frame.putpixel((4, 3), (90, 80, 70, 0))
            frames.append(frame)
        columns, rows = source_grid
        sheet = Image.new("RGBA", (columns * 12, rows * 10))
        for index, frame in enumerate(frames):
            sheet.paste(frame, (index % columns * 12, index // columns * 10))
        path = self.root / name
        sheet.save(path)
        return path, frames

    def call(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=self.root,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_rectangular_grids_preserve_every_cropped_frame_and_source(self):
        cases = ((3, (1, 3), (3, 1)), (6, (6, 1), (2, 3)), (8, (1, 8), (4, 2)),
                 (10, (2, 5), (5, 2)), (12, (4, 3), (3, 4)), (14, (1, 14), (7, 2)),
                 (16, (16, 1), (4, 4)), (64, (8, 8), (16, 4)))
        for count, source_grid, target_grid in cases:
            with self.subTest(count=count):
                source, frames = self.sheet(count, source_grid, f"hero{count}.png")
                before = source.read_bytes()
                result = grid.convert_to_grid(source, frame_count=count, source_grid=source_grid,
                                              target_grid=target_grid)
                self.assertEqual(source.read_bytes(), before)
                self.assertEqual(result.name, f"hero{count}_{target_grid[0]}x{target_grid[1]}_o.png")
                with Image.open(result) as atlas:
                    self.assertEqual(atlas.size, (target_grid[0] * 8, target_grid[1] * 6))
                    for index, original in enumerate(frames):
                        x, y = index % target_grid[0] * 8, index // target_grid[0] * 6
                        actual = atlas.crop((x, y, x + 8, y + 6))
                        self.assertEqual(actual.tobytes(), original.crop((2, 2, 10, 8)).tobytes())

    def test_without_optimization_preserves_full_cells(self):
        source, frames = self.sheet(8, (2, 4))
        result = grid.convert_to_grid(source, frame_count=8, source_grid=(2, 4),
                                      target_grid=(4, 2), optimize=False)
        self.assertEqual(result.name, "hero_4x2.png")
        with Image.open(result) as atlas:
            self.assertEqual(atlas.size, (48, 20))
            for index, original in enumerate(frames):
                x, y = index % 4 * 12, index // 4 * 10
                self.assertEqual(atlas.crop((x, y, x + 12, y + 10)).tobytes(), original.tobytes())

    def test_invalid_grids_dimensions_and_inplace_output_leave_original(self):
        source, _ = self.sheet(8, (1, 8))
        before = source.read_bytes()
        for options in (
            {"frame_count": 8, "target_grid": (4, 4)},
            {"frame_count": 8, "target_grid": (4, 2), "source_grid": (1, 16)},
            {"frame_count": 8, "target_grid": (4, 2), "source_grid": (8, 1)},
            {"frame_count": 8, "target_grid": (0, 8)},
            {"frame_count": 0, "target_grid": (4, 2)},
            {"frame_count": 8, "target_grid": (4, 2), "output_path": source, "overwrite": True},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                grid.convert_to_grid(source, **options)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(list(self.root.iterdir()), [source])

    def test_solo_repeats_the_same_crop_in_any_target_grid(self):
        source, frames = self.sheet(1, (1, 1))
        result = grid.convert_to_grid(source, frame_count=6, target_grid=(3, 2), solo=True)
        with Image.open(result) as atlas:
            self.assertEqual(atlas.size, (24, 12))
            for index in range(6):
                x, y = index % 3 * 8, index // 3 * 6
                self.assertEqual(atlas.crop((x, y, x + 8, y + 6)).tobytes(),
                                 frames[0].crop((2, 2, 10, 8)).tobytes())

    def test_changed_source_requires_explicit_overwrite(self):
        source, frames = self.sheet(8, (1, 8))
        options = {"frame_count": 8, "source_grid": (1, 8), "target_grid": (4, 2)}
        output = grid.convert_to_grid(source, **options)
        with Image.open(output) as image:
            size = image.size
        with Image.open(source) as image:
            image.putpixel((3, 3), (230, 20, 60, 255))
            image.save(source)
        frames[0].putpixel((3, 3), (230, 20, 60, 255))
        old = (output.read_bytes(), output.stat().st_mtime_ns)
        with self.assertRaisesRegex(ValueError, "bleibt unverändert"):
            grid.convert_to_grid(source, **options)
        self.assertEqual((output.read_bytes(), output.stat().st_mtime_ns), old)
        grid.convert_to_grid(source, **options, overwrite=True)
        with Image.open(output) as result:
            self.assertEqual(result.size, size)
            self.assertEqual(result.crop((0, 0, 8, 6)).tobytes(),
                             frames[0].crop((2, 2, 10, 8)).tobytes())
        before = (output.read_bytes(), output.stat().st_mtime_ns)
        grid.convert_to_grid(source, **options)
        self.assertEqual((output.read_bytes(), output.stat().st_mtime_ns), before)

    def test_cli_dry_run_preflight_repeat_and_overwrite(self):
        source, _ = self.sheet(10, (2, 5))
        output_dir = self.root / "results"
        args = (self.root, "--frames", "10", "--source-grid", "2x5", "--target-grid", "5x2",
                "--optimize", "--output-dir", output_dir)
        before = source.read_bytes()
        self.call(*args, "--dry-run")
        self.assertFalse(output_dir.exists())
        invalid = self.root / "z_invalid.png"
        Image.new("RGBA", (5, 7), "red").save(invalid)
        self.call(*args, expected=1)
        self.assertFalse(output_dir.exists())
        invalid.unlink()
        self.call(*args)
        target = output_dir / "hero_5x2_o.png"
        stat = (target.read_bytes(), target.stat().st_mtime_ns)
        self.call(*args)
        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), stat)
        target.write_bytes(b"broken")
        self.call(*args, "--overwrite")
        with Image.open(target) as atlas:
            self.assertEqual(atlas.size, (40, 12))
        self.assertEqual(source.read_bytes(), before)

    def test_cli_explicit_sheet_with_grid_suffix_and_same_directory_rerun(self):
        source, _ = self.sheet(12, (3, 4), "source_3x4.png")
        self.call(source, "--frames", "12", "--source-grid", "3x4", "--target-grid", "4x3",
                  "--optimize")
        self.assertTrue((self.root / "source_3x4_4x3_o.png").is_file())
        source.unlink()
        plain, _ = self.sheet(8, (1, 8))
        args = ("--frames", "8", "--source-grid", "1x8", "--target-grid", "4x2", "--optimize")
        self.call(*args)
        self.call(*args)
        self.assertEqual(grid.find_spritesheets(self.root), [plain])
        self.assertFalse((self.root / "hero_4x2_o_4x2_o.png").exists())

    def test_cli_help_without_pillow_and_invalid_options(self):
        result = subprocess.run([sys.executable, "-S", str(SCRIPT), "--help"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.call("--frames", "8", "--target-grid", "4x4", expected=1)
        self.call("--frames", "8", "--target-grid", "0x8", expected=2)
        self.call("--frames", "8", "--target-grid", "4x2", "--source-grid", "1x8", "--solo",
                  expected=1)


if __name__ == "__main__":
    unittest.main()
