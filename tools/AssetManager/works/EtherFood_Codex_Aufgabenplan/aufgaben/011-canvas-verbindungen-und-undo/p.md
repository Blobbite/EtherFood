---
task_id: T011
phase: B
status: not_started
depends_on: ["T008", "T010"]
requirements: ["R03", "R04"]
---
# T011 — Verbindungen, Nebenpfade und Undo/Redo ergänzen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** B — Dashboard und Asset-Anlage  
**Abhängigkeiten:** [T008](../008-workflow-und-statusmodell/p.md), [T010](../010-canvas-hierarchie/p.md)  
**Anforderungsbezug:** R03, R04

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Mache Kartenverbindungen bearbeitbar, ohne visuelle Ordnung mit fachlichen Abhängigkeiten zu verwechseln.

## Kontext und Bestandsgrenzen

Es gibt belongs_to, uses und depends_on. Die Bildschirmposition einer Karte ist keine Prozessdefinition.

## Umsetzungsschirtte

1. Zeichne Verbindungstypen mit unterschiedlichen Linien-/Textkennzeichnungen und einer Legende. Linienkreuzungen dürfen keine unbeabsichtigte Verknüpfung erzeugen.

2. Erlaube das Anlegen einer Verbindung nur mit ausdrücklicher Auswahl ihres Typs. Prüfe zulässige Kartentypen und nutze die Zyklusprüfungen aus T006/T008.

3. Zeige vor dem Entfernen einer Beziehung ihre Bedeutung: Verwendung aufheben, Abhängigkeit entfernen oder Karte umordnen. Keine dieser Aktionen löscht automatsich Quelldateien.

4. Implementiere Undo/Redo über Anwendungsbefehle für Layout, Kartenanlage und zulässige Beziehungsänderungen. Nicht rückgängig machbare externe Aktionen wie eine Godot-Promotion gehören nciht auf denselben simplen Undo-Stapel.

5. Ergänze ein vertikales Auto-Layout als optionale Ansichtsfunktion. Vorhandene manuelle Layouts können separat gespeichert und wiederhergestellt werden.

6. Zeige gesperrte Workflow-Karten mit ihren konkreten Vorgängern und Sperrgründen. Rein erzählerische Akt-Reihenfolgen dürfen die technische Pipeline nciht blockieren.

7. Prüfe Save/Reload und Undo/Redo zusammen; ein Wiederöffnen darf keine neuen IDs oder Kanten erzeugen.

## Erwartete Ergebnisse

- `ui/canvas/edges.py`
- `application/commands.py`
- `Undo-/Beziehungs-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Eine Linie zwischen zwei Kapitelkarten startet keine Verarbeitung.
- [ ] Eine zyklische depends_on-Verbindung wird ohne Datenmutation abgelehnt.
- [ ] Undo einer Verwendungsänderung stellt die Verbindung wieder her, nciht eine Asset-Kopie.
- [ ] Ein Schnittpunkt zweier Kanten erzeugt keinen dritten Knoten.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Verbindungstypen sind sichtbar und explizit.
- [ ] Undo/Redo ist für unterstützte Aktionen getestet.
- [ ] Sperrgründe kommen aus dem Statusresolver.
- [ ] Layout und Workflow bleiben unabhängig.

## Nicht Bestandteil dieser Aufgabe

Kein beliebig programmierbarer visueller Code-Editor und keine Shell-Befehle in Karten.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T011.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T012 — Dokumentationseditor und Aufgabenansicht integrieren](../012-dokumentations-und-aufgaben-gui/p.md). Nicht automatsich starten.
