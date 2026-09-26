# Q04 — Farbpipeline Bestand

Original: `allsummary(1).md`. SHA-256 der vollständigen Upload-Datei: `55bb37c2fb9909384a89d3ac4c7e4b011f1fa8d0319243c04e436fe567570c69`.

Relevanz: Aktueller dokumentierter Farbvertrag: soft/fixed/material, Masken, Profile und Schreibregeln.

Die Zeilennummern in den folgenden Blöcken beziehen sich auf die Originaldatei. Der Text ist ein Quellenbeleg, keine neu erteilte Arbeitsanweisung.

## Originalzeilen 7386–7712

````text
L7386: ## 📝 README.md — ./3-SpritesheetColor-Pipline/README.md
L7387: 
L7388: # SpritesheetColor-Pipline
L7389: 
L7390: Vereinheitlicht PNG-Farben anhand aller acht Stand-Richtungen. Wählbar sind
L7391: weiche Farbangleichung (`soft`), eine exakte gemeinsame Palette (`fixed`) oder
L7392: feste Farbreihen pro Material mit positionsgenauen Masken (`material`).
L7393: Alle Stand-Frames fließen in die Referenz ein; Alpha gewichtet sichtbare Pixel.
L7394: Ergebnisse liegen getrennt von den Originalen. Die Stand-Referenzen werden
L7395: bytegleich kopiert und ausdrücklich als Referenzen gekennzeichnet.
L7396: 
L7397: | Farbmodus | Ergebnis | Standardausgabe |
L7398: | --- | --- | --- |
L7399: | `soft` | Farben behutsam an Stand annähern; bisheriger Standard. | `<Quelle>-color` |
L7400: | `fixed` | Jeden sichtbaren Zielpixel exakt einer gemeinsamen Palettenfarbe zuordnen. | `<Quelle>-fixed` |
L7401: | `material` | Jeden sichtbaren Zielpixel einer festen Farbe seiner Material-ID zuordnen. | `<Quelle>-material` |
L7402: 
L7403: Die Festfarbenprüfung gilt für **eingefärbte Ziel-PNGs**. Die unveränderten
L7404: Stand-Kopien sind davon ausgenommen. Die [Fortführungsdatei](FORTFUEHRUNG-FESTFARBEN.prompt.md)
L7405: dokumentiert den historischen Entwurf; der ausführbare Vertrag steht hier und
L7406: in `--help`.
L7407: 
L7408: ## Befehl und Installation
L7409: 
L7410: Der installierte Befehl heißt `PyPiplineStart-SpritesheetColor`. Ohne Pfadangabe
L7411: arbeitet er im aktuellen Terminalordner:
L7412: 
L7413: ```bash
L7414: PyPiplineStart-SpritesheetColor --help
L7415: 
L7416: # Direkt aus dem Projektordner, mit Python und installiertem Pillow:
L7417: python3 Pipline/SpritesheetColor-Pipline/PyPiplineStart-SpritesheetColor.py --help
L7418: ```
L7419: 
L7420: Eine bestehende Systeminstallation im aktualisierten PyGameTools-Projektordner
L7421: aktualisieren; der zweite Aufruf ergänzt auch den Color-Befehl:
L7422: 
L7423: ```bash
L7424: python3 PyGameTools.py --update
L7425: sudo python3 PyGameTools.py --apply-system --install-dir "$HOME/.local/share/PyGameTools"
L7426: 
L7427: # Benutzerinstallation ohne sudo:
L7428: python3 PyGameTools.py --install --user-bin
L7429: ```
L7430: 
L7431: Bei einem eigenen Installationsverzeichnis denselben Pfad mit `--install-dir`
L7432: angeben. Details: [PyGameTools-README](../../README.md#installation-unter-linux).
L7433: 
L7434: ## CLI-Optionen
L7435: 
L7436: | Argument / Option | Standard | Bedeutung |
L7437: | --- | --- | --- |
L7438: | `QUELLE` | Aktueller Terminalordner | Flacher PNG-Ordner, Pose oder hd-Wurzel. |
L7439: | `-h`, `--help` | — | Hilfe anzeigen und beenden. |
L7440: | `--color-mode soft\|fixed\|material` | `soft` | Farbverfahren ausdrücklich wählen. |
L7441: | `--reference ORDNER` | Automatische Stand-Suche | Ordner mit acht eindeutigen Stand-Originalen; für Soft oder Profilexport. |
L7442: | `--profile DATEI.json` | Aus Stand bilden | Vorhandenes `pyimg-reference-colors`-Profil für Soft oder Festpalettenexport. |
L7443: | `--fixed-palette DATEI.json` | — | Verbindliche Palette für `fixed`; erforderlich. |
L7444: | `--material-profile DATEI.json` | — | Verbindliche Materialfarbreihen für `material`; erforderlich. |
L7445: | `--mask-dir ORDNER` | — | Labelmasken für `material` oder Materialprofilexport; erforderlich. |
L7446: | `--output-dir ORDNER` | Je Farbmodus, siehe oben | Getrennter Zielordner, weder im Quellbaum noch dessen Elternordner. |
L7447: | `--grid SPALTENxZEILEN` | Aus Frameordner / Streifenrichtung | Quellraster, z.B. `16x1`; maximal 64 Zellen. Einzelbilder bleiben einzeln. |
L7448: | `--strength ZAHL` | `0.75` | Nur Soft: Stärke `0..1`. `0` deaktiviert die Korrektur nach der sRGB-Normalisierung. |
L7449: | `--max-distance ZAHL` | `18` | Nur Soft: Lab-Abstand `1..50` begrenzt die angeglichenen Farbbereiche. |
L7450: | `--export-fixed-palette DATEI.json` | — | Eine gemeinsame Palette aus allen Stand-Referenzen festschreiben. |
L7451: | `--prepare-masks ORDNER` | — | Noch unmarkierte Labelmasken mit Quellbindung und Raster vorbereiten. |
L7452: | `--material-definitions DATEI.json` | — | IDs, Namen und Anzahl Farbstufen für den Materialprofilexport. |
L7453: | `--export-material-profile DATEI.json` | — | Materialfarbreihen aus markierten Stand-Pixeln ableiten. |
L7454: | `--dry-run` | Aus | Eingaben, Verarbeitung und vorhandene Ausgaben prüfen; nichts schreiben. |
L7455: | `--overwrite` | Aus | Ausgaben der gewählten Verarbeitung ersetzen. |
L7456: 
L7457: `--reference` und `--profile` schließen sich aus. Optionen verschiedener
L7458: Farbmodi sind nicht kombinierbar; `--strength` und `--max-distance` werden in
L7459: `fixed` und `material` auch bei Angabe ihrer Standardwerte abgewiesen.
L7460: Vorbereitung und Profilexport sind eigene Aufrufe: dabei kein `--color-mode`,
L7461: `--output-dir`, `--strength` oder `--max-distance` setzen. `--prepare-masks`
L7462: benötigt nur Quelle, bei Bedarf Raster und Schreibmodus.
L7463: 
L7464: Relative Pfade beziehen sich auf den Terminalordner. Dezimalzahlen mit Punkt
L7465: angeben. **Spalten × Zeilen:** Ein waagerechter 16er-Streifen ist `16x1`.
L7466: Die Pipeline erstellt GIFs fest mit **8 FPS und Endlosschleife** sowie
L7467: `farbvergleich.html`; `--fps`, `-f8` und `--no-html` sind keine Color-Optionen.
L7468: 
L7469: ## Weicher Abgleich
L7470: 
L7471: Bestehende Aufrufe behalten das bisherige Verhalten:
L7472: 
L7473: ```bash
L7474: PyPiplineStart-SpritesheetColor /pfad/spritesheet --dry-run
L7475: PyPiplineStart-SpritesheetColor /pfad/spritesheet
L7476: 
L7477: PyPiplineStart-SpritesheetColor /pfad/hd \
L7478:   --reference /pfad/hd/stand/comic_high/spritesheet-fram16/PixelEng
L7479: 
L7480: PyPiplineStart-SpritesheetColor /pfad/weitere-originale \
L7481:   --profile /pfad/hd-color/.color_profile/reference-colors.json
L7482: ```
L7483: 
L7484: Soft nähert Farbton und Farbigkeit in CIELAB-D65 an. L*-Helligkeit bleibt bis
L7485: auf RGB-Rundung und LUT-Interpolation erhalten. Sehr dunkle und fast neutrale
L7486: Farben werden geschützt; der interpolierte 33³-LUT vermeidet harte Farbstufen.
L7487: **Auch `--strength 1` erzeugt keine exakte Palettenzugehörigkeit.**
L7488: Das Verfahren kann gleichfarbige Haare und Leder nicht unterscheiden.
L7489: 
L7490: ## Exakte gemeinsame Palette
L7491: 
L7492: Zuerst einmal die Palette aus sämtlichen Stand-Frames exportieren, danach für
L7493: alle Animationen dieselbe Datei verwenden:
L7494: 
L7495: ```bash
L7496: PyPiplineStart-SpritesheetColor /pfad/spritesheet --grid 16x1 \
L7497:   --export-fixed-palette /pfad/stand-fixed-palette.json
L7498: 
L7499: PyPiplineStart-SpritesheetColor /pfad/spritesheet --grid 16x1 \
L7500:   --color-mode fixed --fixed-palette /pfad/stand-fixed-palette.json \
L7501:   --output-dir /pfad/spritesheet-fixed --dry-run
L7502: ```
L7503: 
L7504: Zum Erzeugen nach der Prüfung dieselben Argumente ohne `--dry-run` verwenden.
L7505: Der Export übernimmt bis zu 64 gemeinsame Stand-Farben aus der bereits
L7506: über alle Frames gebildeten `pixel_palette`. Mit `--profile` kann dafür ein
L7507: vorhandenes Referenzprofil dienen. Das JSON hält die konkrete RGB-Liste und
L7508: Herkunft fest; diese Palette visuell prüfen.
L7509: 
L7510: `fixed` wählt die nächste Farbe nach dem gesamten Lab-Farbabstand. Die gewählte
L7511: sRGB-Farbe wird direkt geschrieben: ohne Mischung, Dithering oder interpolierten
L7512: LUT. Bei Gleichstand gewinnt der erste Eintrag der Profilreihenfolge.
L7513: 
L7514: ## Materialmasken und feste Farbreihen
L7515: 
L7516: Jede Material-ID erhält eine gemeinsame Farbreihe. Die Maske entscheidet, ob
L7517: ein Quellpixel beispielsweise Haare oder Leder zeigt; seine L*-Helligkeit wählt
L7518: anschließend die nächste feste Farbstufe dieses Materials. Auch identische
L7519: Quell-RGB-Werte können bei verschiedenen IDs verschiedene Zielfarben erhalten.
L7520: Gleiche Material-/Farbbedingungen ergeben über alle Frames dieselbe Farbe.
L7521: 
L7522: 1. Pro Quelle eine Maskenvorlage anlegen.
L7523: 2. Material-IDs positionsgenau in **jedem Frame** markieren und visuell prüfen.
L7524: 3. IDs, Namen und gewünschte Farbstufenzahl als Materialdefinition speichern.
L7525: 4. Farbreihen aus allen acht markierten Stand-Richtungen exportieren.
L7526: 5. Alle Zielmasken prüfen und den Materiallauf starten.
L7527: 
L7528: ```bash
L7529: PyPiplineStart-SpritesheetColor /pfad/spritesheet --grid 16x1 \
L7530:   --prepare-masks /pfad/spritesheet/materialmasken
L7531: 
L7532: # Erst nach der Markierung und mit den passenden Materialdefinitionen:
L7533: PyPiplineStart-SpritesheetColor /pfad/spritesheet --grid 16x1 \
L7534:   --export-material-profile /pfad/spritesheet/materialmasken/stand-materials.json \
L7535:   --material-definitions /pfad/spritesheet/materialmasken/materials.definitions.json \
L7536:   --mask-dir /pfad/spritesheet/materialmasken
L7537: 
L7538: PyPiplineStart-SpritesheetColor /pfad/spritesheet --grid 16x1 \
L7539:   --color-mode material \
L7540:   --material-profile /pfad/spritesheet/materialmasken/stand-materials.json \
L7541:   --mask-dir /pfad/spritesheet/materialmasken \
L7542:   --output-dir /pfad/spritesheet-material --dry-run
L7543: ```
L7544: 
L7545: Die vorbereiteten Masken enthalten zunächst nur ID 0 und sind dadurch noch
L7546: **keine gültigen Materialmasken**. Der Export verlangt markierte Stand-Masken;
L7547: der Materiallauf prüft alle benötigten Zielmasken vor der ersten Ausgabe.
L7548: Für den Materialprofilexport müssen die Stand-Referenzen innerhalb der Quelle
L7549: liegen. `--reference` kann sie auswählen; `--profile` ersetzt hier keine Masken.
L7550: 
L7551: Eine Definition sieht so aus; dieses minimale Beispiel legt keine tatsächliche
L7552: Greenhero-Materialzuordnung fest:
L7553: 
L7554: ```json
L7555: {
L7556:   "format": "pyimg-material-definitions",
L7557:   "version": 1,
L7558:   "materials": [
L7559:     {"id": 1, "name": "Beispielmaterial", "levels": 6}
L7560:   ]
L7561: }
L7562: ```
L7563: 
L7564: IDs `1..255` und Namen müssen eindeutig sein; `levels` erlaubt `1..256`.
L7565: Die Farbreihen entstehen ausschließlich aus den markierten Stand-Pixeln. Jeder
L7566: Frame, in dem das jeweilige Material vorkommt, liefert gleich viele Samples;
L7567: Alpha gewichtet darin die Pixel. Materialien ohne markierte Stand-Pixel werden
L7568: abgewiesen. Wenige Farbstufen können gröbere Schattenverläufe erzeugen.
L7569: 
L7570: ### Maskenformat
L7571: 
L7572: Unter `--mask-dir` liegen PNGs mit demselben Namen und relativen Pfad wie die
L7573: Originale, etwa `materialmasken/greenhero_hd_run_spritesheet_N.png`. Jede Maske muss:
L7574: 
L7575: - eine statische 8-Bit-PNG in `L` oder `P`, ohne Transparenz, sein;
L7576: - Bildgröße, Raster, Framezahl und Framepositionen der Quelle beibehalten;
L7577: - bei jedem Quellpixel mit Alpha > 0 eine gültige Material-ID enthalten;
L7578: - bei vollständig transparenten Quellpixeln ID 0 enthalten;
L7579: - die PNG-Textfelder `pyimg_mask_version` = `1`, `pyimg_grid` = z.B. `16x1`
L7580:   und `pyimg_source_sha256` = SHA-256 der zugehörigen Original-PNG enthalten.
L7581: 
L7582: Bei `P` zählen die **Palettenindizes**, bei `L` die Graustufenwerte als IDs.
L7583: Vorschaufarben sind keine Ziel-RGB-Werte. Beim Bearbeiten weder interpolieren
L7584: noch glätten; das PNG-Programm muss IDs und Textfelder erhalten. In Python
L7585: liefert `PyImgFixedColors.mask_metadata(grid, source_sha256)` die passenden
L7586: `pnginfo`-Felder für `Image.save`. Einen Quellhash erst nach Prüfung aktualisieren:
L7587: bei geänderter Quelle kann die alte Materialmarkierung falsch liegen.
L7588: 
L7589: Eine Stand-Maske passt nicht automatisch auf Laufbewegungen. Automatisch
L7590: vorgeschlagene Labels benötigen eine visuelle Kontrolle; technisch gültige IDs
L7591: beweisen keine richtige Haar-/Leder-/Umhangzuordnung. Fehlende Zuordnungen werden
L7592: mit Pixelbereich und Frame gemeldet. Es gibt keinen Rückfall auf Soft.
L7593: 
L7594: ### Greenhero-Daten in diesem Projekt
L7595: 
L7596: Die Vorschläge liegen unter [spritesheet/materialmasken](../../spritesheet/materialmasken/README.md):
L7597: 40 Label-PNGs mit den Originaldateinamen, `materials.definitions.json`,
L7598: `stand-materials.json`, `stand-fixed-palette.json` und `masken-pruefung.json`.
L7599: Die Materialdefinition umfasst Umhang, Kleidung, Haare, Leder, Haut, Metall,
L7600: Konturen und Stoffbesatz. Die Labels sind aus den jeweiligen Frames abgeleitete
L7601: **Vorschläge mit noch ausstehender vollständiger visueller Materialprüfung**.
L7602: Das Materialprofil stammt aus den damit markierten Stand-Pixeln. Der
L7603: Prüfbericht und die Materialvorschau dokumentieren diesen Stand.
L7604: 
L7605: ## Profile, Quellen und Ausgaben
L7606: 
L7607: Die drei Farbprofile sind getrennte, versionierte JSON-Formate:
L7608: 
L7609: | Verwendung | `format` | Farbwerte | Datei im Ergebnisordner |
L7610: | --- | --- | --- | --- |
L7611: | Soft / Resolution-Pixelpalette | `pyimg-reference-colors` | Farbstützpunkte und `pixel_palette` | `.color_profile/reference-colors.json` |
L7612: | Fixed | `pyimg-fixed-palette` | `colors: [[R, G, B], ...]` | `.color_profile/fixed-palette.json` |
L7613: | Material | `pyimg-material-colors` | `materials: [{id, name, colors}, ...]` | `.color_profile/material-colors.json` |
L7614: 
L7615: Fest- und Materialprofile haben `version: 1`, `color_space: "sRGB"` und
L7616: Herkunftsdaten aller acht Stand-Richtungen in der Reihenfolge
L7617: N, NO, O, SO, S, SW, W, NW. Jeder Referenzeintrag enthält `direction`, `path`,
L7618: `sha256`, `size`, `grid` und `frames`. Größen und Raster müssen zusammenpassen,
L7619: die Framezahl muss in allen Richtungen gleich sein. RGB-Tripel enthalten ganze
L7620: Zahlen `0..255`; jede Palette umfasst `1..256` eindeutige Farben. Ein Material
L7621: enthält `id`, `name` und `colors`. Die Exportbefehle erzeugen vollständige Profile
L7622: einschließlich der Herkunfts- und Ableitungsdaten.
L7623: 
L7624: Automatisch werden Stand-Sheets unter
L7625: `stand/comic_high/spritesheet-fram16/PixelEng/` bevorzugt, dann Stand-Einzelbilder
L7626: unter `stand/comic_high/`, danach Stand-PNGs direkt im Quellordner. Es müssen acht
L7627: eindeutige Richtungen vorliegen. Ein gespeichertes Farbprofil kann auch ohne
L7628: seine Referenzbilder angewandt werden; dann kann die Stand-Vorschau fehlen.
L7629: 
L7630: Bei hd-Wurzeln dienen `Pose/comic_high/*.png` und
L7631: `Pose/comic_high/spritesheet-framN/PixelEng/*.png` als Originalquellen.
L7632: Eigenständige 8/10/12/14-Frame-Quellen bleiben eigenständige Varianten.
L7633: Archive, versteckte Ordner, tools und abgeleitete Auflösungen werden ausgelassen.
L7634: In flachen PNG-Ordnern werden nur direkte Original-PNGs verarbeitet; dort können
L7635: Masken deshalb in einem eigenen Unterordner liegen.
L7636: 
L7637: Ohne Frameordner kennzeichnet `spritesheet` im Dateinamen einen 16er-Streifen:
L7638: waagerecht `16x1`, senkrecht `1x16`. Andere Raster benötigen `--grid`.
L7639: Bei gemischten Rastern getrennte Aufrufe mit demselben Profil verwenden.
L7640: Es gibt keinen automatischen Zuschnitt, keine Umordnung oder Frame-Reduktion.
L7641: Einzelbilder bekommen kein GIF.
L7642: 
L7643: `PyImgColorMatch.py` übernimmt Stand-Referenz und Soft-Korrektur,
L7644: `PyImgFixedColors.py` exakte Farben, Masken und Materialprofile. Beide liegen in
L7645: `Pipline/PiplineToos/`. `PyImgGif.py` erstellt die GIFs. `color-build.json`
L7646: dokumentiert Modus, Parameter, Quell-/Profil-/Masken-Hashes und Prüfungen.
L7647: 
L7648: ## PNG-Vertrag und visuelle Prüfung
L7649: 
L7650: Alpha einschließlich Teiltransparenz, unsichtbares RGB, Größe, Position und
L7651: Framefolge bleiben exakt erhalten. Eingebettete ICC-Profile werden vor der
L7652: Farbzuordnung relativ farbmetrisch nach sRGB umgerechnet und im Bericht vermerkt.
L7653: PNGs ohne Profil gelten als sRGB; widersprüchliche Gamma-/Primärfarben und
L7654: 16-Bit-Eingaben werden abgewiesen. Nach der exakten Zuordnung entsteht keine
L7655: weitere Farbmischung. Bei Teiltransparenz hängt die Bildschirmfarbe zusätzlich
L7656: vom Hintergrund ab. Die verbindlichen RGB-Werte stehen in den PNGs; GIFs bleiben
L7657: abgeleitete Vorschauen mit ihren Formatgrenzen.
L7658: 
L7659: `farbvergleich.html` zeigt den Farbmodus, Original, Ergebnis und passende
L7660: Stand-Richtung mit synchronen Frames. Im Materialmodus kommen Materialmaske
L7661: und ID-Legende hinzu; die Vorschau-PNGs liegen unter `.material_masks/` mit
L7662: gleichem relativen Pfad. Alle Richtungen und Frames visuell prüfen. Der Bericht
L7663: kennzeichnet die technische Palettenprüfung getrennt von der Materialtreue.
L7664: Die Seite lädt lokale PNGs: Quell- und Ergebnisordner beim Weitergeben zusammen
L7665: beibehalten. Stand-Referenzkopien sind keine reduzierten Festfarben-Spielgrafiken.
L7666: 
L7667: ## Schreibmodi und weitere Pipelines
L7668: 
L7669: | Schreibmodus | Verhalten |
L7670: | --- | --- |
L7671: | `--dry-run` | Vollständig prüfen; keine Dateien oder Ordner schreiben. |
L7672: | Normal | Fehlende Ausgaben ergänzen, vorhandene Dateien erhalten. |
L7673: | `--overwrite` | Nur Ausgaben der gewählten Verarbeitung ersetzen. |
L7674: | `--dry-run --overwrite` | Auch geplantes Ersetzen nur prüfen. |
L7675: 
L7676: Ungültige Profile, Masken und Optionskombinationen werden vor dem ersten
L7677: Schreiben gemeldet. Geänderte Quellen, Profile, Masken oder Parameter ersetzen
L7678: im Normalmodus keine Ergebnisse. HTML und Berichte werden ebenfalls nur mit
L7679: `--overwrite` erneuert. Für neue Farbvarianten einen eigenen Ausgabeordner
L7680: verwenden. Bereits farbangepasste Ergebnisordner sind keine gültigen Quellen.
L7681: 
L7682: Nach der Farbprüfung können Frame-/Optimierungs- und Resolution-Pipelines
L7683: anschließen. Resolution akzeptiert mit `--palette-profile` ausschließlich die
L7684: gemeinsame `pixel_palette` aus einem `pyimg-reference-colors`-Profil:
L7685: 
L7686: ```bash
L7687: PyPiplineStart-SpritesheetResolution /pfad/hd-color -s-a \
L7688:   --palette-profile /pfad/hd-color/.color_profile/reference-colors.json
L7689: ```
L7690: 
L7691: `pyimg-fixed-palette` und `pyimg-material-colors` sind damit nicht kompatibel;
L7692: die Resolution-Pipeline liest keine Materialmasken. Auch das ältere
L7693: `color_profile.json` von PyImgTestColor/PyImgTuneColor ist ein anderes Format.
L7694: Die Pixelpalette ersetzt bei Pixel High/Low die sonst je Sheet berechneten
L7695: Farben. Comic-Skalierung erzeugt Mischfarben. Falls auch skalierte Comic-PNGs
L7696: exakt zur Palette gehören sollen, ist anschließend eine ausdrückliche erneute
L7697: Zuordnung nötig; Materialmasken müssten zu den neuen Abmessungen passen.
L7698: 
L7699: ## Tests
L7700: 
L7701: ```bash
L7702: python3 -m unittest discover -s .tests -v
L7703: python3 -m unittest discover -s Pipline/SpritesheetResolution-Pipline/tests -p 'test_*.py' -v
L7704: ```
L7705: 
L7706: Die Tests prüfen unter anderem Palettenzugehörigkeit, Materialtrennung bei
L7707: gleichem Quell-RGB, deterministische Farbstufen, Alpha/unsichtbares RGB,
L7708: Masken-/Profilfehler, Schreibmodi und den bisherigen Soft-Modus.
L7709: 
L7710: ## Source-Einzelbilder
L7711: 
L7712: Für Einzelbilder steht die zusätzliche [SourceColor-Pipline](../SourceColor-Pipline/README.md) bereit. Beide Farb-Pipelines verwenden denselben Kern `Pipline/PiplineToos/PyImgColorPipeline.py`; die Spritesheet-Verarbeitung und FramReduce bleiben erhalten.
````
