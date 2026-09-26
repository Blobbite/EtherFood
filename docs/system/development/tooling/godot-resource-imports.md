<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Reproduzierbare Godot-Ressourcenimporte

## Quellen und generierter Cache

Grafiken wie PNG-Dateien und ihre `.png.import`-Metadaten sind getrackte
Quell-Assets. Godot erzeugt daraus plattform- und versionsabhängige
Importartefakte, zum Beispiel `.ctex`-Dateien unter
`game/.godot/imported/`. Der gesamte Ordner `game/.godot/` ist ein lokaler
Cache und wird durch `.gitignore` ausgeschlossen.

Dieser Cache gehört nicht ins Repository: Er lässt sich aus den Quellen neu
erzeugen, kann sich zwischen Godot-Versionen und Betriebssystemen unterscheiden
und würde unnötige Binäränderungen verursachen. Ein frischer Checkout enthält
daher absichtlich noch keinen fertigen Ressourcen-Cache.

## Manueller Import

Der gemeinsame Einstiegspunkt führt einen vollständigen kopflosen
Godot-Editorimport aus:

```text
python tools/control.py godot4 import
```

Das Werkzeug findet die konfigurierte Godot-4-Binärdatei und startet
funktional `godot4 --headless --path <repository>/game --import`. Es verwendet
keine Shell-Interpretation und beendet sich mit dem Exit-Code des
Godot-Prozesses. Der Import besitzt ein begrenztes Timeout und zeigt Godots
Ausgabe sowie einen klaren Primärfehler an, wenn die Vorbereitung scheitert.

Große Heldenraster werden nacheinander importiert. Die Projekteinstellung
`editor/import/use_multiple_threads=false` begrenzt die gleichzeitigen
Speicherspitzen; ein paralleler Vollimport überschritt bei der Strukturumstellung
das Containerlimit von 4 GiB. Die Auflösung und Qualität der Bilder bleiben
unverändert. Die Einstellung ist in der
[Godot-Referenz](https://docs.godotengine.org/en/stable/classes/class_projectsettings.html#class-projectsettings-property-editor-import-use-multiple-threads)
beschrieben.

Testressourcen unter `test_assets/` und `test_scenes/` bleiben im Editor
importierbar. Ihre Ausschlüsse werden ausschließlich über die
[Exportvorlagen](../architecture/asset-ablage-und-freigabe.md#release-export)
gesteuert.

## Automatische Vorbereitung

Die üblichen Befehle verwenden denselben Importablauf automatisch:

```text
python tools/control.py godot4 run
python tools/control.py godot4 test
python tools/control.py check
```

`godot4 run` importiert zuerst und startet das Spiel nur nach erfolgreicher
Vorbereitung. `godot4 test` importiert ebenfalls zuerst und startet danach den
Repository-eigenen `test_scenes/helpers/bootstrap_integration_test.gd`. Nutzerargumente hinter `--`
gelangen nur an den eigentlichen Run- oder Testprozess, nicht an den Import.
Der Editor-Modus benötigt keinen vorgeschalteten zweiten Prozess, weil der
normale Godot-Editor selbst importiert.

Das Release-Gate `check` führt weiterhin Doctor, Quellstil und Python-Tests als
unabhängige Prüfungen aus. Danach folgen zwei getrennte, abhängige Schritte:

1. `Godot resource import` prüft, ob der Editor alle getrackten Ressourcen in
   den lokalen Cache übersetzen kann.
2. `Godot headless integration test` startet nur nach erfolgreichem Import und
   prüft den Bootstrap des Spiels. Sein expliziter Erfolgstext bleibt
   verbindlich.

Ein erfolgreicher Import ersetzt damit nicht den Integrationstest. Scheitert
der Import, wird der Test einmal klar als übersprungen gemeldet; die sonst
entstehende Kaskade aus Textur-, Szenen- und Parsefehlern wird vermieden.

## Lokale Entwicklung und CI

Nach dem Checkout wird die Repository-Umgebung eingerichtet und geprüft:

```text
python tools/control.py install --yes
python tools/control.py doctor
python tools/control.py godot4 import
python tools/control.py check
```

Der explizite Import ist nützlich, um die Vorbereitung getrennt zu prüfen.
Für den normalen Ablauf reicht anschließend `run`, `test` oder `check`, da
diese Befehle selbst importieren. Die CI stellt Godot als `godot4` im `PATH`
bereit und ruft dasselbe `python tools/control.py check` auf. Sie setzt keinen
vorhandenen `game/.godot`-Ordner voraus und lädt keine `.ctex`-Dateien herunter.

## Fehlerdiagnose und Wiederherstellung

Eine Meldung wie

```text
Unable to open file: res://.godot/imported/*.ctex
```

weist meist auf einen fehlenden oder veralteten lokalen Import-Cache hin. Der
erste Reparaturschritt ist:

```text
python tools/control.py godot4 import
```

Das gilt auch nach einem frischen Clone oder nachdem `git clean -fdx` bewusst
alle ignorierten Dateien einschließlich `.venv` und `game/.godot` entfernt hat.
Nach einem solchen Clean muss zuerst die lokale Python-Umgebung erneut
eingerichtet werden; danach erzeugt der Import den Godot-Cache wieder.

Scheitert der Import selbst, ist die erste echte Godot-Fehlermeldung maßgeblich.
Prüfe dann, ob das genannte Quell-Asset und seine Referenz vorhanden und gültig
sind. Eine Warnung zu `DRI_PRIME` erklärt keine fehlende `.ctex`-Datei. Der
richtige Reparaturweg bleibt ein erfolgreicher Neuimport aus den getrackten
Quellen, niemals das Committen von `game/.godot/` oder `.ctex`-Artefakten.
