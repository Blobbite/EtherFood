# Q02 — Resolution Bestand

Original: `allsummary(1).md`. SHA-256 der vollständigen Upload-Datei: `55bb37c2fb9909384a89d3ac4c7e4b011f1fa8d0319243c04e436fe567570c69`.

Relevanz: Grafikprofile, Einzelbilder, HTML-Vergleiche, Palettenbeschränkung und reservierter Texturmodus.

Die Zeilennummern in den folgenden Blöcken beziehen sich auf die Originaldatei. Der Text ist ein Quellenbeleg, keine neu erteilte Arbeitsanweisung.

## Originalzeilen 4377–4712

````text
L4377: ## 📝 README.md — ./2-SpritesheetResolution-Pipline/README.md
L4378: 
L4379: # SpritesheetResolution-Pipline – Auflösung reduzieren
L4380: 
L4381: Erstellt kleinere Comic- und Pixel-Auflösungen aus vorhandenen HD-PNGs und
L4382: Spritesheets. Die Framezahl und Reihenfolge bleiben erhalten. Der Starter heißt
L4383: `PyPiplineStart-SpritesheetResolution`.
L4384: 
L4385: Im Ordner starten, der `comic_high` enthält. Der Ordnername ist beliebig,
L4386: z.B. `stand`, `run` oder ein anderer Aktionsname:
L4387: 
L4388: ```bash
L4389: cd /pfad/stand
L4390: PyPiplineStart-SpritesheetResolution --spritesheet
L4391: ```
L4392: 
L4393: **Keine Pfadangabe und keine Scale-Einstellungen nötig.** Ausgangspunkt ist
L4394: immer der aktuelle Terminalordner. Die Installation übernimmt dein vorhandenes
L4395: `PyGameTools.py` (siehe [Installation](../../README.md)).
L4396: 
L4397: ## Automatischer Ablauf
L4398: 
L4399: 1. PNG-Einzelbilder direkt in `comic_high` und Spritesheets in dessen Frame-Ordnern lesen.
L4400: 2. `comic_mid`, `comic_low`, `pixel_high` und `pixel_low` daneben verwenden
L4401:    oder anlegen. Dieselben Frame-Unterordner und PNG-Dateinamen übernehmen;
L4402:    Einzelbilder direkt im jeweiligen Variantenordner speichern.
L4403: 3. Über die vier Verarbeitungsskripte zunächst alle kleineren PNGs erzeugen.
L4404:    Spritesheets behalten ihr Raster und ihre Frame-Reihenfolge.
L4405: 4. Danach das vorhandene GIF-Programm in jedem Ziel-Frame-Ordner ausführen.
L4406:    Es erstellt GIFs mit standardmäßig 8 FPS und `gif-vergleich.html`.
L4407: 5. Im Startordner `aufloesungsvergleich.html` für den gemeinsamen visuellen Test erstellen.
L4408: 
L4409: ```text
L4410: stand/                         ← hier PyPiplineStart-SpritesheetResolution aufrufen
L4411: ├── comic_high/                ← HD-Quelle, bleibt unverändert
L4412: │   ├── spritesheet-fram16/
L4413: │   ├── spritesheet-fram14/
L4414: │   ├── spritesheet-fram12/
L4415: │   ├── spritesheet-fram10/
L4416: │   ├── spritesheet-fram8/
L4417: │   ├── greenhero_hd_stand_N.png
L4418: │   └── … weitere Einzelbilder
L4419: ├── comic_mid/                 ← gleiche Frame-Ordner und verkleinerte Einzelbilder
L4420: ├── comic_low/
L4421: ├── pixel_high/
L4422: └── pixel_low/
L4423: ```
L4424: 
L4425: Verarbeitet werden alle vorhandenen Frame-Ordner mit 3 bis 64 Zellen und alle
L4426: normalen PNG-Dateien direkt in `comic_high`. Ein Aktionsordner mit ausschließlich
L4427: Einzelbildern funktioniert ebenfalls. Archive, `PixelEng`, versteckte Dateien,
L4428: Dateilinks, vorhandene GIFs und PNGs außerhalb von `comic_high` dienen nicht als
L4429: HD-Quellen.
L4430: 
L4431: Zum Beispiel wird `comic_high/greenhero_hd_stand_N.png` nach
L4432: `comic_mid/greenhero_hd_stand_N.png`, `comic_low/greenhero_hd_stand_N.png`,
L4433: `pixel_high/greenhero_hd_stand_N.png` und `pixel_low/greenhero_hd_stand_N.png`
L4434: umgerechnet. Diese Einzelbilder werden nicht zu GIFs zusammengefasst.
L4435: 
L4436: | Verarbeitungsskript | Voreinstellung pro Einzelbild bzw. Frame |
L4437: | --- | --- |
L4438: | `SComicMid.py` | 50 % der HD-Breite und -Höhe |
L4439: | `SComicLow.py` | 25 % der HD-Breite und -Höhe |
L4440: | `SPixelHigh.py` | längste Seite maximal 128 px, bis zu 64 Farben |
L4441: | `SPixelLow.py` | 90 % der tatsächlichen Pixel-High-Größe, dieselbe Farbpalette (standardmäßig 64 Farben) |
L4442: 
L4443: Die Comic-Stufen und Pixel High entstehen direkt aus HD. Pixel Low reproduziert
L4444: Pixel High aus derselben HD-Quelle und verkleinert dessen Frames ohne neue
L4445: Farbmischung. Die bisherige zusätzliche Reduktion auf 16 Farben entfällt.
L4446: Bei 128 px High entstehen 115 px Low; bei kleineren High-Frames gilt ebenfalls
L4447: der Faktor 0,9. Die vorhandene High-Datei wird dabei nicht verändert.
L4448: Transparente Ränder gehören zur Frame-Größe; kleinere Bilder werden nicht
L4449: vergrößert. Comic wird glatt
L4450: verkleinert, Pixel erhält eine gemeinsame reduzierte Palette pro Sheet und
L4451: harte Transparenzkanten.
L4452: 
L4453: Mit `--palette-profile /pfad/.color_profile/reference-colors.json` verwendet
L4454: Pixel High/Low stattdessen die gemeinsame feste Stand-Palette aus der
L4455: [Color-Pipeline](../SpritesheetColor-Pipline/README.md), über alle Sheets hinweg.
L4456: Die Palette im Profil ersetzt dabei die Farbzahlvorgaben für beide Pixelstufen;
L4457: Comic behält seine feinen Abstufungen. Bereits vorhandene Ausgaben werden auch
L4458: mit diesem Schalter nur bei zusätzlichem `--overwrite` neu erstellt.
L4459: 
L4460: `--palette-profile` akzeptiert das Format `pyimg-reference-colors` mit
L4461: `pixel_palette`. Die neuen Color-Formate `pyimg-fixed-palette` und
L4462: `pyimg-material-colors` sind keine gültigen Resolution-Palettenprofile; diese
L4463: Pipeline verarbeitet keine Materialmasken. Comic-Skalierung kann durch Glättung
L4464: neue Mischfarben erzeugen. Für exakte Festfarben auch in diesen Comic-Ausgaben
L4465: ist anschließend eine ausdrückliche erneute Farbzuordnung erforderlich; bei
L4466: Materialfarben müssen die Masken zu den skalierten Bildern passen.
L4467: 
L4468: ## Gemeinsamer visueller Test
L4469: 
L4470: Nach dem Durchlauf `aufloesungsvergleich.html` im Startordner im Browser öffnen.
L4471: Die Seite funktioniert offline ohne Server. Sie lädt die vorhandenen PNG-
L4472: Spritesheets über relative Dateipfade und zeigt die passende Rasterzelle im
L4473: Browser an. Normale PNGs erscheinen als „Einzelbild“ in derselben Auswahl und
L4474: werden vollständig angezeigt; die Wiedergabe- und FPS-Regler sind dann deaktiviert.
L4475: Beim Start und beim Wechsel der Auswahl werden nur die fünf Bilder der gewählten
L4476: Animation bzw. Einzelbildgruppe und Richtung geladen. FPS-Wechsel und Frameschritte
L4477: verwenden diese geladenen Bilder weiter.
L4478: 
L4479: Es werden weder Bilddaten eingebettet noch zusätzliche Frame-PNGs oder GIFs für
L4480: die Vorschau erzeugt. Das bisherige 128-MiB-Einbettungslimit entfällt. Auch die
L4481: Seiten `gif-vergleich.html` je Frame-Ordner verwenden vorhandene Spritesheets.
L4482: Beim Verschieben oder Weitergeben den Aktionsordner mit HTML, PNG-Spritesheets
L4483: und GIF-Unterordnern zusammenhalten. Der Browser benötigt weiterhin Speicher
L4484: für die gerade geladenen Bilder.
L4485: 
L4486: Die Vergleichsseite bietet:
L4487: 
L4488: - Comic High/HD, Comic Mittel, Comic Low, Pixel High und Pixel Low nebeneinander.
L4489: - Gleiche Anzeigegröße bei unterschiedlichen tatsächlichen Pixelauflösungen.
L4490: - Auswahl von Einzelbildern oder Animationen mit Framezahl und den acht Blickrichtungen N, NO, O, SO, S, SW, W, NW.
L4491: - Gemeinsame Wiedergabe, Pause, Einzelbildschritte und Frame-Regler.
L4492: - Gemeinsame Vorschau-FPS: **2, 4, 6, 8, 10, 12, 16, 18, 20, 22 oder 24**.
L4493: - Gemeinsame Anzeigegröße, Hintergrundfarbe und optionale Vorschauglättung.
L4494: 
L4495: So lassen sich Farben, Konturen und Unschärfe bei gleicher Animationsphase
L4496: vergleichen. Comic Mittel wird vorerst nicht zusätzlich nachgeschärft.
L4497: Fehlende PNG-Varianten erscheinen als Hinweis. Die gemeinsame Vorschau benötigt
L4498: keine GIFs; vorhandene GIFs bleiben über einen zusätzlichen Link erreichbar.
L4499: `comic_high` bleibt unverändert. Die Vorschau zeigt alle Rasterzellen, auch
L4500: Leerzellen und identische Nachbarframes. Sie zeigt die PNG-Farben und Transparenz;
L4501: Farbänderungen oder Transparenzverluste des GIF-Exports sind darin nicht sichtbar.
L4502: Die FPS-Auswahl ändert nur die Vorschau, nicht die gespeicherten Dateien.
L4503: 
L4504: Nur die Vergleichsseite aus den vorhandenen Ergebnissen neu erstellen:
L4505: 
L4506: ```bash
L4507: PyPiplineStart-SpritesheetResolution --compare-only
L4508: ```
L4509: 
L4510: Nach erfolgreicher Neuerstellung entfernt das Skript die unveränderten,
L4511: anhand ihres Inhalts und Hash-Dateinamens erkannten Bildkopien im alten
L4512: `aufloesungsvergleich-bilder`-Ordner. Bei den einzelnen GIF-Galerien gilt dasselbe
L4513: für `gif-vergleich-bilder`. Fremde oder veränderte Dateien, Links und Unterordner
L4514: werden dabei beibehalten. Leere Cache-Ordner werden entfernt.
L4515: 
L4516: `PyGraphicsCompare.py` und `PyGraphicsPoseCompare.py` gehören als
L4517: Vergleichsmodule zu den Pipeline-Dateien. Beide beim Installieren mitnehmen.
L4518: `PyImgGif.py` liegt gemeinsam für Resolution, Fram8, Fram16 und FramReduce unter `Pipline/PiplineToos/`.
L4519: Fram8 und Fram16 verwenden dort außerdem `PyImgGrid.py` und `PySpritesheetPipeline.py`.
L4520: Der Installer übernimmt diese Struktur; die Hilfsmodule bekommen keine Terminal-Wrapper.
L4521: 
L4522: ## CLI: eine Pose oder alle Posen
L4523: 
L4524: `--spritesheet` / `-s` verarbeitet eine Pose. Ohne Modus bleibt dies der Standard.
L4525: `--spritesheet-all` / `-s-a` startet im gemeinsamen Posenordner und findet Posen
L4526: auch in Unterordnern. Jeder Ordner mit `comic_high` gilt als Pose. Versteckte
L4527: Ordner, Verzeichnislinks und die Variantenordner werden bei dieser Suche
L4528: ausgelassen. Alle Posen werden vor der ersten Ausgabe geprüft.
L4529: 
L4530: ```bash
L4531: PyPiplineStart-SpritesheetResolution -s /pfad/posen/jump
L4532: PyPiplineStart-SpritesheetResolution -s-a /pfad/posen
L4533: PyPiplineStart-SpritesheetResolution --spritesheet-all /pfad/posen --output-root /pfad/ergebnisse
L4534: ```
L4535: 
L4536: Die Unterstruktur der Posen bleibt auch bei `--output-root` erhalten. Standardmäßig
L4537: werden sämtliche vorhandenen Raster und alle vier kleineren Auflösungen erstellt.
L4538: Die hochauflösenden Quellen und eventuell dort vorhandene GIFs bleiben unverändert.
L4539: 
L4540: ```text
L4541: posen/
L4542: ├── jump/
L4543: │   ├── comic_high/spritesheet-fram{8,10,12,14,16}/  # Quellen
L4544: │   ├── comic_mid/spritesheet-fram{8,10,12,14,16}/   # PNG, GIF, gif-vergleich.html
L4545: │   ├── comic_low/spritesheet-fram{8,10,12,14,16}/
L4546: │   ├── pixel_high/spritesheet-fram{8,10,12,14,16}/
L4547: │   ├── pixel_low/spritesheet-fram{8,10,12,14,16}/
L4548: │   └── aufloesungsvergleich.html
L4549: ├── walk/                                         # gleicher Aufbau
L4550: └── positionsvergleich.html                       # nur bei -s-a
L4551: ```
L4552: 
L4553: Nur tatsächlich vorhandene Frame-Ordner werden verarbeitet. Einzelbilder
L4554: bleiben im Auflösungsvergleich sichtbar; der Positionsvergleich zeigt Animationen.
L4555: Posen mit ausschließlich Einzelbildern erscheinen deshalb nicht in seiner Auswahl.
L4556: `--no-gif` unterdrückt sämtliche GIF- und HTML-Ausgaben auch bei `-s-a`.
L4557: 
L4558: ## Größen- und Positionsvergleich
L4559: 
L4560: `positionsvergleich.html` direkt im Browser öffnen. Die Seite lädt ausschließlich
L4561: vorhandene PNGs und GIFs über relative Links. Sie enthält weder eingebettete
L4562: Bilddaten noch externe Bibliotheken und benötigt keinen Server. Beim Kopieren
L4563: die gesamte Ergebnisstruktur mitnehmen; bei einer separaten Ausgabe liegen
L4564: HD-Verweise weiterhin im Quellordner.
L4565: 
L4566: - Pose A wählen, optional Pose B hinzufügen, etwa Jump und Walk.
L4567: - Eine der acht Richtungen N, NO, O, SO, S, SW, W, NW auswählen.
L4568: - Auflösungen und Raster wie 4×4 oder 7×7 beliebig kombinieren.
L4569: - Alle gewählten Ebenen zunächst am gleichen Ursprung überlagern. Der untere
L4570:   Abstandsregler zieht sie stufenlos auseinander und wieder zusammen.
L4571: - Zwischen tatsächlichen Pixelgrößen und einem gemeinsamen HD-Maßstab wechseln.
L4572:   Zoom und Deckkraft einstellen; Leinwandmitte, unten mittig oder oben links als
L4573:   Ursprung wählen. Transparente Ränder werden weder beschnitten noch verschoben.
L4574: - Leinwandrahmen, Ursprung und sichtbare Inhaltsgrenzen einblenden. Eine Ebene
L4575:   als Referenz wählen und Positions- und Größenunterschiede je Frame in der
L4576:   Tabelle ablesen. Leere Frames haben keine messbaren Inhaltsgrenzen.
L4577: - Einzelne Ebenen ausblenden oder direkt ihre PNG-/GIF-Dateien öffnen.
L4578: 
L4579: Die **Synchronvorschau** liest die vorhandenen Spritesheet-Zellen. Sie ermöglicht
L4580: gemeinsame FPS, Wiedergabe/Pause, Einzelbildschritte und einen Frame-Regler.
L4581: „Gleiche Animationsphase“ passt unterschiedliche Framezahlen auf einen gemeinsamen
L4582: Zyklus an; die gewählten FPS gelten für den längsten Zyklus. „Gleiche Framenummer“
L4583: spielt jede Animation mit derselben Bildrate und ihrer eigenen Framezahl ab.
L4584: Die Messwerte basieren auf den PNG-Frames; Alpha-Werte unter 16 werden dabei
L4585: als unsichtbar gewertet. Ohne HD dient die größte verfügbare Variante der
L4586: jeweiligen Animation als Größenbezug; die Tabelle kennzeichnet diesen Fall.
L4587: 
L4588: **Original-GIFs** zeigt die tatsächlich exportierten Animationen mit GIF-Farben,
L4589: GIF-Transparenz und ihrer gespeicherten Bildrate. Die Überlagerungs-, Größen-
L4590: und Abstandsregler funktionieren auch hier. Native GIF-Wiedergabe im Browser
L4591: erlaubt keine gemeinsame FPS-/Pause-/Frame-Steuerung; diese Regler und die
L4592: Frame-Messwerte sind in dieser Ansicht deaktiviert. Dafür zur Synchronvorschau
L4593: wechseln. Vorhandene GIFs bleiben auch ohne Spritesheet-PNG darstellbar.
L4594: 
L4595: ## Vorhandene Ergebnisse weiterverwenden
L4596: 
L4597: | Option | Verhalten |
L4598: | --- | --- |
L4599: | `--gif-only` | GIFs und HTML aus vorhandenen Varianten-PNGs; keine PNG-Skalierung oder PNG-Erzeugung |
L4600: | `--html-only` | Fehlende GIF-Galerien und Vergleichsseiten erstellen; PNGs und GIFs unverändert lassen |
L4601: | `--compare-only` | Fehlende Auflösungsvergleiche und bei `-s-a` den Positionsvergleich erstellen |
L4602: | `--overwrite` | Ausgaben der gewählten Verarbeitung erneuern, einschließlich HTML |
L4603: | `--dry-run` | Eingaben und Ausgabewege prüfen, ohne Dateien zu schreiben |
L4604: 
L4605: ```bash
L4606: PyPiplineStart-SpritesheetResolution -s --gif-only --fps 12
L4607: PyPiplineStart-SpritesheetResolution -s-a /pfad/posen --gif-only
L4608: PyPiplineStart-SpritesheetResolution -s-a /pfad/posen --html-only --overwrite
L4609: PyPiplineStart-SpritesheetResolution -s-a /pfad/posen --compare-only --overwrite
L4610: ```
L4611: 
L4612: Diese drei Modi funktionieren auch ohne HD-Originale, wenn Varianten-PNGs bzw.
L4613: GIFs vorhanden sind. Fehlende Auflösungen werden im Vergleich angezeigt und
L4614: nicht nachberechnet. Für reine HTML-Erstellung sind ausschließlich vorhandene
L4615: GIFs ebenfalls ausreichend. `--gif-only` benötigt Spritesheet-PNGs in mindestens
L4616: einer gewählten Zielvariante. Die Optionen sind untereinander und mit `--no-gif`
L4617: nicht kombinierbar. Vorhandene Ausgaben bleiben ohne `--overwrite` erhalten.
L4618: Das gilt auch für ein eigenes `--gif-script`: Es verarbeitet temporäre PNG-Kopien;
L4619: die Pipeline übernimmt nur die vorgesehenen GIFs gemäß dem gewählten Ausgabemodus.
L4620: 
L4621: ## Spritesheet- und spätere Texturmodule
L4622: 
L4623: Die bisherigen Worker wurden in `SComicLow.py`, `SComicMid.py`, `SPixelHigh.py`
L4624: und `SPixelLow.py` umbenannt; direkte Aufrufe und Installationsverweise entsprechend
L4625: anpassen. Die Ausgabeordner heißen weiterhin `comic_low`, `comic_mid`,
L4626: `pixel_high` und `pixel_low`.
L4627: 
L4628: `--Textur` / `--textur` / `-t` ist bereits in `-h` dokumentiert und für die spätere
L4629: Texturskalierung mit `TComicLow.py`, `TComicMid.py`, `TPixelHigh.py` und
L4630: `TPixelLow.py` reserviert. Diese Module und ihre Skalierungsregeln sind noch
L4631: nicht implementiert. Der Aufruf beendet sich mit einer klaren Meldung und
L4632: Exit-Code 2, ohne Daten zu erzeugen.
L4633: 
L4634: ## Vorhandenes GIF-Skript
L4635: 
L4636: Die Pipeline führt `PyImgGif.py` als Programm aus, nachdem die PNG-Erzeugung
L4637: abgeschlossen ist. GIFs und HTML-Seiten je Frame-Ordner kommen aus diesem
L4638: Werkzeug; der gemeinsame Auflösungsvergleich entsteht zusätzlich. Beide
L4639: HTML-Ansichten verwenden vorhandene Spritesheets. In `gif-vergleich.html` stehen
L4640: die FPS unter „Feste FPS“ global und auch je Animation zur Auswahl. Fehlt zu
L4641: einem GIF ein passendes Spritesheet (zum Beispiel bei einem fremden GIF oder
L4642: einem Solo-Export), zeigt diese Galerie das Original-GIF ohne FPS- und
L4643: Einzelbildsteuerung; sie erzeugt dafür keine zusätzlichen Bilddateien.
L4644: 
L4645: Eine einzelne GIF-Galerie ohne erneute GIF-Konvertierung aktualisieren:
L4646: 
L4647: ```bash
L4648: python3 /pfad/zu/PyImgGif.py --html-only --overwrite
L4649: ```
L4650: 
L4651: Diesen Befehl im jeweiligen Frame-Ordner ausführen.
L4652: 
L4653: ## Erneuter Durchlauf und freiwillige Optionen
L4654: 
L4655: Im **Normalmodus** werden fehlende PNGs, GIFs und HTML-Seiten ergänzt. Alle
L4656: vorhandenen Dateien bleiben unverändert. Unlesbare oder veraltete GIFs werden
L4657: gemeldet und ohne `--overwrite` nicht ersetzt. Vorhandene HTML-Seiten behalten
L4658: ihren bisherigen Stand. Wenn du HD-Bilder geändert hast oder die ausgewählten
L4659: Ausgaben neu berechnen möchtest:
L4660: 
L4661: ```bash
L4662: PyPiplineStart-SpritesheetResolution --overwrite
L4663: ```
L4664: 
L4665: `--overwrite` ersetzt zugehörige PNGs, GIFs und HTML-Seiten. Geänderte HD-Quellen oder neue
L4666: Skalierungseinstellungen werden damit auch auf bestehende Varianten angewendet.
L4667: Originalquellen und fremde Dateien bleiben erhalten. `--variants` und `--frames`
L4668: begrenzen die PNG-/GIF-Erzeugung wie bei einem normalen Lauf.
L4669: Mit `--gif-only --overwrite` werden GIFs und HTML erneuert; PNGs bleiben erhalten.
L4670: Mit `--html-only --overwrite` bzw. `--compare-only --overwrite` werden nur die
L4671: jeweiligen HTML-Seiten erneuert.
L4672: 
L4673: **`--dry-run`** prüft Quellen und Ausgabewege, ohne Dateien oder Ordner anzulegen.
L4674: **`--dry-run --overwrite`** zeigt, welche Ausgaben ersetzt würden, und schreibt nichts.
L4675: 
L4676: Weitere Optionen stehen unter `PyPiplineStart-SpritesheetResolution --help`. `--dry-run` zeigt nur
L4677: den Ablauf; `--no-gif` erzeugt nur PNGs. Zielgrößen bleiben bei Bedarf einstellbar.
L4678: Die vier Verarbeitungsskripte lassen sich auch einzeln im Aktionsordner starten.
L4679: `--frames 8 16` beschränkt nur die Frame-Ordner; die Einzelbilder direkt in
L4680: `comic_high` werden weiterhin verarbeitet. `--grid` gilt ausschließlich für
L4681: Spritesheets, auch wenn ein Einzelbild eine Rasterangabe im Dateinamen enthält.
L4682: 
L4683: Für die GIF-Erstellung stehen dieselben elf Bildraten zur Verfügung:
L4684: 
L4685: ```bash
L4686: PyPiplineStart-SpritesheetResolution --fps 18
L4687: ```
L4688: 
L4689: Der Standard bleibt 8 FPS. Der Export berücksichtigt die 10-ms-Zeitauflösung
L4690: des GIF-Formats; die HTML-Vorschau verwendet die gewählte Bildrate direkt.
L4691: 
L4692: Raster stammen aus dem PNG-Dateinamen oder aus der Ordnerzuordnung:
L4693: 16 → 4×4, 14 → 7×2, 12 → 4×3, 10 → 5×2, 8 → 4×2. Quadratische
L4694: Framezahlen haben ebenfalls eine Zuordnung, etwa 49 → 7×7 und 64 → 8×8.
L4695: Andere Raster benötigen einen Dateinamenhinweis oder `--grid`; die Zellenzahl
L4696: muss zur Zahl in `spritesheet-framN` passen. Ungültige Raster werden
L4697: vor der Ausgabe gemeldet. PNGs behalten alle Zellen; für Leerzellen und
L4698: identische GIF-Frames gelten die Regeln deines vorhandenen GIF-Werkzeugs.
L4699: 
L4700: Voraussetzungen bleiben Python ab 3.10 und Pillow ab 10.3.
L4701: 
L4702: Tests im Werkzeugordner: `python3 -m unittest discover -s tests -v`.
L4703: 
L4704: Optionale Browserprüfungen (lokale HTML-Dateien ohne Server):
L4705: 
L4706: ```bash
L4707: python3 -m pip install playwright
L4708: python3 -m playwright install chromium
L4709: python3 tests/browser_comparison.py -v
L4710: ```
L4711: 
L4712: Playwright wird ausschließlich für diese Tests benötigt.
````
