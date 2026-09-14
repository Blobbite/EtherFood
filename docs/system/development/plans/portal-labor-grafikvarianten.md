<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: F5-Grafikvarianten für das Portal-Labor

## Zweck und Ausgangslage

Stand: 12. September 2026.

Die F5-Grafikauswahl soll außer der Figur auch den Blueprint-Boden, die
Portaltüren und die Testobjekte des Portal-Labors umschalten. Der Benutzer
hat die sechs bisherigen SVG-Testvorlagen nach `portal_lab/test/` verschoben
und sechs PNGs unter `portal_lab/pixelart/` ergänzt. Die Godot-Verweise zeigen
noch auf die bisherigen Wurzelpfade. Die neuen PNGs haben andere native
Abmessungen; ihre Weltgröße muss unabhängig davon erhalten bleiben.

## Umfang und Entscheidungen

- Die vorhandene F5-Auswahl wird gemeinsam für Figur und Portal-Labor genutzt.
  Die gespeicherte Einstellungs-ID bleibt kompatibel.
- `Pixel Art` verwendet `pixelart`, `Testversion` verwendet `test`.
  Für `HD` und `Ultra` gibt es keinen eigenen Portal-Bildsatz; sie verwenden
  die vorhandenen HD-Testvorlagen. Das Menü zeigt diese Zuordnung an.
- Eine zentrale Texturzuordnung versorgt Boden, Türen, Lampen, Objekte,
  Monster und Partikel. PNGs und SVGs werden unterstützt; fehlende einzelne
  Varianten dürfen auf die mitgelieferte Testvorlage zurückfallen.
- Texturwechsel erhält Anker, Objektgrößen, Kollisionen, Raumzustände,
  Bewegung, Rastergröße und die unabhängigen Filter-/Pixel-Snap-Testwerte.
- Vorhandene Bilder werden unverändert eingebunden. Kanon, Spielstandards
  und die vier Vergleichsfiguren im Sprite-Raum werden nicht neu definiert.

## Schritte und Fortschritt

1. [x] Vorhandene Ordner, Bildgrößen und F5-Verknüpfung untersuchen.
2. [x] Zentrale Texturzuordnung und auflösungsunabhängige Anker einbauen.
3. [x] F5, Raumwechsel, Neustart und Menüanzeigen verbinden.
4. [x] Laufzeit- und Assettests für beide Bildsätze aktualisieren.
5. [x] Ordnerverwendung und F5-Zuordnung dokumentieren.
6. [x] Gezielte Prüfungen, Sichtkontrolle und Standardlauf durchführen.

## Erkenntnisse und Prüfungen

Die Ordner waren bereits vorbereitet. Zu Beginn fehlten die Laufzeitverknüpfung
und die Anpassung bisheriger Tests an die neue Ablage. Die SVGs behalten die
definierte Palette; die neuen Benutzer-PNGs sind eigene Vergleichsdateien.

Beide gezielten Godot-Suiten für Grafikumschaltung und Portalnavigation
bestehen ohne Fehler. Alle sechs Python-Assettests, die Stilprüfung für
100 Dateien und die Prüfung der Dokumentationslinks bestehen ebenfalls.
Zwölf Renderaufnahmen in 1920 × 1080 zeigen beide Varianten im F5-Menü,
Turm sowie Lampen-, Monster-, Objekt- und Partikelraum. Die PNGs sind
RGB-Bilder ohne Alphakanal; ihre schwarzen Hintergründe sind sichtbar.
Die Zuordnung ist für spätere freigestellte Ersatzdateien vorbereitet.
Alle sechs Benutzer-PNGs und die Darstellungsgrundlage sind bytegleich
zum Stand vor dieser Aufgabe.

Der vorherige Laborlauf hatte 75 Godot-Erwartungsfehler und einen lokalen
Dokumentationsstrukturfehler. Inzwischen ist auch die Darstellungsgrundlage
im Arbeitsbaum verändert; sie wird bei dieser Aufgabe nicht angepasst.
Die abschließenden Ergebnisse werden daher erneut konkret erfasst.

Der vollständige Lauf `python tools/control.py check` am 12. September 2026
ergab: Doctor 12/12, Stilprüfung 100 Dateien bestanden, Python 230 bestanden
und ein Fehler wegen der zusätzlichen lokalen Dokumentationsebene
`docs/concept/.obsidian/`. Godot meldet 427 Erwartungsfehler, jedoch keine
Script-, Parse- oder sonstigen Laufzeitfehler. Beide Portal-Suiten bestehen
auch innerhalb dieses vollständigen Laufs.

Die 75 Meldungen des vorherigen Laborlaufs sind weiterhin enthalten. Die
352 zusätzlichen Meldungen beziehen sich sämtlich auf Texturfilter: Die
vorhandenen Tests erwarten `Nearest`, die schon vor dieser Aufgabe
vorliegende Darstellungsgrundlage verwendet `soft`. Davon entfallen 341
Meldungen auf die bisherige Filter-Suite. Die neue gemeinsame Umschaltung
prüft ausdrücklich, dass eine unabhängige weiche Filterauswahl erhalten
bleibt. Die Standardprüfung ist wegen dieser Erwartungen und des
Dokumentationsfehlers insgesamt nicht grün.

## Wiederholbarkeit und Wiederherstellung

Keine Git-Rücksetzungen, keine neuen Projektabhängigkeiten und keine
Änderungen an Zugangsdaten. Die bisherigen Dateien sind für einen gezielten
Vergleich flüchtig gesichert. Alle Testbilder bleiben unter `game/tests/assets/`.

## Ergebnis

Die F5-Auswahl schaltet Figur und Portal-Labor gemeinsam. Beide vorhandenen
Bildsätze sind vollständig eingebunden; Raumwechsel und Neustarts behalten
die Auswahl. Weltgrößen und Bodenanker bleiben trotz verschiedener
Bildauflösungen gleich. Die zentrale Zuordnung und Ordnerdokumentation
bereiten weitere Testbilder mit denselben Namen vor. HD und Ultra verwenden
vorläufig die Testvorlagen; der F5-Status macht diese Zuordnung sichtbar.
Die schwarzen Hintergründe der derzeitigen Benutzer-PNGs sind als Eigenschaft
des Bildsatzes dokumentiert.
