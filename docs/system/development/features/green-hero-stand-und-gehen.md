<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Funktion: Green Hero – Stehen und Gehen

## Ziel und Umsetzungsstand

Der spielbare `HeroCharacter` verwendet seit dem 8. September 2026
standardmäßig den Green Hero anstelle der bisherigen Platzhaltergrafik.
Eingebunden sind die Ultra-Folgen für Stehen und Gehen: acht Richtungen, 16
Frames je Folge und damit insgesamt 256 Frames aus 16 optimierten PNG-Sheets.
Am 10. September 2026 wurden die acht Stand-Sheets durch die neue Hero-Version
ersetzt. Jedes neue Stand-Sheet wiederholt sein Einzelbild in allen 16 Feldern;
es zeigt daher eine ruhende Pose. Auf Benutzerwunsch werden dieselben Sheets
auch unter `walk/` eingesetzt, um die neue Figur beim Bewegen zu prüfen.
Die Figur wechselt ihre Blickrichtung, zeigt dabei aber dieselbe ruhende Pose
wie im Stand; eine Gehbewegungsschleife ist für diese Testversion nicht aktiv.
Im visuellen Testlabor stehen vier getrennte Varianten bereit: HD, Pixel Art,
Ultra und Testversion. HD enthält die frühere animierte Fassung aus
Git mit 640-Pixel-Bezugsfeld. Seit dem 11. September 2026 verwendet die
Testversion 48 Einzelposen mit 1436 × 1254 Pixeln: Stand, Gehen, Laufen/Rennen,
Schleichen, Sprinten und Springen in acht Richtungen. Ihr Skript ermöglicht
den schnellen Austausch. Pixel Art verwendet ein Standbild je Richtung und Aktion.

Alle Charakter- und Prototypgrafiken liegen bis zur finalen Freigabe unter
`game/tests/assets/`. Die aktuelle Verwendung in Szenen ist keine Freigabe;
die Regel steht unter [Asset-Ablage und Freigabe](../architecture/asset-ablage-und-freigabe.md).

Die vorhandenen Bewegungswerte, Kollision, Interaktion, Kamera und Sprungkurven
bleiben davon getrennt. Lange und genervte Wartefolgen sind noch nicht
eingebunden. HD, Pixel Art und Ultra verwenden für alle Bodenbewegungsstufen
die Gehfolge; ein Sprung zeigt dort weiterhin das erste Standbild der
Blickrichtung. Nur Test besitzt die zusätzlichen, nicht animierten Posen.

## Laufzeitassets und Richtungen

Die Laufzeitdateien liegen unter:

```text
game/tests/assets/characters/heroes/green_hero/
├── hd/                         frühere animierte Fassung, 640-px-Bezugsfeld
│   ├── sources/stand/ und sources/walk/
│   ├── stand/ und walk/
│   ├── stand_walk_manifest.json
│   └── green_hero_stand_walk_hd.tres
├── pixel_art/                  bestehende 265-px-Einzelbilder
│   ├── stand/ und walk/
│   ├── stand_walk_manifest.json
│   └── green_hero_stand_walk_pixel_art.tres
├── ultra/                      neue 4×4-Sheets für Stand und Walk
│   ├── sources/stand/ und sources/walk/
│   ├── stand/ und walk/
│   ├── stand_walk_manifest.json
│   └── green_hero_stand_walk_ultra.tres
└── test/                       austauschbarer Testbestand
    ├── sources/                Einzelposen und Raster; imported/ und previous/
    ├── stand/, walk/, run/, sneak/, sprint/ und jump/
    ├── stand_walk_manifest.json
    ├── green_hero_stand_walk_test.tres
    ├── rename_test_assets.sh
    └── README.md
```

Alle vier Varianten verwenden dieselben großgeschriebenen deutschen
Himmelsrichtungen in Quellen, Laufzeitdateien, Manifesten und Godot-Namen:

| Kürzel | Spielrichtung | Godot: Stehen / Gehen |
|---|---|---|
| `N` | Norden | `stand_N` / `walk_N` |
| `NO` | Nordosten | `stand_NO` / `walk_NO` |
| `NW` | Nordwesten | `stand_NW` / `walk_NW` |
| `O` | Osten | `stand_O` / `walk_O` |
| `S` | Süden | `stand_S` / `walk_S` |
| `SO` | Südosten | `stand_SO` / `walk_SO` |
| `SW` | Südwesten | `stand_SW` / `walk_SW` |
| `W` | Westen | `stand_W` / `walk_W` |

