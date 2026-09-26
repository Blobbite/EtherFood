# Fortführung: SpritesheetColor-Pipline um exakte Festfarben erweitern

**Aktualisierung 24.09.2026:** Die unten geplanten Modi `fixed` und `material`
sind inzwischen implementiert. Den gültigen CLI-Vertrag beschreibt die
[README](README.md); Ergebnisse und Prüfungen stehen im
[Umsetzungsbericht](UMSETZUNG-FESTFARBEN.md). Die [Greenhero-Masken](../../spritesheet/materialmasken/README.md)
liegen als technisch vollständige, künstlerisch noch zu prüfende Entwürfe vor.
Der folgende Übergabetext dokumentiert den Stand **vor** dieser Umsetzung.

Stand dieser Übergabe: 24.09.2026. Arbeitsverzeichnis: PyGameTools-Projektordner,
in der bisherigen Sitzung `/workspace`.

## Auftrag und Status dieser Datei

Der Benutzer braucht eine echte Farbvereinheitlichung seines Greenhero über
Animationen und Richtungen hinweg. Die bisherige automatische Annäherung wirkt
ihm zu schwach. Ziel sind **exakte, wiederverwendete Zielfarben**, insbesondere
feste Farbreihen pro Material.

Diese Datei wurde auf Wunsch als Fortführungsprompt erstellt. Beim Erstellen
dieser Dokumentation wurden weder Festfarben-Modi implementiert noch weitere
Bilder verändert. Die unten genannten neuen CLI-Optionen sind ein Entwurf.
Wenn der Benutzer diesen Prompt später zur Umsetzung beauftragt, arbeite am
vorhandenen Code weiter; behandle den Entwurf nicht als bereits vorhandene API.

## Verbindliche Entscheidungen des Benutzers

- Alle **Stand-PNGs aus acht Richtungen** sind die gemeinsame Farbreferenz:
  `N, NO, O, SO, S, SW, W, NW`. Die Auswahl ist geklärt, nicht erneut danach fragen.
- Sämtliche Frames dieser Referenzen berücksichtigen; Richtungen und Frames
  gleich gewichten. Im Beispielsatz sind es 8 Sheets mit zusammen 128 Frames.
- Waagerechte 16er-Streifen heißen im CLI **16x1**, Spalten × Zeilen. Der Benutzer
  hatte sie umgangssprachlich auch als „1x16“ bezeichnet. Nicht wieder verwechseln.
- Originale und unabhängig vorhandene Framevarianten bleiben erhalten.
- `--dry-run`: prüfen, nichts schreiben. Normal: Fehlendes ergänzen, vorhandene
  Dateien erhalten. `--overwrite`: nur Ausgaben der gewählten Verarbeitung ersetzen.
- Gemeinsamer Code gehört nach `Pipline/PiplineToos/`.
- Canvas-Dokumentation: kurze Überschriften und minimale Texte im vorhandenen Stil.
  Vor Änderungen vorhandene Canvas-Dateien als `.bak` sichern; ältere Backups erhalten.

## Bereits umgesetzt

Die fünfte Pipeline `SpritesheetColor-Pipline` ist in `PyGameTools.py` registriert.
Installierter Befehl: `PyPiplineStart-SpritesheetColor`.

| Datei | Aufgabe |
| --- | --- |
| `Pipline/SpritesheetColor-Pipline/PyPiplineStart-SpritesheetColor.py` | CLI, Quellsuche, Referenzen, Ausgabemodi, PNG/GIF, Vergleichs-HTML und Bericht. |
| `Pipline/PiplineToos/PyImgColorMatch.py` | Profilbildung, PNG-/ICC-Verarbeitung, weicher Farbtransform, Prüfungen und gemeinsame Pixelpalette. |
| `Pipline/PiplineToos/PyImgGif.py` | GIFs mit 8 FPS/Endlosschleife; vorhandenen Export wiederverwenden. |
| `Pipline/PiplineToos/PyPipelineOutputs.py` | Gemeinsame Schreibregeln und atomare Textausgaben. |
| `Pipline/SpritesheetResolution-Pipline/PyPiplineStart-SpritesheetResolution.py` | Besitzt bereits `--palette-profile` für eine feste gemeinsame Pixelpalette. |
| `Pipline/SpritesheetResolution-Pipline/SPixelHigh.py`, `SPixelLow.py` | Können dieselbe feste Pixelpalette statt eigener Paletten pro Sheet verwenden. |
| `.tests/test_color_pipeline.py` | Farbabbildung, Alpha/unsichtbares RGB, ICC, Quellen, Modi und Pixelpalette. |
| `.tests/test_installer.py` | Installierte fünf Wrapper einschließlich Color testen. |

