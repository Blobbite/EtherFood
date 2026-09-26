---
task_id: T018
phase: C
status: not_started
depends_on: ["T008", "T013", "T015", "T017"]
requirements: ["R20", "R21", "R22"]
---
# T018 — Build-Abhängigkeiten, Cache und Änderungsfolgen umsetzen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** C — Aufträge, Farben und Frame-Verarbeitung  
**Abhängigkeiten:** [T008](../008-workflow-und-statusmodell/p.md), [T013](../013-assettypen-posen-und-richtungen/p.md), [T015](../015-quellen-und-spritesheet-import/p.md), [T017](../017-worker-und-pipeline-adapter/p.md)  
**Anforderungsbezug:** R20, R21, R22

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Baue nur die tatsächlich betroffenen Varianten neu und erkläre vor jedem Lauf, was geplant ist.

## Kontext und Bestandsgrenzen

Der technische Build-Graph ist von Akt-/Kapitelstruktur und Canvas-Layout getrennt. Die Semantik des alten Normalmodus darf nciht als Cache-Validierung dienen.

## Umsetzungsschirtte

1. Implementiere einen gerichteten azyklischen Build-Graph mit typisierten Ein-/Ausgaben. Arbeitsphasen sind Profilbildung, Maskenprüfung, Farbkorrektur, Frame-Auswahl, Zuschnitt, Grafikableitung, Vorschau, Tests und Paketbildung.

2. Berechne deterministische Input-Fingerprints aus Quelldigests, benötigten Masken, Profilinhalten, Timing, Algorithmus-/Tool-Versionen und relevanten Parametern. Zeitstempel, Canvas-Position und Anzeigenamen dürfen reine Pixelaufträge nciht unnötig invalidieren.

3. Speichere Ergebnisdigests getrennt vom Input-Fingerprint. Gleiche Eingaben sind kein Beweis gleicher Ausgaben; prüfe Cache-Datein gegen ihre vollständigen Ergebnislisten und Prüfsummen.

4. Implementiere Plan/Dry-run mit Anzahl neuer, wiederverwendeter, veralteter, blockierter und nciht erforderlicher Varianten. Ein Dry-run schreibt keine Asset-, Build- oder Godot-Datein.

5. Führe transitive Invalidierung ein. Eine geänderte Referenzpalette betrifft alle abhängigen Posen; eine Maskenänderung einer Zielpose nur deren Farb- und Folgeergebnisse, außer sie gehört selbst zur Masterprofilbildung.

6. Wiederaufnahme erfolgt nur über verifizierte vollständige Zwischenergebnisse. Teilordner aus abgebrochenen FramReduce-Läufen dürfen niemals als fertiger Cache gelten.

7. Historische Builds bleiben unverändert. Neue Anforderugnen erzeugen neue Entwurfspläne; bestehende Freigaben behalten ihren exakten Bezug.

## Erwartete Ergebnisse

- `application/build_planner.py`
- `pipelines/fingerprints.py`
- `Cache-/Invalidierungstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Eine Maskenänderung an walk erzeugt keinen unnötigen Neubau eines unabhängigen Tempelpakets.
- [ ] Geänderte Mastermasken invalidieren die Materialpalette und sämtliche davon abhängigen Zielposen.
- [ ] Ein umbenanntes Kapitel erzeugt keine Pixel-Neuberechnung.
- [ ] Beschädigte Cache-Datein und fehlende Reports verhindern Wiederverwendung.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Plan und tatsächliche Ausführung lassen sich vergleichen.
- [ ] Cache-Treffer sind inhaltlich verifiziert.
- [ ] Ungültige Graphzyklen werden abgelehnt.
- [ ] Abhängigkeiten sind unabhängig vom visuellen Canvas.

## Nicht Bestandteil dieser Aufgabe

Keine verteilte Buildfarm und kein automatisches Löschen alter Builds.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)
- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T018.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T019 — Freie Masterreferenzen und variable Richtungssets unterstützen](../019-masterreferenzen-und-profilversionen/p.md). Nicht automatsich starten.
