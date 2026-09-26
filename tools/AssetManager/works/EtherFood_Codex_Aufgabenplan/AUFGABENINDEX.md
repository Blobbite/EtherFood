# Codex-Aufgabenindex

**48 Aufgaben, 6 Phasen.** Empfohlen ist die numerische Reihenfolge. Abhängigkeiten sind zusätzlich explizit angegeben; die Implementierung eines Vorgängers muss tatsächlich vorliegen. Ein neuer Codex-Auftrag erhält jeweils genau eine `p.md`.

Alle Aufgaben stehen in diesem ausgelieferten Plan auf `not_started`. Die Prüfungen dieses ZIP-Pakets betreffen die Planung, nciht eine schon entwickelte Anwendung.

## Phase A: Grundlagen und Verwaltungskern — T001 bis T008

Pfadkarte, Modelle, Schutzregeln, Dokumente und Schrittketten

| Aufgabe | Arbeitsauftrag | Abhängigkeiten |
| --- | --- | --- |
| T001 | [Bestand aufnehmen und Schreibgrenzen festlegen](aufgaben/001-bestand-und-schreibgrenzen/p.md) | — |
| T002 | [Architektur und gemeinsame Datenverträge festschreiben](aufgaben/002-architektur-und-vertraege/p.md) | T001 |
| T003 | [Python-Paket, CLI und Testgerüst anlegen](aufgaben/003-python-grundgeruest/p.md) | T002 |
| T004 | [Projektkatalog und Datenmigrationen implementieren](aufgaben/004-katalog-und-migrationen/p.md) | T003 |
| T005 | [Sichere Pfade, Dateiablage und Importjournal bauen](aufgaben/005-pfade-und-objektspeicher/p.md) | T004 |
| T006 | [Akte, Kapitel und globale Inhalte als Dienste umsetzen](aufgaben/006-akte-kapitel-und-globale-inhalte/p.md) | T004, T005 |
| T007 | [Dokumentation, Anhänge und Fehlerkarten verwalten](aufgaben/007-dokumente-notizen-und-aufgaben/p.md) | T006 |
| T008 | [Typabhängige Schrittketten und Freigabestatus modellieren](aufgaben/008-workflow-und-statusmodell/p.md) | T002, T006, T007 |
## Phase B: Dashboard und Asset-Anlage — T009 bis T016

Canvas, Akte/Kapitel, Editor, Bestandsimport und NPC-Anlage

| Aufgabe | Arbeitsauftrag | Abhängigkeiten |
| --- | --- | --- |
| T009 | [Desktop-GUI und Projektstart implementieren](aufgaben/009-gui-und-projektstart/p.md) | T003, T004, T006, T008 |
| T010 | [Karten-Canvas für globale Inhalte, Akte und Kapitel bauen](aufgaben/010-canvas-hierarchie/p.md) | T006, T009 |
| T011 | [Verbindungen, Nebenpfade und Undo/Redo ergänzen](aufgaben/011-canvas-verbindungen-und-undo/p.md) | T008, T010 |
| T012 | [Dokumentationseditor und Aufgabenansicht integrieren](aufgaben/012-dokumentations-und-aufgaben-gui/p.md) | T007, T009, T010 |
| T013 | [Asset-Typen, Posen und variable Richtungen modellieren](aufgaben/013-assettypen-posen-und-richtungen/p.md) | T004, T006, T008 |
| T014 | [Vorhandenen Asset-Bestand lesend erfassen und zuordnen](aufgaben/014-bestandsimport-lesend/p.md) | T005, T009, T013 |
| T015 | [Quellbilder und externe Animationslieferungen importieren](aufgaben/015-quellen-und-spritesheet-import/p.md) | T005, T013, T014 |
| T016 | [NPC-Anlage, Vorlagen und Held-Menü implementieren](aufgaben/016-asset-anlage-und-held-menue/p.md) | T008, T009, T013, T015 |
## Phase C: Aufträge, Farben und Frame-Verarbeitung — T017 bis T024

