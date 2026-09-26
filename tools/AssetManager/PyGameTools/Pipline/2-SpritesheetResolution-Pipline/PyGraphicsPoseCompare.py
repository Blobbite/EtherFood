#!/usr/bin/env python3
"""Offline pose comparison using relative links to existing PNGs and GIFs."""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PiplineToos"))
import PyImgGif as gif_tools
import PyPipelineOutputs as output_policy

if __package__:
    from .PyGraphicsCompare import DIRECTIONS, VARIANTS, identify_direction
else:
    from PyGraphicsCompare import DIRECTIONS, VARIANTS, identify_direction


FOLDER_PATTERN = re.compile(r"spritesheet-frame?([0-9]+)", re.IGNORECASE)


def frame_folders(variant: Path, frames: list[int] | None) -> list[Path]:
    if variant.is_symlink():
        raise ValueError(f"Variantenordner ist ein Link: {variant}")
    if not variant.is_dir():
        return []
    folders = []
    for path in variant.iterdir():
        match = FOLDER_PATTERN.fullmatch(path.name)
        if match and path.is_dir():
            if path.is_symlink():
                raise ValueError(f"Frame-Ordner ist ein Link: {path}")
            if frames is None or int(match[1]) in frames:
                folders.append(path)
    return sorted(folders, key=gif_tools.natural_key)


def png_files(directory: Path) -> list[Path]:
    return sorted((p for p in directory.iterdir() if p.is_file() and not p.is_symlink()
                   and not p.name.startswith(".") and p.suffix.lower() == ".png"),
                  key=gif_tools.natural_key)


def content_bounds(path: Path, item: dict) -> list[list[int] | None]:
    """Measure visible content without cropping, shifting or exporting frames."""
    bounds = []
    with gif_tools.Image.open(path) as image:
        if item["sheet"]:
            with image.convert("RGBA") as rgba:
                alpha = rgba.getchannel("A").point([0] * 16 + [255] * 240)
            for index in range(item["logicalFrames"]):
                x = index % item["columns"] * item["width"]
                y = index // item["columns"] * item["height"]
                with alpha.crop((x, y, x + item["width"], y + item["height"])) as cell:
                    box = cell.getbbox()
                    bounds.append(list(box) if box else None)
            alpha.close()
        else:
            stored = []
            for index in range(item["storedFrames"]):
                image.seek(index)
                with image.convert("RGBA") as rgba:
                    box = rgba.getchannel("A").point([0] * 16 + [255] * 240).getbbox()
                    stored.append(list(box) if box else None)
            bounds = [stored[index] for index in item["frameMap"]]
    return bounds


def collect_pose(root: Path, high: Path, output: Path, fps: int,
                 frames: list[int] | None = None, grid: tuple[int, int] | None = None,
                 *, measure: bool = False) -> tuple[list[dict], int]:
    """Discover actual results, including incomplete sets and GIF-only folders."""
    groups = {}
    errors = 0
    for variant, _ in VARIANTS:
        directory = high if variant == "comic_high" else root / variant
        folders = frame_folders(directory, frames)
        if not directory.is_dir():
            continue
        for folder in [directory, *folders]:
            single = folder == directory
            folder_name = "" if single else folder.name
            sources = {}
            for path in png_files(folder):
                if path.stem in sources:
                    raise ValueError(f"Mehrdeutige PNG-Dateinamen: {path}")
                sources[path.stem] = path
            exports = {}
            if not single:
                for path in gif_tools.discover_gifs(folder):
                    stem = re.sub(r"_[0-9]+fps$", "", path.stem, flags=re.IGNORECASE)
                    choices = exports.setdefault(stem, [])
                    choices.append(path)
            for stem in sorted(sources.keys() | exports.keys()):
                family, direction = identify_direction(stem)
                key = (folder_name, family)
                group = groups.setdefault(key, {"folder": folder_name, "family": family,
                                                "frames": 1, "single": single, "directions": {}})
                tracks = group["directions"].setdefault(direction, {})
                candidates = exports.get(stem, [])
                gif = next((p for p in candidates if p.stem.lower().endswith(f"_{fps}fps")),
                           candidates[0] if candidates else None)
                path = sources.get(stem)
                try:
                    if path:
                        manual = gif_tools.Grid(*grid, "CLI") if grid and not single else None
                        item = gif_tools.read_sheet_preview(path, output, fps, manual, gif, single_image=single)
                        if not single and item["logicalFrames"] != int(FOLDER_PATTERN.fullmatch(folder.name)[1]):
                            raise ValueError(f"Raster passt nicht zum Frame-Ordner: {path}")
                    else:
                        item = gif_tools.read_gif_for_gallery(gif, output)
                        item["columns"] = item["rows"] = None
                    item["bounds"] = content_bounds(path or gif, item) if measure else []
                    group["frames"] = max(group["frames"], item["logicalFrames"])
                    tracks[variant] = item
                except (OSError, ValueError, SyntaxError, EOFError, MemoryError,
                        gif_tools.Image.DecompressionBombError, gif_tools.Image.DecompressionBombWarning) as exc:
                    tracks[variant] = {"missing": True, "reason": str(exc)}
                    errors += 1
                    print(f"VERGLEICH: {path or gif}: {exc}", file=sys.stderr)
    result = sorted(groups.values(), key=lambda group: (group["frames"], group["folder"], group["family"]))
    for group in result:
        for tracks in group["directions"].values():
            available = [item for item in tracks.values() if not item.get("missing")]
            if available:
                reference = tracks.get("comic_high")
                if reference is None or reference.get("missing"):
                    reference = max(available, key=lambda item: item["width"] * item["height"])
                for item in available:
                    item["referenceWidth"] = reference["width"]
                    item["referenceHeight"] = reference["height"]
                    item["hasHDReference"] = bool(tracks.get("comic_high") and not tracks["comic_high"].get("missing"))
            for variant, _ in VARIANTS:
                tracks.setdefault(variant, {"missing": True, "reason": "Für diese Variante fehlen PNG und GIF."})
    return result, errors


