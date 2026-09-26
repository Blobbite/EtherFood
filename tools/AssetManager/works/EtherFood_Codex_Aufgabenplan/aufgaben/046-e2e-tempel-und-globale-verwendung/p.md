---
task_id: T046
phase: F
status: not_started
depends_on: ["T028", "T029", "T033", "T035", "T036", "T037", "T038", "T039", "T040", "T041", "T042", "T043", "T044"]
requirements: ["R06", "R24", "R28", "R29", "R30", "R35"]
---
# T046 — Tempelpaket, globale Effekte und gemeinsame Verwendung testen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** F — Betrieb und Gesamtprüfung  
**Abhängigkeiten:** [T028](../028-statische-texturpipeline/p.md), [T029](../029-assetpakete-und-tempel/p.md), [T033](../033-kandidaten-und-versionsarchiv/p.md), [T035](../035-godot-exportvertrag/p.md), [T036](../036-godot-testbereitstellung/p.md), [T037](../037-godot-tests-und-abnahmeszene/p.md), [T038](../038-freigabe-und-pruefbindungen/p.md), [T039](../039-runtime-promotion-und-rollback/p.md), [T040](../040-testbereich-sicher-aufraeumen/p.md), [T041](../041-versionsvergleich-und-projektfortschritt/p.md), [T042](../042-automatische-dokumentation-und-export/p.md), [T043](../043-erweiterbare-vorlagen-und-typen/p.md), [T044](../044-backup-recovery-und-speicherpflege/p.md)  
**Anforderungsbezug:** R06, R24, R28, R29, R30, R35

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Prüfe die statische Paketverarbeitung und die organisatorische Wiederverwendung von Assets durch mehrere Akte und Kapitel.

## Kontext und Bestandsgrenzen

Der Tempel enthält statische Bestandteile und benötigt keine Frame-Reduktion. Ein globaler Effekt kann dagegen animiert sein; Scope und Typ bleiben unabhängig.

## Umsetzungsschirtte

1. Erzeuge ein synthetisches Tempelpaket mit Boden, Decke und Säulen einschließlich gemeinsamer Maßstabs-/Ankerregeln. Lege es unter Akt 1 → Kapitel 1 an und verwende es zusätzlich in Kapitel 2.

2. Führe Import, Grafikableitung, statische Sichtprüfung, Kandidat, Godot-Test und kontrollierte Übernahme aus. Kein Auftrag für Frames oder GIFs darf dabei entstehen.

3. Prüfe Paketanschlüsse und gemeinsame Skalierung über alle fünf Grafikstufen. Erzeuge gezielt eine fehlerhafte Kachelgröße und verifiziere den daraus folgenden Befund.

4. Ändere eine Mitgliedsrevision. Nur davon abhängige Entwürfe werden veraltet; ein freigegebenes Paket behält seine gepinnten Mitglieder.

5. Verschiebe den Besitzer-Scope von aktbezogen zu global und ergänze eine Verwendung in Akt 2. Quellen, IDs, Archivpakete und aktive Versionen dürfen dadurch nciht dupliziert werden.

6. Lege zusätzlich einen globalen animierten Effekt mit kleiner Richtungsmenge an. Prüfe die passende Workflow-Auswahl, ohne eine echte neue Animation im Manager zu erzeugen.

7. Exportiere Akt-/Paketdokumentation und stelle eine Sicherung in einem anderen Verzeichnis wieder her. Verknüpfungen, Vorschauen und Freigabeverweise müssen danach konsistent bleiben.

## Erwartete Ergebnisse

- `tests/asset_studio/e2e/test_package_flow.py`
- `Statische Paketfixtures`
- `Paket-/Scope-E2E-Protokoll`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Das statische Paket erzeugt genau seine konfigurierten Grafikvarianten, keine Frameordner.
- [ ] Ein globaler animierter Effekt verwendet den animierten Workflow.
- [ ] Scope-Wechsel verändert keine Binärhashes und keine Mitglieds-IDs.
- [ ] Entfernen einer Kapitelverwendung löscht weder Paket noch andere Verwendungen.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Statischer und animierter Weg sind generisch nutzbar.
- [ ] Paketversionen pinnen ihre Mitglieder.
- [ ] Dokumentation und Restore funktionieren end-to-end.
- [ ] Keine Duplikation durch organisatorische Änderungen.

## Nicht Bestandteil dieser Aufgabe

Keine behauptete Prüffung der echten Tempelgrafiken ohne deren tatsächliche Sichtung.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T046.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T047 — Installation, automatisierte Prüfungen und Betrieb dokumentieren](../047-paketierung-ci-und-betrieb/p.md). Nicht automatsich starten.
