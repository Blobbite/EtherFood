<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Funktion: Portal-Testlabor

## Zugang und Bedienung

Stand: 27. September 2026.

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
| Sprite-Testraum | Fünf statische Vergleichsfiguren für die Comic- und Pixel-Art-Stufen. Die bewegliche Figur verwendet die Auswahl unter `F5 → Darstellung`. |
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

Die drei gelieferten Raster unter `game/test_assets/characters/npc/sools/`
enthalten jeweils acht Frames in vier Spalten und zwei Zeilen. Die Szene
`game/test_scenes/environment/portal_lab/soul.tscn` und `soul_frames.tres` referenzieren
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

Der Turm verwendet einen kreisförmigen Boden aus den neuen Blueprint-Tempeltexturen,
Rasterlinien, Markierungen und statischen Türgrafiken. Wandblöcke und
Dachschindeln bilden zwei je 32 Weltpixel breite Streifen außerhalb der
Bodenfläche. In den Fachräumen verläuft dieser Rand rechteckig. Das Dach
verdeckt den Innenraum nicht. Der bestehende Kollisionsring begrenzt weiterhin
die begehbare Fläche des Turms.
Die Boden-Rastergröße folgt `F5 → Maßstab → Tilegröße` mit 32, 48 oder 64 Pixeln,
ohne Objekte oder Türen zu skalieren. Die Fußbodenkomponente bietet im
Godot-Inspector zusätzlich Größe und Radius der Fläche an.

Die gezeichneten Bodenmarkierungen und die weiterhin verwendeten
SVG-Testobjekte verwenden acht Blau-Grau-Grundfarben. Die gelieferten
Tempel-PNGs behalten ihre eigenen Farben:

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
`game/test_assets/environment/locations/portal_lab/test/`. Tür, Lampe, Objekt,
Monster und Partikel besitzen mindestens 1024 Pixel auf der längeren Seite.
Feine Konturen und Vektorformen ersetzen grobe Pixelstufen. Godot importiert
die Texturen verlustfrei in nativer HD-Größe; die sichtbare Größe im Raum
wird davon getrennt skaliert. Die acht Grundfarben gelten für die Vorlagen;
Kantenglättung und der optionale Filtervergleich können Zwischenwerte erzeugen.
Es sind noch keine freigegebenen Spielassets.

## F5-Grafikvarianten für Figur und Portal-Labor

Unter `F5 → Darstellung → Grafik: Figur und Portal-Labor` schalten fünf
Schaltflächen die Figur sowie Boden, Wand und Dach des Blueprint-Tempels um.
Jede Stufe lädt einen eigenen Tempelbildsatz. Die Wahl gilt sofort im
geöffneten Raum und bleibt bei Raumwechseln sowie nach einem Neustart erhalten.

| Auswahl | Tempelordner unter `<Fläche>/blueprint/` | Native PNG-Größe |
|---|---|---|
| Comic High | `comic_high` | 1254 × 1254 |
| Comic Mittel | `comic_mid` | 627 × 627 |
| Comic Low | `comic_low` | 314 × 314 |
| Pixel Art High | `pixel_high` | 128 × 128 |
| Pixel Art Low | `pixel_low` | 115 × 115 |

Die 55 PNGs liegen unter `game/test_assets/environment/tilesets/temple/`.
`<Fläche>` steht für `floors`, `walls` oder `roofs`. Sie werden verlustfrei
in nativer Auflösung importiert. Eine vollständige Textur wiederholt sich
über vier eingestellte Tiles; die Weltgröße hängt somit nicht von der
PNG-Auflösung ab.

Direkt darunter wählt **Tempelboden** eines von neun Motiven: Ornamente,
Schlicht, Cyan-Ornamente, Cyan-Platten, Gerahmter Stein, Achteckiger Stein,
Genietetes Metall, Versetzter Stein und Steinraster. Ausgangswert ist
Ornamente. Das Motiv gilt für alle Portalräume und bleibt bei einem Wechsel
der Grafikstufe erhalten. Gespeichert wird die stabile Motiv-ID unter
`temple_floor`; fehlende oder ungültige Werte verwenden Ornamente. Diese
Auswahl ist ein lokaler Testwert und kein übernehmbarer Spielstandard.

Hin- und Rückportale, Lampen, Objekt- und Shaderproben, Monsterplatzhalter und
Partikel verwenden weiterhin `environment/locations/portal_lab/`: Comicstufen
nutzen `test`, Pixelstufen `pixelart`. Das Tempelpaket enthält für diese
Objekte keine neuen Sprites. F5 und F11 nennen deshalb Tempelstufe und
Objektbildsatz getrennt. Die fünf Vergleichsfiguren bleiben gleichzeitig
sichtbar. Die alten `floor_tile`-Dateien sind nicht mehr als Laborboden eingebunden.

`portal_graphics.gd` bündelt die Tempelzuordnung und die bisherigen Objektbilder.
Bei Objekten haben gleichnamige PNGs Vorrang vor SVGs; fehlende Einzeldateien
verwenden die SVG-Testvorlage. Die schwarzen Hintergründe der bisherigen
Pixel-Art-Objektbilder bleiben eine Eigenschaft dieser PNGs. Neue oder ersetzte
Dateien müssen zunächst von Godot importiert werden.

Alle Objektgrößen und Bodenanker sind unabhängig von der nativen Auflösung.
Der Wechsel baut den Raum nicht neu auf und erhält Portalpositionen,
Kollisionen, Kamera, Bewegung und Raumzustände. Rastergröße, Texturfilter und
Pixel-Snap bleiben unabhängige Testwerte. Die gezeichneten Ringmarkierungen
verwenden bei Pixel Art harte Kanten und bei den Testvorlagen Kantenglättung.

## Einen Raum ergänzen

Die Erweiterungsstelle ist `game/test_scenes/environment/portal_lab/rooms.tres`. Ihre
Reihenfolge bestimmt die Nummerierung der Türen im Turm. Jede Definition
enthält eine eindeutige `room_id`, `title`, `description` und die `scene`.
Der Name `hub` ist für den Turm reserviert.

1. Unter `game/test_scenes/environment/portal_lab/rooms/` eine Szene von `test_room.tscn`
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

`game/test_scenes/helpers/runtime/portal_lab_test.gd` prüft tatsächliche Hin- und Rückwege
durch alle neun Türen, sichere Ankunft, gehaltene Bewegung, fremde Körper,
Raumzustände, gemeinsame Testwerte, getrennte Effekte und einen auf 33 Räume
erweiterten Katalog. `portal_lab_graphics_test.gd` prüft die echten
F5-Menüschalter, alle fünf Grafikstufen und neun Bodenmotive, Wand und Dach,
gespeicherte und ungültige Auswahlwerte, Raumwechsel, Weltgrößen, Anker,
unabhängige Filter und unveränderte Raumeigenschaften.
`tools/tests/test_portal_lab_assets.py` prüft die Vollständigkeit der 55
Tempel-PNGs samt nativer Importe sowie die bisherigen Objektbildsätze,
SVG-Palette und Vektorgeometrie.
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
Die neuen Texturen stehen im
[Tempel-Arbeitsplan](../plans/blueprint-tempel-texturen.md).
