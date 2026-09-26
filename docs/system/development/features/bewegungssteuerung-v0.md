<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Funktion: Bewegungssteuerung V0

## Ziel

Die gemeinsame Heldenfigur stellt fünf tastaturgesteuerte
Bewegungsgeschwindigkeiten und fünf Top-down-Sprungarten bereit. Die
verbindlichen Regeln stehen im Konzept unter
[Bewegungssteuerung V0](../../../game/design/gameplay/bewegungssteuerung-v0.md).

## Umfang

Enthalten sind WASD und Pfeiltasten, Feststelltasten-Gehen, aktionsbasierte
Doppel-Taps für Rennen, gehaltenes Shift-Sprinten, Strg-Schleichen, Sprünge
mit Leertaste, Schleichzoom, Kollisions- und Dialogsperren sowie
Diagnosewerte im visuellen Testlabor.

Freie Tastenbelegung, vollständige Controllerunterstützung,
Barrierefreiheitsoptionen, Ausdauer, Sprungangriffe, Ausweichen,
Schleichrolle, Ausweich-Backflip und niedrige überspringbare Hindernisse
gehören nicht zu V0. Die Geschwindigkeiten und Sprungprofile bleiben
abstimmbare Testwerte.

## Entwurf

`HeroCharacter` wertet die vier semantischen Bewegungsaktionen aus. Ein
zweiter echter Tastendruck derselben Richtung innerhalb des konfigurierten
Fensters aktiviert Rennen; Echo-Ereignisse zählen nicht. Der Rennzustand ist
von der auslösenden Richtung getrennt. Er bleibt bei Richtungswechseln aktiv
und endet nach vollständigem Loslassen plus kurzer Wechseltoleranz.

`gameplay_walk_toggle` schaltet den Gehmodus über Feststelltaste.
`gameplay_sprint` bildet beide Shift-Tasten ab und wirkt nur zusammen mit
aktivem Rennen. `gameplay_sneak` hat Vorrang vor allen anderen
Geschwindigkeiten. `Input.get_vector()` begrenzt diagonale Richtungen auf
Länge eins.

Die Werte liegen in
`res://shared/resources/hero_movement_v0.tres` auf Grundlage von
`HeroMovementConfig`. Die Ressource enthält:

- Schleichen, Gehen, Laufen, Rennen und Sprinten,
- Steh-, Geh-, Lauf-, Renn- und Sprintsprunghöhe,
- die Weiten der vier Bewegungssprünge,
- Sprungdauern sowie Doppel-Tap- und Richtungswechseltoleranz.

Beim Sprung bleibt `CharacterBody2D` der kollidierende Bodenanker. Der äußere
`Visual`-Knoten bleibt für Pixel-Snap zuständig, während `JumpVisual` Figur
und Richtungsmarker entlang einer Parabel versetzt. Der Schatten bleibt am
Boden. Der Stehsprung hat keine horizontale Bewegung; alle anderen Profile
verwenden eine feste Zielweite mit begrenzter Luftkorrektur.

Ein Sprung aus dem Schleichen wählt den Stehsprung und sendet sofort den
inaktiven Schleichzustand. Bei der Landung wird Schleichen wieder aktiv, wenn
Strg weiterhin gehalten ist. Der gemeinsame `PlayerCameraController`
kombiniert dieses Signal mit dem szeneneigenen `CameraProfile`.

## Darstellung

Die Bewegungslogik stellt zusätzlich eine achtteilige Animationsrichtung und
die tatsächlich nach Kollision verbleibende Bodenbewegung bereit. Der getrennte
Animationscontroller verwendet diese Angaben für die eingebundenen
[Green-Hero-Stand- und Gehfolgen](green-hero-stand-und-gehen.md). Normale
Richtungseingaben zeigen `walk`; gehaltenes Shift zeigt außerhalb des aktiven
Rennens `slowwalk`. Aktives Rennen mit Shift zeigt `sprint`. Eingaben und
Geschwindigkeiten werden dabei nicht doppelt ausgewertet. Alle Sprünge zeigen
das erste Standbild ihrer Richtung.

## Gameplay-Labor

Das visuelle Testlabor weist dem Helden eine tiefe Laufzeitkopie der geladenen
Bewegungsressource zu. Die Regler verändern nur diese Kopie und speichern
ihren Arbeitsstand in `user://visual_lab_settings.cfg` mit Schema 4. Werte
werden auch bei manipulierten Einstellungsdateien auf sichere Grenzen
beschränkt.

Nur `Als Spielstandard übernehmen` oder `Strg + Alt + E` schreibt den
fokussierten Wert in die versionierte Bewegungsressource. Andere Testwerte
werden dabei nicht mitgeschrieben.

## Prüfung

Die Godot-Integration prüft:

- alle acht Tastaturbelegungen für richtungsbezogene Doppel-Taps,
- Feststelltasten-Gehen und ignorierte Echo-Ereignisse,
- fortgesetztes Rennen, gehaltenes Sprinten und Schleichpriorität,
- alle fünf Sprungprofile, den senkrechten Schleichsprung und Luftkorrektur,
- Kollisionen, Bewegungssperre und Dialoginteraktion,
- Reglergrenzen, lokale Vorschauwerte, tiefe Ressourcenkopie und fokussierte
  Einzelwertübernahme im Gameplay-Labor.

Die Input-Map-Regression prüft Leertaste, Feststelltaste sowie linke und rechte
Strg- und Shift-Taste ausdrücklich.
