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
| Animationsstandard | 7 Animationstypen mit je 8 Richtungen |
| Aktuell dokumentiert | Stand, Slow Walk, Walk, Sneak, Run, Sprint und Jump vollständig |
| Belegte Richtungsplätze | 56 von 56 im Testmodell |
| Dokumentierte GIFs | 51 |
| Frames je GIF | 6 bis 16 |
| Dokumentationsformat | GIF |
| Doku-Assets | `docs/game/reference/animations/heroes/green-hero/previews/` |
| Im Spiel eingebunden | Keine der fünf Testvarianten ist final freigegeben; alle sieben Animationstypen laufen im visuellen Testlabor |

## Kurzbeschreibung

Das Testmodell verwendet fünf bereitgestellte Bildvarianten: Comic High,
Comic Mittel, Comic Low, Pixel Art High und Pixel Art Low. Für Stand, Slow Walk,
Walk, Sneak und Run stehen 8, 10, 12, 14 und 16 Frames mit jeweils gleicher
FPS-Zahl als passende
Spritesheet-Raster zur Verfügung. Sprint liest das Run-Raster mit 12 FPS;
Jump verwendet pro Richtung genau ein Standbild. Alle Testgrafiken bleiben bis
zur finalen Freigabe unter `game/test_assets/`.

Der Green Hero ist eine spielbare Heldenfigur von EtherFood. Diese Seite
dokumentiert die vorhandenen visuellen Vorschauen und trennt sie vom noch
nicht freigegebenen Testbestand. Die neuen Testanimationen werden in fünf
Varianten und fünf Frames-/FPS-Stufen im Godot-Testlabor aufgebaut. Ein Gedankenstrich
(`—`) bedeutet bei den historischen GIF-Tabellen, dass für diesen
Richtungsplatz keine Vorschau vorliegt.

## Herkunft und Verwendung

| Merkmal | Angabe |
|---|---|
| Zweck | Öffentliche, releasegeeignete Vorschau und visuelle Referenz der vorhandenen Animationen |
| Herkunft | Fertige GIF-Exporte aus der lokal bereitgestellten Green-Hero-Arbeitsstruktur |
| Dokumentationsstand | 8. September 2026 |
| Grafikbestand | Stehen, langes Warten, Gehen, Laufen, Rennen und Sprinten vollständig; genervtes Warten nur nach Süden |
| Laufzeitstand | Testlabor: fünf Grafikvarianten, fünf Frames-/FPS-Stufen und sieben Animationstypen je acht Richtungen |
| Technische Merkmale | Stand, Slow Walk, Walk, Sneak und Run verwenden 8/10/12/14/16 Frames; Sprint nutzt Run bei 12 Frames und 12 FPS; Jump ist ein Einzelbild |
| Quellzuordnung | Sprint: `run` bei 12 FPS; Jump: `jump`-Einzelbilder |
| Urheberschaft und Lizenzstatus | Ausgangsmotiv vom Benutzer bereitgestellt; die Übernahme der Vorschauen verändert dessen Nutzungsrechte nicht |

Die Test-Spritesheets liegen unter
`game/test_assets/characters/heroes/greenhero/spritesheets/`. Die historischen
GIFs unter `previews/` bleiben reine Dokumentationsvorschauen und bestimmen
nicht den Godot-Testablauf.

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
Großschreibung, etwa `greenhero_hd_walk_spritesheet_NO_4x4_o.png` und
`walk_NO`.
Die historischen GIF-Vorschauen behalten ihre vorhandenen Dateipfade.

## Laufzeit-Einbindung

Im Spieltest baut `green_hero_animation_library.gd` die `SpriteFrames` aus den
Spritesheets unter `game/test_assets/characters/heroes/greenhero/spritesheets/`
auf. Die Auswahl von Grafikvariante sowie Frames und FPS wird im flüchtigen
`user://visual_lab_settings.cfg` gespeichert. Das automatische Godot-Testmodell
prüft die vollständige Matrix aus fünf Varianten, fünf Frames-/FPS-Stufen, sieben
Animationstypen und acht Richtungen sowie die Bewegungssteuerung.

Diese Testbilder sind weder GIF-Vorschauen noch angenommene neue Spielgrafik.
Eine finale Variante wird erst nach der dokumentierten Asset-Freigabe in
`game/assets/` übernommen.

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
