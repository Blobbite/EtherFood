# Q05 — SourceColor Bestand

Original: `allsummary(1).md`. SHA-256 der vollständigen Upload-Datei: `55bb37c2fb9909384a89d3ac4c7e4b011f1fa8d0319243c04e436fe567570c69`.

Relevanz: Einzelbild-Farbkorrektur ohne Animationserzeugung; keine automatische Materialerkennung behauptet.

Die Zeilennummern in den folgenden Blöcken beziehen sich auf die Originaldatei. Der Text ist ein Quellenbeleg, keine neu erteilte Arbeitsanweisung.

## Originalzeilen 11864–11964

````text
L11864: ## 📝 README.md — ./SourceColor-Pipline/README.md
L11865: 
L11866: # SourceColor-Pipline
L11867: 
L11868: Gemeinsame Farben für die **Source-Einzelbilder aller Posen und Richtungen**.
L11869: Die Bilder behalten ihre Größe, Position und Transparenz. Ausgabe: PNGs,
L11870: Farbprofil, Prüfbericht und `farbvergleich.html` im getrennten Zielordner.
L11871: 
L11872: `SourceColor` behandelt jedes Bild als **1×1**. Es erzeugt keine Animationen,
L11873: GIFs oder Framevarianten. `SpritesheetFramReduce-Pipline` bleibt die eigene
L11874: Pipeline für die Reduktion vorhandener Animationen.
L11875: 
L11876: ```bash
L11877: PyPiplineStart-SourceColor /pfad/source --dry-run
L11878: PyPiplineStart-SourceColor /pfad/source
L11879: ```
L11880: 
L11881: Ohne Installation, mit Python 3.10+ und Pillow:
L11882: 
L11883: ```bash
L11884: python3 Pipline/SourceColor-Pipline/PyPiplineStart-SourceColor.py /pfad/source
L11885: ```
L11886: 
L11887: ## Eingaben
L11888: 
L11889: PNG-Dateien direkt im Quellordner, eine Ebene tiefer in Posenordnern oder
L11890: direkt in deren `comic_high`. Die relative Struktur bleibt in der Ausgabe
L11891: erhalten. Frameordner, `PixelEng`, kleinere Grafikstufen, Masken, versteckte
L11892: Ordner und vorhandene Farbausgaben werden nicht als Source-Bilder eingelesen.
L11893: Erkannte Spritesheet-Dateien werden abgelehnt. `--grid` gibt es hier nicht.
L11894: 
L11895: ```text
L11896: source/
L11897: ├── jump/greenhero_hd_jump_N.png
L11898: ├── run/greenhero_hd_run_N.png
L11899: ├── stand/greenhero_hd_stand_N.png
L11900: └── … weitere Posen und Richtungen
L11901: ```
L11902: 
L11903: Die Pipeline schneidet selbst keine Frames aus Sheets aus. Im Greenhero-Lauf
L11904: wurden auf ausdrücklichen Wunsch die ersten Frames der fünf vorhandenen
L11905: Original-Animationen verlustfrei als Source-Einzelbilder übernommen. Jump
L11906: verwendet seine acht vollständigen Einzelbilder.
L11907: 
L11908: ## Farbmodi und Masken
L11909: 
L11910: | Modus | Eingabe | Ergebnis |
L11911: | --- | --- | --- |
L11912: | `soft` (Standard) | Acht Stand-Einzelbilder oder `--profile` | Weicher Farbabgleich |
L11913: | `fixed` | `--fixed-palette` | Jeder sichtbare Zielpixel liegt in der festen RGB-Palette |
L11914: | `material` | `--material-profile` und `--mask-dir` | Jeder sichtbare Zielpixel liegt in der Farbreihe seiner Material-ID |
L11915: 
L11916: Für alle Posen **dasselbe Profil** verwenden. Ein bereits aus Stand-Sheets
L11917: abgeleitetes Materialprofil kann wiederverwendet werden; die verarbeiteten
L11918: Source-Bilder bleiben trotzdem Einzelbilder. Tatsächlich im Profil gebundene
L11919: Stand-Referenzbilder werden bytegleich kopiert. Andere Source-Bilder, auch aus
L11920: Stand-Sheets entnommene Frames, werden regulär korrigiert.
L11921: 
L11922: ```bash
L11923: PyPiplineStart-SourceColor /pfad/source \
L11924:   --color-mode material \
L11925:   --material-profile /pfad/materialmasken/source/stand-materials.json \
L11926:   --mask-dir /pfad/materialmasken/source \
L11927:   --output-dir /pfad/source-color --dry-run
L11928: ```
L11929: 
L11930: Zum Erzeugen `--dry-run` weglassen. Die Labelmasken müssen dieselbe relative
L11931: Struktur und dieselben Pixelmaße wie die Source-Bilder besitzen. Format:
L11932: 8-Bit-L/P-PNG, Material-IDs 1..255, ID 0 ausschließlich auf transparentem
L11933: Hintergrund; Metadaten `pyimg_grid=1x1`, Version und SHA-256 der Quelle.
L11934: Farbige Maskenvorschauen sind keine Labelmasken.
L11935: 
L11936: Neue **leere Vorlagen**, die anschließend beschriftet werden müssen:
L11937: 
L11938: ```bash
L11939: PyPiplineStart-SourceColor /pfad/source --prepare-masks /pfad/materialmasken/source
L11940: ```
L11941: 
L11942: Die Pipeline behauptet keine automatische Materialerkennung. Die korrekte
L11943: Zuordnung von Haaren, Leder, Haut, Metall usw. ist in der Maskenvorschau zu
L11944: prüfen. Maße, Quellbindung, vollständige Belegung und exakte Zielfarben werden
L11945: technisch geprüft.
L11946: 
L11947: `--export-fixed-palette` sowie `--export-material-profile` funktionieren auch
L11948: mit den acht Stand-Einzelbildern. Der Materialexport benötigt zusätzlich
L11949: `--material-definitions` und die fertigen Stand-Masken. Details zu Formaten und
L11950: Farboptionen: [gemeinsamer Farbvertrag](../SpritesheetColor-Pipline/README.md).
L11951: 
L11952: ## Schreiben und Fortführen
L11953: 
L11954: `--dry-run` prüft ohne Ausgabe. Normal werden fehlende Ausgaben ergänzt und
L11955: passende vorhandene Dateien unverändert erhalten. Abweichende Ergebnisse oder
L11956: geänderte Einstellungen werden gemeldet. `--overwrite` ersetzt nur gewählte
L11957: Ausgaben im getrennten Zielordner. Originalbilder bleiben erhalten.
L11958: 
L11959: Die Vorschau zeigt Original, Ergebnis, passende Stand-Referenz und die
L11960: Materialmaske. Einzelbilder haben keine Wiedergabe- oder Frame-Steuerung.
L11961: 
L11962: Gemeinsamer Code liegt in `Pipline/PiplineToos/PyImgColorPipeline.py`.
L11963: Der Installer registriert `PyPiplineStart-SourceColor` als sechsten Befehl.
L11964: 
````