Dokumentation: `Pipline/SpritesheetColor-Pipline/README.md` und die Projekt-README.
Die Canvas-Dateien liegen inzwischen **in ihren jeweiligen Pipeline-Ordnern**,
z.B. `Pipline/SpritesheetColor-Pipline/SpritesheetColor-Pipline.canvas`.
Diese vom Benutzer geänderte Ablage beibehalten.

Aktuell verfügbare Color-Argumente sind ausschließlich:

```text
[QUELLE]
-h / --help
--reference ORDNER    ODER    --profile DATEI.json
--output-dir ORDNER
--grid SPALTENxZEILEN
--strength ZAHL             Standard 0.75, Bereich 0..1
--max-distance ZAHL         Standard 18, Bereich 1..50
--dry-run
--overwrite
```

Color hat derzeit kein `--fps`, `-f8`, `--no-html` oder `--color-mode`.
GIFs laufen fest mit 8 FPS; `farbvergleich.html` wird immer vorgesehen.

## Vorhandene Daten und verifizierter Stand

- `spritesheet/`: 40 Original-PNGs, jeweils 10240×640 Pixel, 16 Frames à 640×640.
- Animationen: `stand`, `walk`, `slowwalk`, `run`, `sneak`, jeweils acht Richtungen.
- Referenzdateien: `spritesheet/greenhero_hd_stand_spritesheet_<Richtung>.png`.
- `spritesheet-color/`: erster Durchlauf, 32 angeglichene Sheets und 8 bytegleiche
  Stand-Kopien, insgesamt 40 PNG-/GIF-Paare.
- `spritesheet-color/farbvergleich.html`: Original, Ergebnis und passende Stand-
  Richtung synchron nebeneinander; voller PNG-Farbumfang, Frame-Regler und Wiedergabe.
- `spritesheet-color/.color_profile/reference-colors.json`: bestehendes Referenzprofil.
- `spritesheet-color/color-build.json`: Parameter, Quellhashes und Prüfungen.

Bei Abschluss der Implementierung bestanden 75 Tests unter `.tests` und 47 Tests
unter `Pipline/SpritesheetResolution-Pipline/tests`, zusammen **122**. Zusätzlich
wurden alle 40 PNG-/GIF-Paare, unveränderte Quellen, bytegleiche Referenzen, Alpha,
GIF-Zyklusdauer 2000 ms und Endlosschleife geprüft. Die Chromium-Prüfung umfasste
40 Auswahloptionen, sechs Sheets, 18 Framewechsel und Wiedergabe ohne JS-Fehler.
Das sind frühere Prüfergebnisse; nach neuen Codeänderungen passend erneut prüfen.
Die künstlerische Materialtreue wurde dadurch nicht als garantiert bestätigt.

Der Benutzer hat darüber hinaus eine hd-Struktur:
`hd/<Animation>/comic_high/`, weitere Comic-/Pixel-Auflösungen und Frameordner
8/10/12/14/16 mit `PixelEng/`. Diese Struktur ist Kontext, nicht pauschal als lokal
vorhanden anzunehmen. Die Quellsuche berücksichtigt Originale in `comic_high`
und `spritesheet-framN/PixelEng`, keine Archive, Tools oder abgeleiteten Auflösungen.
Unabhängige vorhandene 8-Frame-Sheets niemals automatisch aus 16 Frames ersetzen.

## Warum der bisherige Abgleich nur gering wirkt

Das Profil hat `format: pyimg-reference-colors`, `version: 1` und
`method: Lab_D65_chroma_projection_smooth_lut_v1`. Es enthält acht Referenzdatensätze,
bis zu 256 Farbstützpunkte in `colors` und eine gemeinsame Palette mit bis zu
64 Farben in `pixel_palette`. Es enthält **keine Materialzuordnungen**.

