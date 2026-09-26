# Q09 — Masken Profilregeln Bestand

Original: `allsummary(1).md`. SHA-256 der vollständigen Upload-Datei: `55bb37c2fb9909384a89d3ac4c7e4b011f1fa8d0319243c04e436fe567570c69`.

Relevanz: Feste acht Profilreferenzen, Maskenmetadaten und dokumentierter offener Sichtstatus; historischer Fortführungstext gekennzeichnet.

Die Zeilennummern in den folgenden Blöcken beziehen sich auf die Originaldatei. Der Text ist ein Quellenbeleg, keine neu erteilte Arbeitsanweisung.

## Originalzeilen 9636–9805

````text
L9636: ## 📝 PyImgFixedColors.py — ./PiplineToos/PyImgFixedColors.py
L9637: 
L9638: """Exakte sRGB-Paletten und Materialfarbreihen; keine Mischung oder LUT-Interpolation.
L9639: 
L9640: Labelmasken sind 8-Bit-L/P-PNGs. Ihre Pixelwerte sind Material-IDs, keine Farben.
L9641: Raster und Quellhash binden jede Maske an ein konkretes Original-Sheet.
L9642: """
L9643: from __future__ import annotations
L9644: 
L9645: from functools import lru_cache
L9646: import json
L9647: import math
L9648: from pathlib import Path
L9649: import re
L9650: import warnings
L9651: 
L9652: from PIL import Image, ImageChops, PngImagePlugin
L9653: 
L9654: import PyImgColorMatch as color
L9655: 
L9656: FIXED_FORMAT = "pyimg-fixed-palette"
L9657: MATERIAL_FORMAT = "pyimg-material-colors"
L9658: DEFINITIONS_FORMAT = "pyimg-material-definitions"
L9659: VERSION = 1
L9660: FIXED_METHOD = "Lab_D65_nearest_palette_v1"
L9661: MATERIAL_METHOD = "Lab_D65_nearest_material_lightness_v1"
L9662: MASK_VERSION = "pyimg_mask_version"
L9663: MASK_GRID = "pyimg_grid"
L9664: MASK_SOURCE = "pyimg_source_sha256"
L9665: 
L9666: 
L9667: def read_json(path):
L9668:     path = Path(path)
L9669:     if path.stat().st_size > 2_000_000:
L9670:         raise ValueError(f"Profil zu groß: {path}")
L9671:     value = json.loads(path.read_text(encoding="utf-8"))
L9672:     if not isinstance(value, dict):
L9673:         raise ValueError(f"Profil muss ein JSON-Objekt sein: {path}")
L9674:     return value
L9675: 
L9676: 
L9677: def validate_colors(colors, where):
L9678:     if not isinstance(colors, list) or not 1 <= len(colors) <= 256 or any(
L9679:             not isinstance(c, list) or len(c) != 3 or any(
L9680:                 type(v) is not int or not 0 <= v <= 255 for v in c) for c in colors):
L9681:         raise ValueError(f"{where}: 1..256 RGB-Tripel mit ganzen Zahlen 0..255 erforderlich.")
L9682:     if len({tuple(c) for c in colors}) != len(colors):
L9683:         raise ValueError(f"{where}: doppelte RGB-Farben entfernen.")
L9684: 
L9685: 
L9686: def validate_references(refs):
L9687:     if not isinstance(refs, list) or len(refs) != 8 or any(not isinstance(r, dict) for r in refs):
L9688:         raise ValueError("Profil benötigt Herkunftsdaten aller acht Stand-Richtungen.")
L9689:     if [r.get("direction") for r in refs] != list(color.DIRECTIONS):
L9690:         raise ValueError("Stand-Richtungen im Profil: N, NO, O, SO, S, SW, W, NW erforderlich.")
L9691:     frame_counts = set()
L9692:     for ref in refs:
L9693:         grid = ref.get("grid")
L9694:         size = ref.get("size")
L9695:         if (not isinstance(ref.get("path"), str) or not ref["path"]
L9696:                 or not isinstance(ref.get("sha256"), str)
L9697:                 or not re.fullmatch(r"[0-9a-f]{64}", ref["sha256"])
L9698:                 or not isinstance(grid, list) or len(grid) != 2
L9699:                 or any(type(n) is not int or n < 1 for n in grid)
L9700:                 or math.prod(grid) > 64
L9701:                 or not isinstance(size, list) or len(size) != 2
L9702:                 or any(type(n) is not int or n < 1 for n in size)):
L9703:             raise ValueError("Ungültige Stand-Herkunft: Pfad, SHA-256, Größe und Raster erforderlich.")
L9704:         list(color.frame_boxes(size, grid))
L9705:         if type(ref.get("frames")) is not int or ref["frames"] != math.prod(grid):
L9706:             raise ValueError("Framezahl widerspricht Stand-Raster im Profil.")
L9707:         frame_counts.add(ref["frames"])
L9708:     if len(frame_counts) != 1:
L9709:         raise ValueError("Alle Stand-Richtungen müssen dieselbe Framezahl haben.")
L9710: 
L9711: 
L9712: def validate_header(profile, expected):
L9713:     if (not isinstance(profile, dict) or profile.get("format") != expected
L9714:             or type(profile.get("version")) is not int or profile["version"] != VERSION):
L9715:         raise ValueError(f"Erwartetes Profilformat: {expected}, Version {VERSION}.")
L9716: 
L9717: 
L9718: def validate_materials(materials, definitions=False):
L9719:     if not isinstance(materials, list) or not 1 <= len(materials) <= 255:
L9720:         raise ValueError("1..255 Materialdefinitionen erforderlich.")
L9721:     ids, names = set(), set()
L9722:     for material in materials:
L9723:         if not isinstance(material, dict):
L9724:             raise ValueError("Jedes Material muss ein JSON-Objekt sein.")
L9725:         mid, name = material.get("id"), material.get("name")
L9726:         if type(mid) is not int or not 1 <= mid <= 255 or mid in ids:
L9727:             raise ValueError("Material-IDs müssen eindeutig zwischen 1 und 255 liegen; 0 ist Hintergrund.")
L9728:         if not isinstance(name, str) or not name.strip() or name.casefold() in names:
L9729:             raise ValueError("Materialnamen müssen nichtleer und eindeutig sein.")
L9730:         ids.add(mid)
L9731:         names.add(name.casefold())
L9732:         if definitions:
L9733:             levels = material.get("levels")
L9734:             if type(levels) is not int or not 1 <= levels <= 256:
L9735:                 raise ValueError(f"Material {name}: levels muss zwischen 1 und 256 liegen.")
L9736:         else:
L9737:             validate_colors(material.get("colors"), f"Material {name}")
L9738: 
L9739: 
L9740: def load_palette(path):
L9741:     profile = read_json(path)
L9742:     validate_header(profile, FIXED_FORMAT)
L9743:     if profile.get("color_space") != "sRGB":
L9744:         raise ValueError("Festfarbenprofil benötigt color_space: sRGB.")
L9745:     validate_colors(profile.get("colors"), "Festpalette")
L9746:     validate_references(profile.get("references"))
L9747:     return profile
L9748: 
L9749: 
L9750: def load_material_profile(path):
L9751:     profile = read_json(path)
L9752:     validate_header(profile, MATERIAL_FORMAT)
L9753:     if profile.get("color_space") != "sRGB":
L9754:         raise ValueError("Materialprofil benötigt color_space: sRGB.")
L9755:     validate_materials(profile.get("materials"))
L9756:     validate_references(profile.get("references"))
L9757:     return profile
L9758: 
L9759: 
L9760: def load_definitions(path):
L9761:     definitions = read_json(path)
L9762:     validate_header(definitions, DEFINITIONS_FORMAT)
L9763:     validate_materials(definitions.get("materials"), definitions=True)
L9764:     return definitions
L9765: 
L9766: 
L9767: def make_palette(reference_profile):
L9768:     """Konkrete gemeinsame 64er-Palette des bestehenden Stand-Profils festschreiben."""
L9769:     validate_references(reference_profile.get("references"))
L9770:     colors = [list(c) for c in dict.fromkeys(tuple(c) for c in reference_profile["pixel_palette"])]
L9771:     validate_colors(colors, "Stand-Palette")
L9772:     return {"format": FIXED_FORMAT, "version": VERSION, "color_space": "sRGB",
L9773:             "colors": colors, "references": reference_profile["references"],
L9774:             "derivation": {"reference_profile_sha256": color.fingerprint(reference_profile),
L9775:                            "sampling": reference_profile["sampling"],
L9776:                            "palette": "pixel_palette; up to 64 colors; review visually"}}
L9777: 
L9778: 
L9779: def mask_metadata(grid, source_sha256):
L9780:     info = PngImagePlugin.PngInfo()
L9781:     info.add_text(MASK_VERSION, "1")
L9782:     info.add_text(MASK_GRID, f"{grid[0]}x{grid[1]}")
L9783:     info.add_text(MASK_SOURCE, source_sha256)
L9784:     return info
L9785: 
L9786: 
L9787: def mask_error(region, path, reason, grid):
L9788:     bounds = region.getbbox()
L9789:     if bounds:
L9790:         x, y = bounds[:2]
L9791:         fw, fh = region.width // grid[0], region.height // grid[1]
L9792:         frame = y // fh * grid[0] + x // fw + 1
L9793:         count = region.histogram()[255]
L9794:         raise ValueError(f"Maske {path}: {reason}; {count} Pixel, erster Bereich bei "
L9795:                          f"({x}, {y}), Frame {frame}. Materialmarkierungen prüfen.")
L9796: 
L9797: 
L9798: def validate_labels(mask, image, materials, path="<Maske>", grid=(1, 1)):
L9799:     if mask.mode != "L" or mask.size != image.size:
L9800:         raise ValueError(f"Maske {path}: Größe oder Labelmodus passt nicht zur Quelle.")
L9801:     ids = {m["id"] for m in materials}
L9802:     histogram = mask.histogram()
L9803:     unknown = [i for i, n in enumerate(histogram) if n and i != 0 and i not in ids]
L9804:     if unknown:
L9805:         raise ValueError(f"Maske {path}: unbekannte Material-IDs {unknown}.")
````

