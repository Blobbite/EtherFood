---
task_id: T037
phase: E
status: not_started
depends_on: ["T025", "T029", "T035", "T036"]
requirements: ["R24", "R25", "R29", "R36"]
---
# T037 — Godot-Testszene, technische Prüfungen und manuelle Abnahme bauen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** E — Versionen und Godot-Freigabe  
**Abhängigkeiten:** [T025](../025-timing-und-animationsevents/p.md), [T029](../029-assetpakete-und-tempel/p.md), [T035](../035-godot-exportvertrag/p.md), [T036](../036-godot-testbereitstellung/p.md)  
**Anforderungsbezug:** R24, R25, R29, R36

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Prüfe die tatsächlichen Spielressourcen und ermögliche die visuelle Abnahme in Godot.

## Kontext und Bestandsgrenzen

Ein erfolgreicher Import ist keine bestandene Assetprüfung. Technische Checks und menschliche Abnahme benötigen verschiedene Nachweise.

## Umsetzungsschirtte

1. Implementiere eine sichtbare Testszene mit Auswahl von Asset/Paket, Pose, Richtung, Grafikprofil und Frame-Stufe. Zeige Kandidat-/ExportBundle-ID, tatsächliche Maße, Dauer und Anker.

2. Baue automatisierte Godot-Tests für Laden, vollständige Animationen, Framezahl, Timing, Loop, Anker und fehlende Abhängigkeiten. Für statische Pakete prüfe Mitglieder, Maßstab und korrekte Ressourcenauflösung.

3. Führe alle geforderten Kombinationen technisch durch; die visuelle Ansicht lädt nur die aktuelle Auswahl. Sammle Fehler je Kombination und erzeugte Screenshots nur dort, wo sinnvoll.

4. Schreibe einen maschinenlesbaren Testbericht mit build_id, candidate_id, export_id, deployment_id, Engine-Version, Template-Digest, Projektkonfigurationshash, Testfällen und tatsächlich ausgeführten Ergebnissen.

5. Ergänze die manuelle Checkliste für Farbe, Bewegung, Materialgrenzen, Übergänge und Paketanschlüsse. Eine Betätigung in der Testszene oder im Dashboard wird als manuelle Bestätigung mit Scope gespeichert, nciht als automatsich bewiesene Prüffung.

6. Erfasse Performance-Messwerte nur mit Testplattform und Szenario. Keine pauschale Speicher-/Geschwindigkeitsgarantie aus Framezahl oder Datei-Kilobytes ableiten.

7. Binde Rückmeldungen kontrolliert an den Manager, etwa über lokal verifizierte Reportdateien. Ein beliebiger alter JSON-Bericht oder fremdes passed=true darf keine Freigabe auslösen.

## Erwartete Ergebnisse

- `Godot test_scenes und Testscripts`
- `Versioniertes Testreport-Schema`
- `Godot-Integrationstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Eine absichtlich fehlende Richtung wird mit der konkreten Kombination als Fehler gemeldet.
- [ ] Ein alter Report eines anderen Kandidaten wird abgelehnt.
- [ ] Ein 2-Sekunden-preserve_duration-Build bleibt in Godot 2 Sekunden lang.
- [ ] Manuelle Abnahme bleibt offen, wenn nur Headless-Tests liefen.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Headless- und sichtbare Prüfungen sind vorhanden.
- [ ] Berichte sind an den vollständigen Kontext gebunden.
- [ ] Alle erforderlichen Kombinationen sind technisch abgedeckt.
- [ ] Visuelle Abnahme wird niemals fingiert.

## Nicht Bestandteil dieser Aufgabe

Keine Änderungen an Gameplay-Kampf-/Questlogik und keine automatischen Screenshots als menschliche Freigabe behandeln.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T037.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T038 — Freigaben mit exakten Build- und Testbindungen implementieren](../038-freigabe-und-pruefbindungen/p.md). Nicht automatsich starten.
