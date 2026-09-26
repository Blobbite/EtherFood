---
task_id: T020
phase: C
status: not_started
depends_on: ["T005", "T013", "T015", "T019"]
requirements: ["R11"]
---
# T020 — Materialdefinitionen, Maskenrevisionen und Validierung bauen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** C — Aufträge, Farben und Frame-Verarbeitung  
**Abhängigkeiten:** [T005](../005-pfade-und-objektspeicher/p.md), [T013](../013-assettypen-posen-und-richtungen/p.md), [T015](../015-quellen-und-spritesheet-import/p.md), [T019](../019-masterreferenzen-und-profilversionen/p.md)  
**Anforderungsbezug:** R11

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Speichere Materialmasken als überprüfbare, an konkrete Quellen gebundene Entwürfe und bestätigte Revisionen.

## Kontext und Bestandsgrenzen

Die vorhandenen Labelmasken sind 8-Bit-PNGs in L oder P. ID 0 ist Hintergrund, IDs 1..255 sind Materialien. Unbeschriftete Vorlagen sind kein fertiges Maskenergebnis.

## Umsetzungsschirtte

1. Übernimm Materialdefinitionen und echte Labelmasken aus dem bestehenden Farbvertrag. Unterscheide Label-IDs, Vorschaufarben und finale Materialfarbreihen.

2. Implementiere MaskRevision mit SourceRevision/Quelldigest, Raster, Materialdefinitionsrevision, Maskendigest, Erzeugungsmethode und getrenntem technischem/visuellem Status.

3. Prüfe alle sichtbaren Quellpixel, Hintergrund-ID, bekannte IDs, Bildgröße, Framepositionen und PNG-Metadaten pyimg_mask_version, pyimg_grid und pyimg_source_sha256. Nutze den vorhandenen Validator, wo er passt.

4. Erlaube unvollständige Entwürfe als Arbeitsstände, aber nciht als freigegebene Materialeingabe. Unbekannte Bereiche werden separat gespeichert oder als ungültige sichtbare ID-0-Bereiche dargestellt; keine gültige Material-ID heimlich als Unknown reservieren.

5. Erstelle Fehlerbefunde mit Pose, Richtung, Frame und Pixelbereich. Quelländerung markiert die Maskenbindung als veraltet; aktualisiere nciht nur den Quellhash, um die Prüffung zu umgehen.

6. Erhalte alte Masken beim Import und bei Änderungen als Revisionen. Eine Bestätigung gilt für den konkreten Maskeninhalt und die Quellenbindung.

7. Führe die vorhandenen Greenhero-Masken bei Migration als vorgeschlagen/visuell offen, sofern keine nachweisbare spätere Abnahme vorliegt.

## Erwartete Ergebnisse

- `domain/materials.py`
- `application/mask_service.py`
- `Maskenvalidierungs- und Herkunftstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Unmarkierte Vorlagen sind speicherbare Entwürfe, aber keine gültige Materialfreigabe.
- [ ] Gleiche RGB-Farbe mit zwei unterschiedlichen Material-IDs bleibt unterscheidbar.
- [ ] Ein veralteter Quellhash verhindert automatische Weiterverwendung.
- [ ] P-PNGs verwenden Palettenindizes als IDs, nciht ihre Vorschau-RGB-Werte.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Masken sind eindeutig an Quellen gebunden.
- [ ] Technisch gültig und visuell bestätigt sind getrennt.
- [ ] Fehler sind mit konkreter Bildfundstelle darstellbar.
- [ ] Vorlagen und bestätigte Revisionen können nciht verwechselt werden.

## Nicht Bestandteil dieser Aufgabe

Keine automatische semantische Materialerkennung in dieser Aufgabe und keine Änderung der Originalbilder.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q05: SourceColor Bestand](../../quellen/Q05_SourceColor_Bestand.md)
- [Q09: Masken Profilregeln Bestand](../../quellen/Q09_Masken_Profilregeln_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T020.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T021 — Maskeneditor mit Materialauswahl und Sichtabnahme integrieren](../021-maskeneditor-und-materialauswahl/p.md). Nicht automatsich starten.