Arbeitsprozesse, Cache, Masterreferenzen, Masken und Farbpipeline

| Aufgabe | Arbeitsauftrag | Abhängigkeiten |
| --- | --- | --- |
| T017 | [Arbeitsprozesse und gemeinsame Pipeline-Adapter bauen](aufgaben/017-worker-und-pipeline-adapter/p.md) | T003, T005, T008, T015 |
| T018 | [Build-Abhängigkeiten, Cache und Änderungsfolgen umsetzen](aufgaben/018-buildplan-cache-und-invalidation/p.md) | T008, T013, T015, T017 |
| T019 | [Freie Masterreferenzen und variable Richtungssets unterstützen](aufgaben/019-masterreferenzen-und-profilversionen/p.md) | T013, T015, T018 |
| T020 | [Materialdefinitionen, Maskenrevisionen und Validierung bauen](aufgaben/020-materialmasken-und-quellbindung/p.md) | T005, T013, T015, T019 |
| T021 | [Maskeneditor mit Materialauswahl und Sichtabnahme integrieren](aufgaben/021-maskeneditor-und-materialauswahl/p.md) | T016, T020 |
| T022 | [Automatische Maskenvorschläge mit Unsicherheitsanzeige entwickeln](aufgaben/022-automatische-maskenvorschlaege/p.md) | T017, T018, T020, T021 |
| T023 | [SourceColor und SpritesheetColor in die Build-Pipeline einbinden](aufgaben/023-farbkorrektur-pipeline/p.md) | T017, T018, T019, T020, T022 |
| T024 | [Frame-Abstufungen, Raster und Anker sicher ableiten](aufgaben/024-frameableitung-und-geometrie/p.md) | T017, T018, T023 |
## Phase D: Varianten, Texturen und Sichtprüfung — T025 bis T032

Timing, Grafikstufen, Texturpakete, Vorschauen und Befunde

| Aufgabe | Arbeitsauftrag | Abhängigkeiten |
| --- | --- | --- |
| T025 | [Timing-Profile und gemeinsame Animationszeit ergänzen](aufgaben/025-timing-und-animationsevents/p.md) | T013, T018, T024 |
| T026 | [Grafikstufen für Spritesheets integrieren](aufgaben/026-grafikstufen-spritesheets/p.md) | T018, T023, T024, T025 |
| T027 | [Exakte Farbprüfung und optionale Material-Nachzuordnung implementieren](aufgaben/027-materialfarben-nach-skalierung/p.md) | T019, T020, T023, T024, T026 |
| T028 | [Statische Grafik- und Texturverarbeitung implementieren](aufgaben/028-statische-texturpipeline/p.md) | T013, T017, T018, T026 |
| T029 | [Asset-Pakete und Tempel-Arbeitsbereich umsetzen](aufgaben/029-assetpakete-und-tempel/p.md) | T006, T013, T016, T028 |
| T030 | [Automatische Schrittketten und Auftragsbedienung integrieren](aufgaben/030-pipeline-bedienung-im-dashboard/p.md) | T016, T017, T018, T023, T024, T025, T026, T027, T028, T029 |
| T031 | [HTML-Vergleiche im Asset-Menü sicher wiederverwenden](aufgaben/031-integrierte-vorschauen/p.md) | T009, T016, T026, T027, T028, T030 |
| T032 | [Variantenmatrix, Prüfcheckliste und Sichtbefunde implementieren](aufgaben/032-variantenpruefung-und-fehlerkarten/p.md) | T007, T008, T013, T025, T027, T029, T031 |
## Phase E: Versionen und Godot-Freigabe — T033 bis T040

Kandidaten, Git, Export, Godot-Test, Promotion und Cleanup