## Originalzeilen 8216–8290

````text
L8216: ## 📝 UMSETZUNG-FESTFARBEN.md — ./3-SpritesheetColor-Pipline/UMSETZUNG-FESTFARBEN.md
L8217: 
L8218: # Festfarben umgesetzt
L8219: 
L8220: Stand: 24.09.2026. Arbeitsverzeichnis: `/workspace`.
L8221: 
L8222: Die bestehende Color-Pipeline unterstützt jetzt `soft`, `fixed` und `material`.
L8223: Alte Aufrufe behalten den weichen Farbtransform. Neue Profile, Materialmasken,
L8224: CLI-Kombinationen und vorhandene Ausgaben werden vor dem Schreiben geprüft.
L8225: Gemeinsamer Code liegt in `Pipline/PiplineToos/PyImgFixedColors.py` und ist im
L8226: Installer registriert. Die gültigen Optionen stehen in der [README](README.md).
L8227: 
L8228: ## Vorhandene Ergebnisse
L8229: 
L8230: | Ergebnis | Inhalt |
L8231: | --- | --- |
L8232: | [Materialvergleich](../../spritesheet-material/farbvergleich.html) | 32 eingefärbte Sheets mit festen Materialfarbreihen, acht bytegleiche Stand-Kopien; insgesamt 40 PNG-/GIF-Paare. |
L8233: | [Festfarbenvergleich](../../spritesheet-fixed/farbvergleich.html) | 32 eingefärbte Sheets mit gemeinsamer 64-Farben-Palette, acht bytegleiche Stand-Kopien; insgesamt 40 PNG-/GIF-Paare. |
L8234: | [Maskenansicht](../../spritesheet/materialmasken/masken-vorschau.html) | Alle 40 Masken einschließlich Stand, 640 Frames, acht Material-IDs und Hintergrund. |
L8235: | [Masken und Farbreihen](../../spritesheet/materialmasken/README.md) | Dateien, konkrete Zielfarben, Bearbeitungshinweise und Befehle für die weitere Arbeit. |
L8236: | [Abschlussprüfung](../../spritesheet/materialmasken/abschluss-pruefung.json) | Technische Prüfungen, Canvas-Backups und Browserergebnisse. |
L8237: 
L8238: `spritesheet/` enthält weiterhin die 40 unveränderten Original-PNGs.
L8239: `spritesheet-color/` mit dem früheren Soft-Ergebnis blieb vollständig erhalten.
L8240: Die Masken liegen im neuen Unterordner `spritesheet/materialmasken/`; die
L8241: Quellsuche verarbeitet diese Unterordner nicht als Original-Sheets.
L8242: 
L8243: ## Materialmasken: Entwürfe
L8244: 
L8245: Die Masken sind ausgefüllt und technisch gültig. Sie wurden aus betrachteten
L8246: Stand-Farbproben und der Silhouette jedes einzelnen Frames vorgeschlagen.
L8247: Eine Stand-Maske wurde nicht auf andere Animationen kopiert. Raster und
L8248: Quellhash binden jede Maske an das jeweilige Original.
L8249: 
L8250: Die künstlerische Materialzuordnung ist **noch nicht vollständig bestätigt**.
L8251: Insbesondere Metall/Stoffbesatz, Haut/helles Leder, dunkle Umhangfalten und
L8252: Materialgrenzen benötigen eine gezielte Sichtprüfung. Dieser offene Punkt ist
L8253: in den Maskenmetadaten und Berichten als Entwurfsstatus dokumentiert. Eine
L8254: gültige Material-ID ist kein Nachweis der richtigen semantischen Zuordnung.
L8255: 
L8256: Die acht Materialfarbreihen enthalten zusammen 45 Stufen. Sie wurden aus allen
L8257: acht gelabelten Stand-Richtungen abgeleitet und übernehmen die Unsicherheit der
L8258: Masken. Die globale 64-Farben-Palette benötigt keine Materialmasken.
L8259: 
L8260: ## Durchgeführte Prüfungen
L8261: 
L8262: - 160 Tests bestanden: 113 Projekttests und 47 Resolution-Tests, darunter 38 neue Festfarben-/Materialtests.
L8263: - Beide tatsächlichen Ausgaben geprüft: zusammen 80 PNGs und 80 GIFs.
L8264: - Jeder eingefärbte sichtbare PNG-Pixel gehört exakt zur jeweiligen Zielpalette oder Materialfarbreihe.
L8265: - Alpha, unsichtbares RGB und Bildgröße erhalten; alle Sheets weiterhin 16x1 mit 10240×640 Pixeln.
L8266: - Alle 16 Stand-Kopien der beiden neuen Ausgaben bytegleich zu ihren Originalen.
L8267: - Alle GIFs mit 16 Quellframes, 2000 ms Zyklusdauer und Endlosschleife.
L8268: - Alle 123 Dateien des bisherigen Original-/Soft-Bestands per SHA-256 unverändert bestätigt.
L8269: - Drei HTML-Ansichten in Chromium geprüft: jeweils 40 Sheets mit Frames 0, 7 und 15, insgesamt 360 Frameprüfungen; Wiedergabe, Maskenpositionen und Alpha synchron, keine JavaScript- oder Ladefehler.
L8270: - Alle fünf Canvas-Dateien vor Änderungen als `.canvas.bak` gesichert; nur die Color-Canvas angepasst.
L8271: 
L8272: Die Testumgebung verwendete Python 3.11 und Pillow 12.3. Die Pipeline benötigt
L8273: weiterhin Python ab 3.10 und Pillow ab 10.3. Playwright/Chromium waren nur
L8274: Prüfwerkzeuge und sind keine zusätzliche Pipeline-Abhängigkeit.
L8275: 
L8276: ## Weiterarbeit
L8277: 
L8278: Zuerst die [Maskenansicht](../../spritesheet/materialmasken/masken-vorschau.html)
L8279: und den [Materialvergleich](../../spritesheet-material/farbvergleich.html)
L8280: beurteilen. Nach Änderungen an Stand-Masken die Materialfarbreihen erneut
L8281: exportieren und die Materialausgabe mit `--dry-run --overwrite` prüfen.
L8282: Die konkreten Befehle stehen in der Masken-README. Originale weiterhin als
L8283: Quellen verwenden.
L8284: 
L8285: `SpritesheetResolution --palette-profile` liest weiterhin das bisherige
L8286: `reference-colors.json`; neue Festfarben-/Materialprofile sind ein anderes
L8287: Format. Comic-Skalierung kann Mischfarben erzeugen und benötigt für erneut
L8288: exakte RGB-Werte einen ausdrücklichen weiteren Festfarbenabgleich.
L8289: 
L8290: ---
````

## Originalzeilen 7100–7109

````text
L7100: ## 📝 FORTFUEHRUNG-FESTFARBEN.prompt.md — ./3-SpritesheetColor-Pipline/FORTFUEHRUNG-FESTFARBEN.prompt.md
L7101: 
L7102: # Fortführung: SpritesheetColor-Pipline um exakte Festfarben erweitern
L7103: 
L7104: **Aktualisierung 24.09.2026:** Die unten geplanten Modi `fixed` und `material`
L7105: sind inzwischen implementiert. Den gültigen CLI-Vertrag beschreibt die
L7106: [README](README.md); Ergebnisse und Prüfungen stehen im
L7107: [Umsetzungsbericht](UMSETZUNG-FESTFARBEN.md). Die [Greenhero-Masken](../../spritesheet/materialmasken/README.md)
L7108: liegen als technisch vollständige, künstlerisch noch zu prüfende Entwürfe vor.
L7109: Der folgende Übergabetext dokumentiert den Stand **vor** dieser Umsetzung.
````
