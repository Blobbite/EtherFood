---
task_id: T038
phase: E
status: not_started
depends_on: ["T008", "T032", "T033", "T036", "T037"]
requirements: ["R24", "R25", "R26", "R36"]
---
# T038 — Freigaben mit exakten Build- und Testbindungen implementieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** E — Versionen und Godot-Freigabe  
**Abhängigkeiten:** [T008](../008-workflow-und-statusmodell/p.md), [T032](../032-variantenpruefung-und-fehlerkarten/p.md), [T033](../033-kandidaten-und-versionsarchiv/p.md), [T036](../036-godot-testbereitstellung/p.md), [T037](../037-godot-tests-und-abnahmeszene/p.md)  
**Anforderungsbezug:** R24, R25, R26, R36

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Erteile Freigaben ausschließlich für den konkret geprüften Inhalt und verhindere veraltete oder unvollständige Nachweise.

## Kontext und Bestandsgrenzen

Erledigt, technisch geprüft, in Godot getestet, freigegeben und im Spiel verwendet sind verschiedene Zustände.

## Umsetzungsschirtte

1. Implementiere Approval mit unveränderlichem Bezug auf Candidate/ExportBundle, Prüfumfang, erforderliche Checks, manuelle Reviews, Engine-/Template-/Projektkontext, Entscheiderangabe und Zeitpunkt.

2. Prüfe vor der Freigabe Vollständigkeit, aktuelle Datei-Prüfsummen, Pflichtchecks, offene blockierende Issues und menschliche Sichtbestätigungen. Not_required braucht eine zulässige begründete Regel.

3. Verhindere die Verwendung veralteter Testberichte nach Änderung von Profil, Maske, Exporter, Testszene oder relevanter Importkonfiguration. Ein globaler zuletzt-bestanden-Zustand ist unzulässig.

4. Baue den Freigabedialog mit klarer Zusammenfassung: exakt freizugebende Version, Prüfungen, manuelle Bestätigungen, offene nciht blockierende Hinweise und spätere Zielverwendung.

5. Freigabe schreibt einen neuen Auditdatensatz, verändert aber keine eingefrorenen Kandidatenbytes. Widerruf und Ablehnung werden ebenfalls als neue Ereignisse mit Grund festgehalten.

6. Nach einer Freigabe kann ein neuer Entwurf entstehen, ohne den alten Stand aus dem Spiel zu entfernen. Eine neue Freigabe schaltet die Runtime nciht automatsich um; Promotion bleibt ein gesonderter Schritt.

7. Führe Sammelfreigaben für Pakete nur aus, wenn die exakten Mitgliedsbuilds feststehen und alle Paketkriterien erfüllt sind.

## Erwartete Ergebnisse

- `application/approval_service.py`
- `ui/approval_dialog.py`
- `Freigabe-/Stale-Report-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein fehlgeschlagener Pflichtcheck blockiert auch bei gesetztem erledigt-Haken.
- [ ] Freigabe für Kandidat A lässt sich nciht auf Kandidat B anwenden.
- [ ] Eine nach dem Test geänderte Importoption erfordert einen neuen passenden Nachweis.
- [ ] Ein widerrufener Kandidat wird nciht neu promotet; bestehende Verwendung wird sichtbar gemeldet.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Freigaben sind exakt und nachvollziehbar.
- [ ] Keine stillen Ausnahmen von Pflichtprüfungen.
- [ ] Auditverlauf bleibt erhalten.
- [ ] Freigabe und produktive Aktivierung sind getrennt.

## Nicht Bestandteil dieser Aufgabe

Keine Dateiverschiebung in Runtime und keine fingierten Personennamen oder Sichtprüfungen.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T038.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T039 — Freigegebene Versionen sicher ins Spiel übernehmen](../039-runtime-promotion-und-rollback/p.md). Nicht automatsich starten.
