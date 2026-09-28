# Skriptpakete im Canvas und Ergebnisse beim Asset

Studio stellt Canvas, Projektstruktur, Dokumentation, Registrierung, generische
Eigenschaften und geprüfte Bildjobs bereit. Grafik-, Frame- und Farbverarbeitung
werden von mitgelieferten Python-Paketen angeboten. Eigene Pakete werden bewusst
importiert und freigegeben. Fachliche Dialoge sind optionale Paketdienste;
beispielsweise erscheinen Referenzen und Masken bei einer zugewiesenen aktiven
Farbpipeline. Eine Skalierung benötigt dieses Werkzeug nicht.

## Skalierungspaket verwenden

1. Studio über `python tools/control.py asset-manager run` öffnen und ein Projekt
   auswählen. Im Canvas **Pipeline importieren …** wählen.
2. `tools/AssetManager/examples/pipeline_scale/manifest.json` auswählen. Die
   danebenliegende `scale.py` gehört zu diesem Paket. Die Vorschau zeigt
   Verarbeitung, Parameter, optionale Aktionen und den Codehash. Mit
   **Als Pipeline importieren** eine Projektkopie anlegen.
3. Die Pipeline-Karte öffnen. Unter **Python-Erweiterungen …** die registrierte
   Version ansehen und bewusst freigeben. Der Import allein startet und
   autorisiert keinen Python-Code.
4. Im Pipeline-Canvas den Skalierungsschritt auswählen. Rechts **Größenmodus**
   auf `factor` und **Faktor** beispielsweise auf `0.5` stellen. Alternativ
   `max_edge` und eine maximale Frame-Kante wählen. Die Beschreibung jedes
   Feldes erklärt, in welchem Modus es verwendet wird.
5. Optional **Größenvorgabe wählen …** öffnen. Diese Oberfläche wird von
   `scale.py` bereitgestellt; der Host kennt ihre Größenoptionen nicht.
   Übernommene Werte erscheinen in denselben Eigenschaften und können
   rückgängig gemacht werden. Danach speichern.
6. Unter **Zuweisungen …** Assets, eine Typregel oder den Projektstandard
   zuordnen. Benötigte Quellen vorher am Asset importieren.
7. **Dry-run / Ausführen …** öffnen, betroffene Assets prüfen und starten.
   Die bestehende Hintergrundausführung liefert echte PNGs. Das Ergebnis
   enthält tatsächliche Maße, Raster und Darstellungsmetadaten.
8. Die Asset-Karte rechtsklicken und **Ordner öffnen** wählen. Quellen und
   Ergebnisse stehen im Ordner dieses Assets.

Bei 512×256 Pixeln ergibt Faktor 0,5 genau 256×128 Pixel. Bei Spritesheets
gilt dies je Frame-Zelle. Das vorhandene Comic-Verfahren wird wiederverwendet;
Raster, Reihenfolge, Alpha, Timing und logische Weltgröße bleiben erhalten.
Die Maximal-Kante vergrößert kleine Bilder nicht. Positive Pixelmaße werden
deterministisch half-up gerundet. Das Paket ist kein Ersatz für das besondere
Pixel-Art-Verfahren bestehender Grafikrezepte.

## Lesbare Projektablage

Die tatsächlichen Besitzer und Kartennamen bestimmen die Ordner:

