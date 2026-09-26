---
task_id: T027
phase: D
status: not_started
depends_on: ["T019", "T020", "T023", "T024", "T026"]
requirements: ["R12", "R14", "R16", "R36"]
---
# T027 — Exakte Farbprüfung und optionale Material-Nachzuordnung implementieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** D — Varianten, Texturen und Sichtprüfung  
**Abhängigkeiten:** [T019](../019-masterreferenzen-und-profilversionen/p.md), [T020](../020-materialmasken-und-quellbindung/p.md), [T023](../023-farbkorrektur-pipeline/p.md), [T024](../024-frameableitung-und-geometrie/p.md), [T026](../026-grafikstufen-spritesheets/p.md)  
**Anforderungsbezug:** R12, R14, R16, R36

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Mache klar prüfbar, welche Farbgarantie ein Build tatsächlich erfüllt, und unterstütze bei Bedarf exakte Materialfarben nach der Skalierung.

## Kontext und Bestandsgrenzen

Comic-Glättung kann Mischfarben erzeugen. Der vorhandene Resolution-Weg liest keine Materialmasken. Daher ist eine durchgängige Materialgarantie eine neue Verarbeitung, nciht ein zusätzliches grünes Häkchen.

## Umsetzungsschirtte

1. Definiere zwei explizite Farbpolitiken: match_master_then_scale und exact_material_after_scale. Dokumentiere ihre Unterschiede; bestehende Ergebnisse behalten ihre ursprüngliche Politik.

2. Implementiere für fixed einen kompatiblen, dokumentierten finalen Palettenabgleich ohne ein Materialprofil als anderes Format zu tarnen. Erhalte sRGB-, Alpha- und Timing-Verträge.

3. Für material leite Labelmasken mit denselben Frame-Indizes, Zuschnitten und geometrischen Transformationen wie die Bilder ab. Kategorien dürfen nciht durch bilineare oder Lanczos-Interpolation neue IDs erhalten.

4. Lege eine deterministische Regel für Materialgrenzen fest, etwa diskrete Deckungszuordnung mit dokumentierter Gleichstandsregel. Sichtbare Ausgabepixel ohne belastbares Materiallabel werden als Fehler beziehungsweise zu prüfender Entwurf markiert, nciht still eingefärbt.

5. Binde abgeleitete Masken an die konkreten skalierten Bilder und speichere die Transformationsherkunft. Verwende hierfür einen ausdrücklichen neuen Verarbeitungsweg; umgehe nciht die Ablehnung beriets korrigierter Quellen im Legacy-Color-CLI.

6. Erzeuge bei geforderter exakter Runtime-Palette separate Spielausgaben der Masterpose. Unveränderte Referenzkopien bleiben im Referenzbereich und werden von der Runtime-Farbgarantie getrennt.

7. Prüfe jeden sichtbaren Ausgabe-RGB-Wert gegen die erlaubte Palette beziehungsweise Materialfarbreihe und zeige technische Zugehörigkeit getrennt von menschlich bestätigter Materialsemantik.

## Erwartete Ergebnisse

- `pipelines/final_color_policy.py`
- `Abgeleitete Maskenverträge`
- `Material-Endprüfungen`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein geglätteter Comic-Rand fällt bei strenger Prüffung auf, wenn sein RGB nciht in der erlaubten Palette liegt.
- [ ] Labels bleiben ganze gültige IDs; unbekannte Grenzpixel führen zu einem Befund.
- [ ] Rohreferenzen bleiben bytegleich, während optionale Runtime-Referenzausgaben gesondert geprüft werden.
- [ ] Zwei gleiche Quell-RGB-Werte mit unterschiedlichen Labels können unterschiedliche Zielfarben erhalten.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Die ausgewiesene Garantie entspricht der tatsächlich ausgeführten Verarbeitung.
- [ ] Materialmasken folgen allen Geometrieschritten.
- [ ] Kein stiller Rückfall auf Soft oder globale Palette.
- [ ] Strenge und kompatible Politik sind reproduzierbar getestet.

## Nicht Bestandteil dieser Aufgabe

Keine Behauptung automatsich bewiesener künstlerischer Materialtreue und keine Glättung von Label-IDs.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)
- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q09: Masken Profilregeln Bestand](../../quellen/Q09_Masken_Profilregeln_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T027.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T028 — Statische Grafik- und Texturverarbeitung implementieren](../028-statische-texturpipeline/p.md). Nicht automatsich starten.
