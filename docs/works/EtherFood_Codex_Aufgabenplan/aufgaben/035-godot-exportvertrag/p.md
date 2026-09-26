---
task_id: T035
phase: E
status: not_started
depends_on: ["T001", "T013", "T025", "T026", "T028", "T029", "T033"]
requirements: ["R15", "R16", "R23", "R26"]
---
# T035 — Godot-Export und portable Runtime-Ressourcen implementieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** E — Versionen und Godot-Freigabe  
**Abhängigkeiten:** [T001](../001-bestand-und-schreibgrenzen/p.md), [T013](../013-assettypen-posen-und-richtungen/p.md), [T025](../025-timing-und-animationsevents/p.md), [T026](../026-grafikstufen-spritesheets/p.md), [T028](../028-statische-texturpipeline/p.md), [T029](../029-assetpakete-und-tempel/p.md), [T033](../033-kandidaten-und-versionsarchiv/p.md)  
**Anforderungsbezug:** R15, R16, R23, R26

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Erzeuge aus einem Kandidaten einen unveränderlichen Godot-Export, der in Test- und Spielbereich verwendet werden kann.

## Kontext und Bestandsgrenzen

Die tatsächliche Godot-Version und der derzeitige Ressourcenverbraucher müssen aus T001 geprüft werden. Die Quellen belegen keine fertige Godot-Anbindung.

## Umsetzungsschirtte

1. Erfasse die vorhandenen Godot-Ressourcen und Namens-/Ankerkonventionen. Lege die konkret unterstützte Engine-Version und Import-/Render-Einstellungen fest; keine ungetestete Versionsspanne versprechen.

2. Definiere ExportBundle mit candidate_id, exporter_version, runtime_template_digest, Ziel-Engine und vollständigem Payload-Manifest. Alle Bilddaten stammen bytegleich aus dem eingefrorenen Kandidaten.

3. Bevorzuge einen portablen Manifest-/Loader-Vertrag: paketrelative Pfade, Pose-/Richtungsnamen, Raster, Anker, Zeiten und Profile. Ein geprüftes GDScript lädt daraus die benötigten Ressourcen mit übergebener Paketwurzel, statt res://test_assets fest in jede Ressource zu schreiben.

4. Binde den bestehenden Godot-Verbraucher kompatibel an oder erzeuge die erforderlichen SpriteFrames/Atlas-Ressourcen mit Godots API. Werden .tres/.tscn gespeichert, teste relative Pfade, ResourceUID und Abhängigkeiten ausdrücklich; eine reine Textpfad-Ersetzung reicht nciht.

5. Wähle Grafik- und Frame-Stufe zur Laufzeit über den Manifestvertrag. Lade nciht sofort alle Varianten. Niedrige Frame-Stufen verwenden tatsächlich kompakte Bildpakete; bloßes Überspringen von Frames eines weiterhin voll geladenen Atlas ist kein Speicherreduktionsnachweis.

6. Für statische Pakete exportiere Mitgliedsbezüge, Maßstab und Anker ohne Animationsdaten. Erzeuge bei Bedarf eine Testzusammenstellung, ohne vorhandene Spiel-/Level-Logik zu überschreiben.

7. Prüfe den Export in einem isolierten synthetischen Godot-Projekt und friere ExportBundle samt Digest ein. Deployment-spezifische Importpfade/UIDs werden getrennt vom unveränderlichen Bild-/Manifest-Payload dokumentiert.

## Erwartete Ergebnisse

- `godot/exporter.py`
- `Godot Runtime-/Test-Loader`
- `ExportBundle-Schema und Ressourcen-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Test- und Runtime-Wurzel liefern dieselben Bild-/Manifest-Payload-Hashes.
- [ ] Alle benötigten Pose-/Richtungs-/Grafik-/Framekombinationen sind adressierbar.
- [ ] Ein korrigierter Anker und preserve_duration-Zeiten kommen korrekt im Godot-Vertrag an.
- [ ] Ein statisches Paket verlangt keine SpriteFrames oder Richtungsmetadaten.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Ein echter Godot-Loader oder kompatibler Ressourcenexport existiert.
- [ ] ExportBundles sind reproduzierbar und unveränderlich.
- [ ] Testpfade sind nciht fest im Runtime-Payload verankert.
- [ ] Die konkrete Engine-Version wurde geprüft oder der Integrationstest ist ausdrücklich blockiert.

## Nicht Bestandteil dieser Aufgabe

Keine produktive Projektänderung, kein Erfinden vorhandener Godot-Szenen und keine zusätzliche Animationserzeugung.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T035.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T036 — Kandidaten im Godot-Testbereich bereitstellen und importieren](../036-godot-testbereitstellung/p.md). Nicht automatsich starten.
