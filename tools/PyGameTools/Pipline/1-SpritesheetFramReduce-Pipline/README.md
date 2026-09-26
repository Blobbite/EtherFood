# SpritesheetFramReduce-Pipline

Erzeugt fehlende Varianten mit 8, 10, 12 und 14 Frames aus den Original-PNGs in
`spritesheet-fram16/PixelEng/`. Die 16-Frame-Originale bleiben unverändert.

```bash
cd /pfad/run/comic_high
PyPiplineStart-SpritesheetFramReduce --dry-run
PyPiplineStart-SpritesheetFramReduce
```

Alternativ den Projektordner als Argument übergeben. Ohne Installation:

```bash
python3 /pfad/PyGameTools/Pipline/SpritesheetFramReduce-Pipline/PyPiplineStart-SpritesheetFramReduce.py /pfad/run/comic_high
```

Python 3.10+ und Pillow aus der PyGameTools-Umgebung sind erforderlich.

## Ausgabemodi

**Normal, ohne Schalter:** Sobald ein Zielordner eine Datei enthält, wird **die gesamte Variante** übersprungen.
Das schließt Dateien in `PixelEng/` und anderen Unterordnern ein, auch einzelne
Richtungen, GIFs, Dokumentation oder unvollständige Ergebnisse. Links und mit
Dateien belegte Zielpfade werden ebenfalls übersprungen. Es wird nichts überschrieben
oder ergänzt. Leere Verzeichnisbäume werden weiterverwendet.

Beispiel: `spritesheet-fram8/PixelEng/hero_N.png` ist schon vorhanden.
Fram8 bleibt vollständig unverändert; nur die fehlenden Varianten 10, 12 und 14
werden aus Fram16 erstellt. Ein erneuter Aufruf nach einem erfolgreichen Lauf
überspringt alle vier Varianten ohne Dateien neu zu schreiben.

**`--dry-run`:** Quellen und geplante Ausgaben prüfen, ohne Dateien oder Ordner zu
erstellen. Vorhandene Varianten werden wie im Normalmodus übersprungen.

**`--overwrite`:** Die gewählten Varianten aus den 16-Frame-Originalen neu erstellen.
Ersetzt werden die zugehörigen reduzierten PNGs in `PixelEng/`, optimierten PNGs,
GIFs, HTML-Seiten und Berichte. Originalquellen, andere Varianten und fremde
Dateien bleiben erhalten. Links oder andere ungültige Ausgabepfade werden vor
der Verarbeitung abgelehnt.

Nach einem Abbruch bleiben bereits geschriebene Dateien erhalten. Der Normalmodus
überspringt deshalb auch unvollständige Varianten; `--overwrite` baut sie bewusst
neu auf. Die Kombination mit `--dry-run` zeigt diesen Plan, ohne ihn auszuführen:

```bash
PyPiplineStart-SpritesheetFramReduce --frames 10 14 --dry-run --overwrite
PyPiplineStart-SpritesheetFramReduce --frames 10 14 --overwrite
```

## Optionen

| Option | Wirkung |
| --- | --- |
| `source` | Projektordner mit `spritesheet-fram16/PixelEng/`; Standard: aktueller Ordner |
| `--frames 8 10 12 14` | Gewünschte Varianten; standardmäßig alle vier |
| `--grid 16x1` | Horizontalen Quellstreifen ausdrücklich vorgeben |
| `--grid 1x16` | Vertikalen Quellstreifen ausdrücklich vorgeben |
| `--dry-run` | Quellen, Skip-Entscheidungen und Plan prüfen; nichts schreiben |
| `--overwrite` | Zugehörige Ausgaben der gewählten Varianten neu erstellen |

Raster bedeuten **Spalten × Zeilen**. Ohne `--grid` wird die längere Bildseite pro
Quelldatei verwendet. Bei ungewöhnlich breiten oder hohen Einzelbildern das Raster
ausdrücklich vorgeben. Die GIFs laufen immer mit **8 FPS in Endlosschleife**; HTML
wird immer erstellt.

