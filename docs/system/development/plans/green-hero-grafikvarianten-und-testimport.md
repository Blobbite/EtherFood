<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: Green-Hero-Grafikvarianten und Testimport

## Zweck und Ausgangslage

Das Testlabor soll unter Darstellung → Hero-Grafik die Varianten HD,
Pixel Art, Ultra und Testversion anbieten. Die teilweise angelegten Ordner
unter `game/tests/assets/characters/heroes/green_hero/` werden entsprechend
vervollständigt. Der Arbeitsbaum enthält bereits die Verlagerung sämtlicher
vorläufiger Assets aus `game/assets/` und weitere Benutzeränderungen.

Die acht neuen `ultra/sources/*_solo_4x4_o.png` sind bytegleich zu den derzeit
eingebundenen Stand- und Walk-Sheets. Ihre Einzelbildquellen liegen unter
`ultra/sources/stand/`. Ein eigener HD-Bildsatz fehlt im Arbeitsbaum; die
frühere animierte 640-Pixel-Fassung ist in Git vorhanden.

## Umfang und Schritte

1. Bestand, Richtungen, Generator, Menü und bestehende Prüfungen untersuchen.
2. Eigenständige Grafikpakete mit Quellen, Stand, Walk und Ressourcen anlegen.
3. Ein SH-Skript im Testordner zum Zuordnen und Einbinden neuer Test-Sheets
   ergänzen; Eingaben prüfen und Quelldateien erhalten.
4. Vier Auswahlknöpfe mit Speicherung, korrektem Maßstab und Fußpunkt
   integrieren; die aktuelle Dokumentation nachführen.
5. Gezielte Python- und Godot-Prüfungen, Standardlauf und Abschlusskontrolle
   ausführen.

Kanon, Spielregeln, Bewegung und finale Asset-Freigaben sind nicht Gegenstand
dieser Änderung. Bestehende Benutzeränderungen werden erhalten.

## Fortschritt

- [x] Bestand und bestehende Einbindung untersucht.
- [x] Grafikpakete und Quellen eingeordnet.
- [x] Testimport und Umbenennung umgesetzt.
- [x] Darstellungsauswahl und Dokumentation aktualisiert.
- [x] Prüfungen ausgewertet und Abschlusskontrolle erledigt.

## Erkenntnisse und Entscheidungen

Die neuen PNGs werden bytegleich übernommen. Die Testversion beginnt mit
der bisherigen Stand-/Walk-Fassung und den zugehörigen Einzelbildern.
Richtungsnamen bleiben eindeutig: deutsches `W` bedeutet Westen, das
Dateikürzel `greenhero_w_` bezeichnet dagegen die W-Taste und damit Norden.

Für HD wurde zunächst die frühere animierte 640-Pixel-Fassung aus Git gewählt.
Der Benutzer hat diese Zuordnung anschließend bestätigt. Die neuen
Quell-Sheets liegen unter `ultra/sources/stand/` und `ultra/sources/walk/`;
die bisherigen Einzelbilder wurden nach `test/sources/stand/` verschoben.
Das Testskript benötigt keine GitHub-Anmeldung und keine zusätzlichen
Python-Abhängigkeiten. Neue Test-Sheets werden bytegleich kopiert; geänderte
Zellmaße erhalten einen mittigen Fußpunkt an der Unterkante. Die vier Knöpfe
stehen in zwei Spalten, damit sie in das vorhandene Menü passen.

## Prüfungen

- Ausgangsprüfung: neun Python-Tests für Animationsgenerator und Pixelart
  bestanden. Der Standardlauf vor der Umstellung meldet bestehende Fehler;
  seine Ergebnisse dienen dem anschließenden Vergleich.
- 19 gezielte Python-Tests bestanden, einschließlich Umbenennung, anderer
  Zellmaße, getrennter Aktionen, Wiederholung und unverändertem Bestand bei
  ungültigen Eingaben oder `--dry-run`.
- SH-Syntaxprüfung und Skriptaufruf mit `--dry-run` aus einem anderen
  Arbeitsverzeichnis bestanden. Ein zusätzlicher Test führt den SH-Einstieg
  in einer temporären Repositorystruktur mit Leerzeichen im Pfad aus.
- Stilprüfung für 86 Python-/GDScript-Dateien und Godot-Ressourcenimport
  bestanden. Die Generatorprüfung bestätigt für HD, Ultra und Test jeweils
  16 Animationen und 256 Frames.
- Drei gezielte Godot-Suiten für Green-Hero-Animation, Grafikvergleich und
  Gameplay bestanden. Geprüft sind alle Paketressourcen, acht Richtungen für
  Stand und Walk, Maßstab und Fußpunkt, gespeicherte HD-/Test-Auswahl und das
  erneute Laden der Testressource per Knopfdruck.
- 112 PNG-Importverweise ohne fehlende Dateien oder doppelte UIDs geprüft.
  Alle eingegangenen Ultra-PNGs sind an ihrem Ziel bytegleich erhalten;
  44 relative Dokumentationslinks sind gültig.
- Vollständiger Standardlauf mit Godot im Suchpfad ausgeführt: Doctor 12/12,
  Stil und Ressourcenimport bestanden; 207 Python-Tests bestanden. Derselbe
  bestehende Dokumentationsstrukturtest scheitert weiterhin am lokalen
  `docs/concept/.obsidian/`. Die 75 Godot-Fehlermeldungen stimmen in Inhalt
  und Anzahl exakt mit dem Ausgangslauf überein. Keine neuen Standardfehler.
