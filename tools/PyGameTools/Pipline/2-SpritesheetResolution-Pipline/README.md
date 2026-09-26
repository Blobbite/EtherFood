# SpritesheetResolution-Pipline – Auflösung reduzieren

Erstellt kleinere Comic- und Pixel-Auflösungen aus vorhandenen HD-PNGs und
Spritesheets. Die Framezahl und Reihenfolge bleiben erhalten. Der Starter heißt
`PyPiplineStart-SpritesheetResolution`.

Im Ordner starten, der `comic_high` enthält. Der Ordnername ist beliebig,
z.B. `stand`, `run` oder ein anderer Aktionsname:

```bash
cd /pfad/stand
PyPiplineStart-SpritesheetResolution --spritesheet
```

**Keine Pfadangabe und keine Scale-Einstellungen nötig.** Ausgangspunkt ist
immer der aktuelle Terminalordner. Die Installation übernimmt dein vorhandenes
`PyGameTools.py` (siehe [Installation](../../README.md)).

## Automatischer Ablauf

1. PNG-Einzelbilder direkt in `comic_high` und Spritesheets in dessen Frame-Ordnern lesen.
2. `comic_mid`, `comic_low`, `pixel_high` und `pixel_low` daneben verwenden
   oder anlegen. Dieselben Frame-Unterordner und PNG-Dateinamen übernehmen;
   Einzelbilder direkt im jeweiligen Variantenordner speichern.
3. Über die vier Verarbeitungsskripte zunächst alle kleineren PNGs erzeugen.
   Spritesheets behalten ihr Raster und ihre Frame-Reihenfolge.
4. Danach das vorhandene GIF-Programm in jedem Ziel-Frame-Ordner ausführen.
   Es erstellt GIFs mit standardmäßig 8 FPS und `gif-vergleich.html`.
5. Im Startordner `aufloesungsvergleich.html` für den gemeinsamen visuellen Test erstellen.

```text
stand/                         ← hier PyPiplineStart-SpritesheetResolution aufrufen
├── comic_high/                ← HD-Quelle, bleibt unverändert
│   ├── spritesheet-fram16/
│   ├── spritesheet-fram14/
│   ├── spritesheet-fram12/
│   ├── spritesheet-fram10/
│   ├── spritesheet-fram8/
│   ├── greenhero_hd_stand_N.png
│   └── … weitere Einzelbilder
├── comic_mid/                 ← gleiche Frame-Ordner und verkleinerte Einzelbilder
├── comic_low/
├── pixel_high/
└── pixel_low/
```

Verarbeitet werden alle vorhandenen Frame-Ordner mit 3 bis 64 Zellen und alle
normalen PNG-Dateien direkt in `comic_high`. Ein Aktionsordner mit ausschließlich
Einzelbildern funktioniert ebenfalls. Archive, `PixelEng`, versteckte Dateien,
Dateilinks, vorhandene GIFs und PNGs außerhalb von `comic_high` dienen nicht als
HD-Quellen.

Zum Beispiel wird `comic_high/greenhero_hd_stand_N.png` nach
`comic_mid/greenhero_hd_stand_N.png`, `comic_low/greenhero_hd_stand_N.png`,
`pixel_high/greenhero_hd_stand_N.png` und `pixel_low/greenhero_hd_stand_N.png`
umgerechnet. Diese Einzelbilder werden nicht zu GIFs zusammengefasst.

| Verarbeitungsskript | Voreinstellung pro Einzelbild bzw. Frame |
| --- | --- |
| `SComicMid.py` | 50 % der HD-Breite und -Höhe |
| `SComicLow.py` | 25 % der HD-Breite und -Höhe |
| `SPixelHigh.py` | längste Seite maximal 128 px, bis zu 64 Farben |
| `SPixelLow.py` | 90 % der tatsächlichen Pixel-High-Größe, dieselbe Farbpalette (standardmäßig 64 Farben) |

Die Comic-Stufen und Pixel High entstehen direkt aus HD. Pixel Low reproduziert
Pixel High aus derselben HD-Quelle und verkleinert dessen Frames ohne neue
Farbmischung. Die bisherige zusätzliche Reduktion auf 16 Farben entfällt.
Bei 128 px High entstehen 115 px Low; bei kleineren High-Frames gilt ebenfalls
der Faktor 0,9. Die vorhandene High-Datei wird dabei nicht verändert.
Transparente Ränder gehören zur Frame-Größe; kleinere Bilder werden nicht
vergrößert. Comic wird glatt
verkleinert, Pixel erhält eine gemeinsame reduzierte Palette pro Sheet und
harte Transparenzkanten.

