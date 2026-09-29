# Werkzeugpakete, Python-Schnittstelle und Asset-Ablage

Die [Bedienung des Ablaufeditors](PIPELINES.md) beschreibt Bibliothek, Canvas,
Posen und Migration. Dieses Dokument erklärt eigene Bausteine und den Austausch.

## Pipeline-Dashboard und GIF-Vorschauen

Das frühere Pipeline-Dashboard heißt **Ablaufeditor** und liegt unter
**Verarbeitung**. PyImgGif ist ein einzeln verwendbarer Baustein mit einem
GIF-Ausgang und konfigurierbarem Zielordner. Auch mehrere GIF-Ausgänge und
anschließende Vergleichsschritte lassen sich im selben Canvas verbinden.

## Pipeline-Board im Asset-Menü

Das Board am Asset zeigt wirksame Abläufe, Zuweisungen und deren deklarierte
Ausgabeordner. Bearbeitung und Verarbeitung öffnen den zentralen Ablaufeditor.
Grafikprofile, Zielframes, Farbparameter und separate Buildknöpfe werden dort
nicht mehr parallel angeboten. Posen zeigen weiterhin Quellen, Richtungen,
Quell-Timing, Maskenlieferstand und geprüfte Ergebnisse.

## Eigenen Baustein erstellen oder importieren

1. Unter **Verarbeitung → Neuer Python-Baustein** einen Namen eingeben. Das
   Studio legt eine Kopiervorlage mit `run(context, inputs, parameters)` an.
   Alternativ **Importieren** für `.py`, `manifest.json` oder ein Paket-ZIP wählen.
2. Im Python-Editor die konkrete Aufgabe implementieren. **Neue Datei** ergänzt
   Hilfsmodule; **+ Skriptbaustein** ergänzt einen weiteren Einstieg;
   **+ Teilablauf** öffnet einen Canvas zur Zusammensetzung innerhalb des Pakets.
3. Im `manifest.json` Ein-/Ausgänge, Parameter, Bibliotheken und Standardordner
   beschreiben. **Prüfen** meldet fehlende Dateien, Syntaxfehler, falsche
   Funktionssignaturen, Bibliotheksbestand und fehlende externe Python-Module.
4. **Umgebung einrichten / reparieren** installiert die deklarierten Bibliotheken
   in eine separate Projektumgebung. **Entwurf testen** verwendet eine ausgewählte
   importierte Asset-Quelle und schreibt ausschließlich in den Job-Arbeitsbereich.
5. **Neue Version übernehmen** veröffentlicht den Paketentwurf unter einer neuen
   Versionsnummer. Danach diese Version im Ablauf auswählen und freigeben.
   Bestehende Abläufe behalten ihren zuvor gebundenen Inhaltshash.

Ein beliebiges CLI-Skript wird beim Import nicht automatisch umgeschrieben.
Fehlt die `run`-Schnittstelle, erscheint dies als Diagnose im editierbaren Paket.
Für PyImgGrid, PyImgGif, Comic-/Pixelverfahren und Vergleiche sind passende
Wrapper bereits im mitgelieferten Bildpaket enthalten.

Das direkt importierbare, mehrteilige Beispiel liegt unter
[`examples/tool_report/manifest.json`](../../../../tools/AssetManager/examples/tool_report/manifest.json).
Es erzeugt einen JSON-Dateibericht mit einem Hilfsmodul und benötigt nur die
Python-Standardbibliothek. Die vorhandenen Beispiele `pipeline_scale`,
`pipeline_frames` und `pipeline_grayscale` dokumentieren ältere Verträge;
beim Import ihrer v2-Manifeste erfolgt die Übernahme in den neuen Ablauf.

## Schnittstelle eines Skriptbausteins

```python
import json
from helper import describe


def run(context, inputs, parameters):
    source = inputs["image"]
    output = context.artifact("report.json", "json")
    output.path.write_text(json.dumps(describe(source.path)), encoding="utf-8")
    return {"report": output}
```

`inputs` enthält die benannten Eingänge. Ein einzelner Eingang ist ein
`Artifact`, ein Anschluss mit `multiple: true` eine Liste von Artefakten.
Optionale leere Einzeleingänge sind `None`. Python-Unterpakete und relative
Hilfsimporte wie `from .helper import convert` werden unterstützt. Ein `Artifact` besitzt `path`,
`type` und `metadata`. Eingänge sind Arbeitskopien; Ergebnisse müssen unter
`context.output` liegen. `context.artifact(name, type, metadata)` legt eine
Ausgabebeschreibung an und erzeugt nötige Unterordner. Das Skript schreibt die
Datei selbst. `context.path(name)`, `context.package`, `context.resources` und
`context.log(text)` stehen ebenfalls zur Verfügung.

