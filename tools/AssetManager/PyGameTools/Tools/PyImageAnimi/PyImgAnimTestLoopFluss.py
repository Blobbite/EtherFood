#!/usr/bin/env python3
"""Loop-Fluss für PNG-Spritesheet-Animationen prüfen.

Eigenständiges Python-Programm für direkte Aufrufe und Linux-Wrapper.
Benötigte Pakete laut venv.txt: numpy und pillow.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import redirect_stdout
from dataclasses import asdict, dataclass
from functools import cached_property
import hashlib
import html
import io
import json
import math
from pathlib import Path
import re
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

CHECKS = {'loop-flow': ('Loop-Fluss', 'seam_score', None)}


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

def frame_durations(args):
    validate_frame_count(args.frame)
    if not 0 <= args.alpha_threshold <= 254:
        raise ValueError("--alpha-threshold muss 0..254 sein.")
    if not math.isfinite(args.fps) or not 0 < args.fps <= 240:
        raise ValueError("--fps muss endlich und größer als 0, höchstens 240 sein.")
    if not math.isfinite(args.slow_factor) or not 1 <= args.slow_factor <= 20:
        raise ValueError("--slow-factor muss zwischen 1 und 20 liegen.")
    if args.fail_below is not None and (not math.isfinite(args.fail_below) or not 0 <= args.fail_below <= 100):
        raise ValueError("--fail-below muss 0..100 sein.")
    durations = ([float(v.strip()) for v in args.durations.split(",")] if args.durations
                 else [1000. / args.fps] * args.frame)
    if len(durations) != args.frame or any(not math.isfinite(v) or not 1 <= v <= 30000 for v in durations):
        raise ValueError("Für jeden Frame ist genau eine endliche Dauer von 1..30000 ms nötig.")
    if max(durations) * args.slow_factor > 655350:
        raise ValueError("Zeitlupendauer überschreitet das GIF-Limit.")
    return durations

def resolve_settings(path, args):
    """Zeit/Raster pro Datei auflösen. Widersprüche nicht stillschweigend bewerten."""
    resolved = argparse.Namespace(**vars(args))
    metadata_path = args.metadata or path.with_suffix(".anim.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    if args.metadata and not metadata_path.exists():
        raise ValueError(f"Metadaten fehlen: {metadata_path}")
    if not isinstance(metadata, dict):
        raise ValueError("Metadaten müssen ein JSON-Objekt sein.")
    hints = re.findall(r"(?<!\d)([1-9]\d*)[xX]([1-9]\d*)(?!\d)", path.stem)
    name_grid = tuple(map(int, hints[-1])) if hints else None
    meta_grid = metadata.get("grid")
    if isinstance(meta_grid, dict):
        meta_grid = (meta_grid.get("cols", meta_grid.get("columns")), meta_grid.get("rows"))
    elif isinstance(meta_grid, str) and re.fullmatch(r"[1-9]\d*[xX][1-9]\d*", meta_grid):
        meta_grid = tuple(map(int, meta_grid.lower().split("x")))
    elif meta_grid is not None:
        raise ValueError("Metadaten-Raster erwartet cols/rows oder z.B. 4x4.")
    if meta_grid and any(type(v) is not int or v < 1 for v in meta_grid):
        raise ValueError("Metadaten-Raster muss positive ganze Spalten-/Zeilenzahlen enthalten.")
    explicit_grid = tuple(map(int, args.grid.lower().split("x"))) if re.fullmatch(r"[1-9]\d*[xX][1-9]\d*", args.grid) else None
    if args.trust_grid and args.grid == "auto":
        raise ValueError("--trust-grid verlangt ein explizites --grid.")
    counts = [v for v in (args.frame, metadata.get("frames"),
                          math.prod(meta_grid) if meta_grid else None,
                          math.prod(explicit_grid) if explicit_grid else None,
                          math.prod(name_grid) if name_grid and not args.trust_grid else None) if v is not None]
    if not counts:
        raise ValueError("Framezahl unbekannt. -f, explizites --grid oder .anim.json angeben.")
    for n in counts:
        validate_frame_count(n)
    if len(set(counts)) != 1:
        raise ValueError(f"Framezahl/Raster widersprechen sich ({counts}). Keine Bewertung. Bei diesem Blatt -f und --grid prüfen; veralteten Namenshinweis nur mit --trust-grid übergehen.")
    resolved.frame = counts[0]
    grids = [g for g in (explicit_grid, meta_grid, name_grid if not args.trust_grid else None) if g]
    if len(set(grids)) > 1:
        raise ValueError("Rasterangaben in Dateiname, Metadaten und --grid widersprechen sich.")
    if args.grid in {"horizontal", "vertical"} and grids:
        expected = (resolved.frame, 1) if args.grid == "horizontal" else (1, resolved.frame)
        if expected != grids[0]:
            raise ValueError("--grid widerspricht dem Rasterhinweis.")
    if args.grid == "auto" and grids:
        resolved.grid = f"{grids[0][0]}x{grids[0][1]}"
    resolved.fps = args.fps if args.fps is not None else metadata.get("fps", 8.)
    resolved.durations = args.durations
    if args.durations is None and args.fps is None and "durations_ms" in metadata:
        resolved.durations = ",".join(map(str, metadata["durations_ms"]))
    resolved.timing_source = ("CLI-Framezeiten" if args.durations else "CLI-FPS" if args.fps is not None
                              else "Metadaten" if "fps" in metadata or "durations_ms" in metadata else "Annahme: 8 FPS")
    resolved.layout_source = ("explizites Raster" if args.grid != "auto" else "Metadaten" if meta_grid
                              else "Dateiname + Geometrieprüfung" if name_grid else "Geometrie-Heuristik")
    profile = json.loads(args.regions.read_text(encoding="utf-8")) if args.regions else metadata.get("regions_profile")
    return resolved, profile

def repeated_subdivision(frames, threshold):
    """Konservativer Verdacht: zwei große Motive mit leerer Trennlinie je Zelle.

    Keine Connected-Component-Anatomie: lose Waffen/Finger sind keine neuen Frames.
    Nur wiederkehrende, ähnlich große und fast zellhohe/-breite Hälften zählen.
    """
    suspicious = []
    for axis, label in ((1, "Spalten"), (0, "Zeilen")):
        votes = 0
        for frame in frames:
            mask = np.asarray(frame)[..., 3] > threshold
            length, orthogonal = mask.shape[axis], mask.shape[1-axis]
            if length % 2 or length < 8:
                continue
            mask = np.moveaxis(mask, axis, 1)
            mid = length//2
            band = max(1, round(length*.005))
            if mask[:, mid-band:mid+band].mean() > .015:
                continue
            a, b = mask[:, :mid], mask[:, mid:]
            mass_a, mass_b = int(a.sum()), int(b.sum())
            if min(mass_a, mass_b) < 16 or not .5 <= mass_a/max(1, mass_b) <= 2:
                continue
            spans = [np.ptp(np.where(half)[0])+1 for half in (a, b)]
            if min(spans) >= .75*orthogonal:
                votes += 1
        if votes >= math.ceil(.75*len(frames)):
            suspicious.append(label)
    return suspicious

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

def crop_common(a, b):
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    return a[:h, :w], b[:h, :w]

def similarity_from_mae(a, b):
    a, b = crop_common(a.astype(np.float32), b.astype(np.float32))
    return float(np.clip(1 - np.abs(a-b).mean() / 255., 0, 1))

def silhouette_iou(a, b, threshold):
    aa, bb = np.asarray(a)[..., 3] > threshold, np.asarray(b)[..., 3] > threshold
    union = np.logical_or(aa, bb).sum()
    return float(np.logical_and(aa, bb).sum() / union) if union else 0.

def pair_metrics(a_img, b_img, a_m, b_m, threshold):
    """Unsichtbares RGB und leere Außenfläche haben KEIN positives Gewicht."""
    aa, bb = np.asarray(a_img), np.asarray(b_img)
    dx, dy = b_m.center_x-a_m.center_x, b_m.center_y-a_m.center_y
    shift = math.hypot(dx, dy)
    iou = silhouette_iou(a_img, b_img, threshold)
    a, b = aa[..., 3].astype(float)/255, bb[..., 3].astype(float)/255
    union_mass = np.maximum(a, b).sum()
    alpha_sim = float(1 - np.abs(a-b).sum()/union_mass) if union_mass else 0.
    overlap = np.minimum(a, b)
    if overlap.sum():
        delta = np.abs(aa[..., :3].astype(float)-bb[..., :3].astype(float)).mean(axis=2)/255
        rgb_sim = float(1 - (delta*overlap).sum()/overlap.sum())
    else:
        rgb_sim = 0.
    height = max(a_m.bbox[3]-a_m.bbox[1], b_m.bbox[3]-b_m.bbox[1], 1)
    pos_score = math.exp(-shift/max(1., height*.10))
    score = .35*iou + .25*alpha_sim + .20*rgb_sim + .20*pos_score
    if not a_m.visible_pixels or not b_m.visible_pixels:
        score = 0.
    # Nur zum transparenten Vorher/Nachher-Vergleich, niemals zur neuen Note.
    legacy_pos = max(0., 1.-min(1., shift/(math.hypot(*a_img.size)*.08)))
    legacy_iou = iou if a_m.visible_pixels or b_m.visible_pixels else 1.
    legacy = (.35*legacy_iou + .25*similarity_from_mae(aa[..., 3], bb[..., 3])
              + .20*similarity_from_mae(aa[..., :3], bb[..., :3]) + .20*legacy_pos)
    return PairMetrics(a_m.index, b_m.index, dx, dy, shift, iou, alpha_sim, rgb_sim,
                       float(np.clip(score, 0, 1)), float(legacy))

def global_character_bbox(frames, threshold):
    boxes = [frame_metrics(f, i, threshold).bbox for i, f in enumerate(frames)]
    boxes = [b for b in boxes if b[2] > b[0] and b[3] > b[1]]
    if not boxes:
        return (0, 0, frames[0].width, frames[0].height)
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))

def region_bounds(frames, threshold):
    _, y0, _, y1 = global_character_bbox(frames, threshold)
    h = max(1, y1-y0)
    a, b = y0+round(h*.36), y0+round(h*.64)
    return {"full": (y0, y1), "top": (y0, a), "middle": (a, b), "bottom": (b, y1)}

def region_boxes(frames, threshold, profile=None):
    x0, y0, x1, y1 = global_character_bbox(frames, threshold)
    boxes = {name: {"box": (x0, a, x1, b), "label": ZONE_LABELS[name]}
             for name, (a, b) in region_bounds(frames, threshold).items()}
    if profile is None:
        return boxes
    if not isinstance(profile, dict) or profile.get("space", "subject") != "subject" or not isinstance(profile.get("regions"), dict):
        raise ValueError('Bereichsprofil erwartet {"space":"subject","regions":{"name":{"label":"...","box":[x0,y0,x1,y1]}}}.')
    if len(profile["regions"]) > 16:
        raise ValueError("Höchstens 16 zusätzliche Messbereiche erlaubt.")
    for name, spec in profile["regions"].items():
        if name in boxes or not re.fullmatch(r"[a-zA-Z][\w-]{0,40}", name):
            raise ValueError(f"Ungültiger oder reservierter Bereichsname: {name}")
        box = spec.get("box") if isinstance(spec, dict) else None
        if not isinstance(box, list) or len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in box):
            raise ValueError(f"Bereich {name}: vier endliche Koordinaten zwischen 0 und 1 nötig.")
        a, b, c, d = box
        if a >= c or b >= d:
            raise ValueError(f"Leerer Messbereich: {name}")
        bounds = (x0+round(a*(x1-x0)), y0+round(b*(y1-y0)),
                  x0+round(c*(x1-x0)), y0+round(d*(y1-y0)))
        boxes[name] = {"box": bounds, "label": str(spec.get("label", name))}
    return boxes

def region_features(frames, y0, y1, threshold, x0=0, x1=None):
    features = []
    for frame in frames:
        mask = np.asarray(frame)[..., 3] > threshold
        ys, xs = np.where(mask[y0:y1, x0:x1])
        ys, xs = ys+y0, xs+x0
        if len(xs) < 4:
            return None
        # Robuste 5-/95-%-Spannen mindern Einzelpixel-Rauschen. Keine
        # Einzelbild-Zentrierung: tatsächliche globale Verschiebung bleibt messbar.
        width = float(np.quantile(xs, .95)-np.quantile(xs, .05))
        height = float(np.quantile(ys, .95)-np.quantile(ys, .05))
        features.append([float(xs.mean()), float(ys.mean()), width, height, math.sqrt(len(xs))])
    return np.asarray(features, dtype=float)

def reference_indices(n):
    # N-1→N, N→1, 1→2 sind das Prüf-Fenster, nicht seine eigene Referenz.
    return list(range(1, n-2)) if n >= 6 else list(range(n-1))

def limit_for(values, floor, refs):
    ref = np.asarray(values, dtype=float)[refs]
    median = float(np.median(ref))
    mad = float(np.median(np.abs(ref-median)))*1.4826
    return max(float(floor), median*2.5, float(np.quantile(ref, .75))+2.5*mad)

def severity_to_quality(ratio):
    return float(math.exp(-1.5*max(0., float(ratio)-1.)**1.1))

def region_measurements(frames, threshold, profile=None):
    """Gemeinsame Geometriemessung, ohne Fluss- oder Ruhebewertung."""
    result = {}
    for name, spec in region_boxes(frames, threshold, profile).items():
        x0, y0, x1, y1 = spec["box"]
        features = region_features(frames, y0, y1, threshold, x0, x1)
        result[name] = {"label": spec["label"], "valid": features is not None,
                        "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                        "features": features}
    return result

@dataclass
class AnalysisContext:
    """Einmal validierte Frames; Messwerte werden bei Bedarf gemeinsam genutzt."""
    frames: list
    threshold: int = 8
    durations_ms: list | None = None
    regions_profile: dict | None = None

    def __post_init__(self):
        validate_frame_count(len(self.frames))
        if len({f.size for f in self.frames}) != 1:
            raise ValueError("Alle Frames benötigen dieselbe Canvasgröße.")
        self.durations = (list(self.durations_ms) if self.durations_ms is not None
                          else [125.]*len(self.frames))
        if len(self.durations) != len(self.frames) or any(
                not math.isfinite(v) or v <= 0 for v in self.durations):
            raise ValueError("Ungültige Framezeiten.")

    @cached_property
    def metrics(self):
        return [frame_metrics(f, i+1, self.threshold) for i, f in enumerate(self.frames)]

    @cached_property
    def pairs(self):
        n = len(self.frames)
        return [pair_metrics(self.frames[i], self.frames[(i+1) % n],
                             self.metrics[i], self.metrics[(i+1) % n], self.threshold)
                for i in range(n)]

    @cached_property
    def regions(self):
        return region_measurements(self.frames, self.threshold, self.regions_profile)

    @cached_property
    def height(self):
        box = global_character_bbox(self.frames, self.threshold)
        return max(1, box[3]-box[1])

    @cached_property
    def invalid_frames(self):
        return [f.index for f in self.metrics if not f.visible_pixels]

    @cached_property
    def static(self):
        return all(p.silhouette_iou == 1 and p.alpha_similarity == 1
                   and p.rgb_similarity == 1 for p in self.pairs)

def motion_channels(features, dt, height):
    """Lokale Geschwindigkeitsfortsetzung, nicht Gleichheit von End- und Startpose."""
    nominal = float(np.median(dt))
    velocity = (np.roll(features, -1, axis=0)-features)/dt[:, None]
    before = (np.roll(dt, 1)+dt)/2
    after = (np.roll(dt, -1)+dt)/2
    predicted = (np.roll(velocity, 1, axis=0)*after[:, None]
                 + np.roll(velocity, -1, axis=0)*before[:, None])/(before+after)[:, None]
    residual = (velocity-predicted)*nominal
    movement = velocity*nominal
    return {
        "position_step": (np.linalg.norm(movement[:, :2], axis=1), max(.8, height*.0025)),
        "direction_change": (np.linalg.norm(residual[:, :2], axis=1), max(1., height*.004)),
        "shape_step": (np.linalg.norm(movement[:, 2:], axis=1), max(1.2, height*.005)),
        "shape_change": (np.linalg.norm(residual[:, 2:], axis=1), max(1.5, height*.006)),
    }, residual[:, :2], velocity[:, :2]

def region_loop_diagnostics(frames, threshold, durations_ms=None, regions_profile=None,
                            *, measurements=None):
    dt = np.asarray(durations_ms if durations_ms is not None else [125.]*len(frames), dtype=float)/1000
    n = len(frames)
    refs = reference_indices(n)
    height = max(1, global_character_bbox(frames, threshold)[3]-global_character_bbox(frames, threshold)[1])
    result = {}
    focus = sorted({(n-2) % n, n-1, 0})
    if measurements is None:
        measurements = region_measurements(frames, threshold, regions_profile)
    for name, spec in measurements.items():
        x0, y0, x1, y1 = (spec[key] for key in ("x0", "y0", "x1", "y1"))
        features = spec["features"]
        if features is None:
            result[name] = {"valid": False, "label": spec["label"], "score": None, "continuity_score": None}
            continue
        channels, residual, velocity = motion_channels(features, dt, height)
        values, limits, ratios = {}, {}, {}
        for key, (measure, floor) in channels.items():
            limits[key] = limit_for(measure, floor, refs)
            values[key] = measure.tolist()
            ratios[key] = (measure/limits[key]).tolist()
        worst = np.max(np.asarray(list(ratios.values())), axis=0)
        qualities = [severity_to_quality(v) for v in worst]
        score = max(float(worst[i]) for i in focus)
        result[name] = {
            "valid": True, "label": spec["label"], "x0": x0, "x1": x1, "y0": y0, "y1": y1,
            "error_x": float(residual[-1, 0]), "error_y": float(residual[-1, 1]),
            "error": float(np.linalg.norm(residual[-1])),
            "typical_motion": float(np.median(values["position_step"][:-1])),
            "score": score, "continuity_score": min(qualities[i] for i in focus),
            "centers": features[:, :2].tolist(), "extents": features[:, 2:].tolist(),
            "velocity_px_s": velocity.tolist(), "channels": values,
            "limits": limits, "ratios": ratios, "transition_scores": qualities,
        }
    return result

def evaluate_check(context):
    frames, threshold = context.frames, context.threshold
    durations, profile = context.durations, context.regions_profile
    n, pm = len(frames), context.pairs
    regions = region_loop_diagnostics(frames, threshold, durations, profile,
                                      measurements=context.regions)
    refs = reference_indices(n)
    appearance = np.asarray([.60*(1-p.silhouette_iou)+.15*(1-p.alpha_similarity)
                             + .25*(1-p.rgb_similarity) for p in pm])
    # Separate Farbprüfung: ein Farbblitz darf nicht durch normale Konturbewegung
    # in einer gemischten Referenz verschwinden. Normiert auf ein typisches Zeitintervall.
    time_scale = float(np.median(durations))/np.asarray(durations)
    visual_values = {"appearance_change": appearance*time_scale,
                     "color_change": np.asarray([1-p.rgb_similarity for p in pm])*time_scale,
                     "alpha_change": np.asarray([1-p.alpha_similarity for p in pm])*time_scale}
    visual_limits = {key: limit_for(values, .06, refs) for key, values in visual_values.items()}
    visual_ratios = {key: values/visual_limits[key] for key, values in visual_values.items()}
    appearance_quality = [severity_to_quality(v) for v in np.max(list(visual_ratios.values()), axis=0)]
    regional = [r["transition_scores"] for r in regions.values() if r["valid"]]
    temporal = np.min(np.asarray(regional+[appearance_quality]), axis=0).tolist()
    # Bildwerte spielen mit, normale Poseänderungen werden nicht mit Identität verwechselt.
    sequence = float(np.mean([.7*q+.3*p.score for q, p in zip(temporal, pm)]))
    focus = [(n-2) % n, n-1, 0]
    minimum = min(temporal[i] for i in focus)
    seam = .7*minimum+.3*float(np.mean([temporal[i] for i in focus]))
    valid_regions = [k for k, v in regions.items() if v["valid"]]
    suspect = min(valid_regions, key=lambda k: regions[k]["continuity_score"]) if valid_regions else "unknown"
    boundary_findings = []
    for key, ratios in visual_ratios.items():
        for i in focus:
            if ratios[i] > 1:
                boundary_findings.append({"region": "full", "metric": key,
                    "transition": [pm[i].a, pm[i].b], "severity": float(ratios[i]),
                    "value": float(visual_values[key][i]), "reference_limit": visual_limits[key]})
    for name in valid_regions:
        r = regions[name]
        for key, ratios in r["ratios"].items():
            for i in focus:
                if ratios[i] > 1:
                    boundary_findings.append({"region": name, "metric": key,
                        "transition": [pm[i].a, pm[i].b], "severity": ratios[i],
                        "value": r["channels"][key][i], "reference_limit": r["limits"][key]})
    boundary_findings.sort(key=lambda item: item["severity"], reverse=True)
    return {"regions": regions, "appearance": appearance,
            "visual_values": visual_values, "visual_limits": visual_limits,
            "visual_ratios": visual_ratios, "temporal": temporal,
            "sequence_score": sequence, "seam_score": seam,
            "suspected_region": suspect, "boundary_findings": boundary_findings[:12]}

def selected_report(context, result):
    """Nur die ausgewählte Prüfung bewerten und im Bericht ausweisen."""
    frames, fm, pm = (context.frames, context.metrics, context.pairs)
    n = len(frames)
    invalid, static = (context.invalid_frames, context.static)
    measurable = any((region['valid'] for region in context.regions.values()))
    warnings, confidence = ([], 'normal')
    if invalid:
        confidence = 'ungültig'
        warnings.append('Leere/nicht messbare Frames: ' + ', '.join(map(str, invalid)) + '. Framezahl/Raster oder Loop-Eignung prüfen.')
    elif not measurable:
        confidence = 'nicht messbar'
        warnings.append('Zu wenig sichtbare Pixel für eine zeitliche Geometrieprüfung.')
    elif static:
        confidence = 'statisch'
        warnings.append('Statische Bildfolge: keine Bewegung messbar; Bildidentität beweist keine flüssige Animation.')
    elif n < 6:
        confidence = 'niedrig'
        warnings.append('Weniger als sechs Frames: sehr kleine Bewegungsreferenz; visuelle Abnahme erforderlich.')
    report = {'schema_version': 4, 'tool_version': VERSION, 'test': 'loop-flow', 'tests_run': ['loop-flow'], 'frames': n, 'valid': not invalid and measurable, 'static': static, 'confidence': confidence, 'warnings': warnings, 'durations_ms': context.durations, 'duration_ms': float(sum(context.durations)), 'frame_size': list(frames[0].size), 'frames_metrics': [asdict(f) for f in fm], 'regions_profile': context.regions_profile, 'seam_window': [n - 1, n, 1, 2]}
    seam, sequence = (result['seam_score'], result['sequence_score'])
    if invalid:
        seam = sequence = 0.0
    elif not measurable or static:
        seam = sequence = None
    elif n < 6:
        seam = min(seam, 0.89)
    focus = [(n - 2) % n, n - 1, 0]
    worst = min(focus, key=lambda i: result['temporal'][i])
    report.update({'seam_score': seam, 'sequence_score': sequence, 'regions': result['regions'], 'suspected_region': result['suspected_region'], 'boundary_findings': result['boundary_findings'], 'seam_transitions': [[pm[i].a, pm[i].b] for i in focus], 'worst_seam_transition': [pm[worst].a, pm[worst].b], 'reference_transition_indices': reference_indices(n), 'visual_channels': {key: {'values': values.tolist(), 'limit': result['visual_limits'][key], 'ratios': result['visual_ratios'][key].tolist()} for key, values in result['visual_values'].items()}, 'pair_metrics': [asdict(p) | {'temporal_score': 0.0 if invalid else result['temporal'][i] if seam is not None else None, 'appearance_change': float(result['appearance'][i])} for i, p in enumerate(pm)]})
    if pm[-1].silhouette_iou == 1 and pm[-1].alpha_similarity == 1 and (pm[-1].rgb_similarity == 1) and (not static):
        warnings.append('Letzter und erster Frame sind identisch. Bei normalem Abspielen kann das eine Doppelbildpause erzeugen.')
    if any((f.bbox[0] == 0 or f.bbox[1] == 0 or f.bbox[2] == frames[0].width or (f.bbox[3] == frames[0].height) for f in fm if f.visible_pixels)):
        warnings.append('Motiv berührt einen Zellrand; möglichen Beschnitt visuell prüfen.')
    return report

def evaluate_frames(frames, threshold=8, durations_ms=None, regions_profile=None,
                    *, include_aggregate=False):
    context = AnalysisContext(frames, threshold, durations_ms, regions_profile)
    result = evaluate_check(context)
    report = selected_report(context, result)
    if include_aggregate:
        # TestAll benötigt die ungekappte Messbasis für die bisherige Gesamtnote.
        report["_aggregate"] = {key: result[key] for key in ("sequence_score", "seam_score", "temporal")}
    return report

def report_scores(report):
    test = report.get('test', 'all')
    return (CHECKS['loop-flow'][:2],)

def artifact_stem(path, test='all'):
    return path.stem + '_animtest' + ('_' + 'loop-flow'.replace('-', '_'))

def index_name(test='all'):
    return 'animtest' + ('_' + 'loop-flow'.replace('-', '_')) + '_index.html'

def region_label(report, name):
    return report['regions'].get(name, {}).get('label', ZONE_LABELS.get(name, name))

def bar(score, width=20):
    full = round(float(np.clip(score, 0, 1)) * width) if score is not None else 0
    return '█' * full + '░' * (width - full)

def rating(score):
    if score is None:
        return '⚪ nicht bewertbar'
    if score >= 0.9:
        return '🟢 sehr gut'
    if score >= GOOD:
        return '🟢 gut'
    if score >= NOTICE:
        return '🟡 auffällig'
    return '🔴 kritisch'

def percentage(score):
    return '—' if score is None else f'{score * 100:.1f}%'

def font(size):
    try:
        return ImageFont.truetype('DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default()

def checker(size):
    image = Image.new('RGB', size, '#142338')
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], 16):
        for x in range(0, size[0], 16):
            if (x // 16 + y // 16) % 2:
                draw.rectangle((x, y, x + 15, y + 15), fill='#1d3047')
    return image

def display_geometry(frames, edge=420):
    box = global_character_bbox(frames, 0)
    box = (max(0, box[0] - 12), max(0, box[1] - 12), min(frames[0].width, box[2] + 12), min(frames[0].height, box[3] + 12))
    scale = min(edge / max(1, box[2] - box[0]), edge / max(1, box[3] - box[1]))
    size = (max(1, round((box[2] - box[0]) * scale)), max(1, round((box[3] - box[1]) * scale)))
    offset = ((edge - size[0]) // 2, (edge - size[1]) // 2)
    return (box, size, offset, scale)

def render_stage(frame, geometry, edge=420):
    box, size, offset, _ = geometry
    result = checker((edge, edge)).convert('RGBA')
    image = frame.crop(box).resize(size, Image.Resampling.LANCZOS)
    result.alpha_composite(image, offset)
    return result.convert('RGB')

def arrow(draw, start, end, color):
    draw.line([start, end], fill=color, width=3)
    dx, dy = (end[0] - start[0], end[1] - start[1])
    length = math.hypot(dx, dy)
    if length < 2:
        draw.ellipse((end[0] - 3, end[1] - 3, end[0] + 3, end[1] + 3), outline=color, width=2)
        return
    ux, uy = (dx / length, dy / length)
    draw.polygon([end, (end[0] - ux * 9 - uy * 4, end[1] - uy * 9 + ux * 4), (end[0] - ux * 9 + uy * 4, end[1] - uy * 9 - ux * 4)], fill=color)

def create_slow_gif(frames, report, output, slow_factor):
    geometry = display_geometry(frames)
    indices = [len(frames) - 2, len(frames) - 1, 0, 1]
    images, durations = ([], [])
    for order, i in enumerate(indices):
        panel = Image.new('RGB', (460, 580), '#09121f')
        draw = ImageDraw.Draw(panel)
        draw.text((20, 16), 'Loop-Grenze in Zeitlupe', font=font(24), fill='#e4eefb')
        label = f'Frame {i + 1:02d}/{len(frames):02d}'
        if order == 2:
            label += '  ← LOOP'
        draw.text((20, 55), label, font=font(23), fill='#ffb08c' if order == 2 else '#a4c7ee')
        panel.paste(render_stage(frames[i], geometry), (20, 100))
        if order == 2:
            draw.rectangle((19, 99, 440, 520), outline='#ff996c', width=3)
        draw.text((20, 538), f"{slow_factor:g}× langsamer · Fluss {percentage(report['seam_score'])}", font=font(17), fill='#b0bfd4')
        images.append(panel)
        durations.append(max(20, int(round(report['durations_ms'][i] * slow_factor / 10)) * 10))
    separator = Image.new('RGB', (460, 580), '#182130')
    draw = ImageDraw.Draw(separator)
    for y, line in zip((190, 235, 280, 325), ('Diagnose-Ausschnitt', 'startet erneut', 'Kein Animationsframe', 'Kein echter Übergang 2 → N-1')):
        draw.text((24, y), line, font=font(21 if y < 280 else 17), fill='#bac9dd')
    images.append(separator)
    durations.append(700)
    atlas = Image.new('RGB', (460 * len(images), 580))
    for i, panel in enumerate(images):
        atlas.paste(panel, (i * 460, 0))
    palette = atlas.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    indexed = [panel.quantize(palette=palette, dither=Image.Dither.NONE) for panel in images]
    indexed[0].save(output, save_all=True, append_images=indexed[1:], duration=durations, disposal=2, loop=0, optimize=False)
    return {'frame_indices_1_based': [i + 1 for i in indices], 'durations_ms': durations, 'separator_frame': True, 'slow_factor': slow_factor}

def create_overlay(frames, report, output):
    edge = 350
    geometry = display_geometry(frames, edge)
    box, size, offset, scale = geometry
    names = [name for name, r in report['regions'].items() if name != 'full' and r['valid']]
    image = Image.new('RGB', (1120, max(585, 510 + 28 * len(names))), '#09121f')
    draw = ImageDraw.Draw(image)
    draw.text((20, 16), f'Loop {len(frames):02d} → 01 · Position, Kontur und lokale Verschiebung', font=font(23), fill='#e6eef9')
    stages = [render_stage(frames[-1], geometry, edge), render_stage(frames[0], geometry, edge)]
    onion = checker((edge, edge)).convert('RGBA')
    for frame, color in ((frames[-1], (62, 222, 245)), (frames[0], (248, 96, 205))):
        mask = frame.crop(box).getchannel('A').resize(size, Image.Resampling.LANCZOS)
        tint = Image.new('RGBA', size, (*color, 0))
        tint.putalpha(mask.point(lambda a: round(a * 0.56)))
        onion.alpha_composite(tint, offset)
    stages.append(onion.convert('RGB'))
    origins = [(20, 105), (385, 105), (750, 105)]
    for stage, origin, title in zip(stages, origins, (f'Frame {len(frames)}', 'Frame 1', 'Cyan: Ende · Magenta: Anfang')):
        draw.text((origin[0], 70), title, font=font(18), fill='#aac4e5')
        image.paste(stage, origin)

    def point(center, origin):
        return (origin[0] + offset[0] + (center[0] - box[0]) * scale, origin[1] + offset[1] + (center[1] - box[1]) * scale)
    for name in names:
        region = report['regions'][name]
        if not region['valid']:
            continue
        color = '#ffac70' if region['continuity_score'] < GOOD else '#b1f5bb'
        arrow(draw, point(region['centers'][-1], origins[2]), point(region['centers'][0], origins[2]), color)
        if region['continuity_score'] < GOOD:
            for origin in origins:
                y0 = origin[1] + offset[1] + (region['y0'] - box[1]) * scale
                y1 = origin[1] + offset[1] + (region['y1'] - box[1]) * scale
                x0 = origin[0] + offset[0] + (region['x0'] - box[0]) * scale
                x1 = origin[0] + offset[0] + (region['x1'] - box[0]) * scale
                draw.rectangle((x0, y0, x1, y1), outline=color, width=2)
    for j, name in enumerate(names):
        region = report['regions'][name]
        if region['valid']:
            a, b = (region['centers'][-1], region['centers'][0])
            message = f'{region_label(report, name)}: Δx {b[0] - a[0]:+.1f}px · Δy {b[1] - a[1]:+.1f}px'
            draw.text((20, 472 + j * 28), message, font=font(17), fill='#bfd0e4')
    draw.text((650, 487), 'Pfeile = Bereichsschwerpunkte.', font=font(17), fill='#bfd0e4')
    draw.text((650, 519), 'Orange = auffälliges Grenzfenster.', font=font(17), fill='#ffac70')
    image.save(output)

def score_html(label, value):
    color = '#8492a8' if value is None else '#80d5a2' if value >= GOOD else '#f3bf68' if value >= NOTICE else '#f38b85'
    width = 0 if value is None else max(0, min(100, value * 100))
    return f'<div class="score"><span>{html.escape(label)}</span><b>{percentage(value)}</b><div class="track"><div style="width:{width:.2f}%;background:{color}"></div></div></div>'

def loop_preview_html(frames, durations):
    encoded = []
    for frame in frames:
        stream = io.BytesIO()
        frame.save(stream, format='PNG')
        encoded.append('data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode('ascii'))
    data = json.dumps({'images': encoded, 'durations': durations}, separators=(',', ':'))
    return f'<canvas id="loop" width="{frames[0].width}" height="{frames[0].height}" aria-label="Vollständige Animation"></canvas><div><button id="play">Pause</button><label>Tempo <select id="speed"><option value="1">Originaltempo</option><option value="0.5">½ Tempo</option><option value="0.25">¼ Tempo</option></select></label><label>Frame <input id="seek" type="range" min="0" max="{len(frames) - 1}" value="0"></label><output id="position"></output></div><p>Verlustfreie PNG-Frames, feste Position und angegebene Framezeiten. Der Regler pausiert die Wiedergabe.</p><script>const animationData=' + data + ';</script>' + "<script>\n(()=>{const d=animationData, canvas=document.getElementById('loop'),ctx=canvas.getContext('2d');\nconst play=document.getElementById('play'),seek=document.getElementById('seek'),speed=document.getElementById('speed'),position=document.getElementById('position');\nconst starts=[];let total=0;d.durations.forEach(t=>{starts.push(total);total+=t});\nlet running=!matchMedia('(prefers-reduced-motion: reduce)').matches,phase=0,last=performance.now(),rate=1,current=-1;\nplay.textContent=running?'Pause':'Abspielen';\nPromise.all(d.images.map(src=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=reject;im.src=src}))).then(images=>{\nfunction draw(){let i=starts.findIndex((t,j)=>phase<t+d.durations[j]);if(i<0)i=0;if(i!==current){ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(images[i],0,0);seek.value=i;position.textContent=`${i+1} / ${images.length} · ${d.durations[i]} ms`;current=i}}\nfunction tick(now){if(running)phase=(phase+(now-last)*rate)%total;last=now;draw();requestAnimationFrame(tick)}\nplay.onclick=()=>{running=!running;last=performance.now();play.textContent=running?'Pause':'Abspielen'};\nseek.oninput=()=>{running=false;play.textContent='Abspielen';phase=starts[Number(seek.value)];draw()};\nspeed.onchange=()=>{rate=Number(speed.value);last=performance.now()};requestAnimationFrame(tick);\n}).catch(()=>{position.textContent='Vorschaubilder konnten nicht geladen werden.'});})();\n</script>"

def write_reports(path, frames, report, out_dir, slow_factor):
    return write_selected_reports(path, frames, report, out_dir, slow_factor)

def write_index(reports, out_dir):
    cards = []
    for r in reports:
        scores = ''.join((score_html(label, r[key]) for label, key in report_scores(r)))
        links = ' · '.join((f'''<a href="{quote(r['artifacts'][key])}">{label}</a>''' for key, label in (('slow_gif', 'Zeitlupe'), ('overlay', 'Überlagerung'), ('chart', 'Diagramm')) if key in r['artifacts']))
        cards.append(f'''<article class="card"><h2><a href="{quote(r['artifacts']['html'])}">{html.escape(r['source'])}</a></h2><div class="scores">{scores}</div><p>{html.escape(r['confidence'])} · {links}</p></article>''')
    page = f"""<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Loopprüfung · Übersicht</title><style>{STYLE}</style><body><h1>Animationen · Loopprüfung {VERSION}</h1><p>Bildähnlichkeit, Naht und Bewegungsruhe werden getrennt geprüft. Die Gesamtnote berücksichtigt alle drei.</p>{''.join(cards)}</body></html>"""
    test = reports[0].get('test', 'all') if reports else 'all'
    page = page.replace('Bildähnlichkeit, Naht und Bewegungsruhe werden getrennt geprüft. Die Gesamtnote berücksichtigt alle drei.', 'Einzelprüfung: ' + CHECKS['loop-flow'][0] + '. Die Übersicht zeigt nur diese Wertung.')
    (out_dir / index_name('loop-flow')).write_text(page, encoding='utf-8')

def invalid_report(path, reason, out_dir, test='all'):
    report = {'schema_version': 4, 'tool_version': VERSION, 'source': path.name, 'test': 'loop-flow', 'tests_run': [], 'valid': False, 'confidence': 'Eingabe ungültig', 'warnings': [reason], **{key: None for _, key in (CHECKS['loop-flow'][:2],)}}
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = artifact_stem(path, 'loop-flow')
        report['artifacts'] = {'json': stem + '.json', 'markdown': stem + '.md', 'html': stem + '.html'}
        (out_dir / (stem + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (out_dir / (stem + '.md')).write_text(f'# Keine Bewertung – {path.name}\n\n{reason}\n', encoding='utf-8')
        (out_dir / (stem + '.html')).write_text(f'''<!doctype html><html lang="de"><meta charset="utf-8"><title>Keine Bewertung</title><style>{STYLE}</style><body><h1>{html.escape(path.name)}</h1><p>Keine Bewertung: {html.escape(reason)}</p><a href="{index_name('loop-flow')}">Übersicht</a></body></html>''', encoding='utf-8')
    return report

def measurement_table(report):
    test = report['test']
    key = 'temporal_score'
    return (['Übergang', CHECKS['loop-flow'][0], 'Δx', 'Δy'], [[f"{p['a']}→{p['b']}", percentage(p[key]), f"{p['dx']:+.2f}px", f"{p['dy']:+.2f}px"] for p in report['pair_metrics']])
    return (['Bereich', 'Framefenster', 'Prüfung', 'Referenzgrenze'], [[item['label'], ' → '.join(map(str, item['support_frames'])), DETAIL_LABELS[item['metric']], f"{item['severity']:.2f}×"] for item in report['details']['findings'][:12]])

def write_selected_reports(path, frames, report, out_dir, slow_factor):
    out_dir.mkdir(parents=True, exist_ok=True)
    test = report['test']
    label, key, _ = CHECKS['loop-flow']
    stem = artifact_stem(path, 'loop-flow')
    names = {kind: stem + extension for kind, extension in (('json', '.json'), ('markdown', '.md'), ('html', '.html'))}
    names['overlay'] = stem + '_overlay.png'
    overlay_report = report
    create_overlay(frames, overlay_report, out_dir / names['overlay'])
    names['slow_gif'] = stem + '_loop_slow.gif'
    report['preview'] = create_slow_gif(frames, report, out_dir / names['slow_gif'], slow_factor)
    report['artifacts'] = names
    (out_dir / names['json']).write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    descriptions = {'loop-image': 'Bildähnlichkeit zwischen letztem und erstem Frame; keine zeitliche Bewegungswertung.', 'loop-flow': 'Bewegungs- und Bildfortsetzung rund um das Grenzfenster N-1 → N → 1 → 2.', 'calmness': 'Kurze Rückschritte im gesamten Loop. Die Messung erfasst nicht jede mögliche Zitterart.', 'details': 'Textur- und Konturfortsetzung in den ausdrücklich ausgewählten Detailbereichen.'}
    notes = [descriptions['loop-flow'], *report['warnings']]
    for item in report.get('boundary_findings', []):
        notes.append(f"{region_label(report, item['region'])}: {METRIC_LABELS[item['metric']]} bei {item['transition'][0]}→{item['transition'][1]}, {item['severity']:.2f}× Referenzgrenze.")
    headers, rows = measurement_table(report)
    metadata = f"Raster {report['grid']['cols']}×{report['grid']['rows']} · {len(frames)} Frames · {report['duration_ms']:g} ms · Bewertbarkeit: {report['confidence']}"
    figures = [(kind, title) for kind, title in (('overlay', 'Überlagerung'), ('slow_gif', 'Loop-Zeitlupe'), ('details', 'Lokale Details')) if kind in names]
    lines = [f'# {label} – {path.name}', '', f'- {label}: {percentage(report[key])} / {rating(report[key])}', '- ' + metadata, '', f"[Browserbericht]({quote(names['html'])}) · [JSON]({quote(names['json'])})", '']
    lines += ['- ' + note for note in notes]
    lines += ['', '## Messwerte', '', '| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |']
    lines += ['| ' + ' | '.join((str(cell).replace('|', '\\|').replace('\n', ' ') for cell in row)) + ' |' for row in rows]
    for kind, title in figures:
        lines += ['', f'![{title}]({quote(names[kind])})']
    (out_dir / names['markdown']).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    table = '<table><thead><tr>' + ''.join(('<th>' + html.escape(cell) + '</th>' for cell in headers)) + '</tr></thead><tbody>'
    table += ''.join(('<tr>' + ''.join(('<td>' + html.escape(str(cell)) + '</td>' for cell in row)) + '</tr>' for row in rows)) + '</tbody></table>'
    images = ''.join((f'<h2>{title}</h2><img src="{quote(names[kind])}" alt="{title}"' + (' class="gif"' if kind == 'slow_gif' else '') + '>' for kind, title in figures))
    note_html = ''.join(('<li>' + html.escape(note) + '</li>' for note in notes))
    page = f'''<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>{label} · {html.escape(path.name)}</title><style>{STYLE}</style><body>\n<p>PyImgAnimTest {VERSION} · <a href="{index_name('loop-flow')}">Übersicht</a></p>\n<h1>{label} · {html.escape(path.name)}</h1><div class="scores">{score_html(label, report[key])}</div>\n<p>{html.escape(metadata)}</p><ul class="warning">{note_html}</ul>\n<h2>Vollständiger Loop</h2>{loop_preview_html(frames, report['durations_ms'])}\n<h2>Messwerte</h2>{table}{images}\n<p><a href="{quote(names['markdown'])}">Messwerte und Hinweise</a> · <a href="{quote(names['json'])}">JSON</a></p></body></html>'''
    (out_dir / names['html']).write_text(page, encoding='utf-8')

def parse_args(argv=None):
    description = 'PyImgAnimTest – PNG-Spritesheets prüfen.\nTestAll: Loop-Bild → Loop-Fluss → Bewegungsruhe → Details.\nBeispiel: python3 PyImgAnimTestAll.py -f 16 --grid 4x4 bild.png'
    description = 'PyImgAnimTest – Einzelprüfung: ' + CHECKS['loop-flow'][0]
    p = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.set_defaults(test='loop-flow')
    p.add_argument('files', nargs='*', type=Path, help='Optional einzelne PNGs; sonst alle PNGs im Arbeitsordner')
    p.add_argument('-f', '--frame', type=int, help='Tatsächliche Framezahl, 3 bis 24; sonst aus Raster/Metadaten/Dateinamen')
    p.add_argument('--grid', default='auto', help='auto, horizontal, vertical oder explizit z.B. 4x4 / 3x4')
    p.add_argument('--alpha-threshold', type=int, default=8)
    p.add_argument('--fps', type=float, help='Wiedergabe-FPS; ohne Zeitangabe werden 8 angenommen')
    p.add_argument('--durations', help='Alternativ individuelle Framezeiten in ms, kommagetrennt')
    p.add_argument('--metadata', type=Path, help='Animations-Metadaten; sonst automatisch <Dateistamm>.anim.json')
    p.add_argument('--regions', type=Path, help='Benannte Messbereiche und optionale detail_regions als JSON, relativ zum gemeinsamen Motiv-Rechteck')
    p.add_argument('--trust-grid', action='store_true', help='Explizites Raster trotz widersprechendem Dateinamen/Unterteilungsverdacht verwenden')
    p.add_argument('--slow-factor', type=float, default=4.0, help='Zeitlupe relativ zur Wiedergabe, Standard 4')
    p.add_argument('--output-dir', type=Path, help='Anderer Reportordner; Standard .compare im Arbeitsordner')
    p.add_argument('--no-report', action='store_true', help='Keine Dateien/Ordner schreiben')
    p.add_argument('--include-fixed', action='store_true', help='Auch *_loopfix.png prüfen')
    p.add_argument('--fail-below', type=float, help='Exit 3 unter Grenzwert (0..100) oder nicht bewertbar: bei Einzeltests nur deren Wertung; bei all Gesamt, Loop-Fluss, Bewegungsruhe und konfigurierte Details')
    p.add_argument('--version', action='version', version=VERSION)
    p.add_argument('--pipe-json', action='store_true', help=argparse.SUPPRESS)
    return p.parse_args(argv)

def analyze(path, args, collected=None):
    test = getattr(args, 'test', 'all')
    try:
        settings, profile = resolve_settings(path, args)
        durations = frame_durations(settings)
        with Image.open(path) as source:
            if source.format != 'PNG' or getattr(source, 'n_frames', 1) != 1:
                raise ValueError('Erwartet wird ein statisches PNG-Spritesheet.')
            frames, cols, rows = split_frames(source, settings.frame, settings.grid)
        subdivisions = repeated_subdivision(frames, settings.alpha_threshold)
        if subdivisions and (not args.trust_grid):
            raise ValueError('Zellen enthalten wahrscheinlich weitere Frames (' + ', '.join(subdivisions) + '). Raster/Framezahl visuell prüfen; keine Qualitätswertung. --trust-grid nur nach Sichtprüfung verwenden.')
        report = evaluate_frames(frames, settings.alpha_threshold, durations, profile, include_aggregate=args.pipe_json)
        report.update({'source': path.name, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'grid': {'cols': cols, 'rows': rows}, 'grid_mode': args.grid, 'layout_validation': {'source': settings.layout_source, 'subdivision_suspicions': subdivisions, 'override': args.trust_grid, 'status': 'plausibel, visuell bestätigen'}, 'timing_source': settings.timing_source})
        if settings.layout_source == 'Geometrie-Heuristik':
            report['warnings'].append('Raster nur geometrisch bestimmt: visuelle Bestätigung oder .anim.json empfohlen.')
        if args.trust_grid:
            report['warnings'].append('--trust-grid aktiv: Namenshinweise und Unterteilungsverdacht werden vom Nutzer übergangen.')
        print(f'\n📄 {path.name} | {cols}x{rows} | {settings.frame} Frames | {settings.timing_source}')
        for label, key in report_scores(report):
            value = report[key]
            print(f'   {label:13s} [{bar(value)}] {percentage(value):>6} {rating(value)}')
        print('   Grenzfenster: ' + ' → '.join(map(str, report['seam_window'])) + ' | Messbasis: ' + report['confidence'])
        for item in report.get('boundary_findings', [])[:3]:
            print(f"   ⚠ {region_label(report, item['region'])}: {METRIC_LABELS[item['metric']]} bei {item['transition'][0]}→{item['transition'][1]}, {item['severity']:.2f}× Referenzgrenze")
        for item in report.get('jitter_findings', [])[:4]:
            print(f"   ⚠ Zitterverdacht {region_label(report, item['region'])}: kurzer Rückschritt bei {item['transition'][0]}→{item['transition'][1]} ({item['location']}), {item['value']:.2f}px / Grenze {item['reference_limit']:.2f}px")
        for item in report.get('details', {}).get('findings', [])[:3]:
            print(f"   ⚠ Detail {item['label']}: {DETAIL_LABELS[item['metric']]}, Fenster {' → '.join(map(str, item['support_frames']))}, {item['severity']:.2f}× Referenzgrenze, Rechteck {item['box']}")
        if 'details' in report and (not report['details']['configured']):
            print('   ℹ Kleine Details nicht geprüft: optional detail_regions im Bereichsprofil angeben.')
        for warning in report['warnings']:
            print('   ℹ ' + warning)
        if not args.no_report:
            out_dir = args.output_dir if args.output_dir is not None else Path.cwd() / '.compare'
            write_reports(path, frames, report, out_dir, args.slow_factor)
        if collected is not None:
            collected.append(report)
        return True
    except (OSError, ValueError, TypeError) as exc:
        print(f'\n⚠ {path.name}: nicht analysiert – {exc}')
        out_dir = None if args.no_report else args.output_dir if args.output_dir is not None else Path.cwd() / '.compare'
        try:
            report = invalid_report(path, str(exc), out_dir, test='loop-flow')
            if collected is not None:
                collected.append(report)
        except OSError as report_error:
            print(f'   Bericht konnte nicht geschrieben werden: {report_error}', file=sys.stderr)
        return False

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
        files = args.files or sorted(Path.cwd().glob('*.png'))
        if not args.include_fixed:
            files = [p for p in files if not p.stem.endswith('_loopfix')]
        if not files:
            raise ValueError('Keine PNG-Dateien ausgewählt.')
        if not args.no_report and len({p.stem for p in files}) != len(files):
            raise ValueError('Gleiche Dateistämme aus mehreren Ordnern: getrennte Läufe verwenden, sonst kollidieren Reports.')
        if args.metadata and len(files) != 1:
            raise ValueError('--metadata gehört zu genau einer PNG-Datei; für mehrere Dateien .anim.json verwenden.')
        print(f'PyImgTestAnim {VERSION} | {len(files)} PNGs | Raster und Zeiten werden je Datei geprüft')
        selected = ('loop-flow',)
        print('Prüfungen: ' + ' → '.join((CHECKS[name][0] for name in selected)))
        ok = sum((analyze(path, args, reports) for path in files))
        if not args.no_report and reports:
            out_dir = args.output_dir if args.output_dir is not None else Path.cwd() / '.compare'
            write_index(reports, out_dir)
            print(f"\nVorschau: {out_dir / index_name('loop-flow')}")
        print(f'Fertig: {ok}/{len(files)} Dateien analysiert; Originale unverändert.')
        if ok != len(files):
            return 2
        if args.fail_below is not None and any((quality_failed(r, args.fail_below) for r in reports)):
            return 3
        return 0
    except (OSError, ValueError) as exc:
        print(f'Fehler: {exc}', file=sys.stderr)
        return 2

def main(argv=None):
    args = parse_args(argv)
    reports = []
    try:
        if args.pipe_json:
            # Übergabe an TestAll ohne Dateien, lokale Imports oder Wrapper-Abhängigkeit.
            args.no_report = True
            with redirect_stdout(io.StringIO()):
                code = run_args(args, reports)
            print(json.dumps({"reports": reports}, ensure_ascii=False, allow_nan=False))
            return code
        return run_args(args, reports)
    except KeyboardInterrupt:
        print("Abbruch durch Benutzer.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
