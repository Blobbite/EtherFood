---
task_id: T023
phase: C
status: not_started
depends_on: ["T017", "T018", "T019", "T020", "T022"]
requirements: ["R08", "R10", "R12"]
---
# T023 — SourceColor und SpritesheetColor in die Build-Pipeline einbinden

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** C — Aufträge, Farben und Frame-Verarbeitung  
**Abhängigkeiten:** [T017](../017-worker-und-pipeline-adapter/p.md), [T018](../018-buildplan-cache-und-invalidation/p.md), [T019](../019-masterreferenzen-und-profilversionen/p.md), [T020](../020-materialmasken-und-quellbindung/p.md), [T022](../022-automatische-maskenvorschlaege/p.md)  
**Anforderungsbezug:** R08, R10, R12

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Führe die vorhandene Farbkorrektur aus den bestätigten Quellen, Profilen und Masken automatsich in isolierten Arbeitsbereichen aus.

## Kontext und Bestandsgrenzen

Der Bestand hat soft, fixed und material. Materialvorbereitung, Profilexport und Farbauftrag sind getrennte CLI-Vorgänge mit unterschiedlichen zulässigen Argumenten.

## Umsetzungsschirtte

1. Implementiere Adapter für SourceColor und SpritesheetColor mit einer passenden Optionstabelle. Nur tatsächlich unterstützte Argumente übergeben; Color hat im Bestand keine --fps- oder --no-html-Option.

2. Baue den Auftrag aus eingefrorenen Source-, Reference-, Mask- und ProfileRevisionen. SourceColor verarbeitet einzelne Bilder und wird nur bei ausdrücklich aktiviertem Einzelbild-Farbschritt genutzt, nciht als Animationserzeuger.

3. Exportiere feste Palette oder Materialprofil aus der gewählten Referenz und den erforderlichen bestätigten Mastermasken. Nutze den neuen Vertragsweg aus T019 für variable Referenzmengen und den alten Weg unverändert für kompatible Bestandsprofile.

4. Erstelle getrennte Eingabe- und Ausgabeordner, die die Schutzregeln der Farb-CLI erfüllen. Farboutputs dürfen nciht als unmarkierte Originalquellen für einen weiteren Farbauftrag entdeckt werden.

5. Führe Vorprüfung und anschliesend Verarbeitung aus; lies color-build.json und prüfe erwartete PNGs, Quell-/Profil-/Masken-Hashes und relevante Pixel-/Alpha-Verträge.

6. Kennzeichne bytegleich kopierte Masterreferenzen als Referenzkopien. Sie sind nciht automatsich palette-reduzierte Spielgrafiken. Eine zusätzliche korrigierte Runtime-Ausgabe der Masterpose braucht eine eigene explizite Regel.

7. Übergebe nur vollständige Ergebnisse an die Frame-/Grafik-Folgephasen. Bei Fehlern bleiben alte Builds und Quellen erhalten; kein heimlicher Rückfall von material auf soft.

## Erwartete Ergebnisse

- `pipelines/color_adapter.py`
- `Profil-/Masken-Buildintegration`
- `Farbadapter-Integrationstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] soft, fixed und material haben eigene zulässige Parameter und Fehlerfälle.
- [ ] Falsche Maskengröße oder Quellbindung verhindert Ausgabe vor der eigentlichen Verarbeitung.
- [ ] Referenzkopien werden nciht als exakt reduzierte Materialausgabe ausgegeben.
- [ ] Ein identischer Auftrag kann verifiziert wiederverwendet werden; ein geändertes Profil erzeugt einen neuen Build.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Bestehender Farbkern wird wiederverwendet.
- [ ] Alle Eingaben sind im Bericht nachvollziehbar.
- [ ] Einzelbilder bleiben Einzelbilder.
- [ ] Ergebnisprüfung ist unabhängig vom Konsolentext.

## Nicht Bestandteil dieser Aufgabe

Keine neue Farbalgorithmus-Neuschreibung ohne notwendigen Vertragsgrund und keine Änderungen an Originalen.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q05: SourceColor Bestand](../../quellen/Q05_SourceColor_Bestand.md)
- [Q08: Referenzauswahl Bestand](../../quellen/Q08_Referenzauswahl_Bestand.md)
- [Q09: Masken Profilregeln Bestand](../../quellen/Q09_Masken_Profilregeln_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T023.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T024 — Frame-Abstufungen, Raster und Anker sicher ableiten](../024-frameableitung-und-geometrie/p.md). Nicht automatsich starten.
