---
task_id: T014
phase: B
status: not_started
depends_on: ["T005", "T009", "T013"]
requirements: ["R22", "R32"]
---
# T014 — Vorhandenen Asset-Bestand lesend erfassen und zuordnen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** B — Dashboard und Asset-Anlage  
**Abhängigkeiten:** [T005](../005-pfade-und-objektspeicher/p.md), [T009](../009-gui-und-projektstart/p.md), [T013](../013-assettypen-posen-und-richtungen/p.md)  
**Anforderungsbezug:** R22, R32

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Mache Greenhero und andere vorhandene Bestände im Dashboard sichtbar, ohne ihre Ablage zu verändern.

## Kontext und Bestandsgrenzen

Die hochgeladene Baumstruktur nennt viele Varianten, Berichte und Vergleichsseiten. Ordnerexistenz oder historische Prüflogs belegen weder Vollständigkeit noch Freigabe.

## Umsetzungsschirtte

1. Implementiere einen explizit gestarteten Scanner für ausgewählte Wurzeln. Erkenne bekannte Posen-, Grafik- und Frameordner sowie Berichte und HTML-Vergleiche. Folge keinen Verzeichnislinks.

2. Ordne gefundene Datein anhand Metadaten, Raster und Dateinamen als Vorschläge zu. Zeige Konflikte, unbekannte Namen, doppelte Richtugnen und unklare Herkunft in einer Importprüfung.

3. Validiere PNG-Header und Raster in begrenzten Arbeitsaufträgen. Ein Dateibaum allein darf keine bestandenen Pixelprüfungen erzeugen.

4. Lies build-info.json, pruefung.json und color-build.json als externe Nachweise. Prüfe ihren Bezug zu tatsächlichen Quellen-/Ergebnis-Hashes, bevor sie einem historischen Build zugeordnet werden.

5. Zeige erkannte Vergleichsseiten als lesende Links. Eine kaputte relative Verknüpfung wird als solche gemeldet; der Scanner repariert sie nciht automatsich.

6. Nach bewusster Übernahme werden Katalogeinträge und Herkunftsverweise erstellt. Der Ursprungsbestand bleibt unangetastet. Spätere verwaltete Bearbeitung benötigt einen separaten Import/Snapshot.

7. Erstelle einen Importbericht mit übernommenen, ausgelassenen und manuell zu klärenden Elementen.

## Erwartete Ergebnisse

- `application/inventory_service.py`
- `ui/import_review.py`
- `Bestands-Fixtures und Importtests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein teilweise belegter Fram8-Ordner erscheint als unvollständig, nciht als bestanden.
- [ ] Ein alter Prüfbericht mit falschem Quellhash wird nciht als aktuelle Freigabe importiert.
- [ ] Ein unbekannter PixelEng-Bestand bleibt Herkunft unklar.
- [ ] Ein erneuter Scan erzeugt keine Dubletten und ändert keine Originaldatei.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Der Bestand kann lesend angezeigt werden.
- [ ] Konflikte sind sichtbar und nciht automatsich entschieden.
- [ ] Historische Reports sind von aktuellen Checks getrennt.
- [ ] Vorher-/Nachher-Hashes des Quellbestands stimmen überein.

## Nicht Bestandteil dieser Aufgabe

Keine Verschiebung in die neue Struktur und keine automatische Freigabe alter Assets.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)
- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q07: Workspace Skizze](../../quellen/Q07_Workspace_Skizze.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T014.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T015 — Quellbilder und externe Animationslieferungen importieren](../015-quellen-und-spritesheet-import/p.md). Nicht automatsich starten.
