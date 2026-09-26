---
task_id: T028
phase: D
status: not_started
depends_on: ["T013", "T017", "T018", "T026"]
requirements: ["R14", "R16", "R28", "R29", "R36"]
---
# T028 — Statische Grafik- und Texturverarbeitung implementieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** D — Varianten, Texturen und Sichtprüfung  
**Abhängigkeiten:** [T013](../013-assettypen-posen-und-richtungen/p.md), [T017](../017-worker-und-pipeline-adapter/p.md), [T018](../018-buildplan-cache-und-invalidation/p.md), [T026](../026-grafikstufen-spritesheets/p.md)  
**Anforderungsbezug:** R14, R16, R28, R29, R36

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Ergänze den bislang reservierten Texturweg für Böden, Decken, Säulen, Hintergründe und andere statische 2D-Inhalte.

## Kontext und Bestandsgrenzen

Der Bestand kann einzelne PNGs skalieren, aber --Textur und die vorgesehenen T-Worker sind laut Quelle noch nciht implementiert. Diese Aufgabe schließt diese Lücke ausdrücklich.

## Umsetzungsschirtte

1. Definiere TextureRecipe für statische Farbbilder mit Grafikstufen, Skalierung, Alpha-Politik, optionaler Palette, Anker, Weltmaßstab und Kachel-/Randregeln. Keine Frame- oder Animationspflicht einführen.

2. Implementiere die vorgesehenen TComicMid/TComicLow/TPixelHigh/TPixelLow-Funktionen oder gleichwertige kompatibel angebundene Module. Registriere --Textur erst dann als funktionierend, wenn Hilfe, Tests und reale Ausgabe übereinstimmen.

3. Wiederverwende geeignete Resize-Kerne, trenne aber paketweiten Maßstab von einer unabhängigen maximalen Kantenlänge pro Bild. Verbundene Bodenkacheln dürfen nciht durch uneinheitliche Skalierung ihre Anschlussmaße verlieren.

4. Bewahre transparente Ränder und definierte Anker. Kachelbare Bilder benötigen ausdrücklich festgelegte Randbehandlung; eine wiederholte Vorschau darf Nahtfreiheit nciht ohne Prüffung behaupten.

5. Erzeuge die fünf Grafikstufen und eine statische Vergleichsansicht ohne GIFs, FPS- oder Frame-Regler. Farbe/Materialkorrektur ist nur aktiv, wenn das gewählte Rezept sie vorsieht.

6. Kennzeichne unterstützte Bildarten. Normalmaps, Höhenkarten und andere Datenkarten werden in dieser Erstversion nciht wie Farbbilder quantisiert; nciht unterstützte Typen führen zu einer klaren Meldung.

7. Ergänze Report, Dateiintegrität und Dry-run. Dokumentiere neue CLI-/Rezeptverträge getrennt vom bisherigen reservierten Modus.

## Erwartete Ergebnisse

- `Neue Texturmodule und Adapter`
- `Statische Grafikprofile`
- `Textur- und Kachel-Fixtures`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein Paket aus Boden-/Säulenbildern erzeugt nur Grafikvarianten, keine GIFs oder Frameordner.
- [ ] Gemeinsame Kachelgrößen bleiben bei jedem Paketprofil konsistent.
- [ ] Ein ausdrücklich als Normalmap markiertes Bild wird nciht als Farbtextur verarbeitet.
- [ ] Ein erneuter identischer Lauf erhält verifizierte Ergebnisse und Quellen.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Der Texturmodus ist tatsächlich implementiert.
- [ ] Statische und animierte Rezepte sind klar getrennt.
- [ ] Maßstab und Randregeln sind testbar.
- [ ] Unbekannte Datenkarten werden nciht still beschädigt.

## Nicht Bestandteil dieser Aufgabe

Keine 3D-Modellerzeugung und keine automatische Material-/Normalmap-Synthese.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T028.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T029 — Asset-Pakete und Tempel-Arbeitsbereich umsetzen](../029-assetpakete-und-tempel/p.md). Nicht automatsich starten.
