#!/usr/bin/env python3
"""Stand-Farbreferenz → weiche, feste oder materialgebundene PNG-Farben → GIFs und Vergleich."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import dataclass
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import quote

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PiplineToos"))
import PyImgColorMatch as color
import PyImgFixedColors as exact
import PyImgGif as gif
import PyPipelineOutputs as outputs

FRAME_FOLDER = re.compile(r"spritesheet-fram(?:e)?([1-9][0-9]*)$", re.I)
OPTIMIZED = re.compile(r"_\d+x\d+(?:_o)?$", re.I)
DIRECTION = re.compile(r"_(N|NO|NW|O|S|SO|SW|W)$", re.I)


@dataclass(frozen=True)
class Source:
    path: Path
    relative: Path
    grid: tuple[int, int]
    size: tuple[int, int]
    sha256: str


def pngs(folder):
    if not folder.is_dir() or folder.is_symlink():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and not p.is_symlink()
                  and not p.name.startswith(".") and p.suffix.lower() == ".png"
                  and not OPTIMIZED.search(p.stem))


def high_sources(folder):
    result = pngs(folder)
    for child in sorted(folder.iterdir()):
        if child.is_dir() and not child.is_symlink() and FRAME_FOLDER.fullmatch(child.name):
            result.extend(pngs(child / "PixelEng"))
    return result


def discover(root):
    """Nur flache PNGs bzw. die bekannten comic_high/PixelEng-Quellen auswählen."""
    if not root.is_dir():
        raise ValueError(f"Quellordner fehlt: {root}")
    if (root / "mask-templates.json").exists():
        raise ValueError("Maskenordner gewählt; QUELLE muss die Original-Sheets enthalten.")
    if (root / "color-build.json").exists():
        raise ValueError("Bereits farbangepasste Ausgabe gewählt; erneut von den Originalen starten.")
    if root.name == "comic_high":
        return high_sources(root)
    if (root / "comic_high").is_dir():
        return high_sources(root / "comic_high")
    poses = [p for p in sorted(root.iterdir()) if p.is_dir() and not p.is_symlink()
             and not p.name.startswith(".") and (p / "comic_high").is_dir()]
    if poses:
        return [image for pose in poses for image in high_sources(pose / "comic_high")]
    if FRAME_FOLDER.fullmatch(root.name):
        return pngs(root / "PixelEng")
    return pngs(root)


def discover_single(root):
    """Single sources directly, per pose, or directly in comic_high; never frame folders."""
    if not root.is_dir():
        raise ValueError(f"Quellordner fehlt: {root}")
    excluded = {"comic_mid", "comic_low", "pixel_high", "pixel_low", "pixeleng",
                "materialmasken", "masken", "masks", "vorschau", "archive", "archiv", "backup"}

    def usable(folder):
        return (folder.is_dir() and not folder.is_symlink() and not folder.name.startswith(".")
                and folder.name.casefold() not in excluded and not FRAME_FOLDER.fullmatch(folder.name)
                and not (folder / "color-build.json").exists()
                and not (folder / "mask-templates.json").exists())

    if not usable(root):
        raise ValueError("SourceColor erwartet Original-Einzelbilder; kein Frame-, Masken- oder Ausgabeordner.")
    if root.name == "comic_high":
        return pngs(root)
    if (root / "comic_high").is_dir():
        return pngs(root / "comic_high")
    result = pngs(root)
    for folder in sorted(root.iterdir()):
        if usable(folder):
            result.extend(pngs(folder / "comic_high" if (folder / "comic_high").is_dir() else folder))
    return result


def single_grid(path, size):
    if "spritesheet" in path.stem.casefold() or OPTIMIZED.search(path.stem) or any(
            FRAME_FOLDER.fullmatch(parent.name) for parent in path.parents):
        raise ValueError(f"SourceColor verarbeitet Einzelbilder; Spritesheet erkannt: {path}")
    return (1, 1)


def infer_grid(path, size, explicit=None):
    frame_count = next((int(m[1]) for p in path.parents if (m := FRAME_FOLDER.fullmatch(p.name))), None)
    is_sheet = frame_count is not None or "spritesheet" in path.stem.lower()
    if explicit is not None and is_sheet:
        grid = explicit
    elif is_sheet:
        count = frame_count or 16
        grid = (count, 1) if size[0] >= size[1] else (1, count)
    else:
        grid = (1, 1)
    if math.prod(grid) > 64:
        raise ValueError(f"Höchstens 64 Frames unterstützt: {path}")
    list(color.frame_boxes(size, grid))
    if frame_count and frame_count != math.prod(grid):
        raise ValueError(f"Raster widerspricht Frameordner: {path}")
    return grid


def inspect(paths, root, grid, *, single_images=False):
    result = []
    names = set()
    for path in paths:
        if any(p.is_symlink() for p in path.parents):
            raise ValueError(f"Quelle liegt in einem symbolischen Verzeichnis: {path}")
        relative = path.relative_to(root)
        if str(relative).casefold() in names:
            raise ValueError(f"Mehrdeutiger Ausgabename: {relative}")
        names.add(str(relative).casefold())
        with color.load_png(path) as image:
            layout = single_grid(path, image.size) if single_images else infer_grid(path, image.size, grid)
            if image.getchannel("A").getbbox() is None:
                raise ValueError(f"Vollständig transparentes Quellbild: {path}")
            result.append(Source(path, relative, layout, image.size, color.sha256(path)))
    if not result:
        raise ValueError(f"Keine Original-PNGs gefunden: {root}")
    return result


def reference_files(root, explicit, grid, *, single_images=False):
    if explicit:
        folder = explicit.expanduser().absolute()
        paths = pngs(folder)
        stand = [p for p in paths if "_stand_" in p.name.lower()]
        paths = stand or paths
    else:
        base = root / "stand" / "comic_high"
        candidates = [base, root / "stand", root] if single_images else [base / "spritesheet-fram16" / "PixelEng", base, root]
        if not single_images and root.name == "comic_high" and root.parent.name == "stand":
            candidates.insert(0, root / "spritesheet-fram16" / "PixelEng")
        paths = []
        for folder in candidates:
            paths = [p for p in pngs(folder) if "_stand_" in p.name.lower()]
            if paths:
                break
    sheets = [p for p in paths if "spritesheet" in p.stem.lower()] if not single_images else []
    paths = sheets or paths
    by_direction = {}
    for path in paths:
        match = DIRECTION.search(path.stem)
        if not match:
            continue
        direction = match[1].upper()
        if direction in by_direction:
            raise ValueError(f"Mehrere Stand-Referenzen für {direction}; --reference auf eindeutigen Ordner setzen.")
        with color.load_png(path) as image:
            layout = single_grid(path, image.size) if single_images else infer_grid(path, image.size, grid)
            by_direction[direction] = (path, direction, layout)
    missing = set(color.DIRECTIONS) - by_direction.keys()
    if missing:
        raise ValueError(f"Stand-Referenz unvollständig ({', '.join(sorted(missing))}); --reference ORDNER angeben.")
    return [by_direction[d] for d in color.DIRECTIONS]


def parse_grid(value):
    match = re.fullmatch(r"([1-9][0-9]*)[xX×]([1-9][0-9]*)", value)
    if not match or math.prod(map(int, match.groups())) > 64:
        raise argparse.ArgumentTypeError("Raster als Spalten×Zeilen mit höchstens 64 Frames angeben, z.B. 16x1.")
    return tuple(map(int, match.groups()))


def url(path, root):
    return quote(os.path.relpath(path, root).replace(os.sep, "/"), safe="/")


def is_reference(source, profile, mode):
    for ref in profile["references"]:
        if source.sha256 != ref["sha256"]:
            continue
        if mode == "soft":
            return True  # Bisheriges Verhalten beibehalten.
        path = Path(ref["path"])
        if (source.path.resolve() == path.resolve() or source.path.name.casefold() == path.name.casefold()) \
                and list(source.grid) == ref["grid"] and list(source.size) == ref["size"]:
            return True
    return False


def comparison_html(sources, root, profile, strength=None, mode="soft"):
    single_only = all(source.grid == (1, 1) for source in sources)
    refs = {r["direction"]: r for r in profile["references"]}
    records = []
    for source in sources:
        match = DIRECTION.search(source.path.stem)
        ref = refs.get(match[1].upper()) if match else None
        ref_path = Path(ref["path"]) if ref else None
        # Referenz kann auch als bytegleiche Kopie in der neuen Ausgabe liegen.
        matching = next((s for s in sources if ref and s.sha256 == ref["sha256"]
                         and (mode == "soft" or s.path.name.casefold() == Path(ref["path"]).name.casefold())), None)
        if matching:
            ref_path = root / matching.relative
        reference_copy = is_reference(source, profile, mode)
        records.append({"name": source.relative.as_posix(), "before": url(source.path, root),
                        "after": url(root / source.relative, root), "grid": source.grid,
                        "reference": url(ref_path, root) if ref_path and (matching or ref_path.is_file()) else None,
                        "referenceCopy": reference_copy,
                        "mask": url(root / ".material_masks" / source.relative, root)
                        if mode == "material" and not reference_copy else None,
                        "refGrid": ref["grid"] if ref else [1, 1]})
    data = json.dumps(records, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    def swatch(colors):
        return '<div class="palette">' + "".join(
            f'<span title="RGB {c}" style="background:rgb({c[0]},{c[1]},{c[2]})"></span>'
            for c in colors) + "</div>"
    legend = ""
    if mode == "material":
        swatches = "".join(f'<p>{m["id"]} · {html.escape(m["name"])}</p>' + swatch(m["colors"])
                           for m in profile["materials"])
        legend = '<p class="legend">' + " ".join(
            f'<span><i style="background:rgb({",".join(map(str, exact.preview_color(m["id"])))})"></i>'
            f'{m["id"]} · {html.escape(m["name"])}</span>' for m in profile["materials"]) + "</p>"
        details = "Feste Farbreihen je Material"
        note = ("Jeder eingefärbte sichtbare PNG-Pixel gehört exakt zur Farbreihe seiner Material-ID. "
                "Die vollständige Maskenbelegung ist technisch geprüft. "
                "Materialzuordnung und Übergänge bitte visuell prüfen; die Palettenprüfung bestätigt keine semantische Materialtreue.")
    elif mode == "fixed":
        swatches, details = swatch(profile["colors"]), "Verbindliche gemeinsame Festpalette"
        note = "Jeder eingefärbte sichtbare PNG-Pixel gehört exakt zur gemeinsamen Festpalette. Materialgrenzen bitte visuell prüfen."
    else:
        swatches, details = swatch(profile["pixel_palette"]), f"Gemeinsame Pixelpalette · Stärke {strength}"
        note = "Weicher Farbabgleich: Die PNGs behalten volle Abstufungen. Ähnlich gefärbte Materialien wie Haare und Leder bitte visuell prüfen."
    mask_panel = (f'<figure id="mask-panel"><figcaption>Materialmaske · gleiche {"Bildposition" if single_only else "Frameposition"}</figcaption>'
                  '<canvas id="mask"></canvas></figure>') if mode == "material" else ""
    return '''<!doctype html><html lang="de"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Farbvergleich</title>
<style>body{background:#161b22;color:#ecf1f8;font:16px system-ui;margin:24px}h1{font-size:24px}
select{max-width:100%}button,select,input{font:inherit;margin:6px}main{display:flex;flex-wrap:wrap;gap:16px}
figure{margin:0;flex:1;min-width:260px}canvas{width:100%;max-width:640px;height:auto;background-color:#777;
background-image:conic-gradient(#666 25%,transparent 0 50%,#666 0 75%,transparent 0);background-size:24px 24px}
.palette{display:flex;flex-wrap:wrap;max-width:768px}.palette span{width:24px;height:24px}p{max-width:1000px}
.legend{display:flex;flex-wrap:wrap;gap:12px}.legend i{display:inline-block;width:18px;height:18px;margin-right:6px;vertical-align:middle}
[hidden]{display:none!important}</style>
<h1>Farbvergleich · Modus MODE</h1>
<p>Alle acht Stand-Richtungen bilden die gemeinsame Farbreferenz. PRESENTATION
REFERENCECOPYNOTICE</p><p>NOTE</p>
<label>Bild <select id="choice"></select></label><button id="play">Pause</button>
<label id="frame-control">Frame <input id="frame" type="range" min="0" value="0"></label><span id="counter"></span>
<p id="state"></p><main><figure><figcaption>Original</figcaption><canvas id="before"></canvas></figure>
<figure><figcaption id="after-label">Ergebnis · MODE</figcaption><canvas id="after"></canvas></figure>
<figure><figcaption>Stand · gleiche Richtung</figcaption><canvas id="reference"></canvas></figure>MASKPANEL</main>
LEGEND<details open><summary>DETAILS</summary>SWATCHES
<p>Maßgeblich sind gespeicherte sRGB-Werte der PNGs. IMAGEFORMATCAVEAT</p></details>
<script>
const records=RECORDS, choice=document.getElementById('choice'), slider=document.getElementById('frame');
let active=records[0], images={}, frame=0, playing=true, last=0, generation=0;
for(const [i,r] of records.entries()){const o=document.createElement('option');o.value=i;o.textContent=r.name;choice.append(o)}
function draw(id,img,grid,index){const c=document.getElementById(id),ctx=c.getContext('2d');
 if(!img){ctx.clearRect(0,0,c.width,c.height);return}const w=img.naturalWidth/grid[0],h=img.naturalHeight/grid[1];
 if(c.width!==w||c.height!==h){c.width=w;c.height=h}ctx.clearRect(0,0,w,h);ctx.imageSmoothingEnabled=false;
 ctx.drawImage(img,(index%grid[0])*w,Math.floor(index/grid[0])*h,w,h,0,0,w,h)}
function render(){draw('before',images.before,active.grid,frame);draw('after',images.after,active.grid,frame);
 if(document.getElementById('mask'))draw('mask',images.mask,active.grid,frame);
 const n=active.grid[0]*active.grid[1],rn=active.refGrid[0]*active.refGrid[1];
 draw('reference',images.reference,active.refGrid,Math.floor(frame*rn/n));
 slider.value=frame;document.getElementById('counter').textContent=n===1?'Einzelbild':`${frame+1} / ${n} · 8 FPS`}
function select(){active=records[choice.value||0];frame=0;images={};generation++;const token=generation;
 slider.max=active.grid[0]*active.grid[1]-1;
 const single=active.grid[0]*active.grid[1]===1;
 document.getElementById('play').hidden=single;document.getElementById('frame-control').hidden=single;
 if(single)playing=false;document.getElementById('play').textContent=playing?'Pause':'Abspielen';
 document.getElementById('after-label').textContent=active.referenceCopy?'Unveränderte Stand-Referenzkopie':'Ergebnis · MODE';
 document.getElementById('state').textContent=(active.referenceCopy?'Bytegleiche Referenzkopie · keine Festfarbenprüfung.':
   (active.mask?'Materialmaske vollständig geprüft · Materialtreue visuell prüfen.':'Eingefärbtes Ziel-PNG.'))+
   (active.reference?'':' Referenzdatei hier nicht verfügbar.');
 const panel=document.getElementById('mask-panel');if(panel)panel.hidden=!active.mask;
 for(const id of ['before','after','reference','mask']){if(!active[id])continue;const img=new Image();
 img.onload=()=>{if(token===generation){images[id]=img;render()}};
 img.onerror=()=>{if(token===generation)document.getElementById('state').textContent='Bild nicht verfügbar: '+active[id]};img.src=active[id]}render()}
choice.onchange=select;const play=document.getElementById('play');
play.onclick=()=>{playing=!playing;play.textContent=playing?'Pause':'Abspielen'};
slider.oninput=()=>{playing=false;play.textContent='Abspielen';frame=Number(slider.value);render()};
function tick(t){if(playing&&images.before&&images.after&&t-last>=125){frame=(frame+1)%(active.grid[0]*active.grid[1]);render();last=t}requestAnimationFrame(tick)}
select();requestAnimationFrame(tick);
</script></html>'''.replace("MODE", mode).replace("NOTE", html.escape(note)).replace("DETAILS", html.escape(details)).replace(
        "MASKPANEL", mask_panel).replace("LEGEND", legend).replace("SWATCHES", swatches).replace(
        "PRESENTATION", "Original und Ergebnis werden als Einzelbilder verglichen." if single_only else "Original und Ergebnis laufen synchron.").replace(
        "IMAGEFORMATCAVEAT", "" if single_only else "GIFs können Farben und Teiltransparenz nur eingeschränkt darstellen.").replace(
        "REFERENCECOPYNOTICE", "Stand-Kopien bleiben unverändert und sind von der Festfarbenprüfung ausgenommen." if any(r['referenceCopy'] for r in records)
        else "Alle ausgewählten Bilder werden mit demselben Farbprofil korrigiert.").replace("RECORDS", data)


def atomic_copy(source, target):
    fd, name = tempfile.mkstemp(prefix=".color-copy-", dir=target.parent)
    os.close(fd)
    try:
        shutil.copyfile(source, name)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)


def validate_options(args):
    preparation = any((args.export_fixed_palette, args.export_material_profile, args.prepare_masks))
    if preparation:
        forbidden = {"--color-mode": args.color_mode, "--output-dir": args.output_dir,
                     "--strength": args.strength, "--max-distance": args.max_distance,
                     "--fixed-palette": args.fixed_palette, "--material-profile": args.material_profile}
        if args.prepare_masks:
            forbidden.update({"--reference": args.reference, "--profile": args.profile,
                              "--material-definitions": args.material_definitions, "--mask-dir": args.mask_dir})
        elif args.export_fixed_palette:
            forbidden.update({"--material-definitions": args.material_definitions, "--mask-dir": args.mask_dir})
        else:
            forbidden["--profile"] = args.profile
            if not args.material_definitions or not args.mask_dir:
                raise ValueError("--export-material-profile benötigt --material-definitions und --mask-dir.")
        used = [name for name, value in forbidden.items() if value is not None]
        if used:
            raise ValueError("Vorbereitungsaktion nicht mit " + ", ".join(used) + " kombinieren.")
        return
    mode = args.color_mode or "soft"
    if args.material_definitions:
        raise ValueError("--material-definitions gehört ausschließlich zu --export-material-profile.")
    if mode == "soft":
        if args.fixed_palette or args.material_profile or args.mask_dir:
            raise ValueError("soft erlaubt keine --fixed-palette, --material-profile oder --mask-dir.")
    else:
        if args.reference or args.profile:
            raise ValueError("fixed/material verwenden die Herkunft im exakten Profil; --reference/--profile weglassen.")
        if args.strength is not None or args.max_distance is not None:
            raise ValueError("--strength und --max-distance gelten nur für soft; Festfarben werden ohne Mischung geschrieben.")
        if mode == "fixed" and (not args.fixed_palette or args.material_profile or args.mask_dir):
            raise ValueError("fixed benötigt --fixed-palette; --material-profile/--mask-dir sind hier nicht erlaubt.")
        if mode == "material" and (not args.material_profile or not args.mask_dir or args.fixed_palette):
            raise ValueError("material benötigt --material-profile und --mask-dir; --fixed-palette ist hier nicht erlaubt.")


def checked_directory(path, label, must_exist=True):
    path = path.expanduser().absolute()
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError(f"{label} darf keine symbolischen Verzeichnisse enthalten: {path}")
    if (must_exist and not path.is_dir()) or (path.exists() and not path.is_dir()):
        raise ValueError(f"{label} ist kein vorhandener Ordner: {path}")
    return path.resolve()


def input_files(args):
    paths = [p.expanduser().absolute() for p in
             (args.profile, args.fixed_palette, args.material_profile, args.material_definitions) if p]
    for path in paths:
        outputs.validate(path)
        if not path.is_file():
            raise ValueError(f"Eingabedatei fehlt: {path}")
    return paths


def validate_targets(targets, protected):
    if len(targets) != len({str(p.resolve()).casefold() for p in targets}):
        raise ValueError("Ausgabepfade sind mehrdeutig.")
    protected = list(protected)
    for target in targets:
        outputs.validate(target)
        for original in protected:
            if target.resolve() == original.resolve() or (
                    target.exists() and original.exists() and target.samefile(original)):
                raise ValueError(f"Ausgabe würde eine Eingabe ersetzen: {target}")


def text_output(path, content, args):
    if args.dry_run:
        outputs.should_write(path, overwrite=args.overwrite, dry_run=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        outputs.write_text(path, content, overwrite=args.overwrite)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def soft_profile(args, root, *, single_images=False):
    if args.profile:
        return color.load_profile(args.profile.expanduser())
    refs = reference_files(root, args.reference, args.grid, single_images=single_images)
    print("Referenz: Stand, acht Richtungen; alle Frames gleich gewichtet.", flush=True)
    return color.make_profile(refs)


def validate_template(path, source, overwrite):
    # Vorlagen dürfen bereits manuell beschriftet sein; im Normalmodus unverändert erhalten.
    with path.open("rb") as stream:
        header = stream.read(26)
    if len(header) < 26 or not header.startswith(b"\x89PNG\r\n\x1a\n") or header[24] != 8:
        raise ValueError(f"Vorhandene Datei ist keine 8-Bit-Maskenvorlage: {path}")
    with Image.open(path) as image:
        if (image.mode not in {"L", "P"} or getattr(image, "n_frames", 1) != 1
                or "transparency" in image.info or image.info.get(exact.MASK_VERSION) != "1"):
            raise ValueError(f"Vorhandene Datei ist keine eigene Labelmaske und bleibt erhalten: {path}")
        if not overwrite and (image.size != source.size
                or image.info.get(exact.MASK_GRID) != f"{source.grid[0]}x{source.grid[1]}"
                or image.info.get(exact.MASK_SOURCE) != source.sha256):
            raise ValueError(f"Maskenvorlage gehört zu anderer Quelle/Raster: {path}; --overwrite verwenden.")
        image.load()


def save_template(source, target):
    fd, name = tempfile.mkstemp(prefix=".mask-template-", suffix=".png", dir=target.parent)
    os.close(fd)
    try:
        with Image.new("L", source.size, 0) as mask:
            mask.save(name, format="PNG", pnginfo=exact.mask_metadata(source.grid, source.sha256))
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)


def prepare_masks(args, root, sources):
    destination = checked_directory(args.prepare_masks, "Maskenvorlagenordner", must_exist=False)
    if destination == root or root.is_relative_to(destination):
        raise ValueError("Für Maskenvorlagen einen eigenen Unterordner oder separaten Ordner wählen.")
    manifest_path = destination / "mask-templates.json"
    targets = [destination / s.relative for s in sources]
    validate_targets([*targets, manifest_path], [s.path for s in sources])
    if manifest_path.exists():
        previous = exact.read_json(manifest_path)
        if previous.get("format") != "pyimg-mask-templates" or previous.get("version") != 1:
            raise ValueError(f"Fremde Datei bleibt erhalten: {manifest_path}")
    for source, target in zip(sources, targets):
        if target.exists():
            validate_template(target, source, args.overwrite)
    for source in sources:
        if color.sha256(source.path) != source.sha256:
            raise ValueError(f"Quelle wurde während der Prüfung verändert: {source.path}")
    for source, target in zip(sources, targets):
        if outputs.should_write(target, overwrite=args.overwrite, dry_run=args.dry_run):
            target.parent.mkdir(parents=True, exist_ok=True)
            save_template(source, target)
    manifest = {"format": "pyimg-mask-templates", "version": 1, "source_root": str(root),
                "status": "Vorlagen unvollständig: ID 0 ist Hintergrund; alle sichtbaren Pixel manuell markieren.",
                "complete": False, "images": [{"path": s.relative.as_posix(), "grid": s.grid,
                "size": s.size, "source_sha256": s.sha256} for s in sources]}
    text_output(manifest_path, json_text(manifest), args)
    print(f"{'Plan geprüft' if args.dry_run else 'Vorlagen erstellt/erhalten'}: {len(sources)} Labelmasken. "
          "Neue Masken sind unvollständig; Material-IDs vor --color-mode material markieren.")
    return 0


def export_profile(args, root, sources, protected, *, single_images=False):
    target = (args.export_fixed_palette or args.export_material_profile).expanduser().absolute()
    if target.suffix.lower() != ".json":
        raise ValueError("Profilexport benötigt eine .json-Ausgabedatei.")
    if args.export_fixed_palette:
        profile, loader = exact.make_palette(soft_profile(args, root, single_images=single_images)), exact.load_palette
    else:
        masks = checked_directory(args.mask_dir, "Maskenordner")
        refs = reference_files(root, args.reference, args.grid, single_images=single_images)
        definitions = exact.load_definitions(args.material_definitions.expanduser())
        profile = exact.make_material_profile(refs, definitions, masks, root)
        protected += [masks / path.relative_to(root) for path, _, _ in refs]
        loader = exact.load_material_profile
    protected += [Path(r["path"]) for r in profile["references"]]
    validate_targets([target], protected)
    if target.exists() and not args.overwrite and loader(target) != profile:
        raise ValueError(f"Vorhandenes Profil weicht ab und bleibt erhalten: {target}; --overwrite verwenden.")
    text_output(target, json_text(profile), args)
    print(f"{'Plan geprüft' if args.dry_run else 'Profil erstellt/erhalten'}: {target}. "
          "Abgeleitete Zielfarben vor der Anwendung visuell prüfen.")
    return 0


def mask_inputs(sources, profile, masks):
    records = {}
    for i, source in enumerate(sources, 1):
        if is_reference(source, profile, "material"):
            continue
        path = masks / source.relative
        print(f"[Maskenprüfung {i}/{len(sources)}] {source.relative}", flush=True)
        original_hash = color.sha256(path) if path.is_file() else None
        with color.load_png(source.path) as before, exact.load_mask(
                path, before, source.grid, profile["materials"], source.sha256):
            if color.sha256(path) != original_hash:
                raise ValueError(f"Maske wurde während der Prüfung verändert: {path}")
            records[source.relative] = {"path": path, "sha256": original_hash}
    return records


def open_images(stack, source, reference, matcher, profile, mask_record):
    if color.sha256(source.path) != source.sha256:
        raise ValueError(f"Quelle wurde während der Verarbeitung verändert: {source.path}")
    before = stack.enter_context(color.load_png(source.path))
    mask = None
    if mask_record:
        if color.sha256(mask_record["path"]) != mask_record["sha256"]:
            raise ValueError(f"Maske wurde während der Verarbeitung verändert: {mask_record['path']}")
        mask = stack.enter_context(exact.load_mask(mask_record["path"], before, source.grid,
                                                  profile["materials"], source.sha256))
    after = stack.enter_context(before.copy() if reference else
                                matcher.apply(before, mask) if mask is not None else matcher.apply(before))
    return before, after, mask


def image_record(source, reference, before, after, mode, profile, mask, mask_record):
    record = {"path": source.relative.as_posix(), "source_sha256": source.sha256,
              "reference_copy": reference, "grid": source.grid, "frames": math.prod(source.grid),
              "color_management": before.info["color_management"], **color.verify_pixels(before, after)}
    if reference:
        record["palette_check"] = "not_applicable_reference_copy"
    elif mode != "soft":
        record.update(exact.verify_palette(after, profile, mask))
    if mask_record:
        record.update({"mask_path": str(mask_record["path"]), "mask_sha256": mask_record["sha256"]})
    return record


def validate_existing_png(path, expected, reference=None, stored_rgb=False):
    if reference and color.sha256(path) != reference.sha256:
        raise ValueError(f"Vorhandene Stand-Kopie ist nicht bytegleich: {path}; --overwrite verwenden.")
    with color.load_png(path) as existing:
        if existing.size != expected.size or existing.tobytes() != expected.tobytes():
            raise ValueError(f"Vorhandenes PNG weicht ab und bleibt erhalten: {path}; --overwrite verwenden.")
    if stored_rgb:
        with Image.open(path) as saved, saved.convert("RGBA") as pixels:
            if pixels.tobytes() != expected.tobytes():
                raise ValueError(f"Gespeicherte RGB-Werte weichen ab: {path}; --overwrite verwenden.")


def previous_settings(report_path, settings, sources, masks):
    previous = exact.read_json(report_path)
    old_settings = previous.get("settings")
    if not isinstance(old_settings, dict):
        raise ValueError("Vorhandener Bericht enthält keine gültigen Farbeinstellungen.")
    # Berichte aus dem bisherigen einzigen Modus haben noch kein color_mode-Feld.
    old_settings = {"color_mode": "soft", **old_settings}
    if old_settings != settings:
        raise ValueError("Vorhandene Ausgabe hat andere Farbeinstellungen; --overwrite verwenden.")
    images = previous.get("images")
    if not isinstance(images, list) or any(not isinstance(r, dict) or not isinstance(r.get("path"), str) for r in images):
        raise ValueError("Vorhandener Bericht enthält keine gültige Quellliste.")
    old = {r["path"]: r for r in images}
    for source in sources:
        record = old.get(source.relative.as_posix())
        if record is None:
            continue
        if record.get("source_sha256") != source.sha256 or record.get("grid") != list(source.grid):
            raise ValueError(f"Originalquelle oder Raster hat sich geändert: {source.relative}; --overwrite verwenden.")
        mask = masks.get(source.relative)
        if mask and record.get("mask_sha256") != mask["sha256"]:
            raise ValueError(f"Materialmaske hat sich geändert: {source.relative}; --overwrite verwenden.")


def run(args, *, single_images=False):
    validate_options(args)
    root = checked_directory(args.source, "Quellpfad")
    protected = input_files(args)
    input_hashes = {path: color.sha256(path) for path in protected}
    sources = inspect(discover_single(root) if single_images else discover(root), root, args.grid,
                      single_images=single_images)
    protected += [s.path for s in sources]
    if args.prepare_masks:
        return prepare_masks(args, root, sources)
    if args.export_fixed_palette or args.export_material_profile:
        return export_profile(args, root, sources, protected, single_images=single_images)
    mode = args.color_mode or "soft"
    destination = checked_directory(args.output_dir or root.with_name(
        root.name + {"soft": "-color", "fixed": "-fixed", "material": "-material"}[mode]),
        "Ausgabeordner", must_exist=False)
    if root == destination or destination.is_relative_to(root) or root.is_relative_to(destination):
        raise ValueError("Separaten Ausgabeordner außerhalb des Quellbaums wählen.")
    masks, mask_root = {}, None
    if mode == "soft":
        profile, loader = soft_profile(args, root, single_images=single_images), color.load_profile
        args.strength = 0.75 if args.strength is None else args.strength
        args.max_distance = 18 if args.max_distance is None else args.max_distance
        matcher = color.ColorMatcher(profile, args.strength, args.max_distance)
        settings = {"method": color.METHOD, "strength": args.strength,
                    "max_distance": args.max_distance, "lut_size": 33}
        profile_name = "reference-colors.json"
    elif mode == "fixed":
        profile, loader = exact.load_palette(args.fixed_palette.expanduser()), exact.load_palette
        matcher, settings, profile_name = exact.FixedMatcher(profile), {"method": exact.FIXED_METHOD}, "fixed-palette.json"
    else:
        profile, loader = exact.load_material_profile(args.material_profile.expanduser()), exact.load_material_profile
        matcher, settings = exact.MaterialMatcher(profile), {"method": exact.MATERIAL_METHOD, "mask_format_version": 1}
        profile_name = "material-colors.json"
        mask_root = checked_directory(args.mask_dir, "Maskenordner")
        if (destination == mask_root or destination.is_relative_to(mask_root)
                or mask_root.is_relative_to(destination)):
            raise ValueError("Ausgabeordner und Maskeneingaben dürfen sich nicht überlappen.")
        masks = mask_inputs(sources, profile, mask_root)
        protected += [m["path"] for m in masks.values()]
    settings.update({"color_mode": mode, "profile_sha256": color.fingerprint(profile), "fps": None if single_images else 8})
    if single_images:
        settings["source_kind"] = "single_image"
    protected += [Path(r["path"]) for r in profile["references"]]
    profile_path = destination / ".color_profile" / profile_name
    report_path, html_path = destination / "color-build.json", destination / "farbvergleich.html"
    targets = [profile_path, report_path, html_path]
    paths = {}
    for source in sources:
        target = destination / source.relative
        gif_path = target.with_name(target.stem + "_8fps.gif") if math.prod(source.grid) > 1 else None
        preview_path = destination / ".material_masks" / source.relative if source.relative in masks else None
        paths[source.relative] = (target, gif_path, preview_path)
        targets.extend(p for p in (target, gif_path, preview_path) if p is not None)
    validate_targets(targets, protected)
    if not args.overwrite:
        if profile_path.exists() and loader(profile_path) != profile:
            raise ValueError("Vorhandenes Farbprofil weicht ab; anderen Zielordner oder --overwrite verwenden.")
        if report_path.exists():
            previous_settings(report_path, settings, sources, masks)
    planned_records = {}
    # Alle Masken, Parametervarianten und vorhandenen Ausgaben vor dem ersten Schreiben prüfen.
    # Neue Ziele benötigen hier keinen zweiten kompletten Farbtransform; dry-run prüft ihn immer.
    for i, source in enumerate(sources, 1):
        target, gif_path, preview_path = paths[source.relative]
        if not args.dry_run and (args.overwrite or not any(p and p.exists() for p in (target, gif_path, preview_path))):
            continue
        print(f"[Bestandsprüfung {i}/{len(sources)}] {source.relative}", flush=True)
        reference = is_reference(source, profile, mode)
        with ExitStack() as stack:
            before, after, mask = open_images(stack, source, reference, matcher, profile, masks.get(source.relative))
            planned_records[source.relative] = image_record(source, reference, before, after, mode, profile,
                                                            mask, masks.get(source.relative))
            if not args.overwrite:
                if target.exists():
                    validate_existing_png(target, after, source if reference else None, mode != "soft" and not reference)
                if gif_path and gif_path.exists():
                    # PNGs dürfen unabhängig ergänzt werden. Ihre neue mtime würde sonst ein
                    # erhaltenes GIF beim Folgelauf fälschlich veralten lassen; Quellhash und
                    # Farbeinstellungen werden separat geprüft, die Geometrie bleibt exakt.
                    if not gif.reusable_gif(source.path, gif_path, 8, gif.Grid(*source.grid, "Color"), keep_empty=True):
                        raise ValueError(f"Vorhandenes GIF ist veraltet/beschädigt: {gif_path}; --overwrite verwenden.")
                if preview_path and preview_path.exists():
                    with exact.mask_preview(mask, before, profile["materials"]) as preview:
                        validate_existing_png(preview_path, preview, stored_rgb=True)
    # Änderungen in späteren Quellen/Masken dürfen nicht erst nach ersten Ausgabeschritten auffallen.
    for source in sources:
        if color.sha256(source.path) != source.sha256:
            raise ValueError(f"Quelle wurde während der Prüfung verändert: {source.path}")
    for record in masks.values():
        if color.sha256(record["path"]) != record["sha256"]:
            raise ValueError(f"Maske wurde während der Prüfung verändert: {record['path']}")
    for path, digest in input_hashes.items():
        if color.sha256(path) != digest:
            raise ValueError(f"Eingabeprofil wurde während der Prüfung verändert: {path}")
    records = []
    for i, source in enumerate(sources, 1):
        target, gif_path, preview_path = paths[source.relative]
        print(f"[{i}/{len(sources)}] {source.relative} | {mode} | {source.grid[0]}x{source.grid[1]}", flush=True)
        reference = is_reference(source, profile, mode)
        if args.dry_run or (not args.overwrite and all(p is None or p.exists() for p in (target, gif_path, preview_path))):
            records.append(planned_records[source.relative])
            for path in (target, gif_path, preview_path):
                if path:
                    outputs.should_write(path, overwrite=args.overwrite, dry_run=args.dry_run)
            continue
        with ExitStack() as stack:
            before, after, mask = open_images(stack, source, reference, matcher, profile, masks.get(source.relative))
            record = image_record(source, reference, before, after, mode, profile, mask, masks.get(source.relative))
            if outputs.should_write(target, overwrite=args.overwrite):
                target.parent.mkdir(parents=True, exist_ok=True)
                if reference:
                    atomic_copy(source.path, target)
                else:
                    color.save_png(after, target)
            if gif_path and outputs.should_write(gif_path, overwrite=args.overwrite):
                frames = [after.crop(box) for box in color.frame_boxes(after.size, source.grid)]
                try:
                    result = gif.save_gif(frames, gif_path, 8)
                    record.update({"gif_stored_frames": result.stored_frames, "gif_duration_ms": result.duration_ms})
                finally:
                    for frame in frames:
                        frame.close()
            if preview_path and outputs.should_write(preview_path, overwrite=args.overwrite):
                preview_path.parent.mkdir(parents=True, exist_ok=True)
                with exact.mask_preview(mask, before, profile["materials"]) as preview:
                    color.save_png(preview, preview_path)
            records.append(record)
    content = comparison_html(sources, destination, profile, args.strength, mode)
    report = {"settings": settings, "source_root": str(root), "output_root": str(destination),
              "images": records, "checks": "PNG-Größe, Alpha und unsichtbares RGB exakt; keine Frameverschiebung.",
              "visual_review": "Farben und Materialzuordnung in farbvergleich.html visuell prüfen. "
                               "Technische Palettenprüfung bestätigt keine semantische Materialtreue."}
    if mask_root:
        report["mask_root"] = str(mask_root)
    if input_hashes:
        report["profile_input"] = {"path": str(next(iter(input_hashes))), "sha256": next(iter(input_hashes.values()))}
    for path, value in ((profile_path, json_text(profile)), (report_path, json_text(report)), (html_path, content)):
        text_output(path, value, args)
    print(f"{'Plan geprüft' if args.dry_run else 'Fertig'}: Modus {mode}; {len(sources)} PNGs; "
          f"{sum(r['reference_copy'] for r in records)} unveränderte Referenzen.\n→ {html_path}")
    return 0


def main(argv=None, *, single_images=False):
    description = "SourceColor: Einzelbilder aller Posen mit gemeinsamen Stand-Farben; PNGs und Vergleich ohne Frame-Reduktion oder GIFs." if single_images else __doc__
    parser = argparse.ArgumentParser(description=description, allow_abbrev=False)
    parser.add_argument("source", nargs="?", type=Path, default=Path.cwd(), help="PNG-Ordner, Pose oder Posen-Wurzel")
    reference = parser.add_mutually_exclusive_group()
    reference.add_argument("--reference", type=Path, help="Ordner mit den acht Stand-Originalen; sonst automatisch")
    reference.add_argument("--profile", type=Path, help="Vorhandenes reference-colors.json wiederverwenden")
    parser.add_argument("--color-mode", choices=("soft", "fixed", "material"),
                        help="Farbmodus; Standard soft (bisheriges Verhalten)")
    parser.add_argument("--fixed-palette", type=Path, help="Verbindliche pyimg-fixed-palette-JSON für fixed")
    parser.add_argument("--material-profile", type=Path, help="Verbindliche pyimg-material-colors-JSON für material")
    parser.add_argument("--mask-dir", type=Path, help="Quellgebundene L/P-Labelmasken in gleicher relativer Ordnerstruktur")
    preparation = parser.add_mutually_exclusive_group()
    preparation.add_argument("--export-fixed-palette", type=Path, metavar="DATEI.json",
                             help="Festpalette aus allen acht Stand-Richtungen oder --profile ableiten; keine Bildkorrektur")
    preparation.add_argument("--export-material-profile", type=Path, metavar="DATEI.json",
                             help="Materialfarbreihen aus gelabelten Stand-Referenzen ableiten; --material-definitions + --mask-dir")
    preparation.add_argument("--prepare-masks", type=Path, metavar="ORDNER",
                             help="Unvollständige L8-Nullmasken aller Quellen mit Raster/Quellhash vorbereiten; anschließend markieren")
    parser.add_argument("--material-definitions", type=Path,
                        help="Material-IDs, Namen, Anzahl Farbstufen (levels); nur für --export-material-profile")
    parser.add_argument("--output-dir", type=Path, help="Separater Ausgabeordner; Standard: <Quelle>-color, -fixed oder -material")
    if single_images:
        parser.set_defaults(grid=None)
    else:
        parser.add_argument("--grid", type=parse_grid, help="Quellraster für Sheets, z.B. 16x1; Einzelbilder bleiben einzeln")
    parser.add_argument("--strength", type=float, help="Nur soft: Stärke 0..1; Standard 0.75")
    parser.add_argument("--max-distance", type=float, help="Nur soft: maximaler Lab-Farbabstand 1..50; Standard 18")
    parser.add_argument("--dry-run", action="store_true", help="Eingaben, Farbtransform und Ausgaben prüfen; nichts schreiben")
    parser.add_argument("--overwrite", action="store_true", help="Nur gewählte Ausgaben im getrennten Ziel ersetzen")
    args = parser.parse_args(argv)
    try:
        return run(args, single_images=single_images)
    except (ValueError, OSError, gif.ConversionError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
