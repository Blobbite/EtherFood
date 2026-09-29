# EtherFood

<!-- PYGINDEX:README START -->
## Dokumentation
- [Dokumentationsübersicht](docs/index.md)
- [EtherFood – Spiel](docs/game/index.md)
- [Release](docs/release/index.md)
- [System – Technik und Entwicklung](docs/system/index.md)

## Projektdateien
- [Repository-Regeln für EtherFood](AGENTS.md)
- [Änderungsprotokoll](CHANGELOG.md)
- [Mitarbeit an EtherFood](CONTRIBUTING.md)
- [Sicherheitsrichtlinie](SECURITY.md)
<!-- PYGINDEX:README END -->

Ein Top-down-Action-RPG über den Wiederaufbau einer verlorenen Welt, die
Rückkehr ihrer Zivilisationen und vergessene Erinnerungen. `EtherFood`
befindet sich in der Konzept- und Vorproduktionsphase.

Die Dokumentation ist in
[System und Entwicklung](docs/system/index.md),
[Spiel](docs/game/index.md) und
[Release](docs/release/index.md) gegliedert. Kanon, Gamedesign, unfertige
Konzepte und Referenzen besitzen im Spielbereich getrennte Aufgaben. Die
übrige Projektdokumentation wird ebenfalls auf Deutsch geführt. Nur die
unverändert bewahrte Forge2D-Vorlage bleibt als englische technische und
historische Referenz erhalten.

## Technischer Einstieg

Das Repository verwendet Godot 4 und die geerbten Forge2D-Werkzeuge. Die
wichtigsten Befehle sind:

- Version: `0.1.0`

```text
python tools/control.py install --dry-run
python tools/control.py install --yes
python tools/control.py doctor
python tools/control.py style
python tools/control.py check
python tools/control.py godot4 import
python tools/control.py godot4 run
python tools/control.py godot4 test
```

`godot4 import` erzeugt den ignorierten Godot-Ressourcen-Cache aus den
getrackten Quell-Assets. `run`, `test` und `check` führen diese Vorbereitung
automatisch aus; ein frischer Checkout benötigt deshalb keinen eingecheckten
`game/.godot`-Ordner. Details und Fehlerdiagnose stehen unter
[Godot-Ressourcenimporte](docs/system/development/tooling/godot-resource-imports.md).

Auf Systemen ohne `python` kann `python3` beziehungsweise unter Windows
`py -3.11` verwendet werden. Abhängigkeiten gehören in die lokale `.venv` und
nicht in die systemweite Python-Installation.

## Asset Manager starten

Der Asset Manager (`EtherFood Asset Studio`) verwaltet Projekte, Assets,
Dokumente und Aufgaben. Er wird ebenfalls zentral über Control gesteuert:

```sh
python tools/control.py asset-manager run
python tools/control.py asset-manager doctor
python tools/control.py asset-manager install
python tools/control.py asset-manager upgrade
python tools/control.py asset-manager install --dry-run
python tools/control.py asset-manager import
python tools/control.py asset-manager test
python tools/control.py asset-manager pipeline-test
python tools/control.py asset-manager check
```

`run` legt beim ersten Start eine fehlende `.venv` an, ergänzt bei Bedarf pip,
installiert die benötigten Python-Pakete darin und öffnet das Studio. Eine
manuelle Aktivierung entfällt; spätere Starts verwenden die passende Installation
wieder. `install` repariert ebenfalls fehlendes pip in einer vorhandenen `.venv`.
`upgrade` aktualisiert pip über `ensurepip` und installiert die im Projekt
festgelegten Studio-Paketversionen mit `--upgrade`. `doctor` prüft nur
und meldet fehlende Pakete oder Qt-Systembibliotheken. `import` bereitet wie
`install` nur die Tool-Umgebung samt Python-Modulen vor, **keine Spielgrafiken**.
`test` prüft das Studio einschließlich Oberfläche ohne sichtbares Fenster;
`check` ergänzt die vorhandenen Pipeline-Tests. Ohne Qt: `test --core`.

Für den ersten Start „Neues Projekt“ mit einem leeren Testordner außerhalb
des Repositorys wählen, danach „Demo anlegen“.
Unter **Verarbeitung → Ablaufeditor** lassen sich Python-Bausteine und
Werkzeugpakete zu Abläufen verbinden, bearbeiten, ausführen und vollständig
importieren/exportieren. Bibliotheken liegen in getrennten Projektumgebungen.
Die [Bedienung](docs/system/development/asset-studio/PIPELINES.md),
[Python-Schnittstelle und Ablage](docs/system/development/asset-studio/SKRIPTPAKETE.md)
sowie [Umbau und Prüfungen](docs/system/development/plans/asset-studio-ablaufeditor.md)
beschreiben den aktuellen Stand.
Godot-Bereitstellung und persönliche Desktop-Abnahme bleiben getrennt offen;
die bisherigen Studio-Roadmaps sind historische Nachweise.
Befehle und Voraussetzungen (einschließlich Qt-Systembibliotheken) stehen unter
[Entwicklung und Start](docs/system/development/asset-studio/DEVELOPMENT.md),
die Klickfolge unter [Erste Sichtprüfung](docs/system/development/asset-studio/SICHTPRUEFUNG.md).

## Mitarbeit

Kanon- und Handlungsdokumentation wird während der Konzeptphase direkt auf
`main` gepflegt. Spätere Spielentwicklung erfolgt über Arbeitszweige und Pull
Requests mit CI-Prüfungen. Details stehen in [CONTRIBUTING.md](CONTRIBUTING.md).
Sicherheitsprobleme gehören nicht in öffentliche Issues; der vertrauliche Weg
ist in [SECURITY.md](SECURITY.md) beschrieben.

Das Projekt steht unter der [MIT-Lizenz](LICENSE).
