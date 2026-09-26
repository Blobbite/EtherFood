# Q01 — FramReduce Bestand

Original: `allsummary(1).md`. SHA-256 der vollständigen Upload-Datei: `55bb37c2fb9909384a89d3ac4c7e4b011f1fa8d0319243c04e436fe567570c69`.

Relevanz: Frame-Stufen, Raster, feste 8 FPS, Skipverhalten und technische Berichte.

Die Zeilennummern in den folgenden Blöcken beziehen sich auf die Originaldatei. Der Text ist ein Quellenbeleg, keine neu erteilte Arbeitsanweisung.

## Originalzeilen 1342–1471

````text
L1342: ## 📝 README.md — ./1-SpritesheetFramReduce-Pipline/README.md
L1343: 
L1344: # SpritesheetFramReduce-Pipline
L1345: 
L1346: Erzeugt fehlende Varianten mit 8, 10, 12 und 14 Frames aus den Original-PNGs in
L1347: `spritesheet-fram16/PixelEng/`. Die 16-Frame-Originale bleiben unverändert.
L1348: 
L1349: ```bash
L1350: cd /pfad/run/comic_high
L1351: PyPiplineStart-SpritesheetFramReduce --dry-run
L1352: PyPiplineStart-SpritesheetFramReduce
L1353: ```
L1354: 
L1355: Alternativ den Projektordner als Argument übergeben. Ohne Installation:
L1356: 
L1357: ```bash
L1358: python3 /pfad/PyGameTools/Pipline/SpritesheetFramReduce-Pipline/PyPiplineStart-SpritesheetFramReduce.py /pfad/run/comic_high
L1359: ```
L1360: 
L1361: Python 3.10+ und Pillow aus der PyGameTools-Umgebung sind erforderlich.
L1362: 
L1363: ## Ausgabemodi
L1364: 
L1365: **Normal, ohne Schalter:** Sobald ein Zielordner eine Datei enthält, wird **die gesamte Variante** übersprungen.
L1366: Das schließt Dateien in `PixelEng/` und anderen Unterordnern ein, auch einzelne
L1367: Richtungen, GIFs, Dokumentation oder unvollständige Ergebnisse. Links und mit
L1368: Dateien belegte Zielpfade werden ebenfalls übersprungen. Es wird nichts überschrieben
L1369: oder ergänzt. Leere Verzeichnisbäume werden weiterverwendet.
L1370: 
L1371: Beispiel: `spritesheet-fram8/PixelEng/hero_N.png` ist schon vorhanden.
L1372: Fram8 bleibt vollständig unverändert; nur die fehlenden Varianten 10, 12 und 14
L1373: werden aus Fram16 erstellt. Ein erneuter Aufruf nach einem erfolgreichen Lauf
L1374: überspringt alle vier Varianten ohne Dateien neu zu schreiben.
L1375: 
L1376: **`--dry-run`:** Quellen und geplante Ausgaben prüfen, ohne Dateien oder Ordner zu
L1377: erstellen. Vorhandene Varianten werden wie im Normalmodus übersprungen.
L1378: 
L1379: **`--overwrite`:** Die gewählten Varianten aus den 16-Frame-Originalen neu erstellen.
L1380: Ersetzt werden die zugehörigen reduzierten PNGs in `PixelEng/`, optimierten PNGs,
L1381: GIFs, HTML-Seiten und Berichte. Originalquellen, andere Varianten und fremde
L1382: Dateien bleiben erhalten. Links oder andere ungültige Ausgabepfade werden vor
L1383: der Verarbeitung abgelehnt.
L1384: 
L1385: Nach einem Abbruch bleiben bereits geschriebene Dateien erhalten. Der Normalmodus
L1386: überspringt deshalb auch unvollständige Varianten; `--overwrite` baut sie bewusst
L1387: neu auf. Die Kombination mit `--dry-run` zeigt diesen Plan, ohne ihn auszuführen:
L1388: 
L1389: ```bash
L1390: PyPiplineStart-SpritesheetFramReduce --frames 10 14 --dry-run --overwrite
L1391: PyPiplineStart-SpritesheetFramReduce --frames 10 14 --overwrite
L1392: ```
L1393: 
L1394: ## Optionen
L1395: 
L1396: | Option | Wirkung |
L1397: | --- | --- |
L1398: | `source` | Projektordner mit `spritesheet-fram16/PixelEng/`; Standard: aktueller Ordner |
L1399: | `--frames 8 10 12 14` | Gewünschte Varianten; standardmäßig alle vier |
L1400: | `--grid 16x1` | Horizontalen Quellstreifen ausdrücklich vorgeben |
L1401: | `--grid 1x16` | Vertikalen Quellstreifen ausdrücklich vorgeben |
L1402: | `--dry-run` | Quellen, Skip-Entscheidungen und Plan prüfen; nichts schreiben |
L1403: | `--overwrite` | Zugehörige Ausgaben der gewählten Varianten neu erstellen |
L1404: 
L1405: Raster bedeuten **Spalten × Zeilen**. Ohne `--grid` wird die längere Bildseite pro
L1406: Quelldatei verwendet. Bei ungewöhnlich breiten oder hohen Einzelbildern das Raster
L1407: ausdrücklich vorgeben. Die GIFs laufen immer mit **8 FPS in Endlosschleife**; HTML
L1408: wird immer erstellt.
L1409: 
L1410: ## Ablauf
L1411: 
L1412: Jede Phase wird für **alle zu erstellenden Varianten, Animationen und Richtungen**
L1413: abgeschlossen, bevor die nächste beginnt. Im Normalmodus nehmen belegte Varianten
L1414: an keiner Phase teil.
L1415: 
L1416: 1. Alle Zielordner und deren `PixelEng/` anlegen oder leere Ordner verwenden.
L1417: 2. Alle Original-PNGs unverändert in alle neuen `PixelEng/` kopieren; jede Kopie
L1418:    und die unveränderte Quelle per SHA-256 prüfen. GIFs, Archive und erzeugte Raster
L1419:    sind keine Eingaben; Quell-Unterordner werden nicht durchsucht.
L1420: 3. Nur die Kopien reduzieren. Für Zielanzahl N werden die Quellindizes
L1421:    `floor(16 * k / N)` für `k = 0 … N-1` verwendet. Jede Variante stammt direkt
L1422:    von Fram16. Alle Richtungen verwenden dieselbe Indexliste. Ausgabe horizontal
L1423:    als `Nx1`, ohne Skalierung, Verschiebung oder Pixeländerung.
L1424: 4. GIFs und `gif-vergleich.html` in jedem neuen `PixelEng/` erstellen.
L1425: 5. Mit dem gemeinsamen `PyImgGrid.py` optimieren. Pro Sheet denselben vollständig
L1426:    transparenten Außenrand an allen ausgewählten Frames entfernen und ins Zielraster packen.
L1427: 6. GIFs mit explizitem Zielraster und HTML neben den optimierten PNGs erstellen.
L1428: 7. Pixel, Reihenfolge, Transparenz, Raster, logische GIF-Framezahl, Laufzeit,
L1429:    Endlosschleife und HTML-Verknüpfungen prüfen. Dokumentation im Zielordner schreiben.
L1430: 
L1431: | Frames | PixelEng | Optimiert | Zyklus bei 8 FPS |
L1432: | --- | --- | --- | --- |
L1433: | 8 | 8×1 | 4×2 | 1,00 s |
L1434: | 10 | 10×1 | 5×2 | 1,25 s |
L1435: | 12 | 12×1 | 4×3 | 1,50 s |
L1436: | 14 | 14×1 | 7×2 | 1,75 s |
L1437: 
L1438: Bestehende leere Frames werden als Teil der gewählten Sequenz erhalten; zusätzliche
L1439: oder wiederholte Füllframes werden nicht erzeugt. Eine vollständig transparente
L1440: Auswahl ist ein Fehler und wird schon vor dem Anlegen der Zielordner erkannt.
L1441: 
L1442: ## Ausgabe und Prüfung
L1443: 
L1444: ```text
L1445: spritesheet-fram10/
L1446: ├── PixelEng/
L1447: │   ├── hero_N.png
L1448: │   ├── hero_N_8fps.gif
L1449: │   └── gif-vergleich.html
L1450: ├── hero_N_5x2_o.png
L1451: ├── hero_N_5x2_o_8fps.gif
L1452: ├── gif-vergleich.html
L1453: ├── README.md
L1454: ├── build-info.json
L1455: └── pruefung.json
L1456: ```
L1457: 
L1458: Die Dateipaare entstehen für alle vorhandenen Animationen und Richtungen.
L1459: `build-info.json` enthält Quellen und Prüfsummen, Quellframe-Indizes, Raster,
L1460: Zuschnitt und die tatsächlich ausgeführten Python-Toolaufrufe mit Parametern.
L1461: `pruefung.json` enthält die Ergebnisse der technischen Prüfungen.
L1462: 
L1463: PNG-Zellen werden exakt gegen die ausgewählten Originalframes bzw. deren gemeinsamen
L1464: Zuschnitt geprüft. GIF-Bilder werden mit derselben Palette und Transparenzschwelle
L1465: geprüft, die der Export verwendet. Identische GIF-Frames dürfen zusammengefasst sein,
L1466: wenn die logische Sequenz und ihre Gesamtdauer erhalten bleiben.
L1467: 
L1468: PNG bleibt die verlustfreie Referenz. GIF verwendet eine begrenzte Farbpalette und
L1469: binäre Transparenz. Die sichtbare Bewegungsqualität nach dem Weglassen von Frames
L1470: muss zusätzlich in den HTML-Vorschauen beurteilt werden; sie wird im Prüfbericht
L1471: nicht als automatisch bestätigt ausgegeben.
````

