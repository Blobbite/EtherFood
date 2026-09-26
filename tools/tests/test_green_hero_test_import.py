"""Exercise the Green Hero test import with small, independent PNG fixtures."""

from __future__ import annotations

import hashlib
from importlib import util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock
import zlib


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = REPOSITORY_ROOT / "game" / "tools"
MANIFEST_PATH = (
    REPOSITORY_ROOT / "game/test_assets/characters/heroes/greenhero/test/stand_walk_manifest.json"
)
INPUT_DIRECTIONS = ("N", "NO", "O", "SO", "S", "SW", "W", "NW")


def _png(width: int, height: int, color: int = 80) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload))
        )

    scanline = b"\0" + bytes((color, 100, 120, 255)) * width
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanline * height))
        + chunk(b"IEND", b"")
    )


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*") if path.is_file()
    }


@unittest.skipUnless(
    MANIFEST_PATH.is_file(),
    "legacy manifest importer is not part of the five-variant animation matrix",
)
class GreenHeroTestImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(TOOLS_ROOT))
        try:
            spec = util.spec_from_file_location(
                "green_hero_test_import", TOOLS_ROOT / "prepare_green_hero_test.py",
            )
            cls.importer = util.module_from_spec(spec)
            spec.loader.exec_module(cls.importer)
        finally:
            sys.path.remove(str(TOOLS_ROOT))
        cls.generator = cls.importer.generator

    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package_root = self.root / "test"
        self.source_root = self.root / "incoming"
        self.source_root.mkdir()
        manifest = json.loads(MANIFEST_PATH.read_text())
        manifest["actions"] = ["stand", "walk"]
        manifest["animations"] = [
            raw for raw in manifest["animations"] if raw["action"] in manifest["actions"]
        ]
        manifest["source_canvas"] = [3, 4]
        manifest["defaults"].update(
            columns=4, rows=4, frame_count=16, frame_order=list(range(16)),
            frame_durations_ms=[120] * 16, loop=True, height_pixels=4, foot_anchor=[1, 4],
        )
        manifest["reference_pose"].update(
            alpha_bounds=[0, 0, 3, 4], height_pixels=4, foot_anchor=[1, 4],
        )
        payload = _png(12, 16)
        digest = hashlib.sha256(payload).hexdigest()
        for animation in manifest["animations"]:
            animation.update(crop_rect=[0, 0, 3, 4])
            animation["runtime_file"] = (
                f"{animation['action']}/greenhero_{animation['direction']}_"
                f"{animation['action']}_spritesheet_4x4_o.png"
            )
            for optional in ("source_canvas", *self.importer.LAYOUT_FIELDS):
                animation.pop(optional, None)
            animation["source"] = {
                "optimized": [animation["runtime_file"], digest],
                "input_sheet": [animation["runtime_file"], digest],
            }
            path = self.package_root / animation["runtime_file"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        self.manifest_path = self.package_root / "stand_walk_manifest.json"
        self.manifest_path.write_text(json.dumps(manifest))
        package = self.generator.load_package(self.manifest_path)
        (self.package_root / package.resource_file).write_text(
            self.generator.generate_resource(package),
        )
        for index, direction in enumerate(INPUT_DIRECTIONS):
            (self.source_root / f"{direction}_solo_4x4_o.png").write_bytes(
                _png(20, 24, index),
            )

    def _prepare(self, **options) -> tuple[str, ...]:
        return self.importer.prepare_test_package(
            self.package_root, source_root=self.source_root, **options,
        )

    def _pose_inputs(self, root: Path, actions: tuple[str, ...] | None = None) -> None:
        root.mkdir(parents=True, exist_ok=True)
        for action_index, action in enumerate(actions or self.generator.TEST_ACTIONS):
            for index, direction in enumerate(INPUT_DIRECTIONS):
                stem = f"greenhero_hd_{action}_{direction}"
                (root / f"{stem}.png").write_bytes(_png(3, 4, action_index * 8 + index))
                (root / f"{stem}_solo_4x4.png").write_bytes(_png(12, 16, 240))

    def test_all_named_poses_replace_sheets_without_creating_raw_copies(self) -> None:
        self._pose_inputs(self.source_root)
        inputs = _snapshot(self.source_root)
        old_images = {
            path.relative_to(self.package_root): path.read_bytes()
            for folder in ("stand", "walk")
            for path in (self.package_root / folder).glob("*.png")
        }
        self._prepare()
        self.assertEqual(_snapshot(self.source_root), inputs)
        package = self.generator.load_package(self.manifest_path)
        self.generator.validate_runtime_assets(package, self.package_root)
        self.assertEqual(package.actions, self.generator.TEST_ACTIONS)
        self.assertEqual(len(package.animations), 48)
        for animation in package.animations:
            source = self.source_root / f"greenhero_hd_{animation.name}.png"
            self.assertEqual((self.package_root / animation.runtime_file).read_bytes(),
                             source.read_bytes())
            self.assertEqual((animation.columns, animation.rows, animation.frame_count), (1, 1, 1))
            self.assertFalse(animation.loop)
            self.assertEqual(animation.height_pixels, 4)
            self.assertEqual(animation.foot_anchor, (1, 4))
        for relative in old_images:
            self.assertFalse((self.package_root / relative).exists())
        self.assertFalse((self.package_root / "sources").exists())
        for animation in package.animations:
            self.assertEqual(animation.input_sheet.relative_path, animation.runtime_file)
        before = _snapshot(self.package_root)
        self._prepare()
        self.assertEqual(_snapshot(self.package_root), before)

    def test_import_requires_an_explicit_external_candidate(self) -> None:
        before = _snapshot(self.package_root)
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "--source-dir"):
            self.importer.prepare_test_package(self.package_root)
        self.assertEqual(_snapshot(self.package_root), before)

    def test_import_rejects_sources_inside_the_godot_project(self) -> None:
        before = _snapshot(self.package_root)
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "outside the Godot"):
            self.importer.prepare_test_package(
                self.package_root, source_root=TOOLS_ROOT.parent / "test_assets",
            )
        self.assertEqual(_snapshot(self.package_root), before)

    def test_named_grids_without_single_images_remain_nonanimated_poses(self) -> None:
        self._pose_inputs(self.source_root, ("jump",))
        for path in self.source_root.glob("greenhero_hd_jump_*.png"):
            if "_solo_" not in path.name:
                path.unlink()
        self._prepare(action="jump")
        package = self.generator.load_package(self.manifest_path)
        self.generator.validate_runtime_assets(package, self.package_root)
        jump = [item for item in package.animations if item.action == "jump"]
        self.assertEqual(len(jump), 8)
        for item in jump:
            self.assertEqual((item.columns, item.rows), (4, 4))
            self.assertEqual(item.frame_order, (0,))
            self.assertFalse(item.loop)

    def test_pose_dry_run_leaves_originals_and_runtime_untouched(self) -> None:
        self._pose_inputs(self.source_root)
        before = _snapshot(self.root)
        self._prepare(dry_run=True)
        self.assertEqual(_snapshot(self.root), before)

    def test_missing_pose_direction_cannot_partially_import_other_actions(self) -> None:
        self._pose_inputs(self.source_root)
        for path in self.source_root.glob("greenhero_hd_jump_W*.png"):
            path.unlink()
        before = _snapshot(self.package_root)
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "missing jump.*W"):
            self._prepare()
        self.assertEqual(_snapshot(self.package_root), before)

    def test_pose_batches_reject_ambiguous_stills_and_mismatched_canvases(self) -> None:
        self._pose_inputs(self.source_root)
        duplicate = self.source_root / "greenhero_test_run_N.png"
        duplicate.write_bytes(_png(3, 4))
        before = _snapshot(self.package_root)
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "ambiguous run.*N"):
            self._prepare()
        self.assertEqual(_snapshot(self.package_root), before)
        duplicate.unlink()
        (self.source_root / "greenhero_hd_run_N.png").write_bytes(_png(4, 4))
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "pose canvas must match"):
            self._prepare()
        self.assertEqual(_snapshot(self.package_root), before)

    def test_single_action_import_preserves_other_runtime_poses_and_reference(self) -> None:
        self._pose_inputs(self.source_root)
        before_stand = _snapshot(self.package_root / "stand")
        before_walk = _snapshot(self.package_root / "walk")
        reference = self.generator.load_package(self.manifest_path).reference_pose
        self._prepare(action="run")
        package = self.generator.load_package(self.manifest_path)
        self.generator.validate_runtime_assets(package, self.package_root)
        self.assertEqual(package.actions, ("stand", "walk", "run"))
        self.assertEqual(package.reference_pose, reference)
        self.assertEqual(_snapshot(self.package_root / "stand"), before_stand)
        self.assertEqual(_snapshot(self.package_root / "walk"), before_walk)

    def test_legacy_grid_import_can_replace_stand_walk_while_retaining_new_poses(self) -> None:
        poses = self.root / "poses"
        self._pose_inputs(poses)
        self.importer.prepare_test_package(self.package_root, source_root=poses)
        before_run = _snapshot(self.package_root / "run")
        self._prepare(action="both")
        package = self.generator.load_package(self.manifest_path)
        self.generator.validate_runtime_assets(package, self.package_root)
        for animation in package.animations:
            animated = animation.action in ("stand", "walk")
            self.assertEqual(animation.frame_count, 16 if animated else 1)
            self.assertEqual(animation.loop, animated)
        self.assertEqual(_snapshot(self.package_root / "run"), before_run)

    def test_failed_pose_write_restores_the_previous_package(self) -> None:
        self._pose_inputs(self.source_root)
        before = _snapshot(self.package_root)
        write_atomic = self.importer._write_atomic
        calls = 0

        def fail_once(path: Path, payload: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 20:
                raise OSError("simulated full disk")
            write_atomic(path, payload)

        with mock.patch.object(self.importer, "_write_atomic", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "simulated full disk"):
                self._prepare()
        self.assertEqual(_snapshot(self.package_root), before)

    def test_batch_maps_compass_names_and_updates_layout_without_changing_inputs(self) -> None:
        inputs = _snapshot(self.source_root)
        self._prepare()
        self.assertEqual(_snapshot(self.source_root), inputs)
        package = self.generator.load_package(self.manifest_path)
        self.generator.validate_runtime_assets(package, self.package_root)
        self.assertEqual(package.source_canvas, (5, 6))
        for direction in INPUT_DIRECTIONS:
            payload = (self.source_root / f"{direction}_solo_4x4_o.png").read_bytes()
            for action in ("stand", "walk"):
                path = (
                    self.package_root / action
                    / f"greenhero_{direction}_{action}_spritesheet_4x4_o.png"
                )
                self.assertEqual(path.read_bytes(), payload)
        for animation in package.animations:
            self.assertEqual(animation.foot_anchor, (2, 6))
            self.assertEqual(animation.height_pixels, 6)
        self.assertEqual(
            (self.package_root / package.resource_file).read_text(),
            self.generator.generate_resource(package),
        )
        snapshot = _snapshot(self.package_root)
        self._prepare()
        self.assertEqual(_snapshot(self.package_root), snapshot)

    def test_dry_run_leaves_all_files_untouched(self) -> None:
        before = _snapshot(self.root)
        self._prepare(dry_run=True)
        self.assertEqual(_snapshot(self.root), before)

    def test_canonical_compass_names_preserve_all_eight_directions(self) -> None:
        expected = {}
        for direction in INPUT_DIRECTIONS:
            source = self.source_root / f"{direction}_solo_4x4_o.png"
            expected[direction] = source.read_bytes()
            source.rename(
                source.with_name(f"greenhero_{direction}_stand_spritesheet_4x4_o.png")
            )
        self._prepare(action="stand")
        for direction, payload in expected.items():
            path = self.package_root / f"stand/greenhero_{direction}_stand_spritesheet_4x4_o.png"
            self.assertEqual(path.read_bytes(), payload)
        self.assertNotEqual(expected["N"], expected["W"])

    def test_legacy_keyboard_names_import_into_compass_names(self) -> None:
        legacy = {"N": "w", "NO": "wd", "O": "d", "SO": "sd",
                  "S": "s", "SW": "sa", "W": "a", "NW": "wa"}
        expected = {}
        for direction, key in legacy.items():
            source = self.source_root / f"{direction}_solo_4x4_o.png"
            expected[direction] = source.read_bytes()
            source.rename(source.with_name(f"greenhero_{key}_walk_spritesheet_4x4_o.png"))
        self._prepare(action="walk")
        for direction, payload in expected.items():
            path = self.package_root / f"walk/greenhero_{direction}_walk_spritesheet_4x4_o.png"
            self.assertEqual(path.read_bytes(), payload)

    def test_canonical_and_legacy_north_are_rejected_as_duplicate_input(self) -> None:
        source = self.source_root / "N_solo_4x4_o.png"
        source.rename(source.with_name("greenhero_N_stand_spritesheet_4x4_o.png"))
        (self.source_root / "greenhero_w_stand_spritesheet_4x4_o.png").write_bytes(_png(20, 24))
        before = _snapshot(self.package_root)
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "ambiguous stand"):
            self._prepare(action="stand")
        self.assertEqual(_snapshot(self.package_root), before)

    def test_walk_only_preserves_stand_images_and_reference(self) -> None:
        before = _snapshot(self.package_root / "stand")
        self._prepare(action="walk")
        self.assertEqual(_snapshot(self.package_root / "stand"), before)
        package = self.generator.load_package(self.manifest_path)
        self.generator.validate_runtime_assets(package, self.package_root)
        self.assertEqual(package.reference_pose.height_pixels, 4)
        self.assertEqual(package.source_canvas, (3, 4))
        for animation in package.animations:
            self.assertEqual(animation.height_pixels, 6 if animation.action == "walk" else 4)

    def test_action_folder_overrides_shared_sheets(self) -> None:
        folder = self.source_root / "walk"
        folder.mkdir()
        payload = _png(20, 24, 240)
        (folder / "greenhero_W_walk_spritesheet_4x4_o.png").write_bytes(payload)
        self._prepare()
        walk = self.package_root / "walk/greenhero_W_walk_spritesheet_4x4_o.png"
        stand = self.package_root / "stand/greenhero_W_stand_spritesheet_4x4_o.png"
        self.assertEqual(walk.read_bytes(), payload)
        self.assertNotEqual(stand.read_bytes(), payload)

    def test_external_grid_names_leave_candidate_inputs_unchanged(self) -> None:
        incoming = self.root / "candidate"
        incoming.mkdir()
        for source in self.source_root.iterdir():
            name = source.name.replace("_4x4_o.png", "_4x4.png")
            shutil.copyfile(source, incoming / name)
        before_inputs = {
            path.name: path.read_bytes() for path in incoming.glob("*.png")
        }
        self.importer.prepare_test_package(self.package_root, source_root=incoming)
        package = self.generator.load_package(self.manifest_path)
        self.generator.validate_runtime_assets(package, self.package_root)
        for direction in INPUT_DIRECTIONS:
            payload = before_inputs[f"{direction}_solo_4x4.png"]
            for action in ("stand", "walk"):
                output = (
                    self.package_root / action
                    / f"greenhero_{direction}_{action}_spritesheet_4x4_o.png"
                )
                self.assertEqual(output.read_bytes(), payload)
        self.assertEqual(
            {path.name: path.read_bytes() for path in incoming.glob("*.png")},
            before_inputs,
        )

    def test_incomplete_candidate_cannot_fall_back_to_existing_runtime_images(self) -> None:
        incoming = self.root / "incomplete"
        incoming.mkdir()
        shutil.copyfile(
            self.source_root / "N_solo_4x4_o.png", incoming / "N_solo_4x4.png",
        )
        before = _snapshot(self.package_root)
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "missing stand"):
            self.importer.prepare_test_package(self.package_root, source_root=incoming)
        self.assertEqual(_snapshot(self.package_root), before)

    def test_full_grid_names_are_supported_in_sources(self) -> None:
        for path in self.source_root.iterdir():
            path.rename(path.with_name(path.name.replace("_4x4_o.png", "_4x4.png")))
        self._prepare()
        package = self.generator.load_package(self.manifest_path)
        self.generator.validate_runtime_assets(package, self.package_root)
        self.assertEqual(package.source_canvas, (5, 6))

    def test_optimized_and_full_grid_duplicates_are_rejected(self) -> None:
        shutil.copyfile(
            self.source_root / "N_solo_4x4_o.png", self.source_root / "N_solo_4x4.png",
        )
        before = _snapshot(self.package_root)
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "ambiguous stand"):
            self._prepare()
        self.assertEqual(_snapshot(self.package_root), before)

    def test_incomplete_or_ambiguous_directions_do_not_replace_any_files(self) -> None:
        missing = self.source_root / "W_solo_4x4_o.png"
        payload = missing.read_bytes()
        missing.unlink()
        before = _snapshot(self.package_root)
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "missing stand"):
            self._prepare()
        self.assertEqual(_snapshot(self.package_root), before)
        missing.write_bytes(payload)
        (self.source_root / "E_solo_4x4_o.png").write_bytes(payload)
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "ambiguous stand"):
            self._prepare()
        self.assertEqual(_snapshot(self.package_root), before)

    def test_corrupt_png_or_incomplete_grid_does_not_replace_any_files(self) -> None:
        source = self.source_root / "W_solo_4x4_o.png"
        for payload in (b"invalid PNG", _png(21, 24)):
            source.write_bytes(payload)
            before = _snapshot(self.package_root)
            with self.assertRaises(self.generator.AnimationPackageError):
                self._prepare()
            self.assertEqual(_snapshot(self.package_root), before)

    def test_other_variants_cannot_be_replaced(self) -> None:
        manifest = json.loads(self.manifest_path.read_text())
        manifest["variant"] = "hd"
        self.manifest_path.write_text(json.dumps(manifest))
        before = _snapshot(self.package_root)
        with self.assertRaisesRegex(self.generator.AnimationPackageError, "only the test"):
            self._prepare()
        self.assertEqual(_snapshot(self.package_root), before)

    @unittest.skipUnless(shutil.which("sh"), "the shell entry point requires sh")
    def test_shell_entry_point_accepts_paths_with_spaces_from_another_directory(self) -> None:
        repository = self.root / "repository with spaces"
        tools = repository / "game/tools"
        tools.mkdir(parents=True)
        for filename in ("prepare_green_hero_test.py", "generate_green_hero_animations.py"):
            shutil.copyfile(TOOLS_ROOT / filename, tools / filename)
        target = repository / "game/test_assets/characters/heroes/greenhero/test"
        shutil.copytree(self.package_root, target)
        wrapper = target / "rename_test_assets.sh"
        shutil.copyfile(MANIFEST_PATH.parent / wrapper.name, wrapper)
        before = _snapshot(target)
        result = subprocess.run(
            ["sh", str(wrapper), "--source-dir", str(self.source_root), "--dry-run"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Test package validated", result.stdout)
        self.assertEqual(_snapshot(target), before)


if __name__ == "__main__":
    unittest.main()
