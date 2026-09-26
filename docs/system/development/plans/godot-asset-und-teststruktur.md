<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: Godot-Asset- und Teststruktur

## Zweck und Gesamtbild

Die bereits angelegte Godot-Struktur wird verbindlich: `game/assets/` enthält
freigegebene Assets, `game/test_assets/` enthält den Testbestand,
`game/scenes/` enthält die Anwendung und `game/test_scenes/` die Prototypen
und Testhilfen. Release-Exporte müssen ohne Testressourcen starten können.

## Ausgangslage

- Die neuen Verzeichnisse sind vorhanden und leer; Git speichert sie nicht.
- Der bisherige Bestand liegt unter `game/tests/assets/`.
- Labor und Heldenraum liegen unter `game/scenes/` und laden Testgrafiken.
- Die Anwendung bindet beide Prototypen bereits beim Laden fest ein.
- Linux, Windows und macOS exportieren alle Ressourcen ohne Ausschlussfilter.
- Eine bestehende Benutzeränderung am Gamedesign bleibt erhalten.

## Umfang und Nicht-Ziele

Dateien ohne Inhaltsverlust verschieben; Ressourcen, Importmetadaten,
Generatoren und Tests mitführen. Die Anwendung lädt Prototypen nur in der
Entwicklungsumgebung. Kanon, Spielregeln und Asset-Freigaben ändern sich nicht.
Der Benutzer hat den USB-Workspace als Quelle bestätigt und das Entfernen
nicht mehr benötigter Quellen beauftragt. Keine neuen Rohdateien oder Archive
im Godot-Projekt anlegen.

## Schritte und Fortschritt

- [x] Struktur, Exportvorlagen und Startabhängigkeiten aufnehmen.
- [x] Testassets, Szenen und Testhilfen verschieben und Referenzen nachführen.
- [x] Release-Filter und unabhängigen Anwendungsstart umsetzen.
- [x] Aktive Dokumentation und persönliche Notiz unter `game/` aktualisieren.
- [x] Passende Prüfungen, Godot-Import, Laufzeittests und Export prüfen.

## Erkenntnisse und Überraschungen

Ein bloßer Exportfilter reicht nicht: `application_root.tscn` lädt derzeit
Labor und Heldenraum als feste Abhängigkeiten. Außerdem ist bislang kein
Asset final freigegeben. Ein Release kann deshalb vorerst Titel und Menü,
aber keinen freigegebenen Spielabschnitt enthalten.

Der erste Godot-Import wurde wegen Überschreitung des Containerlimits von
4 GiB beendet. Mit `editor/import/use_multiple_threads=false` und entferntem
Quellballast gelingt der Import ohne Änderung der Bildqualität.

Die vorhandenen Laufzeittests erwarten teilweise andere Werte als die bereits
versionierten Ressourcen, etwa Joggen 220 statt 210 und Kamerazoom 1,0 statt
0,75. Eine separate Kopie des Git-Ausgangsstands meldet dieselben 427 fehlgeschlagenen
Laufzeitassertionen; die Umstellung fügt keine weitere hinzu. Zudem fehlen
schon im Git-Ausgangsstand referenzierte Spieldesign-Entscheidungen.

## Entscheidungen

- Der aktuelle Benutzerauftrag ersetzt die alte Pfadregel
  `game/tests/assets/` durch `game/test_assets/`.
- Alle benötigten Varianten bleiben erhalten; keine implizite Freigabe.
- 192 entbehrliche Quellbilder samt 192 Importdateien wurden entfernt.
  SHA-256 bestätigt unveränderte Laufzeitbilder; neue Eingaben kommen explizit
  aus einem externen Kandidatenordner.
- Automatisierte Godot-Prüfungen gehören ebenfalls zum ausgeschlossenen
  Testbereich. Gemeinsamer Anwendungscode bleibt außerhalb davon.
- Die persönliche Übergabenotiz wird nicht in die Dokumentationsnavigation
  aufgenommen und bleibt aus Exporten ausgeschlossen.

## Prüfungen

Bisher ausgeführt:

- Quellstil: 103 Dateien bestanden.
- 38 gezielte Python-Prüfungen zu Asset-Struktur, Manifest und Import bestanden.
- Godot 4.7.2: Ressourcenimport bestanden.
- Die vier Laufzeitsuiten für SceneRouter, ApplicationRoot, Heldenanimationen
  und Testposen bestanden, einschließlich Start ohne Entwicklungsszenen.
- Für Linux, Windows und macOS jeweils ein Ressourcen-ZIP mit dem tatsächlichen
  Preset exportiert: je 53 Einträge, keine Testressourcen, Werkzeuge oder
  Markdown-Dateien; Start aller drei Pakete außerhalb des Projektordners
  bestanden. Dies prüft die Datenpakete; native Betriebssystem-Builds wurden
  nicht ausgeführt.
- Alle 129 PNGs, sieben SVGs und 48 verschobenen Script-UIDs sind bytegleich.

- Vollständige Python-Suite: 235 bestanden, zwei bestehende Dokumentationsfehler
  (fehlende Entscheidungen und darauf verweisende Links). Beide Fehler wurden
  auch in der separaten Kopie des Git-Ausgangsstands reproduziert.
- Vollständiger Godot-Laufzeitlauf: 427 fehlgeschlagene Assertionen; dieselben
  427 Meldungen treten im Git-Ausgangsstand auf, keine zusätzliche Assertion.
  Für die Vergleichskopie wurden ausschließlich der speichersparende Import
  gesetzt und nicht verwendete Arbeitsquellen vom Import ausgenommen.
- Die Generatorprüfungen für Ultra, HD und Test sowie Maßstabs- und
  Weltzustandsbilder bestanden.

- `python tools/control.py check` wurde mit der vorhandenen Python-Umgebung
  und dem offiziellen, SHA-512-geprüften Godot 4.7.2 ausgeführt: Doctor,
  Quellstil und Ressourcenimport bestanden. Die 235 erfolgreichen Python-Tests,
  zwei vorbestehenden Dokumentationsfehler und dieselben 427 vorbestehenden
  Godot-Assertionen wurden im Standardlauf bestätigt. Der Gesamtstatus bleibt
  deshalb fehlgeschlagen; es wurde kein vollständig grüner Prüflauf behauptet.
- Die 136 Textur-UIDs und sämtliche Texturimportoptionen stimmen mit `HEAD`
  überein. `git diff --check` bestand.

 Die offizielle
[Exportdokumentation](https://docs.godotengine.org/en/stable/tutorials/export/exporting_projects.html)
bestätigt die Ausschlussfilter. Testordner erhalten keine `.gdignore`, damit
der Editor sie weiterhin importiert.

## Wiederholbarkeit und Wiederherstellung

Vor dem Verschieben werden Zielkollisionen geprüft und die Quelldateien
inventarisiert. Quellbilder bleiben bytegleich. UID-Dateien und Importoptionen
werden mitgeführt; Godots lokaler Cache wird neu importiert und nicht
versioniert. Rücknahme erfolgt anhand der nachvollziehbaren Git-Änderungen,
ohne bestehende Benutzeränderungen zu verwerfen.

## Ergebnis und Rückblick

Die angeforderte Umstellung ist abgeschlossen. Godot verwendet die neuen
Testbereiche; der frühere Ordner `game/tests/` entfällt. Editor-Prototypen,
Animationen und Szenenrouting funktionieren mit den migrierten Ressourcen.
Alle drei geprüften Export-Datenpakete starten ohne Testinhalte. Aktive
Dokumentation und persönliche Übergabenotiz sind aktualisiert.

Die bereits vorhandenen Abweichungen zwischen Testannahmen und gespeicherten
Spielstandards sowie die fehlenden Spieldesign-Entscheidungen bleiben ein
separater Befund. Sie wurden im Ausgangsstand reproduziert und nicht durch
Änderung von Spielwerten oder Abschwächung der Prüfungen verdeckt. Native
Linux-, Windows- und macOS-Programme wurden nicht gebaut; geprüft wurden
Export-Datenpakete und ihr kopfloser Start mit Godot.
