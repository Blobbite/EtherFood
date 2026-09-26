---
task_id: T042
phase: F
status: not_started
depends_on: ["T007", "T012", "T029", "T033", "T037", "T038", "T041"]
requirements: ["R05", "R31"]
---
# T042 — Projekt- und Asset-Dokumentation automatsich erzeugen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** F — Betrieb und Gesamtprüfung  
**Abhängigkeiten:** [T007](../007-dokumente-notizen-und-aufgaben/p.md), [T012](../012-dokumentations-und-aufgaben-gui/p.md), [T029](../029-assetpakete-und-tempel/p.md), [T033](../033-kandidaten-und-versionsarchiv/p.md), [T037](../037-godot-tests-und-abnahmeszene/p.md), [T038](../038-freigabe-und-pruefbindungen/p.md), [T041](../041-versionsvergleich-und-projektfortschritt/p.md)  
**Anforderungsbezug:** R05, R31

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Erzeuge lesbare Dokumentation aus der aktuellen Projektstruktur und den verifizierten technischen Ergebnissen.

## Kontext und Bestandsgrenzen

Manueller Inhalt und automatsich erzeugte Berichte bleiben getrennt. Die Dokumentation soll im Dashboard sichtbar und als Paket exportierbar sein.

## Umsetzungsschirtte

1. Implementiere Dokumentgeneratoren für Projekt, Akt, Kapitel, Asset, Paket und Freigabe. Übernimm Beschreibungen, Anforderugnen, Beziehungen, Quellenherkunft, Profilwahl, Buildzahlen und tatsächlich vorhandene Prüfnachweise.

2. Nutze einen festgehaltenen Katalog-/Versionsstand für jeden Export. Ändert sich das Projekt während der Erstellung, darf kein gemischter Bericht mit alten Überschriften und neuen Freigaben entstehen.

3. Erzeuge Markdown und eine lokal lesbare HTML-Ansicht mit relativen Links. Die Original-Benutzerdokumente bleiben unberührt; technische Abschnitte sind als generiert gekennzeichnet.

4. Verknüpfe bestehende GIF-/Farb-/Positionsvergleiche statt unnötig alle Frames erneut als Bilder zu exportieren. Dokumentiere fehlende Vorschauen und deren Grund.

5. Erstelle eine technische Versionskarte mit den exakten Kandidat-, Export-, Freigabe- und Deployment-IDs. Historische Testergebnisse dürfen nur als historische Ergebnisse erscheinen.

6. Ergänze einen portablen Dokumentations-ZIP-Export mit Dateiliste und Prüfsummen. Optional eingebettete Bilder/Anhänge werden ausdrücklich ausgewählt; Quellen und private Maschinenpfade werden nciht ungefragt veröffentlicht.

7. Stelle den Dokumentationsstand im Dashboard dar und biete bewusstes Neuerzeugen an. Eine Dokumentänderung invalidiert keine Pixel-Builds, solange sie keine relevanten Verarbeitungsanforderungen ändert.

## Erwartete Ergebnisse

- `application/document_export.py`
- `HTML-/Markdown-Vorlagen`
- `Portabilitäts- und Snapshot-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Eine neue Berichtserstellung überschreibt keine manuelle Aktbeschreibung.
- [ ] Exportierte HTML-Links funktionieren nach Entpacken an einem anderen Ort.
- [ ] Ein nciht ausgeführter Godot-Test steht nciht als bestanden im Bericht.
- [ ] Ein während des Exports geändertes Projekt führt zu einem konsistenten alten Snapshot oder kontrolliertem Neustart.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Dokumentation ist aus dem Dashboard erreichbar.
- [ ] Export ist versionsgebunden und portabel.
- [ ] Nutzertext und generierter Text sind getrennt.
- [ ] Keine unbelegten Test- oder Qualitätsbehauptungen.

## Nicht Bestandteil dieser Aufgabe

Keine PDF-/Office-Pflicht und keine automatische Story- oder Lore-Erfindung.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)
- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q07: Workspace Skizze](../../quellen/Q07_Workspace_Skizze.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T042.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T043 — Erweiterbare Kartentypen und Pipeline-Vorlagen bereitstellen](../043-erweiterbare-vorlagen-und-typen/p.md). Nicht automatsich starten.
