# Asset Studio: zwei Editorbereiche und Pipelineautomatik

[Planübersicht](index.md) · [Asset Studio](../asset-studio/index.md)

## Zweck und Gesamtbild

Stand: 29.09.2026. Der neue Umsetzungsauftrag ersetzt die widersprechenden
Bedienkonzepte des bisherigen Ablaufeditors. Projekt und Skripte & Pipelines
erhalten dieselbe Anordnung. Aktuelle Dateien, ausdrückliche Verwendungen,
geprüfte lokale Freigaben und eine serielle Automatik ersetzen Paketversionen
als Arbeitsgrundlage und die bisherige Auftragsverwaltung.

## Ausgangslage

Gelesen: Repository-Regeln, Dokumentationsübersicht, `.agent/PLANS.md`,
Asset-Studio-Übersicht, Architektur, Entwicklung, Pipeline-, Skriptpaket-,
Auftrags- und Buildplan-Dokumentation. Ausgangspunkt ist der aktuelle
Arbeitsbaum, einschließlich der noch nicht eingecheckten Markdown-Erweiterung.
Diese Änderungen bleiben erhalten. Das unversionierte Testprojekt unter
`schemas/` wird weder migriert noch für destruktive Prüfungen verwendet.

| Bestand | Abhängigkeiten und notwendige Ablösung |
| --- | --- |
| `MainWindow`, `Navigation`, `ProcessingWorkspace` | Projekt-Tabs, rechte Eigenschaften, separater Verarbeitungseinstieg; auf zwei gleich angeordnete Haupteditoren umstellen. |
| `PipelineService`, `pipeline_assignment` | Definitionen sind bisher Projektkarten; Asset-/Typ-/Projektregeln besitzen Prioritäten. Definition und konkrete Verwendung trennen, wirksame Altzuordnung erhalten. |
| `ToolPackageService`, `WorkflowMigration` | Unveränderliche Pakete und Entwürfe; implizite Bildbibliothek. Bestehende Versionen samt Hilfsdateien übernehmen, keine automatische Demo. |
| `RecipeBuildService`, `ToolBuildService`, `BuildPlanner` | Alte Planungswege führen über `JobService`; Ergebnisprüfungen und fachliche Herkunft übernehmen, Ausführung ablösen. |
| `JobService`, `JobStore`, Supervisor, `jobs`, `job_events`, `build_cache` | Prozesskontrolle, Abbruch und Ergebnisbelege hängen zusammen. Benötigte Ergebnisse zuerst übernehmen, danach ausschließlich alte Auftragsbestände entfernen. |
| `ProjectFiles`, `FileChanges`, `BlobStore` | Sichere Pfade, unveränderliche Quellen, SQL-/Dateijournal und Veröffentlichungen weiterverwenden. |
| `SourceImportService`, Assetdefinitionen | Aktuelle Quellrevisionen, Raster und Timing bilden generische Eingaben; keine Verzeichnissuche nach beliebigen Bildern. |
| `ProjectTree`, Canvas, `Commands` | Besitz und Verweise vorhanden; getrennte Verwendungszustände, Papierkorb, Fristbereinigung und Wiederherstellung ergänzen. |
| Markdown-, Notiz-, Kanban- und Assetansichten | Bestehende Inhalte, Medien, Revisionen und Bearbeitung erhalten. Automatische Dokumenttextgenerierung nur bei notwendiger Vertragsanpassung ändern. |

## Umfang und Nicht-Ziele

Oberfläche, Anwendungsdienste, versionierte Migration, aktuelle Werkzeugdateien,
Ausführung, Archiv/Papierkorb, Suchen, Demo, Tests und deutsche Bedienung gehören
zum Auftrag. Keine Godot-Bereitstellung, kein Betriebssystemdienst, keine neue
Browseranwendung, keine Spielinhalte und kein Schließen bestehender Issues.
Neue Abhängigkeiten sind zunächst nicht vorgesehen.

## Konkrete Schritte und Fortschritt

- [x] 1. Regeln und Arbeitsbaum prüfen; Bestandsabhängigkeiten und Plan anlegen.
- [x] 2. Definition/Verwendung, aktuelle Dateien, Freigaben, Lebenszyklus und Migration vorbereiten.
- [x] 3. Zwei Editorbereiche, Übersicht/Canvas und Pythoneditor integrieren.
- [x] 4. Eingabebereiche, benannte Ergebnisverbindungen, Phasen und Folder-Ausgaben.
- [x] 5. Prüfung, ausdrückliche Freigabe, inkrementelle Automatik und Abbruch.
- [x] 6. Ablagen, 30-Tage-Bereinigung, Suchen und ausdrückliche Demo.
- [ ] 7. Übernommenen Altbestand und ausschließlich alte Auftragswege entfernen.
- [ ] 8. Backend-, GUI-, Integrations- und Migrationstests sowie Bedienungsdokumentation.