## Originalzeilen 1211–1251

````text
L1211: def run(args) -> int:
L1212:     root = args.source.expanduser().resolve()
L1213:     if not root.is_dir():
L1214:         raise ValueError(f"Projektordner fehlt: {root}")
L1215:     variants, skipped = [], []
L1216:     for count in sorted(set(args.frames)):
L1217:         variant = Variant(count, root / f"spritesheet-fram{count}")
L1218:         if occupied(variant.root) and not args.overwrite:
L1219:             print(f"[SKIP] {variant.root.name}: bereits belegt; bleibt vollständig unverändert.", flush=True)
L1220:             skipped.append(count)
L1221:         else:
L1222:             variants.append(variant)
L1223:     if not variants:
L1224:         print("Fertig: Alle angeforderten Varianten vorhanden; nichts geändert.")
L1225:         return 0
L1226:     if gif.Image is None:
L1227:         raise ImportError("Pillow fehlt; PyGameTools.py --install ausführen.")
L1228:     manual_grid = raster.parse_grid(args.grid) if args.grid else None
L1229:     sources = read_sources(root, variants, manual_grid)
L1230:     for variant in variants:
L1231:         print(f"[PLAN] {variant.root.name}: 16 → {variant.count}x1 → {raster.grid_name(variant.grid)}; "
L1232:               f"Indizes {select.uniform_indices(SOURCE_COUNT, variant.count)}", flush=True)
L1233:         planned = [variant.root / name for name in ("gif-vergleich.html", "README.md", "build-info.json", "pruefung.json")]
L1234:         planned.append(variant.archive / "gif-vergleich.html")
L1235:         for source in sources:
L1236:             for png in (variant.reduced(source), variant.optimized(source)):
L1237:                 planned.extend((png, png.with_name(f"{png.stem}_{FPS}fps.gif")))
L1238:         for path in planned:
L1239:             output_policy.should_write(path, overwrite=args.overwrite, dry_run=True)
L1240:     if args.dry_run:
L1241:         print(f"Plan geprüft: {len(variants)} Variante(n) erstellen, {len(skipped)} übersprungen; nichts geschrieben.")
L1242:         return 0
L1243:     # Eine zwischenzeitlich belegte Variante ebenfalls in Ruhe lassen.
L1244:     for variant in variants[:]:
L1245:         if occupied(variant.root) and not args.overwrite:
L1246:             print(f"[SKIP] {variant.root.name}: inzwischen belegt.", flush=True)
L1247:             skipped.append(variant.count)
L1248:             variants.remove(variant)
L1249:     if not variants:
L1250:         print("Fertig: Alle Ziele inzwischen belegt; nichts geändert.")
L1251:         return 0
````
