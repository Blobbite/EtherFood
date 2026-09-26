# Greenhero Sprint

Sprint verwendet die Greenhero-Run-Spritesheets als Quelle. Die Bilddaten und
Richtungen bleiben identisch zu `../run`; der Unterschied ist ausschließlich
die Wiedergabegeschwindigkeit von **12 FPS**.

## Quelle und Ausgabe

- Quelle: `../run/<qualitaet>/spritesheet-fram<anzahl>/`
- Charakter: `Greenhero`
- Richtungen: `N`, `NO`, `O`, `SO`, `S`, `SW`, `W`, `NW`
- Qualitätsstufen: `comic_high`, `comic_mid`, `comic_low`, `pixel_high`, `pixel_low`
- Framevarianten: `spritesheet-fram8`, `spritesheet-fram10`, `spritesheet-fram12`, `spritesheet-fram14`, `spritesheet-fram16`
- Ziel-GIFs: `characters/heroes/greenhero/previews/gif/sprint/`
- GIF-Takt: `12 FPS` (Endlosschleife)

Die Sprint-Spritesheets werden nicht dupliziert. Bei der Ausgabe werden die
Run-Spritesheets gelesen und als Greenhero-Sprint-GIFs mit 12 FPS exportiert.
Die bestehende Verzeichnisstruktur aus Qualität, Frameanzahl und optionalem
`PixelEng`-Raster bleibt dabei erhalten.
