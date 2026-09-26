#!/usr/bin/env python3
"""Gemeinsamer Offline-Vergleich der fünf Auflösungen; GIF-Code bleibt PyImgGif."""
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


VARIANTS = (
    ("comic_high", "Comic High · HD"),
    ("comic_mid", "Comic Mittel"),
    ("comic_low", "Comic Low"),
    ("pixel_high", "Pixel High"),
    ("pixel_low", "Pixel Low"),
)
DIRECTIONS = ("N", "NO", "O", "SO", "S", "SW", "W", "NW")
# Großschreibung ist absichtlich relevant: das abschließende _o ist keine Richtung O.
DIRECTION_PATTERN = re.compile(r"(?<![^_])(NO|NW|SO|SW|N|O|S|W)(?=_|$)")


def identify_direction(stem: str) -> tuple[str, str]:
    match = DIRECTION_PATTERN.search(stem)
    if match is None:
        return stem, "?"
    return stem[:match.start()] + "{Richtung}" + stem[match.end():], match[0]


def build_comparison(root: Path, high: Path, sheets, fps: int, *, overwrite: bool = False) -> int:
    output = root / "aufloesungsvergleich.html"
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError("Vergleichsausgabe ist ein Link oder keine reguläre Datei.")
    if output.exists() and not overwrite:
        output_policy.should_write(output)
        return 0
    groups = {}
    errors = 0
    for sheet in sheets:
        family, direction = identify_direction(sheet.source.stem)
        key = (sheet.folder, family)
        group = groups.setdefault(key, {
            "folder": sheet.folder, "family": family,
            "frames": sheet.grid[0] * sheet.grid[1], "single": sheet.single, "directions": {},
        })
        if direction in group["directions"]:
            raise ValueError(f"Mehrdeutige Vergleichszuordnung: {sheet.source}")
        tracks = {}
        group["directions"][direction] = tracks
        gif_name = f"{sheet.source.stem}_{fps}fps.gif"
        for variant, _ in VARIANTS:
            directory = high / sheet.folder if variant == "comic_high" else root / variant / sheet.folder
            path = directory / sheet.source.name
            if not path.exists():
                tracks[variant] = {"missing": True, "reason": "Für diese Variante fehlt die PNG-Datei."}
                continue
            try:
                tracks[variant] = gif_tools.read_sheet_preview(
                    path, output, fps, gif_tools.Grid(*sheet.grid, "Pipeline"), directory / gif_name,
                    single_image=sheet.single)
            except (OSError, ValueError, SyntaxError, MemoryError,
                    gif_tools.Image.DecompressionBombError,
                    gif_tools.Image.DecompressionBombWarning) as exc:
                errors += 1
                tracks[variant] = {"missing": True, "reason": str(exc)}
                print(f"VERGLEICH: {variant}/{sheet.folder}/{path.name}: {exc}", file=sys.stderr)
    return write_comparison(root, list(groups.values()), fps, errors, overwrite=overwrite)


def write_comparison(root: Path, groups: list[dict], fps: int, errors: int = 0, *,
                     overwrite: bool = False) -> int:
    output = root / "aufloesungsvergleich.html"
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError("Vergleichsausgabe ist ein Link oder keine reguläre Datei.")
    if not output_policy.should_write(output, overwrite=overwrite):
        return 1 if errors else 0
    payload = {
        "title": root.name, "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "fps": fps, "fpsChoices": gif_tools.FPS_CHOICES,
        "variants": [{"id": key, "label": label} for key, label in VARIANTS],
        "directions": list(DIRECTIONS), "sets": groups,
    }
    html = HTML_TEMPLATE.replace("__COMPARISON_DATA__", gif_tools.script_safe_json(payload))
    root.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".aufloesungsvergleich-", suffix=".html", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(html)
        gif_tools.validate_html_output(output)
        os.replace(name, output)
    finally:
        Path(name).unlink(missing_ok=True)
    if overwrite:
        gif_tools.cleanup_legacy_html_assets(output)
    print(f"Auflösungsvergleich: {output} (vorhandene Bilder verlinkt)", flush=True)
    return 1 if errors else 0


