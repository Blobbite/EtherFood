<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: Testassets und neue Ultra-Standbilder

## Zweck und Ausgangslage

Alle bisherigen Charakter- und Prototypgrafiken sind vorläufig. Sie liegen
noch unter `game/assets/`; die neuen acht Stand-Sheets und acht Einzelbilder
liegen bereits unter `game/tests/assets/characters/hero/`.

## Umfang und Schritte

1. Bildmaße, Richtungen und Ressourcenverweise prüfen.
2. Charaktere und Prototypen nach `game/tests/assets/` verschieben und alle
   aktiven Verweise einschließlich Generatoren und Importmetadaten nachführen.
3. Die acht Ultra-Stand-Sheets durch die neuen, passend benannten PNGs ersetzen.
   Ausschnitte, Prüfsummen und Größenbezug anpassen; Einzelbilder als Quellen
   erhalten. Gehbilder und Spielregeln bleiben erhalten.
4. Die Trennung zwischen Testbestand und freigegebenen Assets dokumentieren.
5. Generator-, Python-, Stil- und Godot-Prüfungen ausführen und Änderungen prüfen.

## Fortschritt

- [x] Struktur, bestehende Benutzeränderungen und Bildmaße geprüft.
- [x] Testassets verschoben und Verweise aktualisiert.
- [x] Neue Stand-Sheets eingebunden und Darstellung angepasst.
- [x] Freigaberegel und aktuelle Asset-Dokumentation nachgeführt.
- [x] Prüfungen und Abschlusskontrolle abgeschlossen.

## Erkenntnisse und Entscheidungen

Die neuen Sheets besitzen 16 Felder mit jeweils 1205 Pixeln Höhe und stammen
aus 1254 × 1254 Pixel großen Einzelbildern. Die bisherige 640-Pixel-Referenz
passt deshalb nur noch zu den Gehbildern. Original-PNGs werden unverändert
übernommen; Größen- und Fußbezug müssen in den Animationsdaten unterschieden
werden. Die bestehenden Animationsnamen bleiben erhalten.

Alle 16 Felder jeder neuen Standrichtung sind identische Kopien des
Alpha-Zuschnitts ihres Einzelbilds. Das vorhandene Raster und die Taktung
bleiben erhalten; die Standversion zeigt eine ruhende Pose. Die PNG-Dateien
werden weder neu gerendert noch skaliert.

Der Benutzer hat die bisherige Testgrafik bereits nach `game/tests/assets/`
verschoben. Diese Änderung wird erhalten und ihr Importverweis berichtigt.
Die Verwendung in einer Prototypszene bedeutet keine finale Asset-Freigabe.
Kanon und Gamedesign werden durch diese Bestandsordnung nicht verändert.

## Prüfungen

- `.venv/bin/python -m pytest tools/tests/test_green_hero_animation_generator.py
  tools/tests/test_green_hero_pixel_art_assets.py -q`: neun Tests bestanden.
- `.venv/bin/python game/tools/generate_green_hero_animations.py --check`:
  16 Animationen und 256 Frames geprüft.
- `.venv/bin/python game/tools/generate_scale_reference_assets.py --check`:
  21 deterministische Prototypassets und zwei optimierte Nebeltexturen geprüft.
- Vier gezielte Godot-4.7.2-Suiten über einen temporären Teststarter:
  Green-Hero-Animation, Hero-Grafikvergleich, Weltzustände und Gameplay
  bestanden. Einschließlich Vergleich aller 128 Standfelder mit den Quellen,
  Größen-/Fußbezug für Stehen und Gehen und Grafikwechsel während des Gehens.
- `.venv/bin/python tools/control.py check` mit Godot im Suchpfad:
  Doctor 12/12, Stilprüfung für 84 Dateien und Godot-Ressourcenimport bestanden.
  197 von 198 Python-Tests bestanden. Der Dokumentationsstrukturtest scheitert
  am bereits vorhandenen, ignorierten `docs/concept/.obsidian/`, der einen
  vierten lokalen Dokumentationsordner erzeugt.
