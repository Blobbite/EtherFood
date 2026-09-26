<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Funktion: Green Hero – Animations-Testmatrix

## Ziel und Umfang

Das visuelle Testlabor prüft den Green Hero in fünf bereitgestellten
Grafikvarianten und fünf Frames-/FPS-Stufen. Die Testassets liegen ausschließlich
unter `game/test_assets/`; ihre Verwendung im Labor ist keine finale Freigabe.

| Grafik-ID | Anzeige | Auflösungsebene |
|---|---|---|
| `comic_high` | Comic High | Comic hoch |
| `comic_mid` | Comic Mittel | Comic mittel |
| `comic_low` | Comic Low | Comic niedrig |
| `pixel_high` | Pixel Art High | Pixel Art hoch |
| `pixel_low` | Pixel Art Low | Pixel Art niedrig |

Für `stand`, `slowwalk`, `walk`, `sneak` und `run` existieren die Raster
`spritesheet-fram8`, `spritesheet-fram10`, `spritesheet-fram12`,
`spritesheet-fram14` und `spritesheet-fram16`. Das Menü schaltet zwischen
8, 10, 12, 14 und 16 Frames um und zeigt daneben die jeweilige Wiedergabe-
geschwindigkeit in FPS. Die acht Richtungen verwenden `N`, `NO`, `O`, `SO`,
`S`, `SW`, `W`, `NW`.

`sprint` verwendet das `run`-Raster mit 12 Frames und wird fest mit 12 FPS
abgespielt. Es gibt keine duplizierten Sprint-PNGs. `jump` verwendet je
Richtung ein PNG mit genau einer Standpose, hält Frame 0 an und läuft nicht.

## Laufzeitmodell

`green_hero_animation_library.gd` baut eine unabhängige `SpriteFrames`
Ressource zur Laufzeit aus den vorhandenen Spritesheets. Die gebauten
Ressourcen tragen die Metadaten `hero_variant`, `hero_frames`, `hero_fps`,
`animation_sources` und `animation_layouts`. Die Quellen bleiben je Aktion und
Richtung getrennt; insbesondere verwendet `walk_SW` die SW-Datei und niemals
die SO-Datei. Der Animationscontroller übernimmt daraus Skalierung und Fußanker
bei jedem Varianten- oder Frames-/FPS-Wechsel.

```text
game/test_assets/characters/heroes/greenhero/spritesheets/
├── stand/<variant>/spritesheet-fram{8,10,12,14,16}/
├── slowwalk/<variant>/spritesheet-fram{8,10,12,14,16}/
├── walk/<variant>/spritesheet-fram{8,10,12,14,16}/
├── sneak/<variant>/spritesheet-fram{8,10,12,14,16}/
├── run/<variant>/spritesheet-fram{8,10,12,14,16}/
└── jump/<variant>/
```

Die normale Bodenbewegung zeigt im Testlabor `walk`. Wird Shift während der
Bewegung gehalten, zeigt der Held `slowwalk`; Rennen und Sprinten behalten ihre
eigenen Stufen. `sneak` hat weiterhin Vorrang. Die vorhandenen Bewegungswerte
und Kollisionsregeln bleiben unverändert.

## Bedienung im Testlabor

Unter `F5 → Darstellung` stehen die fünf Grafikvarianten und die fünf
Animations-Frames/FPS-Kombinationen. Die Umschaltung gilt sofort für den Laborhelden und
bleibt in `user://visual_lab_settings.cfg` erhalten. Portal-Bildvarianten
verwenden weiterhin die vorhandenen Test-/Pixel-Art-Platzhalter und sind von
der Helden-Framerate unabhängig.

Für den manuellen Durchlauf:

1. Jede Grafikvariante und danach jede Frames/FPS-Auswahl anwählen.
2. Stand, Slow Walk, Walk, Sneak, Run und Sprint in allen acht Richtungen
   bewegen; Sprint muss sichtbar mit 12 FPS laufen.
3. In jeder Richtung springen; Jump muss auf einer einzigen Standpose stehen.
4. F5 während Bewegung und Sprung öffnen und schließen; Position,
   Kollisionskörper und Fußanker dürfen nicht springen.

## Automatische Prüfung

`green_hero_animation_test.gd` prüft die vollständige Matrix aus fünf
Varianten, fünf Frame-/FPS-Stufen, sieben Animationstypen und acht Richtungen sowie
Slow Walk, Sneak, Sprint und Jump in der echten `HeroCharacter`-Szene.
`visual_lab_hero_graphics_test.gd` prüft zusätzlich die F5-Auswahl,
Einstellungen, Migration alter Testeinstellungen und das erneute Öffnen des
Labors. Der Python-Test
`tools/tests/test_green_hero_animation_library.py` prüft die Vollständigkeit
der gelieferten PNG-Matrix und die Sprint-Ableitung.

Schnelle Prüfungen:

```text
python3 -m unittest tools.tests.test_green_hero_animation_library
python3 -m unittest tools.tests.test_asset_layout
```

Der vollständige Repository-Standard bleibt `python tools/control.py check`.
Godot-Laufzeittests werden ausgeführt, sobald die Godot-CLI in der
Entwicklungsumgebung verfügbar ist.

## Abgrenzung

Die Grafikvarianten sind Testassets und ändern weder Kanon noch Gamedesign.
Eine finale Übernahme in `game/assets/` benötigt weiterhin die dokumentierte
Asset-Freigabe. `Google Excel Engine` ist kein Repository-Bestandteil; der
Testablauf ist deshalb in die vorhandene Godot-Testszene und ihre Laufzeit-
und Python-Prüfungen integriert.