| Aufgabe | Arbeitsauftrag | Abhängigkeiten |
| --- | --- | --- |
| T033 | [Unveränderliche Kandidaten und Versionsarchiv implementieren](aufgaben/033-kandidaten-und-versionsarchiv/p.md) | T005, T018, T029, T032 |
| T034 | [Git-Anbindung und Quellenrevisionen ergänzen](aufgaben/034-git-und-quellenrevisionen/p.md) | T001, T004, T015, T033 |
| T035 | [Godot-Export und portable Runtime-Ressourcen implementieren](aufgaben/035-godot-exportvertrag/p.md) | T001, T013, T025, T026, T028, T029, T033 |
| T036 | [Kandidaten im Godot-Testbereich bereitstellen und importieren](aufgaben/036-godot-testbereitstellung/p.md) | T005, T017, T033, T035 |
| T037 | [Godot-Testszene, technische Prüfungen und manuelle Abnahme bauen](aufgaben/037-godot-tests-und-abnahmeszene/p.md) | T025, T029, T035, T036 |
| T038 | [Freigaben mit exakten Build- und Testbindungen implementieren](aufgaben/038-freigabe-und-pruefbindungen/p.md) | T008, T032, T033, T036, T037 |
| T039 | [Freigegebene Versionen sicher ins Spiel übernehmen](aufgaben/039-runtime-promotion-und-rollback/p.md) | T005, T033, T035, T036, T037, T038 |
| T040 | [Testbereitstellungen nach erfolgreicher Übernahme gezielt aufräumen](aufgaben/040-testbereich-sicher-aufraeumen/p.md) | T005, T036, T038, T039 |
## Phase F: Betrieb und Gesamtprüfung — T041 bis T048

Historie, Dokumentation, Vorlagen, Backup, E2E und Pilotmigration

| Aufgabe | Arbeitsauftrag | Abhängigkeiten |
| --- | --- | --- |
| T041 | [Versionsverlauf, Vergleich und Dashboard-Fortschritt vervollständigen](aufgaben/041-versionsvergleich-und-projektfortschritt/p.md) | T006, T007, T008, T032, T033, T034, T038, T039, T040 |
| T042 | [Projekt- und Asset-Dokumentation automatisch erzeugen](aufgaben/042-automatische-dokumentation-und-export/p.md) | T007, T012, T029, T033, T037, T038, T041 |
| T043 | [Erweiterbare Kartentypen und Pipeline-Vorlagen bereitstellen](aufgaben/043-erweiterbare-vorlagen-und-typen/p.md) | T008, T013, T018, T029, T030, T041 |
| T044 | [Sicherung, Wiederherstellung und Speicherpflege absichern](aufgaben/044-backup-recovery-und-speicherpflege/p.md) | T004, T005, T017, T018, T033, T034, T039, T040, T041 |
| T045 | [Gesamtablauf für Held und NPCs mit weniger Richtungen testen](aufgaben/045-e2e-held-und-npc/p.md) | T016, T022, T023, T024, T025, T026, T027, T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040, T041, T044 |
| T046 | [Tempelpaket, globale Effekte und gemeinsame Verwendung testen](aufgaben/046-e2e-tempel-und-globale-verwendung/p.md) | T028, T029, T033, T035, T036, T037, T038, T039, T040, T041, T042, T043, T044 |
| T047 | [Installation, automatisierte Prüfungen und Betrieb dokumentieren](aufgaben/047-paketierung-ci-und-betrieb/p.md) | T003, T009, T031, T042, T043, T044, T045, T046 |
| T048 | [Pilotmigration und abschließende Projektabnahme vorbereiten](aufgaben/048-pilotmigration-und-abschluss/p.md) | T001, T014, T034, T039, T040, T041, T042, T044, T045, T046, T047 |

## Wie groß ist eine Aufgabe?

Jede Datei enthält Ziel, Kontext, konkrete Schritte, Ergebnisse, Negativ-/Wiederholungstests, Abnahmekriterien, Grenzen, Quellen und Übergabe. Muss eine Aufgabe im realen Checkout weiter geteilt werden, bleibt ihre ID als übergeordnete Anforderung erhalten; zusätzliche Teilaufgaben dürfen keine Pflichtkriterien verschwinden lassen.

Keine Kalendertermine oder Zeitversprechen sind enthalten. Der Plan priorisiert einen benutzbaren schrittweisen Ausbau und sichtbare Prüfschranken.
