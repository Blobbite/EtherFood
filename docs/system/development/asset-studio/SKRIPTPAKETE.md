# Python-Skripte und aktuelle Werkzeugdateien

[Asset Studio](index.md) · [Pipelines und Automatik](PIPELINES.md)

## Aktuelle Dateien statt Paketversionen

Die verbindlichen Projektpfade heißen absichtlich:

| Pfad | Inhalt |
| --- | --- |
| `.tools/scrips/` | Aktuelle Python-Skripte, eigene Unterordner, deklarierte Hilfsmodule und Ressourcen |
| `.tools/piplins/` | Aktuelle bearbeitbare Pipelinedefinitionen |

**Speichern** aktualisiert diese Dateien atomar über das bestehende
Dateijournal. Der nächste freigegebene Lauf liest den aktuellen gespeicherten
Stand. Ein zusätzlicher Paketversions-/Veröffentlichungsschritt entfällt.
IDs, Zuordnungen, Skriptbeschreibungen, Layout und Freigaben bleiben im lokalen
Katalog. Historischer Datenbankcode ersetzt niemals fehlende aktuelle Dateien.
Ein `start.py` ist für die aktuelle Ausführung nicht erforderlich; der Runner
liest genau die gespeicherte Ablaufbeschreibung.

## Pythoneditor bedienen

In **Skripte & Pipelines → Python-Editor** eine Datei aus **Eigene Skripte**
auswählen. Der Editor bietet Python-Hervorhebung, Zeilennummern, Undo/Redo,
Speichern, Neu laden, Prüfen und einen ausdrücklichen Testlauf. Die Beschreibung
unter dem Text legt Einstieg, Ein-/Ausgänge, Verarbeitung je Quelle oder
Sammlung je Asset, Parameter, Bibliotheken und Hilfsdateien fest.

Ungültiger Pythoncode darf gespeichert bleiben und repariert werden. Syntax-
und Importdiagnosen verhindern seinen freigegebenen Start. Speichern ist keine
Freigabe. Ein Dateikonflikt erhält den Entwurf; **Neu laden** verwirft ihn nur
nach der bestehenden Speichern-/Verwerfen-/Abbrechen-Entscheidung. Auch
Hilfsdateien können aus der Struktur ausdrücklich geöffnet werden.

Ordner erstellen sowie Umbenennen/Verschieben arbeiten auf der tatsächlichen
Dateistruktur. Stabile Skript-IDs erhalten die Knotenreferenzen. Relative
Imports, bekannte lokale Modulimporte und Ressourcenpfade werden geprüft;
ein erkennbar beschädigender Umzug wird abgewiesen. Dynamisch berechnete
Importpfade müssen zusätzlich im ausdrücklichen Testlauf geprüft werden.

Ein Skript auf den Pipeline-Canvas ziehen erzeugt eine Knoteninstanz. Über
**Rechtsklick → Skript bearbeiten** öffnet sich dieselbe Datei im Pythoneditor.
Das Entfernen des Knotens löscht die gemeinsam verwendete Datei nicht.

## Python-Schnittstelle

Ein einzelner Eingang liefert ein `Artifact`, ein mehrfacher Eingang eine Liste.
`execution = map` verarbeitet Quellen einzeln; `collect` sammelt die passenden
Quellen eines Assets. Der Manager ändert Einzelbilder nicht still in Spritesheets.

```python
def run(context, inputs, parameters):
    source = inputs["input"]
    result = context.artifact("copy.bin", source.type, source.metadata)
    result.path.write_bytes(source.path.read_bytes())
    return {"output": result}
```

`context.output` ist der kontrollierte Laufbereich. `context.package` enthält
die eingefrorenen Skript-/Hilfsdateien, `context.resources` ausdrücklich
deklarierte Ressourcen. Ergebnisse werden nach benanntem Ausgang zurückgegeben.
Die Dateiendung allein ersetzt keine Typ- und Inhaltsprüfung.

Ein-/Ausgangsbeschreibungen verwenden beispielsweise:

```json
{
  "input": {
    "type": "spritesheet",
    "animated": true,
    "required": true,
    "multiple": false
  }
}
```