Der Rückgabewert enthält jeden deklarierten Ausgang, jeweils als Artefakt oder
Liste. Ein optionaler Ausgang (`required: false`) darf eine leere Liste liefern;
Pflichtausgänge benötigen mindestens eine Datei. Unterstützte Typen sind `image`
(PNG), `spritesheet` (PNG mit Rasterdaten),
`gif`, `html`, `json` und `file`. `file` akzeptiert alle Dateitypen.
Ein Mehrfachausgang benötigt einen Mehrfacheingang. `map` verarbeitet jede
verbundene Quellrevision; `collect` erhält alle verbundenen Ergebnisse eines
Assets, beispielsweise die Bilder für einen Vergleich.

PNG-/Spritesheet-Bausteine sollten die mitgegebenen Herkunfts-, Geometrie- und
Timingdaten erhalten. Das SDK bietet `images(artifact)` zum Zerlegen eines
bekannten Rasters und `sheet(context, frames, metadata, name, grid=...)` zum
Zusammensetzen samt konsistenten Maßen. Es errät kein Raster aus Dateinamen.
Beliebige Dateien und Berichte benötigen keine Bildmetadaten.

## Manifest und Teilabläufe

Der Vertrag `studio-tool-package-v1` enthält Paket-ID, Name, Version,
Beschreibung, Python-Haupt-/Nebenversion, festgelegte Bibliotheken, Dateiliste,
Bausteine und Teilabläufe. Jeder Baustein benennt Python-Datei, Einstieg,
Ausführungsart, Anschlüsse, Parameter und benötigte Asset-Fähigkeiten.
Parameter können Zahlen, Ganzzahlen, Schalter, Text, Auswahlen oder
Ressourcenverweise sein. Sie erzeugen die Eigenschaftenfelder im Canvas.

Ausgänge deklarieren beispielsweise:

```json
{"report": {"type": "json", "directory": "Ergebnisse/Berichte", "publish": true}}
```

Ein Teilablauf verwendet `studio-pipeline-v2`, genau einen Asset-Eingang und
benannte Ausgänge auf ausgewählte innere Knoten. `local:<baustein-id>` und
`local-flow:<ablauf-id>` verweisen auf Einträge desselben Pakets. Externe
Verwendungen enthalten einen Paket-Inhaltshash. Dadurch bleiben alte Abläufe
reproduzierbar, auch wenn der Code im Editor geändert wird. Rekursive Abläufe
und Zyklen werden abgewiesen; die Verschachtelung ist auf 16 Ebenen begrenzt.

Die maschinenlesbaren Verträge stehen unter
[Werkzeugpaket](../../../../schemas/asset-studio/tool-package-v1.json),
[Ablauf](../../../../schemas/asset-studio/pipeline-recipe-v2.json),
[Austauschpaket](../../../../schemas/asset-studio/workflow-bundle-v1.json) und
[Assetdefinition](../../../../schemas/asset-studio/asset-definition-v2.json).
Zusätzlich prüft das Domain-Modell Beziehungen, Porttypen und Ressourcen.

## Python-Umgebungen und Diagnose

Umgebungen liegen im geöffneten Projekt unter `.asset-studio/environments/`.
Sie verwenden `venv` ohne Systempakete und dieselbe Python-Haupt-/Nebenversion
wie Studio. Der Schlüssel berücksichtigt Python, Plattform und die im Manifest
festgelegten Bibliotheken. Identische Anforderungen teilen eine Umgebung;
abweichende Anforderungen erhalten getrennte Umgebungen. Die Studio-Installation
und das System-Python erhalten dabei keine zusätzlichen Skriptbibliotheken.

Bibliotheken müssen als `Name==Version` angegeben sein. Die Einrichtung
installiert Wheel-Dateien über pip, protokolliert die aufgelösten Versionen und
Downloadhashes und legt eine lokale `requirements.lock` an. Vor einem Job werden
Interpreter und installierter Bibliotheksbestand gegen den Nachweis geprüft.
Fehlende passende Wheels oder eine andere verlangte Python-Version werden als
Fehler gemeldet. **Umgebung einrichten / reparieren** baut eine beschädigte
Umgebung neu auf. Der Import selbst installiert nichts.

