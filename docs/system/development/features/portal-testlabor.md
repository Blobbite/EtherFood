<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Funktion: Portal-Testlabor

## Zugang und Bedienung

Stand: 12. September 2026.

Das **Visuelle Testlabor** im Entwicklungsmenü öffnet den Portalturm.
Der Held startet in dessen Mitte. Neun beschriftete Türen stehen auf einem
Kreis um den Startplatz. Eine Tür zu betreten öffnet den zugehörigen Testraum.
Dessen Rückportal führt wieder zur gleichen Tür im Turm.

Die Ankunft liegt außerhalb der Türschwelle. Nach einem Wechsel die
Bewegungstasten kurz loslassen; danach sind die Portale wieder benutzbar.
So löst eine gehaltene Richtung keinen sofortigen Rücksprung aus.

Die normale Bewegungssteuerung gilt in allen Räumen. `F5` enthält weiterhin
Kamera, Maßstab, Grafikvarianten und die gespeicherten Testwerte. `F4` zeigt
Kollisionen, `F11` die rahmenlose Spieldiagnose mit dem aktuellen Raum und
`F12` die separate Leistungsanzeige. `Esc` verlässt das Labor. Die Route
`visual_lab` bleibt ausschließlich in Entwicklungsbuilds erreichbar.

Bei einem geöffneten Seelengespräch schließt `Esc` zuerst das Gespräch.

Der frühere gemeinsame Testraum wurde durch die folgenden Räume ersetzt.
Gemeinsame Einstellungen bleiben beim Wechsel erhalten. Lampen, Partikel und
Tageszyklus haben zusätzlich eigene Schaltflächen links unten. Diese
Raumzustände bleiben während eines Laborbesuchs erhalten; der Tageszyklus
pausiert beim Verlassen seines Raums.

## Räume

| Raum | Inhalt und Bedienung |
|---|---|
| Lampenraum | Drei Lampen mit Lichtstärken 0,5, 1,0 und 1,5; gemeinsam ein-/ausschaltbar. |
| Sprite-Testraum | Statische Vergleichsfiguren für HD, Pixel Art, Ultra und Testversion. Die bewegliche Figur verwendet die Auswahl unter `F5 → Darstellung`. |
| Monsterraum | Drei unbewegte Gegnerplatzhalter in unterschiedlichen Größen. |
| Shaderraum | Drei statische Objektflächen als Vorbereitung für spätere Shaderversuche. |
| Objekt-Testraum | Bisherige Größenreferenzen, Bodenraster und Kollisionshindernis sowie drei neue Objektplatzhalter. |
| Partikel-Testraum | Drei einzeln angeordnete Proben: Strahl, Fächer und Streuung; gemeinsam start-/stoppbar. |
| Nebelraum | Vorhandene Weltkulisse mit Nebel, ohne zusätzliche Lichtmodulation. Nebel und Kulisse über `F5 → Welt & Atmosphäre` wählen. |
| Tag-Nacht-Raum | Dieselbe Kulisse ohne Nebel. Schaltflächen für Tag, Dämmerung, Nacht und einen 30-Sekunden-Zyklus zwischen hell und dunkel. Die F5-Lichtauswahl setzt eine feste Tagesphase. |
| Weltzustandsraum | Aufgebaute und zerstörte Kulisse unter neutralem Licht ohne Nebel. Umschalten über `F5 → Welt & Atmosphäre → Weltzustand`. |

Monster und Shaderflächen sind vorbereitete Testplätze. Es wurden keine
Gegner-KI und keine neuen Spieleffekte oder Spielregeln eingeführt. „Spiceraum“
wird hier als Sprite-Testraum verstanden.

## Seele im Portalturm

Neben dem Startplatz schwebt eine leicht blau leuchtende Seele. In ihrer
Nähe erscheint **E / A: Seele ansprechen**. Sie benutzt den vorhandenen
Interaktionsdetektor des Helden und blockiert keine Laufwege.

1. Bis zum ersten Ansprechen läuft `idle` dauerhaft.
2. **E** oder **Controller-A** spielt `interact` einmal. Anschließend erscheint
   für vier Sekunden ein Textfeld mit zwei Zeilen eigens erfundener
   Seelenzeichen. Während des Gesprächs ruht die Bewegung. `Esc/B` kann das
   Gespräch schließen; zusätzliche E-Eingaben lösen keinen Abschied aus.
3. Nach dem Gespräch wartet die Seele wieder in `idle`. Erst das zweite
   Ansprechen spielt `depart` einmal vollständig. Das Leuchten klingt mit
   den Frames ab; nach dem letzten Frame ist die Seele verschwunden.

