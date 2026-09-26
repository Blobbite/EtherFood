"""Wrapper-Lebenszyklus in temporären Pfaden; keine Systeminstallation, kein Netz."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "PyGameTools.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pygametools-install-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.install = self.root / "Programm mit 'Leerzeichen' und $zeichen"
        self.bin = self.root / "bin mit Leerzeichen"
        self.work = self.root / "Arbeitsordner"
        self.work.mkdir()

    def prepared(self):
        self.install.mkdir()
        (self.install / installer.MARKER).write_text(json.dumps(installer.IDENTITY))
        for relative in installer.FILES:
            target = self.install / "app" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        python = self.install / "venv/bin/python"
        python.parent.mkdir(parents=True)
        python.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} \"$@\"\n")
        python.chmod(0o755)

    def call(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(ROOT / "PyGameTools.py"),
                                 "--install-dir", str(self.install), "--bin-dir", str(self.bin), *args],
                                cwd=self.work, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def wrapper(self, name, *args):
        env = os.environ.copy()
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        env.pop("PYTHONPATH", None)
        result = subprocess.run([name, *args], cwd=self.work, env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_six_wrappers_run_from_caller_folder_and_uninstall(self):
        self.prepared()
        self.call("--apply-system")
        self.assertEqual(set(path.name for path in self.bin.iterdir()), set(installer.COMMANDS))
        self.assertEqual(len(installer.COMMANDS), 6)
        for name in installer.COMMANDS:
            self.wrapper(name, "--help")
        color_root = self.work / "Farbquellen"
        color_root.mkdir()
        for direction in ("N", "NO", "O", "SO", "S", "SW", "W", "NW"):
            Image.new("RGBA", (128, 8), (80, 120, 40, 255)).save(
                color_root / f"hero_stand_spritesheet_{direction}.png")
        Image.new("RGBA", (128, 8), (70, 122, 48, 255)).save(color_root / "hero_run_spritesheet_N.png")
        self.wrapper("PyPiplineStart-SpritesheetColor", str(color_root))
        self.assertTrue((self.work / "Farbquellen-color/farbvergleich.html").is_file())
        self.assertTrue((self.work / "Farbquellen-color/hero_run_spritesheet_N_8fps.gif").is_file())
        single_root = self.work / "Source-Posen"
        single_root.mkdir()
        for direction in ("N", "NO", "O", "SO", "S", "SW", "W", "NW"):
            Image.new("RGBA", (12, 10), (80, 120, 40, 255)).save(single_root / f"hero_stand_{direction}.png")
        Image.new("RGBA", (12, 10), (70, 122, 48, 255)).save(single_root / "hero_jump_N.png")
        self.wrapper("PyPiplineStart-SourceColor", str(single_root))
        self.assertTrue((self.work / "Source-Posen-color/hero_jump_N.png").is_file())
        self.assertFalse(list((self.work / "Source-Posen-color").rglob("*.gif")))
        # Alle installierten Pipelines ausführen, ohne den Projektpfad im PATH.
        Image.new("RGBA", (192, 10), (40, 150, 80, 255)).save(self.work / "hero_N.png")
        self.wrapper("PyPiplineStart-SpritesheetFram16")
        self.assertTrue((self.work / "PixelEng/hero_N.png").is_file())
        self.assertTrue((self.work / "hero_N_4x4_o_8fps.gif").is_file())
        fram8 = self.work / "spritesheet-fram8"
        fram8.mkdir()
        Image.new("RGBA", (12, 80), (60, 140, 90, 255)).save(fram8 / "hero_N.png")
        self.wrapper("PyPiplineStart-SpritesheetFram8", str(fram8))
        self.assertTrue((fram8 / "PixelEng/hero_N.png").is_file())
        with Image.open(fram8 / "hero_N_4x2_o.png") as sheet:
            self.assertEqual(sheet.size, (48, 20))
        self.assertTrue((fram8 / "hero_N_4x2_o_8fps.gif").is_file())
        high = self.work / "comic_high/spritesheet-fram16"
        high.mkdir(parents=True)
        shutil.copy2(self.work / "hero_N_4x4_o.png", high)
        high8 = self.work / "comic_high/spritesheet-fram8"
        high8.mkdir()
        shutil.copy2(fram8 / "hero_N_4x2_o.png", high8)
        archive = high / "PixelEng"
        archive.mkdir()
        shutil.copy2(self.work / "PixelEng/hero_N.png", archive)
        existing8 = (high8 / "hero_N_4x2_o.png").read_bytes()
        reduce = self.wrapper("PyPiplineStart-SpritesheetFramReduce", str(high.parent))
        self.assertIn("[SKIP] spritesheet-fram8", reduce.stdout)
        self.assertEqual((high8 / "hero_N_4x2_o.png").read_bytes(), existing8)
        self.assertFalse((high8 / "PixelEng").exists())
        self.assertTrue((high.parent / "spritesheet-fram10/hero_N_5x2_o_8fps.gif").is_file())
        self.assertTrue((high.parent / "spritesheet-fram14/pruefung.json").is_file())
        self.wrapper("PyPiplineStart-SpritesheetResolution", "--variants", "comic_mid")
        self.assertTrue((self.work / "comic_mid/spritesheet-fram16/hero_N_4x4_o_8fps.gif").is_file())
        self.assertTrue((self.work / "comic_mid/spritesheet-fram8/hero_N_4x2_o_8fps.gif").is_file())
        self.assertTrue((self.work / "aufloesungsvergleich.html").is_file())
        self.assertFalse((self.install / "comic_mid").exists())
        self.assertFalse((self.install / "app/Tools").exists())
        unrelated = self.bin / "PyAnderesTool"
        unrelated.write_text("fremdes Werkzeug")
        self.call("--uninstall")
        self.assertFalse(self.install.exists())
        self.assertEqual(unrelated.read_text(), "fremdes Werkzeug")
        self.assertTrue((self.work / "hero_N_4x4_o.png").exists())

    def test_conflicting_wrapper_prevents_partial_install(self):
        self.prepared()
        self.bin.mkdir()
        conflict = self.bin / list(installer.COMMANDS)[1]
        conflict.write_text("fremder Befehl")
        self.call("--apply-system", expected=1)
        self.assertEqual(list(self.bin.iterdir()), [conflict])
        self.assertEqual(conflict.read_text(), "fremder Befehl")

    def test_resolution_update_keeps_old_wrapper_working_until_wrapper_migration(self):
        self.prepared()
        old_name = "PyPiplineStart-SpritsheetAll"
        old_relative = "Pipline/SpritesheetAll-Pipline/PyPiplineStart-SpritsheetAll.py"
        old_script = self.install / "app" / old_relative
        old_script.parent.mkdir(parents=True)
        old_script.write_text("raise SystemExit('alte Installation')\n")
        self.bin.mkdir()
        old_wrapper = self.bin / old_name
        old_wrapper.write_text(installer.wrapper_content(self.install, old_relative))
        old_wrapper.chmod(0o755)
        before = old_wrapper.read_bytes(), old_wrapper.stat().st_mtime_ns
        # Das Update ersetzt app/, kann aber die systemweiten Wrapper nicht schreiben.
        with patch.object(installer.subprocess, "run"):
            installer.prepare(self.install)
        self.assertEqual((old_wrapper.read_bytes(), old_wrapper.stat().st_mtime_ns), before)
        self.assertIn("SpritesheetResolution", self.wrapper(old_name, "--help").stdout)
        high = self.work / "comic_high"
        high.mkdir()
        Image.new("RGBA", (16, 12), (80, 130, 40, 255)).save(high / "hero_N.png")
        self.wrapper(old_name, "--variants", "comic_mid", "--no-gif")
        with Image.open(self.work / "comic_mid/hero_N.png") as result:
            self.assertEqual(result.size, (8, 6))
        planned = self.call("--apply-system", "--dry-run")
        self.assertIn("PyPiplineStart-SpritesheetResolution", planned.stdout)
        self.assertEqual(set(p.name for p in self.bin.iterdir()), {old_name})
        self.assertEqual((old_wrapper.read_bytes(), old_wrapper.stat().st_mtime_ns), before)
        self.call("--apply-system")
        self.assertFalse(old_wrapper.exists())
        self.assertEqual(set(p.name for p in self.bin.iterdir()), set(installer.COMMANDS))
        self.wrapper("PyPiplineStart-SpritesheetResolution", "--help")

    def test_resolution_migration_and_uninstall_preserve_foreign_old_command(self):
        self.prepared()
        self.bin.mkdir()
        foreign = self.bin / "PyPiplineStart-SpritsheetAll"
        foreign.write_text("eigenes Werkzeug; nicht von PyGameTools\n")
        before = foreign.read_bytes(), foreign.stat().st_mtime_ns
        self.call("--apply-system")
        self.assertEqual((foreign.read_bytes(), foreign.stat().st_mtime_ns), before)
        self.call("--uninstall")
        self.assertEqual((foreign.read_bytes(), foreign.stat().st_mtime_ns), before)

    def test_uninstall_removes_owned_old_wrapper_without_prior_migration(self):
        self.prepared()
        self.bin.mkdir()
        old = self.bin / "PyPiplineStart-SpritsheetAll"
        old.write_text(installer.wrapper_content(
            self.install, "Pipline/SpritesheetAll-Pipline/PyPiplineStart-SpritsheetAll.py"))
        self.call("--uninstall")
        self.assertFalse(old.exists())
        self.assertFalse(self.install.exists())

    def test_dry_run_and_unmanaged_target_leave_files_alone(self):
        self.call("--install", "--dry-run")
        self.assertFalse(self.install.exists())
        self.assertFalse(self.bin.exists())
        self.install.mkdir()
        keep = self.install / "eigen.txt"
        keep.write_text("behalten")
        self.call("--uninstall", expected=1)
        self.assertEqual(keep.read_text(), "behalten")

    def test_root_cannot_install_dependencies(self):
        with patch.object(installer.os, "geteuid", return_value=0), \
                patch.object(installer, "prepare") as prepare:
            result = installer.main(["--prepare", "--install-dir", str(self.install)])
        self.assertEqual(result, 1)
        prepare.assert_not_called()
        self.assertFalse(self.install.exists())

    def test_incomplete_installation_does_not_create_wrappers(self):
        self.prepared()
        (self.install / "app" / installer.INTERNAL_FILES[0]).unlink()
        self.call("--apply-system", expected=1)
        self.assertFalse(self.bin.exists())


if __name__ == "__main__":
    unittest.main()