Die Diagnose nennt fehlende Paketdateien, Syntaxfehler und fehlende Python-Module
mit Datei und Zeile. Fehlende Imports auf Modulebene blockieren die Freigabe.
Imports innerhalb von Funktionen oder Bedingungen werden als bedingt gemeldet;
ob sie benötigt werden, prüft anschließend der konkrete Testlauf.

Der Python-Editor zeigt Dateien, Zeilennummern, Syntaxhervorhebung und den
Vergleich mit der veröffentlichten Paketversion. **Fehlerkontext kopieren**
stellt Manifest, ausgewählte Datei und Diagnose für einen KI-Agenten oder
externen Editor bereit. Vorschläge werden als Entwurf eingefügt, geprüft und
getestet; es erfolgt keine automatische Übermittlung an einen KI-Dienst.

Python läuft mit den Benutzerrechten des Studios. Die separate
Bibliotheksumgebung ist keine Sicherheits-Sandbox. Eine Freigabe gilt nur für
den geprüften Pakethash und wird nicht in andere Projekte übertragen.

## Vollständiger Import und Export

- Ein einzelnes Paket-ZIP enthält `manifest.json` und alle deklarierten Dateien.
- Der Export aus der Bibliothek enthält zusätzlich transitiv benötigte Pakete
  und Ressourcen in einem Werkzeugbündel mit `toolkit.json`.
- Der Ablaufexport enthält `workflow.json`, alle benötigten Werkzeugpakete,
  Hilfsmodule und deklarierte Ressourcen. Asset-Zuweisungen und Quellbilder
  bleiben projektspezifisch.
- Die Importvorschau meldet fehlende Dateien, Pakete und Ressourcen. Ein
  unvollständiger Ablauf kann als blockierter Entwurf übernommen und repariert
  werden. Archive mit Elternpfaden, Symlinks oder nicht deklarierten Dateien werden
  abgewiesen. Grenzen: 16 MiB je Datei, 128 MiB je Archiv, 2048 Archivdateien.
- Installierte Umgebungen, lokale Codefreigaben und Zugangsdaten werden nicht
  exportiert. Auf dem Zielrechner wird die Umgebung aus den festgelegten direkten
  Anforderungen neu eingerichtet. Der dort aufgelöste transitive Bestand kann
  von einem früheren lokalen Nachweis abweichen und erhält einen eigenen Nachweis.

## Lesbare Projektablage

Die tatsächlichen Besitzer und Kartennamen bestimmen die Ordner:

```text
Projektordner/
├── Index.md                         # automatisch gepflegte Startseite
├── Projekt.md                       # Grunddokument mit Platz für eigene Texte
├── .pipelines/
│   └── Skalierung/
│       ├── Skalierung.md
│       └── rezept.json
├── Projektweite Inhalte/
│   ├── Projektweite Inhalte.md
│   └── Assets/
│       ├── index.md
│       └── Figur/…
├── Akt 1/
│   ├── Akt 1.md
│   └── Kapitel 2/
│       ├── Kapitel 2.md
│       └── Assets/
│           ├── index.md
│           └── NPC/
│               ├── index.md
│               └── Wächter/
│                   ├── Wächter.md
│                   ├── Dokumente/…  # weitere Dokumente und Notizen
│                   ├── source/walk/          # einzelne Posenbilder, 1×1
│                   ├── spritesheets/walk/    # gelieferte Raster
│                   ├── masks/
│                   │   ├── source/walk/
│                   │   └── spritesheets/walk/
│                   ├── previews/
│                   │   ├── gif/              # GIFs, Metadaten und Galerie
│                   │   └── video/            # vorbereiteter Zielordner
│                   └── Ergebnisse/
│                       ├── walk/ComicLow/    # deklarierte Bausteinausgabe
│                       └── aktuell.json
└── Akt 2/…
```

Die Namen folgen den tatsächlichen Karten; ein Kapitel kann beispielsweise auch
`chapter_1` heißen. Typen werden aus den bestehenden Asset-Definitionen aufgelöst,
nicht als zweite Typenliste angelegt. Bestehende Pakete stehen unter
`Assets/Pakete/<Paketname>/<Asset-Typ>/<Assetname>/`; ihr Besitzer und ihre IDs
bleiben erhalten. Auch Assets direkt an Akten oder im projektweiten Bereich
verwenden dort dieselbe Typgruppierung.