HTML_TEMPLATE = r'''<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PyGraphics · Auflösungsvergleich</title>
<style>
:root{color-scheme:dark;--bg:#151719;--panel:#202326;--line:#3b4045;--text:#eef0f2;--muted:#afb6bd;--accent:#c5dea0;--display:224px}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.55 system-ui,sans-serif}
main{max-width:1800px;padding:28px 32px 40px;margin:auto}header{display:flex;gap:20px;justify-content:space-between;align-items:center;margin-bottom:24px}
.eyebrow{font-size:11px;letter-spacing:1.8px;text-transform:uppercase;color:var(--accent);font-weight:700}h1{font-size:29px;letter-spacing:-.8px;line-height:1.2;margin:6px 0 8px}p{margin:0;color:var(--muted)}.offline{border:1px solid var(--line);border-radius:20px;padding:6px 12px;white-space:nowrap;font-size:12px}
.controls{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;display:flex;gap:14px 24px;align-items:end;flex-wrap:wrap}
.controls>label{max-width:100%;min-width:0}
label{display:flex;flex-direction:column;gap:6px;color:var(--muted);font-size:12px}select,button{font:inherit;color:var(--text);background:#292d31;border:1px solid #50565c;border-radius:6px;padding:8px 11px;min-height:38px}button{cursor:pointer}button:hover:not(:disabled){border-color:var(--accent)}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:3px}button:disabled{opacity:.4;cursor:default}select{max-width:420px;font-size:13px}input{accent-color:var(--accent)}input[type=range]{width:100%;cursor:pointer}
.directions{display:flex;gap:5px;flex-wrap:wrap}.directions button{min-width:38px;padding:7px 8px}.directions [aria-pressed=true]{background:var(--accent);color:#182016;border-color:var(--accent);font-weight:750}.control-label{font-size:12px;color:var(--muted);margin-bottom:6px}.setting{min-width:155px}.check{flex-direction:row;align-items:center;min-height:38px;color:var(--text)}
.transport{margin:16px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}.transport>input{max-width:400px;min-width:150px;flex:1}.transport>span{font-variant-numeric:tabular-nums;color:var(--muted);min-width:95px}.transport .status{margin-left:auto;font-size:12px}.play{background:var(--accent);color:#182016;border-color:var(--accent);font-weight:700}
.comparison-scroll{overflow-x:auto;padding-bottom:14px}.comparison{display:grid;grid-template-columns:repeat(5,minmax(248px,1fr));gap:14px;min-width:max(1296px,calc(5 * (var(--display) + 26px) + 56px))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;min-width:0}.card-head{padding:15px 14px 12px;min-height:90px}.card-head h2{font-size:15px;margin:0 0 5px;font-weight:650}.resolution{font-size:12px;color:var(--accent);font-variant-numeric:tabular-nums}.badge{color:var(--muted);font-size:11px;margin-left:6px}
.stage{height:calc(var(--display) + 32px);display:flex;align-items:center;justify-content:center;position:relative;border-top:1px solid var(--line);border-bottom:1px solid var(--line);background-color:#4b4b4b;background-image:linear-gradient(45deg,#575757 25%,transparent 25%),linear-gradient(-45deg,#575757 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#575757 75%),linear-gradient(-45deg,transparent 75%,#575757 75%);background-size:20px 20px;background-position:0 0,0 10px,10px -10px,-10px 0}
canvas{display:block;image-rendering:pixelated}body[data-smooth=true] canvas{image-rendering:auto}body[data-background=light] .stage{background:#f7f7f7}body[data-background=gray] .stage{background:#808080}body[data-background=dark] .stage{background:#111}.missing{padding:24px;color:#e8c894;text-align:center;font-size:12px;max-width:260px}.card-foot{padding:12px 14px;min-height:92px;display:flex;flex-direction:column;gap:6px}.card-foot a{color:var(--accent);font-size:12px}.filename{font-size:10px;color:var(--muted);overflow-wrap:anywhere}.note{font-size:11px;color:#e8c894}.frame-info{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums}
footer{display:flex;justify-content:space-between;gap:20px;margin-top:15px;padding-top:18px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}footer p{max-width:900px}#created{white-space:nowrap}#empty{padding:24px;border:1px solid var(--line);border-radius:8px;color:#e8c894}
@media(max-width:700px){main{padding:20px 16px}header{align-items:start}.offline{display:none}h1{font-size:25px}.controls{gap:16px}select{max-width:100%}.transport .status{flex-basis:100%;margin-left:0}footer{flex-direction:column}}
</style>
</head>
<body data-background="checker" data-smooth="false">
<main>
<header><div><div class="eyebrow">PyGraphics · visueller Test</div><h1>Auflösung &amp; Farbe</h1><p id="subtitle">Fünf Varianten. Gleiche Anzeigegröße. Gemeinsame Wiedergabe.</p></div><span class="offline">Offline nutzbar</span></header>
<section class="controls" aria-label="Vergleich auswählen">
<label>Einzelbild / Animation<select id="sequence" aria-label="Einzelbild oder Animation und Framezahl"></select></label>
<label>Vorschau-FPS<select id="fps" aria-label="Gemeinsame Vorschau-FPS"></select></label>
<div><div class="control-label">Blickrichtung</div><div id="directions" class="directions" role="group" aria-label="Blickrichtung"></div></div>
<label class="setting">Anzeigegröße: <span id="sizeLabel">224 px</span><input id="size" type="range" min="128" max="512" step="16" value="224"></label>
<label>Hintergrund<select id="background"><option value="checker">Schachbrett</option><option value="light">Hell</option><option value="gray">Neutralgrau</option><option value="dark">Dunkel</option></select></label>
<label class="check"><input type="checkbox" id="smooth">Vorschau glätten</label>
</section>
<section class="transport" aria-label="Gemeinsame Wiedergabe">
<button id="play" class="play" disabled>Abspielen</button><button id="previous" aria-label="Vorheriger Frame" disabled>←</button><button id="next" aria-label="Nächster Frame" disabled>→</button>
<input id="frame" type="range" min="0" max="15" value="0" step="1" aria-label="Gemeinsamer Frame" disabled><span id="frameLabel">Frame 1 / 16</span>
<span id="status" class="status" role="status" aria-live="polite">Vorschau wird geladen …</span>
</section>
<div id="empty" hidden>Keine Bilder für den Vergleich vorhanden.</div>
<div class="comparison-scroll"><section id="comparison" class="comparison" aria-label="Alle Auflösungen nebeneinander"></section></div>
<footer><p>Alle Ansichten zeigen die vorhandenen PNG-Einzelbilder oder Spritesheets auf derselben Anzeigegröße. GIF-Farbänderungen werden hier nicht dargestellt. Die Pixelmaße unter dem Titel sind die tatsächlichen Auflösungen. Die Vorschau verändert keine Datei. Beim Kopieren den Aktionsordner mit HTML und den Bild-Unterordnern zusammenhalten. Fehlende oder abweichende Bilder werden an der jeweiligen Variante angezeigt.</p><span id="created"></span></footer>
</main>
<script id="comparison-data" type="application/json">__COMPARISON_DATA__</script>
<script>
(() => {
  "use strict";
  const data = JSON.parse(document.getElementById("comparison-data").textContent);
  const $ = id => document.getElementById(id);
  const state = {set:0,direction:"N",position:0,fps:data.fps,playing:!matchMedia("(prefers-reduced-motion: reduce)").matches,last:null,tracks:[],epoch:0,ready:false};
  function element(tag, className, text) { const node=document.createElement(tag); if(className)node.className=className; if(text!==undefined)node.textContent=text; return node; }
  function group() { return data.sets[state.set]; }
  function animated() { return group()?.frames>1; }
  function displaySize() { return Number($("size").value); }
  function setPlaying(playing) { state.playing=playing; state.last=null; $("play").textContent=animated()&&playing?"Pause":"Abspielen"; }
  function updateStatus() { const sync=state.tracks.some(track=>track.loaded&&!track.native);$("status").textContent=`${state.tracks.filter(track=>track.loaded).length} / 5 Varianten · ${state.direction==="?"?"ohne Richtung":state.direction} · ${animated()?(sync?`${state.fps} FPS · synchron`:"Original-GIFs · gespeicherte Bildrate"):"Einzelbild"}`; }
  function resize(track) { const side=displaySize(),max=Math.max(track.item.width,track.item.height); track.canvas.style.width=`${side*track.item.width/max}px`; track.canvas.style.height=`${side*track.item.height/max}px`; }
  function draw(force=false) {
    if(!group())return;
    for(const track of state.tracks){
      if(!track.loaded||track.native)continue;
      const index=Math.min(group().frames-1,Math.floor(state.position)),ctx=track.context;
      if(track.lastFrame===index&&!force)continue;track.lastFrame=index;
      const {width,height,columns}=track.item;
      ctx.clearRect(0,0,width,height);
      ctx.imageSmoothingEnabled=$("smooth").checked;
      ctx.drawImage(track.picture,(index%columns)*width,Math.floor(index/columns)*height,width,height,0,0,width,height);
      track.frameInfo.textContent=animated()?`PNG-Frame ${index+1} / ${track.item.logicalFrames}`:"Einzelbild";
    }
    const frame=Math.min(group().frames-1,Math.floor(state.position));
    $("frame").value=frame;$("frameLabel").textContent=animated()?`Frame ${frame+1} / ${group().frames}`:"Einzelbild";
  }
  function makeCard(variant,item){
    const card=element("article","card"),head=element("div","card-head"),stage=element("div","stage"),foot=element("div","card-foot");
    card.dataset.variant=variant.id;head.append(element("h2","",variant.label));
    const resolution=element("div","resolution",item&&!item.missing?`${item.width} × ${item.height} px`:"Keine Vorschau");
    head.append(resolution);card.append(head,stage,foot);$("comparison").append(card);
    if(!item||item.missing){stage.append(element("p","missing",item?.reason||"Für diese Richtung fehlt das Bild."));return null;}
    resolution.append(element("span","badge",`${(item.bytes/1024).toFixed(1)} KiB`));
    if(!item.sheet&&item.gif){
      const picture=element("img");picture.src=item.gif;picture.alt=variant.label+", "+state.direction;stage.append(picture);
      const link=element("a","","Original-GIF öffnen");link.href=item.gif;
      foot.append(element("p","note","Original-GIF mit gespeicherter Bildrate; Spritesheet für FPS- und Einzelbildsteuerung fehlt."),link);
      const track={item,canvas:picture,native:true,loaded:true};resize(track);return track;
    }
    const canvas=element("canvas");canvas.width=item.width;canvas.height=item.height;canvas.setAttribute("aria-label",variant.label+", "+state.direction);stage.append(canvas);
    const frameInfo=element("div","frame-info","Wird geladen …");
    const download=element("a","",animated()?"Spritesheet herunterladen":"PNG herunterladen");download.href=item.sheet;download.download=item.name;
    foot.append(frameInfo,download,element("span","filename",item.name));
    if(item.gif){const gif=element("a","original-gif","Original-GIF herunterladen");gif.href=item.gif;gif.download=item.gifName;foot.append(gif);}
    for(const note of item.notes)foot.append(element("span","note",note));
    const track={item,canvas,context:canvas.getContext("2d"),frameInfo,stage,picture:null,loaded:false,lastFrame:-1};resize(track);return track;
  }
  function directions(){
    $("directions").replaceChildren();
    const names=[...data.directions];if(group().directions["?"])names.push("?");
    for(const name of names){
      const button=element("button","",name==="?"?"Ohne Richtung":name);button.type="button";button.dataset.direction=name;
      button.disabled=!group().directions[name];button.setAttribute("aria-pressed",String(name===state.direction));
      button.addEventListener("click",()=>{state.direction=name;loadSelection();});$("directions").append(button);
    }
  }
  async function loadSelection(){
    const epoch=++state.epoch;state.ready=false;state.last=null;state.position=0;state.tracks=[];
    document.body.dataset.ready="false";$("comparison").dataset.ready="false";
    if(!group().directions[state.direction])state.direction=data.directions.find(name=>group().directions[name])||Object.keys(group().directions)[0];
    directions();$("comparison").replaceChildren();$("frame").max=group().frames-1;$("status").textContent="Vorschau wird geladen …";
    for(const name of ["play","previous","next","frame","fps"])$(name).disabled=true;
    setPlaying(state.playing);
    const items=group().directions[state.direction]||{};
    for(const variant of data.variants){const track=makeCard(variant,items[variant.id]);if(track)state.tracks.push(track);}
    const tracks=state.tracks;
    await Promise.all(tracks.map(async track=>{
      if(track.native)return;
      try{
        if(!track.context)throw Error("Canvas wird nicht unterstützt.");
        const picture=await new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(Error("PNG nicht lesbar."));img.src=track.item.sheet;});
        if(picture.naturalWidth!==track.item.width*track.item.columns||picture.naturalHeight!==track.item.height*track.item.rows)throw Error("PNG wurde geändert. Vergleichsseite neu erstellen.");
        if(epoch!==state.epoch)return;track.picture=picture;track.loaded=true;
      }catch(error){if(epoch===state.epoch){track.stage.replaceChildren(element("p","missing",error.message));track.frameInfo.textContent="Ladefehler";}}
    }));
    if(epoch!==state.epoch)return;
    const loaded=tracks.filter(track=>track.loaded&&!track.native).length;state.ready=loaded>0;state.last=null;
    for(const name of ["play","previous","next","frame","fps"])$(name).disabled=!state.ready||!animated();
    updateStatus();
    $("comparison").dataset.ready="true";document.body.dataset.ready="true";draw();
  }
  function step(delta){if(!state.ready||!animated())return;setPlaying(false);state.position=(Math.floor(state.position)+delta+group().frames)%group().frames;draw();}
  function tick(now){
    if(state.last===null)state.last=now;
    const elapsed=Math.max(0,now-state.last);state.last=now;
    if(state.ready&&animated()&&state.playing&&!document.hidden){state.position=(state.position+elapsed*state.fps/1000)%group().frames;draw();}
    requestAnimationFrame(tick);
  }
  $("subtitle").textContent=`${data.title} · Fünf Varianten in gleicher Anzeigegröße.`;
  $("created").textContent=`Erstellt ${new Date(data.created).toLocaleString("de-DE")}`;
  for(const fps of data.fpsChoices){const option=element("option","",`${fps} FPS`);option.value=fps;$("fps").append(option);}$("fps").value=state.fps;
  $("fps").addEventListener("change",()=>{state.fps=Number($("fps").value);state.last=null;if(state.ready)updateStatus();});
  if(!data.sets.length){$("empty").hidden=false;$("status").textContent="Keine PNGs verfügbar.";return;}
  data.sets.forEach((set,index)=>{const option=element("option","",`${set.frames>1?`${set.frames} Frames`:"Einzelbild"} · ${set.family.replace("{Richtung}","…")}`);option.value=index;$("sequence").append(option);});
  $("sequence").addEventListener("change",()=>{state.set=Number($("sequence").value);loadSelection();});
  $("play").addEventListener("click",()=>setPlaying(!state.playing));
  $("previous").addEventListener("click",()=>step(-1));$("next").addEventListener("click",()=>step(1));
  $("frame").addEventListener("input",()=>{setPlaying(false);state.position=Number($("frame").value);draw();});
  $("size").addEventListener("input",()=>{document.documentElement.style.setProperty("--display",`${displaySize()}px`);$("sizeLabel").textContent=`${displaySize()} px`;for(const track of state.tracks)resize(track);});
  $("background").addEventListener("change",()=>{document.body.dataset.background=$("background").value;});
  $("smooth").addEventListener("change",()=>{document.body.dataset.smooth=String($("smooth").checked);draw(true);});
  document.addEventListener("visibilitychange",()=>{state.last=null;});
  document.addEventListener("keydown",event=>{if(event.target.closest("input,select,button,a")||event.ctrlKey||event.metaKey||event.altKey)return;if(event.code==="Space"){event.preventDefault();if(state.ready&&animated())setPlaying(!state.playing);}else if(event.code==="ArrowLeft"){event.preventDefault();step(-1);}else if(event.code==="ArrowRight"){event.preventDefault();step(1);}});
  setPlaying(state.playing);loadSelection().catch(error=>{$("status").textContent=error.message;});requestAnimationFrame(tick);
})();
</script>
</body>
</html>
'''
