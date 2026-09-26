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

## Installation und CLI

Vom Repository-Stamm mit einer virtuellen Python-Umgebung:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e './tools/AssetManager[test,gui]'
.venv/bin/python tools/AssetManager/studio.py --help
.venv/bin/python tools/AssetManager/studio.py --version
.venv/bin/python tools/AssetManager/studio.py doctor
.venv/bin/python tools/AssetManager/studio.py gui
```

`doctor` schreibt nichts. Ohne lokale Konfiguration ist Exit 1 mit den
fehlenden Wurzeln/Tools korrekt, kein erfolgreicher Produktionscheck.
Optional `doctor --config <datei.studio-local.json>` mit Schema 1 und
`roots`-Objekt (`TOOL_ROOT`, `WORKSPACE_ROOT`, `VERSIONS_ROOT`, `GODOT_ROOT`).
Absolute Maschinenpfade stehen ausschließlich in dieser ignorierten Datei.

```sh
.venv/bin/python -m pytest -q tools/AssetManager/tests --ignore=tools/AssetManager/tests/gui
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tools/AssetManager/tests/gui
.venv/bin/python -m pytest -q tools/AssetManager/PyGameTools/.tests tools/AssetManager/PyGameTools/Pipline/2-SpritesheetResolution-Pipline/tests
.venv/bin/python tools/control.py check
```

Der GUI-Bereich ist seit Paket 4 verfügbar. Ohne GUI-Abhängigkeit bleiben dessen
Tests ausdrücklich übersprungen; Core-Tests benötigen kein Qt. Alle
Bildfixtures sind synthetisch und temporär. Der vollständige Repo-Check
prüft zusätzlich den bestehenden Spielbestand und benötigt Godot.

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
