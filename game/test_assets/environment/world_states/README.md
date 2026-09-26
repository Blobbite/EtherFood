# Originale Weltzustands-Prototypassets

Diese PNG-Dateien bilden den beschädigten und den wiederhergestellten
Debug-Vergleich in derselben schrägen Top-down-Perspektive ab. Die
`1440 × 810` Weltfläche enthält ein Haus, eine Sägewerk-Teststation und ein
Waldstück. Paarige Assets verwenden identische Leinwandgrößen, Positionen und
Grundsilhouetten; nur Material, Bewuchs, Schäden und Atmosphäre unterscheiden
sich. Das ist eine nicht-kanonische Testanordnung und kein festgelegter Ort
der Spielwelt.

Grund, Weg, Gebäude, Sägewerk, Bäume und Pflanzen werden zusammen mit den
Größenreferenzen deterministisch und ohne Netzwerkzugriff erzeugt:

```bash
python game/tools/generate_scale_reference_assets.py
python game/tools/generate_scale_reference_assets.py --check
```

Das Hilfsskript verwendet ausschließlich die Python-Standardbibliothek. Die
Grafiken sind originale EtherFood-Prototypassets und keine Produktionsassets.

## Wolkige Nebeltexturen

`damaged_fog.png` und `restored_fog.png` wurden mit dem eingebauten
Bildgenerator aus den alten Nebelbändern und einer gerenderten Testansicht als
Referenzen neu erzeugt. Verwendeter Prompt:

```text
Use case: stylized-concept
Asset type: transparent fog overlay texture for a top-down pixel-art game test area
Primary request: replace the straight fog bands from Images 1 and 2 with a
genuinely cloudy, irregular mist texture that can cover a much larger outdoor
area around a house, forest, and sawmill
Input images: Image 1 and Image 2 are edit/style references for the old
transparent fog overlays; Image 3 is a style and scale reference for the
existing game scene
Scene/backdrop: genuinely transparent background; fog only
Subject: several broad, overlapping banks of soft-edged low mist, broken into
natural cloud lobes, wisps, gaps, pockets, and varying density; coverage
distributed across the full landscape canvas, with enough clear holes to keep
a player and obstacles readable
Style/medium: restrained 16-bit-inspired pixel art; deliberately clustered
pixels and subtle dither; hard nearest-neighbor-friendly pixel structure, not
a smooth photographic cloud render
Composition/framing: wide 16:9 landscape texture; edge-to-edge coverage that
tiles or overlaps without a visible frame; no single central focal cloud
Color palette: neutral pale blue-gray fog with low saturation; alpha variation
carries most of the density
Constraints: preserve true RGBA transparency; fog pixels must remain
translucent; no fully opaque region; no background color; no scene, ground,
buildings, trees, characters, UI, text, border, logo, or watermark; avoid
straight horizontal bands and repetitive punched-out holes; suitable for later
tinting and opacity control in Godot
```

Für die Projektfassungen wurde das Ergebnis auf ein logisches
`720 × 405`-Raster reduziert, auf `1440 × 810` mit Nearest-Neighbor
verdoppelt, auf 16 Transparenzstufen begrenzt und ohne Metadaten als
komprimiertes RGBA-PNG gespeichert. Die beschädigte Fassung ist kühler und bis
zu 68 Prozent deckend, die wiederhergestellte wärmer und bis zu 38 Prozent
deckend. So bleibt das Wolkenmuster statisch und pixelstabil, während Godot die
eigentliche Variantenstärke weiterhin nur über die Sprite-Deckkraft steuert.
