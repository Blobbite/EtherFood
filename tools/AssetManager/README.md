# EtherFood Asset Studio

Native Python-/PySide6-Anwendung mit **Projekt** und **Skripte & Pipelines**.
Projektkarten, Dokumente, Aufgaben und Anhänge verwenden den bestehenden
Katalog. Gemeinsame Pipelinedefinitionen und ihre Projektverwendungen sind
getrennt. Aktuelle Dateien liegen unter `.tools/scrips/` und `.tools/piplins/`.
Verarbeitung benötigt eine ausdrückliche lokale Freigabe des geprüften Stands.
Neue Projekte enthalten keine Verarbeitungsskripte oder fertigen Pipelines.

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
- [Pipelineeditor und Automatik verwenden](../../docs/system/development/asset-studio/PIPELINES.md)
- [Aktuelle Python-Skripte und Dateitransport](../../docs/system/development/asset-studio/SKRIPTPAKETE.md)
- [Historische Sichtprüfung nach Paket 4](../../docs/system/development/asset-studio/SICHTPRUEFUNG.md)
- [Architektur und aktueller Stand](../../docs/system/development/asset-studio/index.md)

`works/EtherFood_Codex_Aufgabenplan/` bleibt das ursprüngliche, hashgeprüfte
Auftragspaket. Der tatsächliche Umsetzungsstand steht im
[aktuellen Arbeitsplan](../../docs/system/development/plans/asset-studio-zwei-editoren-und-automatik.md)
und seinen Prüfergebnissen, nicht in den ursprünglichen `not_started`-Vorlagen.
Vor Aufgabenbearbeitung oder Issue-Veröffentlichung den
[aktuellen Planungseinstieg](works/README.md) verwenden. Lokale Kataloge, Originalkopien und
Generatorausgaben gehören nicht nach Git.
