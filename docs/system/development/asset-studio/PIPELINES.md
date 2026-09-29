# Verarbeitung und Ablaufeditor

Der Bereich **Verarbeitung → Ablaufeditor** verbindet kleine Python-Bausteine
zu wiederverwendbaren Abläufen. Die Bibliothek, der Canvas und der Python-Editor
gehören zur echten PySide6-Anwendung unter `tools/AssetManager/`.
Der frühere HTML-Entwurf ist dafür nicht erforderlich.

| Bestandteil | Aufgabe und Bedienung |
| --- | --- |
| Skriptbaustein | Eine Aufgabe mit benannten Ein-/Ausgängen, Parametern und Ausgabeordnern. Doppelklick im Canvas öffnet den Python-Entwurf. |
| Werkzeugpaket | Versionierte Lieferung aus Bausteinen, Hilfsdateien und Teilabläufen. Doppelklick in der Bibliothek öffnet Dateien, Diagnose und Umgebung. |
| Ablauf | Verbindet Bausteine und Teilabläufe. Ein Paketablauf öffnet seinen eigenen Canvas. |
| Python-Umgebung | Projektlokaler Bibliotheksbestand. Gleiche Python-/Paketanforderungen teilen dieselbe Umgebung. |

## Einstieg und Bedienung

1. Im Repository `python tools/control.py asset-manager run` starten und ein
   Projekt öffnen. Oben **Verarbeitung** wählen. Pipeline-Karten im Projekt
   öffnen ebenfalls diesen Editor.
2. **Neuer Ablauf** erstellt einen Ablauf mit Asset-Eingang. Links ein Asset
   einblenden und Skripte per Doppelklick einsetzen. Anschlüsse verbinden;
   bei mehreren passenden Möglichkeiten erscheint eine Auswahl der Portnamen.
3. Rechts Parameter und Ausgabeziele des ausgewählten Bausteins einstellen.
   Jeder Ausgang kann einen eigenen Ordner und Veröffentlichungsschalter haben.
   Der Canvas zeigt die deklarierten Ordner schon vor der Ausführung.
4. **Speichern** übernimmt Rezept, Layout und explizite Asset-Verbindungen.
   **Zuweisungen …** ergänzt Regeln für Asset-Typen/Fähigkeiten oder das ganze
   Projekt. Explizite Zuweisungen haben Vorrang vor Typregeln und Projektstandard.
   Mehrere Abläufe pro Asset sind möglich; ausgeführt wird der gewählte Ablauf.
5. Mit **Werkzeugpakete / Python …** oder über die Bibliothek die verwendeten
   Paketdateien prüfen. **Umgebung einrichten / reparieren** bereitet die
   Bibliotheken vor. Fremde Codeversionen benötigen eine lokale Freigabe.
6. **Dry-run / Ausführen …** zeigt geplante Schritte, Cachetreffer und Blockaden.
   Der Start verarbeitet Arbeitskopien. Fortschritt, Protokolle, Ergebnisprüfung
   und Abbruch verwenden die vorhandene Auftragsverwaltung.
7. Ein Baustein öffnet per Doppelklick seinen Code; ein Teilablauf seinen Canvas.
   **Zurück** führt zum vorherigen Editor, **Bibliothek** zur Übersicht.
   Entwürfe werden beim Wechsel gespeichert. Laufende Testaufträge müssen zuvor
   beendet oder abgebrochen werden.

## Bildbausteine und Beispielketten

**EtherFood · Bildwerkzeuge** wird mitgeliefert und verwendet die vorhandenen
Algorithmen unter `PyGameTools/Pipline/`. Die Starter, die ganze Ordnerketten
abarbeiten, sind durch einzelne Einträge ersetzt; die CLI-Dateien bleiben nutzbar.

| Baustein | Aufgabe |
| --- | --- |
| Comic High, SComicMid, SComicLow | Proportionale Frameauflösung; Vorgaben 1, 0,5 und 0,25 des Eingangs. |
| SPixelHigh | Pixelverfahren, Alphabehandlung und Palette; längste Framekante standardmäßig 128 Pixel. |
| SPixelLow | Nearest-Ableitung des verbundenen Pixel-High-Ausgangs; Vorgabefaktor 0,9. |
| PyImgGrid | Gemeinsamer transparenter Randbeschnitt und frei wählbare Spaltenzahl. |
| Frameauswahl | Vorhandene Frames auswählen, FPS oder Animationsdauer festlegen. |
| PyImgGif | Aus einem Spritesheet ein GIF mit Quell- oder eigenen FPS erzeugen. |
| PyGraphicsCompare | Mehrere Bild-/GIF-Ausgänge als interaktiven HTML-Vergleich sammeln. |
| PyGraphicsPoseCompare | Interaktiver Posen- und Positionsvergleich. |
| Farbverarbeitung | Referenzfarben, feste Palette oder Materialprofil mit gebundener Maske. |

Das Paket enthält den Teilablauf **Spritesheet-Auflösungen**. Seine Comiczweige
beginnen an derselben Quelle; Pixel Low folgt auf Pixel High. Der Vergleich
wartet auf alle verbundenen Zweige. Die Reihenfolge folgt den Pfeilen und
Abhängigkeiten, nicht den Bildschirmpositionen.

Eine mögliche Animationskette ist:

```text
Asset → PyImgGrid → SComicLow → Frameauswahl → PyImgGif
                                              └→ Posenvergleich
```

