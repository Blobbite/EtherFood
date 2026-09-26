---
task_id: T044
phase: F
status: not_started
depends_on: ["T004", "T005", "T017", "T018", "T033", "T034", "T039", "T040", "T041"]
requirements: ["R22", "R33", "R34"]
---
# T044 — Sicherung, Wiederherstellung und Speicherpflege absichern

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** F — Betrieb und Gesamtprüfung  
**Abhängigkeiten:** [T004](../004-katalog-und-migrationen/p.md), [T005](../005-pfade-und-objektspeicher/p.md), [T017](../017-worker-und-pipeline-adapter/p.md), [T018](../018-buildplan-cache-und-invalidation/p.md), [T033](../033-kandidaten-und-versionsarchiv/p.md), [T034](../034-git-und-quellenrevisionen/p.md), [T039](../039-runtime-promotion-und-rollback/p.md), [T040](../040-testbereich-sicher-aufraeumen/p.md), [T041](../041-versionsvergleich-und-projektfortschritt/p.md)  
**Anforderungsbezug:** R22, R33, R34

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Mache die Anwendung gegen Abbrüche, volle Laufwerke und beschädigte Zwischenergebnisse widerstandsfähig.

## Kontext und Bestandsgrenzen

Originalquellen, eingefrorene Kandidaten und aktive Spielversionen dürfen nciht wie löschbarer Cache behandelt werden.

## Umsetzungsschirtte

1. Implementiere konsistente Projektsicherungen mit Katalog, referenzierten Quellen/Masken/Profilen, Dokumenten, Kandidaten und Deployment-Journalen. Ein reines DB-Backup ohne Binärreferenzen reicht nciht.

2. Ergänze Wiederherstellen in einen neuen Zielordner mit Pfad-Neuzuordnung, Hashprüfung und Schema-Kompatibilität. Überschreibe kein laufendes Projekt beim ersten Restore.

3. Implementiere Startup-Recovery für unterbrochene Importe, Builds, Kandidatenkopien und Promotions. Journalzustände werden anhand tatsächlicher Datein abgeglichen, nciht pauschal auf succeeded gesetzt.

4. Führe eine Retentionsplanung für nachweislich unreferenzierte temporäre Datein und Cache-Artefakte ein. Quellen, Freigaben, aktive Deployments und für Rollback gepinnte Pakete sind geschützt.

5. Zeige Speicherverbrauch nach Quellen, Cache, Kandidaten, Testbereitstellungen und Runtime. Vor einer Bereinigung wird eine konkrete Lösch-/Quarantäneliste mit Besitz- und Hashprüfung angezeigt.

6. Behandle entfernbare Datenträger, Schreibschutz, fehlenden Speicher und konkurrierende Anwendungsinstanzen. Zweite Instanz wird lesend geöffnet oder kontrolliert abgewiesen; kein unkoordiniertes Schreiben.

7. Führe automatisierte Fehler-Injektion für relevante Operationsschritte aus. Dokumentiere, welche Wiederherstellungswege tatsächlich getestet wurden.

## Erwartete Ergebnisse

- `storage/backup_service.py`
- `application/recovery_service.py`
- `Retentions-/Restore-/Crash-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Restore eines Projekts an einem anderen Pfad öffnet Quellen und Kandidaten korrekt.
- [ ] Ein während Promotion abgezogenes Zielmedium erzeugt einen rekonstruierbaren Zustand.
- [ ] Cache-Cleanup entfernt keine von Kandidaten oder Runtime referenzierten Datein.
- [ ] Eine zweite Instanz schreibt nciht gleichzeitig dieselbe lokale Metadatenbasis.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Backup und Restore sind praktisch getestet.
- [ ] Journale werden konsistent wiederaufgenommen.
- [ ] Speicherpflege respektiert alle Referenzen.
- [ ] Keine globale Löschung anhand bloßer Ordnernamen.

## Nicht Bestandteil dieser Aufgabe

Keine Behauptung eines hochverfügbaren Mehrbenutzersystems und keine automatische Löschung ohne Vorschau.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T044.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T045 — Gesamtablauf für Held und NPCs mit weniger Richtungen testen](../045-e2e-held-und-npc/p.md). Nicht automatsich starten.