Die drei gelieferten Raster unter `game/tests/assets/characters/sools/`
enthalten jeweils acht Frames in vier Spalten und zwei Zeilen. Die Szene
`game/scenes/dev/portal_lab/soul.tscn` und `soul_frames.tres` referenzieren
die unveränderten PNGs. Der Abschied verwendet ausdrücklich
`soul_depart_spritesheet_4x2.png`, einschließlich seines transparenten Endes.
`soul_script.svg` zeichnet die Fantasiezeichen unabhängig von installierten
Schriftarten. Die Probe definiert keine verbindliche Sprache oder Spielregel.

Beim Wechsel in einen Testraum und zurück bleiben erstes Gespräch und
Abschied erhalten. Erneutes Öffnen des Labors setzt die Seele zurück.
F5 bleibt verfügbar und pausiert die Anzeigezeit der Nachricht im Menü.
Alle Grafikvarianten verwenden derzeit denselben Seelenbildsatz; der
unabhängige Texturfiltervergleich wirkt auch auf die Seelenanimation.

## Blueprint-Gestaltung

Der Turm verwendet einen kreisförmigen Boden mit umschaltbarer Textur,
Rasterlinien, Markierungen und statischen Türgrafiken. Ein äußerer Kollisionsring
begrenzt die begehbare Fläche.
Die Boden-Rastergröße folgt `F5 → Maßstab → Tilegröße` mit 32, 48 oder 64 Pixeln,
ohne Objekte oder Türen zu skalieren. Die Fußbodenkomponente bietet im
Godot-Inspector zusätzlich Größe und Radius der Fläche an.

Die SVG-Testvorlagen und gezeichneten Bodenmarkierungen verwenden acht
Blau-Grau-Grundfarben:

| Verwendung | Farbe |
|---|---|
| Umgebung | `#101c28` |
| Tiefe Flächen | `#1b2e40` |
| Boden | `#263d50` |
| Vertiefungen | `#304b61` |
| Raster | `#45667c` |
| Kanten | `#7295aa` |
| Beschriftung | `#acc4d2` |
| Helle Markierungen | `#d8e6ee` |

Die Türen besitzen weder Shader-Material noch Animation oder Partikel.
Die Heldenvarianten und vorhandenen Vergleichskulissen in den Fachräumen
behalten ihre eigenen Grafiken. Beleuchtungsversuche finden im Lampen- und
Tag-Nacht-Raum statt. Der Turm behält neutrales Umgebungslicht; die Seele
ergänzt ein schwaches, räumlich begrenztes blaues Licht.

Die SVG-Testvorlagen liegen unter
`game/tests/assets/prototypes/portal_lab/test/`. Bodenplatte, Tür, Lampe, Objekt,
Monster und Partikel besitzen mindestens 1024 Pixel auf der längeren Seite.
Feine Konturen und Vektorformen ersetzen grobe Pixelstufen. Godot importiert
die Texturen verlustfrei in nativer HD-Größe; die sichtbare Größe im Raum
wird davon getrennt skaliert. Die acht Grundfarben gelten für die Vorlagen;
Kantenglättung und der optionale Filtervergleich können Zwischenwerte erzeugen.
Es sind noch keine freigegebenen Spielassets.

## F5-Grafikvarianten für Figur und Portal-Labor

Seit dem 12. September 2026 schaltet die bestehende Auswahl unter
`F5 → Darstellung → Grafik: Figur und Portal-Labor` auch Boden, Hin- und
Rückportale, Lampen, Objekt- und Shaderproben, Monsterplatzhalter und
Partikel um. Die Wahl gilt sofort im geöffneten Raum und wird bei allen
weiteren Raumwechseln sowie nach einem Neustart wieder verwendet.

| Auswahl | Bildsatz unter `game/tests/assets/prototypes/portal_lab/` |
|---|---|
| Pixel Art | Benutzer-PNGs unter `pixelart/` |
| Testversion | Testvorlagen unter `test/` |
| HD | Vorläufig die HD-Testvorlagen unter `test/` |
| Ultra | Vorläufig die HD-Testvorlagen unter `test/` |

HD und Ultra haben derzeit keinen eigenen Portal-Bildsatz. Das F5-Menü
zeigt deshalb zusätzlich zum Figurenstatus den tatsächlich verwendeten
Portal-Bildsatz. F11 enthält dieselbe Zuordnung in der Spieldiagnose.
Die vier Vergleichsfiguren im Sprite-Testraum bleiben gleichzeitig sichtbar.