Mit `--palette-profile /pfad/.color_profile/reference-colors.json` verwendet
Pixel High/Low stattdessen die gemeinsame feste Stand-Palette aus der
[Color-Pipeline](../SpritesheetColor-Pipline/README.md), über alle Sheets hinweg.
Die Palette im Profil ersetzt dabei die Farbzahlvorgaben für beide Pixelstufen;
Comic behält seine feinen Abstufungen. Bereits vorhandene Ausgaben werden auch
mit diesem Schalter nur bei zusätzlichem `--overwrite` neu erstellt.

`--palette-profile` akzeptiert das Format `pyimg-reference-colors` mit
`pixel_palette`. Die neuen Color-Formate `pyimg-fixed-palette` und
`pyimg-material-colors` sind keine gültigen Resolution-Palettenprofile; diese
Pipeline verarbeitet keine Materialmasken. Comic-Skalierung kann durch Glättung
neue Mischfarben erzeugen. Für exakte Festfarben auch in diesen Comic-Ausgaben
ist anschließend eine ausdrückliche erneute Farbzuordnung erforderlich; bei
Materialfarben müssen die Masken zu den skalierten Bildern passen.

## Gemeinsamer visueller Test

Nach dem Durchlauf `aufloesungsvergleich.html` im Startordner im Browser öffnen.
Die Seite funktioniert offline ohne Server. Sie lädt die vorhandenen PNG-
Spritesheets über relative Dateipfade und zeigt die passende Rasterzelle im
Browser an. Normale PNGs erscheinen als „Einzelbild“ in derselben Auswahl und
werden vollständig angezeigt; die Wiedergabe- und FPS-Regler sind dann deaktiviert.
Beim Start und beim Wechsel der Auswahl werden nur die fünf Bilder der gewählten
Animation bzw. Einzelbildgruppe und Richtung geladen. FPS-Wechsel und Frameschritte
verwenden diese geladenen Bilder weiter.

Es werden weder Bilddaten eingebettet noch zusätzliche Frame-PNGs oder GIFs für
die Vorschau erzeugt. Das bisherige 128-MiB-Einbettungslimit entfällt. Auch die
Seiten `gif-vergleich.html` je Frame-Ordner verwenden vorhandene Spritesheets.
Beim Verschieben oder Weitergeben den Aktionsordner mit HTML, PNG-Spritesheets
und GIF-Unterordnern zusammenhalten. Der Browser benötigt weiterhin Speicher
für die gerade geladenen Bilder.

Die Vergleichsseite bietet:

- Comic High/HD, Comic Mittel, Comic Low, Pixel High und Pixel Low nebeneinander.
- Gleiche Anzeigegröße bei unterschiedlichen tatsächlichen Pixelauflösungen.
- Auswahl von Einzelbildern oder Animationen mit Framezahl und den acht Blickrichtungen N, NO, O, SO, S, SW, W, NW.
- Gemeinsame Wiedergabe, Pause, Einzelbildschritte und Frame-Regler.
- Gemeinsame Vorschau-FPS: **2, 4, 6, 8, 10, 12, 16, 18, 20, 22 oder 24**.
- Gemeinsame Anzeigegröße, Hintergrundfarbe und optionale Vorschauglättung.

So lassen sich Farben, Konturen und Unschärfe bei gleicher Animationsphase
vergleichen. Comic Mittel wird vorerst nicht zusätzlich nachgeschärft.
Fehlende PNG-Varianten erscheinen als Hinweis. Die gemeinsame Vorschau benötigt
keine GIFs; vorhandene GIFs bleiben über einen zusätzlichen Link erreichbar.
`comic_high` bleibt unverändert. Die Vorschau zeigt alle Rasterzellen, auch
Leerzellen und identische Nachbarframes. Sie zeigt die PNG-Farben und Transparenz;
Farbänderungen oder Transparenzverluste des GIF-Exports sind darin nicht sichtbar.
Die FPS-Auswahl ändert nur die Vorschau, nicht die gespeicherten Dateien.

Nur die Vergleichsseite aus den vorhandenen Ergebnissen neu erstellen:

```bash
PyPiplineStart-SpritesheetResolution --compare-only
```