`image` und `spritesheet` sind unterschiedliche Typen; `file` akzeptiert
allgemeine Dateien. Animation benötigt passende Raster-, Frame- und Timingdaten.
Optionalität und Mehrfachheit werden ausdrücklich deklariert. Ausgänge können
unter anderem Bilder, GIF, JSON und Dateien liefern. Metadaten bleiben erhalten
und werden bei Bildausgaben gegen die tatsächliche Geometrie geprüft.

Die Ressourcenbeschreibung eines Pipelineeingangs kann feste, hashgeprüfte
Projektblobs oder bewusste Assetbindungen enthalten. Übernommene Farb- und
Maskenschritte verwenden `color_profile`, `source_mask` beziehungsweise
`declared_mask`. Materialverarbeitung erhält benötigte Originalpixel über einen
zusätzlich ausdrücklich verbundenen Eingang. Ein Folgeschritt einer anderen
Pipeline bekommt keine heimlichen Originalquellen.

## Bibliotheken, Prüfung und Test

Bibliotheken werden mit Version deklariert und nur durch
**Bibliotheken prüfen / einrichten** in einer getrennten projektlokalen Umgebung
bereitgestellt. Verzeichnis-/Bibliotheksansichten importieren keinen fremden
Skriptcode. Installation und echte Ausführung sind ausdrückliche lokale
Handlungen. Die Umgebung isoliert Abhängigkeiten, nicht Zugriffsrechte.

Prüfung und Start kontrollieren Interpreter, deklarierte Imports und tatsächliche
Bibliotheksdateien. Geänderte Bibliotheken oder Hilfsdateien entwerten den
abhängigen freigegebenen Gesamtstand. Ein Testlauf verarbeitet ausdrücklich
gewählte vorhandene Eingaben in einem separaten Laufbereich. Er veröffentlicht
keine produktiven Ergebnisse und erteilt keine Pipelinefreigabe.

## Import und Export

**Importieren** übernimmt eine ausdrücklich gewählte `.py`-Datei oder ein
vollständiges Werkzeugbündel. Neue Bündel enthalten aktuelle Skripte,
Hilfsdateien, Beschreibungen, Verbindungen und notwendige Ressourcen mit
Hashes. Vollständige ältere Ablauf-/Werkzeugbündel werden direkt in die neue
Dateistruktur umgesetzt. Verschachtelte Abläufe werden semantisch aufgefaltet;
unaufgelöste Stellen bleiben als Blockade sichtbar.

Import startet keinen Code, installiert keine Bibliotheken und übernimmt keine
lokale Freigabe. Neue Identitäten verhindern das Überschreiben bestehender
Skripte. Export erhält alle ausdrücklich deklarierten Hilfsdateien. Nicht
deklarierte Nachbardateien werden nicht ungefragt eingepackt.

## Sichere Bestandsübernahme

Schemaänderungen erzeugen vorab eine SQLite-Sicherung. Die inhaltliche Übernahme
legt zusätzlich unter `.asset-studio/migrations/current-pipeline-files-v1/`
einen Katalogstand und `managed-files.zip` mit Hashmanifest ab. Aktuelle Dateien
werden journalgeführt übernommen; bei Konflikten wird abgebrochen, ohne fremde
Dateien zu überschreiben. Wiederaufnahme benutzt dieselben stabilen Identitäten.

Bewusst verschieden gebundene alte Skriptversionen bleiben unterscheidbar.
Alte Prioritätsregeln liefern zunächst die früher tatsächlich wirksame
Assetauswahl. Unklare Zuordnungen benötigen eine Entscheidung im Projekt.
Prüfbare frühere Ergebnisdateien bleiben historische Ergebnisse mit Nachweisen;
ungeprüfte Bytes werden nicht als gültiger Cache ausgegeben.

Alte Auftragsoberflächen, CLI-Einstiege, Ausführungsdienste und ausschließlich
zugehörige Tabellen sind abgelöst. Historische Entwicklungsberichte bleiben
Nachweise ihres damaligen Stands. Migration legt keine Beispiele in einem
leeren Projekt an. Ausschließlich **Einstellungen → Tests → Demo anlegen**
fügt die aktuellen synthetischen Beispiele hinzu.