```text
Projektordner/
├── Index.md                         # automatisch gepflegte Startseite
├── Projekt.md                       # Grunddokument mit Platz für eigene Texte
├── .pipelines/
│   └── Skalierung/
│       ├── Skalierung.md
│       ├── rezept.json
│       └── Pakete/python-proportional-scale/
│           ├── manifest.json
│           └── scale.py
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
│                   ├── Quellen/
│                   └── Ergebnisse/
│                       ├── aktuell.json
│                       └── scaled/
│                           ├── index.md  # Dateilinks und Bildvorschauen
│                           ├── waechter--<Buildkennung>.png
│                           └── waechter--<Buildkennung>.json
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
Ergebnisse werden nach ihrem tatsächlichen Profil eingeordnet. Der Zusatz im
Dateinamen unterscheidet unveränderliche Buildstände; `aktuell.json` benennt den
letzten vollständig veröffentlichten Lauf. Ältere Dateien bleiben erhalten.
Der geprüfte Aktualitätsstatus in Studio berücksichtigt spätere Rezeptänderungen.

Die sichtbaren Quellen sind eigenständige Kopien der importierten Revisionen.
Dateien in `Quellen`, `Ergebnisse` und `Pakete` werden nicht als veränderbare
Hardlinks auf Originale angelegt. Bearbeiten einer sichtbaren Python-Datei
aktiviert den Code nicht: Die geänderte Datei muss ausdrücklich neu registriert
und freigegeben werden. Extern veränderte verwaltete Dateien werden beim
Ersetzen als Konflikt behandelt und nicht still überschrieben.

`.asset-studio/jobs` und `.asset-studio/objects` bleiben interne Arbeits- und
Cacheablagen. Zwischenstände fehlgeschlagener Läufe werden nicht zu aktuellen
Asset-Ergebnissen. Die sichtbaren Bilddateien werden erst nach erfolgreicher
PNG-/Metadatenprüfung und vollständigem Lauf veröffentlicht. Es gibt keine
pauschale Ordnerbereinigung und keine automatische Freigabe für das Spiel.

Migration 8 ergänzt lokale Pfad- und Besitzlisten, Migration 9 die Markdown-Dateizuordnung. SQLite wird vor der Migration
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
**Datei | Vorschau**, relativen PNG-Links und eingebetteten Bildern. Die Tabelle
zeigt die Ergebnisse des letzten vollständig veröffentlichten Laufs; ältere
Bildstände werden nicht gelöscht. Eigene Absätze außerhalb der Automatikmarkierung
bleiben auch in diesen Übersichten erhalten. Die App öffnet verlinkte Bereichs-
dokumente und Galerien. Bildvorschauen laden ausschließlich bekannte, hashgeprüfte
Projektbilder; beliebige lokale Dateien und Netzwerkbilder werden nicht geladen.

Die technischen SQLite-Dateien und `.asset-studio` bleiben mit ihrem bestehenden
Vertrag erhalten. Der konzeptionelle `.db`-Ordner ist keine zweite Datenbank.
Die lesbare Navigation beginnt bei `Index.md`; Job-UUIDs sind kein Arbeitsverzeichnis
für die Asset-Verwaltung.

## Mitgelieferte Pakete und optionale Werkzeuge

Unter `src/etherfood_studio/packages/` liegen die deklarativen Manifeste und
Python-Verarbeitung für Grafikprofile, Frame-Aufbereitung/-Auswahl und Farben.
Die bestehende PyGameTools-Verarbeitung wird wiederverwendet. Die Pakete nutzen
den gemeinsamen Bildadapter und Job-Runner. Rezept-IDs, Operationen, Profile und
Timing bleiben kompatibel; ein geänderter Werkzeughash macht alte Cache-Ergebnisse
sichtbar veraltet, berechnet aber beim Öffnen keine Bilder neu.

Die Parameterbeschriftungen, Modusbedingungen, Ressourcenbindungen und optionalen
Aktionen kommen aus den Manifesten. **Projektprofile …** gehört zum Grafikpaket.
**Referenzen / Materialien / Masken …** erscheint unter **Pipeline / Werkzeuge**
am Asset, wenn dessen wirksame aktive Pipeline den Farbschritt enthält. Die
bestehenden Referenz- und Maskendaten bleiben erhalten. Ein Malprogramm oder
obligatorischer Maskeneditor ist nicht Bestandteil des Umbaus.

**Pipelines ausführen …** öffnet den echten Bild-Dry-run. Die technische
Cache-Diagnose bleibt unter **Technische Werkzeuge → Cache-Diagnose …** zugänglich.
Sie zählt nicht als Grafikverarbeitung.

Ein zweites importierbares Beispiel liegt unter
`tools/AssetManager/examples/pipeline_frames/manifest.json`. Es wählt vorhandene
Frames aus und trennt Zielframes, FPS und Dauer. Beide Beispiele können über
denselben Canvas-Import, dieselbe Freigabe und dieselben Eigenschaften verwendet
werden; es gibt dafür keine neue Spezialoberfläche.

## Erweiterungsvertrag v2

Das [Manifest-Schema](../../../../schemas/asset-studio/pipeline-manifest-v2.json)
und `PluginService.validate_manifest` beschreiben den Vertrag. Ein Paket besteht
derzeit aus einem JSON-Manifest und genau einer benachbarten Python-Datei. Der
Import kopiert beide in das Projekt; andere Projekte teilen keine Registrierung
oder lokale Vertrauensfreigabe.

Der Verarbeitungseinstieg lautet:

```python
def apply(image, metadata, parameters):
    # Echte Verarbeitung auf einer RGBA-Arbeitskopie.
    return result_image, {"frame_size": [width, height], "profile": "scaled"}