`ColorMatcher` zieht Farbton/Farbigkeit in CIELAB-D65 zur Referenz, bewahrt die
L*-Helligkeit weitgehend, schützt nahezu neutrale/dunkle Farben und begrenzt den
Farbabstand. Die Anwendung erfolgt interpoliert über einen 33³-LUT. Selbst bei
`--strength 1` entstehen dadurch keine garantiert identischen Palettenwerte.
Eine Erhöhung der Stärke erfüllt das neue Ziel daher nicht.

Das Profil ist ein anderes Format als `color_profile.json` von
`Tools/PyImgTools/PyImgTestColor.py` / `Tools/PyImageTest/PyImgTuneColor.py`.
Diese älteren Tools nicht stillschweigend umdeuten. Ihr `--allow-color-merges`
erlaubt Farbkollisionen, aktiviert aber keine Materialerkennung.

## Ziel und vorgeschlagener CLI-Vertrag

Erweitere dieselbe Pipeline um ausdrückliche Modi. Alte Aufrufe behalten ihr
bisheriges Verhalten; neue Modi sind keine stillschweigende Änderung des Standards.

| Geplante Option | Vertrag |
| --- | --- |
| `--color-mode soft` | Bisheriger Standard, unveränderte weiche Abbildung. |
| `--color-mode fixed` | Alle sichtbaren Zielpixel erhalten exakt einen RGB-Wert der festen gemeinsamen Zielpalette. |
| `--fixed-palette DATEI.json` | Verbindliche RGB-Liste für `fixed`; aus Stand ableiten und als konkrete Farbpalette dokumentieren. |
| `--color-mode material` | Zuordnung zu festen Farbstufen der jeweiligen Materialpalette. Dies ist das bevorzugte Ziel für Greenhero. |
| `--material-profile DATEI.json` | Material-IDs, Namen und feste Schatten-/Grund-/Lichtfarbreihen. |
| `--mask-dir ORDNER` | Positionsgenaue Materialmasken pro Quell-PNG, mit derselben relativen Ordnerstruktur. |

Diese Namen sind ein konkreter Vorschlag. Falls die Implementierung eine
Anpassung erfordert, die Gründe dokumentieren und README, Hilfe, Tests und
Canvas zusammen aktualisieren. Vorhandene Optionen nicht widersprüchlich belegen.

`fixed` benötigt `--fixed-palette`; `material` benötigt `--material-profile`
und passende Masken. Optionskombinationen aus verschiedenen Modi zurückweisen.
`--strength` und `--max-distance` wirken nur in `soft`. Werden sie in einem
Festfarben-Modus ausdrücklich gesetzt, verständlich ablehnen, statt sie heimlich
zu ignorieren oder RGB-Werte mit dem Original zu mischen.

Geplante Aufrufe nach der Implementierung:

```bash
# GEPLANT, beim Stand dieser Übergabe noch NICHT ausführbar:
PyPiplineStart-SpritesheetColor /pfad/spritesheet \
  --color-mode fixed --fixed-palette /pfad/stand-fixed-palette.json \
  --output-dir /pfad/spritesheet-fixed --dry-run

PyPiplineStart-SpritesheetColor /pfad/spritesheet \
  --color-mode material --material-profile /pfad/stand-materials.json \
  --mask-dir /pfad/spritesheet-masks \
  --output-dir /pfad/spritesheet-material --dry-run
```

Zum Erzeugen später `--dry-run` weglassen; `--overwrite` nur für bewusste
Neuerstellung verwenden. Einen neuen Zielordner für die Festfarben-Vorschau
wählen, damit der vorhandene weiche Vergleich erhalten bleibt.

## Profile, Masken und tatsächliche Bedeutung von „100 % gleich“

1. **Gemeinsame Palette:** Für `fixed` ein eindeutig versioniertes JSON-Format
   festlegen, z.B. Formatkennung, Version, sRGB-Farbraum, gültige RGB-Tripel und
   Herkunft/Hashes der Stand-Referenzen. Die vorhandenen Stützpunkte können einen
   ersten Vorschlag liefern; ihre Auswahl ist von der später exakten Anwendung
   zu unterscheiden. Keine konkreten „richtigen“ Hex-/RGB-Farben erfinden.
