<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: Vollständige Green-Hero-Testposen

## Zweck und Ausgangslage

Unter `green_hero/test/sources/` liegen 48 neue Einzelbilder sowie passende
4×4-Raster: `stand`, `walk`, `run`, `sneak`, `sprint`, `jump` in acht deutschen
Himmelsrichtungen. Der Benutzer möchte alle Posen im Bereich Test verwenden.
Die bisherige Testressource enthält nur Stehen und Gehen mit wiederholten
Rasterzellen. Die anderen drei Grafikvarianten bleiben erhalten.

## Umfang und Schritte

1. Quellen, Bildmaße, Fußanker und Bewegungszustände prüfen.
2. Manifest und Generator um vollständige optionale Testaktionen und echte
   Einzelbilder erweitern.
3. Testimport für die vorbereiteten Namen erweitern und 48 Laufzeitposen
   samt Quellenbezug erstellen.
4. Godot-Steuerung den passenden Posen zuordnen; Varianten ohne Zusatzposen
   behalten die bisherige Darstellung.
5. Gezielte Import-/Ressourcen-/Laufzeittests und Dokumentation aktualisieren.
6. Godot-Import, Standardprüfung und Abschlusskontrolle durchführen.

Keine neuen Bewegungsregeln, Geschwindigkeiten, Animationen zwischen den
Einzelposen oder Änderungen an HD, Pixel Art und Ultra.

## Fortschritt

- [x] 96 Quellen erfasst; Einzelbilder und Bewegungszustände geprüft.
- [x] Generator um deklarierte Testaktionen und Einzelbilder erweitert.
- [x] Testimport und 48 Laufzeitassets erstellt; 16 alte Raster als Quellen archiviert.
- [x] Godot-Zuordnung integriert und in allen Richtungen geprüft.
- [x] Gezielte Prüfungen und Dokumentation abgeschlossen.
- [x] Gesamtprüfung und Abschluss abgeschlossen; keine neuen Bestandsfehler.

## Erkenntnisse und Entscheidungen

- Die 48 Einzelbilder messen jeweils 1436 × 1254 Pixel. Die 48 Raster
  messen 5744 × 5016 Pixel und bleiben als Quellen erhalten. Die Laufzeit
  nutzt je Pose ein Einzelbild ohne künstliche Animationsfolge.
- `stand`, `walk`, `sneak`, `sprint` und `jump` entsprechen ihren Zuständen.
  Laufen (`JOG`) und Rennen (`RUN`) teilen die vorhandene `run`-Pose.
- Alle Posen verwenden das gemeinsame Bezugsfeld und die Standkalibrierung.
  Eine gebeugte oder springende Figur wird nicht auf Standhöhe gestreckt.
- Neue benannte Posensätze unter `sources/` haben beim automatischen Import
  Vorrang vor den alten losen Standrastern im Testordner. Einzelbilder haben
  Vorrang vor ihrem zusätzlich gelieferten Raster. Unvollständige Richtungen
  brechen vor dem Ersetzen ab.
- Vorhandene alte Quellenunterordner waren durch die neu gelieferten Dateien
  bereits ersetzt. Die alten Stand-/Walk-Laufzeitraster wurden deshalb vor dem
  Formatwechsel verlustfrei unter `sources/previous/` gesichert.
- Die bestehenden Ressourcenpfade der Testversion bleiben als Einstieg
  erhalten, damit lokale Auswahl und Szenen weiter funktionieren.

## Prüfungen

36 gezielte Python-Tests für Import, Generator und Pixel Art bestanden.
Probelauf und Import aller 48 Posen bestanden. Alle 96 Originalquellen haben
unveränderte SHA-256-Prüfsummen; je Aktion liegen acht Laufzeit-PNGs vor.

Godot-Bildimport erfolgreich, ohne weitere Speicherabbrüche. Die temporäre
Editoroption ist entfernt. Vier gezielte Godot-Testreihen bestanden:
Ressourcen, Testposen mit echten Eingabewechseln, Grafikauswahl und Labor-Gameplay.
Stilprüfung für 89 Dateien, Shell-Syntaxprüfung und `git diff --check`
bestanden. Generator-Prüfmodus bestätigt 48 Aktionen/Richtungen mit 48 Frames.
Alle Laufzeit-PNGs besitzen Godot-Importmetadaten.

Standardprüfung mit `python tools/control.py check` durchgeführt:

- Doctor: 12 bestanden, keine Warnungen oder Fehler.
- Python: 224 bestanden; unverändert ein Dokumentationsstrukturfehler wegen
  des lokalen Verzeichnisses `docs/concept/.obsidian/`.
- Godot: Bildimport erfolgreich; weiterhin genau die 75 vorher bekannten
  Erwartungsfehler zu bestehenden Spiel-/Laborstandards. Der Vergleich aller
  Fehlermeldungen einschließlich ihrer Häufigkeit ergibt keine neue Meldung.
- Keine GDScript-Parser- oder Laufzeitfehler im abschließenden Lauf.

Die Gesamtprüfung ist wegen dieser bestehenden Fehler weiterhin nicht grün.
Die aktuellen Posen-, Import- und Variantenprüfungen bestehen vollständig.

## Wiederholbarkeit und Wiederherstellung

`test/rename_test_assets.sh` erzeugt den Testbestand aus den Quellen und
validiert vor dem Schreiben. Die ursprünglichen Quellen bleiben erhalten.
Godot importiert große Raster seriell, um die Container-Speichergrenze
einzuhalten; eine dafür temporär gesetzte Editoroption wird wieder entfernt.
Vorhandene Arbeitsbaumänderungen und Spielstandards werden nicht zurückgesetzt.

## Ergebnis und Rückblick

Alle 48 gelieferten Einzelposen sind unter Test eingebunden. Die sechs
Laufzeitordner enthalten jeweils acht korrekt benannte PNGs; der Controller
zeigt je Bewegung und Richtung die passende feste Pose. Die 96 Originalquellen
bleiben unverändert. Die 16 bisherigen Laufzeitraster sind als Quellen archiviert.
Das SH-Skript kann vollständige oder einzelne Posengruppen erneut übernehmen.
HD, Pixel Art und Ultra behalten ihren bisherigen Bildbestand und Rückfall.
Eine neue Grafikfreigabe oder Änderung von Bewegungsregeln erfolgt dadurch nicht.
