<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Asset-Ablage und Freigabe

## Verbindliche Ablage

| Ordner | Bedeutung |
|---|---|
| `game/tests/assets/` | Vorläufige Grafiken, Prototypen, Vergleichsvarianten und Quellen ohne finale Freigabe |
| `game/assets/` | Final freigegebene und ins Spiel übernommene Assets |

Noch nicht eingeordnete, nicht abschließend integrierte oder nicht freigegebene
Assets gehören unter `game/tests/assets/`. Die Verwendung im visuellen
Testlabor, im Heldenraum oder einer anderen Prototypszene erteilt keine
Freigabe. Eine funktionierende Integration allein macht eine Grafik noch
nicht final.

Aktuell liegen sowohl `characters/` als auch `prototypes/` vollständig unter
`game/tests/assets/`. `game/assets/` bleibt leer, bis Inhalte finalisiert
werden. Git versioniert keine leeren Verzeichnisse; daher kann der Ordner in
einem frischen Checkout fehlen.

## Übernahme ins Spiel

Eine bewusste Freigabe legt fest, welche konkrete Version final ist und wofür
sie im Spiel eingesetzt wird. Danach werden die freigegebenen Dateien aus dem
Testbestand nach `game/assets/` verschoben. Ressourcenverweise, Manifeste,
Generatorziele, `.png.import`-Metadaten, Tests und Dokumentation werden dabei
gemeinsam aktualisiert. Es bleibt keine zweite aktive Kopie im Testbestand.

Arbeitsquellen, verworfene Entwürfe und weitere Vergleichsvarianten besitzen
dadurch keine automatische Freigabe. Ändert eine Übernahme bereits angenommenen
Kanon oder Gamedesign, wird die Entscheidung zusätzlich unter
[`docs/game/decisions/`](../../../game/decisions/index.md) festgehalten.

PNG-Quellen und Importmetadaten werden versioniert. Der von Godot erzeugte
Cache bleibt lokal; Einzelheiten stehen unter
[Godot-Ressourcenimporte](../tooling/godot-resource-imports.md).

## Aktueller Green-Hero-Testbestand

Unter `game/tests/assets/characters/heroes/green_hero/` liegen vier getrennte
Varianten: `hd/`, `pixel_art/`, `ultra/` und `test/`. Ultra enthält die neuen
4×4-Sheets für Stand und Walk samt Quellen. Test enthält inzwischen die
vollständigen Raster mit 1436 × 1254 Pixeln je Feld. Die bisherigen
Einzelbilder bleiben unter `test/sources/stand/` als Referenz erhalten; das
SH-Skript ermöglicht den schnellen Austausch der Testbilder. HD enthält
die vom Benutzer gewählte frühere animierte Fassung aus Git. Alle Varianten
besitzen eigene Stand-/Walk-Dateien,
Manifeste und Godot-Ressourcen. Die Auswahl im Labor erteilt keine Freigabe.
Richtungszuordnung und Bilddaten stehen unter
[Green Hero – Stehen und Gehen](../features/green-hero-stand-und-gehen.md).
