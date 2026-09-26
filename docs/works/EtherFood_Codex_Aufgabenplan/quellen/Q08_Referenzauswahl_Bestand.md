# Q08 — Referenzauswahl Bestand

Original: `allsummary(1).md`. SHA-256 der vollständigen Upload-Datei: `55bb37c2fb9909384a89d3ac4c7e4b011f1fa8d0319243c04e436fe567570c69`.

Relevanz: reference_files: feste Richtungsprüfung im existierenden Code.

Die Zeilennummern in den folgenden Blöcken beziehen sich auf die Originaldatei. Der Text ist ein Quellenbeleg, keine neu erteilte Arbeitsanweisung.

## Originalzeilen 9028–9064

````text
L9028: def reference_files(root, explicit, grid, *, single_images=False):
L9029:     if explicit:
L9030:         folder = explicit.expanduser().absolute()
L9031:         paths = pngs(folder)
L9032:         stand = [p for p in paths if "_stand_" in p.name.lower()]
L9033:         paths = stand or paths
L9034:     else:
L9035:         base = root / "stand" / "comic_high"
L9036:         candidates = [base, root / "stand", root] if single_images else [base / "spritesheet-fram16" / "PixelEng", base, root]
L9037:         if not single_images and root.name == "comic_high" and root.parent.name == "stand":
L9038:             candidates.insert(0, root / "spritesheet-fram16" / "PixelEng")
L9039:         paths = []
L9040:         for folder in candidates:
L9041:             paths = [p for p in pngs(folder) if "_stand_" in p.name.lower()]
L9042:             if paths:
L9043:                 break
L9044:     sheets = [p for p in paths if "spritesheet" in p.stem.lower()] if not single_images else []
L9045:     paths = sheets or paths
L9046:     by_direction = {}
L9047:     for path in paths:
L9048:         match = DIRECTION.search(path.stem)
L9049:         if not match:
L9050:             continue
L9051:         direction = match[1].upper()
L9052:         if direction in by_direction:
L9053:             raise ValueError(f"Mehrere Stand-Referenzen für {direction}; --reference auf eindeutigen Ordner setzen.")
L9054:         with color.load_png(path) as image:
L9055:             layout = single_grid(path, image.size) if single_images else infer_grid(path, image.size, grid)
L9056:             by_direction[direction] = (path, direction, layout)
L9057:     missing = set(color.DIRECTIONS) - by_direction.keys()
L9058:     if missing:
L9059:         raise ValueError(f"Stand-Referenz unvollständig ({', '.join(sorted(missing))}); --reference ORDNER angeben.")
L9060:     return [by_direction[d] for d in color.DIRECTIONS]
L9061: 
L9062: 
L9063: def parse_grid(value):
L9064:     match = re.fullmatch(r"([1-9][0-9]*)[xX×]([1-9][0-9]*)", value)
````
