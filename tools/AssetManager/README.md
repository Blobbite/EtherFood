# EtherFood Asset Studio

Lokales Verwaltungswerkzeug neben dem bestehenden `PyGameTools/`.
Die ersten vier Arbeitspakete umfassen Katalog, sichere Dateiablage,
Projektkarten, Dokumente/Aufgaben und einen PySide6-Desktop.
Bildpipelines und Godot-Bereitstellung sind noch nicht angebunden.

Vom Repository-Stamm starten:

```sh
.venv/bin/python -m pip install -e './tools/AssetManager[test,gui]'
.venv/bin/python tools/AssetManager/studio.py gui
```

- [Entwicklung und Voraussetzungen](../../docs/system/development/asset-studio/DEVELOPMENT.md)
- [Anleitung zur ersten Sichtprüfung](../../docs/system/development/asset-studio/SICHTPRUEFUNG.md)
- [Architektur und aktueller Stand](../../docs/system/development/asset-studio/index.md)

`works/EtherFood_Codex_Aufgabenplan/` bleibt das ursprüngliche, hashgeprüfte
Auftragspaket. Der tatsächliche Umsetzungsstand steht in den GitHub-Issues,
im gepflegten Arbeitsplan und den T001–T012-Ergebnisberichten, nicht in den
ursprünglichen `not_started`-Vorlagen. Lokale Kataloge, Originalkopien und
Generatorausgaben gehören nicht nach Git.