Nach erfolgreicher Neuerstellung entfernt das Skript die unveränderten,
anhand ihres Inhalts und Hash-Dateinamens erkannten Bildkopien im alten
`aufloesungsvergleich-bilder`-Ordner. Bei den einzelnen GIF-Galerien gilt dasselbe
für `gif-vergleich-bilder`. Fremde oder veränderte Dateien, Links und Unterordner
werden dabei beibehalten. Leere Cache-Ordner werden entfernt.

`PyGraphicsCompare.py` und `PyGraphicsPoseCompare.py` gehören als
Vergleichsmodule zu den Pipeline-Dateien. Beide beim Installieren mitnehmen.
`PyImgGif.py` liegt gemeinsam für Resolution, Fram8, Fram16 und FramReduce unter `Pipline/PiplineToos/`.
Fram8 und Fram16 verwenden dort außerdem `PyImgGrid.py` und `PySpritesheetPipeline.py`.
Der Installer übernimmt diese Struktur; die Hilfsmodule bekommen keine Terminal-Wrapper.

## CLI: eine Pose oder alle Posen

`--spritesheet` / `-s` verarbeitet eine Pose. Ohne Modus bleibt dies der Standard.
`--spritesheet-all` / `-s-a` startet im gemeinsamen Posenordner und findet Posen
auch in Unterordnern. Jeder Ordner mit `comic_high` gilt als Pose. Versteckte
Ordner, Verzeichnislinks und die Variantenordner werden bei dieser Suche
ausgelassen. Alle Posen werden vor der ersten Ausgabe geprüft.

```bash
PyPiplineStart-SpritesheetResolution -s /pfad/posen/jump
PyPiplineStart-SpritesheetResolution -s-a /pfad/posen
PyPiplineStart-SpritesheetResolution --spritesheet-all /pfad/posen --output-root /pfad/ergebnisse
```

Die Unterstruktur der Posen bleibt auch bei `--output-root` erhalten. Standardmäßig
werden sämtliche vorhandenen Raster und alle vier kleineren Auflösungen erstellt.
Die hochauflösenden Quellen und eventuell dort vorhandene GIFs bleiben unverändert.

```text
posen/
├── jump/
│   ├── comic_high/spritesheet-fram{8,10,12,14,16}/  # Quellen
│   ├── comic_mid/spritesheet-fram{8,10,12,14,16}/   # PNG, GIF, gif-vergleich.html
│   ├── comic_low/spritesheet-fram{8,10,12,14,16}/
│   ├── pixel_high/spritesheet-fram{8,10,12,14,16}/
│   ├── pixel_low/spritesheet-fram{8,10,12,14,16}/
│   └── aufloesungsvergleich.html
├── walk/                                         # gleicher Aufbau
└── positionsvergleich.html                       # nur bei -s-a
```

Nur tatsächlich vorhandene Frame-Ordner werden verarbeitet. Einzelbilder
bleiben im Auflösungsvergleich sichtbar; der Positionsvergleich zeigt Animationen.
Posen mit ausschließlich Einzelbildern erscheinen deshalb nicht in seiner Auswahl.
`--no-gif` unterdrückt sämtliche GIF- und HTML-Ausgaben auch bei `-s-a`.

## Größen- und Positionsvergleich

`positionsvergleich.html` direkt im Browser öffnen. Die Seite lädt ausschließlich
vorhandene PNGs und GIFs über relative Links. Sie enthält weder eingebettete
Bilddaten noch externe Bibliotheken und benötigt keinen Server. Beim Kopieren
die gesamte Ergebnisstruktur mitnehmen; bei einer separaten Ausgabe liegen
HD-Verweise weiterhin im Quellordner.

- Pose A wählen, optional Pose B hinzufügen, etwa Jump und Walk.
- Eine der acht Richtungen N, NO, O, SO, S, SW, W, NW auswählen.
- Auflösungen und Raster wie 4×4 oder 7×7 beliebig kombinieren.
- Alle gewählten Ebenen zunächst am gleichen Ursprung überlagern. Der untere
  Abstandsregler zieht sie stufenlos auseinander und wieder zusammen.
- Zwischen tatsächlichen Pixelgrößen und einem gemeinsamen HD-Maßstab wechseln.
  Zoom und Deckkraft einstellen; Leinwandmitte, unten mittig oder oben links als
  Ursprung wählen. Transparente Ränder werden weder beschnitten noch verschoben.
- Leinwandrahmen, Ursprung und sichtbare Inhaltsgrenzen einblenden. Eine Ebene
  als Referenz wählen und Positions- und Größenunterschiede je Frame in der
  Tabelle ablesen. Leere Frames haben keine messbaren Inhaltsgrenzen.
