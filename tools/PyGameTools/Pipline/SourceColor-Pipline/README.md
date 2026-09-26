# SourceColor-Pipline

Gemeinsame Farben für die **Source-Einzelbilder aller Posen und Richtungen**.
Die Bilder behalten ihre Größe, Position und Transparenz. Ausgabe: PNGs,
Farbprofil, Prüfbericht und `farbvergleich.html` im getrennten Zielordner.

`SourceColor` behandelt jedes Bild als **1×1**. Es erzeugt keine Animationen,
GIFs oder Framevarianten. `SpritesheetFramReduce-Pipline` bleibt die eigene
Pipeline für die Reduktion vorhandener Animationen.

```bash
PyPiplineStart-SourceColor /pfad/source --dry-run
PyPiplineStart-SourceColor /pfad/source
```

Ohne Installation, mit Python 3.10+ und Pillow:

```bash
python3 Pipline/SourceColor-Pipline/PyPiplineStart-SourceColor.py /pfad/source
```

## Eingaben

PNG-Dateien direkt im Quellordner, eine Ebene tiefer in Posenordnern oder
direkt in deren `comic_high`. Die relative Struktur bleibt in der Ausgabe
erhalten. Frameordner, `PixelEng`, kleinere Grafikstufen, Masken, versteckte
Ordner und vorhandene Farbausgaben werden nicht als Source-Bilder eingelesen.
Erkannte Spritesheet-Dateien werden abgelehnt. `--grid` gibt es hier nicht.

```text
source/
├── jump/greenhero_hd_jump_N.png
├── run/greenhero_hd_run_N.png
├── stand/greenhero_hd_stand_N.png
└── … weitere Posen und Richtungen
```

Die Pipeline schneidet selbst keine Frames aus Sheets aus. Im Greenhero-Lauf
wurden auf ausdrücklichen Wunsch die ersten Frames der fünf vorhandenen
Original-Animationen verlustfrei als Source-Einzelbilder übernommen. Jump
verwendet seine acht vollständigen Einzelbilder.

## Farbmodi und Masken

| Modus | Eingabe | Ergebnis |
| --- | --- | --- |
| `soft` (Standard) | Acht Stand-Einzelbilder oder `--profile` | Weicher Farbabgleich |
| `fixed` | `--fixed-palette` | Jeder sichtbare Zielpixel liegt in der festen RGB-Palette |
| `material` | `--material-profile` und `--mask-dir` | Jeder sichtbare Zielpixel liegt in der Farbreihe seiner Material-ID |

Für alle Posen **dasselbe Profil** verwenden. Ein bereits aus Stand-Sheets
abgeleitetes Materialprofil kann wiederverwendet werden; die verarbeiteten
Source-Bilder bleiben trotzdem Einzelbilder. Tatsächlich im Profil gebundene
Stand-Referenzbilder werden bytegleich kopiert. Andere Source-Bilder, auch aus
Stand-Sheets entnommene Frames, werden regulär korrigiert.

```bash
PyPiplineStart-SourceColor /pfad/source \
  --color-mode material \
  --material-profile /pfad/materialmasken/source/stand-materials.json \
  --mask-dir /pfad/materialmasken/source \
  --output-dir /pfad/source-color --dry-run
```

Zum Erzeugen `--dry-run` weglassen. Die Labelmasken müssen dieselbe relative
Struktur und dieselben Pixelmaße wie die Source-Bilder besitzen. Format:
8-Bit-L/P-PNG, Material-IDs 1..255, ID 0 ausschließlich auf transparentem
Hintergrund; Metadaten `pyimg_grid=1x1`, Version und SHA-256 der Quelle.
Farbige Maskenvorschauen sind keine Labelmasken.

Neue **leere Vorlagen**, die anschließend beschriftet werden müssen:

```bash
PyPiplineStart-SourceColor /pfad/source --prepare-masks /pfad/materialmasken/source
```

Die Pipeline behauptet keine automatische Materialerkennung. Die korrekte
Zuordnung von Haaren, Leder, Haut, Metall usw. ist in der Maskenvorschau zu
prüfen. Maße, Quellbindung, vollständige Belegung und exakte Zielfarben werden
technisch geprüft.

`--export-fixed-palette` sowie `--export-material-profile` funktionieren auch
mit den acht Stand-Einzelbildern. Der Materialexport benötigt zusätzlich
`--material-definitions` und die fertigen Stand-Masken. Details zu Formaten und
Farboptionen: [gemeinsamer Farbvertrag](../SpritesheetColor-Pipline/README.md).

## Schreiben und Fortführen

`--dry-run` prüft ohne Ausgabe. Normal werden fehlende Ausgaben ergänzt und
passende vorhandene Dateien unverändert erhalten. Abweichende Ergebnisse oder
geänderte Einstellungen werden gemeldet. `--overwrite` ersetzt nur gewählte
Ausgaben im getrennten Zielordner. Originalbilder bleiben erhalten.

Die Vorschau zeigt Original, Ergebnis, passende Stand-Referenz und die
Materialmaske. Einzelbilder haben keine Wiedergabe- oder Frame-Steuerung.

Gemeinsamer Code liegt in `Pipline/PiplineToos/PyImgColorPipeline.py`.
Der Installer registriert `PyPiplineStart-SourceColor` als sechsten Befehl.
