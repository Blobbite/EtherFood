"""Gemeinsamer Vertrag aller Starter: Normal, Dry-run und Overwrite."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
STARTERS = {
    "Fram8": "0-SpritesheetFram8-Pipline/PyPiplineStart-SpritesheetFram8.py",
    "Fram16": "0-SpritesheetFram16-Pipline/PyPiplineStart-SpritesheetFram16.py",
    "Reduce": "1-SpritesheetFramReduce-Pipline/PyPiplineStart-SpritesheetFramReduce.py",
    "Resolution": "2-SpritesheetResolution-Pipline/PyPiplineStart-SpritesheetResolution.py",
}


def snapshot(root):
    return {str(p.relative_to(root)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def make_sheet(path, count, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (columns*12, count//columns*10))
    draw = ImageDraw.Draw(image)
    for i in range(count):
        x,y = i % columns * 12, i // columns * 10
        draw.rectangle((x+2,y+2,x+8,y+7), fill=(30+i*12,120,80,255))
    image.save(path)


class OutputModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="output modes # ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def prepare(self, name):
        root = self.base / name
        root.mkdir()
        if name in ("Fram8", "Fram16"):
            count = 8 if name == "Fram8" else 16
            source = root / "hero_N.png"
            make_sheet(source,count,count)
            original = root / "PixelEng/hero_N.png"
            output = root / f"hero_N_{'4x2' if count==8 else '4x4'}_o.png"
        elif name == "Reduce":
            source = original = root / "spritesheet-fram16/PixelEng/hero_N.png"
            make_sheet(source,16,16)
            output = root / "spritesheet-fram8/hero_N_4x2_o.png"
        else:
            source = original = root / "comic_high/spritesheet-fram8/hero_N_4x2_o.png"
            make_sheet(source,8,4)
            output = root / "comic_mid/spritesheet-fram8/hero_N_4x2_o.png"
        return root, source, original, output

    def call(self, name, root, *args, expected=0):
        result = subprocess.run([sys.executable,str(ROOT/"Pipline"/STARTERS[name]),str(root),*args],
                                capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        return result

    def test_all_starters_normal_preserves_every_existing_file_and_dry_run_writes_nothing(self):
        for name in STARTERS:
            with self.subTest(pipeline=name):
                root,source,original,output = self.prepare(name)
                source_bytes = source.read_bytes()
                before = snapshot(root)
                tree = set(root.rglob("*"))
                for flags in (("--dry-run",),("--dry-run","--overwrite")):
                    self.call(name,root,*flags)
                    self.assertEqual(snapshot(root),before)
                    self.assertEqual(set(root.rglob("*")),tree)
                self.call(name,root)
                self.assertEqual(original.read_bytes(),source_bytes)
                before = snapshot(root)
                self.call(name,root)
                self.assertEqual(snapshot(root),before)  # HTML und Prüfberichte sind eingeschlossen.
                for flags in (("--dry-run",),("--dry-run","--overwrite")):
                    self.call(name,root,*flags)
                    self.assertEqual(snapshot(root),before)

    def test_overwrite_repairs_only_planned_outputs_and_protects_sources_and_foreign_files(self):
        for name in STARTERS:
            with self.subTest(pipeline=name):
                root,source,original,output = self.prepare(name)
                self.call(name,root)
                original_bytes = original.read_bytes()
                original_time = original.stat().st_mtime_ns
                output.write_bytes(b"corrupt output")
                animation = output.with_name(output.stem+"_8fps.gif")
                animation.write_bytes(b"corrupt gif")
                html = output.parent/"gif-vergleich.html"
                html.write_text("old gallery")
                foreign = [output.parent/"fremd_5x2_o.png",output.parent/"fremd_8fps.gif",output.parent/"notizen.txt"]
                for p in foreign:
                    p.write_bytes(b"foreign, do not replace")
                if name == "Reduce":
                    (output.parent/"PixelEng/hero_N.png").write_bytes(b"old reduced copy")
                    (output.parent/"pruefung.json").write_text("old report")
                before = snapshot(root)
                self.call(name,root,expected=0 if name=="Reduce" else 1)
                self.assertEqual(snapshot(root),before)
                planned = self.call(name,root,"--dry-run","--overwrite")
                self.assertIn("ERSETZEN",planned.stdout)
                self.assertEqual(snapshot(root),before)
                self.call(name,root,"--overwrite")
                with Image.open(output) as image:
                    self.assertEqual(image.format,"PNG")
                with Image.open(animation) as image:
                    self.assertEqual(image.format,"GIF")
                self.assertIn("<html",html.read_text())
                self.assertEqual((original.read_bytes(),original.stat().st_mtime_ns),(original_bytes,original_time))
                for p in foreign:
                    self.assertEqual(snapshot(root)[str(p.relative_to(root))],before[str(p.relative_to(root))])
                if name == "Reduce":
                    self.assertTrue(json.loads((output.parent/"pruefung.json").read_text())["passed"])

    def test_reduce_overwrite_only_selected_variants_and_rejects_source_links(self):
        root,_,original,_ = self.prepare("Reduce")
        self.call("Reduce",root)
        keep = root/"spritesheet-fram8"
        before = snapshot(keep)
        self.call("Reduce",root,"--overwrite","--frames","10","14")
        self.assertEqual(snapshot(keep),before)
        target = root/"spritesheet-fram10/PixelEng/hero_N.png"
        target.unlink()
        target.symlink_to(original)
        before = snapshot(root)
        self.call("Reduce",root,"--overwrite","--frames","10",expected=1)
        self.assertEqual(snapshot(root),before)

    def test_normal_fills_missing_outputs_without_rewriting_existing_html(self):
        for name in ("Fram8","Fram16","Resolution"):
            with self.subTest(pipeline=name):
                root,_,_,output = self.prepare(name)
                self.call(name,root)
                animation = output.with_name(output.stem+"_8fps.gif")
                animation.unlink()
                before = snapshot(root)
                self.call(name,root)
                self.assertTrue(animation.is_file())
                after = snapshot(root)
                self.assertEqual(before,{k:v for k,v in after.items() if k in before})

    def test_resolution_recursive_html_modes_obey_flags_and_never_touch_images(self):
        root=self.base/"poses"
        source=root/"run/comic_high/spritesheet-fram8/hero_N_4x2_o.png"
        make_sheet(source,8,4)
        self.call("Resolution",root,"-s-a")
        htmls=list(root.rglob("*.html"))
        for html in htmls:
            html.write_text(html.read_text()+"\n<!-- preserved -->")
        before=snapshot(root)
        self.call("Resolution",root,"-s-a","--html-only")
        self.assertEqual(snapshot(root),before)
        self.call("Resolution",root,"-s-a","--html-only","--dry-run","--overwrite")
        self.assertEqual(snapshot(root),before)
        self.call("Resolution",root,"-s-a","--html-only","--overwrite")
        self.assertTrue(all("<!-- preserved -->" not in html.read_text() for html in htmls))
        after=snapshot(root)
        self.assertEqual({p:v for p,v in before.items() if not p.endswith(".html")},
                         {p:v for p,v in after.items() if not p.endswith(".html")})


if __name__ == "__main__":
    unittest.main()
