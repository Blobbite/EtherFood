<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Asset-Ablage und Freigabe

## Verbindliche Ablage

Das Godot-Projekt liegt unter `game/`; dort befindet sich `project.godot`.
Der separate `EtherFood_Workspace` auf dem USB-Stick dient der Vorbereitung.
Sein lokaler Gerätepfad wird nicht im Repository gespeichert.

| Bereich | Inhalt |
|---|---|
| Externer USB-Workspace | Rohmaterial, KI-Zwischenstände, Variantenarchive, Analysen und Prüfberichte |
| `game/test_assets/` | Vorbereitete Assets für die Prüfung in Godot, einschließlich benötigter Manifeste und Ressourcen |
| `game/test_scenes/` | Prototypszenen, Szenenskripte, Testhilfen und automatisierte Godot-Tests |
| `game/assets/` | Ausdrücklich final freigegebene und ins Spiel übernommene Assets |
| `game/scenes/` | Anwendung, Titel, Menü und künftig freigegebene Spielszenen |

Der Ablauf lautet: **USB-Workspace → technische Prüfung → `test_assets` →
Godot-Spieltest → bewusste Freigabe → `assets`**. Die Auswahl einer Variante
im Labor erteilt keine Freigabe. Ein bestandener automatischer Test ersetzt
weder die visuelle Beurteilung noch die Freigabe einer konkreten Version.

## Gemeinsame Struktur

`assets` und `test_assets` besitzen dieselbe vorbereitete Grundstruktur:
`characters`, `environment`, `props`, `items`, `effects`, `ui`, `audio`,
`fonts`, `shaders`, `materials`, `lighting` und `cinematics`.
Leere Zielordner bleiben durch `.gitkeep` in frischen Checkouts erhalten.

Für Green Hero ist der Name `characters/heroes/greenhero` verbindlich.
`sprites/<Aktion>/` enthält verwendete Einzelbilder,
`spritesheets/<Aktion>/` verwendete Raster und `animations/` die
Godot-Animationsressourcen. Richtungsdateien liegen gemeinsam im jeweiligen
Animationsordner; zusätzliche Richtungsordner sind nicht vorgesehen.

Beispiel für neue Laufraster:

```text
test_assets/characters/heroes/greenhero/spritesheets/run/
assets/characters/heroes/greenhero/spritesheets/run/
```

Die vier vorhandenen, weiterhin benötigten Vergleichspakete `hd`,
`pixel_art`, `ultra` und `test` liegen unter
`test_assets/characters/heroes/greenhero/`. Sie behalten ihre zusammengehörigen
Aktionsordner, Manifeste und SpriteFrames. Dadurch lassen sich die Varianten
weiter getrennt im Labor auswählen. Ihre inneren Paketpfade werden beim
Freigeben ebenfalls beibehalten; sie werden nicht miteinander vermischt.
Das Anlegen der Zielstruktur ist keine Freigabe dieser Pakete.

Portal-Grafiken liegen unter `test_assets/environment/locations/portal_lab/`,
Maßstabsproben unter `test_assets/environment/scale_references/`,
Weltzustandsproben unter `test_assets/environment/world_states/` und die Seele
unter `test_assets/characters/npc/sools/`.

## Godot-Tests und Anwendung

- Das visuelle Labor startet über
  `res://test_scenes/visual_lab/visual_lab.tscn`.
- Portalräume liegen unter `test_scenes/environment/portal_lab/`, der
  Heldenraum unter `test_scenes/environment/hero_room.tscn`.
- Die Prototypfiguren liegen unter `test_scenes/characters/`.
- `test_scenes/helpers/bootstrap_integration_test.gd` startet die
  automatisierten Laufzeittests. Der CLI-Befehl bleibt
  `python tools/control.py godot4 test`.

Die Anwendung bindet Prototypen nur in Entwicklungsstarts und nur bei
vorhandener `test_scenes/helpers/development_routes.tres` ein. Titel und Menü
haben keine festen Abhängigkeiten von Testgrafiken oder Testszenen.
Solange kein freigegebener Spielabschnitt existiert, ist „Neues Spiel“ im
Export deaktiviert. Im Editor bleiben Heldenraum und Labor erreichbar.

## Release-Export

In Godot unter **Projekt → Exportieren → Linux, Windows oder macOS →
Ressourcen** sind alle drei vorhandenen Presets vorbereitet. Der Modus bleibt
„Alle Ressourcen exportieren“. Das Ausschlussfeld enthält:

```text
test_assets/*,test_scenes/*,tests/*,tools/*,*.md,*.sh
```

Diese Verzeichnisfilter erfassen auch später hinzugefügte Testdateien und
gelten ebenso beim Debug-Export mit diesen Presets. Die zusätzliche Regel
`tests/*` verhindert, dass ein versehentlich neu angelegter früherer Testordner
mitgeliefert wird. Importskripte und persönliche Markdown-Notizen gehören
ebenfalls nicht ins Spielpaket.

Godot bietet diese Ausschlussfilter in den
[Export-Ressourcenoptionen](https://docs.godotengine.org/en/stable/tutorials/export/exporting_projects.html#resource-options).
**Keine `.gdignore` in `test_assets` oder `test_scenes` anlegen:** Die
Testressourcen müssen im Editor importierbar und mit `load()` beziehungsweise
`preload()` erreichbar bleiben; siehe
[Godot-Projektorganisation](https://docs.godotengine.org/en/stable/tutorials/best_practices/project_organization.html#ignoring-specific-folders).

## Übernahme und Arbeitsquellen

Eine Freigabe benennt die konkrete geprüfte Version und ihre Verwendung.
Danach werden die freigegebenen Dateien bei gleichem relativen Pfad von
`test_assets` nach `assets` verschoben. Ressourcenverweise, Manifeste,
Generatorziele, `.import`-Metadaten, Tests und Dokumentation werden gemeinsam
aktualisiert. Es bleibt keine zweite aktive Kopie im Testbestand.

Die 192 nicht mehr für Godot benötigten Green-Hero-Quellkopien, Rasteralternativen
und ersetzten Fassungen samt Importmetadaten wurden bei der Umstellung
entfernt. Alle verwendeten Bilder blieben bytegleich erhalten. Die aktuellen
Manifeste prüfen deren SHA-256 direkt. Künftige Importe lesen einen explizit
angegebenen externen Kandidatenordner und erzeugen weder `sources/` noch
Versionsarchive im Projekt. Die Quelldateien auf dem USB-Stick bleiben erhalten.

Die vorgeschlagenen Asset-IDs, Kandidatenversionen, Freigabestatus und ein
automatisch erzeugter Katalog sind mögliche spätere Erweiterungen. Ein
`EtherAsset`-Werkzeug oder ein allgemeiner `asset.yml`-Workflow ist derzeit
nicht implementiert; die bestehenden JSON-Manifeste bleiben maßgeblich für
die vorhandenen Heldenpakete.

PNG-Quellen für die Engine, Importmetadaten und Script-UIDs werden versioniert.
Der Cache unter `game/.godot/` bleibt lokal. Große Raster werden nacheinander
importiert (`editor/import/use_multiple_threads=false`), um Speicherspitzen
zu begrenzen; siehe [Godot-Ressourcenimporte](../tooling/godot-resource-imports.md).
Ändert eine spätere Freigabe angenommenen Kanon oder Gamedesign, benötigt sie
zusätzlich eine Entscheidung unter `docs/game/decisions/`.
