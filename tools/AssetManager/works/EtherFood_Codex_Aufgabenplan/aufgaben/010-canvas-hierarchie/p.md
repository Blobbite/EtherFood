---
task_id: T010
phase: B
status: not_started
depends_on: ["T006", "T009"]
requirements: ["R02", "R03", "R04"]
---
# T010 — Karten-Canvas für globale Inhalte, Akte und Kapitel bauen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** B — Dashboard und Asset-Anlage  
**Abhängigkeiten:** [T006](../006-akte-kapitel-und-globale-inhalte/p.md), [T009](../009-gui-und-projektstart/p.md)  
**Anforderungsbezug:** R02, R03, R04

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Stelle das Projekt als übersichtliche, aufklappbare Kartenstruktur von oben nach unten dar.

## Kontext und Bestandsgrenzen

Der obere Rahmen enthält projektweite Grundlagen. Akte und Kapitel folgen darunter; Nebeninhalte werden nur auf der passenden Ebene ausführlich angezeigt.

## Umsetzungsschirtte

1. Implementiere die Kartenansicht mit QGraphicsScene/QGraphicsView oder einem funktional gleichwertigen Qt-Aufbau. Trenne Kartenmodell, Layoutzustand und Darstellung.

2. Zeige den globalen Rahmen oberhalb der geordneten Akte. Ermögliche das Auf-/Zuklappen von Akten und Kapiteln, ohne ihre Daten zu löschen.

3. Ergänze Akt anlegen, Kapitel anlegen und Nebenkarte anlegen als kontextbezogene Aktionen. Dialoge rufen die Dienste aus T006 auf.

4. Unterstütze Zoom, Verschieben der Ansicht, Auswahl, Fokus auf eine Karte und einen nachvollziehbaren Navigationspfad. Eine alternative Baum-/Listenansicht bleibt für große Projekte nutzbar.

5. Speichere Kartenposition und Gruppengröße als reine View-Daten. Kartenverschiebung verändert weder belongs_to noch depends_on; fachliche Umordnung erfolgt über eine ausdrückliche Aktion.

6. Zeige Asset-Verwendungen als Verweise mit Herkunftskennzeichnung. Ein verwendeter globaler Held darf nciht als neuer lokaler Held angelegt werden.

7. Lade Detailinhalte und Vorschaubilder erst bei Bedarf. Eine Variantenmatrix mit hunderten Ergebnissen wird nciht als hunderte Projektkarten gerendert.

## Erwartete Ergebnisse

- `ui/canvas/`
- `Canvas-View-Model`
- `Karten- und Navigationstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein Akt mit zwei Kapiteln kann aufgeklappt und wieder eingeklappt werden.
- [ ] Das Umpositionieren einer Karte verändert nur View-Daten.
- [ ] Zwei Verweise auf den Helden öffnen denselben Asset-Datensatz.
- [ ] Ein leeres Projekt zeigt verständliche Anlageaktionen statt eines kaputten Canvas.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Die Hierarchie ist erkennbar und persistent.
- [ ] Globale Inhalte stehen in einem eigenen Rahmen.
- [ ] Ansicht und fachliche Daten sind getrennt.
- [ ] Eine Listen-/Baumnavigation bleibt verfügbar.

## Nicht Bestandteil dieser Aufgabe

Keine automatischen Pipeline-Kanten aus gezeichneten Linien und keine grafische Bildbearbeitung.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T010.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T011 — Verbindungen, Nebenpfade und Undo/Redo ergänzen](../011-canvas-verbindungen-und-undo/p.md). Nicht automatsich starten.
