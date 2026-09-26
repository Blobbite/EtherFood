---
task_id: T021
phase: C
status: not_started
depends_on: ["T016", "T020"]
requirements: ["R10", "R11"]
---
# T021 — Maskeneditor mit Materialauswahl und Sichtabnahme integrieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** C — Aufträge, Farben und Frame-Verarbeitung  
**Abhängigkeiten:** [T016](../016-asset-anlage-und-held-menue/p.md), [T020](../020-materialmasken-und-quellbindung/p.md)  
**Anforderungsbezug:** R10, R11

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Ermögliche das erstmalige Festlegen und spätere Korrigieren von Materialbereichen direkt im Asset-Menü.

## Kontext und Bestandsgrenzen

Der Editor ist ein spezialisierter Labelmasken-Editor, kein vollständiges Zeichen- oder Animationstool.

## Umsetzungsschirtte

1. Baue eine pixelgenaue Maskenansicht mit Quelle, Label-Overlay, Materialliste, Deckkraft und Zoom. Bei Animationen sind Pose, Richtung und Einzel-Frame explizit wählbar.

2. Implementiere Material anlegen/umbenennen und zulässige Farbstufenanzahl. Konkrete Ziel-Farbreihen werden aus der Masterauswahl abgeleitet; Materialnamen allein enthalten keine Farbdefinition.

3. Ergänze Pinsel, Rechteckauswahl, Pipette für Material-ID und begrenztes Füllwerkzeug. Werkzeuge schreiben ausschließlich ganze Label-IDs ohne Glättung oder Interpolation.

4. Implementiere Undo/Redo innerhalb der Maskenbearbeitung und Speichern als neue MaskRevision. Originalbild und alte bestätigte Masken bleiben unverändert.

5. Zeige nciht zugeordnete sichtbare Pixel und unbekannte IDs deutlich. Springe von einem Validierungsfehler zur betreffenden Frame-/Pixelposition.

6. Ergänze technische Validierung und eine separate menschliche Sichtbestätigung. Bestätigen eines Frames oder Sheets darf nciht unbesehen alle anderen Posen bestätigen.

7. Binde den Editor an die Referenzmasken, ohne eine Materialpalette vor deren erstmaliger Beschriftung zu verlangen. Erst Definition/Labels, dann Profilexport: keine zirkuläre Bedienabhängigkeit.

## Erwartete Ergebnisse

- `ui/masks/`
- `Masken-Bearbeitungsbefehle`
- `Pixelgenaue GUI-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Malen bei 400 % Zoom trifft dieselben Quellpixel wie bei 100 %.
- [ ] Undo stellt die exakten vorherigen Label-Bytes wieder her.
- [ ] Ein Framewechsel verliert keine gespeicherten Änderungen und zeigt ungespeicherte Änderungen an.
- [ ] Bestätigung eines Sheets bestätigt nciht automatsich weitere Sheets.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Masken lassen sich im Dashboard bearbeiten.
- [ ] IDs und PNG-Quellmetadaten bleiben erhalten.
- [ ] Validierungsbefunde sind direkt navigierbar.
- [ ] Speichern und Sichtbestätigung sind unterschiedliche Aktionen.

## Nicht Bestandteil dieser Aufgabe

Keine generative Grafikbearbeitung und kein automatisches Umzeichnen des Helden.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q09: Masken Profilregeln Bestand](../../quellen/Q09_Masken_Profilregeln_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T021.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T022 — Automatische Maskenvorschläge mit Unsicherheitsanzeige entwickeln](../022-automatische-maskenvorschlaege/p.md). Nicht automatsich starten.
