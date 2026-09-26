#!/usr/bin/env python3
"""Alle Animationsprüfungen nacheinander starten und ihre Ergebnisse zusammenfassen.

Eigenständiges Python-Programm für direkte Aufrufe und Linux-Wrapper.
Benötigte Pakete laut venv.txt: numpy und pillow.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, dataclass, fields
import html
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    print("Fehlende Abhängigkeit:", exc, file=sys.stderr)
    print("Benötigte Pakete in der venv: numpy pillow (siehe venv.txt)", file=sys.stderr)
    raise SystemExit(1)

VERSION = "2.2.0"

MIN_FRAMES, MAX_FRAMES = 3, 24

ZONE_LABELS = {"full": "Gesamtfigur", "top": "Oberer Bereich",
               "middle": "Mittlerer Bereich", "bottom": "Unterer Bereich"}

SCORES = (("Gesamt", "overall_score"), ("Loop-Bild", "loop_score"),
          ("Loop-Fluss", "seam_score"), ("Bewegungsruhe", "calmness_score"),
          ("Details", "detail_score"))

METRIC_LABELS = {"position_step": "Positionssprung", "direction_change": "Bewegungsfortsetzung",
                 "shape_step": "Formänderung", "shape_change": "Formfortsetzung",
                 "appearance_change": "Bildänderung", "color_change": "Farbänderung",
                 "alpha_change": "Transparenz-/Konturänderung"}

DETAIL_LABELS = {"texture_continuation": "Falten-/Texturfortsetzung",
                 "contour_continuation": "Lokale Konturfortsetzung"}

GOOD, NOTICE = .78, .65
STYLE = """
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#09121f;color:#e1eaf5}
body{max-width:1220px;margin:auto;padding:28px}h1{font-size:27px}h2{font-size:21px;margin-top:30px}h1,h2,p,li{overflow-wrap:anywhere}
p,li{line-height:1.65;color:#adbed2}a{color:#9ed8f5}img{max-width:100%;height:auto;border:1px solid #34455d;border-radius:8px}
.scores{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}.score{background:#142237;padding:16px;border-radius:8px}
.score b{float:right}.track{height:9px;background:#28394f;margin-top:12px;border-radius:9px;overflow:hidden}.track div{height:100%}
.gif{width:460px}.warning{border-left:3px solid #efb475;padding-left:14px}.card{padding:12px 0 26px;border-bottom:1px solid #33445d}
canvas{max-width:100%;max-height:538px;background:repeating-conic-gradient(#18283c 0% 25%,#24364c 0% 50%) 0/24px 24px}
button,select,input{font:inherit;margin:8px;padding:6px}button,select{color:inherit;background:#20354e;border:1px solid #6683a5;border-radius:4px}
@media(max-width:650px){body{padding:16px}.scores{grid-template-columns:1fr}h1{font-size:22px}}
@media(prefers-reduced-motion:reduce){.gif{display:none}}
"""

CHECKS = {'loop-image': ('Loop-Bild', 'loop_score', 'PyImgAnimTestLoopBild.py'), 'loop-flow': ('Loop-Fluss', 'seam_score', 'PyImgAnimTestLoopFluss.py'), 'calmness': ('Bewegungsruhe', 'calmness_score', 'PyImgAnimTestBewegungsruhe.py'), 'details': ('Details', 'detail_score', 'PyImgAnimTestDetails.py')}


@dataclass
class FrameMetrics:
    index: int
    bbox: tuple
    center_x: float
    center_y: float
    visible_pixels: int

@dataclass
class PairMetrics:
    a: int
    b: int
    dx: float
    dy: float
    shift_magnitude: float
    silhouette_iou: float
    alpha_similarity: float
    rgb_similarity: float
    score: float
    legacy_score: float = 0.

def validate_frame_count(n):
    if isinstance(n, bool) or not isinstance(n, int) or not MIN_FRAMES <= n <= MAX_FRAMES:
        raise ValueError(f"Framezahl muss zwischen {MIN_FRAMES} und {MAX_FRAMES} liegen.")

def choose_layout(img, frames, mode):
    w, h = img.size
    if mode in {"horizontal", "vertical"}:
        cols, rows = (frames, 1) if mode == "horizontal" else (1, frames)
    elif re.fullmatch(r"[1-9]\d*[xX][1-9]\d*", mode):
        cols, rows = map(int, mode.lower().split("x"))
        if cols * rows != frames:
            raise ValueError("Explizites Raster und Framezahl widersprechen sich.")
    elif mode == "auto":
        candidates = []
        for c in range(1, frames + 1):
            if frames % c:
                continue
            r = frames // c
            if w % c == 0 and h % r == 0:
                candidates.append((abs(math.log((w / c) / (h / r))) + abs(c-r) * .12, c, r))
        if not candidates:
            raise ValueError("Kein gleichmäßiges Raster erkannt. --grid und -f prüfen.")
        _, cols, rows = min(candidates)
    else:
        raise ValueError("--grid erwartet auto, horizontal, vertical oder SpaltenxZeilen.")
    if w % cols or h % rows or w < cols or h < rows:
        raise ValueError("Bildgröße ist nicht ohne Rest durch das Raster teilbar.")
    return cols, rows

def split_frames(img, frames, mode):
    validate_frame_count(frames)
    cols, rows = choose_layout(img, frames, mode)
    fw, fh = img.width // cols, img.height // rows
    return [img.crop((i % cols * fw, i // cols * fh,
                      (i % cols + 1) * fw, (i // cols + 1) * fh)).convert("RGBA")
            for i in range(frames)], cols, rows

def frame_metrics(img, idx, threshold):
    mask = np.asarray(img)[..., 3] > threshold
    ys, xs = np.where(mask)
    if not len(xs):
        return FrameMetrics(idx, (0, 0, 0, 0), 0., 0., 0)
    return FrameMetrics(idx, (int(xs.min()), int(ys.min()), int(xs.max())+1, int(ys.max())+1),
                        float(xs.mean()), float(ys.mean()), int(mask.sum()))

def global_character_bbox(frames, threshold):
    boxes = [frame_metrics(f, i, threshold).bbox for i, f in enumerate(frames)]
    boxes = [b for b in boxes if b[2] > b[0] and b[3] > b[1]]
    if not boxes:
        return (0, 0, frames[0].width, frames[0].height)
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))

def reference_indices(n):
    # N-1→N, N→1, 1→2 sind das Prüf-Fenster, nicht seine eigene Referenz.
    return list(range(1, n-2)) if n >= 6 else list(range(n-1))

def report_scores(report):
    test = report.get("test", "all")
    return SCORES if test == "all" else (CHECKS[test][:2],)

def artifact_stem(path, test="all"):
    return path.stem+"_animtest"+("" if test == "all" else "_"+test.replace("-", "_"))

def index_name(test="all"):
    return "animtest"+("" if test == "all" else "_"+test.replace("-", "_"))+"_index.html"

def region_label(report, name):
    return report["regions"].get(name, {}).get("label", ZONE_LABELS.get(name, name))

def bar(score, width=20):
    full = round(float(np.clip(score, 0, 1))*width) if score is not None else 0
    return "█"*full+"░"*(width-full)

def rating(score):
    if score is None:
        return "⚪ nicht bewertbar"
    if score >= .90:
        return "🟢 sehr gut"
    if score >= GOOD:
        return "🟢 gut"
    if score >= NOTICE:
        return "🟡 auffällig"
    return "🔴 kritisch"

def percentage(score):
    return "—" if score is None else f"{score*100:.1f}%"

def font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()

def checker(size):
    image = Image.new("RGB", size, "#142338")
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], 16):
        for x in range(0, size[0], 16):
            if (x//16+y//16) % 2:
                draw.rectangle((x, y, x+15, y+15), fill="#1d3047")
    return image

def display_geometry(frames, edge=420):
    # EIN gemeinsamer Ausschnitt für alle Frames: kein Wegzentrieren eines Sprungs.
    box = global_character_bbox(frames, 0)
    box = (max(0, box[0]-12), max(0, box[1]-12),
           min(frames[0].width, box[2]+12), min(frames[0].height, box[3]+12))
    scale = min(edge/max(1, box[2]-box[0]), edge/max(1, box[3]-box[1]))
    size = (max(1, round((box[2]-box[0])*scale)), max(1, round((box[3]-box[1])*scale)))
    offset = ((edge-size[0])//2, (edge-size[1])//2)
    return box, size, offset, scale

def render_stage(frame, geometry, edge=420):
    box, size, offset, _ = geometry
    result = checker((edge, edge)).convert("RGBA")
    image = frame.crop(box).resize(size, Image.Resampling.LANCZOS)
    result.alpha_composite(image, offset)
    return result.convert("RGB")

def arrow(draw, start, end, color):
    draw.line([start, end], fill=color, width=3)
    dx, dy = end[0]-start[0], end[1]-start[1]
    length = math.hypot(dx, dy)
    if length < 2:
        draw.ellipse((end[0]-3, end[1]-3, end[0]+3, end[1]+3), outline=color, width=2)
        return
    ux, uy = dx/length, dy/length
    draw.polygon([end, (end[0]-ux*9-uy*4, end[1]-uy*9+ux*4),
                  (end[0]-ux*9+uy*4, end[1]-uy*9-ux*4)], fill=color)

def create_slow_gif(frames, report, output, slow_factor):
    geometry = display_geometry(frames)
    indices = [len(frames)-2, len(frames)-1, 0, 1]
    images, durations = [], []
    for order, i in enumerate(indices):
        panel = Image.new("RGB", (460, 580), "#09121f")
        draw = ImageDraw.Draw(panel)
        draw.text((20, 16), "Loop-Grenze in Zeitlupe", font=font(24), fill="#e4eefb")
        label = f"Frame {i+1:02d}/{len(frames):02d}"
        if order == 2:
            label += "  ← LOOP"
        draw.text((20, 55), label, font=font(23), fill="#ffb08c" if order == 2 else "#a4c7ee")
        panel.paste(render_stage(frames[i], geometry), (20, 100))
        if order == 2:
            draw.rectangle((19, 99, 440, 520), outline="#ff996c", width=3)
        draw.text((20, 538), f"{slow_factor:g}× langsamer · Fluss {percentage(report['seam_score'])}",
                  font=font(17), fill="#b0bfd4")
        images.append(panel)
        durations.append(max(20, int(round(report["durations_ms"][i]*slow_factor/10))*10))
    separator = Image.new("RGB", (460, 580), "#182130")
    draw = ImageDraw.Draw(separator)
    for y, line in zip((190, 235, 280, 325), ("Diagnose-Ausschnitt", "startet erneut", "Kein Animationsframe", "Kein echter Übergang 2 → N-1")):
        draw.text((24, y), line, font=font(21 if y < 280 else 17), fill="#bac9dd")
    images.append(separator)
    durations.append(700)
    atlas = Image.new("RGB", (460*len(images), 580))
    for i, panel in enumerate(images):
        atlas.paste(panel, (i*460, 0))
    palette = atlas.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    indexed = [panel.quantize(palette=palette, dither=Image.Dither.NONE) for panel in images]
    indexed[0].save(output, save_all=True, append_images=indexed[1:], duration=durations,
                    disposal=2, loop=0, optimize=False)
    return {"frame_indices_1_based": [i+1 for i in indices],
            "durations_ms": durations, "separator_frame": True, "slow_factor": slow_factor}

def create_overlay(frames, report, output):
    edge = 350
    geometry = display_geometry(frames, edge)
    box, size, offset, scale = geometry
    names = [name for name, r in report["regions"].items() if name != "full" and r["valid"]]
    image = Image.new("RGB", (1120, max(585, 510+28*len(names))), "#09121f")
    draw = ImageDraw.Draw(image)
    draw.text((20, 16), f"Loop {len(frames):02d} → 01 · Position, Kontur und lokale Verschiebung",
              font=font(23), fill="#e6eef9")
    stages = [render_stage(frames[-1], geometry, edge), render_stage(frames[0], geometry, edge)]
    onion = checker((edge, edge)).convert("RGBA")
    for frame, color in ((frames[-1], (62, 222, 245)), (frames[0], (248, 96, 205))):
        mask = frame.crop(box).getchannel("A").resize(size, Image.Resampling.LANCZOS)
        tint = Image.new("RGBA", size, (*color, 0))
        tint.putalpha(mask.point(lambda a: round(a*.56)))
        onion.alpha_composite(tint, offset)
    stages.append(onion.convert("RGB"))
    origins = [(20, 105), (385, 105), (750, 105)]
    for stage, origin, title in zip(stages, origins, (f"Frame {len(frames)}", "Frame 1", "Cyan: Ende · Magenta: Anfang")):
        draw.text((origin[0], 70), title, font=font(18), fill="#aac4e5")
        image.paste(stage, origin)
    def point(center, origin):
        return (origin[0]+offset[0]+(center[0]-box[0])*scale,
                origin[1]+offset[1]+(center[1]-box[1])*scale)
    for name in names:
        region = report["regions"][name]
        if not region["valid"]:
            continue
        color = "#ffac70" if region["continuity_score"] < GOOD else "#b1f5bb"
        arrow(draw, point(region["centers"][-1], origins[2]), point(region["centers"][0], origins[2]), color)
        if region["continuity_score"] < GOOD:
            for origin in origins:
                y0 = origin[1]+offset[1]+(region["y0"]-box[1])*scale
                y1 = origin[1]+offset[1]+(region["y1"]-box[1])*scale
                x0 = origin[0]+offset[0]+(region["x0"]-box[0])*scale
                x1 = origin[0]+offset[0]+(region["x1"]-box[0])*scale
                draw.rectangle((x0, y0, x1, y1), outline=color, width=2)
    for j, name in enumerate(names):
        region = report["regions"][name]
        if region["valid"]:
            a, b = region["centers"][-1], region["centers"][0]
            message = f"{region_label(report, name)}: Δx {b[0]-a[0]:+.1f}px · Δy {b[1]-a[1]:+.1f}px"
            draw.text((20, 472+j*28), message, font=font(17), fill="#bfd0e4")
    draw.text((650, 487), "Pfeile = Bereichsschwerpunkte.", font=font(17), fill="#bfd0e4")
    draw.text((650, 519), "Orange = auffälliges Grenzfenster.", font=font(17), fill="#ffac70")
    image.save(output)

def create_chart(report, output):
    image = Image.new("RGB", (1180, 875), "#09121f")
    draw = ImageDraw.Draw(image)
    draw.text((24, 18), "Alle Übergänge · orange markiert: letzter → erster Frame", font=font(24), fill="#e5eefa")
    pairs = report["pair_metrics"]
    n = len(pairs)
    left, right = 82, 1140
    step = (right-left)/n
    xs = [left+(i+.5)*step for i in range(n)]
    jitter_values = np.max([r["jitter"]["ratios"] for r in report["regions"].values() if r["valid"]] or [[0.]*n], axis=0).tolist()
    for top, bottom, label, values, maximum, color in (
        (105, 280, "Schwerpunktversatz pro Übergang [px]", [p["shift_magnitude"] for p in pairs],
         max(2., max(p["shift_magnitude"] for p in pairs)*1.15), "#7ed4f3"),
        (355, 540, "Zeitliche Flusswertung [%] · Poseänderungen sind erlaubt",
         [p["temporal_score"]*100 if p["temporal_score"] is not None else None for p in pairs], 100., "#a0edb0"),
        (610, 770, "Kurzer Rückschritt [× Rauschgrenze] · >1: Zitterverdacht",
         jitter_values, max(2., max(jitter_values)*1.15), "#e6a0e9"),
    ):
        draw.text((24, top-35), label, font=font(19), fill="#bfd0e4")
        draw.rectangle((left+(n-1)*step, top, right, bottom), fill="#392720")
        for tick in range(5):
            y = bottom-(bottom-top)*tick/4
            draw.line((left, y, right, y), fill="#2a3c53")
            draw.text((18, y-9), f"{maximum*tick/4:.1f}", font=font(14), fill="#91a7c2")
        points = [(x, bottom-v/maximum*(bottom-top)) for x, v in zip(xs, values) if v is not None]
        if len(points) > 1:
            draw.line(points, fill=color, width=3)
        if not points:
            draw.text((left+20, top+70), "Keine zeitliche Bewertung: statisch oder nicht messbar.", font=font(22), fill="#b8c5d8")
        for i, (x, y) in enumerate(points):
            draw.ellipse((x-4, y-4, x+4, y+4), fill="#ffae75" if i == n-1 else color)
        if top == 355:
            y = bottom-GOOD*(bottom-top)
            for x in range(left, right, 14):
                draw.line((x, y, min(x+7, right), y), fill="#a59965")
        if top == 610:
            y = bottom-(bottom-top)/maximum
            draw.line((left, y, right, y), fill="#a59965")
    for i, p in enumerate(pairs):
        draw.multiline_text((xs[i]-17, 784), f"{p['a']:02d}\n→{p['b']:02d}", font=font(13),
                            fill="#ffae75" if i == n-1 else "#aabdd5", spacing=2)
    draw.text((24, 842), "Loop-Fluss: N-1→N→1→2. Bewegungsruhe: kurze Rückschritte im ganzen Loop, natürliche Umkehrpunkte bleiben erlaubt.",
              font=font(15), fill="#9db2cb")
    image.save(output)

def create_detail_overlay(frames, report, output):
    details = report["details"]
    finding = details["findings"][0] if details["findings"] else None
    window = (finding if finding else max(details["windows"], key=lambda w: max(w["ratios"]), default=None))
    spec = next(iter(details["regions"].values()))
    box = window["box"] if window else spec["box"]
    indices = finding["support_frames"] if finding else report["seam_window"]
    edge, geometry = 420, display_geometry(frames)
    canvas = Image.new("RGB", (1180, 655), "#09121f")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 16), "Lokale Details · "+percentage(report["detail_score"]), font=font(24), fill="#e4eefb")
    draw.text((20, 53), "Orange: auffälliges Fenster" if finding else "Geprüftes Fenster · kein lokaler Befund" if window else details["status"],
              font=font(18), fill="#ffaf7d" if finding else "#a7dabc")
    frame = frames[indices[1]-1]
    canvas.paste(render_stage(frame, geometry), (20, 125))
    common, _, offset, scale = geometry
    def rect(coords):
        x0, y0, x1, y1 = coords
        return (20+offset[0]+(x0-common[0])*scale, 125+offset[1]+(y0-common[1])*scale,
                20+offset[0]+(x1-common[0])*scale, 125+offset[1]+(y1-common[1])*scale)
    for region in details["regions"].values():
        draw.rectangle(rect(region["box"]), outline="#75bce6", width=2)
    color = "#ffae75" if finding else "#a0edb0"
    draw.rectangle(rect(box), outline=color, width=3)
    context = (max(0, box[0]-24), max(0, box[1]-24), min(frames[0].width, box[2]+24), min(frames[0].height, box[3]+24))
    zoom = min(195/max(1, context[2]-context[0]), 195/max(1, context[3]-context[1]))
    size = (max(1, round((context[2]-context[0])*zoom)), max(1, round((context[3]-context[1])*zoom)))
    for k, index in enumerate(indices):
        x, y = 495+(k % 2)*310, 122+(k//2)*250
        draw.text((x, y-30), f"Frame {index} / {len(frames)}", font=font(19), fill="#bfd0e4")
        panel = checker(size).convert("RGBA")
        panel.alpha_composite(frames[index-1].crop(context).resize(size, Image.Resampling.NEAREST))
        canvas.paste(panel.convert("RGB"), (x, y))
        draw.rectangle((x+(box[0]-context[0])*zoom, y+(box[1]-context[1])*zoom,
                        x+(box[2]-context[0])*zoom, y+(box[3]-context[1])*zoom), outline=color, width=2)
    label = finding["label"] if finding else spec["label"]
    draw.text((20, 572), label, font=font(20), fill="#a4c7ee")
    draw.text((20, 608), "Fenster "+" → ".join(map(str, indices))+" · Ein Befund betrifft diese Bildgruppe, nicht zwingend nur einen Übergang.",
              font=font(16), fill="#aabbd1")
    canvas.save(output)

def score_html(label, value):
    color = "#8492a8" if value is None else "#80d5a2" if value >= GOOD else "#f3bf68" if value >= NOTICE else "#f38b85"
    width = 0 if value is None else max(0, min(100, value*100))
    return (f'<div class="score"><span>{html.escape(label)}</span><b>{percentage(value)}</b>'
            f'<div class="track"><div style="width:{width:.2f}%;background:{color}"></div></div></div>')

def loop_preview_html(frames, durations):
    encoded = []
    for frame in frames:
        stream = io.BytesIO()
        frame.save(stream, format="PNG")
        encoded.append("data:image/png;base64,"+base64.b64encode(stream.getvalue()).decode("ascii"))
    data = json.dumps({"images": encoded, "durations": durations}, separators=(",", ":"))
    return (f'<canvas id="loop" width="{frames[0].width}" height="{frames[0].height}" aria-label="Vollständige Animation"></canvas>'
            '<div><button id="play">Pause</button><label>Tempo <select id="speed"><option value="1">Originaltempo</option><option value="0.5">½ Tempo</option><option value="0.25">¼ Tempo</option></select></label>'
            f'<label>Frame <input id="seek" type="range" min="0" max="{len(frames)-1}" value="0"></label><output id="position"></output></div>'
            '<p>Verlustfreie PNG-Frames, feste Position und angegebene Framezeiten. Der Regler pausiert die Wiedergabe.</p>'
            '<script>const animationData='+data+';</script>'+"""<script>
(()=>{const d=animationData, canvas=document.getElementById('loop'),ctx=canvas.getContext('2d');
const play=document.getElementById('play'),seek=document.getElementById('seek'),speed=document.getElementById('speed'),position=document.getElementById('position');
const starts=[];let total=0;d.durations.forEach(t=>{starts.push(total);total+=t});
let running=!matchMedia('(prefers-reduced-motion: reduce)').matches,phase=0,last=performance.now(),rate=1,current=-1;
play.textContent=running?'Pause':'Abspielen';
Promise.all(d.images.map(src=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=reject;im.src=src}))).then(images=>{
function draw(){let i=starts.findIndex((t,j)=>phase<t+d.durations[j]);if(i<0)i=0;if(i!==current){ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(images[i],0,0);seek.value=i;position.textContent=`${i+1} / ${images.length} · ${d.durations[i]} ms`;current=i}}
function tick(now){if(running)phase=(phase+(now-last)*rate)%total;last=now;draw();requestAnimationFrame(tick)}
play.onclick=()=>{running=!running;last=performance.now();play.textContent=running?'Pause':'Abspielen'};
seek.oninput=()=>{running=false;play.textContent='Abspielen';phase=starts[Number(seek.value)];draw()};
speed.onchange=()=>{rate=Number(speed.value);last=performance.now()};requestAnimationFrame(tick);
}).catch(()=>{position.textContent='Vorschaubilder konnten nicht geladen werden.'});})();
</script>""")

def write_reports(path, frames, report, out_dir, slow_factor):
    if report.get("test", "all") != "all":
        return write_selected_reports(path, frames, report, out_dir, slow_factor)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = path.stem+"_animtest"
    names = {"json": stem+".json", "markdown": stem+".md", "html": stem+".html",
             "slow_gif": stem+"_loop_slow.gif", "overlay": stem+"_overlay.png", "chart": stem+"_transitions.png"}
    preview = create_slow_gif(frames, report, out_dir/names["slow_gif"], slow_factor)
    create_overlay(frames, report, out_dir/names["overlay"])
    create_chart(report, out_dir/names["chart"])
    if report["details"]["configured"]:
        names["details"] = stem+"_details.png"
        create_detail_overlay(frames, report, out_dir/names["details"])
    report["artifacts"] = names
    report["preview"] = preview
    (out_dir/names["json"]).write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    lines = [f"# Loopprüfung – {path.name}", "",
             f"- Gesamt: {percentage(report['overall_score'])} / {rating(report['overall_score'])}",
             f"- Loop-Bild N→1: {percentage(report['loop_score'])} (Bildähnlichkeit, nicht Bewegungsqualität)",
             f"- Loop-Fluss N-1→N→1→2: {percentage(report['seam_score'])} / {rating(report['seam_score'])}",
             f"- Bewegungsruhe im gesamten Loop: {percentage(report['calmness_score'])} / {rating(report['calmness_score'])}",
             f"- Bewegungsruhe ohne Grenzfenster: {percentage(report['interior_calmness_score'])}",
             f"- Lokale Details: {percentage(report['detail_score'])}; {report['details']['status']}.",
             f"- Raster: {report['grid']['cols']}×{report['grid']['rows']}, {len(frames)} Frames.",
             f"- Bewertbarkeit: {report['confidence']}. Zeiten: {report['durations_ms']} ms.",
             f"- Alte Formel zum Vergleich: Gesamt {percentage(report['legacy_overall_score'])}, Loop {percentage(report['legacy_loop_score'])}.",
             "", f"[Browserbericht]({quote(names['html'])}) · [JSON]({quote(names['json'])})", "",
             f"![Loop-Zeitlupe]({quote(names['slow_gif'])})", "",
             "Die graue Karte trennt Wiederholungen des Diagnose-Ausschnitts; sie gehört nicht zur Animation.", "",
             f"![Überlagerung]({quote(names['overlay'])})", "", f"![Übergänge]({quote(names['chart'])})", "",
             "## Hinweise", ""]
    lines += ["- "+warning for warning in report["warnings"]]
    lines += ["- Geometrische Heuristik, keine Anatomie-Erkennung. Eine gute Zahl ersetzt keine visuelle Abnahme.",
              "- 35% Loop-Fluss, 35% Bildfolge, 30% Bewegungsruhe. Schlechte Naht oder Bewegungsruhe begrenzen die Gesamtnote.",
              "- Bei konfigurierten Detailbereichen kann die Gesamtnote die Detailwertung nicht überschreiten.",
              "- Bewegungsruhe erkennt kurze Gegenschritte zwischen gleichgerichteten Nachbarn. 100% bedeutet: kein solches Muster oberhalb der Rauschgrenze gefunden; andere Zitterarten sind möglich.",
              "- Lokale Fehler vergleichen die Bewegung mit den benachbarten Schritten und einer robusten Binnenreferenz.",
              "- Ein Fehlervektor ist keine ungeprüfte Verschiebe-Anweisung an PyImgAnimFix.", "",
              "## Übergänge", "", "| Übergang | Bild | Fluss | Δx | Δy | Schwerpunkt |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for p in report["pair_metrics"]:
        lines.append(f"| {p['a']:02d}→{p['b']:02d} | {p['score']*100:.1f}% | {percentage(p['temporal_score'])} | {p['dx']:+.2f}px | {p['dy']:+.2f}px | {p['shift_magnitude']:.2f}px |")
    lines += ["", "## Stärkste Auffälligkeiten am Übergang", ""]
    for item in report["boundary_findings"][:6]:
        lines.append(f"- {region_label(report, item['region'])} / {METRIC_LABELS[item['metric']]}, {item['transition'][0]}→{item['transition'][1]}: "
                     f"{item['value']:.2f} bei Referenzgrenze {item['reference_limit']:.2f} ({item['severity']:.2f}×).")
    lines += ["", "## Zitterverdacht – kurze Rückschritte", ""]
    for item in report["jitter_findings"]:
        lines.append(f"- {region_label(report, item['region'])}, {item['transition'][0]}→{item['transition'][1]} ({item['location']}): {item['value']:.2f}px / Grenze {item['reference_limit']:.2f}px ({item['severity']:.2f}×).")
    lines += ["", "## Lokale Details", "", "Status: "+report["details"]["status"]+".", "",
              "Kleine überlappende Fenster prüfen Falten-/Texturänderung und Alpha-Konturen getrennt. Die Referenz enthält alle übrigen Übergänge außer dem geprüften Schritt und seinen direkten Nachbarn. Bereits beobachtete natürliche Detailmuster erhöhen die Referenzgrenze.", "",
              "Nur die ausdrücklich konfigurierten Bereiche werden untersucht. Wiederholte gleichförmige Fehler können unerkannt bleiben. Dies ist keine Materialverfolgung; ein Befund ist ein Hinweis für die Sichtprüfung.", ""]
    if "details" in names:
        lines += [f"![Lokale Detailprüfung]({quote(names['details'])})", ""]
    for item in report["details"]["findings"][:12]:
        lines.append(f"- {item['label']} / {DETAIL_LABELS[item['metric']]}, Fenster {'→'.join(map(str, item['support_frames']))}, Rechteck {item['box']}: {item['severity']:.2f}× Referenzgrenze ({item['location']}).")
    (out_dir/names["markdown"]).write_text("\n".join(lines)+"\n", encoding="utf-8")
    scores = "".join(score_html(label, report[key]) for label, key in SCORES)
    warnings = "".join("<li>"+html.escape(w)+"</li>" for w in report["warnings"])
    title = html.escape(path.name)
    findings = "".join(f"<li>{html.escape(region_label(report, item['region']))}: kurzer Rückschritt {item['transition'][0]}→{item['transition'][1]}, {item['value']:.2f}px ({item['location']}).</li>" for item in report["jitter_findings"][:8])
    detail_findings = "".join(f"<li>{html.escape(item['label'])}: {DETAIL_LABELS[item['metric']]}, Fenster {' → '.join(map(str, item['support_frames']))}, {item['severity']:.2f}× Referenzgrenze.</li>" for item in report["details"]["findings"][:8])
    detail_html = f'<h2>Lokale Details</h2><p>{html.escape(report["details"]["status"])}. Die Detailwertung gilt für die ausgewählten Bereiche.</p><ul class="warning">{detail_findings}</ul>'
    if "details" in names:
        detail_html += f'<img src="{quote(names["details"])}" alt="Markierte Messbereiche und vier vergrößerte Detailbilder">'
    text = f"""<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Loopprüfung · {title}</title><style>{STYLE}</style><body>
<p>PyImgTestAnim {VERSION} · <a href="animtest_index.html">Übersicht</a></p><h1>{title}</h1>
<div class="scores">{scores}</div>
<p>Loop-Bild misst Ähnlichkeit. Loop-Fluss prüft die Bewegungsfortsetzung rund um die Naht, nicht identische End-/Startposen.
Bewegungsruhe sucht kurze Rückschritte im gesamten Loop. Details prüfen kleine Bildfenster in ausgewählten Bereichen und begrenzen ebenfalls die Gesamtnote.</p>
<p>Raster {report['grid']['cols']}×{report['grid']['rows']} · {len(frames)} Frames · {report['duration_ms']:g} ms · Bewertbarkeit: {html.escape(report['confidence'])}</p>
<ul class="warning">{warnings}</ul>
<h2>Vollständiger Loop</h2>{loop_preview_html(frames, report['durations_ms'])}
<ul class="warning">{findings}</ul>
{detail_html}
<h2>1 · Letzte zwei → erste zwei Frames</h2>
<p>{' → '.join(map(str, report['seam_window']))}, {slow_factor:g}× langsamer. Die graue Karte kennzeichnet nur den Neustart des Diagnose-Ausschnitts.</p>
<img class="gif" src="{quote(names['slow_gif'])}" alt="Beschriftete Loop-Zeitlupe">
<p>Bei reduzierter Bewegung ausgeblendet. <a href="{quote(names['slow_gif'])}">GIF gezielt öffnen</a>.</p>
<h2>2 · Überlagerung und Verschiebungen</h2><img src="{quote(names['overlay'])}" alt="Ende und Anfang, farbige Überlagerung mit Schwerpunktpfeilen">
<h2>3 · Alle Übergänge im Vergleich</h2><img src="{quote(names['chart'])}" alt="Schwerpunktversatz und Flusswertung; Loopübergang orange">
<p><a href="{quote(names['markdown'])}">Messwerte und Hinweise</a> · <a href="{quote(names['json'])}">JSON</a></p>
<p>Heuristische Geometrieprüfung, keine Garantie für anatomisch oder künstlerisch natürliche Bewegung. Originalbilder bleiben unverändert.</p></body></html>"""
    (out_dir/names["html"]).write_text(text, encoding="utf-8")

def write_index(reports, out_dir):
    cards = []
    for r in reports:
        scores = "".join(score_html(label, r[key]) for label, key in report_scores(r))
        links = " · ".join(f'<a href="{quote(r["artifacts"][key])}">{label}</a>' for key, label in
                           (("slow_gif", "Zeitlupe"), ("overlay", "Überlagerung"), ("chart", "Diagramm")) if key in r["artifacts"])
        cards.append(f'<article class="card"><h2><a href="{quote(r["artifacts"]["html"])}">{html.escape(r["source"])}</a></h2>'
                     f'<div class="scores">{scores}</div><p>{html.escape(r["confidence"])} · '
                     f'{links}</p></article>')
    page = f'<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Loopprüfung · Übersicht</title><style>{STYLE}</style><body><h1>Animationen · Loopprüfung {VERSION}</h1><p>Bildähnlichkeit, Naht und Bewegungsruhe werden getrennt geprüft. Die Gesamtnote berücksichtigt alle drei.</p>{"".join(cards)}</body></html>'
    test = reports[0].get("test", "all") if reports else "all"
    if test != "all":
        page = page.replace("Bildähnlichkeit, Naht und Bewegungsruhe werden getrennt geprüft. Die Gesamtnote berücksichtigt alle drei.",
                            "Einzelprüfung: "+CHECKS[test][0]+". Die Übersicht zeigt nur diese Wertung.")
    (out_dir/index_name(test)).write_text(page, encoding="utf-8")

def invalid_report(path, reason, out_dir, test="all"):
    report = {"schema_version": 4, "tool_version": VERSION, "source": path.name,
              "test": test, "tests_run": [],
              "valid": False, "confidence": "Eingabe ungültig", "warnings": [reason],
              **{key: None for _, key in (SCORES if test == "all" else (CHECKS[test][:2],))}}
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = artifact_stem(path, test)
        report["artifacts"] = {"json": stem+".json", "markdown": stem+".md", "html": stem+".html"}
        (out_dir/(stem+".json")).write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (out_dir/(stem+".md")).write_text(f"# Keine Bewertung – {path.name}\n\n{reason}\n", encoding="utf-8")
        (out_dir/(stem+".html")).write_text(f'<!doctype html><html lang="de"><meta charset="utf-8"><title>Keine Bewertung</title><style>{STYLE}</style><body><h1>{html.escape(path.name)}</h1><p>Keine Bewertung: {html.escape(reason)}</p><a href="{index_name(test)}">Übersicht</a></body></html>', encoding="utf-8")
    return report

def measurement_table(report):
    test = report["test"]
    if test in {"loop-image", "loop-flow"}:
        key = "score" if test == "loop-image" else "temporal_score"
        return ["Übergang", CHECKS[test][0], "Δx", "Δy"], [
            [f"{p['a']}→{p['b']}", percentage(p[key]), f"{p['dx']:+.2f}px", f"{p['dy']:+.2f}px"]
            for p in report["pair_metrics"]]
    if test == "calmness":
        rows = []
        for region in report["regions"].values():
            if region["valid"]:
                jitter = region["jitter"]
                rows.extend([region["label"], f"{i+1}→{(i+1) % report['frames']+1}",
                             f"{value:.2f}px", f"{jitter['ratios'][i]:.2f}×"]
                            for i, value in enumerate(jitter["backstep_px"]))
        return ["Bereich", "Übergang", "Kurzer Rückschritt", "Rauschgrenze"], rows
    return ["Bereich", "Framefenster", "Prüfung", "Referenzgrenze"], [
        [item["label"], " → ".join(map(str, item["support_frames"])),
         DETAIL_LABELS[item["metric"]], f"{item['severity']:.2f}×"]
        for item in report["details"]["findings"][:12]]

def write_selected_reports(path, frames, report, out_dir, slow_factor):
    out_dir.mkdir(parents=True, exist_ok=True)
    test = report["test"]
    label, key, _ = CHECKS[test]
    stem = artifact_stem(path, test)
    names = {kind: stem+extension for kind, extension in (
        ("json", ".json"), ("markdown", ".md"), ("html", ".html"))}
    if test in {"loop-image", "loop-flow"}:
        names["overlay"] = stem+"_overlay.png"
        overlay_report = report if test == "loop-flow" else report | {"regions": {}}
        create_overlay(frames, overlay_report, out_dir/names["overlay"])
    if test == "loop-flow":
        names["slow_gif"] = stem+"_loop_slow.gif"
        report["preview"] = create_slow_gif(frames, report, out_dir/names["slow_gif"], slow_factor)
    if test == "details" and report["details"]["configured"]:
        names["details"] = stem+"_details.png"
        create_detail_overlay(frames, report, out_dir/names["details"])
    report["artifacts"] = names
    (out_dir/names["json"]).write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    descriptions = {
        "loop-image": "Bildähnlichkeit zwischen letztem und erstem Frame; keine zeitliche Bewegungswertung.",
        "loop-flow": "Bewegungs- und Bildfortsetzung rund um das Grenzfenster N-1 → N → 1 → 2.",
        "calmness": "Kurze Rückschritte im gesamten Loop. Die Messung erfasst nicht jede mögliche Zitterart.",
        "details": "Textur- und Konturfortsetzung in den ausdrücklich ausgewählten Detailbereichen."}
    notes = [descriptions[test], *report["warnings"]]
    if test == "details":
        notes.append("Detailprüfung: "+report["details"]["status"]+".")
    if test == "calmness":
        notes.append("Bewegungsruhe ohne Grenzfenster: "+percentage(report["interior_calmness_score"])+".")
    for item in report.get("boundary_findings", []):
        notes.append(f"{region_label(report, item['region'])}: {METRIC_LABELS[item['metric']]} bei "
                     f"{item['transition'][0]}→{item['transition'][1]}, {item['severity']:.2f}× Referenzgrenze.")
    headers, rows = measurement_table(report)
    metadata = (f"Raster {report['grid']['cols']}×{report['grid']['rows']} · {len(frames)} Frames · "
                f"{report['duration_ms']:g} ms · Bewertbarkeit: {report['confidence']}")
    figures = [(kind, title) for kind, title in (
        ("overlay", "Überlagerung"), ("slow_gif", "Loop-Zeitlupe"), ("details", "Lokale Details")) if kind in names]
    lines = [f"# {label} – {path.name}", "", f"- {label}: {percentage(report[key])} / {rating(report[key])}",
             "- "+metadata, "", f"[Browserbericht]({quote(names['html'])}) · [JSON]({quote(names['json'])})", ""]
    lines += ["- "+note for note in notes]
    lines += ["", "## Messwerte", "", "| "+" | ".join(headers)+" |", "| "+" | ".join(["---"]*len(headers))+" |"]
    lines += ["| "+" | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in row)+" |" for row in rows]
    for kind, title in figures:
        lines += ["", f"![{title}]({quote(names[kind])})"]
    (out_dir/names["markdown"]).write_text("\n".join(lines)+"\n", encoding="utf-8")
    table = "<table><thead><tr>"+"".join("<th>"+html.escape(cell)+"</th>" for cell in headers)+"</tr></thead><tbody>"
    table += "".join("<tr>"+"".join("<td>"+html.escape(str(cell))+"</td>" for cell in row)+"</tr>" for row in rows)+"</tbody></table>"
    images = "".join(f'<h2>{title}</h2><img src="{quote(names[kind])}" alt="{title}"'+
                     (' class="gif"' if kind == "slow_gif" else '')+'>' for kind, title in figures)
    note_html = "".join("<li>"+html.escape(note)+"</li>" for note in notes)
    page = f'''<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{label} · {html.escape(path.name)}</title><style>{STYLE}</style><body>
<p>PyImgAnimTest {VERSION} · <a href="{index_name(test)}">Übersicht</a></p>
<h1>{label} · {html.escape(path.name)}</h1><div class="scores">{score_html(label, report[key])}</div>
<p>{html.escape(metadata)}</p><ul class="warning">{note_html}</ul>
<h2>Vollständiger Loop</h2>{loop_preview_html(frames, report['durations_ms'])}
<h2>Messwerte</h2>{table}{images}
<p><a href="{quote(names['markdown'])}">Messwerte und Hinweise</a> · <a href="{quote(names['json'])}">JSON</a></p></body></html>'''
    (out_dir/names["html"]).write_text(page, encoding="utf-8")

def parse_args(argv=None, test=None):
    description = ("PyImgAnimTest – PNG-Spritesheets prüfen.\n"
                   "TestAll: Loop-Bild → Loop-Fluss → Bewegungsruhe → Details.\n"
                   "Beispiel: python3 PyImgAnimTestAll.py -f 16 --grid 4x4 bild.png")
    if test is not None and test != "all":
        description = "PyImgAnimTest – Einzelprüfung: "+CHECKS[test][0]
    p = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    if test is None:
        p.add_argument("--test", choices=("all", *CHECKS), default="all",
                       help="Nur diese Prüfung ausführen; Standard: all")
    else:
        p.set_defaults(test=test)
    p.add_argument("files", nargs="*", type=Path, help="Optional einzelne PNGs; sonst alle PNGs im Arbeitsordner")
    p.add_argument("-f", "--frame", type=int, help="Tatsächliche Framezahl, 3 bis 24; sonst aus Raster/Metadaten/Dateinamen")
    p.add_argument("--grid", default="auto", help="auto, horizontal, vertical oder explizit z.B. 4x4 / 3x4")
    p.add_argument("--alpha-threshold", type=int, default=8)
    p.add_argument("--fps", type=float, help="Wiedergabe-FPS; ohne Zeitangabe werden 8 angenommen")
    p.add_argument("--durations", help="Alternativ individuelle Framezeiten in ms, kommagetrennt")
    p.add_argument("--metadata", type=Path, help="Animations-Metadaten; sonst automatisch <Dateistamm>.anim.json")
    p.add_argument("--regions", type=Path, help="Benannte Messbereiche und optionale detail_regions als JSON, relativ zum gemeinsamen Motiv-Rechteck")
    p.add_argument("--trust-grid", action="store_true", help="Explizites Raster trotz widersprechendem Dateinamen/Unterteilungsverdacht verwenden")
    p.add_argument("--slow-factor", type=float, default=4., help="Zeitlupe relativ zur Wiedergabe, Standard 4")
    p.add_argument("--output-dir", type=Path, help="Anderer Reportordner; Standard .compare im Arbeitsordner")
    p.add_argument("--no-report", action="store_true", help="Keine Dateien/Ordner schreiben")
    p.add_argument("--include-fixed", action="store_true", help="Auch *_loopfix.png prüfen")
    p.add_argument("--fail-below", type=float, help="Exit 3 unter Grenzwert (0..100) oder nicht bewertbar: bei Einzeltests nur deren Wertung; bei all Gesamt, Loop-Fluss, Bewegungsruhe und konfigurierte Details")
    p.add_argument("--version", action="version", version=VERSION)
    return p.parse_args(argv)

def quality_failed(report, threshold):
    if report.get("test", "all") != "all":
        value = report.get(CHECKS[report["test"]][1])
        return not report["valid"] or value is None or value*100 < threshold
    values = [report.get(key) for key in ("overall_score", "seam_score", "calmness_score")]
    if report.get("details", {}).get("configured"):
        values.append(report.get("detail_score"))
    return not report["valid"] or any(v is None for v in values) or min(values)*100 < threshold

def run_args(args, reports):
    try:
        files = args.files or sorted(Path.cwd().glob("*.png"))
        if not args.include_fixed:
            files = [p for p in files if not p.stem.endswith("_loopfix")]
        if not files:
            raise ValueError("Keine PNG-Dateien ausgewählt.")
        if not args.no_report and len({p.stem for p in files}) != len(files):
            raise ValueError("Gleiche Dateistämme aus mehreren Ordnern: getrennte Läufe verwenden, sonst kollidieren Reports.")
        if args.metadata and len(files) != 1:
            raise ValueError("--metadata gehört zu genau einer PNG-Datei; für mehrere Dateien .anim.json verwenden.")
        print(f"PyImgTestAnim {VERSION} | {len(files)} PNGs | Raster und Zeiten werden je Datei geprüft")
        selected = CHECKS if args.test == "all" else (args.test,)
        print("Prüfungen: "+" → ".join(CHECKS[name][0] for name in selected))
        ok = sum(analyze(path, args, reports) for path in files)
        if not args.no_report and reports:
            out_dir = args.output_dir if args.output_dir is not None else Path.cwd()/".compare"
            write_index(reports, out_dir)
            print(f"\nVorschau: {out_dir/index_name(args.test)}")
        print(f"Fertig: {ok}/{len(files)} Dateien analysiert; Originale unverändert.")
        if ok != len(files):
            return 2
        if args.fail_below is not None and any(quality_failed(r, args.fail_below) for r in reports):
            return 3
        return 0
    except (OSError, ValueError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2

def combine_reports(results):
    """Bereits ausgeführte Einzelprüfungen mit der bisherigen Gesamtformel verbinden."""
    image, flow, motion = (results[name] for name in ("loop-image", "loop-flow", "calmness"))
    durations, regions_profile = image["durations_ms"], image["regions_profile"]
    frame_size, n = image["frame_size"], image["frames"]
    fm = [FrameMetrics(**item) for item in image["frames_metrics"]]
    pm = [PairMetrics(**{field.name: item[field.name] for field in fields(PairMetrics)})
          for item in image["pair_metrics"]]
    regions = flow["regions"]
    for name, region in regions.items():
        if region["valid"]:
            region["jitter"] = motion["regions"][name]["jitter"]
    details = results["details"]["details"]
    outliers = [item["motion_outlier_z"] for item in image["pair_metrics"]]
    refs, focus = reference_indices(n), [(n-2) % n, n-1, 0]
    appearance = [item["appearance_change"] for item in flow["pair_metrics"]]
    visual_values = {key: channel["values"] for key, channel in flow["visual_channels"].items()}
    visual_limits = {key: channel["limit"] for key, channel in flow["visual_channels"].items()}
    visual_ratios = {key: channel["ratios"] for key, channel in flow["visual_channels"].items()}
    temporal, sequence, seam = (flow["_aggregate"][key] for key in ("temporal", "sequence_score", "seam_score"))
    regional = [r["transition_scores"] for r in regions.values() if r["valid"]]
    calmness, interior_calmness = motion["calmness_score"], motion["interior_calmness_score"]
    suspect, boundary_findings = flow["suspected_region"], flow["boundary_findings"]
    jitter_findings = motion["jitter_findings"]
    overall = .35*sequence+.35*seam+.30*(calmness if calmness is not None else seam)
    if details["score"] is not None:
        # Lokale Auffälligkeiten dürfen nicht in der großen Figur verschwinden.
        overall = min(overall, details["score"])
    for component in (seam, calmness):
        if component is not None and component < GOOD:
            overall = min(overall, GOOD-.001)
        if component is not None and component < NOTICE:
            overall = min(overall, NOTICE-.001)
    if min(temporal) < .35:
        overall = min(overall, GOOD-.001)
    invalid = [f.index for f in fm if not f.visible_pixels]
    static = all(p.silhouette_iou == 1 and p.alpha_similarity == 1 and p.rgb_similarity == 1 for p in pm)
    warnings = []
    confidence = "normal"
    if invalid:
        warnings.append("Leere/nicht messbare Frames: "+", ".join(map(str, invalid))+". Framezahl/Raster oder Loop-Eignung prüfen.")
        overall = seam = 0.
        sequence = 0.
        confidence = "ungültig"
        calmness = interior_calmness = None
        details["score"] = None
        details["status"] = "ungültige Bildfolge"
    elif not regional:
        warnings.append("Zu wenig sichtbare Pixel für eine zeitliche Geometrieprüfung.")
        overall = seam = None
        sequence = None
        confidence = "nicht messbar"
        calmness = interior_calmness = None
    elif static:
        warnings.append("Statische Bildfolge: keine Bewegung messbar; Bildidentität beweist keine flüssige Animation.")
        overall = seam = None
        sequence = None
        confidence = "statisch"
        calmness = interior_calmness = None
        details["score"] = None
        details["status"] = "statische Bildfolge"
    elif n < 6:
        warnings.append("Weniger als sechs Frames: sehr kleine Bewegungsreferenz; visuelle Abnahme erforderlich.")
        confidence = "niedrig"
        overall, seam = min(overall, .89), min(seam, .89)
    if details["configured"] and details["score"] is None:
        warnings.append("Lokale Detailprüfung: "+details["status"]+".")
    if pm[-1].silhouette_iou == 1 and pm[-1].alpha_similarity == 1 and pm[-1].rgb_similarity == 1 and not static:
        warnings.append("Letzter und erster Frame sind identisch. Bei normalem Abspielen kann das eine Doppelbildpause erzeugen.")
    if fm and any(f.bbox[0] == 0 or f.bbox[1] == 0 or f.bbox[2] == frame_size[0] or f.bbox[3] == frame_size[1]
                  for f in fm if f.visible_pixels):
        warnings.append("Motiv berührt einen Zellrand; möglichen Beschnitt visuell prüfen.")
    report = {
        "schema_version": 4, "tool_version": VERSION, "frames": n,
        "test": "all", "tests_run": list(CHECKS),
        "overall_score": overall, "loop_score": image["loop_score"],
        "seam_score": seam, "sequence_score": sequence,
        "calmness_score": calmness, "interior_calmness_score": interior_calmness,
        "detail_score": details["score"], "details": details,
        "jitter_findings": jitter_findings, "regions_profile": regions_profile,
        "legacy_overall_score": image["legacy_overall_score"],
        "legacy_loop_score": image["legacy_loop_score"],
        "confidence": confidence, "valid": not invalid and bool(regional), "static": static,
        "durations_ms": durations, "duration_ms": float(sum(durations)),
        "suspected_region": suspect, "warnings": warnings, "regions": regions,
        "frame_size": frame_size, "frames_metrics": [asdict(f) for f in fm],
        "pair_metrics": [asdict(p) | {"motion_outlier_z": outliers[i],
                          "temporal_score": (0. if invalid else temporal[i] if seam is not None else None),
                          "appearance_change": float(appearance[i])}
                         for i, p in enumerate(pm)],
        "seam_window": [n-1, n, 1, 2],
        "seam_transitions": [[pm[i].a, pm[i].b] for i in focus],
        "worst_seam_transition": [pm[min(focus, key=lambda i: temporal[i])].a,
                                  pm[min(focus, key=lambda i: temporal[i])].b],
        "boundary_findings": boundary_findings[:12],
        "visual_channels": {key: {"values": values, "limit": visual_limits[key],
                                   "ratios": visual_ratios[key]} for key, values in visual_values.items()},
        "reference_transition_indices": refs,
        "scoring": {"overall_weights": {"sequence": .35, "seam": .35, "calmness": .30},
                    "overall_cap_below_bad_seam": True,
                    "overall_cap_below_bad_calmness": True,
                    "overall_cannot_exceed_configured_detail_score": True,
                    "spatial_normalization": "visible subject height, never canvas size",
                    "temporal_method": "local velocity prediction from preceding/following steps; region shape and appearance anomalies",
                    "jitter_method": "isolated backward step between coherent neighbors; all cyclic transitions; fixed subject-relative noise floor; interior separately reported",
                    "limitations": "Heuristic geometry, not anatomical tracking or an artistic quality guarantee. Calmness only detects resolvable brief centroid backsteps; texture-only flicker, long-period wobble and changes below the noise floor can escape it."},
    }
    report.update({key: image[key] for key in ("source", "source_sha256", "grid", "grid_mode",
                                               "layout_validation", "timing_source")})
    if image["layout_validation"]["source"] == "Geometrie-Heuristik":
        report["warnings"].append("Raster nur geometrisch bestimmt: visuelle Bestätigung oder .anim.json empfohlen.")
    if image["layout_validation"]["override"]:
        report["warnings"].append("--trust-grid aktiv: Namenshinweise und Unterteilungsverdacht werden vom Nutzer übergangen.")
    return report

def find_check_command(filename):
    """Direkte Skripte neben TestAll bevorzugen; sonst installierte Wrapper nutzen."""
    sibling = Path(__file__).resolve().parent/filename
    if sibling.is_file():
        return [sys.executable, str(sibling)]
    for name in (Path(filename).stem, filename):
        command = shutil.which(name)
        if command:
            return [command]
    raise FileNotFoundError(f"Prüfprogramm fehlt: {filename}; neben TestAll ablegen oder als {Path(filename).stem} im PATH installieren.")

def run_check(name, path, args):
    command = find_check_command(CHECKS[name][2])
    options = ["--pipe-json"]
    for flag, value in (("--frame", args.frame), ("--grid", args.grid),
                         ("--alpha-threshold", args.alpha_threshold), ("--fps", args.fps),
                         ("--durations", args.durations), ("--metadata", args.metadata),
                         ("--regions", args.regions), ("--slow-factor", args.slow_factor)):
        if value is not None:
            options.extend([flag, str(value)])
    if args.trust_grid:
        options.append("--trust-grid")
    if args.include_fixed:
        options.append("--include-fixed")
    proc = subprocess.run([*command, *options, "--", str(path)], capture_output=True,
                          text=True, encoding="utf-8", shell=False, check=False)
    if proc.returncode == 130 or proc.returncode == -2:
        raise KeyboardInterrupt
    try:
        payload = json.loads(proc.stdout)
        reports = payload["reports"]
        if not isinstance(reports, list) or len(reports) != 1 or not isinstance(reports[0], dict):
            raise ValueError("genau ein Ergebnis erwartet")
    except (ValueError, KeyError, TypeError) as exc:
        message = proc.stderr.strip() or f"Keine gültige Ergebnisübergabe (Exit {proc.returncode}): {exc}"
        raise ValueError(CHECKS[name][0]+": "+message) from exc
    report = reports[0]
    if proc.returncode != 0:
        reason = "; ".join(report.get("warnings", [])) or proc.stderr.strip() or f"Exit {proc.returncode}"
        raise ValueError(CHECKS[name][0]+": "+reason)
    if report.get("test") != name:
        raise ValueError(CHECKS[name][0]+": Ergebnis gehört zu einer anderen Prüfung.")
    return report

def analyze(path, args, collected=None):
    test = args.test
    try:
        selected = CHECKS if test == "all" else (test,)
        results, failures = {}, []
        for name in selected:
            try:
                results[name] = run_check(name, path, args)
            except (OSError, ValueError) as exc:
                failures.append(str(exc))
        if failures:
            raise ValueError("; ".join(failures))
        first = next(iter(results.values()))
        for result in results.values():
            if any(result[key] != first[key] for key in ("source_sha256", "grid", "frames", "durations_ms")):
                raise ValueError("Eingabe oder Einstellungen haben sich zwischen den Prüfungen geändert.")
        report = combine_reports(results) if test == "all" else first
        report.pop("_aggregate", None)
        print(f"\n📄 {path.name} | {report['grid']['cols']}x{report['grid']['rows']} | {report['frames']} Frames | {report['timing_source']}")
        for label, key in report_scores(report):
            value = report[key]
            print(f"   {label:13s} [{bar(value)}] {percentage(value):>6} {rating(value)}")
        print("   Grenzfenster: "+" → ".join(map(str, report["seam_window"]))+" | Messbasis: "+report["confidence"])
        for item in report.get("boundary_findings", [])[:3]:
            print(f"   ⚠ {region_label(report, item['region'])}: {METRIC_LABELS[item['metric']]} bei {item['transition'][0]}→{item['transition'][1]}, {item['severity']:.2f}× Referenzgrenze")
        for item in report.get("jitter_findings", [])[:4]:
            print(f"   ⚠ Zitterverdacht {region_label(report, item['region'])}: kurzer Rückschritt bei {item['transition'][0]}→{item['transition'][1]} ({item['location']}), {item['value']:.2f}px / Grenze {item['reference_limit']:.2f}px")
        for item in report.get("details", {}).get("findings", [])[:3]:
            print(f"   ⚠ Detail {item['label']}: {DETAIL_LABELS[item['metric']]}, Fenster {' → '.join(map(str, item['support_frames']))}, {item['severity']:.2f}× Referenzgrenze, Rechteck {item['box']}")
        if "details" in report and not report["details"]["configured"]:
            print("   ℹ Kleine Details nicht geprüft: optional detail_regions im Bereichsprofil angeben.")
        for warning in report["warnings"]:
            print("   ℹ "+warning)
        if not args.no_report:
            grid = report["grid"]
            with Image.open(path) as source:
                frames, _, _ = split_frames(source, report["frames"], f"{grid['cols']}x{grid['rows']}")
            out_dir = args.output_dir if args.output_dir is not None else Path.cwd()/".compare"
            write_reports(path, frames, report, out_dir, args.slow_factor)
        if collected is not None:
            collected.append(report)
        return True
    except (OSError, ValueError, TypeError) as exc:
        print(f"\n⚠ {path.name}: nicht analysiert – {exc}")
        out_dir = None if args.no_report else args.output_dir if args.output_dir is not None else Path.cwd()/".compare"
        try:
            report = invalid_report(path, str(exc), out_dir, test=test)
            if collected is not None:
                collected.append(report)
        except OSError as report_error:
            print(f"   Bericht konnte nicht geschrieben werden: {report_error}", file=sys.stderr)
        return False

def main(argv=None):
    args = parse_args(argv)
    if args.fail_below is not None and (not math.isfinite(args.fail_below) or not 0 <= args.fail_below <= 100):
        print("Fehler: --fail-below muss 0..100 sein.", file=sys.stderr)
        return 2
    try:
        return run_args(args, [])
    except KeyboardInterrupt:
        print("Abbruch durch Benutzer.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