- Einzelne Ebenen ausblenden oder direkt ihre PNG-/GIF-Dateien öffnen.

Die **Synchronvorschau** liest die vorhandenen Spritesheet-Zellen. Sie ermöglicht
gemeinsame FPS, Wiedergabe/Pause, Einzelbildschritte und einen Frame-Regler.
„Gleiche Animationsphase“ passt unterschiedliche Framezahlen auf einen gemeinsamen
Zyklus an; die gewählten FPS gelten für den längsten Zyklus. „Gleiche Framenummer“
spielt jede Animation mit derselben Bildrate und ihrer eigenen Framezahl ab.
Die Messwerte basieren auf den PNG-Frames; Alpha-Werte unter 16 werden dabei
als unsichtbar gewertet. Ohne HD dient die größte verfügbare Variante der
jeweiligen Animation als Größenbezug; die Tabelle kennzeichnet diesen Fall.

**Original-GIFs** zeigt die tatsächlich exportierten Animationen mit GIF-Farben,
GIF-Transparenz und ihrer gespeicherten Bildrate. Die Überlagerungs-, Größen-
und Abstandsregler funktionieren auch hier. Native GIF-Wiedergabe im Browser
erlaubt keine gemeinsame FPS-/Pause-/Frame-Steuerung; diese Regler und die
Frame-Messwerte sind in dieser Ansicht deaktiviert. Dafür zur Synchronvorschau
wechseln. Vorhandene GIFs bleiben auch ohne Spritesheet-PNG darstellbar.

## Vorhandene Ergebnisse weiterverwenden

| Option | Verhalten |
| --- | --- |
| `--gif-only` | GIFs und HTML aus vorhandenen Varianten-PNGs; keine PNG-Skalierung oder PNG-Erzeugung |
| `--html-only` | Fehlende GIF-Galerien und Vergleichsseiten erstellen; PNGs und GIFs unverändert lassen |
| `--compare-only` | Fehlende Auflösungsvergleiche und bei `-s-a` den Positionsvergleich erstellen |
| `--overwrite` | Ausgaben der gewählten Verarbeitung erneuern, einschließlich HTML |
| `--dry-run` | Eingaben und Ausgabewege prüfen, ohne Dateien zu schreiben |

```bash
PyPiplineStart-SpritesheetResolution -s --gif-only --fps 12
PyPiplineStart-SpritesheetResolution -s-a /pfad/posen --gif-only
PyPiplineStart-SpritesheetResolution -s-a /pfad/posen --html-only --overwrite
PyPiplineStart-SpritesheetResolution -s-a /pfad/posen --compare-only --overwrite
```

Diese drei Modi funktionieren auch ohne HD-Originale, wenn Varianten-PNGs bzw.
GIFs vorhanden sind. Fehlende Auflösungen werden im Vergleich angezeigt und
nicht nachberechnet. Für reine HTML-Erstellung sind ausschließlich vorhandene
GIFs ebenfalls ausreichend. `--gif-only` benötigt Spritesheet-PNGs in mindestens
einer gewählten Zielvariante. Die Optionen sind untereinander und mit `--no-gif`
nicht kombinierbar. Vorhandene Ausgaben bleiben ohne `--overwrite` erhalten.
Das gilt auch für ein eigenes `--gif-script`: Es verarbeitet temporäre PNG-Kopien;
die Pipeline übernimmt nur die vorgesehenen GIFs gemäß dem gewählten Ausgabemodus.

## Spritesheet- und spätere Texturmodule

Die bisherigen Worker wurden in `SComicLow.py`, `SComicMid.py`, `SPixelHigh.py`
und `SPixelLow.py` umbenannt; direkte Aufrufe und Installationsverweise entsprechend
anpassen. Die Ausgabeordner heißen weiterhin `comic_low`, `comic_mid`,
`pixel_high` und `pixel_low`.

`--Textur` / `--textur` / `-t` ist bereits in `-h` dokumentiert und für die spätere
Texturskalierung mit `TComicLow.py`, `TComicMid.py`, `TPixelHigh.py` und
`TPixelLow.py` reserviert. Diese Module und ihre Skalierungsregeln sind noch
nicht implementiert. Der Aufruf beendet sich mit einer klaren Meldung und
Exit-Code 2, ohne Daten zu erzeugen.

## Vorhandenes GIF-Skript

