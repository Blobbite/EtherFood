# Seele für den Portalturm

Die drei gelieferten PNGs sind aktive Testassets. Die Szene
`res://scenes/dev/portal_lab/soul.tscn` verwendet sie über `soul_frames.tres`.
Sie werden weiterhin in ihrer ursprünglichen Auflösung importiert und
nicht umbenannt oder bearbeitet.

| Datei | Verwendung |
|---|---|
| `soul_idle_spritesheet_4x2.png` | Wartet als Endlosschleife auf ein Gespräch. |
| `soul_interact_spritesheet_4x2.png` | Erstes Ansprechen; läuft einmal vor der Nachricht. |
| `soul_depart_spritesheet_4x2.png` | Zweites Ansprechen; läuft einmal bis zum transparenten letzten Frame. |
| `soul_frames.tres` | Drei Godot-Animationen mit jeweils acht Atlasregionen und 6 FPS. |
| `soul_script.svg` | Zwei Zeilen aus zwölf eigens gezeichneten Fantasiezeichen für die Nachricht. |

Alle PNGs sind 1024 × 512 Pixel groß: vier Spalten, zwei Zeilen, je Frame
256 × 256 Pixel. Die Reihenfolge ist zeilenweise von links oben nach rechts
unten. Die Szene zeigt sie mit einem gemeinsamen Bodenanker auf einer
128 × 128 Weltpixel großen Fläche. Der Alphakanal und alle acht Frames der
Abschiedsdatei werden verwendet; auch das vollständig transparente Ende
gehört zur Animation.

Im Turm zur Seele neben dem Startplatz gehen und **E** oder **Controller-A**
drücken. Nach Interact erscheint die Schrift vier Sekunden lang, anschließend
kehrt die Seele zu Idle zurück. **Esc/B** schließt das Gespräch vorzeitig.
Während des Gesprächs ruht die Bewegung; weitere E-Eingaben werden ignoriert.
Erst ein neuer Tastendruck nach der Rückkehr zu Idle beginnt den Abschied.
Die Seele verschwindet nach dem letzten Frame samt lokalem Licht.

Der Zustand bleibt bei Raumwechseln während desselben Laborbesuchs erhalten.
Das Labor verlassen und erneut öffnen, um die Probe zurückzusetzen.
F5 pausiert die Anzeigezeit der Nachricht, solange das Menü offen ist.
Die Grafikvarianten behalten denselben Seelenbildsatz; Nearest/Weich wirkt
auch auf die Soul-Sprites.

Die Glyphen sind frei erfundene Prototypgrafik ohne menschlich lesbaren
Dialogtext und ohne festgelegte Übersetzung oder Bindung an den Spielkanon.
Die `.import`-Dateien enthalten Godots Textureinstellungen; PNGs, SVG und
SpriteFrames sind weiterhin für diese Probe erforderlich.

Siehe [Portal-Testlabor](../../../../../docs/system/development/features/portal-testlabor.md)
und [Asset-Ablage und Freigabe](../../../../../docs/system/development/architecture/asset-ablage-und-freigabe.md).
