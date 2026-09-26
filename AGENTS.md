# Repository-Regeln für EtherFood

Beginne bei der [Dokumentationsübersicht](docs/index.md).

- Die Dokumentation besitzt genau drei aktive Oberbereiche:
  [`system`](docs/system/index.md), [`game`](docs/game/index.md) und
  [`release`](docs/release/index.md).
- Der deutsche Spielkanon unter
  [`docs/game/canon/`](docs/game/canon/index.md) und das Gamedesign unter
  [`docs/game/design/`](docs/game/design/index.md) sind die einzigen aktuellen
  Quellen für Welt, Handlung und Spielregeln.
- [`docs/game/concept/`](docs/game/concept/index.md) enthält unverbindliche
  Ideen und Vorschläge. Inhalte daraus werden erst nach einer bewussten
  Übernahme in Kanon oder Design verbindlich.
- Die Projektdokumentation wird auf Deutsch geführt. Code, Befehle, Pfade und
  technische Bezeichner dürfen Englisch bleiben.
- Die geerbte
  [Forge2D-Grundlage](docs/system/.forge2d-template/index.md) bleibt
  unverändert auf Englisch und dient nur als technische und historische
  Referenz.
- Halte die Dokumentation einfach, verständlich und nah an der tatsächlichen
  Entwicklung. Führe keine zweite Konzeptfassung und keinen Sprachspiegel.
- Änderungen an bereits angenommenem Kanon oder Gamedesign benötigen eine
  nachvollziehbare Entscheidung unter `docs/game/decisions/`.
- Komplexe technische Arbeiten verwenden fortlaufend gepflegte Pläne unter
  `docs/system/development/plans/` und folgen
  [`.agent/PLANS.md`](.agent/PLANS.md).
- Aktualisiere Tests und passende Dokumentation, wenn sich Verhalten ändert.
  Es gelten die geerbten Python- und GDScript-Stilregeln.
- Assets ohne finale Freigabe liegen unter `game/test_assets/`. Godot-Testszenen
  und Testhilfen liegen unter `game/test_scenes/`. Erst final
  freigegebene und ins Spiel übernommene Dateien werden nach `game/assets/`
  verschoben. Die Verwendung in Prototypszenen ist keine Freigabe; siehe
  [Asset-Ablage und Freigabe](docs/system/development/architecture/asset-ablage-und-freigabe.md).
- Verwende keine zerstörerischen Git-Befehle, übernimm keine Geheimnisse und
  füge keine ungeprüften Abhängigkeiten hinzu. Generierte Caches, Binärdateien
  und lokale Rechnerpfade gehören nicht ins Repository.
- Führe zuerst die schnellsten passenden Prüfungen aus. Der vollständige
  Standardlauf ist `python tools/control.py check`. Melde nur tatsächlich
  ausgeführte Prüfungen.