- `git diff --check` bestanden. Vorhandene Benutzeränderungen und die
  unveränderte englische Forge2D-Referenz bleiben erhalten.

## Wiederholbarkeit und Wiederherstellung

Manifeste, PNGs und Godot-Ressourcen bleiben im Testbestand versioniert.
Importcaches und temporäre Sicherungen werden nicht versioniert. Das Skript
behält Eingangsdateien und meldet unvollständige oder mehrdeutige Bildsätze,
bevor es Laufzeitdaten ersetzt. Git wird nicht zurückgesetzt.

## Ergebnis und Rückblick

Abgeschlossen: Vier getrennte Grafikvarianten sind im Labor auswählbar und
werden lokal gespeichert. Die neuen Quellen sind für Ultra-Stand und -Walk
eingeordnet; die bisherige Fassung samt Einzelbildern liegt unter Test. Das
SH-Skript übernimmt vollständige Bildsätze und aktualisiert die Godot-Daten.
HD verwendet die bestätigte frühere animierte Fassung. Die gezielten Prüfungen
bestehen; die bestätigten, bereits vorhandenen Standardfehler bleiben ein
separates Arbeitspaket.

## Nachtrag: Vollständige PNG-Raster für die Testversion

Der Benutzer hat acht `N/NO/O/SO/S/SW/W/NW_solo_4x4.png` direkt im Testordner
und bytegleiche Kopien unter `sources/` bereitgestellt. Die Raster messen
5744 × 5016 Pixel; jedes der 16 Felder misst 1436 × 1254 Pixel. Das bisherige
Skript erkennt nur Dateinamen mit `_o` und lehnt diese Quellen deshalb ab.

- [x] Alle acht Raster, ihre Zellmaße und transparenten Ränder untersucht.
- [x] Namensformate und den direkten Eingang im Testordner unterstützen.
- [x] Neue PNGs für Stand und Walk übernehmen und die Darstellung kalibrieren.
- [x] Gezielte Prüfungen, Standardlauf und Dokumentation abschließen.

Die PNGs bleiben unverändert. Alle Felder einer Richtung sind identisch; die
Testversion zeigt weiterhin ruhende Posen beim Stehen und Bewegen. Die
sichtbare Höhe beträgt 1205 Pixel, der untere Rand der Figur liegt bei
`y = 1224`. Die vollständigen Zellen einschließlich ihrer transparenten
Ränder werden eingebunden. Der Fußanker liegt mittig bei `x = 718`.

Lose PNGs direkt unter `test/` haben Vorrang vor `sources/`. Bei diesem Eingang
dürfen die bereits erzeugten `stand/`- und `walk/`-Dateien nicht erneut als
Quellen verwendet werden. Unvollständige Eingaben müssen weiterhin abbrechen.
HD, Pixel Art und Ultra behalten ihre bisherigen Daten. Die ursprünglichen
PNG-Eingänge bleiben für erneute Importe erhalten.

Prüfungen bisher:

- Acht bestehende Importtests bestanden; die Ablehnung des neuen Namensformats
  wurde vor der Korrektur nachvollzogen.
- 23 gezielte Python-Tests, Stilprüfung und SH-Syntaxprüfung bestanden. Die
  neuen Tests decken vollständige Raster im Testordner und unter `sources/`,
  unvollständige Eingänge und doppelte Richtungen ab.
- Alle 16 Laufzeitdateien und ihre Importquellen sind bytegleich zu den acht
  neuen Original-PNGs. Ein erneuter SH-Import erhält das kalibrierte Manifest
  und die Godot-Ressource bytegleich.
- Der erste parallele Godot-Import überschritt die 4-GB-Grenze der Sitzung.
  Der erfolgreiche Wiederholungslauf verwendete vorübergehend
  `editor/import/use_multiple_threads=false`; die ursprüngliche
  Projektkonfiguration wurde anschließend bytegleich wiederhergestellt.
- Drei gezielte Godot-Suiten für Animation, Grafikvergleich und Gameplay
  bestanden. Die zusätzliche Bildprüfung bestätigt die tatsächlichen
  Alpha-Grenzen, 80 Weltpixel sichtbare Referenzhöhe und den Bodenanker.
- Generatorprüfung für 16 Animationen und 256 Frames, 56 Test-PNG-Importe
  und 17 relative Dokumentationslinks bestanden. HD, Pixel Art und Ultra
  sind gegenüber dem Beginn dieses Nachtrags unverändert.

Der abschließende Standardlauf wurde ausgeführt: Doctor 12/12, Stil und
Ressourcenimport bestanden; 211 Python-Tests bestanden. Der bekannte lokale
Dokumentationsstrukturfehler und dieselben 75 Godot-Fehlermeldungen bestehen
unverändert. Der Vergleich mit dem vorherigen Standardlauf zeigt keine neuen
Fehler. `git diff --check` ist ebenfalls bestanden.

Ergebnis des Nachtrags: abgeschlossen. Die acht neuen Raster sind für Stand
und Walk unter Testversion eingebunden. Das SH-Skript verarbeitet jetzt beide
Namensformate und den direkten Eingang im Testordner; die Quellen und die
anderen Grafikvarianten bleiben erhalten.
