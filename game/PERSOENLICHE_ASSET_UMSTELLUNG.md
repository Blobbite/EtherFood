# Persönliche Notiz: Asset- und Teststruktur

Stand: 18. September 2026. Diese Übergabenotiz gehört nicht zur aktiven
Dokumentationsnavigation und wird durch die Exportfilter ausgeschlossen.

## Was geändert wurde

Das vorhandene Godot-Projekt unter `game/` verwendet jetzt:

| Ordner | Zweck |
|---|---|
| `assets/` | Freigegebene Spiel-Assets |
| `test_assets/` | Vorbereitete Kandidaten und benötigte Ressourcen für Godot-Tests |
| `scenes/` | Anwendung, Titel, Menü und künftig finale Spielszenen |
| `test_scenes/` | Testlabor, Prototypen, Szenenskripte und Testhilfen |

Die bereits angelegte gemeinsame Grundstruktur ist mit `.gitkeep` auch für
frische Git-Checkouts gesichert. Dateien wurden vor dem Verschieben auf
Zielkollisionen geprüft. Alle 129 weiterhin benötigten PNGs, sieben SVGs und
48 mitgeführten Script-UIDs sind gegenüber dem Ausgangsbestand bytegleich.
Auch die 136 Textur-UIDs und ihre Importoptionen sind erhalten.

## Wo die bisherigen Inhalte jetzt liegen

| Bisher | Jetzt, relativ zu `game/` |
|---|---|
| `tests/assets/characters/heroes/green_hero/` | `test_assets/characters/heroes/greenhero/` |
| `tests/assets/characters/sools/` | `test_assets/characters/npc/sools/` |
| `tests/assets/prototypes/portal_lab/` | `test_assets/environment/locations/portal_lab/` |
| `tests/assets/prototypes/scale_references/` | `test_assets/environment/scale_references/` |
| `tests/assets/prototypes/world_states/` | `test_assets/environment/world_states/` |
| `scenes/dev/` | `test_scenes/visual_lab/` |
| `scenes/dev/portal_lab/` | `test_scenes/environment/portal_lab/` |
| `scenes/gameplay/hero_room.*` | `test_scenes/environment/hero_room.*` |
| `scenes/gameplay/hero/` | `test_scenes/characters/heroes/greenhero/` |
| `scenes/gameplay/guide/` | `test_scenes/characters/npc/guide/` |
| `tests/runtime/` und `tests/fixtures/` | `test_scenes/helpers/runtime/` und `test_scenes/helpers/fixtures/` |
| `tests/bootstrap_integration_test.gd` | `test_scenes/helpers/bootstrap_integration_test.gd` |

Das einzelne `testImage.png` gehört jetzt zu den Maßstabsproben. Der bisherige
Ordner `game/tests/` wird nicht mehr verwendet. Ressourcen, Texturimporte,
Manifeste, Generatorziele, Tests und aktive Dokumentationspfade wurden
nachgeführt. Die vier benötigten Heldenvarianten HD, Pixel Art, Ultra und Test
bleiben getrennte, auswählbare Pakete mit ihren bisherigen Aktionsordnern.

## Quellen auf dem USB-Stick

Dein Ablauf ist jetzt in der Projektdokumentation beschrieben:

**USB-Workspace → technische Prüfung → `test_assets` → Godot-Spieltest →
Freigabe → `assets`.**

192 entbehrliche Quell-PNGs wurden aus dem Projekt entfernt: 128 identische
Kopien verwendeter Bilder und 64 nicht verwendete Rasteralternativen oder
ersetzte Fassungen. Die zugehörigen 192 Importdateien sind ebenfalls entfernt.
Die verwendeten Bilder und ihre Prüfsummen bleiben erhalten.

Für neue Green-Hero-Testbilder den vorbereiteten Kandidatenordner auf dem
USB-Stick ausdrücklich angeben. Im Paketordner `test_assets/characters/heroes/greenhero/test/`:

```sh
./rename_test_assets.sh --source-dir "$candidate_dir" --dry-run
./rename_test_assets.sh --source-dir "$candidate_dir"
```

`candidate_dir` setzt du lokal auf deinen externen Kandidatenordner. Das
Skript schreibt ausschließlich die benötigten Laufzeitdateien und Ressourcen
ins Testpaket. Es legt keine Quellkopien, Analyseberichte oder Archive im
Godot-Projekt an. Bei Fehlern werden die vorherigen Dateien wiederhergestellt.
Eine automatische finale Freigabe gibt es dadurch nicht.

## In Godot

Das Projekt weiterhin über `game/project.godot` öffnen. Im Editor funktionieren
Heldenraum und visuelles Testlabor über das Menü. Das Labor lässt sich auch
über `test_scenes/visual_lab/visual_lab.tscn` öffnen; die zusätzliche Registrierung
liegt unter `test_scenes/helpers/development_routes.tres`.

Große Texturen werden nacheinander importiert. Der erste parallele Import
überschritt das Speicherlimit dieser Sitzung. Die Einstellung beeinflusst
nur die Importparallelität, nicht Bildauflösung oder Qualität.

## Exporte

Unter **Projekt → Exportieren → Ressourcen** sind die Presets **Linux**,
**Windows** und **macOS** eingestellt. Alle verwenden denselben Ausschluss:

```text
test_assets/*,test_scenes/*,tests/*,tools/*,*.md,*.sh
```

Neue Testdateien werden damit ebenfalls ausgeschlossen. Die Testordner besitzen
keine `.gdignore`, damit Godot sie für Editor-Tests laden kann. Für Debug-Exporte
mit diesen Presets gelten dieselben Filter.

Der Release-Start lädt nur Titel und Menü. Weil noch kein Spielabschnitt mit
freigegebenen Assets existiert, ist „Neues Spiel“ dort deaktiviert und das
Labor ausgeblendet. Im Editor bleiben beide Prototypen verfügbar.

## Dokumentation und Prüfungen

Die verbindliche Beschreibung steht in
[Asset-Ablage und Freigabe](../docs/system/development/architecture/asset-ablage-und-freigabe.md).
Der [Arbeitsplan](../docs/system/development/plans/godot-asset-und-teststruktur.md)
hält die tatsächlich ausgeführten Prüfungen und verbleibende Befunde fest.
Die Anleitungen zu Heldenimporten, Labor und Godot-Ressourcenimporten wurden
aktualisiert. Historische Arbeitspläne beschreiben weiterhin den damaligen Stand.

Die zusätzlichen Informationen zu Asset-IDs, Kandidatenversionen,
`asset.yml`, Freigabestatus und einem späteren `EtherAsset`-Werkzeug sind als
Ausblick festgehalten. Ein solches Werkzeug wurde in dieser Umstellung nicht
neu eingeführt.

Der Abschlusscheck wurde ausgeführt: Doctor, Quellstil und Godot-Import
bestanden. 235 Python-Tests bestanden; zwei Dokumentationstests scheitern
bereits im ursprünglichen Stand an fehlenden Entscheidungsdokumenten.
Die umfassenden Godot-Tests melden dieselben 427 fehlgeschlagenen Assertionen
wie eine separat geprüfte Kopie des Ausgangsstands, vor allem zu abweichenden
Kamera-, Grafik- und Bewegungsstandards. Die Umstellung fügt keine weitere hinzu.

Die vier gezielten Godot-Suiten für Routing, Anwendungsstart, Animationen und
Testposen bestanden. Alle drei Export-Datenpakete wurden auf ausgeschlossene
Testinhalte geprüft und außerhalb des Projekts gestartet. Native Programme
für Linux, Windows und macOS wurden dabei nicht gebaut.
