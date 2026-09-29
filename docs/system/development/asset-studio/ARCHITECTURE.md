# Architektur und Datenverträge

[Asset Studio](index.md) · [Arbeitsplan](../plans/asset-studio-zwei-editoren-und-automatik.md)

## Bestehende Anwendung und Zuständigkeiten

Das Python-Paket unter `tools/AssetManager/src/etherfood_studio/` bleibt eine
native PySide6-Anwendung. Es verwendet den vorhandenen Katalog, Dokumentdienst,
BlobStore, sichere Pfade und das SQL-/Dateijournal. PyGameTools-Bildalgorithmen
bleiben nutzbar. Keine zweite Browseroberfläche und keine zweite Dokumentablage.

| Bereich | Verantwortung |
| --- | --- |
| `domain.pipeline_contract` | Aktueller `studio-pipeline-v3`-Vertrag, benannte Ports, Graph, Folder, Parameter |
| `WorkspaceFiles` | Aktuelle Dateien, stabile IDs, Helfer, Konflikte, sichere Umzüge |
| `PipelineWorkspace` | Definition/Verwendung, Eingabebereiche, semantische Reihenfolge, Prüf-/Freigabestand |
| `PipelineInputs`, `SourceReconciliation` | Ausschließlich aktuelle registrierte Quellen; generische Eignung und geprüfte externe Änderungen |
| `PipelineExecution`, `PipelineResults` | Gefrorener Durchgang, Phasengrenzen, Schrittcache, Ergebnisprüfung und aktuelle Herkunft |
| `pipeline_worker`, `pipeline_supervisor` | Einheitliche Python-Schnittstelle, kontrollierte Prozesse, Abbruch und Laufverzeichnisse |
| `PipelineController` | Qt-Dateibeobachtung, gebündelte Ereignisse, ein serieller Hintergrundarbeiter, kontrolliertes Schließen |
| `LifecycleService` | Getrennte Original-/Verwendungszustände, UTC-Fristen, atomare Wiederherstellung, besitzgebundene Bereinigung |
| `WorkspaceMigration`, `RetireJobs` | Gesicherte wiederaufnehmbare Übernahme und tatsächlicher Rückbau der alten Auftragsbestände |
| `SearchService`, `WorkspaceSearch` | Getrennte Suchlogik und identisch angeordnete Projekt-/Werkzeugsuchen |

`MainWindow` besitzt genau zwei Haupteditoren. `DefinitionEditor` verwendet den
vorhandenen Canvas-Unterbau und eine kompakte kontextuelle Bearbeitung.
`ScriptWorkspace` verwendet den vorhandenen Python-Texteditor. Die bestehende
Markdown-, Notiz-, Kanban-, Quellen- und Assetbearbeitung bleibt eingebunden.

## Autoritative Daten

| Inhalt | Maßgebliche Ablage |
| --- | --- |
| Aktueller Pythoncode und deklarierte Hilfsdateien | `.tools/scrips/` |
| Aktuelle Pipelineverschaltung, Parameter, Folder | `.tools/piplins/` |
| IDs, Skriptbeschreibungen, Zuordnungen, Freigaben, Archiv/Papierkorb | Bestehender SQLite-Katalog |
| Koordinaten, Zoom und Ansicht | `layouts`, unabhängig vom Ausführungsfingerprint |
| Unveränderliche registrierte Quellbytes und Ressourcen | Bestehender hashbasierter BlobStore |
| Markdowntext, Dokument-ID und Revision | Bestehender Dokumentdienst und seine Dateiprojektion |

`pipeline_definition` und `pipeline_usage` sind verschiedene Objekte. Mehrere
Verwendungen referenzieren eine Definition. Gewöhnliche `belongs_to`, `uses`
und `depends_on`-Projektbeziehungen ersetzen keine Ergebnisverbindung.
Die Verwendung enthält ausdrücklich benannte Vorgängeranschlüsse und eine
von Bildschirmkoordinaten getrennte fachliche Reihenfolge.

Schema 11 ergänzt aktuelle Dateibesitzlisten, Pipelineprüfstatus, Ergebnisse,
Versuche, Schrittcache und Lebenszykluszustände. Schema 12 ergänzt historische
Ergebnisnachweise und Besitzlisten für Laufkopien. Gemeinsame Hilfsdateien
können mehrere Besitzer besitzen. Alte Auftragstabellen werden erst nach
inhaltlicher Ergebnisübernahme entfernt, nicht blind beim Schema-Upgrade.

## Ausführung und Freigabe