def build_position_comparison(root: Path, poses: list[tuple[str, Path, Path]], fps: int,
                              frames: list[int] | None = None, grid: tuple[int, int] | None = None, *,
                              overwrite: bool = False) -> int:
    output = root / "positionsvergleich.html"
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError(f"Ungültige Vergleichsausgabe: {output}")
    if not output_policy.should_write(output, overwrite=overwrite):
        return 0
    entries = []
    errors = 0
    for name, directory, high in poses:
        groups, failed = collect_pose(directory, high, output, fps, frames, grid, measure=True)
        errors += failed
        # The position view renders animations only. Do not offer a pose whose
        # only assets are single images, otherwise its initial view is empty.
        groups = [group for group in groups if not group["single"]]
        if not groups:
            continue
        entries.append({"name": name, "sets": groups,
                        "comparison": gif_tools.relative_url(directory / "aufloesungsvergleich.html", output)})
    payload = {"title": root.name, "created": datetime.now().astimezone().isoformat(timespec="seconds"),
               "fps": fps, "fpsChoices": gif_tools.FPS_CHOICES, "directions": DIRECTIONS,
               "variants": [{"id": key, "label": label} for key, label in VARIANTS], "poses": entries}
    html = HTML_TEMPLATE.replace("__POSE_DATA__", gif_tools.script_safe_json(payload))
    root.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".positionsvergleich-", suffix=".html", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(html)
        gif_tools.validate_html_output(output)
        os.replace(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(f"Größen- und Positionsvergleich: {output}", flush=True)
    return 1 if errors else 0


HTML_TEMPLATE = r'''<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>PyGraphics · Größen- und Positionsvergleich</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #131719;
        --panel: #1c2327;
        --line: #35434a;
        --text: #eef4f3;
        --muted: #a8b9bf;
        --accent: #bbdf93;
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font:
          14px/1.5 system-ui,
          sans-serif;
      }
      main {
        max-width: 1680px;
        margin: auto;
        padding: 30px;
      }
      header {
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 24px;
      }
      .eyebrow {
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 2px;
        color: var(--accent);
      }
      h1 {
        font-size: clamp(25px, 3vw, 38px);
        letter-spacing: -1px;
        margin: 6px 0 9px;
      }
      p {
        margin: 0;
        color: var(--muted);
      }
      .badge {
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 6px 12px;
        white-space: nowrap;
      }
      .panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
      }
      .controls {
        display: flex;
        flex-wrap: wrap;
        gap: 14px 22px;
        align-items: end;
      }
      label,
      .field {
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 12px;
        color: var(--muted);
      }
      select,
      button {
        font: inherit;
        color: var(--text);
        background: #263137;
        border: 1px solid #50626b;
        border-radius: 6px;
        padding: 8px 10px;
        min-height: 36px;
      }
      select {
        max-width: 320px;
      }
      button {
        cursor: pointer;
      }
      button:hover {
        border-color: var(--accent);
      }
      button:disabled {
        opacity: 0.4;
        cursor: default;
      }
      button[aria-pressed="true"] {
        background: var(--accent);
        color: #1b2615;
      }
      button:focus-visible,
      input:focus-visible,
      select:focus-visible,
      a:focus-visible {
        outline: 2px solid var(--accent);
        outline-offset: 3px;
      }
      input {
        accent-color: var(--accent);
      }
      input[type="range"] {
        min-width: 120px;
        width: 100%;
      }
      .checks {
        display: flex;
        flex-wrap: wrap;
        gap: 7px 16px;
      }
      .checks label,
      .check {
        flex-direction: row;
        align-items: center;
        color: var(--text);
      }
      fieldset {
        border: 0;
        padding: 0;
        margin: 15px 0 0;
      }
      legend {
        font-size: 12px;
        color: var(--muted);
        margin-bottom: 7px;
      }
      .directions {
        display: flex;
        gap: 5px;
        flex-wrap: wrap;
      }
      .directions button {
        min-width: 40px;
      }
      .wide {
        flex: 1;
        min-width: 200px;
      }
      .readout {
        font-variant-numeric: tabular-nums;
        color: var(--accent);
      }
      .transport {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        margin: 15px 0;
      }
      .transport label {
        min-width: 150px;
        flex: 1;
        max-width: 360px;
      }
      .status {
        color: var(--muted);
        font-size: 12px;
      }
      .scene {
        position: relative;
        border: 1px solid var(--line);
        border-radius: 10px;
        overflow: auto;
        background: #202a30;
        max-height: 75vh;
        min-height: 320px;
      }
      .scene[data-bg="checker"] {
        background-color: #28333a;
        background-image:
          linear-gradient(45deg, #202a30 25%, transparent 25%),
          linear-gradient(-45deg, #202a30 25%, transparent 25%),
          linear-gradient(45deg, transparent 75%, #202a30 75%),
          linear-gradient(-45deg, transparent 75%, #202a30 75%);
        background-size: 24px 24px;
        background-position:
          0 0,
          0 12px,
          12px -12px,
          -12px 0;
      }
      .scene[data-bg="light"] {
        background: #dadeda;
      }
      .scene[data-bg="dark"] {
        background: #090d11;
      }
      #stage {
        position: relative;
        min-height: 380px;
        isolation: isolate;
      }
      .sprite {
        position: absolute;
        outline: 1px solid var(--track);
        transform-origin: top left;
      }
      .sprite canvas,
      .sprite img {
        display: block;
        width: 100%;
        height: 100%;
        image-rendering: pixelated;
      }
      .sprite .bounds {
        position: absolute;
        border: 1px dashed var(--track);
        pointer-events: none;
      }
      .sprite .origin {
        position: absolute;
        width: 9px;
        height: 9px;
        border: 1px solid var(--track);
        border-radius: 50%;
        transform: translate(-50%, -50%);
        pointer-events: none;
      }
      .sprite .tag {
        position: absolute;
        left: 0;
        top: -22px;
        white-space: nowrap;
        font-size: 11px;
        padding: 1px 5px;
        border-radius: 3px;
        color: #101618;
        background: var(--track);
        pointer-events: none;
      }
      .axis {
        position: absolute;
        pointer-events: none;
        background: #e9f2f155;
        z-index: -1;
      }
      .axis.x {
        height: 1px;
        left: 0;
        right: 0;
      }
      .axis.y {
        width: 1px;
        top: 0;
        bottom: 0;
      }
      .spread {
        margin: 15px 0 4px;
        display: flex;
        gap: 20px;
        align-items: center;
      }
      .spread label {
        flex: 1;
      }
      .ends {
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: var(--muted);
      }
      .table-wrap {
        overflow: auto;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
      }
      th {
        text-align: left;
        color: var(--muted);
        font-weight: 500;
      }
      th,
      td {
        padding: 10px;
        border-bottom: 1px solid var(--line);
        vertical-align: top;
      }
      td.numeric {
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
      }
      .name {
        max-width: 380px;
      }
      .filename {
        display: block;
        color: var(--muted);
        max-width: 350px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .swatch {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        margin-right: 6px;
      }
      .links a {
        margin-right: 10px;
      }
      a {
        color: var(--accent);
      }
      .note {
        margin: 10px 0;
        color: var(--muted);
        font-size: 12px;
      }
      .empty {
        padding: 45px 20px;
        max-width: 650px;
      }
      .footer {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        font-size: 12px;
        color: var(--muted);
        margin-top: 20px;
      }
      [hidden] {
        display: none !important;
      }
      @media (max-width: 700px) {
        main {
          padding: 14px;
        }
        header {
          align-items: start;
          flex-direction: column;
        }
        .controls > label {
          flex: 1;
          min-width: 140px;
        }
        select {
          max-width: 100%;
        }
        .spread {
          gap: 10px;
        }
        .panel {
          padding: 12px;
        }
        .footer {
          flex-direction: column;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <header>
        <div>
          <div class="eyebrow">PyGraphics / Animationen prüfen</div>
          <h1>Größen &amp; Positionen</h1>
          <p id="subtitle">Posen überlagern, Abweichungen erkennen und Animationen vergleichen.</p>
        </div>
        <span class="badge">Offline · vorhandene Dateien</span>
      </header>
      <section class="panel" aria-label="Auswahl">
        <div class="controls">
          <label>Pose A<select id="poseA"></select></label
          ><label
            >Pose B · optional<select id="poseB">
              <option value="">Keine zweite Pose</option>
            </select></label
          >
          <label
            >Vorschau<select id="source">
              <option value="sheet">Synchron · Spritesheet-Frames</option>
              <option value="gif">Original-GIFs</option>
            </select></label
          >
          <label
            >Größenmaßstab<select id="units">
              <option value="reference">Auf HD-Maßstab zurückgerechnet</option>
              <option value="native">Tatsächliche Pixelgrößen</option>
            </select></label
          >
          <label
            >Gemeinsamer Ursprung<select id="anchor">
              <option value="center">Leinwandmitte</option>
              <option value="bottom">Unten mittig</option>
              <option value="top">Oben links</option>
            </select></label
          >
        </div>
        <fieldset>
          <legend>Blickrichtung</legend>
          <div id="directions" class="directions"></div>
        </fieldset>
        <fieldset>
          <legend>Auflösungen</legend>
          <div id="variants" class="checks"></div>
        </fieldset>
        <fieldset>
          <legend>Raster / Frames · alle ausgewählten Animationen werden überlagert</legend>
          <div id="layouts" class="checks"></div>
        </fieldset>
      </section>
      <section class="panel" aria-label="Überlagerung">
        <div class="controls">
          <label
            >Synchronisierung<select id="sync">
              <option value="phase">Gleiche Animationsphase</option>
              <option value="frame">Gleiche Framenummer</option>
            </select></label
          >
          <label>Vorschau-FPS<select id="fps"></select></label>
          <label
            >Zoom <span id="zoomValue" class="readout">100 %</span
            ><input id="zoom" type="range" min="25" max="400" value="100" step="5"
          /></label>
          <label
            >Deckkraft <span id="opacityValue" class="readout">60 %</span
            ><input id="opacity" type="range" min="10" max="100" value="60"
          /></label>
          <label
            >Hintergrund<select id="background">
              <option value="checker">Schachbrett</option>
              <option value="dark">Dunkel</option>
              <option value="light">Hell</option>
            </select></label
          >
          <label class="check"><input id="outlines" type="checkbox" checked />Leinwand &amp; Ursprung</label
          ><label class="check"><input id="bounds" type="checkbox" checked />Sichtbarer Inhalt</label>
        </div>
        <div class="transport">
          <button id="play" type="button">Abspielen</button
          ><button id="previous" type="button" aria-label="Vorheriger Frame">← Frame</button
          ><button id="next" type="button" aria-label="Nächster Frame">Frame →</button
          ><label class="wide"
            ><span id="frameLabel">Frame 1</span
            ><input id="frame" type="range" min="0" max="15" value="0" step="1" /></label
          ><span id="status" class="status" role="status"></span>
        </div>
        <p id="modeNote" class="note"></p>
        <div id="viewport" class="scene" data-bg="checker">
          <div id="stage">
            <div id="axisX" class="axis x"></div>
            <div id="axisY" class="axis y"></div>
            <p id="empty" class="empty" hidden>
              Keine Animation für diese Auswahl vorhanden. Wähle eine andere Richtung, Auflösung oder ein
              anderes Raster.
            </p>
          </div>
        </div>
        <div class="spread">
          <span>Überlagert</span
          ><label
            ><span id="spreadValue" class="readout">Abstand 0 %</span
            ><input
              id="spread"
              aria-label="Überlagerungen auseinanderziehen"
              type="range"
              min="0"
              max="100"
              value="0" /></label
          ><span>Nebeneinander</span>
        </div>
        <div class="ends">
          <span>Gleicher Ursprung bei 0 %</span><span>Der Abstand verändert nur die Ansicht.</span>
        </div>
      </section>
      <section class="panel" aria-label="Messwerte und Ebenen">
        <div class="controls">
          <label>Referenz für Δ-Werte<select id="reference"></select></label
          ><button id="showAll" type="button">Alle Ebenen zeigen</button
          ><button id="hideAll" type="button">Alle Ebenen ausblenden</button
          ><span id="count" class="status"></span>
        </div>
        <p class="note">
          Δ X / Y vergleichen die linke obere Ecke des sichtbaren Inhalts mit der Referenz; Δ B / H dessen
          Größe. Werte gelten vor Zoom und Auseinanderziehen im gewählten Maßstab. Transparente Ränder bleiben
          erhalten.
        </p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Zeigen</th>
                <th>Pose / Auflösung / Raster</th>
                <th>Framegröße</th>
                <th>Frame</th>
                <th>Δ X / Y</th>
                <th>Δ B / H</th>
                <th>Dateien / Hinweise</th>
              </tr>
            </thead>
            <tbody id="tracks"></tbody>
          </table>
        </div>
      </section>
      <footer class="footer"><span id="created"></span><span id="poseLinks" class="links"></span></footer>
    </main>
    <script id="pose-data" type="application/json">
      __POSE_DATA__
    </script>
    <script>
      (() => {
        "use strict";
        const data = JSON.parse(document.getElementById("pose-data").textContent),
          $ = (id) => document.getElementById(id);
        const state = {
          direction: "N",
          tracks: [],
          position: 0,
          playing: false,
          last: null,
          epoch: 0,
          frames: 1,
          reference: "",
        };
        const colors = [
          "#bde59d",
          "#8fcbff",
          "#f2ae8e",
          "#d8abf5",
          "#ffda7c",
          "#80e0c2",
          "#f09bc2",
          "#aab9ff",
        ];
        function el(tag, text, className) {
          const n = document.createElement(tag);
          if (text !== undefined) n.textContent = text;
          if (className) n.className = className;
          return n;
        }
        function option(parent, value, label) {
          const n = el("option", label);
          n.value = value;
          parent.append(n);
        }
        function poses() {
          return [...new Set([$("poseA").value, $("poseB").value].filter((v) => v !== ""))].map((i) => ({
            index: Number(i),
            pose: data.poses[Number(i)],
          }));
        }
        function layoutKey(item, set) {
          return item && !item.missing && item.columns
            ? `${item.columns}×${item.rows} · ${item.logicalFrames} Frames`
            : `${set.frames} Frames`;
        }
        function choices(container) {
          return new Set([...container.querySelectorAll("input:checked")].map((n) => n.value));
        }
        function checkbox(container, value, label, checked, callback) {
          const l = el("label"),
            c = el("input");
          c.type = "checkbox";
          c.value = value;
          c.checked = checked;
          c.addEventListener("change", callback);
          l.append(c, document.createTextNode(label));
          container.append(l);
        }
        function buildDirections() {
          const available = new Set();
          for (const { pose } of poses())
            for (const set of pose.sets)
              if (!set.single) for (const d of Object.keys(set.directions)) available.add(d);
          if (!available.has(state.direction))
            state.direction = data.directions.find((d) => available.has(d)) || "?";
          $("directions").replaceChildren();
          for (const d of [...data.directions, ...(available.has("?") ? ["?"] : [])]) {
            const b = el("button", d === "?" ? "Ohne Richtung" : d);
            b.type = "button";
            b.disabled = !available.has(d);
            b.setAttribute("aria-pressed", String(d === state.direction));
            b.onclick = () => {
              state.direction = d;
              buildDirections();
              load();
            };
            $("directions").append(b);
          }
        }
        function buildLayouts() {
          const previous = choices($("layouts")),
            known = new Set([...$("layouts").querySelectorAll("input")].map(input => input.value)),
            had = $("layouts").children.length > 0,
            keys = new Set();
          for (const { pose } of poses())
            for (const set of pose.sets)
              if (!set.single)
                for (const tracks of Object.values(set.directions))
                  for (const item of Object.values(tracks)) if (!item.missing) keys.add(layoutKey(item, set));
          $("layouts").replaceChildren();
          for (const key of [...keys].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })))
            checkbox($("layouts"), key, key, !had || !known.has(key) || previous.has(key), load);
          if (had && !choices($("layouts")).size)
            for (const c of $("layouts").querySelectorAll("input")) c.checked = true;
        }
        function records() {
          const variants = choices($("variants")),
            layouts = choices($("layouts")),
            result = [];
          for (const { index, pose } of poses())
            pose.sets.forEach((set, s) => {
              if (set.single) return;
              const tracks = set.directions[state.direction] || {};
              const selectedLayout = Object.values(tracks).some(
                (item) => !item.missing && layouts.has(layoutKey(item, set)),
              );
              if (!selectedLayout && !layouts.has(`${set.frames} Frames`)) {
                const any = Object.values(set.directions).some((group) =>
                  Object.values(group).some((item) => !item.missing && layouts.has(layoutKey(item, set))),
                );
                if (!any) return;
              }
              for (const variant of data.variants) {
                if (!variants.has(variant.id)) continue;
                const item = tracks[variant.id];
                if (item && !item.missing && !layouts.has(layoutKey(item, set))) continue;
                result.push({
                  id: `${index}:${s}:${variant.id}`,
                  pose,
                  variant,
                  set,
                  item,
                  layout: item && !item.missing ? layoutKey(item, set) : `${set.frames} Frames`,
                });
              }
            });
          return result;
        }
        function playing(value) {
          state.playing = value;
          state.last = null;
          $("play").textContent = value ? "Pause" : "Abspielen";
        }
        function native() {
          return $("source").value === "gif";
        }
        function scaleOf(t) {
          return $("units").value === "reference" ? t.item.referenceWidth / t.item.width : 1;
        }
        function anchorOffset(w, h) {
          const a = $("anchor").value;
          return a === "top" ? [0, 0] : a === "bottom" ? [-w / 2, -h] : [-w / 2, -h / 2];
        }
        function frameOf(t) {
          return Math.min(
            t.item.logicalFrames - 1,
            $("sync").value === "phase"
              ? Math.floor((state.position / state.frames) * t.item.logicalFrames)
              : Math.floor(state.position) % t.item.logicalFrames,
          );
        }
        function measurement(t) {
          const b = t.item.bounds?.[frameOf(t)];
          if (!b) return null;
          const s = scaleOf(t),
            [x, y] = anchorOffset(t.item.width * s, t.item.height * s);
          return [x + b[0] * s, y + b[1] * s, (b[2] - b[0]) * s, (b[3] - b[1]) * s];
        }
        function fmt(n) {
          return (n > 0 ? "+" : "") + n.toFixed(1);
        }
        function layout() {
          const visible = state.tracks.filter((t) => t.loaded && t.check.checked),
            zoom = Number($("zoom").value) / 100,
            spread = Number($("spread").value) / 100;
          const maxW = Math.max(160, ...visible.map((t) => t.item.width * scaleOf(t) * zoom)),
            maxH = Math.max(240, ...visible.map((t) => t.item.height * scaleOf(t) * zoom));
          const distance = (maxW + 32) * spread,
            total = (visible.length - 1) * distance;
          const width = Math.max($("viewport").clientWidth, maxW + total + 80),
            height = Math.max(380, maxH + 80);
          $("stage").style.width = `${width}px`;
          $("stage").style.height = `${height}px`;
          const anchor = $("anchor").value,
            originX = anchor === "top" ? (width - maxW) / 2 : width / 2,
            originY = anchor === "top" ? 40 : anchor === "bottom" ? height - 40 : height / 2;
          $("axisX").style.top = `${originY}px`;
          $("axisY").style.left = `${originX}px`;
          for (const t of state.tracks) if (t.node) t.node.hidden = !visible.includes(t);
          visible.forEach((t, i) => {
            const factor = scaleOf(t) * zoom,
              w = t.item.width * factor,
              h = t.item.height * factor,
              [ax, ay] = anchorOffset(w, h);
            t.node.style.left = `${originX + ax + (i - (visible.length - 1) / 2) * distance}px`;
            t.node.style.top = `${originY + ay}px`;
            t.node.style.width = `${w}px`;
            t.node.style.height = `${h}px`;
            t.node.style.outlineWidth = $("outlines").checked ? "1px" : "0";
            t.picture.style.opacity = Number($("opacity").value) / 100;
            t.origin.hidden = !$("outlines").checked;
            t.origin.style.left = `${-ax}px`;
            t.origin.style.top = `${-ay}px`;
            t.tag.hidden = spread === 0;
            t.tag.textContent = `${t.pose.name} · ${t.variant.label} · ${t.layout}`;
          });
          $("empty").hidden = visible.length > 0;
          $("zoomValue").textContent = `${Math.round(zoom * 100)} %`;
          $("opacityValue").textContent = `${$("opacity").value} %`;
          $("spreadValue").textContent = `Abstand ${$("spread").value} %`;
          $("count").textContent = `${visible.length} sichtbare Ebenen · ${state.tracks.length} Einträge`;
          draw(true);
        }
        function draw(force = false) {
          const ref = state.tracks.find((t) => t.id === state.reference && t.loaded),
            reference = ref && !native() ? measurement(ref) : null;
          for (const t of state.tracks) {
            if (!t.loaded) continue;
            const frame = frameOf(t);
            if (!native() && (force || t.lastFrame !== frame)) {
              const { width: w, height: h, columns: c } = t.item;
              t.context.clearRect(0, 0, w, h);
              t.context.imageSmoothingEnabled = false;
              t.context.drawImage(t.image, (frame % c) * w, Math.floor(frame / c) * h, w, h, 0, 0, w, h);
              t.lastFrame = frame;
            }
            t.frameCell.textContent = native() ? "Original-GIF" : `${frame + 1} / ${t.item.logicalFrames}`;
            const b = t.item.bounds?.[frame],
              factor = (scaleOf(t) * Number($("zoom").value)) / 100;
            t.bounds.hidden = native() || !b || !$("bounds").checked;
            if (!t.bounds.hidden) {
              t.bounds.style.left = `${b[0] * factor}px`;
              t.bounds.style.top = `${b[1] * factor}px`;
              t.bounds.style.width = `${(b[2] - b[0]) * factor}px`;
              t.bounds.style.height = `${(b[3] - b[1]) * factor}px`;
            }
            const m = !native() ? measurement(t) : null;
            t.deltaPos.textContent =
              m && reference ? `${fmt(m[0] - reference[0])} / ${fmt(m[1] - reference[1])}` : "—";
            t.deltaSize.textContent =
              m && reference ? `${fmt(m[2] - reference[2])} / ${fmt(m[3] - reference[3])}` : "—";
          }
          const displayedFrame = Math.floor(state.position) % state.frames;
          $("frame").value = displayedFrame;
          $("frameLabel").textContent =
            `Referenzzyklus: Frame ${displayedFrame + 1} / ${state.frames}`;
        }
        function addRow(t, index) {
          const tr = el("tr"),
            enabled = el("td"),
            check = el("input");
          check.type = "checkbox";
          check.checked = true;
          check.setAttribute("aria-label", `${t.pose.name}, ${t.variant.label}, ${t.layout} anzeigen`);
          check.onchange = layout;
          enabled.append(check);
          t.check = check;
          const name = el("td", undefined, "name"),
            swatch = el("span", undefined, "swatch");
          t.color = colors[index % colors.length];
          swatch.style.background = t.color;
          name.append(swatch, document.createTextNode(`${t.pose.name} · ${t.variant.label} · ${t.layout}`));
          name.append(el("span", t.set.family.replace("{Richtung}", state.direction), "filename"));
          const size = el("td", "—", "numeric");
          t.frameCell = el("td", "—", "numeric");
          t.deltaPos = el("td", "—", "numeric");
          t.deltaSize = el("td", "—", "numeric");
          t.notes = el("td", undefined, "links");
          tr.append(enabled, name, size, t.frameCell, t.deltaPos, t.deltaSize, t.notes);
          $("tracks").append(tr);
          if (!t.item || t.item.missing) {
            check.disabled = true;
            check.checked = false;
            t.notes.textContent = t.item?.reason || "Diese Richtung fehlt.";
            return false;
          }
          size.textContent = `${t.item.width} × ${t.item.height} px`;
          if (t.item.sheet) {
            const a = el("a", "PNG");
            a.href = t.item.sheet;
            a.target = "_blank";
            a.rel = "noopener";
            t.notes.append(a);
          }
          if (t.item.gif) {
            const a = el("a", "GIF");
            a.href = t.item.gif;
            a.target = "_blank";
            a.rel = "noopener";
            t.notes.append(a);
          }
          if (!t.item.hasHDReference)
            t.notes.append(el("span", "HD fehlt; größte vorhandene Variante als Größenbezug. "));
          if (!t.item.gif) t.notes.append(el("span", "GIF fehlt. "));
          return true;
        }
        async function load() {
          const epoch = ++state.epoch;
          document.body.dataset.ready = "false";
          playing(false);
          state.position = 0;
          state.tracks = [];
          $("tracks").replaceChildren();
          $("stage")
            .querySelectorAll(".sprite")
            .forEach((n) => n.remove());
          $("status").textContent = "Animationen laden …";
          for (const id of ["play", "previous", "next", "frame", "fps", "sync"]) $(id).disabled = true;
          const chosen = records();
          state.tracks = chosen;
          const loads = [];
          chosen.forEach((t, index) => {
            if (!addRow(t, index)) return;
            const url = native() ? t.item.gif : t.item.sheet;
            if (!url) {
              t.check.disabled = true;
              t.check.checked = false;
              t.notes.append(
                el(
                  "span",
                  native()
                    ? "Kein GIF vorhanden."
                    : "Für Synchronregler fehlt das Spritesheet; Original-GIFs wählen.",
                ),
              );
              return;
            }
            t.node = el("div", undefined, "sprite");
            t.node.dataset.track = t.id;
            t.node.style.setProperty("--track", t.color);
            t.bounds = el("div", undefined, "bounds");
            t.origin = el("div", undefined, "origin");
            t.tag = el("span", undefined, "tag");
            const img = new Image();
            img.alt = `${t.pose.name}, ${t.variant.label}, ${state.direction}, ${t.layout}`;
            if (native()) {
              t.picture = img;
            } else {
              t.picture = el("canvas");
              t.picture.width = t.item.width;
              t.picture.height = t.item.height;
              t.picture.setAttribute("aria-label", img.alt);
              t.context = t.picture.getContext("2d");
            }
            t.node.append(t.picture, t.bounds, t.origin, t.tag);
            $("stage").append(t.node);
            loads.push(
              new Promise((resolve) => {
                img.onload = () => {
                  if (epoch === state.epoch) {
                    const expectedW = native() ? t.item.width : t.item.width * t.item.columns,
                      expectedH = native() ? t.item.height : t.item.height * t.item.rows;
                    if (
                      img.naturalWidth === expectedW &&
                      img.naturalHeight === expectedH &&
                      (native() || t.context)
                    ) {
                      t.image = img;
                      t.loaded = true;
                    } else {
                      t.notes.append(el("span", "Bildmaße geändert; HTML neu erstellen."));
                      t.check.checked = false;
                      t.check.disabled = true;
                    }
                  }
                  resolve();
                };
                img.onerror = () => {
                  if (epoch === state.epoch) {
                    t.notes.append(el("span", "Datei fehlt oder ist nicht lesbar."));
                    t.check.checked = false;
                    t.check.disabled = true;
                  }
                  resolve();
                };
                img.src = url;
              }),
            );
          });
          await Promise.all(loads);
          if (epoch !== state.epoch) return;
          const ready = chosen.filter((t) => t.loaded);
          state.frames = Math.max(1, ...ready.map((t) => t.item.logicalFrames));
          $("frame").max = state.frames - 1;
          for (const id of ["play", "previous", "next", "frame", "fps", "sync"])
            $(id).disabled = native() || !ready.length;
          $("reference").replaceChildren();
          for (const t of ready)
            option($("reference"), t.id, `${t.pose.name} · ${t.variant.label} · ${t.layout}`);
          state.reference = ready.some((t) => t.id === state.reference)
            ? state.reference
            : ready[0]?.id || "";
          $("reference").value = state.reference;
          $("reference").disabled = native() || !ready.length;
          $("bounds").disabled = native();
          $("status").textContent = `${ready.length} / ${chosen.length} geladen · ${state.direction}`;
          $("modeNote").textContent = native()
            ? "Original-GIFs zeigen die exportierten Farben und die gespeicherte Bildrate. Für gemeinsame FPS, Pause und Einzelbildschritte „Synchron“ wählen."
            : "Synchronvorschau aus vorhandenen PNG-Spritesheets, einschließlich Leerzellen. Gleiche Phase gleicht unterschiedliche Framezahlen an; die gewählten FPS bestimmen den längsten Zyklus. GIF-Farben und GIF-Transparenz separat unter „Original-GIFs“ prüfen.";
          $("poseLinks").replaceChildren();
          for (const { pose } of poses()) {
            const a = el("a", `${pose.name}: Auflösungen`);
            a.href = pose.comparison;
            $("poseLinks").append(a);
          }
          document.body.dataset.ready = "true";
          layout();
        }
        function changePose() {
          buildDirections();
          buildLayouts();
          load();
        }
        function step(delta) {
          playing(false);
          state.position = (Math.floor(state.position) + delta + state.frames) % state.frames;
          draw();
        }
        function tick(now) {
          const elapsed = state.last === null ? 0 : Math.min(250, now - state.last);
          state.last = now;
          if (state.playing && !native() && !document.hidden) {
            state.position += (elapsed * Number($("fps").value)) / 1000;
            if ($("sync").value === "phase") state.position %= state.frames;
            draw();
          }
          requestAnimationFrame(tick);
        }
        data.poses.forEach((pose, i) => {
          option($("poseA"), i, pose.name);
          option($("poseB"), i, pose.name);
        });
        for (const variant of data.variants)
          checkbox($("variants"), variant.id, variant.label, variant.id !== "comic_high", load);
        for (const fps of data.fpsChoices) option($("fps"), fps, `${fps} FPS`);
        $("fps").value = data.fps;
        $("subtitle").textContent =
          `${data.title} · ${data.poses.length} Posen · Gemeinsam prüfen, einzeln nachmessen.`;
        $("created").textContent = `Erstellt ${new Date(data.created).toLocaleString("de-DE")}`;
        $("poseA").onchange = changePose;
        $("poseB").onchange = changePose;
        $("source").onchange = load;
        $("reference").onchange = () => {
          state.reference = $("reference").value;
          draw();
        };
        $("play").onclick = () => playing(!state.playing);
        $("previous").onclick = () => step(-1);
        $("next").onclick = () => step(1);
        $("frame").oninput = () => {
          playing(false);
          state.position = Number($("frame").value);
          draw();
        };
        $("fps").onchange = () => {
          state.last = null;
        };
        $("sync").onchange = () => {
          state.position = 0;
          draw();
        };
        for (const id of ["units", "anchor", "zoom", "opacity", "spread", "outlines", "bounds"])
          $(id).addEventListener("input", layout);
        $("background").onchange = () => {
          $("viewport").dataset.bg = $("background").value;
        };
        $("showAll").onclick = () => {
          for (const t of state.tracks) if (!t.check.disabled) t.check.checked = true;
          layout();
        };
        $("hideAll").onclick = () => {
          for (const t of state.tracks) t.check.checked = false;
          layout();
        };
        window.addEventListener("resize", layout);
        document.addEventListener("visibilitychange", () => {
          state.last = null;
        });
        document.addEventListener("keydown", (event) => {
          if (
            event.target.closest("input,select,button,a") ||
            native() ||
            event.ctrlKey ||
            event.metaKey ||
            event.altKey
          )
            return;
          if (event.code === "Space") {
            event.preventDefault();
            if (!$("play").disabled) playing(!state.playing);
          } else if (event.code === "ArrowLeft") {
            event.preventDefault();
            step(-1);
          } else if (event.code === "ArrowRight") {
            event.preventDefault();
            step(1);
          }
        });
        if (data.poses.length) changePose();
        else {
          $("empty").hidden = false;
          $("status").textContent = "Keine Posen vorhanden.";
        }
        requestAnimationFrame(tick);
      })();
    </script>
  </body>
</html>
'''
