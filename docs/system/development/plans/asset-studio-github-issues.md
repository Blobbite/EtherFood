<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Asset Studio: zusammenhängende GitHub-Issues

## Zweck und Gesamtbild

Den vorhandenen `EtherFood_Codex_Aufgabenplan` als nachvollziehbare,
deutschsprachige GitHub-Roadmap für das lokale Asset- und Verwaltungswerkzeug
veröffentlichen. Ein Hauptissue, sechs Phasen und 48 Aufgaben bilden eine
echte Unterissue-Hierarchie. Titel beginnen mit einem passenden Emoji.

## Ausgangslage

- Repository: `Blobbite/EtherFood`, Branch `main`.
- Plan im aktuellen Arbeitsbaum:
  `tools/AssetManager/works/EtherFood_Codex_Aufgabenplan/`.
- Bestehende Pipelines: `tools/AssetManager/PyGameTools/`.
- Die lokale Verschiebung ist noch nicht committed. Der veröffentlichte
  Planstand ist im Commit `59ae32d23e0c18075d6837c35895aa82c08682cd` unter
  `docs/works/EtherFood_Codex_Aufgabenplan/` erreichbar.
- Bei Beginn waren keine offenen oder geschlossenen Repository-Issues und
  keine Meilensteine vorhanden. Die 48 Planaufgaben stehen auf `not_started`.

## Umfang und Nicht-Ziele

Veröffentlicht werden Aufgaben, Tests, Abnahmekriterien, Voraussetzungen und
Phasenabschlüsse einschließlich der Einbindung in das bestehende Godot-Projekt.
Die Erstellung der Issues implementiert keine Planaufgabe und erteilt keine
Asset-Freigabe. Bestehende Arbeitsbaumänderungen werden weder committed noch
verändert. Die Dokumentation bleibt unter `docs/system/`; die Planvorschläge
`docs/asset-studio/` werden entsprechend angepasst.

## Schritte und Fortschritt

- [x] Repository, Authentifizierung, vorhandene Issues und lokale Pfade prüfen.
- [x] Alle Aufgabeninhalte, Anforderungsabdeckung und Abhängigkeiten aufbereiten.
- [x] Hauptissue, sechs Phasen, 48 Aufgaben und Meilensteine veröffentlichen.
- [x] Unterissues, Voraussetzungen und Navigation miteinander verbinden.
- [x] Veröffentlichte Inhalte und sämtliche Beziehungen erneut abrufen und prüfen.

## Erkenntnisse und Entscheidungen

- Die Hierarchie ist `Hauptissue → Phase → Aufgabe`; fachliche Voraussetzungen
  werden getrennt von dieser organisatorischen Zuordnung abgebildet.
- Unfreigegebene Engine-Assets bleiben unter `game/test_assets/`, Tests unter
  `game/test_scenes/`; Freigaben übernehmen die geprüften relativen Assetpfade
  nach `game/assets/`. T035 klärt den Loadervertrag anhand des Bestands.
- Das Werkzeug wird als lokale Python-Anwendung mit Godot-Anbindung geplant;
  es wird keine zusätzliche Web- oder Cloud-Infrastruktur vorausgesetzt.
- Die bisherigen Ignore-Regeln nennen noch `tools/PyGameTools/`. Die Folgen
  der lokalen Verschiebung werden in Bestandsaufnahme und Git-Aufgabe erfasst,
  bevor generierte Bildbestände versehentlich versioniert werden.
- Dauerhafte Quellenlinks zeigen auf den veröffentlichten Commit. Die
  Beschreibungen nennen zusätzlich die aktuellen lokalen Pfade.

## Prüfungen