2. **Materialprofil:** Getrennte IDs und feste Farbreihen für Umhang, Kleidung,
   Haare, Leder, Haut, Metall und gegebenenfalls Konturen. Weitere Materialien nur
   nach tatsächlichem Bildinhalt ergänzen. Die Farbreihen aus Stand ableiten.
   Das bisherige globale Profil enthält diese Informationen nicht.
3. **Maskenvertrag:** Pro Zielquelle eine Label-PNG in Originalgröße, mit demselben
   Raster und derselben Framefolge. IDs passen zum Materialprofil; ID 0 kann den
   Hintergrund kennzeichnen. Jeder Pixel mit Original-Alpha > 0 muss im Material-
   Modus eindeutig zugeordnet sein. Fehlende, unbekannte oder widersprüchliche IDs
   sowie falsche Größe/Raster vor dem ersten Schreiben melden.
4. **Bewegte Figuren:** Eine Stand-Maske nicht auf andere Posen kopieren. Körperteile
   bewegen sich zwischen Frames. Gleiche RGB-Werte können Haar und Leder darstellen;
   ein globaler RGB-Filter kann das nicht unterscheiden. Materialerkennung oder
   Farbschwellen dürfen höchstens Vorschläge liefern. Maskenqualität sichtbar prüfen.
5. **Exakte Anwendung:** Nach der Material-/Palettenauswahl den gewählten RGB-Wert
   direkt schreiben. Keine weiche Mischung, kein interpolierter LUT und keine
   weitere Farbtransformation danach. Keine Dithering-Muster zwischen Frames
   erzeugen. Licht/Schatten auf diskrete Stufen der Zielpalette abbilden; kontinuierlich
   unveränderte Helligkeit ist mit einer begrenzten festen Palette nicht garantiert.
6. **PNG-Vertrag:** Alpha einschließlich Teiltransparenz, unsichtbares RGB, Größe,
   Framefolge, Position und Zentrierung exakt erhalten. Verbindlich sind gespeicherte
   sRGB-Werte der PNGs; die Darstellung teiltransparenter Pixel hängt zusätzlich vom
   Hintergrund ab. GIFs bleiben abgeleitete Vorschauen mit ihren Formatgrenzen.
7. **Stand bleibt Referenz:** Originale und bisherige Stand-Referenzkopien bleiben
   unverändert und werden als Referenz ausgewiesen. Die Festfarben-Prüfung gilt für
   eingefärbte Ziel-PNGs. Werden zusätzlich Stand-Spielgrafiken mit derselben reduzierten
   Palette gewünscht, separate Zielkopien erzeugen und eindeutig kennzeichnen.
   Niemals behaupten, unveränderte HD-Referenzkopien hätten bereits die kleinere Palette.

Die Garantie bedeutet: jedes eingefärbte Pixel gehört exakt zur zulässigen
Palette bzw. zur Palette seines Materials. Sie bedeutet nicht, dass jede Richtung
alle Palettenfarben enthalten muss oder dass ein Material keine Schatten mehr hat.
Eine fehlerfreie Maskenbelegung beweist außerdem nicht, dass die Materiallabels
künstlerisch richtig vergeben wurden; die Vorschau bleibt dafür erforderlich.

## Umsetzungsschritte bei späterem Auftrag

1. Aktuellen Code und lokale Anweisungen prüfen. Die verfügbaren Masken und
   Materialdefinitionen ermitteln; im bisherigen Implementierungsstand wurden
   noch keine Materialmasken erstellt. Fehlende konkrete Zuordnungen benennen,
   nicht durch ungesicherte Materialerkennung ersetzen. Bei nötiger Rückfrage
   gezielt nach Materialmarkierungen fragen, die Stand-Auswahl steht bereits fest.
2. Den neuen CLI-Vertrag und die getrennten Profilformate validieren. Den
   bestehenden Soft-Modus und dessen Profilversion weiter lesbar halten.
3. Exakte globale Palettenabbildung im gemeinsamen Modul implementieren.
   Deterministische Auswahl und stabile Auflösung von Farbabstands-Gleichständen
   verwenden; keine neue Palette je Frame, Richtung oder Animation berechnen.
