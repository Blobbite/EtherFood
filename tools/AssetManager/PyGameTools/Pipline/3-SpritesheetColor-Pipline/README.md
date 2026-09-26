# SpritesheetColor-Pipline

Vereinheitlicht PNG-Farben anhand aller acht Stand-Richtungen. Wählbar sind
weiche Farbangleichung (`soft`), eine exakte gemeinsame Palette (`fixed`) oder
feste Farbreihen pro Material mit positionsgenauen Masken (`material`).
Alle Stand-Frames fließen in die Referenz ein; Alpha gewichtet sichtbare Pixel.
Ergebnisse liegen getrennt von den Originalen. Die Stand-Referenzen werden
bytegleich kopiert und ausdrücklich als Referenzen gekennzeichnet.

| Farbmodus | Ergebnis | Standardausgabe |
| --- | --- | --- |
| `soft` | Farben behutsam an Stand annähern; bisheriger Standard. | `<Quelle>-color` |
| `fixed` | Jeden sichtbaren Zielpixel exakt einer gemeinsamen Palettenfarbe zuordnen. | `<Quelle>-fixed` |
| `material` | Jeden sichtbaren Zielpixel einer festen Farbe seiner Material-ID zuordnen. | `<Quelle>-material` |

Die Festfarbenprüfung gilt für **eingefärbte Ziel-PNGs**. Die unveränderten
Stand-Kopien sind davon ausgenommen. Die [Fortführungsdatei](FORTFUEHRUNG-FESTFARBEN.prompt.md)
dokumentiert den historischen Entwurf; der ausführbare Vertrag steht hier und
in `--help`.

## Befehl und Installation

Der installierte Befehl heißt `PyPiplineStart-SpritesheetColor`. Ohne Pfadangabe
arbeitet er im aktuellen Terminalordner:

```bash
PyPiplineStart-SpritesheetColor --help

# Direkt aus dem Projektordner, mit Python und installiertem Pillow:
python3 Pipline/SpritesheetColor-Pipline/PyPiplineStart-SpritesheetColor.py --help
```

Eine bestehende Systeminstallation im aktualisierten PyGameTools-Projektordner
aktualisieren; der zweite Aufruf ergänzt auch den Color-Befehl:

```bash
python3 PyGameTools.py --update
sudo python3 PyGameTools.py --apply-system --install-dir "$HOME/.local/share/PyGameTools"

# Benutzerinstallation ohne sudo:
python3 PyGameTools.py --install --user-bin
```