- Die vollständige Godot-Integration meldet 75 Fehler durch bestehende
  Abweichungen zwischen Standardressourcen und Testerwartungen, unter anderem
  Heldenhöhe, Kamera, Bewegung und Nebel. Ein separat importierter, unveränderter
  Git-Stand meldet exakt dieselben 75 Fehler; keine neuen Fehler und keine
  geänderten Fehlertexte. Die Standardressourcen wurden nicht verändert.
- Alle 64 behaltenen PNGs sind bytegleich zu den jeweiligen Eingangsdateien;
  die acht alten Stand-Sheets sind entfernt. Alle Import-Quellpfade passen,
  `game/assets/` ist leer, 58 relative Dokumentationslinks sind gültig.
- `git diff --check`: bestanden. Die Forge2D-Referenz blieb unverändert.

## Wiederholbarkeit und Wiederherstellung

Der versionierte Manifestbestand und die PNGs müssen für den Generator ohne
externen Quellordner ausreichen. `.png.import` bleibt versioniert; Godot-Caches
bleiben ausgeschlossen. Alte Stand-Sheets sind über die Git-Historie vorhanden.
Keine Git-Rücksetzungen; bereits vorhandene Benutzeränderungen bleiben erhalten.

## Ergebnis und Rückblick

Abgeschlossen: Charaktere und Prototypen liegen vollständig im Testbestand,
die neue Ultra-Standversion ist eingebunden und die Freigaberegel ist in
Architekturdokumentation und Repository-Regeln verankert. Die gezielten
Prüfungen bestehen. Die unabhängig bestätigten Altfehler des Standardlaufs
bleiben als separates Arbeitspaket offen.

## Nachtrag: Standposen auch beim Gehen prüfen

Der Benutzer möchte dieselben acht neuen Sheets zusätzlich unter `walk/`
einsetzen, um die Darstellung beim Bewegen zu prüfen. Die Walk-Dateien behalten
ihre richtungsbezogenen `_walk_`-Namen und verwenden dieselben Bildausschnitte,
Größenwerte und Einzelbildquellen wie `stand/`. Das ist eine vorläufige
Bewegungsdarstellung mit ruhenden Posen und keine neue Gehbewegungsschleife.
Die bisherigen Gehbilder bleiben über die Git-Historie wiederherstellbar.

- [x] Bestehende Walk-Verweise und Bilddaten geprüft.
- [x] Acht Walk-Dateien ersetzt, Manifest und Ressource nachgeführt.
- [x] Tests und aktuelle Dokumentation angepasst.
- [x] Gezielte Prüfungen und Standardlauf ausgewertet.

Prüfungen des Nachtrags:

- Neun gezielte Python-Tests für Ultra-Generator und Pixelart bestanden.
- Generator mit `--check`: 16 Animationen und 256 Frames geprüft.
- Acht Walk-/Stand-Paare bytegleich; die Standdefinitionen blieben unverändert.
  Alle 256 Felder werden gegen ihre Einzelbildquellen geprüft.
- Vier gezielte Godot-Suiten für Animation, Hero-Grafikvergleich, Weltzustände
  und Gameplay bestanden, einschließlich des Grafikwechsels während des Gehens.
- Standardlauf erneut ausgeführt: Doctor, Stil und Ressourcenimport bestanden;
  weiterhin 197 bestandene Python-Tests und derselbe lokale Obsidian-Fehler.
  Die 75 Godot-Fehler stimmen unverändert mit dem zuvor geprüften Git-Stand
  überein. Keine neuen Fehler.
- 58 relative Dokumentationslinks und `git diff --check` bestanden.

Ergebnis des Nachtrags: abgeschlossen. Stand und Gehen verwenden die neuen
Posen mit identischem Maßstab und Fußanker. Das Menü bezeichnet diese
vorläufige Fassung als `Ultra · Testposen`. Die Bewegungssteuerung bleibt
unverändert; die Freigaberegel gilt weiterhin.
