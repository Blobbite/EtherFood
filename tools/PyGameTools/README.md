# PyGameTools

Sechs Pipeline-Befehle für Spielgrafiken werden installiert:

- `PyPiplineStart-SourceColor`: Source-Einzelbilder aller Posen mit gemeinsamen Stand-Farben vereinheitlichen; PNGs, Materialmasken und Vergleich ohne Frame-Reduktion. [SourceColor-Anleitung](Pipline/SourceColor-Pipline/README.md).
- `PyPiplineStart-SpritesheetColor`: Stand-Farbreferenz aus acht Richtungen → weicher Abgleich, exakte Palette oder Materialfarbreihen mit Masken → PNGs, GIFs und Vergleichs-HTML im getrennten Ordner.
- `PyPiplineStart-SpritesheetFram8`: waagerechter oder senkrechter 8er-Streifen → Original-GIF/HTML → optimiertes 4×2-Sheet → GIF/HTML.
- `PyPiplineStart-SpritesheetFram16`: 16er-Streifen → Original-GIF/HTML → optimiertes 4×4-Sheet → GIF/HTML.
- `PyPiplineStart-SpritesheetFramReduce`: 16-Frame-Originale → 8/10/12/14 Frames, inklusive Optimierung, GIFs, HTML und Prüfbericht; belegte Zielordner werden im Normalmodus vollständig übersprungen.
- `PyPiplineStart-SpritesheetResolution`: Auflösung vorhandener `comic_high`-Daten in Comic-/Pixel-Stufen reduzieren, inklusive GIFs und HTML-Vergleichen.

## Installation unter Linux

Python **3.10+** mit `venv`/`pip` erforderlich (Debian/Ubuntu: `sudo apt install python3-venv`). Im heruntergeladenen Projektordner:

```bash
python3 PyGameTools.py --prepare
sudo python3 PyGameTools.py --apply-system --install-dir "$HOME/.local/share/PyGameTools"
```

Programme und eigene Python-Umgebung liegen in `~/.local/share/PyGameTools`, die sechs Wrapper in `/usr/local/bin`. Die Wrapper verwenden diese Installation; der Benutzerordner muss zugänglich bleiben. Pillow wird bei der Vorbereitung installiert. `PyGameTools.py` ersetzt `PythonLinux.py`.

Ohne sudo: `python3 PyGameTools.py --install --user-bin`; dafür muss `~/.local/bin` im `PATH` stehen. Vorab prüfen: `python3 PyGameTools.py --install --dry-run`.

## Benutzung

```bash
cd /pfad/spritesheet-fram8
PyPiplineStart-SpritesheetFram8

cd /pfad/spritesheet-fram16
PyPiplineStart-SpritesheetFram16

cd /pfad/run/comic_high  # enthält spritesheet-fram16/PixelEng/
PyPiplineStart-SpritesheetFramReduce

cd /pfad/stand  # enthält comic_high/
PyPiplineStart-SpritesheetResolution
# Alle Posen unter einem gemeinsamen Ordner:
PyPiplineStart-SpritesheetResolution -s-a #/pfad/posen
```

Fram8 und Fram16 verarbeiten statische PNGs direkt im Startordner. Rasterangaben bedeuten immer **Spalten × Zeilen**.

| Pipeline | Quellraster | Zielraster | Optimierte Ausgabe |
| --- | --- | --- | --- |
| Fram8 | `8x1` oder `1x8` | `4x2` | `<Name>_4x2_o.png` |
| Fram16 | `16x1` oder `1x16` | `4x4` | `<Name>_4x4_o.png` |

Beide Streifen-Pipelines nehmen anhand der längeren Bildseite ein waagerechtes bzw. senkrechtes Raster an. Mit `--grid 8x1` oder `--grid 1x8` bei Fram8 bzw. `--grid 16x1` oder `--grid 1x16` bei Fram16 lässt sich die Richtung fest vorgeben. Bei ungewöhnlich breiten oder hohen Einzelframes sollte das Raster ausdrücklich angegeben werden.

Beispiel: **5120×640 Pixel** mit acht quadratischen Frames bedeutet **`8x1`**: acht Bilder à **640×640 Pixel nebeneinander**. `1x8` würde dieses Bild fälschlich in acht Streifen à 5120×80 Pixel zerlegen. Die Pipeline zeigt deshalb Quellgröße, Raster und unbeschnittene Framegröße bereits vor der Verarbeitung an.

