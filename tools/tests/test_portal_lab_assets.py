"""Check the restricted blueprint palette and portable development assets."""

from pathlib import Path
import re
import struct
import unittest
from xml.etree import ElementTree


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = REPOSITORY_ROOT / "game/test_assets/environment/locations/portal_lab"
TEST_ASSET_ROOT = ASSET_ROOT / "test"
ASSET_NAMES = {"door", "crate", "lamp", "monster", "particle", "floor_tile"}
TEMPLE_ROOT = REPOSITORY_ROOT / "game/test_assets/environment/tilesets/temple"
TEMPLE_VARIANTS = ("comic_high", "comic_mid", "comic_low", "pixel_high", "pixel_low")
FLOOR_MOTIFS = {
    "cyan_ornate", "cyan_panels", "framed_stone", "octagonal_stone", "ornate",
    "plain", "riveted_metal", "staggered_stone", "stone_grid",
}
PALETTE = {
    "#101c28", "#1b2e40", "#263d50", "#304b61",
    "#45667c", "#7295aa", "#acc4d2", "#d8e6ee",
}


class PortalLabAssetTests(unittest.TestCase):
    def test_all_five_temple_variants_have_the_complete_surface_set(self) -> None:
        surfaces = {
            "floors": {f"blueprinttempel_floor_blueprint_{motif}.png" for motif in FLOOR_MOTIFS},
            "walls": {"blueprinttempel_wall_blueprint_cyan_blocks.png"},
            "roofs": {"blueprinttempel_roof_texture_stone_shingles.png"},
        }
        for surface, names in surfaces.items():
            for variant in TEMPLE_VARIANTS:
                with self.subTest(surface=surface, variant=variant):
                    directory = TEMPLE_ROOT / surface / "blueprint" / variant
                    self.assertEqual({path.name for path in directory.glob("*.png")}, names)

    def test_temple_imports_keep_native_resolution_and_lossless_pixels(self) -> None:
        dimensions = dict(zip(TEMPLE_VARIANTS, (1254, 627, 314, 128, 115)))
        files = list(TEMPLE_ROOT.rglob("*.png"))
        self.assertEqual(len(files), 55)
        for path in files:
            with self.subTest(asset=path.relative_to(TEMPLE_ROOT)):
                with path.open("rb") as source:
                    header = source.read(24)
                self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
                size = dimensions[path.parent.name]
                self.assertEqual(struct.unpack(">II", header[16:24]), (size, size))
                settings = path.with_suffix(".png.import").read_text()
                for option in ("compress/mode=0", "mipmaps/generate=false", "process/size_limit=0"):
                    self.assertIn(option, settings)
                resource = path.relative_to(REPOSITORY_ROOT / "game").as_posix()
                self.assertIn(f'source_file="res://{resource}"', settings)

    def test_both_variants_contain_the_complete_blueprint_set(self) -> None:
        for variant, extension in (("test", "svg"), ("pixelart", "png")):
            with self.subTest(variant=variant):
                files = list((ASSET_ROOT / variant).glob(f"*.{extension}"))
                self.assertEqual({path.stem for path in files}, ASSET_NAMES)

    def test_blueprint_placeholders_use_only_the_eight_blue_gray_colors(self) -> None:
        files = sorted(TEST_ASSET_ROOT.glob("*.svg"))
        self.assertEqual({path.stem for path in files}, ASSET_NAMES)
        used = set()
        for path in files:
            with self.subTest(asset=path.name):
                colors = set(re.findall(r"#[0-9a-fA-F]{6}", path.read_text()))
                self.assertTrue(colors)
                self.assertLessEqual(colors, PALETTE)
                used.update(colors)
        self.assertEqual(used, PALETTE)

    def test_placeholders_have_hd_resolution_and_static_vector_geometry(self) -> None:
        for path in TEST_ASSET_ROOT.glob("*.svg"):
            with self.subTest(asset=path.name):
                root = ElementTree.fromstring(path.read_text())
                self.assertNotEqual(root.attrib.get("shape-rendering"), "crispEdges")
                size = (int(root.attrib["width"]), int(root.attrib["height"]))
                self.assertGreaterEqual(max(size), 1024)
                self.assertGreaterEqual(min(size), 576)
                tags = {node.tag.rsplit("}", 1)[-1] for node in root.iter()}
                self.assertLessEqual(tags, {"svg", "path", "rect", "circle", "ellipse", "g"})

    def test_blueprint_textures_have_lossless_native_size_imports(self) -> None:
        files = list(TEST_ASSET_ROOT.glob("*.svg"))
        files.extend((ASSET_ROOT / "pixelart").glob("*.png"))
        for path in files:
            with self.subTest(asset=path.name):
                settings = path.with_suffix(path.suffix + ".import").read_text()
                self.assertIn("compress/mode=0", settings)
                self.assertIn("mipmaps/generate=false", settings)
                self.assertIn("process/size_limit=0", settings)
                if path.suffix == ".svg":
                    self.assertIn("svg/scale=1.0", settings)
                resource_path = path.relative_to(REPOSITORY_ROOT / "game").as_posix()
                self.assertIn(f'source_file="res://{resource_path}"', settings)

    def test_pixelart_sources_have_valid_png_dimensions(self) -> None:
        for path in (ASSET_ROOT / "pixelart").glob("*.png"):
            with self.subTest(asset=path.name), path.open("rb") as source:
                header = source.read(24)
                self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(header[12:16], b"IHDR")
                width, height = struct.unpack(">II", header[16:24])
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)

    def test_runtime_does_not_reference_the_old_flat_asset_paths(self) -> None:
        pattern = re.compile(
            r"res://test_assets/environment/locations/portal_lab/(?:"
            + "|".join(sorted(ASSET_NAMES)) + r")\.(?:png|svg)"
        )
        scene_root = REPOSITORY_ROOT / "game/test_scenes/visual_lab"
        for path in scene_root.rglob("*"):
            if path.suffix in {".gd", ".tscn"}:
                with self.subTest(source=path.relative_to(scene_root)):
                    self.assertIsNone(pattern.search(path.read_text()))


if __name__ == "__main__":
    unittest.main()
