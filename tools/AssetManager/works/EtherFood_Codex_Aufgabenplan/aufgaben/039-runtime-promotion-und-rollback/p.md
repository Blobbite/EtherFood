---
task_id: T039
phase: E
status: not_started
depends_on: ["T005", "T033", "T035", "T036", "T037", "T038"]
requirements: ["R19", "R26", "R27", "R33"]
---
# T039 — Freigegebene Versionen sicher ins Spiel übernehmen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** E — Versionen und Godot-Freigabe  
**Abhängigkeiten:** [T005](../005-pfade-und-objektspeicher/p.md), [T033](../033-kandidaten-und-versionsarchiv/p.md), [T035](../035-godot-exportvertrag/p.md), [T036](../036-godot-testbereitstellung/p.md), [T037](../037-godot-tests-und-abnahmeszene/p.md), [T038](../038-freigabe-und-pruefbindungen/p.md)  
**Anforderungsbezug:** R19, R26, R27, R33

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Aktiviere genau den freigegebenen Export im regulären Godot-Bereich und ermögliche eine kontrollierte Rückkehr zur vorherigen Version.

## Kontext und Bestandsgrenzen

Das Spiel soll weiterhin funktionieren, wenn eine Übernahme abbricht. Mehrere Dateioperationen sind nciht von selbst eine atomare Transaktion.

## Umsetzungsschirtte

1. Implementiere einen PromotionPlan mit Candidate/ExportBundle/Approval, bisheriger Runtime-Zuordnung, Zielpfaden, owned_files, Prüfsummen und erwarteter Lockdatei-Revision. Prüfe alle Bedingungen erneut unmittelbar vor dem Schreiben.

2. Kopiere das freigegebene unveränderliche Runtime-Payload in einen neuen versionierten Bereich unter assets. Keine erneute Farb-/Frame-/Grafikberechnung beim Promoten.

3. Halte spielseitige Verknüpfungen außerhalb des Payload möglichst in einem stabilen Manifest-/Loadervertrag. Deployment-spezifische Importoptionen, .import-Pfade und UIDs müssen gültig erzeugt und auf ihre wirksame Semantik geprüft werden.

4. Führe am finalen Ziel einen Ressourcenlade-/Referenztest aus. Gibt es unvermeidbare abgeleitete Wrapperänderungen, speichere deren Digest und Testnachweis separat; behaupte nciht bytegleiche Test-/Runtime-Wrapper, wenn sie umgeschrieben wurden.

5. Aktiviere die neue Runtime-Lockdatei erst nach vollständiger Prüffung, mit Konfliktkontrolle und ersetzender Einzeldateioperation im selben Dateisystem. Das Journal erlaubt Wiederaufnahme oder Rücknahme bei Absturz vor/nach Aktivierung.

6. Erhalte die vorherige freigegebene Runtime-Version für Rollback. Andere Assets in assets.lock.json dürfen nciht verloren gehen. Eine Promotion eines globalen Assets zeigt betroffene Verwendungen und verlangt eine bewusste Aktivierung.

7. Bei Fehler bleibt die alte aktive Zuordnung erhalten oder wird anhand Journal konsistent wiederhergestellt. Der Testbereich wird noch nciht gelöscht; dessen Bereinigung gehört T040.

## Erwartete Ergebnisse

- `godot/promotion_service.py`
- `Runtime-Lockvertrag`
- `Fehlerinjektions- und Rollbacktests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Abbruch vor Lock-Aktivierung lässt die bisherige Spielversion aktiv.
- [ ] Eine inzwischen geänderte Lockdatei führt zu Konflikt statt Verlust anderer Assetzuordnungen.
- [ ] Bild-/Manifest-Payload ist identisch mit dem freigegebenen ExportBundle.
- [ ] Finale Ressourcen verweisen nciht auf test_assets; Rollback lädt wieder die vorherige Version.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Promotion ist journalisiert und wiederaufnehmbar.
- [ ] Neue Version wird erst nach finalem Check aktiv.
- [ ] Kein unbemerkter Rebuild während Promotion.
- [ ] Rollback ist an synthetischen Godot-Daten getestet.

## Nicht Bestandteil dieser Aufgabe

Keine rekursive Überschreibung des gesamten assets-Ordners und kein Löschen des alten Standes während Aktivierung.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q07: Workspace Skizze](../../quellen/Q07_Workspace_Skizze.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T039.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T040 — Testbereitstellungen nach erfolgreicher Übernahme gezielt aufräumen](../040-testbereich-sicher-aufraeumen/p.md). Nicht automatsich starten.
