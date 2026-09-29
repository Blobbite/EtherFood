# EtherFood Asset Studio

Lokales Verwaltungswerkzeug neben dem bestehenden `PyGameTools/`.
Der PySide6-Desktop enthält Katalog, Projektkarten, Dokumente/Aufgaben und
**Verarbeitung → Ablaufeditor**. Kleine Python-Bausteine und verschachtelte
Werkzeugpakete bilden dort Bild-/Dateiverarbeitungsketten. Python-Editor,
Import/Export, Diagnose und getrennte Bibliotheksumgebungen sind integriert.

Vom Repository-Stamm starten:

```sh
python3 tools/control.py asset-manager run
python3 tools/control.py asset-manager install
python3 tools/control.py asset-manager upgrade
python3 tools/control.py asset-manager doctor
python3 tools/control.py asset-manager test
```

`run` richtet die lokale `.venv`, fehlendes pip und Python-Pakete automatisch ein;
manuelles Aktivieren ist nicht nötig. `doctor` installiert nichts.
`import`/`install` bereiten nur die Tool-Umgebung vor, nicht Spielassets.
`upgrade` aktualisiert pip über `ensurepip` und die Studio-Pakete auf die
im Projekt festgelegten Versionen.
`pipeline-test` prüft die bestehenden Bildpipelines; `check` kombiniert
Diagnose, Studio- und Pipeline-Tests. Für Tests ohne Qt: `test --core`.

- [Entwicklung und Voraussetzungen](../../docs/system/development/asset-studio/DEVELOPMENT.md)
- [Ablaufeditor verwenden](../../docs/system/development/asset-studio/PIPELINES.md)
- [Eigene Python-Bausteine und Werkzeugpakete](../../docs/system/development/asset-studio/SKRIPTPAKETE.md)
- [Historische Sichtprüfung nach Paket 4](../../docs/system/development/asset-studio/SICHTPRUEFUNG.md)
- [Architektur und aktueller Stand](../../docs/system/development/asset-studio/index.md)

`works/EtherFood_Codex_Aufgabenplan/` bleibt das ursprüngliche, hashgeprüfte
Auftragspaket. Der tatsächliche Umsetzungsstand steht in den GitHub-Issues,
in [PIPELINE-ALIGNMENT-V1](../../docs/system/development/plans/asset-studio-github-issues.md)
und den Ergebnisberichten, nicht in den ursprünglichen `not_started`-Vorlagen.
Vor Aufgabenbearbeitung oder Issue-Veröffentlichung den
[aktuellen Planungseinstieg](works/README.md) verwenden. Lokale Kataloge, Originalkopien und
Generatorausgaben gehören nicht nach Git.