Die Optimierung entfernt den größtmöglichen **gemeinsamen vollständig transparenten Außenrand**. Jeder Frame erhält denselben Zuschnitt; sämtliche sichtbaren Pixel, Teiltransparenz, relative Positionen, Reihenfolge und auch leere Frames bleiben erhalten. Es werden keine zusätzlichen Rasterzellen eingefügt und keine Frames einzeln zentriert oder skaliert.

```text
spritesheet-fram8/
├── PixelEng/
│   ├── hero_N.png             # Original unverändert hierher verschoben
│   ├── hero_N_8fps.gif
│   └── gif-vergleich.html
├── hero_N_4x2_o.png           # optimiertes 4×2-Sheet
├── hero_N_4x2_o_8fps.gif
└── gif-vergleich.html
```

Bei Fram16 ist der Ablauf gleich, mit `4x4` in den Ausgabedateinamen.

Standard: **8 FPS**, unabhängig von der Framezahl. Fram8, Fram16 und Resolution bieten zusätzlich `--fps`. Erneute Fram8-/Fram16-Aufrufe lesen auch `PixelEng`. Vorhandene optimierte PNGs werden anhand ihrer Maße und sämtlicher RGBA-Pixel mit dem erwarteten Ergebnis verglichen. Abweichende oder beschädigte Ausgaben werden im Normalmodus gemeldet und bleiben unverändert. Details zur Resolution-Pipeline: [Pipeline-README](Pipline/SpritesheetResolution-Pipline/README.md).

## Ausgabemodi für alle sechs Pipelines

| Modus | Verhalten |
| --- | --- |
| `--dry-run` | Eingaben, Ausgabewege und vorhandene Ergebnisse prüfen; nichts schreiben oder verschieben. |
| Normal, ohne Schalter | Fehlende Ausgaben erstellen. Alle vorhandenen Dateien bleiben erhalten, einschließlich GIFs, HTML und Berichten. |
| `--overwrite` | Ausgaben der gewählten Verarbeitung neu erstellen, auch wenn sie bereits existieren. |
| `--dry-run --overwrite` | Die geplante Neuerstellung prüfen und anzeigen; nichts verändern. |

Originalquellen und fremde Dateien bleiben erhalten. Fram8 und Fram16 verschieben neue Original-PNGs wie bisher unverändert nach `PixelEng/`; bereits vorhandene GIFs im Startordner bleiben an ihrem Platz. Beschädigte oder veraltete Ausgaben werden ohne `--overwrite` nicht automatisch ersetzt. Bestehende HTML-Seiten werden auch bei neu hinzugekommenen Bildern erst mit `--overwrite` aktualisiert.

**Besonderheit Reduce:** Im Normalmodus wird jede belegte Zielvariante vollständig übersprungen, auch wenn darin noch Ergebnisse fehlen. `--overwrite` erstellt nur die gewählten Varianten aus den unveränderten Fram16-Quellen neu.

Bei Resolution begrenzen `--gif-only`, `--html-only` und `--compare-only` auch das Überschreiben auf die jeweilige Verarbeitung. Beispielsweise erneuert `--html-only --overwrite` nur HTML-Seiten.

Zur vollständigen Neuerstellung falsch zerlegter waagerechter 8er-Sheets nach dem Programmupdate im betroffenen `spritesheet-fram8`-Ordner ausführen:

```bash
PyPiplineStart-SpritesheetFram8 --grid 8x1 --overwrite
```

Die Originale bleiben dabei in `PixelEng`; PNGs, GIFs und beide HTML-Vorschauen werden daraus neu aufgebaut.

## Farben und Materialfarbreihen aus Stand-Referenzen

```bash
PyPiplineStart-SpritesheetColor /pfad/hd --dry-run
PyPiplineStart-SpritesheetColor /pfad/hd
```

Stand aus allen acht Richtungen und sämtlichen Frames liefert die gemeinsame
Farbreferenz. Ohne weitere Option bleibt der bisherige weiche Abgleich (`soft`)
mit Ausgabe unter `/pfad/hd-color`. Flache PNG-Ordner werden ebenfalls unterstützt.

| Farbmodus | Erforderliche Eingaben | Standardziel |
| --- | --- | --- |
| `soft` | Stand-Referenzen oder `--profile` | `<Quelle>-color` |
| `fixed` | `--fixed-palette` | `<Quelle>-fixed` |
| `material` | `--material-profile` und `--mask-dir` | `<Quelle>-material` |

