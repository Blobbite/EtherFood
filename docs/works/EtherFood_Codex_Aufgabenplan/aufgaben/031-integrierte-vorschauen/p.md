---
task_id: T031
phase: D
status: not_started
depends_on: ["T009", "T016", "T026", "T027", "T028", "T030"]
requirements: ["R07", "R15", "R17"]
---
# T031 — HTML-Vergleiche im Asset-Menü sicher wiederverwenden

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** D — Varianten, Texturen und Sichtprüfung  
**Abhängigkeiten:** [T009](../009-gui-und-projektstart/p.md), [T016](../016-asset-anlage-und-held-menue/p.md), [T026](../026-grafikstufen-spritesheets/p.md), [T027](../027-materialfarben-nach-skalierung/p.md), [T028](../028-statische-texturpipeline/p.md), [T030](../030-pipeline-bedienung-im-dashboard/p.md)  
**Anforderungsbezug:** R07, R15, R17

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Zeige die vorhandenen Farb-, Auflösungs- und Positionsvergleiche im selben Dashboard und verknüpfe sie mit konkreten Builds.

## Kontext und Bestandsgrenzen

Die bestehenden HTML-Seiten laden PNGs/GIFs über relative Pfade. Sie sind wiederverwendbar, aber kein Ersatz für Buildidentität oder Freigabelogik.

## Umsetzungsschirtte

1. Integriere QWebEngineView für ausschließlich freigegebene lokale Vorschauinhalte. Nutze einen eingeschränkten Preview-Root oder kontrollierten URL-Resolver; ein einfach geladenes file:// ist keine vollständige Zugriffssperre.

2. Bewahre relative Assetbeziehungen oder erzeuge neue Views über die vorhandenen Generatoren mit korrekter Wurzel. Views dürfen keine Bilddaten verändern und müssen bei fehlenden Quellen eindeutig warnen.

3. Ergänze eine kontrollierte Auswahl für Asset, Build, Pose, Richtung, Grafikstufe und Frame-Anzahl. Ein minimaler geprüfter Nachrichtenvertrag kann die HTML-Auswahl synchronisieren; keine beliebige Python-Ausführung aus JavaScript erlauben.

4. Passe fest verdrahtete Richtungslisten auf die Assetdefinition an. Nicht erforderliche Richtugnen erscheinen anders als tatsächlich fehlende erwartete Datein.

5. Zeige PNG-Synchronvorschau und Original-GIF-Darstellung getrennt. Vorschau-FPS, tatsächliches Exporttiming, logische Frames und gegebenenfalls zusammengefasste GIF-Frames sind nciht gleichzusetzen.

6. Unterstütze Master, korrigierten Build und freigegebenen Vergleichsbuild. Lade nur benötigte Bilder; verwerfe verspätete Ladeantworten nach einem Auswahlwechsel.

7. Blockiere unerwartete Netzwerkanfragen und Navigation außerhalb der kontrollierten Vorschau. Dokumentiere einen externen Browser-Fallback bei fehlendem QtWebEngine, ohne ihn als vollständigen integrierten GUI-Test auszugeben.

## Erwartete Ergebnisse

- `ui/preview/`
- `Kontrollierter Preview-Resolver`
- `QtWebEngine- und Offline-Linktests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Relative Links funktionieren auch bei umgezogenem Demo-Workspace.
- [ ] Ein alter asynchroner Ladevorgang überschreibt nciht die neue Auswahl.
- [ ] Eine Notiz oder Datei mit Script-Inhalt erhält keinen Zugriff auf Python-Aktionen.
- [ ] Statische Assets haben keine aktive Animationssteuerung.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Bestehende Vergleiche sind integriert statt neu erfunden.
- [ ] Die sichtbare Build-ID ist eindeutig.
- [ ] Vorschauen schreiben keine Bilddateien.
- [ ] QtWebEngine-Integration wird gesondert getestet, nciht nur in Chromium.

## Nicht Bestandteil dieser Aufgabe

Keine Einbettung aller Bilder als Base64 und kein vollständiger neuer Animationseditor.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)
- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q05: SourceColor Bestand](../../quellen/Q05_SourceColor_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T031.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T032 — Variantenmatrix, Prüfcheckliste und Sichtbefunde implementieren](../032-variantenpruefung-und-fehlerkarten/p.md). Nicht automatsich starten.