```

`metadata` enthält die geprüfte Eingangsgeometrie. Der Host erlaubt begrenzte
Änderungen an Frame-Größe, Raster, vorhandener Frameauswahl, Zuschnitt, Profil
und Timing. Quellrevision, Quellhash, Slot, Anker und logische Größe bleiben
gebunden. Abgeleitete Pixelanker, Maßstäbe und Dauer berechnet und prüft der
Host. Neue Quellframes oder Animationseinstellungen für Einzelbilder werden
abgelehnt. Das tatsächliche PNG muss zur gemeldeten Geometrie passen.

Die deklarative Parameterliste erzeugt Eigenschaftenfelder einschließlich
Beschriftung und Erklärung. `visible_if`, `disabled_if` und `choice_labels`
steuern deklarativ Modusfelder und verständliche Auswahlnamen. Eine optionale Aktion erklärt `id`, `name` und
`entry_point`. Ihre Funktion erhält `(parent, parameters)` und gibt geprüfte
Parameter oder `None` zurück. Optional benennt `scope` den Kontext `step`
(Standard), `recipe` oder `asset`. Die beiden letzteren erhalten
`(context, parameters, parent)`; der Kontext enthält den Projektdienst und die
Rezept-/Asset-ID. Assetdienste bearbeiten ihre Ressourcen über bestehende
Dienste; Änderungen an Rezeptparametern erfolgen im Pipeline-Editor.
Der Anwendungskern enthält keinen neuen
Skalierungsdialog. Ohne Codefreigabe sowie nach Widerruf oder Entfernen der
Registrierung bietet der Canvas die Paketaktionen nicht an. Gespeicherte
Rezepte bleiben bei fehlendem Werkzeug als blockierte Entwürfe erhalten.

Bloßes Lesen, Importieren, Anzeigen oder Freigeben eines Pakets importiert
keinen fremden Python-Code. Bildverarbeitung läuft nach ausdrücklichem Start
im bestehenden Worker mit Timeout, Abbruch und Ergebnisprüfung. Eine optionale
interaktive Paketoberfläche läuft erst nach ihrem Aufruf im GUI-Prozess.
**Beide Prozesse sind keine Sicherheits-Sandbox.** Nur vertrauenswürdigen Code
freigeben. Paketversion, Codehash und Manifest werden in den Bildauftrag
eingefroren. Abhängigkeiten werden geprüft, nicht automatisch installiert.

## Kompatibilität und verbleibende Grenzen

- v1-Erweiterungen behalten ihren Vertrag: `apply(image, parameters)` mit einem
  gleich großen RGBA-Ergebnis. Es findet keine automatische Vertragsumdeutung statt.
- Die mitgelieferten Grafik-, Frame- und Farboperationen sowie die vorhandenen
  CLI-Werkzeuge bleiben benutzbar. Mitgelieferte Pakete sind Teil der geprüften
  Anwendung; fremder Python-Code nutzt den gesonderten Import-/Freigabevertrag.
- v2 hat derzeit einen Bildeingang und einen Bildausgang mit Metadaten. Allgemeine
  Mehrfacheingänge, mehrere Dateien pro Schritt, zusätzliche Paketmodule und
  ein freies Docking-System für UI-Erweiterungen sind noch nicht implementiert.
- Der Rezept-Export enthält weiterhin keinen Python-Code und keine Freigaben.
  Für den Transfer des Skripts Manifest und Python-Datei getrennt weitergeben
  und im Zielprojekt ausdrücklich importieren; die Quellen bleiben dort separat.
- Die lesbare Ablage ist eine verwaltete Darstellung des Katalogs, kein
  bidirektionaler Dateisystem-Editor. Manuelles Umbenennen von Kartenordnern
  außerhalb Studios wird nicht automatisch als Projektänderung übernommen.
- Alte Ergebnisstände und interne Jobdateien werden nicht automatisch bereinigt.
  Die zusätzliche sichtbare Kopie benötigt entsprechend Speicherplatz.
- Aufgaben und Issues bleiben Katalogeinträge mit Kanban-Bedienung. Die Markdown-
  Dokumentation stellt ihren aktuellen Status dar; sie ist kein zweiter Task-Editor.
- Ausführung bleibt wie beim vorhandenen Runner auf Linux beschränkt.

Prüfergebnisse und Wiederherstellungsstand stehen im
[Umbauplan](../plans/asset-studio-skriptplattform-korrektur.md).
