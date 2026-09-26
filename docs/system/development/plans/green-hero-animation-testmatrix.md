<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: Green-Hero-Animations-Testmatrix

## Zweck und Gesamtbild

Das visuelle Testlabor erhält die fünf gelieferten Grafikvarianten, fünf
umschaltbare Frame-/FPS-Stufen und die Bewegungen Stand, Slow Walk, Walk, Sneak, Run,
Sprint und Jump. Die Umsetzung bleibt auf Testassets und Entwicklungsbuild
beschränkt.

## Ausgangslage

Die neuen PNGs liegen unter
`game/test_assets/characters/heroes/greenhero/spritesheets/`. Vorhanden sind
für fünf Varianten und fünf Rastergrößen die acht Richtungen von Stand,
Slow Walk, Walk, Sneak und Run. Jump besteht aus je einem PNG; Sprint hat
keine eigenen PNGs und wird aus Run bei 12 FPS abgeleitet. Der bisherige
Testaufbau erwartete dagegen vier alte Varianten und alte SpriteFrames-Dateien.

## Umfang und Nicht-Ziele

- Laufzeitbibliothek für die neue vollständige Matrix einführen.
- Grafikvariante sowie Frames und FPS im F5-Menü in zwei Spalten umschaltbar
  und persistent machen.
- Beim Wechsel der Frames-Auswahl die FPS-Spalte auf `Neu` setzen; eine
  gewählte Frames/FPS-Kombination über `Strg + Alt + E` als Spielstandard
  übernehmen können.
- Sprint auf Run/12 FPS und Jump auf ein eingefrorenes Einzelbild festlegen.
- Godot-Laufzeittests und Python-Assetprüfung auf die Matrix umstellen.
- Dokumentation auf den tatsächlichen Teststand bringen.
- Keine finale Assetfreigabe, keine Änderung an Kanon, Gamedesign oder
  Produktionsgrafiken.

## Fortschritt

- [x] Assetmatrix und bestehende Testpfade geprüft.
- [x] Laufzeitbibliothek und fünf Varianten/Frames-/FPS-Auswahl umgesetzt.
- [x] F5-Menü mit getrennten Frames-/FPS-Spalten, `Neu`-Reset und
  Spielstandard-Übernahme angepasst.
- [x] Der Green-Hero-Controller liest das übernommene Frames/FPS-Paar aus
  der versionierten Visual-Lab-Standardressource.
- [x] Godot-Testablauf auf Varianten, FPS und Bewegungen umgestellt.
- [x] Python-Assetprüfung und Dokumentation aktualisiert.
- [ ] Godot-Laufzeitsuite in einer Umgebung mit Godot-CLI ausführen.
- [x] Standardprüfung ausgeführt; Godot und zwei bereits fehlende
  Entscheidungsdokumente bleiben Umgebungs-/Bestandsblockaden.

## Erkenntnisse und Entscheidungen

- „Snake“ wird anhand der vorhandenen Dateien als `sneak` verstanden. Die
  gelieferten Verzeichnisse und der bestehende Eingabepfad heißen `sneak`.
- Sprint erhält keine Kopien der Run-PNGs. Die Bibliothek liest die 12er-Run-
  Variante und setzt deren Wiedergabetakt auf 12 FPS.
- Die SpriteFrames werden zur Laufzeit gebaut. Dadurch müssen 25 große,
  nahezu identische `.tres`-Ressourcen nicht ins Repository gelegt werden.
- Frames und Wiedergabe-FPS sind getrennte Laufzeitparameter. `Neu` verwendet
  vorläufig dieselbe Zahl für beide; erst eine explizit gewählte FPS-Zahl gilt
  als speicherbare Frames/FPS-Kombination.
- Jump verwendet je Variante das tatsächlich gelieferte Canvas und skaliert
  Fußanker und Referenzhöhe proportional; dadurch bleiben Comic- und
  Pixelauflösungen im selben Weltmaßstab.
- „Google Excel Engine“ ist im Repository nicht vorhanden; der Testablauf
  gehört deshalb in die vorhandene Godot-Testszene.

## Prüfungen

Ausgeführt:

- `python3 -m unittest tools.tests.test_asset_layout -v` – bestanden.
- `python3 -m unittest tools.tests.test_green_hero_animation_library
  tools.tests.test_asset_layout tools.tests.test_godot_project -v` – 29 Tests
  bestanden.
- `PYTHONPATH=tools/src python3 -c '... run_style(...)'` – Stilprüfung für
  105 Dateien bestanden.
- `git diff --check` – bestanden.
- `python tools/control.py check` – nicht vollständig bestanden: Godot fehlt;
  zusätzlich fehlen im vorhandenen Arbeitsstand
  `docs/game/decisions/index.md` und `ADR-0008-achtteiliger-spielablauf.md`.
- Godot-Syntaxprüfung versucht: `godot --headless --path game --editor --quit
  --check-only` – nicht ausführbar, weil `godot` in der Umgebung fehlt.

Noch ausstehend:

- gezielte Godot-Laufzeitsuiten nach Installation der Godot-CLI.

## Wiederholbarkeit und Wiederherstellung

Die Bibliothek liest ausschließlich versionierte Testasset-Pfade. Sie schreibt
keine Cache- oder Importdateien. Lokale Laborwerte bleiben unter `user://`;
keine Zugangsdaten oder lokalen Pfade werden in den Arbeitsbaum übernommen.

## Ergebnis und Rückblick

Die Umsetzung stellt die gewünschte Testmatrix im F5-Labor bereit. Der einzige
offene Abschlussnachweis ist die Ausführung der Godot-Suiten in einer Umgebung,
in der die Godot-CLI installiert ist.