Zwischenstand 29.09.2026: Schema 11 ergänzt aktuelle Dateibesitzlisten,
Pipelinefreigaben, Verwendungsergebnisse, Schrittcache und Lebenszykluszustände.
`WorkspaceFiles` schreibt aktuelle Skripte/Definitionen über das bestehende
Dateijournal. `PipelineWorkspace` trennt Definition und Verwendung.
`PipelineExecution` führt eingefrorene Dateien in kontrollierten Prozessen aus,
unabhängig von `JobService`, mit Phasengrenze zwischen Verwendungen.
Die Übernahme von Altpaketen einschließlich Hilfsdateien und bearbeitbaren
Entwürfen ist mit Sicherung und Unterbrechung geprüft. Ergebnisübernahme und
Rückbau sind inzwischen implementiert; ihre Abnahme wird unten ergänzt.
Die neue Hauptoberfläche integriert Projekt und Skripte & Pipelines. Drei echte
Qt-Tests prüfen Navigation, bewussten Kontextwechsel und Entwurf/Undo beim
Editorwechsel. Das ist noch keine vollständige GUI-Abnahme.

Weiterer Zwischenstand: Schema 12 ergänzt Ergebnisbelege und Dateibesitz für
Laufkopien. Die neue Ergebnisübernahme kopiert prüfbare Altdaten vor dem
transaktionalen Entfernen von `jobs`, `job_events`, `build_cache` und den alten
Veröffentlichungstabellen. Ein unterbrochener Rückbau stellt die alten Dateien
und Tabellen wieder her. Unbekannte Dateien in alten Auftragsordnern bleiben
erhalten. `JobService`, `JobStore`, alte Buildplan-Dienste, Auftragsoberfläche
und alte Verarbeitungseinstiege wurden aus dem Anwendungscode entfernt.
Ausschließlich alte Ausführungstests wurden abgelöst. Die fachlichen Bild-,
Quellen-, Referenz- und Dokumentprüfungen verwenden nun die neue Ausführung.

## Entscheidungen

- Die aktiven Verzeichnisse heißen exakt `.tools/scrips/` und `.tools/piplins/`.
  Historische Katalogdaten dürfen fehlende aktuelle Dateien nicht ersetzen.
- Stabile Identitäten und der bestehende Katalog bleiben erhalten. Die neue
  Ausführung benutzt die neutrale Prozesskontrolle und vorhandene Bildverträge,
  nicht die alte Auftragsverwaltung als versteckten zweiten Laufweg.
- Definitionen werden unabhängig von Assets gespeichert. Verwendungen halten
  Eingabezuordnungen, explizite Ergebnisanschlüsse und fachliche Reihenfolge.
- Diagrammlayout gehört weder zur Ausführungsidentität noch zur Reihenfolge.
- Migration alter Prioritätsregeln übernimmt die tatsächlich wirksame Auswahl;
  nicht eindeutig übertragbare Regeln bleiben sichtbar blockiert.
- Lebenszykluszustände beziehen sich auf Original oder Verwendung getrennt.
  Zeitprüfungen verwenden eine injizierbare UTC-Uhr und exakt 30 × 24 Stunden.

## Migration, Wiederholbarkeit und Wiederherstellung

Vor destruktiver Übernahme wird eine Katalogsicherung mit SQLite-Backup sowie
ein Manifest der ausdrücklich verwalteten Dateien erstellt. Die vorhandene
versionierte Schemaaktualisierung und das Dateiänderungsjournal koordinieren
kurze Transaktionen. Unterschiedlich gebundene Skriptfassungen erhalten zunächst
eigene stabile Identitäten. Fremde Dateien und Konflikte werden nicht
überschrieben. Alte Freigaben werden nicht in den neuen Vertrag übernommen.
Unterbrechung und erneutes Öffnen müssen ohne Duplikate fortsetzen können.

Benötigte alte Ergebnisdateien und Herkunftsbelege werden vor Entfernung alter
Auftragstabellen in die neue Ergebnisverwaltung übernommen. Pauschales Löschen
alter Ordner ist ausgeschlossen. Getrennte Sicherungen sind kein App-Papierkorb.

## Prüfungen und Abnahmezuordnung

Frühere Markdown-Prüfungen sind kein Nachweis der neuen Pipelineanforderungen.

Tatsächlich ausgeführt, jeweils mit `.venv/bin/python -m pytest -xq`:

- `tools/AssetManager/tests/test_pipeline_workspace.py` und
  `tools/AssetManager/tests/test_pipeline_execution.py`: 14 bestanden (7,87 s).
  Einschließlich echter Prozesse, PA/PA/PB/PB für zwei unterschiedliche Assets,
  Cacheprüfung, externer Codeänderung, unveränderter Freigabe und fehlender Datei.
- `tools/AssetManager/tests/test_workspace_migration.py`: 3 bestanden (1,30 s).
  Leere Migration, Sicherung, Dokument-/Identitätserhalt und unterbrochene Übernahme.
- `tools/AssetManager/tests/test_lifecycle_service.py`: 5 bestanden (2,83 s).
  Steuerbare UTC-Frist, Wiederherstellung, unabhängige Verweise, gemeinsamer Blob,
  fremde Dateien, atomare Zieländerung mit Undo und geschützte Systemrahmen.

Weitere tatsächlich ausgeführte Zwischenprüfungen:

- Neue Navigation plus vollständiger Dateitransport/externe Quellenübernahme:
  `test_two_editors.py` und `test_workspace_exchange.py`: 6 bestanden (2,22 s).
- Dateigrundlage, echte Ausführung, Übernahme und Dateitransport nach erweitertem
  Dry-run: 17 bestanden (10,03 s).
- Explizite Demo: 1 bestanden (1,88 s), zwei Assets durch PA und anschließend PB,
  GIF-Dateien mit nachweislich unterschiedlichen Frames, zweiter Lauf ohne Neuberechnung.
- Dateigrundlage, Ausführung, Migration, Austausch und Demo nach Entfernung der
  alten Laufdienste: 21 bestanden (12,15 s).
- Erweiterte Migration mit Ergebnisübernahme und Unterbrechung nach Tabellenabbau:
  4 bestanden (2,25 s); fremde Datei bleibt bestehen.

- Qt-Automatik mit echtem Prozess, Pause, externem Quellenabgleich und Abbruch: 2 bestanden (11,64 s).
- Bereinigung einschließlich zugeordneter Laufkopien und Ausführung: 12 bestanden (13,29 s).
- Erweiterte Ausführung mit Map–Collect–Map, Herkunftsnachweis, Assetumbenennung und Cache: 8 bestanden (8,49 s).

- Breiter Backendlauf: 433 bestanden, 6 fehlgeschlagen (244,49 s). Ursachen:
  verbliebene alte Canvasanlage, mehrfach gebundene Eingabepfade, alte
  Importdialogprüfung, übernommene Zwischenpublikationen und zwei veraltete
  Migrationserwartungen. Diese Stellen wurden anschließend bearbeitet.
- Gezielte Backendregression: 46 bestanden, 1 fehlgeschlagen (138,52 s).
  Der verbleibende historische Build ohne Vertragskennung wird jetzt ebenfalls
  als Nachweis übernommen und aus dem alten Objektbestand entfernt.
- Migration, Dateitransport, Altpakete und Umgebung: 15 bestanden (10,26 s).
- Bibliotheksprüfungen erfassen nun tatsächliche Paketdateien. Die Ampelanzeige
  startet keinen Diagnoseprozess im UI-Thread. Alte Werkzeugbündel werden beim
  ausdrücklichen Import direkt in aktuelle Skripte/Definitionen überführt.
- GUI-Abnahme läuft. Frühere Tests der Eigenschaftenleiste, Suchliste und
  separaten Einstellungen werden auf die neue Bedienung übertragen. Eine echte
  Regression wurde behoben: unveränderte ältere Assetdefinitionen verursachten
  beim Schließen eine falsche Änderungswarnung.

- Breiter GUI-Zwischenlauf: 209 bestanden, 9 fehlgeschlagen, 6 Fehler (187,28 s).
  Die Fehler betrafen entfernte Bedienelemente sowie Suchnavigation und
  Kontextzuordnung; anschließend gezielt korrigiert und nachgeprüft.
- Gezielte Qt-Nachprüfung von Kanban, Notizen, Pipelineverwendung, beiden
  Haupteditoren, Suche und Ablage: 30 bestanden (32,67 s).
- Qt-Nachprüfung von Profilen, Assetbearbeitung, Dokumenten, Masken, erhaltenen
  UI-Diensten, Baumzuordnung und echter Automatik: 37 bestanden (54,15 s).
- Erweiterte Backendabnahme: 20 bestanden, 1 fehlgeschlagen (21,16 s).
  Die Symlink-Blockade funktionierte; die Testmeldung erwartete ein anderes
  Wort. Der Test prüft jetzt die tatsächliche Symlink-Diagnose.

Letzte Läufe vor dem Benutzerstopp:

- `.venv/bin/python -m pytest -q tools/AssetManager/tests --ignore=tools/AssetManager/tests/gui`:
  **442 bestanden** (297,83 s).
