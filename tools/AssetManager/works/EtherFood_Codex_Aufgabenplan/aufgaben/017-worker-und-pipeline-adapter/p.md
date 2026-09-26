---
task_id: T017
phase: C
status: not_started
depends_on: ["T003", "T005", "T008", "T015"]
requirements: ["R19", "R21", "R33"]
---
# T017 — Arbeitsprozesse und gemeinsame Pipeline-Adapter bauen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** C — Aufträge, Farben und Frame-Verarbeitung  
**Abhängigkeiten:** [T003](../003-python-grundgeruest/p.md), [T005](../005-pfade-und-objektspeicher/p.md), [T008](../008-workflow-und-statusmodell/p.md), [T015](../015-quellen-und-spritesheet-import/p.md)  
**Anforderungsbezug:** R19, R21, R33

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Führe bestehende Python-Werkzeuge kontrolliert in eigenen Arbeitsprozessen aus und liefere verlässliche Ergebnisse an GUI und CLI.

## Kontext und Bestandsgrenzen

Die vorhandenen Starter haben unterschiedliche Seiteneffekte. Ein separater Prozess ist hier eine Fehler-/Arbeitsraumtrennung, keine vollständige Sicherheits-Sandbox für beliebigen fremden Code.

## Umsetzungsschirtte

1. Definiere PipelineAdapter mit validate, plan, execute und verify. Verwende nur registrierte lokale Werkzeuge; Befehle werden als Argumentlisten ohne Shell-Interpolation aufgebaut.

2. Implementiere je Auftrag einen unverwechselbaren job_id, eine eingefrorene BuildRequest und eigene Eingabe-, Ausgabe- und Logbereiche. Kopien für verändernde Altpipelines sind von geschützten Quellen getrennt.

3. Baue den Qt-Prozessadapter ereignisgesteuert mit stdout/stderr-Verarbeitung, Exit-Code, Startfehler, Zeitlimit und Abbruch. Warte nciht blockierend im GUI-Hauptthread. Der Core-Vertrag bleibt ohne Qt verwendbar.

4. Führe strukturierte Ereignisse mit Sequenznummer ein: gestartet, Phase, Fortschritt, Warnung, Fehler und beendet. Bestehende Konsolenausgaben werden zusätzlich unverändert gespeichert; Erfolg folgt aus Ergebnisprüfung, nciht aus Textsuche nach Fertig.

5. Begrenze parallele Aufträge und verhindere zwei Schreibaufträge auf denselben Ergebnisbereich. Beim Abbruch beende auch verwaltete Kindprozesse und warte, bis keine weiteren Datein geschrieben werden.

6. Implementiere zunächst einen synthetischen Adapter für Tests sowie einen lesenden --help/--dry-run-Adapter für reale Starter. Produktive Läufe bleiben auf ausdrücklich freigegebene Arbeitskopien beschränkt.

7. Persistiere Auftrag und Abschlusszustand. Nach Programmabsturz ist ein offener Auftrag interrupted, niemals automatsich succeeded. Protokolliere alle tatsächlich ausgeführten Argumente und Werkzeug-Hashes.

## Erwartete Ergebnisse

- `pipelines/base.py`
- `application/job_service.py`
- `ui/process_runner.py`
- `Fake-Worker und Prozessintegrationstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein fehlerhaftes Tool mit Exit-Code 7 wird als Fehler gemeldet.
- [ ] Ein Tool mit Exit-Code 0, aber fehlender erwarteter Datei besteht verify nciht.
- [ ] Abbrechen eines Prozesses verhindert nachträgliche Ausgabe eines Kindprozesses.
- [ ] Ein langer Auftrag blockiert weder Navigation noch GUI-Fenster.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Core- und Qt-Ausführung teilen denselben Auftragsvertrag.
- [ ] Keine Shell-Injection über Assetnamen oder Pfade.
- [ ] Abbruch, Fehler und Neustart sind getestet.
- [ ] Quellbilder werden nciht im Arbeitsprozess überschrieben.

## Nicht Bestandteil dieser Aufgabe

Keine Ausführung beliebiger Python-Skripte aus importierten Paketen; keine systemweiten Installationen.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q06: Gemeinsame Schreibregeln](../../quellen/Q06_Gemeinsame_Schreibregeln.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T017.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T018 — Build-Abhängigkeiten, Cache und Änderungsfolgen umsetzen](../018-buildplan-cache-und-invalidation/p.md). Nicht automatsich starten.
