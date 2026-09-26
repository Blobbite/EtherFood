---
task_id: T024
phase: C
status: not_started
depends_on: ["T017", "T018", "T023"]
requirements: ["R09", "R13", "R16", "R22", "R32"]
---
# T024 — Frame-Abstufungen, Raster und Anker sicher ableiten

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** C — Aufträge, Farben und Frame-Verarbeitung  
**Abhängigkeiten:** [T017](../017-worker-und-pipeline-adapter/p.md), [T018](../018-buildplan-cache-und-invalidation/p.md), [T023](../023-farbkorrektur-pipeline/p.md)  
**Anforderungsbezug:** R09, R13, R16, R22, R32

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Erzeuge die vorhandenen Frame-Stufen aus korrigierten Ausgangsanimationen und bewahre ihre räumliche Bedeutung.

## Kontext und Bestandsgrenzen

FramReduce leitet 8/10/12/14 direkt von 16 ab. Fram16 optimiert in 4×4. Der alte gemeinsame Ablauf verschiebt Quellen nach PixelEng; deshalb darf er nur mit Arbeitskopien laufen.

## Umsetzungsschirtte

1. Implementiere den Fram16-/FramReduce-Adapter gegen die ermittelten realen Starter. Verwende je Auftrag neue Arbeitsbereiche und ausschließlich kopierte korrigierte Master-Sheets.

2. Erzeuge den vollständigen 16-Frame-Zweig und die gewählten Ableitungen 14/12/10/8 direkt aus derselben Mastersequenz. Keine Kaskade 16→14→12, da sich sonst Auswahl und Herkunft verändern.

3. Erhalte die dokumentierte Indexregel für den Legacy-Modus. Notiere source_frame_indices, Originalraster, Zielraster und jeden Zuschnitt im standardisierten BuildResult.

4. Führe eine Geometrieabbildung von Originalframe zu zugeschnittenem und skaliertem Frame ein. Ankerpunkte werden durch exakt denselben Offset/Skalierungsvertrag transformiert; unterschiedliche Zuschnitte zwischen Varianten dürfen keine sichtbaren Sprünge verursachen.

5. Wenn Materialmasken weiterverarbeitet werden, wähle und packe exakt dieselben Maskenframes. Masken-Metadaten für abgeleitete Bilder benötigen eine verifizierte Transformationsherkunft, nciht einen ungeprüft ersetzten Quellhash.

6. Behalte eigenständige 8/10/12/14-Originalvarianten getrennt. Konflikte mit gewünschten Ableitungen müssen im Plan sichtbar werden und dürfen nciht automatsich überschrieben werden.

7. Prüfe die vollständige erwartete Dateimenge, Pixel-/Framefolge, HTML-Links und Reports. Ein belegter oder übersprungener Variantenordner ist kein ausreichender Erfolgsnachweis.

## Erwartete Ergebnisse

- `pipelines/frame_adapter.py`
- `domain/frame_geometry.py`
- `Frame-/Anker-/Unvollständigkeits-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] 16→8/10/12/14 verwendet die erwarteten Indizes direkt aus Fram16.
- [ ] Leere und identische Frames werden gemäß Vertrag erhalten; eine komplett transparente Auswahl meldet Fehler.
- [ ] Ein synthetischer Fußanker bleibt nach unterschiedlichem Zuschnitt am selben logischen Ort.
- [ ] Ein abgebrochener, teilweise belegter Ordner wird beim nächsten Lauf nciht als fertig akzeptiert.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Alle gewünschten Frame-Stufen einschließlich 16 sind verwaltet.
- [ ] Quellen und unabhängige Originalvarianten bleiben unangetastet.
- [ ] Geometrie- und Maskentransformationen sind nachvollziehbar.
- [ ] Legacy-Raster und Auswahl bleiben kompatibel.

## Nicht Bestandteil dieser Aufgabe

Keine Neugenerierung von Bewegung und keine Veränderung der Wiedergabedauer ohne ausdrückliches Timing-Profil.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q06: Gemeinsame Schreibregeln](../../quellen/Q06_Gemeinsame_Schreibregeln.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T024.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T025 — Timing-Profile und gemeinsame Animationszeit ergänzen](../025-timing-und-animationsevents/p.md). Nicht automatsich starten.