Beispiel: `NO_solo_4x4_o.png` gehört zu
`stand/greenhero_NO_stand_spritesheet_4x4_o.png` beziehungsweise
`walk/greenhero_NO_walk_spritesheet_4x4_o.png`. Pixel Art verwendet
`greenhero_NO_stand.png` und `greenhero_NO_walk.png`. Test verwendet dieselbe
Einzelbildbenennung für alle sechs Aktionen, beispielsweise
`test/jump/greenhero_NO_jump.png`. Die mitgelieferte Quelle heißt
`test/sources/greenhero_hd_jump_NO.png`; der Bestandteil `hd` ändert ihre
Zuordnung zur Testversion nicht.

Die Umstellung verändert ausschließlich Namen und Verweise. Blickrichtung,
Bildinhalt, Zeitdaten und Fußanker bleiben erhalten. Die Bewegungssteuerung
verwendet weiterhin ihre semantischen Eingabeaktionen. Das Feld `source_file`
im Pixel-Art-Manifest dokumentiert den ursprünglichen externen Dateinamen;
für Godot ist der neue Pfad unter `runtime_file` maßgeblich.

## Geprüfte Bild- und Zeitdaten

Die HD- und Ultra-Folgen behalten 16 Frames, eine Endlosschleife und
120 Millisekunden je Frame, entsprechend `8,333…` Frames pro Sekunde.
Ultra wiederholt dieselbe Pose innerhalb des Rasters. Die Frames werden
zeilenweise von links nach rechts aus dem 4×4-Raster gelesen. Test enthält
stattdessen je Aktion und Richtung genau einen Frame ohne Schleife. Der
Controller hält diese Einzelbilder auf Frame 0 an.

Ultra verwendet für Stand und Gehen ein Bezugsfeld von 1254 × 1254 px.
Ultra verwendet je Richtung folgende Zuschnitte:

| Animation | Ausschnitt im jeweiligen Bezugsfeld `(x, y, b, h)` |
|---|---|
| `stand_N` | `(266, 19, 721, 1205)` |
| `stand_NO` | `(167, 19, 919, 1205)` |
| `stand_O` | `(152, 19, 949, 1205)` |
| `stand_SO` | `(150, 19, 954, 1205)` |
| `stand_S` | `(171, 19, 911, 1205)` |
| `stand_SW` | `(150, 19, 954, 1205)` |
| `stand_W` | `(153, 19, 949, 1205)` |
| `stand_NW` | `(168, 19, 919, 1205)` |
| `walk_N` | `(266, 19, 721, 1205)` |
| `walk_NO` | `(167, 19, 919, 1205)` |
| `walk_O` | `(152, 19, 949, 1205)` |
| `walk_SO` | `(150, 19, 954, 1205)` |
| `walk_S` | `(171, 19, 911, 1205)` |
| `walk_SW` | `(150, 19, 954, 1205)` |
| `walk_W` | `(153, 19, 949, 1205)` |
| `walk_NW` | `(168, 19, 919, 1205)` |

`AtlasTexture.margin` stellt das zur Folge gehörende Bezugsfeld wieder her,
ohne die entfernten transparenten Ränder erneut in den PNGs zu speichern.

Die neue Standreferenz ist 1205 Grafikpixel hoch, ihr Fußanker liegt bei
`(627, 1224)`. Daraus folgen die Texturskalierung `80 / 1205` und der
Sprite-Offset `(0, -597)`. Für den Bewegungstest verwendet Gehen dieselbe
Normalisierung und denselben Fußanker.
Der Generator speichert diese Werte je Animation in der Ressource; der
Controller übernimmt sie bei Animations- und Ressourcenwechseln. So bleiben
Größenbezug und Fußanker beim Wechsel zwischen Stehen und Gehen stabil.
Die bestehende `Appearance`-Skalierung arbeitet weiterhin darüber.

HD verwendet die frühere Referenzhöhe von 618 Grafikpixeln und den Fußanker
`(320, 625)` im 640-Pixel-Bezugsfeld. Auch hier erzeugt der Generator dieselbe
80-Weltpixel-Referenzhöhe. Seine ursprünglichen Stand- und Gehfolgen sind
getrennte Animationen. Der Benutzer hat diesen früheren Bildsatz für HD
bestätigt.

## Technischer Aufbau

```text
HeroCharacter
├── Visual
│   ├── Shadow
│   └── JumpVisual
│       ├── Appearance
│       │   └── TextureScale
│       │       └── HeroSprite (AnimatedSprite2D)
│       └── FacingMarker
├── CollisionShape2D
├── InteractionDetector
├── PlayerCamera
└── AnimationController
```

