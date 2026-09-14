---
title: Green Hero – Animationen
type: reference
entity_id: green-hero
entity_type: hero
updated: 2026-09-10
---

<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](../index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Green Hero – Animationen

## Übersicht

| Eigenschaft | Wert |
|---|---|
| Typ | Held |
| ID | `green-hero` |
| Name | Green Hero |
| Kurzbeschreibung | Spielbarer grüner Held |
| Animationsstandard | 25 Animationstypen mit je 8 Richtungen |
| Aktuell dokumentiert | 7 Animationstypen; 6 davon vollständig in 8 Richtungen |
| Belegte Richtungsplätze | 49 von 200 |
| Dokumentierte GIFs | 51 |
| Frames je GIF | 6 bis 16 |
| Dokumentationsformat | GIF |
| Doku-Assets | `docs/game/reference/animations/heroes/green-hero/previews/` |
| Im Spiel eingebunden | Ultra: Stehen und Gehen, je 8 Richtungen × 16 Frames; Testversion: 48 Einzelposen; HD und Pixel Art zusätzlich im Testlabor |

## Kurzbeschreibung

Die Ultra-Standgrafik im Prototyp wurde am 10. September 2026 durch neue PNGs
ersetzt. Für den Bewegungstest werden dieselben neuen Posen auch beim Gehen
angezeigt. Die Stand- und Geh-GIFs dieser Seite zeigen weiterhin die frühere
Fassung; für die neue Version wurden keine GIF-Vorschauen geliefert. Aktuelle
Bilddaten und Richtungszuordnung stehen unter
[Green Hero – Stehen und Gehen](../../../../../system/development/features/green-hero-stand-und-gehen.md).
Alle Laufzeitgrafiken bleiben bis zur finalen Freigabe unter `game/tests/assets/`.

Der Green Hero ist eine spielbare Heldenfigur von EtherFood. Diese Seite
dokumentiert die tatsächlich vorhandenen visuellen GIF-Vorschauen und weist
davon getrennt aus, welche Folgen bereits als Laufzeitgrafik eingebunden sind.
Stehen, langes Warten, Gehen, Laufen, Rennen und Sprinten liegen in allen acht
Richtungen vor. Genervtes Warten ist als dreiteilige Folge nach Süden
dokumentiert. Rennen verwendet die GIFs aus dem Arbeitsordner `sprint`,
Sprinten die GIFs aus `race`. Ihre Bildfolgen sind je Richtung pixelgleich;
die hinterlegten Wiedergabegeschwindigkeiten werden unverändert übernommen.

Der vollständige Heldenstandard bleibt mit 25 Animationstypen sichtbar. Ein
Gedankenstrich (`—`) bedeutet, dass für diesen Richtungsplatz aktuell kein GIF in
der Dokumentation verfügbar ist. Er ist weder ein kaputter Bildlink noch eine
Aussage darüber, ob außerhalb dieses Dokumentationsbestands bereits weitere
Arbeiten existieren.

## Herkunft und Verwendung

| Merkmal | Angabe |
|---|---|
| Zweck | Öffentliche, releasegeeignete Vorschau und visuelle Referenz der vorhandenen Animationen |
| Herkunft | Fertige GIF-Exporte aus der lokal bereitgestellten Green-Hero-Arbeitsstruktur |
| Dokumentationsstand | 8. September 2026 |
| Grafikbestand | Stehen, langes Warten, Gehen, Laufen, Rennen und Sprinten vollständig; genervtes Warten nur nach Süden |
| Laufzeitstand | Stehen und Gehen als Ultra-Sheets; Testversion mit sechs Einzelposen je Richtung; HD und Pixel Art zusätzlich für den Laborvergleich |
| Technische Merkmale | Alle GIFs mit 640 × 640 Pixeln; 35 GIFs mit 16 Frames; Gehen und Laufen mit je 16 Frames; Rennen und Sprinten mit je 6 Frames pro Richtung |
| Quellzuordnung | Gehen: `walk`; Laufen: `run`; Rennen: `sprint`; Sprinten: `race` |
| Renn-Wiedergabe | `sprint`: sieben Richtungen mit 12 Hundertstelsekunden je Frame (etwa 8,3 FPS), Südosten mit 6 (etwa 16,7 FPS) |
| Sprint-Wiedergabe | `race`: 6 Hundertstelsekunden je Frame, etwa 16,7 FPS |
| Urheberschaft und Lizenzstatus | Ausgangsmotiv vom Benutzer bereitgestellt; die Übernahme der Vorschauen verändert dessen Nutzungsrechte nicht |

Die Arbeitsstruktur und ihre PNG-, Spritesheet- und Quelldateien bleiben lokal
und sind nicht Bestandteil dieser Referenz. Für diese Dokumentation wurden die
GIFs ausschließlich kopiert. Quelldateien und Quellordner wurden weder
verändert noch verschoben oder umbenannt.

Die Zielordner der Dokumentation folgen den deutschen Animationsbezeichnungen:
Unter `race/` liegen die für Rennen bestimmten Kopien aus der Quelle `sprint`,
unter `sprint/` die für Sprinten bestimmten Kopien aus der Quelle `race`.

## Richtungen

Für richtungsabhängige Animationen gilt diese einheitliche Reihenfolge:

| Kürzel | Richtung |
|---|---|
| N | Norden |
| NO | Nordosten |
| O | Osten |
| SO | Südosten |
| S | Süden |
| SW | Südwesten |
| W | Westen |
| NW | Nordwesten |

Die Laufzeitdateien und Godot-Animationen verwenden diese Kürzel in
Großschreibung, etwa `greenhero_NO_walk_spritesheet_4x4_o.png` und `walk_NO`.
Die historischen GIF-Vorschauen behalten ihre vorhandenen Dateipfade.

## Laufzeit-Einbindung

Im Spiel verwendet der `HeroCharacter` derzeit genau 16 optimierte
Spritesheets: acht für Stehen und acht für Gehen. Jedes Sheet besitzt ein
4×4-Raster und 16 Frames; die gemeinsame `SpriteFrames`-Ressource umfasst
damit 256 Frames. Alle Folgen laufen in Endlosschleife mit 120 Millisekunden je
Frame. In dieser Testfassung sind die Frames je Richtung identisch und die
Stand- und Walk-Sheets bytegleich. Beim Start blickt der Held nach Süden;
beim Anhalten behält er die letzte der acht Richtungen.

Die Laufzeitassets liegen unter
`game/tests/assets/characters/heroes/green_hero/ultra/`. Manifest,
Ausschnittkoordinaten, Fußanker, Referenzmaß und Wiederherstellung des
1254 × 1254-px-Bezugsfelds sind in der
[Entwicklungsdokumentation zur Einbindung](../../../../../system/development/features/green-hero-stand-und-gehen.md)
festgehalten.

Ultra besitzt noch keine eigenen Laufzeitfolgen für Laufen, Rennen,
Sprinten, Schleichen, Sprünge und Wartevarianten. Seine Bodenbewegungen
verwenden die passende Gehfolge; der bestehende Sprung friert das erste
Standbild der Richtung ein. Die Testversion ergänzt eigene feste Posen
für die Bewegungszustände.

Das visuelle Testlabor besitzt daneben eine eigenständige Pixelart-Ressource
unter `game/tests/assets/characters/heroes/green_hero/pixel_art/`. Sie ordnet je ein
transparentes `265 × 265`-PNG denselben acht Stand- und acht Gehnamen zu. Die
Figurenhöhe und der Fußpunkt sind für einen deckungsgleichen Vergleich mit
Ultra normalisiert. HD verwendet die bestätigte frühere animierte Fassung mit
640-Pixel-Bezugsfeld. Die unabhängige Testversion enthält 48 nicht animierte
Einzelposen mit 1436 × 1254 Pixeln: `stand`, `walk`, `run`, `sneak`, `sprint`
und `jump` in jeweils acht Richtungen. Laufen und Rennen verwenden `run`.
Ihre ursprünglichen Einzelbilder und Raster bleiben als Quellen erhalten.
Ihr SH-Skript ermöglicht den schnellen Austausch neuer Testposen. Alle vier
Varianten werden im Testlabor unter Darstellung → Hero-Grafik gewählt.

Diese Standbilder sind weder GIF-Vorschauen noch eine
angenommene neue Spielgrafik; außerhalb des Labors bleibt Ultra aktiv.

## Animationsübersicht

### Idle

| Animation | N | NO | O | SO | S | SW | W | NW |
|---|---|---|---|---|---|---|---|---|
| Stehen | <img src="previews/stand/n.gif" alt="Green Hero steht mit Blick nach Norden" width="96"> | <img src="previews/stand/ne.gif" alt="Green Hero steht mit Blick nach Nordosten" width="96"> | <img src="previews/stand/e.gif" alt="Green Hero steht mit Blick nach Osten" width="96"> | <img src="previews/stand/se.gif" alt="Green Hero steht mit Blick nach Südosten" width="96"> | <img src="previews/stand/s.gif" alt="Green Hero steht mit Blick nach Süden" width="96"> | <img src="previews/stand/sw.gif" alt="Green Hero steht mit Blick nach Südwesten" width="96"> | <img src="previews/stand/w.gif" alt="Green Hero steht mit Blick nach Westen" width="96"> | <img src="previews/stand/nw.gif" alt="Green Hero steht mit Blick nach Nordwesten" width="96"> |
| Lange warten | <img src="previews/stand-long/n.gif" alt="Green Hero wartet lange mit Blick nach Norden" width="96"> | <img src="previews/stand-long/ne.gif" alt="Green Hero wartet lange mit Blick nach Nordosten" width="96"> | <img src="previews/stand-long/e.gif" alt="Green Hero wartet lange mit Blick nach Osten" width="96"> | <img src="previews/stand-long/se.gif" alt="Green Hero wartet lange mit Blick nach Südosten" width="96"> | <img src="previews/stand-long/s.gif" alt="Green Hero wartet lange mit Blick nach Süden" width="96"> | <img src="previews/stand-long/sw.gif" alt="Green Hero wartet lange mit Blick nach Südwesten" width="96"> | <img src="previews/stand-long/w.gif" alt="Green Hero wartet lange mit Blick nach Westen" width="96"> | <img src="previews/stand-long/nw.gif" alt="Green Hero wartet lange mit Blick nach Nordwesten" width="96"> |
| Genervtes Warten | — | — | — | — | <img src="previews/stand-very-long-1/s.gif" alt="Green Hero wartet genervt mit Blick nach Süden, Teil 1" width="96"><br><img src="previews/stand-very-long-2/s.gif" alt="Green Hero wartet genervt mit Blick nach Süden, Teil 2" width="96"><br><img src="previews/stand-very-long-3/s.gif" alt="Green Hero wartet genervt mit Blick nach Süden, Teil 3" width="96"> | — | — | — |

Die drei Teile des genervten Wartens bilden gemeinsam einen Animationstyp und
belegen gemeinsam den Richtungsplatz Süden. Jeder Teil besitzt 16 Frames; die
gesamte Folge umfasst damit 48 Frames und 5,76 Sekunden.

### Bewegung

| Animation | N | NO | O | SO | S | SW | W | NW |
|---|---|---|---|---|---|---|---|---|
| Gehen | <img src="previews/walk/n.gif" alt="Green Hero geht nach Norden" width="96"> | <img src="previews/walk/ne.gif" alt="Green Hero geht nach Nordosten" width="96"> | <img src="previews/walk/e.gif" alt="Green Hero geht nach Osten" width="96"> | <img src="previews/walk/se.gif" alt="Green Hero geht nach Südosten" width="96"> | <img src="previews/walk/s.gif" alt="Green Hero geht nach Süden" width="96"> | <img src="previews/walk/sw.gif" alt="Green Hero geht nach Südwesten" width="96"> | <img src="previews/walk/w.gif" alt="Green Hero geht nach Westen" width="96"> | <img src="previews/walk/nw.gif" alt="Green Hero geht nach Nordwesten" width="96"> |
| Laufen | <img src="previews/run/n.gif" alt="Green Hero läuft nach Norden" width="96"> | <img src="previews/run/ne.gif" alt="Green Hero läuft nach Nordosten" width="96"> | <img src="previews/run/e.gif" alt="Green Hero läuft nach Osten" width="96"> | <img src="previews/run/se.gif" alt="Green Hero läuft nach Südosten" width="96"> | <img src="previews/run/s.gif" alt="Green Hero läuft nach Süden" width="96"> | <img src="previews/run/sw.gif" alt="Green Hero läuft nach Südwesten" width="96"> | <img src="previews/run/w.gif" alt="Green Hero läuft nach Westen" width="96"> | <img src="previews/run/nw.gif" alt="Green Hero läuft nach Nordwesten" width="96"> |
| Rennen | <img src="previews/race/n.gif" alt="Green Hero rennt nach Norden" width="96"> | <img src="previews/race/ne.gif" alt="Green Hero rennt nach Nordosten" width="96"> | <img src="previews/race/e.gif" alt="Green Hero rennt nach Osten" width="96"> | <img src="previews/race/se.gif" alt="Green Hero rennt nach Südosten" width="96"> | <img src="previews/race/s.gif" alt="Green Hero rennt nach Süden" width="96"> | <img src="previews/race/sw.gif" alt="Green Hero rennt nach Südwesten" width="96"> | <img src="previews/race/w.gif" alt="Green Hero rennt nach Westen" width="96"> | <img src="previews/race/nw.gif" alt="Green Hero rennt nach Nordwesten" width="96"> |
| Sprinten | <img src="previews/sprint/n.gif" alt="Green Hero sprintet nach Norden" width="96"> | <img src="previews/sprint/ne.gif" alt="Green Hero sprintet nach Nordosten" width="96"> | <img src="previews/sprint/e.gif" alt="Green Hero sprintet nach Osten" width="96"> | <img src="previews/sprint/se.gif" alt="Green Hero sprintet nach Südosten" width="96"> | <img src="previews/sprint/s.gif" alt="Green Hero sprintet nach Süden" width="96"> | <img src="previews/sprint/sw.gif" alt="Green Hero sprintet nach Südwesten" width="96"> | <img src="previews/sprint/w.gif" alt="Green Hero sprintet nach Westen" width="96"> | <img src="previews/sprint/nw.gif" alt="Green Hero sprintet nach Nordwesten" width="96"> |

Rennen und Sprinten besitzen in allen acht Richtungen je 6 Frames. Beim Rennen
laufen sieben Richtungen jeweils 0,72 Sekunden; die Südost-Animation läuft mit
0,36 Sekunden bereits so schnell wie beim Sprinten. Alle Sprint-Animationen
laufen jeweils 0,36 Sekunden. Die Bildfolgen beider Reihen sind richtungsweise
pixelgleich.

### Bewegungssprünge

| Animation | N | NO | O | SO | S | SW | W | NW |
|---|---|---|---|---|---|---|---|---|
| Gehsprung | — | — | — | — | — | — | — | — |
| Laufsprung | — | — | — | — | — | — | — | — |
| Rennsprung | — | — | — | — | — | — | — | — |
| Sprintsprung | — | — | — | — | — | — | — | — |

### Schleichen

| Animation | N | NO | O | SO | S | SW | W | NW |
|---|---|---|---|---|---|---|---|---|
| Schleichen | — | — | — | — | — | — | — | — |

### Angriffe

| Animation | N | NO | O | SO | S | SW | W | NW |
|---|---|---|---|---|---|---|---|---|
| Stehangriff | — | — | — | — | — | — | — | — |
| Schleichangriff | — | — | — | — | — | — | — | — |
| Gehangriff | — | — | — | — | — | — | — | — |
| Laufangriff | — | — | — | — | — | — | — | — |
| Rennangriff | — | — | — | — | — | — | — | — |
| Sprintangriff | — | — | — | — | — | — | — | — |

### Sprungangriffe

| Animation | N | NO | O | SO | S | SW | W | NW |
|---|---|---|---|---|---|---|---|---|
| Stehsprungangriff | — | — | — | — | — | — | — | — |
| Gehsprungangriff | — | — | — | — | — | — | — | — |
| Laufsprungangriff | — | — | — | — | — | — | — | — |
| Rennsprungangriff | — | — | — | — | — | — | — | — |
| Sprintsprungangriff | — | — | — | — | — | — | — | — |

### Ausweichen

| Animation | N | NO | O | SO | S | SW | W | NW |
|---|---|---|---|---|---|---|---|---|
| Schleichrolle | — | — | — | — | — | — | — | — |
| Ausweich-Backflip | — | — | — | — | — | — | — | — |

## Animationsdaten

| Kennzahl | Umfang |
|---|---:|
| Animationstypen im vollständigen Heldenstandard | 25 |
| Richtungen je Animationstyp | 8 |
| Richtungsplätze im vollständigen Standard | 200 |
| Frames je GIF | 6 bis 16 |
| Theoretischer Gesamtumfang des Standards | 3.200 Frames |
| Aktuell durch GIFs belegte Animationstypen | 7 |
| Davon vollständig in acht Richtungen | 6 |
| Aktuell belegte Richtungsplätze | 49 |
| Aktuell vorhandene GIF-Dateien | 51 |
| Aktuell in GIFs dokumentierter Umfang | 656 Frames |
| Derzeit ohne GIF-Vorschau | 151 Richtungsplätze |

Der theoretische Gesamtumfang beschreibt das einheitliche Raster eines
vollständigen Heldenanimationssatzes. Als tatsächlich vorhanden gelten auf
dieser Seite nur die 51 eingebetteten GIF-Dateien. Die drei Teile des genervten
Wartens zählen als ein Animationstyp und ein belegter Richtungsplatz, aber als
drei einzelne GIF-Dateien mit insgesamt 48 Frames. Rennen und Sprinten steuern
jeweils 48 Frames bei; deshalb weicht der tatsächliche Umfang vom theoretischen
16-Frame-Raster ab.

## Dateisystem

Die Dokumentations-GIFs liegen unter:

`docs/game/reference/animations/heroes/green-hero/previews/`

Das Schema lautet:

`<animation>/<direction>.gif`

Die vollständigen Richtungssätze liegen unter `stand/`, `stand-long/`, `walk/`,
`run/`, `race/` und `sprint/`. Die dreiteilige Vorschau des genervten Wartens
verwendet die Pfade `stand-very-long-1/`, `stand-very-long-2/` und
`stand-very-long-3/`. In jedem dieser Pfade liegt die vorhandene Richtung als
`s.gif`.

## Abgrenzung

Die Tabellen dieser Seite dokumentieren nur die sichtbaren GIF-Vorschauen der
fertigen Animationen. Die Laufzeit-Einbindung wird lediglich als getrennter
Status beschrieben. Nicht als öffentliche Vorschau eingebettet sind:

- weitere PNG-Einzelframes außerhalb der versionierten Laborvariante,
- Arbeitsdateien,
- KI-Ausgangsbilder,
- Upscale-Dateien,
- Zwischenversionen,
- die versionierten Ultra-Spritesheets für Godot,
- Godot-Importdateien und
- lokale `.workspace`-Inhalte.

Spritesheets und Runtime-Animationen werden getrennt von diesen GIFs in der
Godot-Struktur verwaltet. Wird eine dokumentierte Animation verbessert oder
ersetzt, wird ihr bestehendes GIF am gleichen Pfad aktualisiert; die
Referenzstruktur bleibt unverändert und der Laufzeitstatus wird ausdrücklich
nachgeführt.
