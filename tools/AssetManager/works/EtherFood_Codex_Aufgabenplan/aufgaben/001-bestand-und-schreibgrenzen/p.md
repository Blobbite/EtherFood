---
task_id: T001
phase: A
status: not_started
depends_on: []
requirements: ["R19", "R32", "R36"]
---
# T001 — Bestand aufnehmen und Schreibgrenzen festlegen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** A — Grundlagen und Verwaltungskern  
**Abhängigkeiten:** Keine. Dies ist der Startpunkt.  
**Anforderungsbezug:** R19, R32, R36

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Ermittle den tatsächlichen Projektzustand und lege überprüfbare Grenzen für alle späteren Änderungen fest.

## Kontext und Bestandsgrenzen

Die Uploads zeigen PyGameTools-Pipelines und eine Workspace/AssetVersions/Godot-Skizze, aber keinen vollständig verfügbaren Repository-Checkout. Der Dump nennt PyGameTools unter EtherFood_AssetVersions/tools; das beweist weder eine eigene Git-Grenze noch den späteren Installationspfad.

## Umsetzungsschirtte

1. Lies zuerst die lokalen Repository-Anweisungen. Erfasse Git-Wurzeln, Branch, vorhandene Änderungen, Python-Umgebung, Godot-Projektdatei und ausführbare Tools ausschließlich lesend. Vorhandene Nutzeränderungen weder zurücksetzen noch als eigene Änderungen übernehmen.

2. Finde PyGameTools.py, Pipline/PiplineToos, sämtliche Starter und deren Tests anhand tatsächlicher Dateinamen. Der Dump verwendet teilweise nummerierte Ordner, seine README-Aufrufe teilweise unnummerierte Pfade; speichere eine explizite Zuordnung statt Pfade zu erraten.

3. Erfasse die drei Datenbereiche EtherFood_Workspace, EtherFood_AssetVersions und EtherFood. Unterscheide darin Tool-Code, bearbeitbare Quellen, veränderliche Arbeitsdaten, eingefrorene Kandidaten und Spielinhalte. Scanne nur ausdrücklich bekannte Wurzeln.

4. Führe vorhandene Tests nur in isolierten Testverzeichnissen aus. Erfasse genaue Befehle, Exit-Codes und fehlende Abhängigkeiten. Historische Angaben wie 160 bestandene Tests sind keine aktuelle Testausführung.

5. Erstelle docs/asset-studio/BASELINE.md mit Pfadkarte, belegten Fähigkeiten, fehlenden Komponenten und SHA-256 der herangezogenen Uploads oder lokalen Quellen. Führe insbesondere feste acht Referenzrichtungen, leere Maskenvorlagen, feste Reduce-GIF-FPS und den reservierten Texturmodus auf.

6. Lege einen Test-/Demo-Arbeitsbereich fest, der keine produktiven Originale enthält. Dokumentiere Werkzeug-, Workspace-, Archiv- und Godot-Aliase. Erstelle noch keine echte Asset-Migration und keine Git-Repositories.

7. Schreibe das Ergebnisprotokoll für T001. Fehlt der Checkout, dokumentiere die konkret fehlenden Pfade und markiere abhängige Ausführung als blockiert; erstelle keinen Ersatzcode aus dem zusammengefügten Dump.

## Erwartete Ergebnisse

- `docs/asset-studio/BASELINE.md`
- `docs/asset-studio/PATH_MAP.json`
- `docs/asset-studio/task-results/T001.md`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Pfadnamen mit Leerzeichen, Umlauten, # und % werden vollständig und unverändert erfasst.
- [ ] Eine fehlende Godot-Installation ergibt einen dokumentierten Blocker, keinen behaupteten erfolgreichen Godot-Test.
- [ ] Vorher-/Nachhervergleich zeigt keine Änderungen an Quellbildern, Spielassets oder fremden Git-Änderungen.
- [ ] Widersprüchliche historische Dokumentation wird als historisch eingeordnet; der aktuelle Code und seine tatsächlich ausgeführte Hilfe werden gesondert dokumentiert.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Die Pfadkarte nennt reale Wurzeln und Schreibrechte.
- [ ] Belegte Funktionen und Zielerweiterungen sind getrennt.
- [ ] Es gibt eine reproduzierbare Testbasis oder präzise Blocker.
- [ ] Keine produktiven Bilddaten wurden verschoben oder verändert.

## Nicht Bestandteil dieser Aufgabe

Keine GUI, keine Installationsänderungen am System, kein git reset/clean, keine Massenverarbeitung.

## Daten- und Rückbauschutz

Änderungen sind auf Berichte und isolierte Testdaten begrenzt. Bei unklaren Git-Grenzen bleibt jede Schreibintegration deaktiviert.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)
- [Q03: Starter Bestand](../../quellen/Q03_Starter_Bestand.md)
- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q05: SourceColor Bestand](../../quellen/Q05_SourceColor_Bestand.md)
- [Q06: Gemeinsame Schreibregeln](../../quellen/Q06_Gemeinsame_Schreibregeln.md)
- [Q07: Workspace Skizze](../../quellen/Q07_Workspace_Skizze.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T001.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T002 — Architektur und gemeinsame Datenverträge festschreiben](../002-architektur-und-vertraege/p.md). Nicht automatsich starten.