Die Projektkarte entspricht dem gewählten Projektordner selbst. Ihr Anzeigename
benennt nicht ungefragt dessen äußeren Betriebssystempfad um. Karten darunter
werden beim Anlegen, fachlichen Umordnen und Umbenennen abgeglichen. Gleichnamige
Geschwister erhalten einen stabilen ID-Zusatz; nicht portable Namenszeichen
werden ersetzt. Reines Verschieben auf dem Canvas verändert weder Pfade noch
Bilder. Eine zusätzliche Verwendung eines Assets erzeugt keine weitere Ablage.

Eine Pipeline hat ihren eigenen Rezeptordner. Ihre Bildausgaben gehören immer
zum verarbeiteten Asset, auch bei Sammelausführungen über mehrere Kapitel.
Die vier Posenbereiche verwenden dieselben Exportnamen: `source`, `spritesheets`,
`masks/source` und `masks/spritesheets`. Neue Posen ergänzen alle vier Ordner;
Umbenennen eines Exportnamens verschiebt die zugehörigen verwalteten Quellen und
Masken. Richtungen bleiben über die zugehörigen Metadaten eindeutig zugeordnet;
zusätzliche Richtungsordner werden nicht angelegt.
Statische Quellen liegen direkt unter `source`; verarbeitete PNGs verwenden die
im Ablauf deklarierten Ausgabeordner. Bereits veröffentlichte historische Builds behalten ihre
registrierten Pfade.
Ergebnisse werden nach den deklarierten Baustein-/Ablaufausgängen eingeordnet. Der Zusatz im
Dateinamen unterscheidet unveränderliche Buildstände; `aktuell.json` benennt den
letzten vollständig veröffentlichten Lauf. Ältere Dateien bleiben erhalten.
Der geprüfte Aktualitätsstatus in Studio berücksichtigt spätere Rezeptänderungen.

Die sichtbaren Quellen sind eigenständige Kopien der importierten Revisionen.
Verwaltete Dateien aus dem bisherigen Ordner `Quellen` werden beim Abgleich in
den passenden Posenbereich verschoben. Fremde Dateien und leere frühere Ordner
bleiben erhalten; es gibt keine pauschale Bereinigung.
Dateien in `source`, `spritesheets`, `masks`, `previews`, `Ergebnisse` und `Pakete`
werden nicht als veränderbare
Hardlinks auf Originale angelegt. Bearbeiten einer sichtbaren Python-Datei
aktiviert den Code nicht: Die geänderte Datei muss ausdrücklich neu registriert
und freigegeben werden. Extern veränderte verwaltete Dateien werden beim
Ersetzen als Konflikt behandelt und nicht still überschrieben.

`.asset-studio/jobs` und `.asset-studio/objects` bleiben interne Arbeits- und
Cacheablagen. Zwischenstände fehlgeschlagener Läufe werden nicht zu aktuellen
Asset-Ergebnissen. Die sichtbaren Bilddateien werden erst nach erfolgreicher
PNG-/GIF-/Metadatenprüfung und vollständigem Lauf veröffentlicht. Es gibt keine
pauschale Ordnerbereinigung und keine automatische Freigabe für das Spiel.

Migration 8 ergänzt lokale Pfad- und Besitzlisten, Migration 9 die Markdown-Dateizuordnung,
Migration 10 Werkzeugpakete, Entwürfe und Dateiveröffentlichungen. SQLite wird vor der Migration
nach der bestehenden Konvention gesichert. Beim regulären Öffnen älterer Projekte
wird die Ablage ergänzt, ohne Bilder neu zu berechnen. Dateiänderungen haben
ein Wiederaufnahmejournal: Schlägt eine Transaktion fehl, werden ihre eigenen
Dateischritte zurückgenommen; nach einem Prozessabbruch erfolgt der Abgleich
beim nächsten Öffnen. Fremde Dateien, Namenskonflikte und Symlinks werden nicht
durch Zusammenführen oder Löschen übergangen. Nur lesendes Öffnen schreibt
keine Ordner.

## Automatische Markdown-Dokumentation