`HeroCharacter` gewinnt aus dem bereits normalisierten Bewegungsvektor eine
achtteilige Animationsrichtung, bevor er seine ältere vierteilige
Interaktionsrichtung bestimmt. Bei Stillstand bleibt die letzte
Animationsrichtung erhalten.

Der getrennte `AnimationController` liest nur Zustand und tatsächliche,
kollisionsbereinigte Bodenbewegung des Helden. Er liest keine Tasten und
verändert weder Geschwindigkeit noch Weltposition. Daher zeigt eine gegen eine
Wand laufende Figur die passende Standfolge. Bei einem Richtungswechsel während
des Gehens werden Frame und Teilfortschritt übernommen, statt die Schrittfolge
neu zu starten. Bewegungssperren wechseln auf Stehen. Für Test ordnet er die
vorhandenen Bewegungszustände wie folgt zu:

| Zustand | Testaktion |
|---|---|
| Stillstand oder blockierte Bewegung | `stand` |
| Gehen (`WALK`) | `walk` |
| Laufen (`JOG`) und Rennen (`RUN`) | `run` |
| Schleichen (`SNEAK`) in Bewegung | `sneak` |
| Sprinten (`SPRINT`) | `sprint` |
| Aktiver Sprung | `jump` |

Die Sprungpose folgt derselben bestehenden Sprungkurve. Nach dem Landen
kehrt die Figur zur passenden Bodenpose zurück. Fehlt die Zusatzaktion in
einer anderen Variante, verwendet Bodenbewegung weiterhin `walk`; beim
Springen wird Frame 0 der richtungsbezogenen Standfolge eingefroren.

## Grafikvergleich im Testlabor

