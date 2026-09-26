"""Funktions- und Integrationstests mit selbst erzeugten PNG-Spritesheets."""
from __future__ import annotations

import hashlib
import contextlib
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
from urllib.parse import unquote

from PIL import Image, ImageDraw


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS.parent / "PiplineToos"))
GIF_SCRIPT = SCRIPTS.parent / "PiplineToos" / "PyImgGif.py"
LAYOUTS = {8: (4, 2), 10: (5, 2), 12: (4, 3), 14: (7, 2), 16: (4, 4)}
VARIANTS = ("comic_mid", "comic_low", "pixel_high", "pixel_low")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def comparison_data(root):
    html = (root / "aufloesungsvergleich.html").read_text()
    match = re.search(r'<script id="comparison-data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(match[1])


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pygraphics-test-")
        self.addCleanup(self.temp.cleanup)
        self.stand = Path(self.temp.name) / "stand mit Leerzeichen"
        self.high = self.stand / "comic_high"
        self.high.mkdir(parents=True)

    def sheet(self, count=8, size=(25, 19), name=None, grid=None):
        columns, rows = grid or LAYOUTS[count]
        folder = self.high / f"spritesheet-fram{count}"
        folder.mkdir(exist_ok=True)
        path = folder / (name or f"greenhero_hd_stand_spritesheet_N_{columns}x{rows}_o.png")
        image = Image.new("RGBA", (columns * size[0], rows * size[1]))
        draw = ImageDraw.Draw(image)
        for index in range(count):
            x, y = index % columns * size[0], index // columns * size[1]
            color = ((index * 37 + 30) % 256, (index * 71 + 60) % 256, (index * 113 + 90) % 256, 255)
            draw.rectangle((x + 2, y + 2, x + size[0] - 3, y + size[1] - 3), fill=color)
        image.save(path)
        image.close()
        return path

    def call(self, *args, script="PyPiplineStart-SpritesheetResolution.py", source=True, cwd=None, expected=0):
        command = [sys.executable, str(SCRIPTS / script)]
        if source:
            command.append(str(self.stand))
        result = subprocess.run(command + list(map(str, args)), cwd=cwd, text=True,
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def target(self, source, variant):
        return self.stand / variant / source.relative_to(self.high)

    def single(self, name="greenhero_hd_stand_N.png", size=(256, 128)):
        path = self.high / name
        with Image.new("RGBA", size) as image:
            draw = ImageDraw.Draw(image)
            draw.rectangle((2, 2, size[0] - 3, size[1] - 3), fill=(210, 65, 30, 160))
            draw.rectangle((size[0] // 3, size[1] // 3, size[0] * 2 // 3, size[1] * 2 // 3),
                           fill=(25, 190, 80, 255))
            image.save(path)
        return path

    def test_single_images_without_sheets_create_variants_and_static_html(self):
        sources = [self.single(f"greenhero_hd_stand_{direction}.png")
                   for direction in ("N", "NO", "O", "SO", "S", "SW", "W", "NW")]
        hashes = {path: digest(path) for path in sources}
        # Einzelbilder brauchen weder Rastererkennung noch das GIF-Unterprogramm.
        self.call("--gif-script", self.stand / "nicht-vorhanden.py")
        sizes = {"comic_mid": (128, 64), "comic_low": (64, 32),
                 "pixel_high": (128, 64), "pixel_low": (115, 58)}
        for source in sources:
            for variant, size in sizes.items():
                with Image.open(self.target(source, variant)) as image:
                    self.assertEqual(image.size, size)
                    alpha = set(image.getchannel("A").tobytes())
                    if variant.startswith("pixel"):
                        self.assertEqual(alpha, {0, 255})
                        visible = {c[:3] for _, c in image.getcolors(image.width * image.height) if c[3]}
                        self.assertLessEqual(len(visible), 64)
                    else:
                        self.assertIn(160, alpha)
            with Image.open(self.target(source, "pixel_high")) as high, \
                    Image.open(self.target(source, "pixel_low")) as low:
                self.assertTrue({c for _, c in low.getcolors(low.width * low.height)} <=
                                {c for _, c in high.getcolors(high.width * high.height)})
        self.assertEqual(hashes, {path: digest(path) for path in sources})
        self.assertEqual(len(list(self.stand.rglob("*.png"))), 40)
        self.assertFalse(list(self.stand.rglob("*.gif")))
        self.assertEqual(len(list(self.stand.rglob("*.html"))), 1)
        self.assertFalse(list(self.stand.rglob("*-bilder")))
        data = comparison_data(self.stand)
        self.assertEqual(len(data["sets"]), 1)
        group = data["sets"][0]
        self.assertTrue(group["single"])
        self.assertEqual(group["frames"], 1)
        self.assertEqual(len(group["directions"]), 8)
        for source in sources:
            direction = source.stem.rsplit("_", 1)[1]
            for variant, item in group["directions"][direction].items():
                expected = source if variant == "comic_high" else self.target(source, variant)
                self.assertEqual(self.stand / unquote(item["sheet"]), expected)
                self.assertEqual((item["columns"], item["rows"]), (1, 1))
                self.assertIsNone(item["gif"])
        self.assertNotIn("data:image/", (self.stand / "aufloesungsvergleich.html").read_text())

    def test_mixed_inputs_keep_single_images_out_of_gif_processing(self):
        single = self.single("Bild # 100% geprüft_4x4_N.png", size=(257, 129))
        sheet = self.sheet(8)
        omitted = self.sheet(16)
        self.call("--dry-run")
        self.assertEqual(set(self.stand.iterdir()), {self.high})
        self.call("--frames", "8", "--grid", "4x2")
        for variant in VARIANTS:
            root = self.stand / variant
            self.assertTrue(self.target(single, variant).is_file())
            self.assertTrue(self.target(sheet, variant).is_file())
            self.assertFalse(self.target(omitted, variant).exists())
            self.assertFalse(list(root.glob("*.gif")))
            self.assertFalse((root / "gif-vergleich.html").exists())
            self.assertEqual(len(list(root.rglob("*.gif"))), 1)
        groups = comparison_data(self.stand)["sets"]
        self.assertEqual([group["frames"] for group in groups], [8, 1])
        self.assertEqual(groups[1]["directions"]["N"]["comic_high"]["width"], 257)
        linked = groups[1]["directions"]["N"]["comic_high"]["sheet"]
        self.assertIn("%23", linked)
        self.assertEqual(self.stand / unquote(linked), single)

    def test_single_workers_output_root_overwrite_and_compare_only(self):
        single = self.single()
        output = Path(self.temp.name) / "separate Ausgabe #"
        self.call("--dry-run", "--output-root", output)
        self.assertFalse(output.exists())
        for script, variant, size in (("SComicMid.py", "comic_mid", (128, 64)),
                                     ("SComicLow.py", "comic_low", (64, 32)),
                                     ("SPixelHigh.py", "pixel_high", (128, 64)),
                                     ("SPixelLow.py", "pixel_low", (115, 58))):
            self.call("--no-gif", "--output-root", output, script=script)
            with Image.open(output / variant / single.name) as image:
                self.assertEqual(image.size, size)
        self.assertFalse(list(output.rglob("*.html")))
        files = {p: (digest(p), p.stat().st_mtime_ns) for p in output.rglob("*.png")}
        self.single(size=(512, 256))
        self.call("--no-gif", "--output-root", output)
        self.assertEqual(files, {p: (digest(p), p.stat().st_mtime_ns) for p in files})
        self.call("--compare-only", "--output-root", output)
        self.assertEqual(files, {p: (digest(p), p.stat().st_mtime_ns) for p in files})
        item = comparison_data(output)["sets"][0]["directions"]["N"]["comic_high"]
        self.assertEqual((output / unquote(item["sheet"])).resolve(), single)
        self.call("--overwrite", "--no-gif", "--output-root", output)
        with Image.open(output / "comic_mid" / single.name) as image:
            self.assertEqual(image.size, (256, 128))

    def test_single_input_validation_before_any_output_and_ignored_files(self):
        self.sheet()
        self.single()
        invalid = self.high / "broken.png"
        invalid.write_bytes(b"not a PNG")
        self.call(expected=1)
        self.assertEqual(set(self.stand.iterdir()), {self.high})
        invalid.unlink()
        for directory in (self.high / ".archive", self.high / "PixelEng"):
            directory.mkdir()
            (directory / "broken.png").write_bytes(b"not a PNG")
        (self.high / ".hidden.png").write_bytes(b"not a PNG")
        (self.high / "linked.png").symlink_to(self.high / ".hidden.png")
        self.call("--no-gif")
        for variant in VARIANTS:
            self.assertEqual(len(list((self.stand / variant).rglob("*.png"))), 2)

    def test_all_layouts_all_directions_and_real_gif_html(self):
        sources = [self.sheet(count, name=f"greenhero_hd_stand_spritesheet_{direction}_{c}x{r}_o.png")
                   for count, (c, r) in LAYOUTS.items()
                   for direction in ("N", "NO", "O", "SO", "S", "SW", "W", "NW")]
        original_hashes = {path: digest(path) for path in sources}
        # Dateien aus dem Beispielbaum, die nicht als Eingabe dienen dürfen.
        for folder in (self.high / ".archive", sources[0].parent / "PixelEng"):
            folder.mkdir()
            (folder / "unlesbar.png").write_bytes(b"kein PNG")
        (sources[0].parent / "alte_vorschau.gif").write_bytes(b"kein GIF")
        (self.stand / "greenhero_hd_stand_N.png").write_bytes(b"kein Spritesheet")
        self.call("--pixel-high-size", "12", "--pixel-low-size", "6")
        expected_frames = {"comic_mid": (13, 10), "comic_low": (6, 5),
                           "pixel_high": (12, 9), "pixel_low": (6, 5)}
        for variant in VARIANTS:
            self.assertEqual(len(list((self.stand / variant).glob("spritesheet-fram*/*.png"))), 40)
            self.assertEqual(len(list((self.stand / variant).rglob("*.gif"))), 40)
            self.assertEqual(len(list((self.stand / variant).rglob("*.html"))), 5)
            for source in sources:
                count = int(source.parent.name.removeprefix("spritesheet-fram"))
                c, r = LAYOUTS[count]
                width, height = expected_frames[variant]
                output = self.target(source, variant)
                with Image.open(output) as image:
                    self.assertEqual(image.size, (c * width, r * height))
                    self.assertEqual(image.mode, "RGBA")
                with Image.open(output.with_name(output.stem + "_8fps.gif")) as gif:
                    self.assertEqual(gif.size, (width, height))
                    self.assertEqual(gif.info["loop"], 0)
                    self.assertEqual(json.loads(gif.info["comment"])["source_frames"], count)
                    duration = 0
                    for frame in range(gif.n_frames):
                        gif.seek(frame)
                        duration += gif.info["duration"]
                    self.assertEqual(duration, count * 125)
                html = (output.parent / "gif-vergleich.html").read_text()
                self.assertIn(output.stem + "_8fps.gif", html)
                self.assertNotIn("data:image/", html)
                self.assertNotIn("gif-vergleich-bilder/", html)
                self.assertIn(output.name, html)
        self.assertEqual(original_hashes, {path: digest(path) for path in sources})
        comparison = comparison_data(self.stand)
        self.assertEqual(len(comparison["sets"]), 5)
        for group in comparison["sets"]:
            self.assertEqual(set(group["directions"]), {"N", "NO", "O", "SO", "S", "SW", "W", "NW"})
            for tracks in group["directions"].values():
                self.assertEqual(set(tracks), {"comic_high", *VARIANTS})
                self.assertTrue(all("gif" in track for track in tracks.values()))
        self.assertEqual(len(list(self.high.rglob("*.gif"))), 1)  # Nur die zuvor angelegte alte_vorschau.gif.
        self.assertFalse((self.stand / "aufloesungsvergleich-bilder").exists())
        self.assertFalse(list(self.stand.rglob("*-bilder")))

    def test_frame_boundaries_order_and_partial_alpha(self):
        source = self.sheet(size=(17, 17))
        with Image.open(source) as original:
            image = Image.new("RGBA", original.size)
        colors = [(255, 0, 0, 128), (0, 255, 0, 128), (0, 0, 255, 128), (255, 255, 0, 128)] * 2
        for index, color in enumerate(colors):
            image.paste(color, (index % 4 * 17, index // 4 * 17,
                                (index % 4 + 1) * 17, (index // 4 + 1) * 17))
        image.save(source)
        self.call("--variants", "comic_mid", "comic_low", "--no-gif")
        for variant, side in (("comic_mid", 9), ("comic_low", 4)):
            with Image.open(self.target(source, variant)) as result:
                for index, color in enumerate(colors):
                    box = (index % 4 * side, index // 4 * side,
                           (index % 4 + 1) * side, (index // 4 + 1) * side)
                    self.assertEqual(result.crop(box).getcolors(), [(side * side, color)])

    def test_pixel_palette_and_binary_alpha(self):
        source = self.sheet(size=(80, 60))
        image = Image.new("RGBA", (320, 120))
        image.putdata([((x * 11) % 256, (y * 7) % 256, (x + y) % 256, (x * 3 + y) % 256)
                       for y in range(120) for x in range(320)])
        image.save(source)
        self.call("--variants", "pixel_high", "pixel_low", "--pixel-high-size", "32",
                  "--pixel-low-size", "16", "--pixel-low-colors", "16", "--no-gif")
        for variant, limit in (("pixel_high", 64), ("pixel_low", 16)):
            with Image.open(self.target(source, variant)) as result:
                self.assertEqual(set(result.getchannel("A").tobytes()), {0, 255})
                visible = {pixel[:3] for _, pixel in result.getcolors(result.width * result.height) if pixel[3]}
                self.assertLessEqual(len(visible), limit)

    def test_each_worker_defaults_and_current_folder(self):
        source = self.sheet(size=(256, 128))
        for script, variant, size in (("SComicMid.py", "comic_mid", (128, 64)),
                                     ("SComicLow.py", "comic_low", (64, 32)),
                                     ("SPixelHigh.py", "pixel_high", (128, 64)),
                                     ("SPixelLow.py", "pixel_low", (115, 58))):
            self.call("--no-gif", script=script, source=False, cwd=self.stand)
            with Image.open(self.target(source, variant)) as output:
                self.assertEqual(output.size, (size[0] * 4, size[1] * 2))

    def test_small_frames_are_not_upscaled(self):
        source = self.sheet(size=(10, 8))
        self.call("--variants", "pixel_high", "pixel_low", "--no-gif")
        for variant, size in (("pixel_high", (40, 16)), ("pixel_low", (36, 14))):
            with Image.open(self.target(source, variant)) as output:
                self.assertEqual(output.size, size)

    def test_low_uses_high_palette_without_new_color_values(self):
        source = self.sheet(size=(256, 128))
        with Image.open(source) as image:
            image = image.convert("RGBA")
            for y in range(20, 110):
                for x in range(20, 230):
                    image.putpixel((x, y), ((x + y) % 256, (x * 2) % 256, (y * 2) % 256, 255))
            image.save(source)
        self.call("--variants", "pixel_high", "pixel_low", "--no-gif")
        with Image.open(self.target(source, "pixel_high")) as high:
            high_pixels = {color for _, color in high.getcolors(high.width * high.height)}
        with Image.open(self.target(source, "pixel_low")) as low:
            low_pixels = {color for _, color in low.getcolors(low.width * low.height)}
            self.assertEqual(low.size, (460, 116))
            self.assertTrue(low_pixels <= high_pixels)
        self.call("--variants", "pixel_high", "pixel_low", "--pixel-high-size", "80",
                  "--pixel-high-colors", "32", "--overwrite", "--no-gif")
        with Image.open(self.target(source, "pixel_high")) as high:
            high_pixels = {color for _, color in high.getcolors(high.width * high.height)}
        with Image.open(self.target(source, "pixel_low")) as low:
            self.assertEqual(low.size, (288, 72))
            self.assertTrue({color for _, color in low.getcolors(low.width * low.height)} <= high_pixels)

    def test_dry_run_and_frame_selection_and_folder_grid_fallback(self):
        selected = self.sheet(8, name="hero.png")
        self.sheet(16)
        self.call("--dry-run")
        self.assertEqual(set(self.stand.iterdir()), {self.high})
        self.call("--frames", "8", "--variants", "comic_low", "--no-gif")
        self.assertTrue(self.target(selected, "comic_low").is_file())
        self.assertFalse((self.stand / "comic_low" / "spritesheet-fram16").exists())

    def test_existing_outputs_and_direct_hd_source(self):
        source = self.sheet()
        self.call("--no-gif")
        low = self.target(source, "comic_low")
        low_hash = digest(low)
        mid = self.target(source, "comic_mid")
        Image.new("RGBA", (4, 2), "magenta").save(mid)
        before = mid.read_bytes()
        self.call("--no-gif")
        self.assertEqual(mid.read_bytes(), before)
        self.call("--no-gif", "--overwrite", script="SComicLow.py")
        self.assertEqual(digest(low), low_hash)
        self.call("--no-gif", "--overwrite", script="SComicMid.py")
        with Image.open(mid) as result:
            self.assertEqual(result.size, (52, 20))

    def test_manual_grid_and_filename_grid_override_folder_default(self):
        source = self.sheet(16, size=(15, 11), grid=(8, 2))
        self.call("--variants", "comic_mid", "--no-gif")
        with Image.open(self.target(source, "comic_mid")) as output:
            self.assertEqual(output.size, (64, 12))
        source.rename(source.with_name("hero_4x4.png"))
        self.call("--grid", "8x2", "--variants", "comic_low", "--no-gif")

    def test_invalid_and_corrupt_input_fail_before_writes(self):
        self.sheet(8)
        invalid = self.sheet(16)
        invalid.write_bytes(b"unlesbares Bild")
        self.call("--no-gif", expected=1)
        self.assertEqual(set(self.stand.iterdir()), {self.high})
        invalid.unlink()
        invalid = self.sheet(16)
        Image.new("RGBA", (101, 100)).save(invalid)
        self.call("--no-gif", expected=1)
        self.assertEqual(set(self.stand.iterdir()), {self.high})

    def test_missing_gif_script_and_invalid_options(self):
        self.sheet()
        self.call("--gif-script", self.stand / "fehlt.py", expected=1)
        self.assertEqual(set(self.stand.iterdir()), {self.high})
        for args in (("--comic-mid-scale", "nan"), ("--comic-low-scale", "0"),
                     ("--pixel-low-size", "0"), ("--pixel-high-colors", "257"),
                     ("--grid", "1x1"), ("--fps", "9")):
            self.call(*args, expected=2)
        self.call("--no-gif", "--frames", "8", "16", expected=1)
        self.call("--no-gif", "--gif-script", self.stand / "fehlt.py")

    def test_all_requested_fps_export_and_recover_logical_frames(self):
        import PyImgGif

        source = self.sheet()
        for fps in (2, 4, 6, 8, 10, 12, 16, 18, 20, 22, 24):
            with self.subTest(fps=fps):
                self.call("--variants", "comic_mid", "--fps", fps, "--overwrite")
                output = self.target(source, "comic_mid").with_name(f"{source.stem}_{fps}fps.gif")
                track = PyImgGif.read_gif_for_gallery(output)
                self.assertEqual(track["exportFps"], fps)
                self.assertEqual(track["logicalFrames"], 8)
                self.assertLessEqual(abs(track["durationMs"] - 8000 / fps), 5)
                self.assertTrue(all(duration > 0 and duration % 10 == 0 for duration in track["durations"]))
                self.assertEqual(comparison_data(self.stand)["fps"], fps)

                # Gleichartige Nachbarframes werden im GIF zusammengefasst;
                # die steuerbare HTML-Vorschau muss trotzdem alle Quellframes kennen.
                frames = [Image.new("RGBA", (4, 4), color)
                          for color in ("red", "red", "blue", "blue")]
                self.addCleanup(lambda images=frames: [image.close() for image in images])
                merged = self.stand / "merged.gif"
                PyImgGif.save_gif(frames, merged, fps)
                recovered = PyImgGif.read_gif_for_gallery(merged)
                self.assertEqual(recovered["exportFps"], fps)
                self.assertEqual(recovered["frameMap"], [0, 0, 1, 1])
                self.assertEqual(recovered["logicalFrames"], 4)

    def test_html_reuses_spritesheets_without_writing_or_embedding_images(self):
        import PyGraphicsCompare
        from importlib import import_module
        pipeline = import_module("PyPiplineStart-SpritesheetResolution")
        import PyImgGif

        source = self.sheet()
        self.call("--no-gif")
        original_hashes = {path: digest(path) for path in self.stand.rglob("*.png")}
        pipeline.load_pillow()
        sheets = pipeline.inspect_sheets([source.parent], None)
        with patch.object(Image.Image, "save", side_effect=AssertionError("Keine Bildkopien")), \
                patch.object(PyImgGif, "convert_sheet", side_effect=AssertionError("Keine GIF-Erstellung")), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(PyGraphicsCompare.build_comparison(self.stand, self.high, sheets, 8), 0)
        comparison = comparison_data(self.stand)
        for name, track in comparison["sets"][0]["directions"]["N"].items():
            expected = source if name == "comic_high" else self.target(source, name)
            self.assertEqual(self.stand / unquote(track["sheet"]), expected)
            self.assertEqual((track["columns"], track["rows"]), (4, 2))
            self.assertEqual(track["logicalFrames"], 8)
            self.assertIsNone(track["gif"])
            self.assertNotIn("images", track)
            with Image.open(expected) as image:
                self.assertEqual((track["width"] * 4, track["height"] * 2), image.size)
        self.assertEqual(original_hashes, {path: digest(path) for path in self.stand.rglob("*.png")})
        self.assertFalse(list(self.stand.rglob("*.gif")))
        self.assertFalse(list(self.stand.rglob("*-bilder")))
        self.assertNotIn("data:image/", (self.stand / "aufloesungsvergleich.html").read_text())

        self.call("--variants", "comic_mid")
        gif_folder = self.target(source, "comic_mid").parent
        output = gif_folder / "Vorschau # 100%.html"
        files = {path: digest(path) for path in self.stand.rglob("*") if path.is_file()}
        with patch.object(Image.Image, "save", side_effect=AssertionError("Keine Bildkopien")), contextlib.redirect_stdout(io.StringIO()):
            result = PyImgGif.build_html_gallery(gif_folder, output)
        self.assertEqual((result.included, result.skipped), (1, 0))
        payload = json.loads(re.search(r'<script id="gif-data" type="application/json">(.*?)</script>', output.read_text(), re.S)[1])
        item = payload["items"][0]
        self.assertEqual(item["sheet"], source.name)
        self.assertEqual(item["gif"], source.stem + "_8fps.gif")
        self.assertEqual(files, {path: digest(path) for path in files})
        self.assertEqual({path for path in self.stand.rglob("*") if path.is_file()} - set(files), {output})
        self.assertNotIn("data:image/", output.read_text())

        copied = Path(self.temp.name) / "kopiert mit Leerzeichen # und %"
        shutil.copytree(self.stand, copied)
        for track in comparison["sets"][0]["directions"]["N"].values():
            self.assertTrue((copied / unquote(track["sheet"])).is_file())

    def test_legacy_cache_cleanup_preserves_unrelated_files_and_links(self):
        source = self.sheet()
        self.call("--no-gif")
        cache = self.stand / "aufloesungsvergleich-bilder"
        cache.mkdir()
        original = source.read_bytes()
        generated = cache / (hashlib.sha256(original).hexdigest() + ".png")
        generated.write_bytes(original)
        modified = cache / ("1" * 64 + ".png")
        modified.write_bytes(b"von Hand geaendert")
        note = cache / "behalten.txt"
        note.write_text("behalten")
        link = cache / ("2" * 64 + ".png")
        link.symlink_to(source)
        subfolder = cache / "eigene-dateien"
        subfolder.mkdir()
        (subfolder / generated.name).write_bytes(original)
        self.call("--compare-only")
        self.assertEqual(generated.read_bytes(), original)
        self.call("--compare-only", "--overwrite")
        self.assertFalse(generated.exists())
        self.assertEqual(modified.read_bytes(), b"von Hand geaendert")
        self.assertEqual(note.read_text(), "behalten")
        self.assertTrue(link.is_symlink())
        self.assertTrue((subfolder / generated.name).exists())
        self.assertEqual(source.read_bytes(), original)

    def test_legacy_cache_removed_only_after_successful_html_write(self):
        import PyImgGif

        source = self.sheet()
        self.call("--variants", "comic_mid")
        folder = self.target(source, "comic_mid").parent
        output = folder / "gif-vergleich.html"
        cache = folder / "gif-vergleich-bilder"
        cache.mkdir()
        data = source.read_bytes()
        generated = cache / (hashlib.sha256(data).hexdigest() + ".png")
        generated.write_bytes(data)
        output.unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            PyImgGif.build_html_gallery(folder, output)
        self.assertEqual(generated.read_bytes(), data)
        html_before = output.read_bytes()
        with patch.object(PyImgGif.os, "replace", side_effect=OSError("Test: Schreiben fehlgeschlagen")), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(OSError):
                PyImgGif.build_html_gallery(folder, output, overwrite=True)
        self.assertTrue(generated.exists())
        self.assertEqual(output.read_bytes(), html_before)
        with contextlib.redirect_stdout(io.StringIO()):
            PyImgGif.build_html_gallery(folder, output, overwrite=True)
        self.assertFalse(cache.exists())

    def test_gallery_without_source_links_native_gif_without_frame_files(self):
        import PyImgGif

        source = self.sheet()
        self.call("--variants", "comic_mid")
        gif = self.target(source, "comic_mid").with_name(source.stem + "_8fps.gif")
        orphan = self.stand / "ohne_spritesheet.gif"
        shutil.copy2(gif, orphan)
        item = PyImgGif.gallery_preview(orphan, self.stand / "native.html")
        self.assertIsNone(item["sheet"])
        self.assertEqual(item["gif"], orphan.name)
        self.assertNotIn("images", item)
        self.assertTrue(any("ohne" in note.lower() for note in item["notes"]))

    def test_sheet_preview_keeps_blank_and_repeated_cells(self):
        import PyImgGif

        source = self.sheet()
        with Image.open(source) as image:
            image.paste(image.crop((0, 0, 25, 19)), (25, 0))
            image.paste((0, 0, 0, 0), (50, 0, 75, 19))
            image.save(source)
        gif = source.with_name(source.stem + "_8fps.gif")
        PyImgGif.convert_sheet(source, gif, 8, PyImgGif.Grid(4, 2, "Test"))
        item = PyImgGif.gallery_preview(gif, self.stand / "preview.html")
        self.assertEqual(item["logicalFrames"], 8)
        self.assertEqual(item["frameMap"], list(range(8)))
        self.assertLess(item["storedFrames"], 8)
        self.assertTrue(any("Leerzellen" in note for note in item["notes"]))

    def test_gallery_recovers_manual_grid_from_existing_gif_dimensions(self):
        import PyImgGif

        source = self.sheet(16, size=(32, 32))
        gif = source.with_name(source.stem + "_8fps.gif")
        PyImgGif.convert_sheet(source, gif, 8, PyImgGif.Grid(8, 2, "Test"))
        item = PyImgGif.gallery_preview(gif, self.stand / "preview.html")
        self.assertEqual((item["columns"], item["rows"]), (8, 2))
        self.assertEqual((item["width"], item["height"]), (16, 64))

    def test_existing_hd_gif_is_linked_from_custom_output_root(self):
        import PyImgGif

        source = self.sheet(name="hero #100%_N_4x2_o.png")
        hd_gif = source.with_name(source.stem + "_8fps.gif")
        PyImgGif.convert_sheet(source, hd_gif, 8, PyImgGif.Grid(4, 2, "Test"))
        before = {path: digest(path) for path in (source, hd_gif)}
        output = Path(self.temp.name) / "Vergleich #100%"
        self.call("--output-root", output, "--variants", "comic_mid")
        tracks = comparison_data(output)["sets"][0]["directions"]["N"]
        self.assertEqual((output / unquote(tracks["comic_high"]["gif"])).resolve(), hd_gif)
        self.assertNotIn("#", tracks["comic_high"]["gif"])
        self.assertFalse(list((output / "aufloesungsvergleich-bilder").glob("*.gif")))
        self.assertEqual(before, {path: digest(path) for path in before})

    def test_output_source_overlap_and_symlinks_fail_before_writes(self):
        source = self.sheet()
        before = digest(source)
        self.call("--no-gif", "--output-root", self.high / "ausgabe", expected=1)
        (self.stand / "comic_mid").symlink_to(self.high, target_is_directory=True)
        self.call("--no-gif", "--overwrite", expected=1)
        self.assertEqual(digest(source), before)
        self.assertFalse((self.stand / "comic_low").exists())

    def test_gif_errors_are_not_reported_as_success(self):
        source = self.sheet()
        broken_program = Path(self.temp.name) / "fehlerhaftes_gif.py"
        broken_program.write_text("raise SystemExit(7)\n")
        result = self.call("--variants", "comic_mid", "--gif-script", broken_program, expected=1)
        self.assertIn("Exit-Code 7", result.stderr)
        output = self.target(source, "comic_mid")
        self.assertTrue(output.is_file())
        output.with_name(output.stem + "_8fps.gif").write_bytes(b"defektes GIF")
        self.call("--variants", "comic_mid", expected=1)
        self.assertEqual(output.with_name(output.stem + "_8fps.gif").read_bytes(), b"defektes GIF")
        self.call("--variants", "comic_mid", "--overwrite")
        with Image.open(output.with_name(output.stem + "_8fps.gif")) as repaired:
            self.assertEqual(repaired.format, "GIF")

    def test_no_argument_start_from_action_folder_with_copied_scripts(self):
        source = self.sheet()
        bundle = Path(self.temp.name) / "werkzeuge an anderem Ort"
        bundle.mkdir()
        copied_pipeline = bundle / "Pipline"
        shutil.copytree(SCRIPTS.parent, copied_pipeline,
                        ignore=shutil.ignore_patterns("tests", "__pycache__"))
        installed_scripts = copied_pipeline / SCRIPTS.name
        self.assertEqual(digest(copied_pipeline / "PiplineToos" / "PyImgGif.py"), digest(GIF_SCRIPT))
        for variant in ("comic_low", "pixel_high"):
            folder = self.stand / variant
            folder.mkdir()
            (folder / "vorhanden.txt").write_text("behalten")
        self.call(source=False, cwd=self.stand, script=installed_scripts / "PyPiplineStart-SpritesheetResolution.py")
        for variant in VARIANTS:
            output = self.target(source, variant)
            self.assertTrue(output.is_file())
            self.assertTrue(output.with_name(output.stem + "_8fps.gif").is_file())
            self.assertTrue((output.parent / "gif-vergleich.html").is_file())
        for variant in ("comic_low", "pixel_high"):
            self.assertEqual((self.stand / variant / "vorhanden.txt").read_text(), "behalten")
        self.assertFalse((bundle / "comic_mid").exists())
        self.assertTrue((self.stand / "aufloesungsvergleich.html").is_file())

    def test_comparison_only_keeps_outputs_and_handles_missing_variants(self):
        source = self.sheet()
        self.call("--variants", "comic_mid")
        paths = list(self.stand.rglob("*.png")) + list(self.stand.rglob("*.gif"))
        hashes = {path: digest(path) for path in paths}
        self.call("--compare-only")
        self.assertEqual(hashes, {path: digest(path) for path in paths})
        tracks = comparison_data(self.stand)["sets"][0]["directions"]["N"]
        self.assertIn("gif", tracks["comic_high"])
        self.assertIn("gif", tracks["comic_mid"])
        self.assertTrue(tracks["pixel_low"]["missing"])
        self.assertEqual(list(self.high.rglob("*.gif")), [])
        self.call("--compare-only", "--no-gif", expected=2)

    def test_comparison_direction_and_filename_text_are_safe(self):
        self.sheet(name="hero_</script>_NO_4x2_o.png".replace("/", "-"))
        # '<' und '>' dürfen im eingebetteten JSON keine HTML-Tags öffnen.
        self.call("--compare-only")
        html = (self.stand / "aufloesungsvergleich.html").read_text()
        self.assertIn("\\u003c", html)
        self.assertEqual(set(comparison_data(self.stand)["sets"][0]["directions"]), {"NO"})

    def test_start_requires_comic_high_in_current_folder(self):
        source = self.sheet()
        for directory in (self.high, source.parent, Path(self.temp.name)):
            result = self.call(source=False, cwd=directory, expected=1)
            self.assertIn("fehlt comic_high", result.stderr)
        self.assertFalse((self.stand / "comic_mid").exists())

    def test_gif_cli_runs_only_after_all_pngs_exist(self):
        self.sheet(8)
        self.sheet(16)
        probe = Path(self.temp.name) / "gif_cli_probe.py"
        log = Path(self.temp.name) / "gif_calls.jsonl"
        probe.write_text(
            "import json, runpy, sys\n"
            "from pathlib import Path\n"
            "folder = Path.cwd()\n"
            f"root = Path({str(self.stand)!r})\n"
            f"variants = {VARIANTS!r}\n"
            "assert all(len(list((root / v).glob('spritesheet-fram*/*.png'))) == 2 for v in variants), 'PNG-Phase unvollständig'\n"
            f"with Path({str(log)!r}).open('a') as handle:\n"
            "    handle.write(json.dumps({'folder': str(folder), 'args': sys.argv[1:]}) + '\\n')\n"
            f"sys.path.insert(0, {str(GIF_SCRIPT.parent)!r})\n"
            f"runpy.run_path({str(GIF_SCRIPT)!r}, run_name='__main__')\n"
        )
        self.call("--gif-script", probe, source=False, cwd=self.stand)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(len(calls), 8)
        for call in calls:
            folder = Path(call["folder"])
            grid = call["args"][-1]
            self.assertIn(grid, ("4x4", "4x2"))
            self.assertEqual(call["args"], ["--fps", "8", "--grid", grid])
            self.assertFalse(folder.exists())  # Externe Programme arbeiten nur mit temporären Kopien.
        for variant in VARIANTS:
            for source in self.high.glob("spritesheet-fram*/*.png"):
                self.assertTrue((self.target(source, variant).parent / "gif-vergleich.html").is_file())

    def test_gif_cli_handles_named_mixed_grids_in_one_folder(self):
        first = self.sheet(16)
        second = self.sheet(16, grid=(8, 2))
        self.call("--variants", "comic_mid")
        for source in (first, second):
            output = self.target(source, "comic_mid")
            with Image.open(output.with_name(output.stem + "_8fps.gif")) as gif:
                self.assertEqual(gif.size, (13, 10))
                self.assertEqual(json.loads(gif.info["comment"])["source_frames"], 16)

    def test_blocked_target_folder_fails_before_any_output(self):
        self.sheet()
        (self.stand / "comic_low").write_text("vorhandene Datei")
        self.call("--no-gif", expected=1)
        self.assertFalse((self.stand / "comic_mid").exists())

    def test_help_works_without_site_packages(self):
        for script in ("PyPiplineStart-SpritesheetResolution.py", "SComicMid.py", "SComicLow.py", "SPixelHigh.py", "SPixelLow.py"):
            result = subprocess.run([sys.executable, "-S", str(SCRIPTS / script), "--help"],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
