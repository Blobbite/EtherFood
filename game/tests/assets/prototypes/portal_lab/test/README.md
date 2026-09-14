# HD-Testvorlagen für das Portal-Labor

`F5 → Darstellung → Testversion` verwendet diesen Bildsatz. `HD` und `Ultra`
verwenden ihn ebenfalls, solange kein eigener Portal-Bildsatz dafür vorliegt.
Die sechs SVGs sind außerdem die mitgelieferten Ersatzgrafiken, falls in
einer Variante eine Datei fehlt. Gleichnamige PNGs in diesem Ordner haben
Vorrang beim Laden; die SVG-Vorlagen können daneben erhalten bleiben.
Die gemeinsame F5-Auswahl ist in [der Ordnerübersicht](../README.md) beschrieben.

Originale EtherFood-Testgrafiken als fein gezeichnete HD-Vektorvorlagen.
Alle Texturen besitzen mindestens 1024 Pixel auf der längeren Seite und
lassen sich aus den SVGs höher auflösen. Keine Fremdgrafiken, Shader oder
Animationen. Diese Platzhalter besitzen noch
keine finale Grafikfreigabe und bleiben deshalb unter `game/tests/assets/`.

| Datei | Zweck | Native Größe |
|---|---|---|
| `floor_tile.svg` | Wiederholbare Bodenplatten-Textur | 1024 × 1024 |
| `door.svg` | Statische Portaltür mit Bodenanker unten mittig | 896 × 1024 |
| `lamp.svg` | Lampenplatzhalter | 576 × 1024 |
| `crate.svg` | Objekt- und Shader-Vergleichsfläche | 1024 × 896 |
| `monster.svg` | Gegnerplatzhalter für Größenversuche | 896 × 1024 |
| `particle.svg` | Kleine Partikelprobe | 1024 × 1024 |

Die acht Blau-Grau-Farben sind `#101c28`, `#1b2e40`, `#263d50`, `#304b61`,
`#45667c`, `#7295aa`, `#acc4d2` und `#d8e6ee`. Dieselbe Palette steht in
`game/scenes/dev/portal_lab/blueprint_palette.gd`. Godot importiert die SVGs
verlustfrei, ohne Mipmaps und mit Skalierung 1. Die Darstellung verwendet
standardmäßig Nearest-Neighbor; der vorhandene F5-Filtervergleich bleibt
verfügbar. Die Objekte besitzen feste Weltgrößen und Bodenanker unabhängig
von der verwendeten Bildauflösung. Die gelieferten SVGs ergeben dabei einen
Maßstab von einem Achtel; Partikel werden auf zwölf Weltpixel verkleinert.
Andere Bildauflösungen erhalten automatisch die passende Skalierung.

Der Boden wird von `blueprint_floor.gd` mit der wiederholbaren HD-Textur
und Vektorlinien aus derselben Palette gezeichnet.
Rastergröße, Ausdehnung und Kreisradius lassen sich ohne neue Bilddateien
anpassen. Im Labor steuert `F5 → Maßstab → Tilegröße` das sichtbare Raster.

Raumaufbau und Erweiterung sind in
`docs/system/development/features/portal-testlabor.md` beschrieben.
