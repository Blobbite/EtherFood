<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: Seele im Portalturm

## Zweck und Ausgangslage

Stand: 12. September 2026.

Die drei vom Benutzer vorbereiteten Seelenraster unter
`game/tests/assets/characters/sools/` sollen im Portalturm spielbar werden.
Jedes transparente PNG misst 1024 × 512 Pixel und enthält acht Frames in
vier Spalten und zwei Zeilen. Das letzte Abschiedsframe ist transparent.
Der Held besitzt bereits einen Interaktionsdetektor und die Aktion
`gameplay_interact` für E und Controller-A. Das Labor benutzt sie bisher nicht.

## Umfang und Entscheidungen

- Eine leicht blau leuchtende Seele steht nahe der Turmmitte, frei von Türen
  und Ankunftspunkten. Alle drei gelieferten PNGs bleiben unverändert.
- Idle läuft endlos. Erstes Ansprechen startet Interact einmal und zeigt
  anschließend eine kurze Nachricht aus eigens gezeichneten Fantasieglyphen.
  Danach kehrt die Seele zu Idle zurück. Esc/B kann das Gespräch schließen.
- Erst das zweite Ansprechen startet `soul_depart_spritesheet_4x2.png`.
  Alle acht Abschiedsframes laufen einmal, dann verschwinden Seele und Licht.
  Während eines Gesprächs oder Abschieds lösen weitere E-Eingaben nichts aus.
- Gespräch und Verschwinden bleiben bei Raumwechseln während eines
  Laborbesuchs erhalten. Erneutes Öffnen des Labors setzt die Probe zurück.
- Die Schrift ist lokale Prototypgrafik, keine neue verbindliche Sprache
  oder Regel des Spielkanons. Keine Quests, Seelenökonomie oder Spielbelohnung.
- F5 bleibt nutzbar. Die Seele verwendet ihren einzigen gelieferten Bildsatz;
  der bestehende Texturfiltervergleich gilt auch für ihre Animation.

## Schritte und Fortschritt

1. [x] Assets, Interaktionsvertrag, Raumwechsel und Vorgaben prüfen.
2. [x] Seelenszene, SpriteFrames, Leuchten und Fantasieschrift erstellen.
3. [x] E-Interaktion, Gespräch, Abschied und Raumzustand verbinden.
4. [x] Aussagekräftige Laufzeittests für den vollständigen Ablauf ergänzen.
5. [x] Assetverwendung und Bedienung dokumentieren.
6. [x] Gezielte Tests, grafische Kontrolle und Standardprüfung ausführen.

## Erkenntnisse und Prüfungen

Die Benutzerdateien enthalten einen Alphakanal; alle 24 Rasterzellen können
unverändert als Atlasregionen eingebunden werden. Die gezielten Godot-Suiten
`portal_lab_soul_test.gd`, `portal_lab_test.gd` und `portal_lab_graphics_test.gd`
bestehen ohne Fehler. Die Stilprüfung und die Dokumentationslinks bestehen
ebenfalls. Im ersten Seelentest wartete die Hinweiskontrolle noch nicht auf
Godots Verarbeitung des aktuellen Frames; die Prüfung wartet nun auf den
vollständig verarbeiteten Zustand. Sieben Godot-Aufnahmen in 1920 × 1080
bestätigen Idle, Interact, Glyphennachricht, F5, erneutes Idle, Abschied und
den leeren Platz nach dem Abschied. Die drei Benutzer-PNGs und die vorhandene
Darstellungsgrundlage sind bytegleich zum Aufgabenbeginn.

Der vollständige Lauf `python tools/control.py check` am 12. September 2026
ergibt Doctor 12/12, bestandene Stilprüfung für 102 Dateien und 230 bestandene
Python-Tests. Der bekannte Python-Fehler durch die lokale zusätzliche
Dokumentationsebene `docs/concept/.obsidian/` bleibt bestehen. Godot meldet
427 Erwartungsfehler: Anzahl und Meldungen stimmen exakt mit dem Lauf vor
dieser Aufgabe überein. Es gibt keine neuen Erwartungsfehler und keine
Script-, Parse- oder sonstigen Laufzeitfehler. Die Seelen- und beiden
Portal-Suiten bestehen auch innerhalb dieses vollständigen Laufs.

Die Gesamtprüfung ist wegen der vorhandenen Standarderwartungen und des
Dokumentationsfehlers weiterhin nicht grün. Die Benutzerstandards bleiben
erhalten. `git diff --check` und die Dokumentationslinkprüfung bestehen.

## Wiederholbarkeit und Wiederherstellung

Szenen, Animationen, Glyphen und Tests liegen als Textressourcen vor. Die
gelieferten PNGs werden nur referenziert. Vorherige Fassungen betroffener
Dateien sind für den Vergleich flüchtig gesichert. Keine Git-Rücksetzungen,
neuen Abhängigkeiten, Zugangsdaten oder Änderungen am Kanon.

## Ergebnis und Rückblick

Die Seele ist neben der Turmmitte eingebunden. Erstes Ansprechen zeigt nach
Interact die erfundene Schrift und führt zurück zu Idle. Zweites Ansprechen
spielt alle acht Frames der gelieferten Abschiedsdatei einmal und entfernt
die sichtbare Seele samt Licht. Raumwechsel erhalten den Zustand; ein neuer
Laborbesuch ermöglicht eine neue Probe. Eingabewiederholungen, F5 und Esc
sind abgedeckt, ohne das bestehende Portal- oder Grafikverhalten zu ändern.