Unabhängige Comicvarianten werden verzweigt, damit Comic Mid nicht versehentlich
noch einmal auf einem bereits verkleinerten Comic Low skaliert wird.
Ein fertiger Paketablauf kann als ein Knoten in einem größeren Ablauf stehen.
Über **Diesen Teilablauf als Projektablauf verwenden** entsteht eine bearbeitbare
Projektkopie der veröffentlichten Paketversion. Änderungen am Paketentwurf
müssen zuvor als neue Version übernommen werden.

## Ordner, Geometrie und Timing

Ausgabeziele sind relativ zum verarbeiteten Asset, beispielsweise
`Ergebnisse/{pose}/ComicLow`, `GIFs/{pose}` oder `Vergleiche`.
`{pose}` verwendet den Exportnamen der Pose, `{variante}` die Ergebnisvariante.
Absolute Pfade, Elternpfade und geschützte Quell-/Maskenordner sind keine
Ausgabeziele. Dateinamen erhalten einen Buildzusatz; alte Stände bleiben erhalten.
Die deklarierte Zielstruktur wird auch am Asset lesend angezeigt. Ist eine
Variante erst zur Laufzeit bekannt, bleibt ihr Platzhalter in der Vorschau
sichtbar; der konkrete Ordner entsteht erst für das tatsächliche Ergebnis.

PNG-/Spritesheet-Metadaten enthalten Raster, Frameindizes, Quellrevision,
Quellhash, Anker, logische Größe, Zuschnitt und Timing. Mitgelieferte Bildbausteine
aktualisieren die Geometrie passend zu ihren tatsächlichen Ergebnissen.
Skalierung gilt für einzelne Framezellen und erhält das Seitenverhältnis.
Die Größenberechnung rundet deterministisch und vergrößert nicht automatisch.

Frames und FPS bleiben getrennt: 16 Frames bei 8 FPS und 8 Frames bei 4 FPS
haben dieselbe Dauer. Eine Frameauswahl erzeugt keine Zwischenbilder.
GIF-Zeiten werden auf die tatsächlich darstellbaren Zeitintervalle gerundet.
Eine Einzelbildquelle kann daher nicht direkt einen Animationsbaustein bedienen.

Farbprofile, Paletten und Masken werden im Ablauf unter
**Assetreferenzen / Masken …** verwaltet. Ressourcen können ausdrücklich am
Rezept gebunden oder über `@asset`/`@source` aus geprüften Quellbindungen bezogen
werden. Fehlende oder mehrdeutige Bindungen blockieren die Verarbeitung.
Die [Referenz- und Maskenverträge](REFERENZEN_UND_MASKEN.md) bleiben maßgeblich.

## Übernahme bisheriger Einstellungen

Beim ersten Öffnen des Verarbeitungsbereichs oder Asset-Menüs werden bestehende
v1-Rezepte in `studio-pipeline-v2` umgewandelt. Grafikprofile werden zu sichtbaren
Bausteinen samt Werten, Frame- und GIF-Schritte zu den entsprechenden Mikrobausteinen.
Abweichende Asset-Ziele und alte lokale Parameter erhalten eigene Abläufe.
Geerbte Regeln behalten ihre Einstellungen auch für später angelegte Assets.
Historische Rezeptrevisionen und Builds bleiben im Katalog erhalten.

Asset-/Posendefinitionen verwenden danach Schema 2: Quelle, Posen, Richtungen,
Anker, Quell-FPS und Loop bleiben dort. Grafikziele und Zielframezahlen stehen
nur noch im Ablauf. Die alten Grafikprofilfelder, Profilkonfigurationen,
Verarbeitungsaktionen und separaten Startknöpfe im Asset-Menü sind entfernt.
Dort bleiben der Lieferstand, Ergebnisansichten und der Link zum Ablaufeditor.
Fehlende alte Python-Erweiterungen bleiben als reparierbare Blockade sichtbar.

## Ausführung, Cache und Austausch

Pakete sind unveränderliche Versionen mit Inhaltshash. Ein Ablauf bindet eine
bestimmte Version; ein neuer Entwurf ersetzt keine bestehende Verwendung.
Typen, benannte Anschlüsse, Dateilisten, fehlende Eingänge und Zyklen werden geprüft.
`map` arbeitet je Quelle; `collect` sammelt die verbundenen Ergebnisse dieses
Assets. Verschachtelte Abläufe werden für die Planung aufgelöst.

Die vorhandene Kette aus BuildGraph, BuildPlanner, JobService, Supervisor und
BuildCache führt auch eigene Bausteine aus. Geprüfte Dateien eines vollständig
erfolgreichen Laufs werden beim Asset veröffentlicht. Fehler, Abbruch und reine
Entwurfstests ändern dessen aktuellen Ergebnisindex nicht. Cachetreffer werden
anhand von Dateien, Hashes, Parametern und Bibliotheksbestand erneut geprüft.

**Exportieren** liefert ZIP-Dateien einschließlich der benötigten Python-Dateien,
Hilfsmodule, verschachtelten Werkzeugpakete und deklarierter Ressourcen.
**Importieren** zeigt die Prüfung vor der Übernahme. Codefreigaben, installierte
Umgebungen, Zugangsdaten und private Maschinenpfade gehören nicht zum Export.
Details und ein direkt importierbares Beispiel stehen unter
[Skriptpakete, Python-Schnittstelle und Ablage](SKRIPTPAKETE.md).

Die Umsetzung und tatsächlich ausgeführten Prüfungen stehen im
[Arbeitsplan](../plans/asset-studio-ablaufeditor.md).
