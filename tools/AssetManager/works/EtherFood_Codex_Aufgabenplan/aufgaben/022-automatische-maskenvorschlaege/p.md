---
task_id: T022
phase: C
status: not_started
depends_on: ["T017", "T018", "T020", "T021"]
requirements: ["R11", "R36"]
---
# T022 — Automatische Maskenvorschläge mit Unsicherheitsanzeige entwickeln

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** C — Aufträge, Farben und Frame-Verarbeitung  
**Abhängigkeiten:** [T017](../017-worker-und-pipeline-adapter/p.md), [T018](../018-buildplan-cache-und-invalidation/p.md), [T020](../020-materialmasken-und-quellbindung/p.md), [T021](../021-maskeneditor-und-materialauswahl/p.md)  
**Anforderungsbezug:** R11, R36

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Reduziere die manuelle Beschriftung durch wiederverwendbare Materialregeln und überprüfbare Vorschläge, ohne falsche Vollautomatik zu behaupten.

## Kontext und Bestandsgrenzen

Dies ist eine neue Funktion. Der Bestand erzeugt Vorlagen und verarbeitet vorhandene Masken, garantiert aber keine allgemeine Materialerkennung.

## Umsetzungsschirtte

1. Definiere ein versioniertes Vorschlagsrezept mit Material-Seeds, Farbbereichen, optionalen räumlichen Einschränkungen und Prioritäts-/Konfliktregeln. Regeln werden vom Nutzer festgelegt oder aus bestätigten Labels abgeleitet und transparent angezeigt.

2. Implementiere einen ersten deterministischen Vorschlagsalgorithmus auf Basis dieser Regeln. Gleiche Eingaben ergeben gleiche Labels; mehrdeutige Bereiche bleiben offen statt willkürlich einem Material zugeordnet zu werden.

3. Führe eine separate Unsicherheits-/Abdeckungsdarstellung ein. Ein heuristischer Score darf nciht als kalibrierte Wahrscheinlichkeit bezeichnet werden.

4. Wende Vorschläge je tatsächlichem Frame an. Eine Stand-Maske wird nciht positionsgleich auf bewegte Frames kopiert. Zeitliche Übertragung darf nur mit explizitem Verfahren, Prüfbarkeit und erhaltenen Unsicherheitsmarkierungen erfolgen.

5. Erhalte manuell bestätigte Bereiche und biete Vorschlag übernehmen, teilweise übernehmen oder verwerfen an. Ein neuer Vorschlagslauf überschreibt keine bestätigte MaskRevision.

6. Integriere den Schritt zwischen Import und Farbkorrektur. Vollständig technisch belegte Labels benötigen weiterhin die vorgesehene Sichtprüfung; offene Pflichtbereiche blockieren Materialfreigabe.

7. Baue synthetische Testsequenzen mit überlappenden Farben, bewegten Formen und verdeckten Bereichen. Keine externen KI-Dienste oder Modellgewichte als Pflichtabhängigkeit einführen.

## Erwartete Ergebnisse

- `pipelines/mask_suggestions.py`
- `Versioniertes Vorschlagsrezept`
- `GUI-Vorschlagsabnahme und Segmentierungs-Fixtures`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Gleiches Braun in Haar- und Lederregion erzeugt ohne ausreichende Unterscheidungsregel einen offenen Konflikt.
- [ ] Bewegte Formen erhalten keine blind kopierten Stand-Labels.
- [ ] Wiederholung mit denselben Seeds liefert denselben Ergebnisdigest.
- [ ] Manuell bestätigte Bereiche bleiben nach einem Vorschlagslauf erhalten.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Vorschläge sind praktisch nutzbar und reproduzierbar.
- [ ] Unsicherheit wird sichtbar statt kaschiert.
- [ ] Der Nutzer kann alle Vorschläge korrigieren.
- [ ] Automatische Erzeugung ist nciht automatische Abnahme.

## Nicht Bestandteil dieser Aufgabe

Keine Garantie vollständiger semantischer Segmentierung und kein erzwungener Cloud-Dienst.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q05: SourceColor Bestand](../../quellen/Q05_SourceColor_Bestand.md)
- [Q09: Masken Profilregeln Bestand](../../quellen/Q09_Masken_Profilregeln_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T022.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T023 — SourceColor und SpritesheetColor in die Build-Pipeline einbinden](../023-farbkorrektur-pipeline/p.md). Nicht automatsich starten.
