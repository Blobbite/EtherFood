<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: Green Hero mit deutschen Himmelsrichtungen

## Zweck und Ausgangslage

Die vier Varianten unter `game/tests/assets/characters/heroes/green_hero/`
verwenden bisher unterschiedliche Richtungsnamen: HD, Ultra und Test nutzen
WASD-Kürzel in Dateinamen, Pixel Art englische Himmelsrichtungen. Godots
Animationsnamen verwenden englische Kürzel. Auf Benutzerwunsch werden
Dateien und Godot-Namen auf `N`, `NO`, `NW`, `O`, `S`, `SO`, `SW`, `W`
vereinheitlicht.

## Umfang und Schritte

1. Dateinamen, Richtungszuordnungen und sämtliche Verbraucher erfassen.
2. Dateien und Importverweise kollisionsfrei umbenennen, Manifeste und
   Godot-Ressourcen angleichen.
3. Laufzeitsteuerung, Generator und Testimport auf dieselben Namen umstellen.
4. Richtungserhalt, Bildprüfsummen und Generator-/Laufzeittests prüfen;
   aktuelle Dokumentation anpassen.
5. Godot-Import und Standardprüfung durchführen, Ergebnis festhalten.

Bildinhalte, Maßstab, Fußanker, Animationsdauer, Spielregeln und die bereits
umgesetzten Diagnoseanzeigen werden nicht verändert.

## Fortschritt

- [x] Bestandsaufnahme abgeschlossen.
- [x] Dateien, Manifeste und Ressourcen umbenannt.
- [x] Generator, Testimport und Laufzeit angepasst.
- [x] Gezielte Prüfungen und Dokumentation abgeschlossen.
- [x] Standardprüfung und Abschlusskontrolle durchgeführt.

## Erkenntnisse und Entscheidungen

- Die Umbenennung erfolgt je bisherigem Namenssystem. Das alte WASD-`w`
  bezeichnet Norden, das alte Pixel-Art-`w` dagegen Westen. Dateinamen werden
  deshalb nicht durch globale Textersetzung vertauscht.
- Die Richtungsanteile werden großgeschrieben, etwa
  `greenhero_NO_walk_spritesheet_4x4_o.png` und `walk_NO` in Godot.
  Bereits korrekt benannte Quellen wie `NO_solo_4x4.png` bleiben erhalten.
- PNG-Inhalte und ihre Prüfsummen bleiben unverändert. Import-UIDs werden
  übernommen; Godot darf seine flüchtigen Importcaches neu erzeugen.
- 104 PNGs samt ihren Importdateien wurden umbenannt. Die Prüfsummen aller
  136 PNGs unter dem Zielordner sind gegenüber dem Ausgangsstand identisch.
- `source_file` im Pixel-Art-Manifest bleibt als Nachweis des ursprünglichen
  externen Dateinamens erhalten; sämtliche lokalen Verweise und die
  Richtungsfelder verwenden die neuen Namen.
- Testimport und Generator erzeugen künftig ausschließlich deutsche Kürzel.
  Vorhandene externe Eingaben mit eindeutig alten WASD-Namen bleiben als
  Importformat lesbar; die Großschreibung kennzeichnet die neuen Namen.

## Prüfungen

Der Prüfsummenvergleich aller PNGs ist erfolgreich. Die 26 gezielten
Python-Tests für Generator, Pixel Art und Testimport bestehen, einschließlich
der unterschiedlichen Bedeutung des alten WASD-`w` und des neuen `W`.
Godot hat die umbenannten Assets erfolgreich seriell importiert. Alle 136
Textur-UIDs sind erhalten, sämtliche Importziele vorhanden. Die temporäre
Editor-Einstellung zur Speicherbegrenzung ist entfernt.

Die Godot-Suiten `green_hero_animation_test`, `visual_lab_hero_graphics_test`
und `visual_lab_gameplay_test` bestehen. Sie prüfen Ressourcen und
Richtungswechsel einschließlich Stehen, Gehen und Wechsel der vier Varianten.
Der Probelauf von `rename_test_assets.sh --dry-run`, die Stilprüfung für 88
Dateien und `git diff --check` sind ebenfalls erfolgreich. Die aktuelle
Dokumentation enthält die neuen Richtungsnamen.

`python tools/control.py check` ist ausgeführt: Doctor 12/12 erfolgreich,
Stilprüfung erfolgreich, 214 Python-Tests bestanden. Es bleiben der bekannte
Dokumentationsstrukturfehler und exakt dieselben 75 Godot-Erwartungsfehler wie
vor der Umbenennung. Der Vergleich der Fehlermeldungen einschließlich ihrer
Häufigkeiten zeigt keine zusätzlichen Fehler. Der abschließende Abgleich
bestätigt unveränderte PNG-Inhalte und alle 64 korrekt benannten Animationen.

Der letzte Standardlauf enthielt 75 bestehende Godot-Erwartungsfehler zu
Spielstandards und einen Dokumentationsstrukturfehler durch den ignorierten
lokalen Ordner `docs/concept/.obsidian/`; der Abschlussvergleich berücksichtigt
diese Ausgangslage.

## Wiederholbarkeit und Wiederherstellung

Der Generator erstellt die SpriteFrames anhand der Manifeste. Das vorhandene
`test/rename_test_assets.sh` aktualisiert Testbilder auch mit den neuen Namen.
Die temporäre Umbenennungsliste und PNG-Prüfsummen dienen zur Kontrolle; sie
werden nicht versioniert. Bestehende Arbeitsbaumänderungen bleiben erhalten.

## Ergebnis und Rückblick

HD, Pixel Art, Ultra und Testversion verwenden in ihren lokalen Dateinamen
und Godot-Animationen einheitlich `N`, `NO`, `NW`, `O`, `S`, `SO`, `SW`, `W`.
Die Zuordnung zu Blickrichtungen und Eingaben bleibt erhalten. Generator,
Testimport, Laufzeitsteuerung und aktuelle Dokumentation verwenden dasselbe
Schema. Bilder, Layoutkalibrierung und Animationszeiten sind unverändert.
