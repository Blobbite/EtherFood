---
task_id: T036
phase: E
status: not_started
depends_on: ["T005", "T017", "T033", "T035"]
requirements: ["R19", "R23"]
---
# T036 — Kandidaten im Godot-Testbereich bereitstellen und importieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** E — Versionen und Godot-Freigabe  
**Abhängigkeiten:** [T005](../005-pfade-und-objektspeicher/p.md), [T017](../017-worker-und-pipeline-adapter/p.md), [T033](../033-kandidaten-und-versionsarchiv/p.md), [T035](../035-godot-exportvertrag/p.md)  
**Anforderungsbezug:** R19, R23

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Stelle genau ein geprüftes ExportBundle kontrolliert unter test_assets bereit und starte passende Godot-Prüfungen.

## Kontext und Bestandsgrenzen

Der Nutzer möchte test_assets und test_scenes innerhalb EtherFood nutzen. Gemeinsame Testszenen sind Tool-Infrastruktur, keine bei jeder Promotion zu löschenden Asset-Datein.

## Umsetzungsschirtte

1. Implementiere DeploymentPlan mit erlaubten Zielen unter test_assets, exakter owned_files-Liste, ExportBundle-Digest, Projektpfad, Ziel-Engine und Importkonfiguration.

2. Nutze pro Testbereitstellung einen eindeutig namespacierten Bereich. Kopiere aus dem eingefrorenen ExportBundle in einen temporären Zielbereich und prüfe alle Datein vor Aktivierung.

3. Stelle die benötigten gemeinsamen Testszenen getrennt bereit und verwalte ihre Version. Bereits existierende benutzerbearbeitete Szenen dürfen nciht ungefragt überschrieben werden.

4. Starte Godots Import über den konfigurierten ausführbaren Pfad. Erfasse Prozessausgabe, Exit-Code und Importbefunde; ein Prozessende ohne erwarteten Report ist kein Testnachweis.

5. Behandle .godot als lokalen Cache und Importoptionen als relevante Konfiguration. Übertrage nciht blind .import-Datein mit Pfaden/UIDs aus einem anderen Deployment; verifiziere die tatsächlich wirksamen Optionen.

6. Verhindere automatische Aktivierung des Testbundles in regulären Spielszenen. Testkandidaten bleiben außerhalb der Runtime-Lockdatei und sind aus Produktions-Exports auszuschließen.

7. Speichere Deployment-ID, Kandidat, ExportBundle, Engine-, Szenen-/Templateversion und Projektkonfigurationsfingerprint. Ein späterer Testbericht muss genau auf diesen Kontext passen.

## Erwartete Ergebnisse

- `godot/deployment_service.py`
- `godot/import_runner.py`
- `Test-Staging- und Konfigurationstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Zwei Testkandidaten überschreiben einander nciht.
- [ ] Importfehler oder fehlende Engine ergeben failed/blocked statt passed.
- [ ] Ein geänderter fremder Testbereich wird vor Überschreiben als Konflikt gemeldet.
- [ ] Runtime-Szenen und Produktionslock bleiben während Tests unverändert.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Testbereitstellung ist vollständig journalisiert.
- [ ] Nur verwaltete Dateipfade werden geschrieben.
- [ ] Godot-Import und inhaltliche Tests sind getrennte Schritte.
- [ ] Testkontext ist eindeutig gebunden.

## Nicht Bestandteil dieser Aufgabe

Keine automatische Freigabe und kein Aufräumen älterer Kandidaten ohne Besitzprüfung.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q07: Workspace Skizze](../../quellen/Q07_Workspace_Skizze.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T036.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T037 — Godot-Testszene, technische Prüfungen und manuelle Abnahme bauen](../037-godot-tests-und-abnahmeszene/p.md). Nicht automatsich starten.
