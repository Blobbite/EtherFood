---
task_id: T026
phase: D
status: not_started
depends_on: ["T018", "T023", "T024", "T025"]
requirements: ["R14", "R16", "R22"]
---
# T026 — Grafikstufen für Spritesheets integrieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** D — Varianten, Texturen und Sichtprüfung  
**Abhängigkeiten:** [T018](../018-buildplan-cache-und-invalidation/p.md), [T023](../023-farbkorrektur-pipeline/p.md), [T024](../024-frameableitung-und-geometrie/p.md), [T025](../025-timing-und-animationsevents/p.md)  
**Anforderungsbezug:** R14, R16, R22

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Erzeuge und verwalte alle fünf Grafikstufen, ohne Raster, Zeitleiste oder Anker zu verlieren.

## Kontext und Bestandsgrenzen

Die vorhandenen Stufen heißen comic_high, comic_mid, comic_low, pixel_high und pixel_low. Die vier kleineren Stufen werden über bestehende Worker erzeugt.

## Umsetzungsschirtte

1. Implementiere den Resolution-Adapter für die tatsächlich vorhandenen Starter und deren Optionen. Bewahre die Profilnamen und Legacy-Voreinstellungen; neue Projektprofile werden ausdrücklich versioniert.

2. Leite Comic Mid/Low und Pixel High aus der vorgesehenen korrigierten HD-Quelle ab. Erhalte die bestehende Pixel-Low-Regel, sofern das gewählte Rezept nichts anderes ausdrücklich vorgibt.

3. Übergebe die erforderlichen Frameordner sowie korrekte Raster. Stelle vorher sicher, dass der gewünschte 16-Frame-Zweig vorhanden ist; archive/PixelEng wird nciht versehentlich als optimiertes Ziel interpretiert.

4. Transportiere Geometrieabbildung, Anker und Timing zu jeder Ausgabe. Framezellen dürfen beim Filtern nciht mit Nachbarzellen vermischt werden.

5. Behandle pyimg-reference-colors, pyimg-fixed-palette und pyimg-material-colors als unterschiedliche Formate. Nutze vorhandene --palette-profile-Unterstützung nur bei kompatiblem Format; weitere Fälle gehören zu T027.

6. Erfasse tatsächliche Bildmaße, Raster, Dateigrößen, Alpha-Politik und erwartete Ausgabezahl je VariantKey. Ein bestehendes PNG mit plausiblen Maßen allein ist kein gültiger Cache.

7. Erzeuge Vorschauen aus den finalen PNGs und speichere ihre Abhängigkeiten. Prüfe richtige relative Links bei separater Ausgabe.

## Erwartete Ergebnisse

- `pipelines/resolution_adapter.py`
- `Grafikprofil-Verwaltung`
- `Raster-/Alpha-/Anker-Integrationstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Alle fünf Grafikstufen erscheinen in der Variantenmatrix; comic_high ist die gewählte Runtime-HD-Ausgabe, nciht still das rohe Original.
- [ ] Raster, Framefolge und Zeitleiste bleiben über alle Grafikstufen erhalten.
- [ ] Teiltransparenz wird entsprechend dem gewählten Comic-/Pixel-Vertrag behandelt.
- [ ] Ein inkompatibles Materialprofil wird nciht an --palette-profile weitergereicht.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Bestehende Skalierungsworker werden wiederverwendet.
- [ ] Output-Hashes und Geometrie sind je Variante gespeichert.
- [ ] Profiländerung invalidiert nur betroffene Zweige.
- [ ] Fehlende oder beschädigte Ausgaben sind keine bestandenen Varianten.

## Nicht Bestandteil dieser Aufgabe

Keine unbemerkte Änderung der Pixel-Low-Palette und keine pauschale Aussage, alle skalierten Farben seien exakt materialtreu.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)
- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T026.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T027 — Exakte Farbprüfung und optionale Material-Nachzuordnung implementieren](../027-materialfarben-nach-skalierung/p.md). Nicht automatsich starten.
