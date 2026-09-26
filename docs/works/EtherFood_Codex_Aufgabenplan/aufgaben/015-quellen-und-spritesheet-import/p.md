---
task_id: T015
phase: B
status: not_started
depends_on: ["T005", "T013", "T014"]
requirements: ["R08", "R09", "R19", "R20", "R32"]
---
# T015 — Quellbilder und externe Animationslieferungen importieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** B — Dashboard und Asset-Anlage  
**Abhängigkeiten:** [T005](../005-pfade-und-objektspeicher/p.md), [T013](../013-assettypen-posen-und-richtungen/p.md), [T014](../014-bestandsimport-lesend/p.md)  
**Anforderungsbezug:** R08, R09, R19, R20, R32

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Baue die sichere Schnittstelle zwischen dem externen Animationstool und dem verwalteten Asset.

## Kontext und Bestandsgrenzen

Das Dashboard erzeugt keine Originalanimationen. Einzelbilder und fertig gelieferte 16-Frame-Sheets sind unterschiedliche Quellenarten.

## Umsetzungsschirtte

1. Implementiere Auswahl oder Drag-and-drop für Source-Einzelbilder und fertige Spritesheets. Speichere Dateiname, Importzeit, Hash, Raster, Pose, Richtung und optional das verwendete externe Tool als Herkunft.

2. Biete den Importmodus 16 Frames nebeneinander mit grid=[16,1]. Vertikale Streifen [1,16] und andere tatsächlich unterstützte Raster müssen ausdrücklich auswählbar sein; ungewöhnliche Bildproportionen dürfen keine stille Rasterheuristik erzwingen.

3. Validiere Bildformat, Pixel-/Dateigrößenlimits, Framezahl, Teilbarkeit und eindeutige Zuordnung vor dem Registrieren. Keine fehlenden Richtugnen durch Duplikate auffüllen.

4. Erstelle eine unveränderliche SourceRevision aus geprüften Kopien. Ändert sich eine Quelle während des Imports, brich den betroffenen Import ab und registriere kein gemischtes Ergebnis.

5. Zeige Posen-/Richtungsmatrix mit erwartet, importiert, fehlt und nciht erforderlich. Unterstütze mehrere Lieferungen als getrennte Revisionen und bewusste Auswahl des aktiven Entwurfsstands.

6. Führe den externen Animationsschritt als waiting_external, bis die benötigten Sheets vorliegen. Optionaler Ordnerbeobachter darf nur stabile fertige Datein vorschlagen; kein automatisches Ausführen externer Programme.

7. Erhalte Source-Einzelbilder unabhängig von den Animationslieferungen. Übernimm nciht ungefragt den ersten Frame eines Sheets als gestalterische Quelle.

## Erwartete Ergebnisse

- `application/source_import.py`
- `ui/source_import_dialog.py`
- `Import- und Snapshot-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein waagerechtes 16er-Sheet wird als 16×1 und nciht 1×16 registriert.
- [ ] Doppelte Pose-/Richtungszuordnung benötigt Konfliktauflösung.
- [ ] Eine halb geschriebene oder während des Imports veränderte PNG wird nciht übernommen.
- [ ] Eine neue Lieferung macht Folgeergebnisse veraltet, ohne die alte SourceRevision zu überschreiben.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Originalanimation bleibt externe Arbeit.
- [ ] Importe sind unveränderlich versioniert.
- [ ] Unvollständige Lieferungen sind klar sichtbar.
- [ ] Richtungsmenge folgt der Asset-Konfiguration.

## Nicht Bestandteil dieser Aufgabe

Keine KI-Animationserzeugung, keine automatische Frameinterpolation und keine neuen bezahlten Dienste.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q05: SourceColor Bestand](../../quellen/Q05_SourceColor_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T015.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T016 — NPC-Anlage, Vorlagen und Held-Menü implementieren](../016-asset-anlage-und-held-menue/p.md). Nicht automatsich starten.