Die Pipeline führt `PyImgGif.py` als Programm aus, nachdem die PNG-Erzeugung
abgeschlossen ist. GIFs und HTML-Seiten je Frame-Ordner kommen aus diesem
Werkzeug; der gemeinsame Auflösungsvergleich entsteht zusätzlich. Beide
HTML-Ansichten verwenden vorhandene Spritesheets. In `gif-vergleich.html` stehen
die FPS unter „Feste FPS“ global und auch je Animation zur Auswahl. Fehlt zu
einem GIF ein passendes Spritesheet (zum Beispiel bei einem fremden GIF oder
einem Solo-Export), zeigt diese Galerie das Original-GIF ohne FPS- und
Einzelbildsteuerung; sie erzeugt dafür keine zusätzlichen Bilddateien.

Eine einzelne GIF-Galerie ohne erneute GIF-Konvertierung aktualisieren:

```bash
python3 /pfad/zu/PyImgGif.py --html-only --overwrite
```

Diesen Befehl im jeweiligen Frame-Ordner ausführen.

## Erneuter Durchlauf und freiwillige Optionen

Im **Normalmodus** werden fehlende PNGs, GIFs und HTML-Seiten ergänzt. Alle
vorhandenen Dateien bleiben unverändert. Unlesbare oder veraltete GIFs werden
gemeldet und ohne `--overwrite` nicht ersetzt. Vorhandene HTML-Seiten behalten
ihren bisherigen Stand. Wenn du HD-Bilder geändert hast oder die ausgewählten
Ausgaben neu berechnen möchtest:

```bash
PyPiplineStart-SpritesheetResolution --overwrite
```

`--overwrite` ersetzt zugehörige PNGs, GIFs und HTML-Seiten. Geänderte HD-Quellen oder neue
Skalierungseinstellungen werden damit auch auf bestehende Varianten angewendet.
Originalquellen und fremde Dateien bleiben erhalten. `--variants` und `--frames`
begrenzen die PNG-/GIF-Erzeugung wie bei einem normalen Lauf.
Mit `--gif-only --overwrite` werden GIFs und HTML erneuert; PNGs bleiben erhalten.
Mit `--html-only --overwrite` bzw. `--compare-only --overwrite` werden nur die
jeweiligen HTML-Seiten erneuert.

**`--dry-run`** prüft Quellen und Ausgabewege, ohne Dateien oder Ordner anzulegen.
**`--dry-run --overwrite`** zeigt, welche Ausgaben ersetzt würden, und schreibt nichts.

Weitere Optionen stehen unter `PyPiplineStart-SpritesheetResolution --help`. `--dry-run` zeigt nur
den Ablauf; `--no-gif` erzeugt nur PNGs. Zielgrößen bleiben bei Bedarf einstellbar.
Die vier Verarbeitungsskripte lassen sich auch einzeln im Aktionsordner starten.
`--frames 8 16` beschränkt nur die Frame-Ordner; die Einzelbilder direkt in
`comic_high` werden weiterhin verarbeitet. `--grid` gilt ausschließlich für
Spritesheets, auch wenn ein Einzelbild eine Rasterangabe im Dateinamen enthält.

Für die GIF-Erstellung stehen dieselben elf Bildraten zur Verfügung:

```bash
PyPiplineStart-SpritesheetResolution --fps 18
```

Der Standard bleibt 8 FPS. Der Export berücksichtigt die 10-ms-Zeitauflösung
des GIF-Formats; die HTML-Vorschau verwendet die gewählte Bildrate direkt.

Raster stammen aus dem PNG-Dateinamen oder aus der Ordnerzuordnung:
16 → 4×4, 14 → 7×2, 12 → 4×3, 10 → 5×2, 8 → 4×2. Quadratische
Framezahlen haben ebenfalls eine Zuordnung, etwa 49 → 7×7 und 64 → 8×8.
Andere Raster benötigen einen Dateinamenhinweis oder `--grid`; die Zellenzahl
muss zur Zahl in `spritesheet-framN` passen. Ungültige Raster werden
vor der Ausgabe gemeldet. PNGs behalten alle Zellen; für Leerzellen und
identische GIF-Frames gelten die Regeln deines vorhandenen GIF-Werkzeugs.

Voraussetzungen bleiben Python ab 3.10 und Pillow ab 10.3.

Tests im Werkzeugordner: `python3 -m unittest discover -s tests -v`.

Optionale Browserprüfungen (lokale HTML-Dateien ohne Server):

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
python3 tests/browser_comparison.py -v
```

Playwright wird ausschließlich für diese Tests benötigt.
