# Asset Studio entwickeln und starten

## Geprüfte Umgebung

Python 3.11.2, pytest 8.4.2, jsonschema 4.26.0, Pillow 12.1.1,
PySide6 6.10.2 auf Linux x86-64. Andere Plattformen sind noch nicht abgenommen.

`--core` lässt Qt weg, führt aber auch die Tests der Markdown-Bearbeitung aus.
Daher gehört das bereits für die Oberfläche verwendete `markdown-it-py==4.0.0`
ebenfalls zu den Testabhängigkeiten und wird von `control.py` mit vorbereitet.
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
Umgebung, wird sie beim ersten Start angelegt. Fehlt darin pip, ergänzt Control
es nach erfolgreicher Interpreterprüfung mit `ensurepip --upgrade`. Das gilt
auch für eine bereits vorhandene `.venv`. Fehlende oder abweichende Studio-Pakete
werden anhand des vorhandenen `pyproject.toml` lokal installiert.
Sind Versionen und Checkout bereits passend, erfolgt kein erneuter pip-Aufruf.
Der erste Start benötigt für Installation/Build-Abhängigkeiten normalerweise
Internetzugriff. Control verwendet keine systemweite pip-Installation.

| Befehl nach `python3 tools/control.py asset-manager` | Wirkung |
| --- | --- |
| `run` | Umgebung bei Bedarf vorbereiten, Qt-Plattform prüfen und Oberfläche öffnen |
| `run --project /pfad/zum/studio-projekt` | Einen vorhandenen Verwaltungskatalog öffnen |
| `install` | Lokale Umgebung vorbereiten, fehlendes pip ergänzen und Python-/Qt-Modulimporte prüfen |
| `upgrade` | pip mit `ensurepip` aktualisieren, Studio-Pakete mit `--upgrade` installieren und Modulimporte prüfen |
| `import` | Alias für `install`: Tool-Vorbereitung, ausdrücklich kein Import von Spielassets |
| `doctor` | `.venv`, Python, pip, festgelegte Paketversionen, Checkout und native Modulimporte nur prüfen |
| `test` | Studio-Tests einschließlich GUI mit `QT_QPA_PLATFORM=offscreen` ausführen |
| `pipeline-test` | Bestehende PyGameTools- und Auflösungspipeline-Tests mit Testdaten ausführen |
| `check` | Umgebung prüfen, danach Studio- und Pipeline-Tests ausführen |
| `--help` | Alle Befehle anzeigen; jeder Unterbefehl besitzt ebenfalls `--help` |

Ohne Unterbefehl startet `asset-manager` wie `asset-manager run`.
`assetmanager` ist ein gleichwertiger Schreibweisen-Alias.
`run`, `install`, `upgrade`, `import`, `test`, `pipeline-test` und `check` unterstützen
`--dry-run`: nur Befehle anzeigen, keine Prozesse starten oder Dateien ändern.
Auch die bedingte pip-Reparatur erscheint dabei als geplanter Befehl.
`test --core`, `check --core`, `doctor --core`, `install --core` und
`upgrade --core` lassen Qt bewusst weg. Core-Tests schließen die GUI-Tests ausdrücklich aus;
`pipeline-test` benötigt ebenfalls weder Qt noch Godot.

### Installieren, reparieren und aktualisieren

Die komplette Einrichtung bleibt innerhalb von Control:

```sh
python3 tools/control.py asset-manager install
python3 tools/control.py asset-manager run
```

`install` ergänzt fehlendes pip und fehlende oder abweichende Studio-Pakete.
`run` erledigt dieselbe Vorbereitung bei Bedarf auch allein. Eine bereits
passende Installation wird wiederverwendet.

Für eine ausdrückliche Aktualisierung:

```sh
python3 tools/control.py asset-manager upgrade
```

`upgrade` führt `ensurepip --upgrade` mit dem Interpreter der Repository-`.venv`
und danach `pip install --upgrade` für das Studio aus. pip wird dabei auf
mindestens den mit dieser Python-Installation ausgelieferten Stand gebracht;
eine neuere installierte Version bleibt erhalten. Für Studio-Pakete gelten
weiterhin die Versionsvorgaben in `tools/AssetManager/pyproject.toml`.
`install` und `upgrade` öffnen kein Fenster. Nach der Einrichtung startet
`asset-manager run` die Oberfläche.

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

Fehlendes pip wird bei der Vorbereitung automatisch ergänzt; `doctor` verweist
dafür auf `asset-manager install`. Eine strukturell defekte, mit nicht
unterstütztem Python erstellte oder nach außen verlinkte `.venv` wird nicht
gelöscht oder automatisch neu erstellt. Fehlt auch das Python-Modul `ensurepip`,
meldet Control den Fehler und stoppt. In diesem Fall zuerst die
Python-Unterstützung für `venv`/`ensurepip` ergänzen (unter Debian/Ubuntu etwa
`python3-venv`) und denselben Control-Befehl erneut ausführen.
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
Kein Netzlaufwerk-Multiwriter. Der 30-Tage-Papierkorb bereinigt ausschließlich
zugehörige verwaltete Daten bei geöffnetem Projekt; Archiv und getrennte
Sicherungen werden dabei nicht automatisch gelöscht.

`Catalog.export_snapshot()` exportiert ausschließlich Metadaten. Der Import
ist nur in einen neuen leeren Katalog erlaubt. Nicht enthaltene Originalbytes
müssen separat geprüft bereitgestellt werden. Fremde Prüf-/Freigabe-/Deployment-
Datensätze werden nicht übernommen; importierte Revisionen bleiben ungeprüft.


## Prüfungen des Umbaus auf zwei Haupteditoren

Der [laufend gepflegte Arbeitsplan](../plans/asset-studio-zwei-editoren-und-automatik.md)
nennt tatsächliche Ergebnisse und getrennte Ausgangsfehler. Gezielte neue
Prüfungen betreffen `test_pipeline_workspace.py`, `test_pipeline_execution.py`,
`test_workspace_migration.py`, `test_workspace_exchange.py`,
`test_lifecycle_service.py` und `test_workspace_demo.py`. Echte Qt-Ereignisse
stehen unter `gui/test_two_editors.py`, `gui/test_pipeline_automation.py` und
`gui/test_workspace_storage_search.py`.

Ausführungstests starten echte kontrollierte Pythonprozesse in temporären
Projekten. Migrationstests unterbrechen gezielt das SQL-/Dateijournal. Die
Papierkorbfrist verwendet eine steuerbare UTC-Uhr. Bild-/GIF-Fixtures sind
synthetisch; fremde Projektordner werden nicht für destruktive Tests verwendet.
Alte ausschließlich auf die entfernte Auftragsverwaltung bezogene Tests wurden
abgelöst, fachliche Quellen-, Masken-, Bild-, Dokument- und Canvasprüfungen bleiben.