`portal_graphics.gd` ordnet die sechs Namen `floor_tile`, `door`, `lamp`,
`crate`, `monster` und `particle` ihren Dateien zu. Gleichnamige PNGs haben
Vorrang vor SVGs. Fehlende Einzeldateien verwenden die mitgelieferte
SVG-Testvorlage. Neue oder ersetzte Dateien müssen zunächst von Godot
importiert werden. Die Benutzer-PNGs werden unverändert eingebunden.
Der aktuelle Pixel-Art-Bildsatz hat keinen Alphakanal; seine schwarzen
Bildhintergründe bleiben sichtbar, bis freigestellte PNGs eingesetzt werden.

Alle Objektgrößen und Bodenanker sind unabhängig von der nativen Auflösung.
Der Wechsel baut den Raum nicht neu auf und erhält Portalpositionen,
Kollisionen, Kamera, Bewegung und Raumzustände. Rastergröße, Texturfilter und
Pixel-Snap bleiben unabhängige Testwerte. Die gezeichneten Ringmarkierungen
verwenden bei Pixel Art harte Kanten und bei den Testvorlagen Kantenglättung.

## Einen Raum ergänzen

Die Erweiterungsstelle ist `game/scenes/dev/portal_lab/rooms.tres`. Ihre
Reihenfolge bestimmt die Nummerierung der Türen im Turm. Jede Definition
enthält eine eindeutige `room_id`, `title`, `description` und die `scene`.
Der Name `hub` ist für den Turm reserviert.

1. Unter `game/scenes/dev/portal_lab/rooms/` eine Szene von `test_room.tscn`
   ableiten. Für einen leeren neuen Fachraum `room_kind` auf eine eigene ID
   setzen. Neue Testobjekte unter `Contents` hinzufügen.
2. `world_size`, `return_portal_position` und `return_arrival_offset` im
   Inspector passend zur Fläche festlegen. Türschwelle und Ankunftspunkt
   freihalten. Den Ankunftspunkt mit Abstand außerhalb der Schwelle wählen.
3. Im Katalog eine `test_room_definition.gd`-Ressource mit neuer ID,
   Beschriftung und der Szene hinzufügen. Den Eintrag in `rooms` aufnehmen.
4. Den Turm öffnen, beide Wege testen und die Kollisionsanzeige mit `F4`
   kontrollieren. Bei zusätzlichen Raumfunktionen die Laufzeittests erweitern.

Die Navigation erstellt die Tür im Turm und das Rückportal automatisch. Bei
mehr Räumen wächst der Portalradius, damit die Türen Abstand behalten; Boden,
Kollisionsring und Kameragrenzen wachsen mit. Es ist jeweils eine Raumszene
aktiv. Die vorhandenen Größen- und Weltvorschauen werden nur im passenden
Raum eingeblendet. Gemeinsame Spiel- und Testeinstellungen verwaltet weiterhin
`visual_lab.gd`.

## Prüfung und Abgrenzung

`game/tests/runtime/portal_lab_test.gd` prüft tatsächliche Hin- und Rückwege
durch alle neun Türen, sichere Ankunft, gehaltene Bewegung, fremde Körper,
Raumzustände, gemeinsame Testwerte, getrennte Effekte und einen auf 33 Räume
erweiterten Katalog. `portal_lab_graphics_test.gd` prüft die echten
F5-Menüschalter, alle sechs Texturarten in sämtlichen Räumen, gespeicherte
Auswahl, Weltgrößen, Anker und unveränderte Raumeigenschaften.
`tools/tests/test_portal_lab_assets.py` prüft die Vollständigkeit beider
Bildsätze, die SVG-Palette, Auflösungen, Vektorgeometrie, neue Pfade und Importe.
`portal_lab_soul_test.gd` prüft die drei gelieferten Raster, Reichweite,
Gespräch und automatische Rückkehr zu Idle, Esc, F5, wiederholte Eingaben,
alle acht Abschiedsframes, das Erlöschen des Lichts und die Zustände bei
Raumwechseln sowie einem neuen Laborbesuch.

Der Umbau verändert nur den Entwicklungsbereich. Übernahmen von Spielwerten
folgen weiterhin dem Verfahren des
[visuellen Testlabors](visuelles-testlabor.md). Die
[Asset-Freigabe](../architecture/asset-ablage-und-freigabe.md) gilt unverändert.
Umsetzung und tatsächlich ausgeführte Abschlussprüfungen stehen im
[Arbeitsplan](../plans/portal-testlabor.md).
Die spätere gemeinsame Grafikumschaltung ist im
[F5-Erweiterungsplan](../plans/portal-labor-grafikvarianten.md) dokumentiert.
Die Seelenprobe steht im [Seelen-Arbeitsplan](../plans/seele-im-portalturm.md).