Bei einem eigenen Installationsverzeichnis denselben Pfad mit `--install-dir`
angeben. Details: [PyGameTools-README](../../README.md#installation-unter-linux).

## CLI-Optionen

| Argument / Option | Standard | Bedeutung |
| --- | --- | --- |
| `QUELLE` | Aktueller Terminalordner | Flacher PNG-Ordner, Pose oder hd-Wurzel. |
| `-h`, `--help` | — | Hilfe anzeigen und beenden. |
| `--color-mode soft\|fixed\|material` | `soft` | Farbverfahren ausdrücklich wählen. |
| `--reference ORDNER` | Automatische Stand-Suche | Ordner mit acht eindeutigen Stand-Originalen; für Soft oder Profilexport. |
| `--profile DATEI.json` | Aus Stand bilden | Vorhandenes `pyimg-reference-colors`-Profil für Soft oder Festpalettenexport. |
| `--fixed-palette DATEI.json` | — | Verbindliche Palette für `fixed`; erforderlich. |
| `--material-profile DATEI.json` | — | Verbindliche Materialfarbreihen für `material`; erforderlich. |
| `--mask-dir ORDNER` | — | Labelmasken für `material` oder Materialprofilexport; erforderlich. |
| `--output-dir ORDNER` | Je Farbmodus, siehe oben | Getrennter Zielordner, weder im Quellbaum noch dessen Elternordner. |
| `--grid SPALTENxZEILEN` | Aus Frameordner / Streifenrichtung | Quellraster, z.B. `16x1`; maximal 64 Zellen. Einzelbilder bleiben einzeln. |
| `--strength ZAHL` | `0.75` | Nur Soft: Stärke `0..1`. `0` deaktiviert die Korrektur nach der sRGB-Normalisierung. |
| `--max-distance ZAHL` | `18` | Nur Soft: Lab-Abstand `1..50` begrenzt die angeglichenen Farbbereiche. |
| `--export-fixed-palette DATEI.json` | — | Eine gemeinsame Palette aus allen Stand-Referenzen festschreiben. |
| `--prepare-masks ORDNER` | — | Noch unmarkierte Labelmasken mit Quellbindung und Raster vorbereiten. |
| `--material-definitions DATEI.json` | — | IDs, Namen und Anzahl Farbstufen für den Materialprofilexport. |
| `--export-material-profile DATEI.json` | — | Materialfarbreihen aus markierten Stand-Pixeln ableiten. |
| `--dry-run` | Aus | Eingaben, Verarbeitung und vorhandene Ausgaben prüfen; nichts schreiben. |
| `--overwrite` | Aus | Ausgaben der gewählten Verarbeitung ersetzen. |

`--reference` und `--profile` schließen sich aus. Optionen verschiedener
Farbmodi sind nicht kombinierbar; `--strength` und `--max-distance` werden in
`fixed` und `material` auch bei Angabe ihrer Standardwerte abgewiesen.
Vorbereitung und Profilexport sind eigene Aufrufe: dabei kein `--color-mode`,
`--output-dir`, `--strength` oder `--max-distance` setzen. `--prepare-masks`
benötigt nur Quelle, bei Bedarf Raster und Schreibmodus.

Relative Pfade beziehen sich auf den Terminalordner. Dezimalzahlen mit Punkt
angeben. **Spalten × Zeilen:** Ein waagerechter 16er-Streifen ist `16x1`.
Die Pipeline erstellt GIFs fest mit **8 FPS und Endlosschleife** sowie
`farbvergleich.html`; `--fps`, `-f8` und `--no-html` sind keine Color-Optionen.

## Weicher Abgleich

Bestehende Aufrufe behalten das bisherige Verhalten:

```bash
PyPiplineStart-SpritesheetColor /pfad/spritesheet --dry-run
PyPiplineStart-SpritesheetColor /pfad/spritesheet

PyPiplineStart-SpritesheetColor /pfad/hd \
  --reference /pfad/hd/stand/comic_high/spritesheet-fram16/PixelEng

PyPiplineStart-SpritesheetColor /pfad/weitere-originale \
  --profile /pfad/hd-color/.color_profile/reference-colors.json
```

Soft nähert Farbton und Farbigkeit in CIELAB-D65 an. L*-Helligkeit bleibt bis
auf RGB-Rundung und LUT-Interpolation erhalten. Sehr dunkle und fast neutrale
Farben werden geschützt; der interpolierte 33³-LUT vermeidet harte Farbstufen.
**Auch `--strength 1` erzeugt keine exakte Palettenzugehörigkeit.**
Das Verfahren kann gleichfarbige Haare und Leder nicht unterscheiden.

## Exakte gemeinsame Palette

Zuerst einmal die Palette aus sämtlichen Stand-Frames exportieren, danach für
alle Animationen dieselbe Datei verwenden:

```bash
PyPiplineStart-SpritesheetColor /pfad/spritesheet --grid 16x1 \
  --export-fixed-palette /pfad/stand-fixed-palette.json

PyPiplineStart-SpritesheetColor /pfad/spritesheet --grid 16x1 \
  --color-mode fixed --fixed-palette /pfad/stand-fixed-palette.json \
  --output-dir /pfad/spritesheet-fixed --dry-run
```

Zum Erzeugen nach der Prüfung dieselben Argumente ohne `--dry-run` verwenden.
Der Export übernimmt bis zu 64 gemeinsame Stand-Farben aus der bereits
über alle Frames gebildeten `pixel_palette`. Mit `--profile` kann dafür ein
vorhandenes Referenzprofil dienen. Das JSON hält die konkrete RGB-Liste und
Herkunft fest; diese Palette visuell prüfen.

`fixed` wählt die nächste Farbe nach dem gesamten Lab-Farbabstand. Die gewählte
sRGB-Farbe wird direkt geschrieben: ohne Mischung, Dithering oder interpolierten
LUT. Bei Gleichstand gewinnt der erste Eintrag der Profilreihenfolge.

## Materialmasken und feste Farbreihen

Jede Material-ID erhält eine gemeinsame Farbreihe. Die Maske entscheidet, ob
ein Quellpixel beispielsweise Haare oder Leder zeigt; seine L*-Helligkeit wählt
anschließend die nächste feste Farbstufe dieses Materials. Auch identische
Quell-RGB-Werte können bei verschiedenen IDs verschiedene Zielfarben erhalten.
Gleiche Material-/Farbbedingungen ergeben über alle Frames dieselbe Farbe.

1. Pro Quelle eine Maskenvorlage anlegen.
2. Material-IDs positionsgenau in **jedem Frame** markieren und visuell prüfen.
3. IDs, Namen und gewünschte Farbstufenzahl als Materialdefinition speichern.
4. Farbreihen aus allen acht markierten Stand-Richtungen exportieren.
5. Alle Zielmasken prüfen und den Materiallauf starten.

```bash
PyPiplineStart-SpritesheetColor /pfad/spritesheet --grid 16x1 \
  --prepare-masks /pfad/spritesheet/materialmasken

# Erst nach der Markierung und mit den passenden Materialdefinitionen:
PyPiplineStart-SpritesheetColor /pfad/spritesheet --grid 16x1 \
  --export-material-profile /pfad/spritesheet/materialmasken/stand-materials.json \
  --material-definitions /pfad/spritesheet/materialmasken/materials.definitions.json \
  --mask-dir /pfad/spritesheet/materialmasken

PyPiplineStart-SpritesheetColor /pfad/spritesheet --grid 16x1 \
  --color-mode material \
  --material-profile /pfad/spritesheet/materialmasken/stand-materials.json \
  --mask-dir /pfad/spritesheet/materialmasken \
  --output-dir /pfad/spritesheet-material --dry-run
```

Die vorbereiteten Masken enthalten zunächst nur ID 0 und sind dadurch noch
**keine gültigen Materialmasken**. Der Export verlangt markierte Stand-Masken;
der Materiallauf prüft alle benötigten Zielmasken vor der ersten Ausgabe.
Für den Materialprofilexport müssen die Stand-Referenzen innerhalb der Quelle
liegen. `--reference` kann sie auswählen; `--profile` ersetzt hier keine Masken.

Eine Definition sieht so aus; dieses minimale Beispiel legt keine tatsächliche
Greenhero-Materialzuordnung fest:

```json
{
  "format": "pyimg-material-definitions",
  "version": 1,
  "materials": [
    {"id": 1, "name": "Beispielmaterial", "levels": 6}
  ]
}
```

IDs `1..255` und Namen müssen eindeutig sein; `levels` erlaubt `1..256`.
Die Farbreihen entstehen ausschließlich aus den markierten Stand-Pixeln. Jeder
Frame, in dem das jeweilige Material vorkommt, liefert gleich viele Samples;
Alpha gewichtet darin die Pixel. Materialien ohne markierte Stand-Pixel werden
abgewiesen. Wenige Farbstufen können gröbere Schattenverläufe erzeugen.

### Maskenformat

Unter `--mask-dir` liegen PNGs mit demselben Namen und relativen Pfad wie die
Originale, etwa `materialmasken/greenhero_hd_run_spritesheet_N.png`. Jede Maske muss:

- eine statische 8-Bit-PNG in `L` oder `P`, ohne Transparenz, sein;
- Bildgröße, Raster, Framezahl und Framepositionen der Quelle beibehalten;
- bei jedem Quellpixel mit Alpha > 0 eine gültige Material-ID enthalten;
- bei vollständig transparenten Quellpixeln ID 0 enthalten;
- die PNG-Textfelder `pyimg_mask_version` = `1`, `pyimg_grid` = z.B. `16x1`
  und `pyimg_source_sha256` = SHA-256 der zugehörigen Original-PNG enthalten.

Bei `P` zählen die **Palettenindizes**, bei `L` die Graustufenwerte als IDs.
Vorschaufarben sind keine Ziel-RGB-Werte. Beim Bearbeiten weder interpolieren
noch glätten; das PNG-Programm muss IDs und Textfelder erhalten. In Python
liefert `PyImgFixedColors.mask_metadata(grid, source_sha256)` die passenden
`pnginfo`-Felder für `Image.save`. Einen Quellhash erst nach Prüfung aktualisieren:
bei geänderter Quelle kann die alte Materialmarkierung falsch liegen.

Eine Stand-Maske passt nicht automatisch auf Laufbewegungen. Automatisch
vorgeschlagene Labels benötigen eine visuelle Kontrolle; technisch gültige IDs
beweisen keine richtige Haar-/Leder-/Umhangzuordnung. Fehlende Zuordnungen werden
mit Pixelbereich und Frame gemeldet. Es gibt keinen Rückfall auf Soft.

### Greenhero-Daten in diesem Projekt

Die Vorschläge liegen unter [spritesheet/materialmasken](../../spritesheet/materialmasken/README.md):
40 Label-PNGs mit den Originaldateinamen, `materials.definitions.json`,
`stand-materials.json`, `stand-fixed-palette.json` und `masken-pruefung.json`.
Die Materialdefinition umfasst Umhang, Kleidung, Haare, Leder, Haut, Metall,
Konturen und Stoffbesatz. Die Labels sind aus den jeweiligen Frames abgeleitete
**Vorschläge mit noch ausstehender vollständiger visueller Materialprüfung**.
Das Materialprofil stammt aus den damit markierten Stand-Pixeln. Der
Prüfbericht und die Materialvorschau dokumentieren diesen Stand.

## Profile, Quellen und Ausgaben

Die drei Farbprofile sind getrennte, versionierte JSON-Formate:

| Verwendung | `format` | Farbwerte | Datei im Ergebnisordner |
| --- | --- | --- | --- |
| Soft / Resolution-Pixelpalette | `pyimg-reference-colors` | Farbstützpunkte und `pixel_palette` | `.color_profile/reference-colors.json` |
| Fixed | `pyimg-fixed-palette` | `colors: [[R, G, B], ...]` | `.color_profile/fixed-palette.json` |
| Material | `pyimg-material-colors` | `materials: [{id, name, colors}, ...]` | `.color_profile/material-colors.json` |

Fest- und Materialprofile haben `version: 1`, `color_space: "sRGB"` und
Herkunftsdaten aller acht Stand-Richtungen in der Reihenfolge
N, NO, O, SO, S, SW, W, NW. Jeder Referenzeintrag enthält `direction`, `path`,
`sha256`, `size`, `grid` und `frames`. Größen und Raster müssen zusammenpassen,
die Framezahl muss in allen Richtungen gleich sein. RGB-Tripel enthalten ganze
Zahlen `0..255`; jede Palette umfasst `1..256` eindeutige Farben. Ein Material
enthält `id`, `name` und `colors`. Die Exportbefehle erzeugen vollständige Profile
einschließlich der Herkunfts- und Ableitungsdaten.

Automatisch werden Stand-Sheets unter
`stand/comic_high/spritesheet-fram16/PixelEng/` bevorzugt, dann Stand-Einzelbilder
unter `stand/comic_high/`, danach Stand-PNGs direkt im Quellordner. Es müssen acht
eindeutige Richtungen vorliegen. Ein gespeichertes Farbprofil kann auch ohne
seine Referenzbilder angewandt werden; dann kann die Stand-Vorschau fehlen.

Bei hd-Wurzeln dienen `Pose/comic_high/*.png` und
`Pose/comic_high/spritesheet-framN/PixelEng/*.png` als Originalquellen.
Eigenständige 8/10/12/14-Frame-Quellen bleiben eigenständige Varianten.
Archive, versteckte Ordner, tools und abgeleitete Auflösungen werden ausgelassen.
In flachen PNG-Ordnern werden nur direkte Original-PNGs verarbeitet; dort können
Masken deshalb in einem eigenen Unterordner liegen.

Ohne Frameordner kennzeichnet `spritesheet` im Dateinamen einen 16er-Streifen:
waagerecht `16x1`, senkrecht `1x16`. Andere Raster benötigen `--grid`.
Bei gemischten Rastern getrennte Aufrufe mit demselben Profil verwenden.
Es gibt keinen automatischen Zuschnitt, keine Umordnung oder Frame-Reduktion.
Einzelbilder bekommen kein GIF.

`PyImgColorMatch.py` übernimmt Stand-Referenz und Soft-Korrektur,
`PyImgFixedColors.py` exakte Farben, Masken und Materialprofile. Beide liegen in
`Pipline/PiplineToos/`. `PyImgGif.py` erstellt die GIFs. `color-build.json`
dokumentiert Modus, Parameter, Quell-/Profil-/Masken-Hashes und Prüfungen.

## PNG-Vertrag und visuelle Prüfung

Alpha einschließlich Teiltransparenz, unsichtbares RGB, Größe, Position und
Framefolge bleiben exakt erhalten. Eingebettete ICC-Profile werden vor der
Farbzuordnung relativ farbmetrisch nach sRGB umgerechnet und im Bericht vermerkt.
PNGs ohne Profil gelten als sRGB; widersprüchliche Gamma-/Primärfarben und
16-Bit-Eingaben werden abgewiesen. Nach der exakten Zuordnung entsteht keine
weitere Farbmischung. Bei Teiltransparenz hängt die Bildschirmfarbe zusätzlich
vom Hintergrund ab. Die verbindlichen RGB-Werte stehen in den PNGs; GIFs bleiben
abgeleitete Vorschauen mit ihren Formatgrenzen.

`farbvergleich.html` zeigt den Farbmodus, Original, Ergebnis und passende
Stand-Richtung mit synchronen Frames. Im Materialmodus kommen Materialmaske
und ID-Legende hinzu; die Vorschau-PNGs liegen unter `.material_masks/` mit
gleichem relativen Pfad. Alle Richtungen und Frames visuell prüfen. Der Bericht
kennzeichnet die technische Palettenprüfung getrennt von der Materialtreue.
Die Seite lädt lokale PNGs: Quell- und Ergebnisordner beim Weitergeben zusammen
beibehalten. Stand-Referenzkopien sind keine reduzierten Festfarben-Spielgrafiken.

## Schreibmodi und weitere Pipelines

| Schreibmodus | Verhalten |
| --- | --- |
| `--dry-run` | Vollständig prüfen; keine Dateien oder Ordner schreiben. |
| Normal | Fehlende Ausgaben ergänzen, vorhandene Dateien erhalten. |
| `--overwrite` | Nur Ausgaben der gewählten Verarbeitung ersetzen. |
| `--dry-run --overwrite` | Auch geplantes Ersetzen nur prüfen. |

Ungültige Profile, Masken und Optionskombinationen werden vor dem ersten
Schreiben gemeldet. Geänderte Quellen, Profile, Masken oder Parameter ersetzen
im Normalmodus keine Ergebnisse. HTML und Berichte werden ebenfalls nur mit
`--overwrite` erneuert. Für neue Farbvarianten einen eigenen Ausgabeordner
verwenden. Bereits farbangepasste Ergebnisordner sind keine gültigen Quellen.

Nach der Farbprüfung können Frame-/Optimierungs- und Resolution-Pipelines
anschließen. Resolution akzeptiert mit `--palette-profile` ausschließlich die
gemeinsame `pixel_palette` aus einem `pyimg-reference-colors`-Profil:

```bash
PyPiplineStart-SpritesheetResolution /pfad/hd-color -s-a \
  --palette-profile /pfad/hd-color/.color_profile/reference-colors.json
```

`pyimg-fixed-palette` und `pyimg-material-colors` sind damit nicht kompatibel;
die Resolution-Pipeline liest keine Materialmasken. Auch das ältere
`color_profile.json` von PyImgTestColor/PyImgTuneColor ist ein anderes Format.
Die Pixelpalette ersetzt bei Pixel High/Low die sonst je Sheet berechneten
Farben. Comic-Skalierung erzeugt Mischfarben. Falls auch skalierte Comic-PNGs
exakt zur Palette gehören sollen, ist anschließend eine ausdrückliche erneute
Zuordnung nötig; Materialmasken müssten zu den neuen Abmessungen passen.

## Tests

```bash
python3 -m unittest discover -s .tests -v
python3 -m unittest discover -s Pipline/SpritesheetResolution-Pipline/tests -p 'test_*.py' -v
```

Die Tests prüfen unter anderem Palettenzugehörigkeit, Materialtrennung bei
gleichem Quell-RGB, deterministische Farbstufen, Alpha/unsichtbares RGB,
Masken-/Profilfehler, Schreibmodi und den bisherigen Soft-Modus.

## Source-Einzelbilder

Für Einzelbilder steht die zusätzliche [SourceColor-Pipline](../SourceColor-Pipline/README.md) bereit. Beide Farb-Pipelines verwenden denselben Kern `Pipline/PiplineToos/PyImgColorPipeline.py`; die Spritesheet-Verarbeitung und FramReduce bleiben erhalten.
