"""Exakte Festfarben, Materialmasken und der öffentliche Color-CLI-Vertrag."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageCms, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Pipline/PiplineToos"))
import PyImgColorMatch as color
import PyImgFixedColors as fixed

STARTER = ROOT / "Pipline/3-SpritesheetColor-Pipline/PyPiplineStart-SpritesheetColor.py"
GRID = (16, 1)
MATERIALS = [
    {"id": 1, "name": "Haare", "colors": [[15, 30, 50], [100, 150, 210]]},
    {"id": 2, "name": "Leder", "colors": [[50, 20, 5], [220, 110, 30]]},
]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def snapshot(root):
    return {str(path.relative_to(root)): (color.sha256(path), path.stat().st_mtime_ns)
            for path in root.rglob("*") if path.is_file()}


def pixels(image):
    return [image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)]


def references():
    return [{"path": f"/reference/hero_stand_spritesheet_{direction}.png",
             "direction": direction, "sha256": f"{i + 1:064x}",
             "size": [64, 4], "grid": list(GRID), "frames": 16}
            for i, direction in enumerate(color.DIRECTIONS)]


def palette_profile():
    return {"format": fixed.FIXED_FORMAT, "version": 1, "color_space": "sRGB",
            "colors": [[17, 29, 53], [103, 149, 197], [231, 193, 67]],
            "references": references()}


def material_profile():
    return {"format": fixed.MATERIAL_FORMAT, "version": 1, "color_space": "sRGB",
            "materials": deepcopy(MATERIALS), "references": references()}


def make_sheet(path, shifted=False, offset=0):
    """16 bewegte Frames; gleiche Quellfarbe auf getrennten Materialflächen."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with Image.new("RGBA", (64, 4), (123, 45, 67, 0)) as image:
        for frame in range(16):
            # Die Bewegung unterscheidet die Frames auch im GIF.
            y = 1 + frame % 2
            rgb = (82, 87, 79) if shifted else (75 + offset, 110, 45)
            image.putpixel((frame * 4 + 1, y), (*rgb, 255))
            image.putpixel((frame * 4 + 2, y), (*rgb, 127))
            image.putpixel((frame * 4 + 1, 3 - y), (30 + offset, 45, 70, 1))
            image.putpixel((frame * 4 + 2, 3 - y), (190, 110 + offset, 40, 255))
        image.save(path)


