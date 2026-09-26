"""Reduktion, Phasengrenzen und unveränderliche vorhandene Varianten."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "Pipline/SpritesheetFramReduce-Pipline/PyPiplineStart-SpritesheetFramReduce.py"
spec = importlib.util.spec_from_file_location("frame_reduce_pipeline", STARTER)
pipeline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pipeline
spec.loader.exec_module(pipeline)

EXPECTED_INDICES = {
    8: [0, 2, 4, 6, 8, 10, 12, 14],
    10: [0, 1, 3, 4, 6, 8, 9, 11, 12, 14],
    12: [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14],
    14: [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14],
}


def snapshot(root):
    return {str(p.relative_to(root)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


class ReduceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="reduce-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "comic high # 100% 'test'"
        self.archive = self.root / "spritesheet-fram16/PixelEng"
        self.archive.mkdir(parents=True)

    def strip(self, name="hero_N.png", vertical=False, identical=False):
        frames = []
        image = Image.new("RGBA", (14, 12 * 16) if vertical else (14 * 16, 12))
        for i in range(16):
            frame = Image.new("RGBA", (14, 12))
            if identical:
                ImageDraw.Draw(frame).rectangle((2, 3, 8, 8), fill=(40, 160, 80, 255))
            elif i != 2:
                ImageDraw.Draw(frame).rectangle((2 + i % 3, 3, 8, 8), fill=(20 + i * 12, 160, 80, 255))
                if i == 4:
                    frame.putpixel((10, 9), (13, 25, 39, 1))
                if i == 6:
                    frame.putpixel((9, 4), (210, 30, 50, 128))
                if i == 15:
                    frame.putpixel((0, 0), (200, 240, 120, 255))
            frame.putpixel((5, 5), (121, 90, 61, 0))
            frames.append(frame)
            image.paste(frame, (0, i * 12) if vertical else (i * 14, 0))
        path = self.archive / name
        image.save(path)
        return path, frames

    def call(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(STARTER), *map(str, args)], cwd=self.root,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def variants(self):
        return [pipeline.Variant(count, self.root / f"spritesheet-fram{count}") for count in EXPECTED_INDICES]

    def test_all_variants_preserve_pixels_directions_alpha_and_previews(self):
        originals = {}
        for name, vertical in (("hero run_N_16x1.png", False), ("hero run_S_1x16.PNG", True)):
            path, frames = self.strip(name, vertical)
            originals[path.name] = frames
        # Vorhandene Vorschauen, Archive und optimierte Bilder sind keine Quellen.
        (self.archive / "old.gif").write_bytes(b"not input")
        (self.archive / "archive.zip").write_bytes(b"not input")
        Image.new("RGBA", (1, 1), "red").save(self.archive / "previous_4x4_o.png")
        nested = self.archive / "archive"
        nested.mkdir()
        Image.new("RGBA", (1, 1), "red").save(nested / "archived.png")
        before = snapshot(self.root / "spritesheet-fram16")
        self.call()
        self.assertEqual(snapshot(self.root / "spritesheet-fram16"), before)
        for variant in self.variants():
            info = json.loads((variant.root / "build-info.json").read_text())
            checks = json.loads((variant.root / "pruefung.json").read_text())
            self.assertTrue(checks["passed"])
            self.assertEqual(checks["files_checked"], 2)
            self.assertEqual(info["source_frame_indices"], EXPECTED_INDICES[variant.count])
            self.assertEqual(info["duration_ms"], variant.count * 125)
            self.assertEqual(info["optimized_grid"], list(variant.grid))
            self.assertEqual([x["phase"] for x in info["tool_calls"]], sorted(x["phase"] for x in info["tool_calls"]))
            self.assertTrue((variant.root / "README.md").is_file())
            for name, frames in originals.items():
                selected = [frames[i] for i in EXPECTED_INDICES[variant.count]]
                # Frame 15 ist nicht ausgewählt: dessen äußeres Pixel darf den Zuschnitt nicht aufblähen.
                box = (2, 3, 11, 10)
                optimized = variant.root / f"{Path(name).stem}_{variant.grid[0]}x{variant.grid[1]}_o.png"
                for path, grid, expected in ((variant.archive / name, (variant.count, 1), selected),
                                              (optimized, variant.grid, [f.crop(box) for f in selected])):
                    with Image.open(path) as image:
                        w, h = expected[0].size
                        self.assertEqual(image.size, (w * grid[0], h * grid[1]))
                        for i, frame in enumerate(expected):
                            x, y = i % grid[0] * w, i // grid[0] * h
                            self.assertEqual(image.crop((x, y, x+w, y+h)).tobytes(), frame.tobytes())
                    gif_path = path.with_name(f"{path.stem}_8fps.gif")
                    with Image.open(gif_path) as animation:
                        self.assertEqual(animation.info["loop"], 0)
                        self.assertEqual(json.loads(animation.info["comment"])["source_frames"], variant.count)
                    html = (path.parent / "gif-vergleich.html").read_text()
                    data = json.loads(re.search(r'<script id="gif-data" type="application/json">(.*?)</script>', html, re.S)[1])
                    item = next(i for i in data["items"] if i["gifName"] == gif_path.name)
                    self.assertEqual((item["columns"], item["rows"]), grid)
                    self.assertEqual(item["logicalFrames"], variant.count)
                    self.assertEqual(item["durationMs"], variant.count * 125)
            self.assertEqual(len(list(variant.archive.iterdir())), 5)  # 2 PNG + 2 GIF + HTML

    def test_existing_fram8_is_skipped_completely_including_partial_outputs(self):
        self.strip()
        target = self.root / "spritesheet-fram8"
        (target / "PixelEng").mkdir(parents=True)
        (target / "PixelEng/hero_N.png").write_bytes(b"existing independent eight-frame original")
        (target / "hero_N_4x2_o.png").write_bytes(b"existing optimized output")
        (target / "gif-vergleich.html").write_text("existing gallery")
        before = snapshot(target)
        result = self.call()
        self.assertIn("[SKIP] spritesheet-fram8", result.stdout)
        self.assertEqual(snapshot(target), before)
        self.assertFalse((target / "build-info.json").exists())
        self.assertTrue((self.root / "spritesheet-fram14/pruefung.json").exists())

    def test_files_in_nested_or_metadata_only_targets_also_skip_whole_variant(self):
        self.strip()
        for count, location in ((8, "PixelEng/only.gif"), (10, "README.md"), (12, "archive/old.png")):
            target = self.root / f"spritesheet-fram{count}" / location
            target.parent.mkdir(parents=True)
            target.write_bytes(b"keep")
        before = {v.count: snapshot(v.root) for v in self.variants() if v.count != 14}
        self.call()
        for count, saved in before.items():
            self.assertEqual(snapshot(self.root / f"spritesheet-fram{count}"), saved)
        self.assertTrue((self.root / "spritesheet-fram14/pruefung.json").exists())

    def test_existing_empty_directories_are_reused_and_second_run_changes_nothing(self):
        self.strip()
        for variant in self.variants():
            variant.archive.mkdir(parents=True)
        self.call()
        before = snapshot(self.root)
        result = self.call()
        self.assertEqual(result.stdout.count("[SKIP]"), 4)
        self.assertEqual(snapshot(self.root), before)

    def test_all_skipped_succeeds_even_without_source_directory(self):
        shutil.rmtree(self.root / "spritesheet-fram16")
        for variant in self.variants():
            variant.root.mkdir()
            (variant.root / "keep.png").write_bytes(b"keep")
        before = snapshot(self.root)
        result = self.call()
        self.assertIn("nichts geändert", result.stdout)
        self.assertEqual(snapshot(self.root), before)

    def test_dry_run_and_subset_never_create_unselected_variants(self):
        self.strip()
        before = snapshot(self.root)
        self.call("--frames", "10", "14", "--dry-run")
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse((self.root / "spritesheet-fram10").exists())
        self.call("--frames", "10", "14")
        self.assertFalse((self.root / "spritesheet-fram8").exists())
        self.assertFalse((self.root / "spritesheet-fram12").exists())
        self.assertTrue((self.root / "spritesheet-fram10/pruefung.json").is_file())

    def test_target_links_and_foreign_files_are_skipped(self):
        self.strip()
        external = Path(self.temp.name) / "outside"
        external.mkdir()
        (external / "keep.png").write_bytes(b"keep")
        (self.root / "spritesheet-fram8").symlink_to(external, target_is_directory=True)
        (self.root / "spritesheet-fram10").mkdir()
        (self.root / "spritesheet-fram10/PixelEng").symlink_to(external, target_is_directory=True)
        (self.root / "spritesheet-fram12").write_bytes(b"foreign file")
        before = snapshot(external)
        self.call()
        self.assertEqual(snapshot(external), before)
        self.assertEqual((self.root / "spritesheet-fram12").read_bytes(), b"foreign file")
        self.assertTrue((self.root / "spritesheet-fram14/pruefung.json").is_file())

    def test_invalid_inputs_fail_before_any_target_is_created(self):
        self.strip()
        invalid = self.archive / "invalid.png"
        for kind in ("corrupt", "dimensions", "transparent", "selected_transparent", "animated"):
            with self.subTest(kind=kind):
                if kind == "corrupt":
                    invalid.write_bytes(b"broken")
                elif kind == "dimensions":
                    Image.new("RGBA", (17, 3), "red").save(invalid)
                elif kind == "transparent":
                    Image.new("RGBA", (160, 10)).save(invalid)
                elif kind == "selected_transparent":
                    image = Image.new("RGBA", (160, 10))
                    image.putpixel((159, 5), (255, 0, 0, 255))
                    image.save(invalid)
                else:
                    Image.new("RGBA", (160, 10), "red").save(
                        invalid, save_all=True, append_images=[Image.new("RGBA", (160, 10), "blue")], duration=100)
                before = snapshot(self.root)
                self.call(expected=1)
                self.assertEqual(snapshot(self.root), before)
                for variant in self.variants():
                    self.assertFalse(variant.root.exists())

    def test_colliding_stems_fail_without_modifying_sources(self):
        original, _ = self.strip()
        shutil.copy2(original, original.with_suffix(".PNG"))
        before = snapshot(self.root)
        self.call(expected=1)
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse((self.root / "spritesheet-fram8").exists())

    def test_missing_source_fails_without_creating_targets(self):
        self.call(expected=1)
        self.assertFalse((self.root / "spritesheet-fram8").exists())

    def test_manual_vertical_grid_for_wide_cells(self):
        image = Image.new("RGBA", (200, 64))
        for i in range(16):
            image.paste((10 + i * 12, 50, 100, 255), (0, i * 4, 200, (i + 1) * 4))
        image.save(self.archive / "wide.png")
        self.call("--frames", "10", "--grid", "1x16")
        with Image.open(self.root / "spritesheet-fram10/PixelEng/wide.png") as result:
            self.assertEqual(result.size, (2000, 4))
            for i, index in enumerate(EXPECTED_INDICES[10]):
                self.assertEqual(result.getpixel((i*200, 0)), (10 + index * 12, 50, 100, 255))

    def test_identical_frames_retain_logical_count_and_duration(self):
        self.strip(identical=True)
        self.call()
        for variant in self.variants():
            checks = json.loads((variant.root / "pruefung.json").read_text())
            for output in checks["files"][0]["outputs"]:
                self.assertEqual(output["gif_check"]["logical_frames"], variant.count)
                self.assertEqual(output["gif_check"]["duration_ms"], variant.count * 125)

    def test_help_without_pillow_and_no_html_switch_rejected(self):
        result = subprocess.run([sys.executable, "-S", str(STARTER), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("überspringen", result.stdout)
        self.assertIn("--overwrite", result.stdout)
        for args in (("--no-html",), ("--frames", "16"), ("--grid", "4x4")):
            self.call(*args, expected=2)
        self.assertFalse((self.root / "spritesheet-fram8").exists())

    def test_global_phase_barriers_for_every_variant_and_direction(self):
        self.strip()
        self.strip("hero_S.png", vertical=True)
        variants = self.variants()
        sources = list(self.archive.glob("*.png"))
        events = []
        copy_original = pipeline.copy_original
        reduce_copy = pipeline.select.reduce_copy
        previews = pipeline.make_previews
        optimize = pipeline.raster.convert_to_grid
        verify = pipeline.verify_variant

        def copy(source, destination, **kwargs):
            self.assertTrue(all(v.archive.is_dir() for v in variants))
            events.append(2)
            return copy_original(source, destination, **kwargs)

        def reduce(path, **kwargs):
            if 3 not in events:
                for v in variants:
                    for src in sources:
                        self.assertEqual((v.archive / src.name).read_bytes(), src.read_bytes())
            events.append(3)
            return reduce_copy(path, **kwargs)

        def preview(paths, grid, directory, calls, phase, **kwargs):
            if phase == 4 and 4 not in events:
                for v in variants:
                    for src in sources:
                        with Image.open(v.archive / src.name) as image:
                            self.assertEqual(image.size, (14 * v.count, 12))
            if phase == 6:
                self.assertTrue(all(len(list(v.root.glob("*_o.png"))) == len(sources) for v in variants))
            events.append(phase)
            return previews(paths, grid, directory, calls, phase, **kwargs)

        def pack(*args, **kwargs):
            self.assertTrue(all((v.archive / "gif-vergleich.html").is_file() for v in variants))
            self.assertTrue(all(len(list(v.archive.glob("*.gif"))) == len(sources) for v in variants))
            events.append(5)
            return optimize(*args, **kwargs)

        def check(*args):
            self.assertTrue(all((v.root / "gif-vergleich.html").is_file() for v in variants))
            self.assertTrue(all(len(list(v.root.glob("*.gif"))) == len(sources) for v in variants))
            events.append(7)
            return verify(*args)

        with patch.object(pipeline, "copy_original", side_effect=copy), \
                patch.object(pipeline.select, "reduce_copy", side_effect=reduce), \
                patch.object(pipeline, "make_previews", side_effect=preview), \
                patch.object(pipeline.raster, "convert_to_grid", side_effect=pack), \
                patch.object(pipeline, "verify_variant", side_effect=check), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pipeline.main([str(self.root)]), 0)
        self.assertEqual(events, sorted(events))
        self.assertEqual(set(events), {2, 3, 4, 5, 6, 7})

    def test_damaged_copy_prevents_any_reduction(self):
        self.strip()
        original = pipeline.copy_original

        def bad_copy(source, destination, **kwargs):
            original(source, destination, **kwargs)
            if "spritesheet-fram14" in str(destination):
                destination.write_bytes(b"incomplete copy")

        before = snapshot(self.archive)
        with patch.object(pipeline, "copy_original", side_effect=bad_copy), \
                patch.object(pipeline.select, "reduce_copy") as reduce, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(pipeline.main([str(self.root)]), 1)
            reduce.assert_not_called()
        self.assertEqual(snapshot(self.archive), before)

    def test_failed_gif_phase_does_not_start_optimization(self):
        self.strip()
        with patch.object(pipeline.gif, "run_sheets", return_value=1), \
                patch.object(pipeline.raster, "convert_to_grid") as optimize, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(pipeline.main([str(self.root)]), 1)
            optimize.assert_not_called()
        for variant in self.variants():
            self.assertFalse((variant.root / "pruefung.json").exists())

    def test_verifier_detects_wrong_gif_order_even_with_valid_metadata(self):
        self.strip()
        self.call("--frames", "10")
        variant = pipeline.Variant(10, self.root / "spritesheet-fram10")
        png = variant.archive / "hero_N.png"
        frames, _, _ = pipeline.raster.read_frames(png, frame_count=10, source_grid=(10, 1))
        animation = png.with_name("hero_N_8fps.gif")
        # Zwei Frames mit derselben Alpha-Maske, aber unterschiedlichen Farben vertauschen.
        wrong_order = frames.copy()
        wrong_order[0], wrong_order[8] = wrong_order[8], wrong_order[0]
        pipeline.gif.save_gif(wrong_order, animation, 8)
        with self.assertRaisesRegex(ValueError, "GIF-Inhalt oder Reihenfolge falsch"):
            pipeline.verify_gif(animation, frames)

    def test_verifier_detects_wrong_html_grid(self):
        self.strip()
        self.call("--frames", "10")
        root = self.root / "spritesheet-fram10"
        html = root / "gif-vergleich.html"
        html.write_text(html.read_text().replace('"columns":5', '"columns":4'))
        with self.assertRaisesRegex(ValueError, "HTML-Raster"):
            pipeline.verify_html(root, [root / "hero_N_5x2_o.png"], (5, 2))


class FrameSelectionTests(unittest.TestCase):
    def test_uniform_selection_is_unique_ordered_and_cyclically_balanced(self):
        for count, expected in EXPECTED_INDICES.items():
            indices = pipeline.select.uniform_indices(16, count)
            self.assertEqual(indices, expected)
            self.assertEqual(len(set(indices)), count)
            gaps = [b-a for a,b in zip(indices, indices[1:] + [16])]
            self.assertLessEqual(max(gaps) - min(gaps), 1)

    def test_invalid_counts_do_not_pad_or_repeat_frames(self):
        for source, target in ((16, 0), (16, 17), (0, 8), (16, -2)):
            with self.assertRaises(ValueError):
                pipeline.select.uniform_indices(source, target)


if __name__ == "__main__":
    unittest.main()
