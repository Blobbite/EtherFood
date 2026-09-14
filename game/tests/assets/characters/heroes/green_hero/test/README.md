# Green Hero: Testposen schnell austauschen

Die Testversion enthält **48 Einzelposen**: `stand`, `walk`, `run`, `sneak`,
`sprint` und `jump` in jeweils acht Richtungen. Jede Pose hat genau ein
Standbild ohne Animationsschleife. Die mitgelieferten 4×4-Raster bleiben als
Quellen erhalten; Godot verwendet die kleineren Einzelbilder.

## Bilder einbinden

1. Pro gewünschter Pose alle acht PNGs unter `sources/` ablegen, beispielsweise
   `greenhero_hd_run_N.png`, `greenhero_hd_run_NO.png`,
   `greenhero_hd_run_NW.png`, `greenhero_hd_run_O.png`,
   `greenhero_hd_run_S.png`, `greenhero_hd_run_SO.png`,
   `greenhero_hd_run_SW.png` und `greenhero_hd_run_W.png`.
2. Im Testordner ausführen:

   ```sh
   ./rename_test_assets.sh --dry-run
   ./rename_test_assets.sh
   ```

3. Godot den Import abschließen lassen. Im visuellen Testlabor unter
   **F5 → Darstellung → Hero-Grafik → Testversion** die Bilder auswählen.
   Erneutes Anklicken lädt die Testressource samt importierten Texturen neu.
   Ohne geöffneten Editor das Projekt nach dem Import neu starten.

Der Namensbestandteil `hd` bezeichnet hier nur die vorbereiteten Quellen:
**Der Import schreibt ausschließlich in Test.** Auch `test`, `ultra` und
`pixel_art` werden an dieser Stelle erkannt. Ein Einzelbild hat Vorrang vor
seinem passenden `*_solo_4x4.png` oder `*_solo_4x4_o.png`. Liegt nur das
benannte Posenraster vor, wird dessen erstes Feld als feste Pose verwendet.

```text
test/
├── sources/                 Originalbilder und ihre Raster
│   ├── imported/            zuletzt eingebundene Bilder als Quellenkopien
│   └── previous/            ersetzte Raster/Einzelbilder bei Formatwechseln
├── stand/                   greenhero_N_stand.png … greenhero_W_stand.png
├── walk/                    greenhero_N_walk.png … greenhero_W_walk.png
├── run/                     greenhero_N_run.png … greenhero_W_run.png
├── sneak/                   greenhero_N_sneak.png … greenhero_W_sneak.png
├── sprint/                  greenhero_N_sprint.png … greenhero_W_sprint.png
├── jump/                    greenhero_N_jump.png … greenhero_W_jump.png
├── stand_walk_manifest.json
├── green_hero_stand_walk_test.tres
├── rename_test_assets.sh
└── README.md
```

Die bisherigen Namen von Manifest und Godot-Ressource bleiben als Einstieg
erhalten; ihr Inhalt umfasst jetzt alle sechs Zustände. Aus `run_NO` lädt
Godot beispielsweise `run/greenhero_NO_run.png`. Richtungen heißen überall
`N`, `NO`, `NW`, `O`, `S`, `SO`, `SW`, `W`.

## Posen im Spiel prüfen

| Bewegung | Bedienung | Testpose |
|---|---|---|
| Stillstand oder blockierte Bewegung | Richtung loslassen oder an eine Wand laufen | `stand` |
| Gehen | Caps Lock aktiviert den Gehmodus | `walk` |
| Laufen / Rennen | normale Richtung / Richtung doppelt drücken | `run` |
| Schleichen | beim Bewegen Strg halten | `sneak` |
| Sprinten | beim Rennen zusätzlich Shift halten | `sprint` |
| Springen | Leertaste | `jump` |

Nach dem Landen folgt wieder die passende Bodenpose. Alle Zustände verwenden
dieselben acht Richtungen; im Stand bleibt die letzte Blickrichtung erhalten.

## Einzelne Aktionen und andere Eingangsordner

Ohne Optionen importiert das Skript alle erkannten benannten Posen. Jede
ausgewählte Aktion muss vollständig sein. Fehlende Richtungen, doppelte
Einzelbilder oder unterschiedliche Bildfelder brechen vor dem Ersetzen ab.
Originaldateien bleiben erhalten; ein Schreibfehler stellt den vorherigen
Bestand wieder her. Bei einem Formatwechsel werden bisherige Laufzeitbilder
unter `sources/previous/<Prüfsumme>/` archiviert.

```sh
./rename_test_assets.sh --action run
./rename_test_assets.sh --action jump
./rename_test_assets.sh --action both
./rename_test_assets.sh --source-dir "/pfad/zu/neuen bildern"
```

`both` beschränkt den Import auf Stand und Walk. Quellen dürfen auch in
`sources/stand/`, `sources/walk/`, `sources/run/` usw. liegen; diese Unterordner
haben Vorrang vor gemeinsam abgelegten Bildern. Benannte Posen in `sources/`
haben beim automatischen Import Vorrang vor alten losen Rastern in `test/`.
Laufzeitordner sowie `sources/imported/` und `sources/previous/` werden nie
automatisch als neue Eingangsordner gelesen.

Der Skriptpfad darf aus einem anderen Arbeitsverzeichnis aufgerufen werden.
Benötigt wird Python ab Version 3.11, ohne zusätzliche Pakete.

## Maßstab und frühere Rasterimporte

Die aktuellen Einzelbilder messen **1436 × 1254 Pixel**, ihre Raster
**5744 × 5016 Pixel**. Transparente Ränder bleiben erhalten. Alle Posen
verwenden die Standkalibrierung: 1205 Grafikpixel entsprechen 80 Weltpixeln,
der Fußanker liegt bei `(718, 1224)`. Dadurch werden gebeugte und springende
Posen nicht auf die Höhe der aufrechten Figur gestreckt.

Bei unverändertem Bezugsfeld bleibt die Kalibrierung erhalten. Ein neuer
vollständiger Satz mit anderen Maßen erhält zunächst die Feldhöhe als
Referenzhöhe und die untere Feldmitte als Fußanker. Transparente Außenränder
oder besondere Fußpunkte müssen danach im Manifest kalibriert werden.

Der frühere Import acht allgemeiner `N_solo_4x4.png` bis `W_solo_4x4.png`
bleibt verfügbar. Diese unbenannten Raster ergeben 16 Frames mit je 120 ms
für Stand und Walk. Solche Raster können aus einem eigenen Eingangsordner
eingelesen werden:

```sh
./rename_test_assets.sh --source-dir "/pfad/zu/rastern" --action both
```

Dabei bleiben zusätzliche Aktionen erhalten. Alternativ werden kanonische
Namen wie `greenhero_N_walk_spritesheet_4x4_o.png` und alte kleingeschriebene
WASD-Namen gelesen: `greenhero_w_…` steht für Norden, `greenhero_a_…` für
Westen. Ausgaben verwenden immer die deutschen Himmelsrichtungen.

Alle Dateien bleiben bis zur finalen Freigabe im Testbestand. Weitere Details:
[Green Hero – Stehen und Gehen](../../../../../../../docs/system/development/features/green-hero-stand-und-gehen.md).
