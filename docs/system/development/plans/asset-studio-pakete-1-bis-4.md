# Arbeitsplan: Asset Studio, Pakete 1 bis 4

## Ziel und Auftrag

Freigegeben sind T001–T012 (#8–#19), verteilt auf vier Pakete. Nach jedem
Paket erfolgen gezielte Prüfungen, ein englischer Commit mit Emoji und Push.
Danach folgt die erste menschliche Sichtprüfung. Keine Umsetzung ab T013,
keine Bildverarbeitung echter Assets und keine Godot-Promotion.

## Ausgangslage

Start: `main`, `59ae32d`. Der Benutzer hat PyGameTools und den Aufgabenplan
nach `tools/AssetManager/` verschoben. Die Inhalte werden vor dem gezielten
Übernehmen der Umzüge byteweise gegen HEAD verglichen. Generierte Grafiken
werden nicht aufgenommen. GitHub-Zugang bleibt ausschließlich im flüchtigen
Sitzungsspeicher.

## Fortschritt

- [x] Paket 1: T001/T002 – Bestand, Schreibgrenzen, Architektur und Verträge.
- [x] Paket 2: T003–T005 – Paket/CLI, Katalog, sichere Dateiablage.
- [ ] Paket 3: T006–T008 – Struktur, Dokumente/Aufgaben, Statusregeln.
- [ ] Paket 4: T009–T012 – Desktop, Canvas, Undo/Redo, Dokumenteditor.
- [ ] Abschluss: vier Pushes, Testnachweise und Anleitung zur Sichtprüfung.

## Entscheidungen

- Eigenständiges Paket unter `tools/AssetManager/`, kein Qt-Zwang für den Kern.
- SQLite ist maßgeblich; JSON ist ein ausdrücklich importierter Snapshot.
- Programmstatus, Build, Sichtprüfung und Bereitstellung bleiben getrennt.
- Technische Dokumentation liegt unter `docs/system/development/asset-studio/`.
- Vorhandene Stil-/Dokumentationsfehler werden nicht durch fremde Änderungen
  verdeckt. Neue Dateien werden separat geprüft.

## Befunde und Prüfstrategie

Paket 1 wurde als `779e60a` gepusht. Paket 2: 26 Studio-Tests, 170
Bestandstests und nach Ergänzung 9 Installer-Tests bestanden. Der nummerierte
Pipelinebestand erforderte korrigierte Installer-/Testverweise; bestehende
Wrapper-Ziele bleiben über Weiterleitungen benutzbar. Keine Bildalgorithmen
geändert. Qt-Systembibliotheken fehlen im Container und wurden isoliert
temporär aus Debian-Paketen bereitgestellt; Qt-Offscreen-Start erfolgreich.

Baseline `python tools/control.py check` über die vorhandene `.venv`:
201 bestanden, 37 übersprungen, 2 fehlgeschlagen (fehlende Spielentscheidungs-
Dokumente). Godot fehlt. 1.985 bestehende Stilbefunde in 167 Quelldateien.
Zuerst kleine Vertrags-/Core-Tests, dann GUI-Tests mit synthetischen Daten
und `QT_QPA_PLATFORM=offscreen`; zum Abschluss erneut der Gesamtcheck.
Offscreen-Tests ersetzen keine manuelle Sichtprüfung auf dem Zielrechner.

## Wiederaufnahme und Rückbau

Pro Paket eigener Commit; keine destruktiven Git-Befehle. Importjournale
und Datenbanksicherungen ermöglichen die Diagnose abgebrochener Operationen.
Alle Testdaten liegen in temporären Verzeichnissen. Hashvergleich schützt
die vorhandenen PNG/GIF/Godot-Dateien. Keine automatische Bereinigung.

## Ergebnis

In Arbeit. Konkrete Ergebnisse stehen zusätzlich in den einzelnen
T001–T012-Berichten; fehlende Prüfungen bleiben ausdrücklich offen.