## Ablauf

Jede Phase wird für **alle zu erstellenden Varianten, Animationen und Richtungen**
abgeschlossen, bevor die nächste beginnt. Im Normalmodus nehmen belegte Varianten
an keiner Phase teil.

1. Alle Zielordner und deren `PixelEng/` anlegen oder leere Ordner verwenden.
2. Alle Original-PNGs unverändert in alle neuen `PixelEng/` kopieren; jede Kopie
   und die unveränderte Quelle per SHA-256 prüfen. GIFs, Archive und erzeugte Raster
   sind keine Eingaben; Quell-Unterordner werden nicht durchsucht.
3. Nur die Kopien reduzieren. Für Zielanzahl N werden die Quellindizes
   `floor(16 * k / N)` für `k = 0 … N-1` verwendet. Jede Variante stammt direkt
   von Fram16. Alle Richtungen verwenden dieselbe Indexliste. Ausgabe horizontal
   als `Nx1`, ohne Skalierung, Verschiebung oder Pixeländerung.
4. GIFs und `gif-vergleich.html` in jedem neuen `PixelEng/` erstellen.
5. Mit dem gemeinsamen `PyImgGrid.py` optimieren. Pro Sheet denselben vollständig
   transparenten Außenrand an allen ausgewählten Frames entfernen und ins Zielraster packen.
6. GIFs mit explizitem Zielraster und HTML neben den optimierten PNGs erstellen.
7. Pixel, Reihenfolge, Transparenz, Raster, logische GIF-Framezahl, Laufzeit,
   Endlosschleife und HTML-Verknüpfungen prüfen. Dokumentation im Zielordner schreiben.

| Frames | PixelEng | Optimiert | Zyklus bei 8 FPS |
| --- | --- | --- | --- |
| 8 | 8×1 | 4×2 | 1,00 s |
| 10 | 10×1 | 5×2 | 1,25 s |
| 12 | 12×1 | 4×3 | 1,50 s |
| 14 | 14×1 | 7×2 | 1,75 s |

Bestehende leere Frames werden als Teil der gewählten Sequenz erhalten; zusätzliche
oder wiederholte Füllframes werden nicht erzeugt. Eine vollständig transparente
Auswahl ist ein Fehler und wird schon vor dem Anlegen der Zielordner erkannt.

## Ausgabe und Prüfung

```text
spritesheet-fram10/
├── PixelEng/
│   ├── hero_N.png
│   ├── hero_N_8fps.gif
│   └── gif-vergleich.html
├── hero_N_5x2_o.png
├── hero_N_5x2_o_8fps.gif
├── gif-vergleich.html
├── README.md
├── build-info.json
└── pruefung.json
```

Die Dateipaare entstehen für alle vorhandenen Animationen und Richtungen.
`build-info.json` enthält Quellen und Prüfsummen, Quellframe-Indizes, Raster,
Zuschnitt und die tatsächlich ausgeführten Python-Toolaufrufe mit Parametern.
`pruefung.json` enthält die Ergebnisse der technischen Prüfungen.

PNG-Zellen werden exakt gegen die ausgewählten Originalframes bzw. deren gemeinsamen
Zuschnitt geprüft. GIF-Bilder werden mit derselben Palette und Transparenzschwelle
geprüft, die der Export verwendet. Identische GIF-Frames dürfen zusammengefasst sein,
wenn die logische Sequenz und ihre Gesamtdauer erhalten bleiben.

PNG bleibt die verlustfreie Referenz. GIF verwendet eine begrenzte Farbpalette und
binäre Transparenz. Die sichtbare Bewegungsqualität nach dem Weglassen von Frames
muss zusätzlich in den HTML-Vorschauen beurteilt werden; sie wird im Prüfbericht
nicht als automatisch bestätigt ausgegeben.
