---
task_id: T025
phase: D
status: not_started
depends_on: ["T013", "T018", "T024"]
requirements: ["R13", "R15"]
---
# T025 — Timing-Profile und gemeinsame Animationszeit ergänzen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** D — Varianten, Texturen und Sichtprüfung  
**Abhängigkeiten:** [T013](../013-assettypen-posen-und-richtungen/p.md), [T018](../018-buildplan-cache-und-invalidation/p.md), [T024](../024-frameableitung-und-geometrie/p.md)  
**Anforderungsbezug:** R13, R15

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Trenne Frame-Anzahl, Wiedergaberate und Zyklusdauer und führe einen ausdrücklich wählbaren Modus mit erhaltener Dauer ein.

## Kontext und Bestandsgrenzen

Der Bestand exportiert Reduce-GIFs mit 8 FPS: weniger Frames bedeuten dort kürzere Zyklen. Diese Semantik darf nciht still geändert werden.

## Umsetzungsschirtte

1. Definiere TimingProfile mit legacy_fixed_fps und preserve_duration. Speichere Master-Zeitleiste, Loop-Einstellung, tatsächliche Anzeigedauern und Referenzdauer separat von Grafikprofilen.

2. Erhalte für alte Aufrufe und importierte Legacy-Builds die vorhandenen Zeiten. Neue Rezepte zeigen ihre Timingwahl ausdrücklich; übernimm keine erfundene Master-FPS aus einem Dateinamen ohne Prüffung.

3. Implementiere für gleichmäßige und ungleichmäßige Masterzeiten eine deterministische Zuordnung ausgewählter Frames zu Zeitintervallen. Die Summe der Ausgabedauern muss bei preserve_duration der Masterdauer entsprechen.

4. Ergänze optionale geschützte Schlüsselbilder. Wenn mehr Pflichtframes existieren als eine Zielstufe aufnehmen kann, wird diese Stufe blockiert statt unbemerkt ein Pflichtbild entfernt.

5. Führe optionale Animationsereignisse als Zeitpunkte auf der gemeinsamen Zeitleiste ein, nciht als feste Bildnummern. Hier werden nur Metadaten exportiert; keine Kampf-, Bewegungs- oder Interaktionslogik neu implementieren.

6. Übertrage die tatsächlichen Zeiten in Vorschau-/Exportmetadaten. GIF-Rundung, gespeicherte GIF-Frames und logische PNG-Frames bleiben unterscheidbar; die spätere Godot-Laufzeit nutzt den präzisen Timingvertrag.

7. Zeige in der GUI Framezahl, FPS beziehungsweise variable Dauern, Zyklusdauer und Modus. Ein Vorschau-FPS-Regler verändert keine gespeicherten Assetdaten.

## Erwartete Ergebnisse

- `domain/timing.py`
- `pipelines/timeline.py`
- `Timing-GUI und Dauertests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Legacy-Fram8 bei 8 FPS bleibt 1 Sekunde lang.
- [ ] Eine 2-Sekunden-Mastersequenz bleibt mit preserve_duration bei 8 und 16 Frames jeweils 2 Sekunden lang.
- [ ] Ungleich lange Masterframes ergeben positive Ausgabedauern mit korrekter Summe.
- [ ] Ein Ereignis bei 750 ms bleibt in allen Frame-Stufen bei 750 ms; zu viele Pflichtframes melden einen Konflikt.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Legacy-Verhalten bleibt erhalten.
- [ ] Timing ist explizit versioniert.
- [ ] Vorschau und Laufzeitmetadaten stimmen im gewählten Modus überein.
- [ ] Schlüsselbildkonflikte werden nciht versteckt.

## Nicht Bestandteil dieser Aufgabe

Keine Interpolation neuer Bilder und keine Änderung von Spiellogik.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T025.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T026 — Grafikstufen für Spritesheets integrieren](../026-grafikstufen-spritesheets/p.md). Nicht automatsich starten.
