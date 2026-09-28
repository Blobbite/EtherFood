# Asset Studio entwickeln und starten

## Geprüfte Umgebung

Python 3.11.2, pytest 8.4.2, jsonschema 4.26.0, Pillow 12.1.1,
PySide6 6.10.2 auf Linux x86-64. Andere Plattformen sind noch nicht abgenommen.
Versionen sind im separaten `tools/AssetManager/pyproject.toml` fixiert.
Der bestehende `g2dtool` benötigt dadurch kein Qt.

Die offiziellen Veröffentlichungen wurden vor Installation geprüft:
[PySide6](https://pypi.org/project/PySide6/6.10.2/),
[Pillow](https://pypi.org/project/pillow/12.1.1/),
[jsonschema](https://pypi.org/project/jsonschema/4.26.0/).
Qt-Desktop benötigt zusätzlich die jeweiligen Systembibliotheken; hier
fehlten EGL, GL, XKB und D-Bus. Die Containerprüfung verwendet isoliert
entpackte Pakete aus den konfigurierten Debian-Bookworm-Quellen, keine
mitgelieferten Binärdateien im Repository. Ein normaler Desktop benötigt
eine funktionierende Qt-Plattformintegration (X11/Wayland/Windows/macOS).

## Zentrale Steuerung über Control

Voraussetzung: Python ab 3.11 mit `venv`/`ensurepip`. Vom Repository-Stamm:

```sh
python3 tools/control.py asset-manager run
```

Unter Windows entsprechend `py -3.11 tools/control.py asset-manager run`.
Control verwendet automatisch `.venv/bin/python` beziehungsweise
`.venv\Scripts\python.exe`, unabhängig von einer Shell-Aktivierung. Fehlt die
Umgebung, wird sie beim ersten Start angelegt. Fehlende oder abweichende
Studio-Pakete werden anhand des vorhandenen `pyproject.toml` lokal installiert.
Sind Versionen und Checkout bereits passend, erfolgt kein erneuter pip-Aufruf.
Der erste Start benötigt für Installation/Build-Abhängigkeiten normalerweise
Internetzugriff. Control verwendet keine systemweite pip-Installation.

| Befehl nach `python3 tools/control.py asset-manager` | Wirkung |
| --- | --- |
| `run` | Umgebung bei Bedarf vorbereiten, Qt-Plattform prüfen und Oberfläche öffnen |
| `run --project /pfad/zum/studio-projekt` | Einen vorhandenen Verwaltungskatalog öffnen |
| `install` | Lokale Umgebung vorbereiten und Python-/Qt-Modulimporte prüfen, kein Fenster öffnen |
| `import` | Alias für `install`: Tool-Vorbereitung, ausdrücklich kein Import von Spielassets |
| `doctor` | `.venv`, Python, pip, festgelegte Paketversionen, Checkout und native Modulimporte nur prüfen |
| `test` | Studio-Tests einschließlich GUI mit `QT_QPA_PLATFORM=offscreen` ausführen |
| `pipeline-test` | Bestehende PyGameTools- und Auflösungspipeline-Tests mit Testdaten ausführen |
| `check` | Umgebung prüfen, danach Studio- und Pipeline-Tests ausführen |
| `--help` | Alle Befehle anzeigen; jeder Unterbefehl besitzt ebenfalls `--help` |

Ohne Unterbefehl startet `asset-manager` wie `asset-manager run`.
`assetmanager` ist ein gleichwertiger Schreibweisen-Alias.
`run`, `install`, `import`, `test`, `pipeline-test` und `check` unterstützen
`--dry-run`: nur Befehle anzeigen, keine Prozesse starten oder Dateien ändern.
`test --core`, `check --core`, `doctor --core` und `install --core` lassen Qt
bewusst weg. Core-Tests schließen die GUI-Tests ausdrücklich aus;
`pipeline-test` benötigt ebenfalls weder Qt noch Godot.

## Diagnose und Fehlerbehandlung

`doctor` installiert nichts und benötigt noch keinen Studio-Projektordner.
Fehlende `.venv`/Pakete ergeben Exit-Code 1 mit Einrichtungshinweis. Mit
`doctor --config /pfad/zum/projekt/project.studio-local.json` werden zusätzlich
die projektspezifischen Wurzeln geprüft: `TOOL_ROOT`, `WORKSPACE_ROOT`,
`VERSIONS_ROOT` und `GODOT_ROOT`. Unkonfigurierte Wurzeln bleiben dabei
sichtbar als fehlend; die erste Sichtprüfung darf dennoch ohne sie erfolgen.
Absolute Rechnerpfade stehen ausschließlich in der ignorierten lokalen Datei.

Installierte PySide6-Pakete bedeuten noch nicht, dass native Bibliotheken oder
das Desktop-Display funktionieren. `doctor` zeigt beispielsweise die konkret
fehlende `libGL.so.1`. `run` prüft zusätzlich die echte Qt-Plattform in einem
separaten Prozess, bevor das Studio startet. `test`/`check` prüfen vorher die
Offscreen-Plattform; ein Qt-Fehler darf nicht als erfolgreich übersprungener
GUI-Test gelten. Systembibliotheken, Betriebssystempakete und ein Display
werden **nicht** automatisch installiert oder konfiguriert.

Eine defekte, veraltete oder nach außen verlinkte `.venv` wird nicht gelöscht
oder automatisch neu erstellt. Bei fehlendem `venv`/`ensurepip` zuerst die
Python-Installation reparieren (unter Debian/Ubuntu etwa `python3-venv`).
Nach Netzwerk-/pip-Fehlern kann derselbe Befehl erneut ausgeführt werden;
Studio und Tests starten erst nach erfolgreicher Vorbereitung. Testfehler
werden als Fehlercode zurückgegeben. `check` führt beide Testsuiten aus und
bleibt auch dann fehlerhaft, wenn nur die erste Suite fehlschlägt.

Die direkte `tools/AssetManager/studio.py`-CLI bleibt für Entwicklung verfügbar,
übernimmt selbst aber keine automatische Einrichtung. Der zentrale Einstieg
und seine Bootstrap-Tests liegen unter `tools/src/g2dtool/asset_manager*.py`
und `tools/tests/test_asset_manager_control.py`.

Der GUI-Bereich ist seit Paket 4 verfügbar; alle Bildfixtures sind synthetisch
und temporär. Der davon unabhängige vollständige Repo-Check bleibt
`python3 tools/control.py check`: Er prüft zusätzlich den bestehenden
Spielbestand und benötigt Godot. Ein erfolgreicher Studio-Check ist weder
Spielabnahme noch Freigabe einer Bildpipeline oder Godot-Bereitstellung.

## Speicherung und Wiederaufnahme

Katalog: `*.studio.sqlite`, lokale Wurzeln: `*.studio-local.json`, importierte
Bytes: `.asset-studio/objects/<hash-prefix>/<sha256>`. SQLite-Migrationen
erzeugen `*.studio-backup-*` mit der SQLite-Backup-API, bevor sie starten.
Ein veralteter Editor erhält einen Konflikt; er überschreibt nichts.

Importjournal: `planned` → `copying` → `copied` → `registered`.
Fehler bleiben als `interrupted` sichtbar. `BlobStore.integrity()` liest
Hashes, fehlende/verwaiste Blobs und temporäre Dateien, löscht aber nichts.
Nach einem Abbruch kann dieselbe Quelle erneut importiert werden; vollständige
Blobs werden dedupliziert. Ein beschädigter Teilblob wird nicht überschrieben:
zuerst Fund und Journal prüfen, anschließend gezielte manuelle Recovery.
Kein Netzlaufwerk-Multiwriter und keine automatische Dateibereinigung.

`Catalog.export_snapshot()` exportiert ausschließlich Metadaten. Der Import
ist nur in einen neuen leeren Katalog erlaubt. Nicht enthaltene Originalbytes
müssen separat geprüft bereitgestellt werden. Fremde Prüf-/Freigabe-/Deployment-
Datensätze werden nicht übernommen; importierte Revisionen bleiben ungeprüft.