- `.venv/bin/python -m pytest -q tools/AssetManager/tests/gui` mit Qt-Offscreen:
  **268 bestanden, 2 fehlgeschlagen** (303,22 s). Beide Fehler betrafen alte
  Such-/Verwendungsannahmen in `test_review_ui.py`.
- Gezielter Folgelauf von `test_review_ui.py`, `test_workspace_storage_search.py`
  und `test_pipeline_workspace.py`: **20 bestanden, 1 fehlgeschlagen** (15,60 s).
  Die beiden vorherigen Fehler bestanden nach Anpassung. Offen bleibt der neue
  Qt-Test zum Undo einer Skriptbaum-Umsortierung.
- PyGameTools `.tests` und `2-SpritesheetResolution-Pipline/tests`:
  **171 bestanden** (38,28 s).
- `python3 tools/control.py check`: **283 bestanden, 4 fehlgeschlagen,
  37 übersprungen** im Pythonteil; außerdem bestehende Stil-/Umgebungsbefunde.
  Assetablage, Godot-Fenstervertrag und zwei Dokumentationsprüfungen schlagen
  unabhängig vom Umbau fehl. Godot 4 fehlt; die Godot-Integration lief nicht.
- Native Qt-Ansichten bei 1100×700 und 1500×960 in hell/dunkel erzeugt;
  ausgewählte Ansichten visuell geprüft. Schmale Werkzeugleisten, Dateititel und
  Ampelfarben wurden korrigiert. Kein Nachweis weiterer Desktopplattformen.

Ein abschließender grüner Gesamtlauf nach den letzten Änderungen steht aus.
Nach dem Stopp wurde die Umsetzung nicht wieder aufgenommen. Der folgende
Abnahmeabgleich ist noch vollständig abzuschließen.

| Prüfgruppe | Abnahmekriterien des Auftrags | Geplanter Nachweis |
| --- | --- | --- |
| Dateien und Migration | Leerstart, Dateiidentität, externe Änderung, Migration, Altcode-Rückbau | Temporäre Projekte, Konflikt-/Unterbrechungsfälle, Abhängigkeitsprüfung |
| Oberfläche | Hauptnavigation, entfernte Elemente, bewusster Wechsel, Pythonbearbeitung | Tatsächliche Qt-Widgets, Fokus und Kontextmenüs, mehrere Fenstergrößen |
| Planung | Pipeline ohne Asset, Scope Asset/Akt/Projekt, Graph, Reihenfolge/Layout, Folder | Diensttests mit synthetischen Assetquellen und eindeutigen Ports |
| Ausführung | PA→PB mit zwei Assets, unverbundene Pipelines, GIF-Eingaben | Echte Worker-Ausführung, sichtbare Phasenfolge und geprüfte Ergebnisbytes |
| Freigabe/Automatik | Ampel, erste Freigabe, inkrementell, Codeänderung, Rückkopplung, Fehler/Pause/Abbruch, Änderung während Lauf, Cache | Kontrollierte Ereignisse und laufende Prozesse in isolierten Projekten |
| Ablage | Archiv/Verwendung, Entf/Papierkorb, Frist, Pipelinekarte entfernen | Steuerbare Testzeit, sichere Dateilöschung, Undo und echte Qt-Drops |
| Suche/Demo | Beide Suchen, ausschließlich ausdrückliche Demo | Dienst- und GUI-Tests einschließlich Wiederöffnung |
| Erhalt | Markdown, Assets, Quellen, Kanban, Bilder und Integration | Relevante bestehende Suiten, danach Repository-Standardcheck |

Tests zuerst eng und schnell, anschließend breiter. Übersprungene Prüfungen
zählen nicht als bestanden. Tatsächliche Befehle und Ergebnisse werden hier
während der Umsetzung ergänzt; auftragsfremde Ausgangsfehler separat erfasst.

## Erkenntnisse und Überraschungen

- Der Altbestand registriert Pakete beim Einstieg in Verarbeitung. Dies muss
  von einer rein lesenden Bibliotheksansicht getrennt werden.
- Alte Cacheeinträge referenzieren die Auftragstabellen direkt. Ein einfaches
  Entfernen der Auftragsoberfläche würde weder den Unterbau ablösen noch die
  erforderliche Ergebnisübernahme erledigen.

## Ergebnis und Rückblick

Auf Benutzerwunsch gestoppt und als Zwischenstand zum Commit vorbereitet.
Die Umsetzung bleibt im Repository; eine Auslagerung wurde nur besprochen.
Der [Bericht zum Zwischenstand](../asset-studio/ABSCHLUSSBERICHT_2026-09-29.md)
fasst Änderungen, tatsächliche Prüfergebnisse und offene Punkte zusammen.
Keine vollständige Umsetzung oder Abnahme behauptet.