4. Materialmodus mit validierten Labelmasken und festen Farbreihen ergänzen.
   Gleiche Material-/Farbbedingungen werden über sämtliche Frames gleich behandelt;
   unterschiedlich gelabelte Materialien dürfen trotz gleichem Quell-RGB verschiedene
   Zielfarben erhalten. Keinen unerwähnten Rückfall auf Soft-Korrektur erlauben.
5. Modus, Paletten-/Materialprofil-Hashes und Masken-Hashes in die Bestandsprüfung
   und `color-build.json` aufnehmen. Normale Wiederholung mit geänderten Parametern
   darf bestehende Ergebnisse nicht ersetzen. Vorab alle benötigten Masken prüfen.
6. Vergleichs-HTML um den aktiven Modus und eine Material-/Maskenvorschau ergänzen.
   Fehlende Zuordnungen nachvollziehbar anzeigen. PNG-Farben als maßgeblich behandeln.
7. Zusammenspiel mit `SpritesheetResolution` prüfen: bereits existierendes
   `--palette-profile` unterstützt die gemeinsame Pixelpalette, aber nicht automatisch
   die neuen Materialprofile. Keine Formatkompatibilität behaupten, die nicht vorhanden
   ist. Comic-Skalierung kann neue Mischfarben erzeugen; für dort ebenfalls exakte
   Festfarben wäre nach dem Skalieren eine ausdrückliche erneute Zuordnung erforderlich.
8. README und `--help` an den implementierten Vertrag anpassen; neue gemeinsame
   Dateien gegebenenfalls im Installer registrieren. Canvas kurz ergänzen und zuvor
   `.bak` erstellen. Bestehende Canvas-Ablage in den Pipeline-Ordnern erhalten.

## Abnahmekriterien und Prüfung

- Alter Aufruf ohne `--color-mode` ergibt unverändert den bisherigen Soft-Modus.
- Bei `fixed` liegt jeder sichtbare Ausgabe-RGB-Wert exakt in der Zielpalette.
- Bei `material` gehört jeder sichtbare Pixel zur Farbreihe seiner gültigen
  Material-ID. Ein Test muss gleiches Quell-RGB bei zwei verschiedenen Materiallabels
  abdecken, z.B. Haare und Leder mit unterschiedlichen Zielfarben.
- Alpha, unsichtbares RGB, Geometrie, Framezahl und Reihenfolge bleiben erhalten.
- Wiederholte identische Farb-/Materialbedingungen ergeben dieselben Zielfarben;
  keine separat geschätzten Paletten oder zufällige Zuordnung je Frame.
- Fehlende Masken, falsche Größe, unbekannte IDs, ungültige RGB-Werte und
  widersprüchliche CLI-Optionen führen vor dem Schreiben zu verständlichen Fehlern.
- Normalmodus erhält vorhandene PNGs, GIFs, HTML und Berichte; `--dry-run` schreibt
  auch mit `--overwrite` nichts. Quellen und fremde Dateien bleiben erhalten.
- Stand-Referenzkopien bleiben bytegleich und sind von Festfarben-Prüfwerten getrennt.
- GIFs/HTML sind vollständig, zeigen die richtigen Frames und laufen bei 8 FPS.
- Für Materialkorrektheit die Vorschau beurteilen; technische Palettenzugehörigkeit
  allein nicht als Beweis für die richtige Haar-/Leder-/Umhangzuordnung ausgeben.

Vorhandene Testaufrufe, Python-Umgebung mit Pillow vorausgesetzt:

```bash
python3 -m unittest discover -s .tests -v
python3 -m unittest discover -s Pipline/SpritesheetResolution-Pipline/tests -p 'test_*.py' -v
```

Die frühere lokale Testumgebung unter `/tmp/pygametools-grid-tests-xqs4d83i/`
ist flüchtig und keine Installationsvoraussetzung. Pfade und verfügbaren Browser
bei einer neuen Sitzung prüfen. Ergänze gezielte Tests für die neuen Verträge;
keine erneuten Massenläufe auf Originaldaten, bevor die Schreibmodi geprüft sind.
