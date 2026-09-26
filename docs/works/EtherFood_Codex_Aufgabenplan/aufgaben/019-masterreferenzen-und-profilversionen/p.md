---
task_id: T019
phase: C
status: not_started
depends_on: ["T013", "T015", "T018"]
requirements: ["R07", "R10", "R12", "R36"]
---
# T019 — Freie Masterreferenzen und variable Richtungssets unterstützen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** C — Aufträge, Farben und Frame-Verarbeitung  
**Abhängigkeiten:** [T013](../013-assettypen-posen-und-richtungen/p.md), [T015](../015-quellen-und-spritesheet-import/p.md), [T018](../018-buildplan-cache-und-invalidation/p.md)  
**Anforderungsbezug:** R07, R10, R12, R36

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Erweitere die Farbprofilbildung so, dass sie zu jedem Asset und seiner tatsächlichen Richtungsmenge passt.

## Kontext und Bestandsgrenzen

Der vorhandene Code erwartet nciht nur im Dialog, sondern auch in reference_files und validate_references acht Stand-Richtugnen. Bestehende Profilformate dürfen nciht still umdefiniert werden.

## Umsetzungsschirtte

1. Untersuche alle Richtungsvoraussetzungen in PyImgColorMatch, PyImgColorPipeline, PyImgFixedColors sowie den Vergleichsansichten. Erstelle gezielte Bestandstests für den unveränderten Acht-Richtungs-Fall.

2. Führe eine explizite ReferenceSelection mit einem oder mehreren referenzierten Quellenständen ein. Speichere Pose, Richtung, Raster, Frames, Quellenhash und eine nachvollziehbare Gewichtungsregel.

3. Für neue Profile implementiere eine neue Schema-/Formatversion mit ausgewählter Referenzmenge. Alte Version-1-Profile bleiben unverändert lesbar und behalten ihren Acht-Richtungs-Vertrag; keine fehlenden Richtugnen fiktiv ergänzen.

4. Entkopple benötigte Asset-Richtugnen von vorhandenen Masterreferenzrichtungen. Ein ausgewählter Master kann eine gemeinsame Palette liefern; die Vorschau zeigt nur tatsächlich verfügbare Referenzen und kennzeichnet eine explizite Anzeigezuordnung.

5. Erhalte für Greenhero die bestehende Vorlage mit allen acht Stand-Sheets und ihren Frames. Bei anderer Auswahl prüfe, dass alle geforderten Materialien tatsächlich in gelabelten Referenzpixeln vorkommen.

6. Implementiere Loader, Exporter, Matcher und CLI-/Adapterübergabe für neue Profile zusammen. Ein GUI-Feld allein reicht nciht. Gemischte Raster werden ausdrücklich unterstützt oder vor Ausgabe mit einer verständlichen Meldung abgelehnt.

7. Versioniere Referenzänderungen und lasse T018 alle abhängigen Resultate invalidieren. Dokumentiere die neue API getrennt vom alten CLI-Vertrag.

## Erwartete Ergebnisse

- `Neue Profilschemas und Loader`
- `Gezielte Erweiterungen in PiplineToos`
- `Referenzwahl-Anwendungsdienst und Kompatibilitätstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein bestehendes v1-Profil liefert dieselben Ergebnisse wie vor der Erweiterung.
- [ ] Ein NPC mit 2 Richtugnen kann ein neues gültiges Profil mit tatsächlich gewählter Referenzmenge erstellen.
- [ ] Eine unbekannte Profilversion wird verständlich zurückgewiesen.
- [ ] Ein Material ohne gelabelte Referenzpixel wird nciht mit erfundenen Farben ergänzt.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Acht Richtugnen sind kein globaler Zwang mehr im neuen Vertragsweg.
- [ ] Alte Profile und Aufrufe bleiben kompatibel.
- [ ] Ausgewählte Quellen sind per Hash gebunden.
- [ ] Profilbildung und Vorschau verwenden dieselbe Referenzdefinition.

## Nicht Bestandteil dieser Aufgabe

Keine stillschweigende Lockerung alter Schema-Versionen, keine künstlichen Richtungsduplikate.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q08: Referenzauswahl Bestand](../../quellen/Q08_Referenzauswahl_Bestand.md)
- [Q09: Masken Profilregeln Bestand](../../quellen/Q09_Masken_Profilregeln_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T019.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T020 — Materialdefinitionen, Maskenrevisionen und Validierung bauen](../020-materialmasken-und-quellbindung/p.md). Nicht automatsich starten.
