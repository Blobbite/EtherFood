# Grafikvarianten des Portal-Labors

Die Grafikschalter unter `F5 → Darstellung → Grafik: Figur und Portal-Labor`
wechseln gemeinsam die Figur und die Blueprint-Texturen. Diese Auswahl wird
lokal gespeichert und gilt auch nach Raumwechseln und beim nächsten Laborstart.

| F5-Auswahl | Bilder für das Portal-Labor |
|---|---|
| Pixel Art | `pixelart/*.png` |
| Testversion | `test/*.png`, ersatzweise `test/*.svg` |
| HD | Vorläufig der Bildsatz aus `test/` |
| Ultra | Vorläufig der Bildsatz aus `test/` |

Für HD und Ultra gibt es derzeit keinen eigenen Portal-Bildsatz. Der
F5-Status nennt die dafür verwendeten Testvorlagen. Die Figur verwendet
weiterhin ihre jeweilige eigene Grafikvariante.

Beide Ordner verwenden dieselben sechs Dateinamen:

| Name ohne Endung | Verwendung | Größe im Raum |
|---|---|---|
| `floor_tile` | Bodenplatte | Eine Textur über vier Rasterzellen je Achse |
| `door` | Hin- und Rückportal | 112 × 128 Weltpixel |
| `lamp` | Lampenprobe | 72 × 128 Weltpixel |
| `crate` | Objekt- und Shaderprobe | 128 × 112 Weltpixel |
| `monster` | Gegnerplatzhalter | 112 × 128 Weltpixel, zusätzlich drei Größenfaktoren |
| `particle` | Partikelprobe | 12 × 12 Weltpixel |

Zum Ersetzen einer Vorlage die gleichnamige PNG- oder SVG-Datei im
gewünschten Ordner ablegen und von Godot importieren lassen. PNG hat Vorrang
vor SVG. Nach dem Import geänderter Bilddateien ein bereits laufendes Spiel
neu starten. Eine fehlende Einzeldatei fällt auf die mitgelieferte SVG-Testvorlage
zurück. Die SVGs unter `test/` deshalb als Grundausstattung erhalten.
Die Bildauflösung darf abweichen; Form und Seitenverhältnis sollten zur
Vorlage passen. Bodenanker liegen unten mittig. Bildwechsel verändern weder
Kollisionen noch Portalpositionen oder Bewegungswerte.

Die zentrale Zuordnung liegt in `game/scenes/dev/portal_lab/portal_graphics.gd`.
`F5 → Maßstab → Tilegröße` steuert weiterhin das Raster. Texturfilter und
Pixel-Snap bleiben unabhängige F5-Testwerte. Die vier Referenzfiguren im
Sprite-Raum zeigen weiterhin gleichzeitig ihre verschiedenen Bildsätze.

Alle Bilder in diesen Ordnern sind Testassets ohne finale Freigabe.