`fixed` schreibt ausschließlich Farben einer gemeinsamen RGB-Palette.
`material` verwendet feste Farbreihen je Material-ID; die Masken ordnen jeden
sichtbaren Quellpixel zu. Profile lassen sich aus Stand exportieren, unmarkierte
Maskenvorlagen mit `--prepare-masks` anlegen. Exakte Zuordnung, Maskenformat und
ausführbare Beispiele: [Color-README](Pipline/SpritesheetColor-Pipline/README.md).

`farbvergleich.html` zeigt Farbmodus, Original, Ergebnis und passende Stand-
Richtung synchron, im Materialmodus zusätzlich die Materialmaske mit Legende.
Originale und bytegleiche Stand-Referenzkopien bleiben erhalten. Die exakte
Palettenprüfung gilt für die eingefärbten Ziel-PNGs; alle Frames behalten Größe,
Position, Alpha und unsichtbares RGB. Die Greenhero-Maskenvorschläge und ihr
Prüfstand liegen unter [spritesheet/materialmasken](spritesheet/materialmasken/README.md).
Ihre vollständige visuelle Materialprüfung steht noch aus.

`--palette-profile /pfad/hd-color/.color_profile/reference-colors.json` bindet
bei der Resolution-Pipeline dieselbe feste Stand-Palette für Pixel High/Low ein.
Die neuen Fest-/Materialprofile werden von Resolution nicht als Palettenprofil
akzeptiert. Comic-Skalierung kann Mischfarben erzeugen; für dort ebenfalls
exakte Farben ist eine erneute Zuordnung erforderlich. Das Referenzprofil ist
außerdem ein anderes Format als `color_profile.json` von PyImgTestColor/PyImgTuneColor.

## Frame-Varianten aus 16 Originalframes

Im Ordner mit `spritesheet-fram16/PixelEng/`:

```bash
PyPiplineStart-SpritesheetFramReduce --dry-run
PyPiplineStart-SpritesheetFramReduce
# Optional nur einzelne Varianten oder eine feste Quellausrichtung:
PyPiplineStart-SpritesheetFramReduce --frames 10 14 --grid 16x1
```

Reduce erzeugt standardmäßig 8, 10, 12 und 14 Frames direkt aus den jeweiligen 16-Frame-Originalen. Es arbeitet mit festen **8 FPS** und Endlosschleife. Alle Dateien eines Schritts werden für sämtliche neuen Varianten fertiggestellt, bevor der nächste Schritt beginnt: Ordner → alle Originalkopien prüfen → reduzieren → GIF/HTML in PixelEng → optimieren → GIF/HTML im Hauptordner → prüfen und dokumentieren.

**Im Normalmodus werden belegte Zielordner als ganze Variante übersprungen.** Sobald Dateien vorhanden sind – auch nur einzelne PNGs, GIFs oder Dokumentation in Unterordnern –, wird dort nichts verändert oder ergänzt. Leere Ordner einschließlich leerem `PixelEng/` werden weiterverwendet. Das gilt auch für unvollständige frühere Läufe. Vorhandene Fram8-Daten bleiben dadurch erhalten, während fehlende Varianten erstellt werden. Für die bewusste Neuerstellung, etwa nur von Fram10: `PyPiplineStart-SpritesheetFramReduce --frames 10 --overwrite`. Dabei bleiben Fram16 und andere Varianten unverändert.

Raster: **8 → 4×2, 10 → 5×2, 12 → 4×3, 14 → 7×2**; in PixelEng jeweils ein horizontaler `Nx1`-Streifen. `README.md`, `build-info.json` und `pruefung.json` dokumentieren Quelle, Indizes, Raster, tatsächliche Toolaufrufe und Prüfergebnisse. Details: [Reduce-README](Pipline/SpritesheetFramReduce-Pipline/README.md).

## Gemeinsame Werkzeuge

Mehrfach verwendeter Pipeline-Code liegt ausschließlich in `Pipline/PiplineToos/`:

- `PyImgColorPipeline.py`: gemeinsamer Farbablauf für Source-Einzelbilder und Spritesheets; SourceColor liest ausschließlich Einzelbilder.