**Startseite** in der oberen Leiste öffnet `Index.md`. Dort stehen Links zu
Projektweit, Akten, Kapiteln, Pipelines, Asset-Typen sowie vorhandenen Dokumenten,
Notizen, Aufgaben und Issues. Die Inhalte kommen aus demselben Katalog wie das
Canvas. Anlegen, Umbenennen, fachliches Verschieben und Archivieren einschließlich
Undo aktualisieren die Indizes in derselben Transaktion. Layoutänderungen tun dies
nicht. Die Startseite und Bereichsdokumente sind über den Projektbaum und die jeweilige
Karte erreichbar. Im Dokument-Kontextmenü blendet **Im Canvas einblenden** eine
zusätzliche Dokumentkarte ein; dies ist rückgängig machbar. Automatische Dokumente
überlagern vorhandene Canvas-Karten nicht ungefragt.

Beim Anlegen oder ersten Öffnen erhält jeder Bereich genau ein Grunddokument.
Projekt, Akt, Kapitel, Paket, Asset und Pipeline haben ihre eigene Markdown-Datei.
Akt-/Kapitelvorlagen enthalten neutrale Überschriften, keine erfundene Handlung.
Im Reiter **Dokumentation & Anhänge** steht das Grunddokument bereit. Mit
**+ Dokumentation** sind beliebig weitere Dokumente im bestehenden Rahmen möglich;
**Notizen** und **Aufgaben-Kanban** bleiben die gemeinsamen Planungswerkzeuge.

Der Abschnitt zwischen `<!-- STUDIO:AUTO START -->` und `<!-- STUDIO:AUTO END -->`
enthält den automatisch gepflegten Inhalt. **Eigene Texte außerhalb dieser
Markierungen schreiben.** Die Startseite ist in der App schreibgeschützt;
Grunddokumente enthalten darunter Platz für eigene Beschreibungen. Das Grunddokument
folgt seinem Bereich und wird nicht unabhängig umgeordnet oder archiviert.
Zusätzliche Dokumente bleiben frei bearbeitbar und umordnungsfähig.

Änderungen am Text einer bekannten Markdown-Datei außerhalb Studios werden beim
nächsten Struktur-/Inhaltsabgleich oder Wiederöffnen übernommen. Ändern Datei und
App denselben Stand parallel, wird der Vorgang mit einem Konflikt abgewiesen;
die Datei bleibt erhalten und der ungespeicherte App-Text bleibt im Editor.
Entfernte oder doppelte Automatikmarkierungen werden nicht still repariert.
Neu ins Dateisystem gelegte Dokumente werden bewusst über **Markdown importieren**
aufgenommen. Es gibt keinen Hintergrund-Dateiwächter.

Jeder veröffentlichte Ergebnisordner erhält `index.md` mit einer Tabelle
**Datei | Vorschau**, relativen Datei-Links und Bildvorschauen für Bilder/GIFs. Die Tabelle
zeigt die Ergebnisse des letzten vollständig veröffentlichten Laufs; ältere
Bildstände werden nicht gelöscht. Eigene Absätze außerhalb der Automatikmarkierung
bleiben auch in diesen Übersichten erhalten. Die App öffnet verlinkte Bereichs-
dokumente und Galerien. Bildvorschauen laden ausschließlich bekannte, hashgeprüfte
Projektbilder; beliebige lokale Dateien und Netzwerkbilder werden nicht geladen.

Die technischen SQLite-Dateien und `.asset-studio` bleiben mit ihrem bestehenden
Vertrag erhalten. Der konzeptionelle `.db`-Ordner ist keine zweite Datenbank.
Die lesbare Navigation beginnt bei `Index.md`; Job-UUIDs sind kein Arbeitsverzeichnis
für die Asset-Verwaltung.

## Betriebsgrenzen und Kompatibilität

Neue Bausteine benötigen keine Änderung am Anwendungskern, solange sie den
Datei-/Paketvertrag einhalten. Das SDK ist für dateibasierte Verarbeitung
vorgesehen; frei ausführbare GUI-Erweiterungen gehören nicht zum neuen Vertrag.
Die ältere Verarbeitung und ihre Revisionen bleiben für Migration und
historische Ergebnisse lesbar. Neue Abläufe verwenden den generischen Worker.

Ausführung und Prozessabbruch verwenden den vorhandenen Linux-Runner.
Quellen, Ergebnisse und generierte Umgebungen sind lokale Projektdaten und
gehören nicht ins Repository. Die sichtbare Ablage bleibt eine verwaltete
Projektion des Katalogs; externe Ordnerumbenennungen sind keine automatischen
Projektänderungen. Alte Dateien werden nicht pauschal gelöscht.

Der [Arbeitsplan](../plans/asset-studio-ablaufeditor.md) dokumentiert Umfang,
Migration und tatsächlich ausgeführte Prüfungen.
