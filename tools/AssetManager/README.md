# EtherFood Asset Studio

Lokales Verwaltungswerkzeug neben dem bestehenden `PyGameTools/`.
Die ersten vier Arbeitspakete umfassen Katalog, sichere Dateiablage,
Projektkarten, Dokumente/Aufgaben und einen PySide6-Desktop.
Projektlokale Canvas-Bildpipelines sind inzwischen angebunden;
Godot-Bereitstellung und persönliche Pipeline-Abnahme bleiben getrennt offen.

Vom Repository-Stamm starten:

```sh
python3 tools/control.py asset-manager run
python3 tools/control.py asset-manager doctor
python3 tools/control.py asset-manager test
```

`run` richtet die lokale `.venv` und fehlende Python-Pakete automatisch ein;
manuelles Aktivieren ist nicht nötig. `doctor` installiert nichts.
`import`/`install` bereiten nur die Tool-Umgebung vor, nicht Spielassets.
`pipeline-test` prüft die bestehenden Bildpipelines; `check` kombiniert
Diagnose, Studio- und Pipeline-Tests. Für Tests ohne Qt: `test --core`.

- [Entwicklung und Voraussetzungen](../../docs/system/development/asset-studio/DEVELOPMENT.md)
- [Anleitung zur ersten Sichtprüfung](../../docs/system/development/asset-studio/SICHTPRUEFUNG.md)
- [Architektur und aktueller Stand](../../docs/system/development/asset-studio/index.md)

`works/EtherFood_Codex_Aufgabenplan/` bleibt das ursprüngliche, hashgeprüfte
Auftragspaket. Der tatsächliche Umsetzungsstand steht in den GitHub-Issues,
in [PIPELINE-ALIGNMENT-V1](../../docs/system/development/plans/asset-studio-github-issues.md)
und den Ergebnisberichten, nicht in den ursprünglichen `not_started`-Vorlagen.
Vor Aufgabenbearbeitung oder Issue-Veröffentlichung den
[aktuellen Planungseinstieg](works/README.md) verwenden. Lokale Kataloge, Originalkopien und
Generatorausgaben gehören nicht nach Git.