Die lesende Planprüfung (`python3 pruefung/check_plan.py --json`) ist bestanden:
48 Aufgaben, 36 Anforderungen, 955 lokale Links und 81 Dateihashes. Die
Veröffentlichungsvorbereitung hat sechs Phasen mit je acht Aufgaben, 227
azyklische Voraussetzungen und 384 übernommene Test-/Abnahmepunkte geprüft.
Alle 48 Originalaufträge stimmen bytegenau mit dem gepinnten GitHub-Commit
überein. Es sind 55 Issue-Beschreibungen vorbereitet; die veröffentlichten
Inhalte und Beziehungen wurden anschließend vollständig mit GitHub abgeglichen.
Der erneute API-Abruf bestätigt ohne Abweichungen:

- 55 offene Issues mit den vorbereiteten Titeln und vollständigen Beschreibungen;
- 54 Eltern-Kind-Beziehungen einschließlich der richtigen Reihenfolge;
- 227 Aufgabenabhängigkeiten in der richtigen Richtung;
- sechs Meilensteine mit je einer Phase und acht Aufgaben;
- 69 unterschiedliche Quellenlinks auf vorhandene Dateien im gepinnten Commit.

`git diff --check -- docs/system/development/plans` war erfolgreich.
Anwendungstests werden für diesen reinen Planungsauftrag nicht als ausgeführt
oder bestanden dargestellt.

## Wiederholbarkeit und Wiederherstellung

Issues werden anhand stabiler Plan-IDs zugeordnet. Vor jedem erneuten Anlegen
werden bestehende Zuordnungen geprüft. Die temporären Veröffentlichungsdaten
liegen ausschließlich unter `/run/codex-session/`; sie enthalten keine Tokens.
Ein unterbrochener Lauf setzt bei fehlenden Inhalten oder Beziehungen fort.
Es werden keine fremden Issues geschlossen oder gelöscht.

## Ergebnis und Rückblick

Veröffentlicht: [Hauptissue #1](https://github.com/Blobbite/EtherFood/issues/1),
sechs Phasen (#2–#7), 48 Aufgaben (#8–#55) und sechs Meilensteine.
Die 54 Eltern-Kind-Beziehungen und 227 Voraussetzungen sind angelegt; Hauptissue
und Phasen besitzen vollständige Übersichtslinks. Der abschließende
GitHub-Abgleich ist erfolgreich. Neun ergänzende Labels kennzeichnen Vorhaben,
Phasen, Aufgaben und betroffene Arbeitsbereiche.

| Phase | GitHub-Issue | Aufgaben | Meilenstein |
| --- | --- | --- | --- |
| 🏗️ A: Grundlagen | [#2](https://github.com/Blobbite/EtherFood/issues/2) | T001–T008, #8–#15 | [Phase A](https://github.com/Blobbite/EtherFood/milestone/1) |
| 🖥️ B: Dashboard | [#3](https://github.com/Blobbite/EtherFood/issues/3) | T009–T016, #16–#23 | [Phase B](https://github.com/Blobbite/EtherFood/milestone/2) |
| 🎨 C: Verarbeitung | [#4](https://github.com/Blobbite/EtherFood/issues/4) | T017–T024, #24–#31 | [Phase C](https://github.com/Blobbite/EtherFood/milestone/3) |
| 🔍 D: Variantenprüfung | [#5](https://github.com/Blobbite/EtherFood/issues/5) | T025–T032, #32–#39 | [Phase D](https://github.com/Blobbite/EtherFood/milestone/4) |
| 🎮 E: Godot-Integration | [#6](https://github.com/Blobbite/EtherFood/issues/6) | T033–T040, #40–#47 | [Phase E](https://github.com/Blobbite/EtherFood/milestone/5) |
| 🏁 F: Betrieb und Pilot | [#7](https://github.com/Blobbite/EtherFood/issues/7) | T041–T048, #48–#55 | [Phase F](https://github.com/Blobbite/EtherFood/milestone/6) |

Einstieg: [T001 / #8](https://github.com/Blobbite/EtherFood/issues/8).
Alle Implementierungsaufgaben bleiben offen; die Veröffentlichung der Roadmap
setzt weder ihren Bearbeitungsstand noch einen Asset-Freigabestatus auf erledigt.