def make_mask(path, source, grid=GRID, mode="L"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with color.load_png(source) as image, Image.new(mode, image.size, 0) as mask:
        if mode == "P":
            # Indizes sind Labels: die sichtbaren RGB-Palettenfarben absichtlich vertauschen.
            palette = [0] * 768
            palette[3:6] = [255, 255, 255]
            palette[6:9] = [10, 10, 10]
            mask.putpalette(palette)
        for y in range(image.height):
            for x in range(image.width):
                if image.getpixel((x, y))[3]:
                    mask.putpixel((x, y), 1 if x % 4 == 1 else 2)
        mask.save(path, pnginfo=fixed.mask_metadata(grid, color.sha256(source)), bits=8)


class ExactColorTests(unittest.TestCase):
    def test_fixed_palette_is_exact_and_preserves_alpha_hidden_rgb_and_positions(self):
        profile = palette_profile()
        rgba = [(90, 86, 79, a) for a in (255, 127, 64, 1, 0, 255, 0, 200)]
        with Image.new("RGBA", (4, 2)) as before:
            before.putdata(rgba)
            with fixed.FixedMatcher(profile).apply(before) as after:
                self.assertEqual(after.size, before.size)
                for expected, actual in zip(rgba, pixels(after)):
                    self.assertEqual(expected[3], actual[3])
                    if expected[3]:
                        self.assertIn(list(actual[:3]), profile["colors"])
                    else:
                        self.assertEqual(expected, actual)
                self.assertTrue(fixed.verify_palette(after, profile)["palette_exact"])

    def test_same_rgb_with_two_material_labels_uses_two_distinct_palettes(self):
        profile = material_profile()
        with Image.new("RGBA", (4, 1), (90, 90, 90, 255)) as before, Image.new("L", (4, 1)) as mask:
            mask.putdata([1, 2, 1, 2])
            with fixed.MaterialMatcher(profile).apply(before, mask) as after:
                actual = pixels(after)
                self.assertEqual(actual[0], actual[2])
                self.assertEqual(actual[1], actual[3])
                self.assertNotEqual(actual[0], actual[1])
                self.assertIn(list(actual[0][:3]), profile["materials"][0]["colors"])
                self.assertIn(list(actual[1][:3]), profile["materials"][1]["colors"])
                check = fixed.verify_palette(after, profile, mask)
                self.assertTrue(check["material_palette_exact"])
                self.assertFalse(check["material_labels_visually_verified"])

    def test_material_mapping_preserves_partial_alpha_and_invisible_source_rgb(self):
        rgba = [(90, 90, 90, 0), (90, 90, 90, 1), (90, 90, 90, 127), (90, 90, 90, 255)]
        with Image.new("RGBA", (2, 2)) as before, Image.new("L", (2, 2)) as mask:
            before.putdata(rgba)
            mask.putdata([0, 1, 2, 1])
            with fixed.MaterialMatcher(material_profile()).apply(before, mask) as after:
                self.assertEqual(after.size, (2, 2))
                self.assertEqual([p[3] for p in pixels(after)], [p[3] for p in rgba])
                self.assertEqual(after.getpixel((0, 0)), rgba[0])

    def test_mapping_is_independent_of_frames_composition_and_application_order(self):
        matcher = fixed.FixedMatcher(palette_profile())
        wanted = (77, 123, 65, 255)
        with Image.new("RGBA", (1, 1), wanted) as isolated, Image.new("RGBA", (32, 2), (250, 0, 190, 255)) as mixed:
            mixed.putpixel((1, 0), wanted)
            mixed.putpixel((30, 1), wanted)
            with matcher.apply(isolated) as a, matcher.apply(mixed) as b, matcher.apply(isolated) as repeated:
                self.assertEqual(a.tobytes(), repeated.tobytes())
                self.assertEqual(a.getpixel((0, 0)), b.getpixel((1, 0)))
                self.assertEqual(a.getpixel((0, 0)), b.getpixel((30, 1)))
            with fixed.FixedMatcher(palette_profile()).apply(mixed) as fresh, matcher.apply(mixed) as cached:
                self.assertEqual(fresh.tobytes(), cached.tobytes())

    def test_distance_ties_use_profile_order_in_both_modes(self):
        # Eine exakt symmetrische Distanz isoliert die Gleichstandsregel von Lab-Rundung.
        with patch.object(color, "rgb_to_lab", side_effect=lambda rgb: tuple(round(c * 255) for c in rgb)):
            colors = [[0, 10, 10], [20, 10, 10]]
            self.assertEqual(fixed.PaletteMapper(colors).nearest(bytes([10, 10, 10])), bytes(colors[0]))
            self.assertEqual(fixed.PaletteMapper(colors[::-1]).nearest(bytes([10, 10, 10])), bytes(colors[1]))
            materials = [[40, 100, 0], [40, 0, 100]]
            self.assertEqual(fixed.PaletteMapper(materials, lightness=True).nearest(bytes([40, 50, 50])), bytes(materials[0]))
            self.assertEqual(fixed.PaletteMapper(materials[::-1], lightness=True).nearest(bytes([40, 50, 50])), bytes(materials[1]))

    def test_png_stored_bytes_are_exact_even_with_icc_and_partial_alpha(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, output = Path(temporary) / "source.png", Path(temporary) / "exact.png"
            icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
            with Image.new("RGBA", (3, 1)) as image:
                image.putdata([(82, 91, 80, 255), (82, 91, 80, 127), (213, 34, 89, 0)])
                image.save(source, icc_profile=icc)
            with color.load_png(source) as before, fixed.FixedMatcher(palette_profile()).apply(before) as after:
                color.save_png(after, output)
                with Image.open(output) as stored:
                    self.assertEqual(stored.mode, "RGBA")
                    self.assertEqual(stored.tobytes(), after.tobytes())
                    self.assertNotIn("icc_profile", stored.info)
                    self.assertEqual(stored.getpixel((2, 0)), (213, 34, 89, 0))
                    self.assertEqual(stored.getpixel((1, 0))[3], 127)
                    self.assertIn(list(stored.getpixel((1, 0))[:3]), palette_profile()["colors"])

    def test_independent_palette_verification_rejects_wrong_global_or_material_color(self):
        profile = palette_profile()
        with Image.new("RGBA", (1, 1), (255, 0, 255, 255)) as image:
            self.assertRaises(ValueError, fixed.verify_palette, image, profile)
        with Image.new("RGBA", (1, 1), (*MATERIALS[0]["colors"][0], 255)) as image, Image.new("L", (1, 1), 2) as mask:
            self.assertRaises(ValueError, fixed.verify_palette, image, material_profile(), mask)

    def test_exact_mapping_requires_normalized_rgba(self):
        with Image.new("RGB", (1, 1)) as image:
            self.assertRaises(ValueError, fixed.FixedMatcher(palette_profile()).apply, image)


class ProfileValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "profile.json"

    def invalid(self, profile, loader=fixed.load_palette):
        write_json(self.path, profile)
        with self.assertRaises(ValueError):
            loader(self.path)

    def test_valid_formats_roundtrip_and_remain_distinct(self):
        for profile, loader, wrong in (
                (palette_profile(), fixed.load_palette, fixed.load_material_profile),
                (material_profile(), fixed.load_material_profile, fixed.load_palette)):
            with self.subTest(format=profile["format"]):
                write_json(self.path, profile)
                self.assertEqual(loader(self.path), profile)
                self.assertRaises(ValueError, wrong, self.path)

    def test_rejects_old_unknown_versions_non_objects_and_wrong_color_spaces(self):
        for value in ([], None, {"schema_version": 3}):
            with self.subTest(profile=value):
                self.invalid(value)
        for key, value in (("version", True), ("version", 2), ("version", 1.0),
                           ("format", color.FORMAT), ("color_space", "Display P3")):
            with self.subTest(key=key, value=value):
                profile = palette_profile()
                profile[key] = value
                self.invalid(profile)

    def test_rgb_validation_rejects_bool_float_out_of_range_duplicate_and_empty(self):
        for colors in ([], None, [[True, 1, 2]], [[1.0, 1, 2]], [[-1, 1, 2]],
                       [[256, 1, 2]], [[1, 2]], [[1, 2, 3, 4]], [[1, 2, 3]] * 2,
                       [[0, 0, i % 256] for i in range(257)]):
            with self.subTest(colors=colors):
                profile = palette_profile()
                profile["colors"] = colors
                self.invalid(profile)

    def test_all_eight_references_require_valid_hashes_geometry_and_frame_counts(self):
        for key, value in (("sha256", "z" * 64), ("path", ""), ("grid", [True, 1]),
                           ("grid", [65, 1]), ("grid", [0, 1]), ("size", [63, 4]),
                           ("size", [64, False]), ("frames", True), ("frames", 8)):
            with self.subTest(key=key, value=value):
                profile = palette_profile()
                profile["references"][0][key] = value
                self.invalid(profile)
        for refs in (references()[:-1], references()[::-1], [None] * 8):
            profile = palette_profile()
            profile["references"] = refs
            self.invalid(profile)
        profile = palette_profile()
        profile["references"][0].update(grid=[8, 1], frames=8)
        self.invalid(profile)

    def test_material_ids_names_and_color_rows_are_strict(self):
        for key, value in (("id", 0), ("id", True), ("id", 256), ("id", 2),
                           ("name", "  "), ("name", "LEDER"), ("colors", [[1, False, 3]])):
            with self.subTest(key=key, value=value):
                profile = material_profile()
                profile["materials"][0][key] = value
                self.invalid(profile, fixed.load_material_profile)

    def test_definition_format_and_levels_are_strict(self):
        definitions = {"format": fixed.DEFINITIONS_FORMAT, "version": 1,
                       "materials": [{"id": 1, "name": "Haare", "levels": 4}]}
        write_json(self.path, definitions)
        self.assertEqual(fixed.load_definitions(self.path), definitions)
        for value in (True, 0, 257, 2.0, None):
            with self.subTest(levels=value):
                invalid = deepcopy(definitions)
                invalid["materials"][0]["levels"] = value
                self.invalid(invalid, fixed.load_definitions)


class MaskValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.source = self.base / "source.png"
        self.path = self.base / "mask.png"
        make_sheet(self.source)
        self.image = color.load_png(self.source)
        self.addCleanup(self.image.close)
        self.source_hash = color.sha256(self.source)

    def load(self):
        return fixed.load_mask(self.path, self.image, GRID, MATERIALS, self.source_hash)

    def rewrite(self, transform=None, metadata=None, mode="L", size=None):
        make_mask(self.path, self.source)
        with Image.open(self.path) as original:
            mask = original.copy()
        with mask:
            if transform:
                transform(mask)
            if size:
                mask = mask.resize(size)
            if mode != "L":
                mask = mask.convert(mode)
            mask.save(self.path, pnginfo=metadata if metadata is not None else fixed.mask_metadata(GRID, self.source_hash))

    def test_palette_png_uses_raw_label_indices_not_palette_luminance(self):
        make_mask(self.path, self.source, mode="P")
        with self.load() as mask:
            self.assertEqual(mask.mode, "L")
            self.assertEqual(mask.getpixel((1, 1)), 1)
            self.assertEqual(mask.getpixel((2, 1)), 2)
            self.assertEqual(mask.getpixel((0, 0)), 0)

    def test_metadata_binds_mask_to_source_and_its_frame_grid(self):
        for info in (PngImagePlugin.PngInfo(), fixed.mask_metadata((8, 2), self.source_hash),
                     fixed.mask_metadata(GRID, "f" * 64)):
            with self.subTest(metadata=info):
                self.rewrite(metadata=info)
                self.assertRaises(ValueError, self.load)

    def test_mask_rejects_unknown_ids_visible_background_and_hidden_material(self):
        cases = [((1, 1), 0, "fehlende Zuordnung"), ((1, 1), 99, "unbekannte"),
                 ((0, 0), 1, "unsichtbarem Hintergrund")]
        for point, label, message in cases:
            with self.subTest(point=point, label=label):
                self.rewrite(lambda mask: mask.putpixel(point, label))
                with self.assertRaisesRegex(ValueError, message):
                    self.load()

    def test_error_identifies_pixel_and_frame_for_missing_material(self):
        self.rewrite(lambda mask: mask.putpixel((29, 2), 0))
        with self.assertRaisesRegex(ValueError, r"1 Pixel.*\(29, 2\), Frame 8"):
            self.load()

    def test_mask_rejects_wrong_size_mode_bitdepth_transparency_and_symlink(self):
        for kwargs in ({"size": (32, 4)}, {"mode": "RGB"}, {"mode": "I;16"}):
            with self.subTest(kwargs=kwargs):
                self.rewrite(**kwargs)
                self.assertRaises(ValueError, self.load)
        make_mask(self.path, self.source)
        with Image.open(self.path) as original:
            original.save(self.path, transparency=0, pnginfo=fixed.mask_metadata(GRID, self.source_hash))
        self.assertRaises(ValueError, self.load)
        linked = self.base / "linked.png"
        self.path.rename(linked)
        self.path.symlink_to(linked)
        self.assertRaises(ValueError, self.load)

    def test_missing_mask_and_source_change_fail(self):
        self.assertRaises(ValueError, self.load)
        make_mask(self.path, self.source)
        with self.load() as mask:
            self.assertEqual(mask.size, self.image.size)
        self.source_hash = "a" * 64
        self.assertRaises(ValueError, self.load)

    def test_preview_keeps_alpha_and_uses_distinct_material_legend_colors(self):
        make_mask(self.path, self.source)
        with self.load() as mask, fixed.mask_preview(mask, self.image, MATERIALS) as preview:
            self.assertEqual(preview.size, self.image.size)
            self.assertEqual(preview.getchannel("A").tobytes(), self.image.getchannel("A").tobytes())
            self.assertEqual(list(preview.getpixel((1, 1))[:3]), fixed.preview_color(1))
            self.assertEqual(list(preview.getpixel((2, 1))[:3]), fixed.preview_color(2))


class ProfileDerivationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.source, self.masks = self.base / "source", self.base / "masks"
        self.refs = []
        for i, direction in enumerate(color.DIRECTIONS):
            path = self.source / f"hero_stand_spritesheet_{direction}.png"
            make_sheet(path, offset=i)
            make_mask(self.masks / path.name, path)
            self.refs.append((path, direction, GRID))
        self.definitions = {"format": fixed.DEFINITIONS_FORMAT, "version": 1,
                            "materials": [{"id": 1, "name": "Haare", "levels": 3},
                                          {"id": 2, "name": "Leder", "levels": 3}]}

    def test_fixed_palette_derives_from_real_reference_profile_and_records_provenance(self):
        reference = color.make_profile(self.refs)
        profile = fixed.make_palette(reference)
        self.assertEqual(profile["colors"], reference["pixel_palette"])
        self.assertEqual(profile["derivation"]["reference_profile_sha256"], color.fingerprint(reference))
        self.assertEqual(sum(r["frames"] for r in profile["references"]), 128)
        path = self.base / "fixed.json"
        write_json(path, profile)
        self.assertEqual(fixed.load_palette(path), profile)
        self.assertEqual(fixed.make_palette(reference), profile)

    def test_material_palette_uses_marked_reference_pixels_and_records_mask_hashes(self):
        profile = fixed.make_material_profile(self.refs, self.definitions, self.masks, self.source)
        self.assertEqual([m["id"] for m in profile["materials"]], [1, 2])
        self.assertTrue(all(1 <= len(m["colors"]) <= 3 for m in profile["materials"]))
        self.assertNotEqual(profile["materials"][0]["colors"], profile["materials"][1]["colors"])
        self.assertEqual(len(profile["derivation"]["reference_masks"]), 8)
        for record in profile["derivation"]["reference_masks"]:
            self.assertEqual(record["sha256"], color.sha256(self.masks / record["path"]))
        path = self.base / "materials.json"
        write_json(path, profile)
        self.assertEqual(fixed.load_material_profile(path), profile)
        self.assertEqual(fixed.make_material_profile(self.refs, self.definitions, self.masks, self.source), profile)

    def test_absent_material_or_unbound_reference_never_invents_colors(self):
        definitions = deepcopy(self.definitions)
        definitions["materials"].append({"id": 3, "name": "Metall", "levels": 3})
        self.assertRaisesRegex(ValueError, "Keine markierten", fixed.make_material_profile,
                               self.refs, definitions, self.masks, self.source)
        self.assertRaisesRegex(ValueError, "acht", fixed.make_material_profile,
                               self.refs[:-1], self.definitions, self.masks, self.source)
        mask_path = self.masks / self.refs[-1][0].name
        mask_path.unlink()
        self.assertRaisesRegex(ValueError, "fehlt", fixed.make_material_profile,
                               self.refs, self.definitions, self.masks, self.source)


class ExactColorPipelineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="fixed # test ")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.source = self.base / "sources"
        self.masks = self.source / "materials/masks"
        self.fixed_output, self.material_output = self.base / "sources-fixed", self.base / "sources-material"
        refs = []
        for i, direction in enumerate(color.DIRECTIONS):
            path = self.source / f"hero_stand_spritesheet_{direction}.png"
            make_sheet(path, offset=i)
            make_mask(self.masks / path.name, path)
            refs.append((path, direction, GRID))
        self.run_png = self.source / "hero_run_spritesheet_N.png"
        self.walk_png = self.source / "hero_walk_spritesheet_N.png"
        make_sheet(self.run_png, shifted=True)
        make_sheet(self.walk_png, shifted=True, offset=5)
        for path in (self.run_png, self.walk_png):
            make_mask(self.masks / path.name, path)
        self.reference = color.make_profile(refs)
        self.reference_path = self.base / "reference.json"
        write_json(self.reference_path, self.reference)
        self.palette = fixed.make_palette(self.reference)
        self.palette_path = self.base / "fixed.json"
        write_json(self.palette_path, self.palette)
        self.material = material_profile()
        self.material["references"] = self.reference["references"]
        self.material_path = self.base / "materials.json"
        write_json(self.material_path, self.material)
        self.definitions = {"format": fixed.DEFINITIONS_FORMAT, "version": 1,
                            "materials": [{"id": 1, "name": "Haare", "levels": 3},
                                          {"id": 2, "name": "Leder", "levels": 3}]}
        self.definitions_path = self.base / "definitions.json"
        write_json(self.definitions_path, self.definitions)

    def call(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(STARTER), str(self.source), *map(str, args)],
                                capture_output=True, text=True, timeout=90)
        if expected is None:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        else:
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def fixed_args(self):
        return ("--color-mode", "fixed", "--fixed-palette", self.palette_path)

    def material_args(self):
        return ("--color-mode", "material", "--material-profile", self.material_path,
                "--mask-dir", self.masks)

    def test_fixed_cli_dry_run_membership_references_and_complete_previews(self):
        original = snapshot(self.base)
        for flags in (("--dry-run",), ("--dry-run", "--overwrite")):
            self.call(*self.fixed_args(), *flags)
            self.assertEqual(snapshot(self.base), original)
            self.assertFalse(self.fixed_output.exists())
        self.call(*self.fixed_args())
        self.assertFalse((self.base / "sources-color").exists())
        self.assertEqual(snapshot(self.source), {k.removeprefix("sources/"): v for k, v in original.items() if k.startswith("sources/")})
        self.assertEqual(fixed.load_palette(self.fixed_output / ".color_profile/fixed-palette.json"), self.palette)
        palette = {tuple(c) for c in self.palette["colors"]}
        for source in self.source.glob("*.png"):
            target = self.fixed_output / source.name
            if "_stand_" in source.name:
                self.assertEqual(source.read_bytes(), target.read_bytes())
            else:
                with Image.open(source) as before, Image.open(target) as after:
                    self.assertEqual(after.size, before.size)
                    self.assertEqual(after.getchannel("A").tobytes(), before.getchannel("A").tobytes())
                    self.assertTrue({rgba[:3] for _, rgba in after.getcolors(256) if rgba[3]} <= palette)
                    self.assertEqual(after.getpixel((0, 0)), before.getpixel((0, 0)))
            with Image.open(target.with_name(target.stem + "_8fps.gif")) as gif:
                self.assertEqual(gif.info["loop"], 0)
                self.assertEqual(json.loads(gif.info["comment"])["source_frames"], 16)
                duration = 0
                for frame in range(gif.n_frames):
                    gif.seek(frame)
                    duration += gif.info["duration"]
                self.assertEqual(duration, 2000)
        report = json.loads((self.fixed_output / "color-build.json").read_text())
        self.assertEqual(report["settings"]["color_mode"], "fixed")
        self.assertEqual(report["settings"]["profile_sha256"], color.fingerprint(self.palette))
        self.assertEqual(len(report["images"]), 10)
        self.assertEqual(sum(r["reference_copy"] for r in report["images"]), 8)
        self.assertTrue(all(r["palette_exact"] for r in report["images"] if not r["reference_copy"]))
        html = (self.fixed_output / "farbvergleich.html").read_text()
        self.assertIn("fixed", html)
        self.assertIn(self.run_png.name, html)

    def test_material_cli_uses_masks_and_records_profile_and_mask_provenance(self):
        original = snapshot(self.source)
        self.call(*self.material_args())
        self.assertEqual(snapshot(self.source), original)
        self.assertEqual(fixed.load_material_profile(self.material_output / ".color_profile/material-colors.json"), self.material)
        report = json.loads((self.material_output / "color-build.json").read_text())
        self.assertEqual(report["settings"]["color_mode"], "material")
        self.assertEqual(report["settings"]["profile_sha256"], color.fingerprint(self.material))
        for record in report["images"]:
            source = self.source / record["path"]
            target = self.material_output / record["path"]
            if record["reference_copy"]:
                self.assertEqual(source.read_bytes(), target.read_bytes())
                self.assertNotIn("material_palette_exact", record)
                continue
            self.assertEqual(record["mask_sha256"], color.sha256(self.masks / record["path"]))
            self.assertTrue(record["material_palette_exact"])
            self.assertFalse(record["material_labels_visually_verified"])
            with Image.open(target) as after, Image.open(self.masks / record["path"]) as labels:
                for y in range(after.height):
                    for x in range(after.width):
                        rgba = after.getpixel((x, y))
                        if rgba[3]:
                            self.assertIn(list(rgba[:3]), MATERIALS[labels.getpixel((x, y)) - 1]["colors"])
            preview = self.material_output / ".material_masks" / record["path"]
            with Image.open(source) as original_image, Image.open(preview) as image:
                self.assertEqual(image.getchannel("A").tobytes(), original_image.getchannel("A").tobytes())
        html = (self.material_output / "farbvergleich.html").read_text()
        self.assertIn("material", html)
        self.assertIn('id="mask"', html)
        self.assertIn("Haare", html)
        self.assertIn("Leder", html)
        self.assertIn(".material_masks/", html)

    def test_material_dry_run_never_writes_even_with_overwrite(self):
        before = snapshot(self.base)
        for flags in (("--dry-run",), ("--dry-run", "--overwrite")):
            self.call(*self.material_args(), *flags)
            self.assertEqual(snapshot(self.base), before)
            self.assertFalse(self.material_output.exists())

    def test_all_material_masks_are_checked_before_first_write(self):
        path = self.masks / self.walk_png.name  # Alphabetisch hinter dem ersten Ziel.
        saved = path.read_bytes()
        mutations = [None, (1, 1, 0), (0, 0, 1), (1, 1, 99)]
        for change in mutations:
            with self.subTest(change=change):
                path.write_bytes(saved)
                if change is None:
                    path.unlink()
                else:
                    with Image.open(path) as original:
                        labels = original.copy()
                    with labels:
                        labels.putpixel(change[:2], change[2])
                        labels.save(path, pnginfo=fixed.mask_metadata(GRID, color.sha256(self.walk_png)))
                before = snapshot(self.base)
                result = self.call(*self.material_args(), expected=None)
                self.assertIn("maske", result.stderr.lower())
                self.assertEqual(snapshot(self.base), before)
                self.assertFalse(self.material_output.exists())

    def test_normal_preserves_all_outputs_overwrite_repairs_only_selected_mode(self):
        self.call(*self.fixed_args())
        self.call(*self.material_args())
        fixed_before, sources_before = snapshot(self.fixed_output), snapshot(self.source)
        before = snapshot(self.material_output)
        self.call(*self.material_args())
        self.call(*self.material_args(), "--dry-run", "--overwrite")
        self.assertEqual(snapshot(self.material_output), before)
        target = self.material_output / self.walk_png.name
        target.write_bytes(b"broken PNG")
        foreign = self.material_output / "keep.txt"
        foreign.write_text("foreign file")
        damaged = snapshot(self.material_output)
        self.call(*self.material_args(), expected=None)
        self.assertEqual(snapshot(self.material_output), damaged)
        self.call(*self.material_args(), "--overwrite")
        self.assertEqual(foreign.read_text(), "foreign file")
        self.assertEqual(snapshot(self.fixed_output), fixed_before)
        self.assertEqual(snapshot(self.source), sources_before)
        with Image.open(target) as restored:
            self.assertEqual(restored.size, (64, 4))

    def test_changed_mask_and_profile_fail_without_replacing_existing_outputs(self):
        self.call(*self.material_args())
        before = snapshot(self.material_output)
        mask_path = self.masks / self.run_png.name
        with Image.open(mask_path) as original:
            mask = original.copy()
        with mask:
            mask.putpixel((1, 1), 2)
            mask.save(mask_path, pnginfo=fixed.mask_metadata(GRID, color.sha256(self.run_png)))
        result = self.call(*self.material_args(), expected=None)
        self.assertRegex(result.stderr.lower(), "maske|mask|material")
        self.assertEqual(snapshot(self.material_output), before)
        make_mask(mask_path, self.run_png)
        self.material["materials"][0]["colors"][0][0] += 1
        write_json(self.material_path, self.material)
        self.call(*self.material_args(), expected=None)
        self.assertEqual(snapshot(self.material_output), before)

    def test_normal_missing_output_is_added_and_other_files_are_preserved(self):
        self.call(*self.fixed_args())
        target = self.fixed_output / self.run_png.name
        gif_path = target.with_name(target.stem + "_8fps.gif")
        for missing in (gif_path, target):
            with self.subTest(missing=missing.name):
                missing.unlink()
                before = snapshot(self.fixed_output)
                self.call(*self.fixed_args())
                after = snapshot(self.fixed_output)
                self.assertTrue(missing.is_file())
                self.assertEqual({k: after[k] for k in before}, before)

    def test_byte_identical_non_reference_animation_is_still_mapped(self):
        self.run_png.write_bytes((self.source / "hero_stand_spritesheet_N.png").read_bytes())
        # Eine kleine Zielliste erzwingt eine sichtbare, technisch überprüfbare Änderung.
        self.palette["colors"] = [[11, 22, 33]]
        write_json(self.palette_path, self.palette)
        self.call(*self.fixed_args())
        report = json.loads((self.fixed_output / "color-build.json").read_text())
        run = next(record for record in report["images"] if record["path"] == self.run_png.name)
        self.assertFalse(run["reference_copy"])
        self.assertTrue(run["palette_exact"])
        with Image.open(self.fixed_output / self.run_png.name) as image:
            self.assertEqual({rgba[:3] for _, rgba in image.getcolors(256) if rgba[3]}, {(11, 22, 33)})

    def test_incompatible_mode_arguments_fail_without_any_writes(self):
        before = snapshot(self.base)
        cases = [
            ("--color-mode", "fixed"),
            ("--color-mode", "material", "--material-profile", self.material_path),
            ("--color-mode", "material", "--mask-dir", self.masks),
            ("--fixed-palette", self.palette_path),
            ("--material-profile", self.material_path, "--mask-dir", self.masks),
            (*self.fixed_args(), "--strength", "0.75"),
            (*self.fixed_args(), "--max-distance", "18"),
            (*self.fixed_args(), "--material-profile", self.material_path),
            (*self.fixed_args(), "--mask-dir", self.masks),
            (*self.fixed_args(), "--profile", self.reference_path),
            (*self.fixed_args(), "--reference", self.source),
            (*self.material_args(), "--strength", "0"),
            (*self.material_args(), "--max-distance", "1"),
            (*self.material_args(), "--fixed-palette", self.palette_path),
            (*self.material_args(), "--profile", self.reference_path),
            (*self.material_args(), "--reference", self.source),
        ]
        for args in cases:
            with self.subTest(args=args):
                self.call(*args, expected=None)
                self.assertEqual(snapshot(self.base), before)

    def test_invalid_fixed_profile_fails_before_output_creation(self):
        self.palette["colors"] = [[256, 0, 0]]
        write_json(self.palette_path, self.palette)
        before = snapshot(self.base)
        self.call(*self.fixed_args(), expected=None)
        self.assertEqual(snapshot(self.base), before)
        self.assertFalse(self.fixed_output.exists())

    def test_prepare_masks_creates_bound_empty_templates_in_source_subfolder(self):
        destination = self.source / "materials/handmarked"
        before = snapshot(self.base)
        for flags in (("--dry-run",), ("--dry-run", "--overwrite")):
            self.call("--prepare-masks", destination, *flags)
            self.assertEqual(snapshot(self.base), before)
            self.assertFalse(destination.exists())
        self.call("--prepare-masks", destination)
        for source in self.source.glob("*.png"):
            path = destination / source.name
            with Image.open(path) as image:
                self.assertEqual(image.mode, "L")
                self.assertEqual(image.size, (64, 4))
                self.assertEqual(image.getextrema(), (0, 0))
                self.assertEqual(image.info[fixed.MASK_GRID], "16x1")
                self.assertEqual(image.info[fixed.MASK_SOURCE], color.sha256(source))
                self.assertEqual(image.info[fixed.MASK_VERSION], "1")
        path = destination / self.run_png.name
        make_mask(path, self.run_png)
        prepared = snapshot(destination)
        self.call("--prepare-masks", destination)
        self.assertEqual(snapshot(destination), prepared)
        self.assertFalse(self.fixed_output.exists())
        self.assertFalse(self.material_output.exists())

    def test_prepare_masks_never_overwrites_original_pngs(self):
        before = snapshot(self.base)
        self.call("--prepare-masks", self.source, "--overwrite", expected=None)
        self.assertEqual(snapshot(self.base), before)

    def test_palette_and_material_exports_are_valid_deterministic_and_dry_run_safe(self):
        fixed_path = self.source / "materials/palettes/stand-fixed.json"
        material_path = self.source / "materials/palettes/stand-materials.json"
        fixed_args = ("--export-fixed-palette", fixed_path, "--profile", self.reference_path)
        material_args = ("--export-material-profile", material_path,
                         "--material-definitions", self.definitions_path, "--mask-dir", self.masks)
        before = snapshot(self.base)
        for args in (fixed_args, material_args):
            for flags in (("--dry-run",), ("--dry-run", "--overwrite")):
                self.call(*args, *flags)
                self.assertEqual(snapshot(self.base), before)
        self.call(*fixed_args)
        self.assertEqual(fixed.load_palette(fixed_path), self.palette)
        self.call(*material_args)
        profile = fixed.load_material_profile(material_path)
        self.assertEqual(len(profile["references"]), 8)
        self.assertEqual(len(profile["derivation"]["reference_masks"]), 8)
        self.assertTrue(profile["derivation"]["visual_review_required"])
        exported = snapshot(self.source / "materials/palettes")
        self.call(*fixed_args)
        self.call(*material_args)
        self.assertEqual(snapshot(self.source / "materials/palettes"), exported)

    def test_invalid_preparation_combinations_or_source_exports_write_nothing(self):
        destination = self.base / "palette.json"
        cases = [
            ("--export-fixed-palette", destination, "--color-mode", "soft"),
            ("--export-fixed-palette", destination, "--output-dir", self.fixed_output),
            ("--export-fixed-palette", destination, "--strength", "0.75"),
            ("--export-fixed-palette", destination, "--max-distance", "18"),
            ("--export-fixed-palette", destination, "--material-definitions", self.definitions_path),
            ("--export-fixed-palette", self.run_png, "--overwrite"),
            ("--export-material-profile", self.run_png, "--material-definitions", self.definitions_path,
             "--mask-dir", self.masks, "--overwrite"),
            ("--export-material-profile", destination, "--mask-dir", self.masks),
            ("--prepare-masks", self.base / "templates", "--fixed-palette", self.palette_path),
            ("--prepare-masks", self.base / "templates", "--export-fixed-palette", destination),
        ]
        before = snapshot(self.base)
        for args in cases:
            with self.subTest(args=args):
                self.call(*args, expected=None)
                self.assertEqual(snapshot(self.base), before)


if __name__ == "__main__":
    unittest.main()