- `PyImgColorMatch.py`: gemeinsames Stand-Farbprofil, stabile Farbkorrektur und feste Pixelpalette für Color/Resolution.
- `PyImgFixedColors.py`: exakte Palettenzuordnung, feste Materialfarbreihen, Labelmasken und Profilexport für Color.
- `PyImgGrid.py`: Framezahl, Quell- und Zielraster prüfen, Frames verlustfrei umordnen und gemeinsam beschneiden.
- `PySpritesheetPipeline.py`: gemeinsamer Ablauf für Fram8 und Fram16 einschließlich Archivierung und Vorschauen.
- `PyImgFrameSelect.py`: gleichmäßige Frame-Auswahl und verlustfreie horizontale Ausgabe einer Arbeitskopie.
- `PyImgGif.py`: GIF-Export und HTML-Vorschauen für die Spritesheet-Pipelines.
- `PyPipelineOutputs.py`: gemeinsame Schreibregeln für Normalmodus, `--dry-run` und `--overwrite`.

Die Fram8-/Fram16-Starter legen nur ihre Framezahl und Rastervorgaben fest. Reduce steuert seine sieben Phasen über alle neuen Varianten und nutzt dieselben Bildwerkzeuge. Die früheren lokalen 4×4-Werkzeuge und der externe Grid-Adapter entfallen; es wird kein Optimierer aus einer separaten Installation geladen.

Das Grid-Werkzeug lässt sich auch direkt aufrufen, zum Beispiel für zehn Frames:

```bash
python3 Pipline/PiplineToos/PyImgGrid.py /pfad/quellen \
  --frames 10 --source-grid 1x10 --target-grid 5x2 --optimize
```

Quell- und Zielraster dürfen beliebige positive Abmessungen haben, müssen aber jeweils genau `--frames` Zellen enthalten. Auch mehrzeilige Quellen sind möglich. Ohne `--source-grid` wird ein Streifen anhand der längeren Bildseite angenommen. Ohne `--optimize` bleiben die vollständigen Frame-Flächen erhalten.

`--output-dir` legt einen getrennten Ausgabeordner fest, `--recursive` bezieht Unterordner ein. `--solo` wiederholt ein Einzelbild in sämtlichen Zielzellen; dabei kein Quellraster angeben. `--dry-run` und `--overwrite` stehen ebenfalls zur Verfügung.

Bei der Ordnersuche werden erzeugte Rasterdateien mit Endungen wie `_4x2.png` oder `_5x2_o.png` ausgelassen. Ein vorhandenes Sheet mit einer solchen Endung kann dem Grid-Werkzeug ausdrücklich als einzelne Quelldatei übergeben werden. Der Optimierer selbst ist nicht auf 8/16 Frames begrenzt; GIF- und Resolution-Pipeline unterstützen derzeit 3 bis 64 Rasterzellen.

## Tests

```bash
python3 -m unittest discover -s .tests -v
python3 -m unittest discover -s Pipline/SpritesheetResolution-Pipline/tests -p 'test_*.py' -v
```

## Aktualisieren / Entfernen

Im aktualisierten Projektordner `python3 PyGameTools.py --update` ausführen. Die bisherigen Wrapper bleiben gültig. Zum Aktualisieren der Befehlsnamen und Hinzufügen neuer Befehle bei einer bestehenden Systeminstallation anschließend:

```bash
sudo python3 PyGameTools.py --apply-system --install-dir "$HOME/.local/share/PyGameTools"
```

Bei einer Benutzerinstallation genügt `python3 PyGameTools.py --install --user-bin`; damit werden Programmdateien und alle sechs Wrapper erneuert. Bei einem eigenen Installationspfad den bisherigen Pfad mit `--install-dir /dein/pfad` angeben.

Die bisherige All-Pipeline heißt jetzt **SpritesheetResolution-Pipline**; der neue
Befehl lautet `PyPiplineStart-SpritesheetResolution`. Ein vorhandener alter
`PyPiplineStart-SpritsheetAll`-Wrapper funktioniert nach `--update` über eine
Weiterleitung weiter. Bei der anschließenden Wrapper-Installation wird der eigene
alte Wrapper durch den neuen Namen ersetzt. Fremde Befehle bleiben erhalten.
`--spritesheet-all` / `-s-a` bezeichnet weiterhin die Verarbeitung **aller Posen**.

```bash
sudo python3 PyGameTools.py --uninstall --system-bin --install-dir "$HOME/.local/share/PyGameTools"
# Bei Benutzerinstallation stattdessen:
# python3 PyGameTools.py --uninstall --user-bin
```