Das [visuelle Testlabor](visuelles-testlabor.md#hero-grafikvergleich) kann die
Ultra-Ressource der dortigen Heldeninstanz gegen die unabhängigen HD-, Test-
oder Pixel-Art-Ressourcen austauschen. Pixel Art enthält dieselben 16 Namen für
Stehen und Gehen in acht Richtungen, aber jeweils genau ein Pixelart-Standbild
auf einem transparenten `265 × 265`-Canvas.

Die sichtbare Höhe von 245 Quellpixeln wird auf dieselben 80 Weltpixel wie die
Ultra-Referenz normiert; ein gemeinsamer Fußanker verhindert einen Sprung der
Weltposition. Die Auswahl wird nur lokal gespeichert. Der gemeinsame
`HeroCharacter`, sein Controller und der Heldenraum behalten standardmäßig die
Ultra-Ressource, bis eine spätere Entscheidung ausdrücklich etwas anderes
festlegt.

Das Menü zeigt **HD**, **Pixel Art**, **Ultra** und **Testversion** in zwei
Spalten. Alle vier Auswahlen werden über stabile IDs lokal gespeichert. Ein
erneuter Klick auf Testversion lädt deren Ressource einschließlich bereits
von Godot importierter Texturen neu.

## Reproduzierbarer Import

`game/tools/generate_green_hero_animations.py` liest ausschließlich das
versionierte Manifest. Es prüft Namen, Richtungszuordnung, Raster, Framefolge,
Zeitdaten, sichere relative Pfade, Dateihashes und PNG-Eigenschaften. Ultra
und HD verweisen auf ihre mitgelieferten Sheets unter `sources/stand/` und
`sources/walk/`. Das aktuelle Testmanifest deklariert sechs Aktionen unter
`actions` und verweist auf Kopien der eingebundenen Einzelbilder unter
`sources/imported/`. Die 48 ursprünglichen Einzelbilder und die 48 Raster
liegen unter `sources/`; beim Formatwechsel ersetzte Laufzeitraster bleiben
unter `sources/previous/<Prüfsumme>/` erhalten.
Ein externer Quellordner ist für diese Pakete nicht nötig. Fehlende oder
widersprüchliche Daten brechen den Vorgang ab; es gibt keinen stillen Ersatz.

```bash
python game/tools/generate_green_hero_animations.py
python game/tools/generate_green_hero_animations.py --check
python game/tools/generate_green_hero_animations.py --manifest game/tests/assets/characters/heroes/green_hero/hd/stand_walk_manifest.json --check
python game/tools/generate_green_hero_animations.py --manifest game/tests/assets/characters/heroes/green_hero/test/stand_walk_manifest.json --check
```

Der Prüfmodus verändert keine Datei. Ein frischer Checkout lässt sich allein
anhand der versionierten Testassets prüfen. `--source-root` bleibt für
Manifestfassungen mit externen Animations-Sheets und GIF-Zeitdaten verfügbar;
die aktuelle Testfassung deklariert solche Quellen nicht. Die
PNG-Importe verwenden verlustfreie Komprimierung, unveränderte Auflösung und
keine Mipmaps; der `AnimatedSprite2D` verwendet `Nearest` und keine
Texturwiederholung.

## Neue Testbilder übernehmen

Vorbereitete Dateien wie `greenhero_hd_run_N.png` in `test/sources/` ablegen
und in `test/` das Skript `./rename_test_assets.sh` ausführen. Es erkennt
`stand`, `walk`, `run`, `sneak`, `sprint` und `jump` und importiert ohne
Optionen alle vorhandenen Gruppen. Jede Gruppe benötigt acht Richtungen.
Einzelbilder haben Vorrang vor passenden `*_solo_4x4.png`-Rastern; liegt nur
ein benanntes Posenraster vor, zeigt die Ressource dessen erstes Feld.

`--dry-run` prüft ohne Änderungen; `--action run` oder eine andere Aktion
beschränkt den Austausch. `--action both` wählt Stand und Walk zusammen.
`--source-dir` liest einen ausdrücklich angegebenen Ordner. Unterordner
wie `sources/run/` haben Vorrang vor gemeinsamen Quellen. Benannte Quellen
unter `sources/` haben beim automatischen Import Vorrang vor losen alten
Rastern in `test/`; erzeugte Laufzeitordner werden nie als Eingang gelesen.

Der bisherige Import allgemeiner `N_solo_4x4.png` bis `W_solo_4x4.png` bleibt
mit `--source-dir "/pfad/zu/rastern" --action both` verfügbar. Er erzeugt 16 Frames mit je
120 ms für Stand und Walk und lässt zusätzliche Aktionen bestehen.

Die Quellen bleiben erhalten. Bei unveränderten Zellmaßen bleibt die bisherige
Kalibrierung bestehen; andere optimierte 4×4-Sheets werden anhand ihrer
Zellhöhe und eines mittigen Fußpunkts unten normalisiert. Zusätzliche Ränder
oder besondere Fußpunkte erfordern eine Kalibrierung im Manifest. Die
ausführliche [Anleitung im Testordner](../../../../game/tests/assets/characters/heroes/green_hero/test/README.md)
beschreibt Namen, Vorrangregeln und den anschließenden Godot-Import.

Die aktuelle Testfassung verwendet 48 vollständige Einzelbilder mit
`1436 × 1254` Pixeln und erhält sämtliche transparenten Ränder.
Die sichtbare Referenzpose liegt bei `(424, 19, 911, 1205)`; 1205 Grafikpixel
werden auf 80 Weltpixel normiert. Der Fußanker `(718, 1224)` ergibt den
Sprite-Offset `(0, -597)`. Erneute Importe mit unveränderten Zellmaßen
erhalten diese Kalibrierung. Dieselben Werte gelten für alle Posen, damit
Schleichen und Springen die Proportionen der aufrechten Figur behalten.
Die historischen Namen `stand_walk_manifest.json` und
`green_hero_stand_walk_test.tres` bleiben stabile Einstiegspfade für alle
sechs Aktionen.

## Prüfvertrag

Automatische Tests sichern Manifest und Generator, die 16 HD-/Ultra-Namen
mit 256 Frames sowie die 48 Testnamen mit je einem Einzelbild, Timings,
Ausschnitte, Ränder, Importoptionen und Texturpfade. Die Laufzeitprüfung deckt
Startzustand, alle acht Richtungen,
Anhalten, eine vollständig blockierte Bewegung, Richtungswechsel mit erhaltener
Phase, Bewegungssperre, Größenreferenz und die Sprungdarstellung ab. Test
prüft außerdem die Eingabewechsel zwischen allen Bewegungsstufen, Landung,
einheitlichen Maßstab und den Rückfall anderer Varianten auf Stand/Walk.
Importtests prüfen Quellenvorrang, Vollständigkeit, Einzelbild-/Rasterwahl,
Teilimporte, Archivierung und Wiederherstellung nach einem Schreibfehler.

Die öffentliche Übersicht der bereits vorhandenen Grafiken steht getrennt
unter [Green Hero – Animationen](../../../game/reference/animations/heroes/green-hero/index.md).