Ein Dry-run prüft ohne Verarbeitung und kann seinen lokalen Prüfstatus
speichern. Die Freigabe bindet den aktuellen ausführbaren Gesamtstand samt
Code, Hilfsdateien, Bibliotheksbestand, Parametern und wirksamer Verschaltung.
Projekt-Eingabezuordnungen werden davon getrennt validiert. Eingabefehler
widerrufen keine unveränderte Codefreigabe.

Vor jedem Start wird die Freigabe erneut geprüft. Skripte, Hilfsdateien,
Ressourcen und Eingaben werden für den Durchgang eingefroren. Je Verwendung
werden erst sämtliche betroffenen Assetquellen verarbeitet; Folge-Verwendungen
beginnen nach erfolgreichem Abschluss der gesamten Vorgängerphase.

Die Ausführung ist seriell, mit höchstens einem vorgemerkten erneuten Abgleich.
Qt bleibt bedienbar. Pause verhindert Starts; Abbruch beendet kontrolliert den
Prozessbaum. Identische fehlgeschlagene Fingerprints warten auf Korrektur oder
einen ausdrücklichen neuen Versuch. Unabhängige gültige Ketten bleiben nutzbar.

Der Schrittcache prüft Ergebnisbytes und Vertrag vor Wiederverwendung. Folder
veröffentlichen ausschließlich vollständig geprüfte Ergebnisse in verwalteten
Bereichen. Ein erneuter Vergleich des wirksamen Eingabe-/Graph-/Codestands
verhindert die Veröffentlichung eines inzwischen veralteten Durchgangs als
aktuelles Ergebnis. Ergebnisse bleiben nach Asset und Verwendung unterscheidbar.

## Transaktionen, Konflikte und Dateibesitz

`Catalog.transaction()` und `FileChanges` koordinieren SQL und Dateien. Schreiben,
Verschieben und besitzgebundenes Löschen werden journalgeführt ausgeführt und
bei Fehlern zurückgenommen. Vor Überschreiben werden Hash und Objekt-Revision
geprüft. Externe Änderungen und App-Entwürfe dürfen einander nicht still ersetzen.
Fehlende aktuelle Dateien werden nicht aus historischem Code rekonstruiert.

Archiv hat kein Ablaufdatum. Papierkorb besitzt UTC-Entfernungszeit und exakt
720 Stunden Frist. Wiederherstellung mit neuer Zielzuordnung ist ein gemeinsamer
Undo-Schritt. Bereinigung prüft aktuelle Frist, Dateibesitz, Hash und verbleibende
Referenzen und läuft nur bei geöffneter App. Fremde Dateien bleiben erhalten.
Nach Bereinigung werden betroffene Undo-Einträge verworfen.

## Migration und historische Verträge

Vor destruktiven Schritten werden Katalog und ausdrücklich verwaltete Dateien
mit Manifest gesichert. Unterschiedliche gebundene Codefassungen erhalten
eigene stabile Skriptidentitäten. Wirksame frühere Zuweisungsprioritäten werden
in konkrete Verwendungen übertragen, Mehrdeutigkeiten sichtbar blockiert.

Alte Paket-/Rezeptdecoder dienen ausschließlich der Übernahme und des bewussten
Imports. Historische Pakete steuern keinen aktuellen Pythonlauf. Frühere
Ergebnisse und Nachweise werden vor Entfernung der Auftragsobjekte und Tabellen
übertragen. `JobService`, `JobStore`, Buildplan-/Adapter-Ausführung und ihre
UI-/CLI-Einstiege sind entfernt. Kanbanaufgaben, Issues, Dokumente und
Entwicklungsarbeitspläne sind davon unabhängig.

Der ältere Vertrag `contracts-v1.json` bleibt für vorhandene historische
Metadaten und gesonderte spätere Export-/Reviewdaten lesbar. Er ist nicht der
aktuelle Pipelineausführungsvertrag.

## Grenzen

Lokale Einzelbenutzerdaten, kein Netzlaufwerk-Multiwriter. Python-Umgebungen
trennen Bibliotheken, bieten aber keine Sicherheits-Sandbox. Freigegebener Code
wird als lokaler Code ausgeführt. Kontrollierte Prozesssteuerung benötigt
gegenwärtig Linux `/proc`. Sichere Pfadprüfung verbietet Elternpfade und Symlink-
Auswege; sie ist keine Garantie gegen einen bösartigen zweiten OS-Benutzer.

Markdowninhalte führen beim Anzeigen oder Navigieren keinen Build oder
Pythoncode aus. Code-/SVG-/Bilddarstellung unterliegt weiterhin den bestehenden
Dokument- und Medienregeln. Automatische Dokumenterzeugung wurde nur dort
angepasst, wo Ergebnisgalerien auf den neuen Ergebnisvertrag verweisen müssen.
