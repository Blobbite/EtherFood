# EtherFood Studio: zurück zur skriptbasierten Canvas-Plattform

Abschlussstand 28.09.2026: Der beauftragte Umbau einschließlich der Fortsetzung
ist technisch abgeschlossen; alle sieben Schritte dieser Fortsetzung sind
erledigt. Die folgenden Bestandsangaben beschreiben die jeweilige frühere
Arbeitsphase. Aktuelle Prüfergebnisse und Wiederherstellung stehen am Ende.
Persönliche Desktop-Abnahme, produktive Bildfreigaben, Godot-Bereitstellung und
die dort aufgeführten projektweiten Bestandsfehler bleiben getrennt davon.

## Entscheidung und Zweck

28.09.2026: Der Benutzer hat die bisherige Ausbauplanung gestoppt. Skalierung,
Frames, Farben und Masken sollen durch importierbare Python-Pipelines geliefert
werden. Benötigte Bedienoberflächen gehören zur jeweiligen Erweiterung und
werden über gemeinsame Dienste im Canvas eingebunden. Die sichtbare
Projektstruktur soll sich in der Ordnerstruktur wiederfinden.

Die bisherigen Asset-Studio- und Szeneneditor-Issues werden auf ausdrücklichen
Benutzerwunsch stillgelegt und als Historie erhalten. Ihre Schließung bedeutet
keine Fertigstellung oder Abnahme. Die frühere T-/SE-Reihenfolge ist kein aktiver
Implementierungsauftrag mehr. Historische Nachweise und Originalaufträge bleiben
erhalten. Dieses Dokument enthält die Bestandsbewertung und einen begrenzten
Korrekturvorschlag. Der Benutzer hat den Umbau anschließend beauftragt; der
erste zusammenhängende Umsetzungsschritt wird unten fortlaufend dokumentiert.

## Bestandsaufnahme

HEAD bei der Prüfung: `fefe137`. Die große Pipeline-Integration liegt in
`2286d2f`; spätere Commits enthalten auch unabhängige Game-/Control-Arbeit.
Zusätzlich liegen 56 geänderte/neue Dateien uncommitted im Arbeitsverzeichnis,
darunter Control-Korrekturen, Projektzuordnung und das letzte Maskenpaket.

Die zentrale Abweichung ist konkret im Code belegt:

- `application/plugin_service.py` beschränkt `studio-python-step-v1` auf ein
  RGBA-Bild mit unveränderter Geometrie und einfache Parameter. Ein importiertes
  Skalierungs- oder Frame-Skript kann diesen Vertrag nicht erfüllen.
- `pipelines/image_worker.py` erzwingt dieselbe Bildgröße nach dem Python-Aufruf.
  Die eingebauten Operationen verwenden dagegen einen besonderen Verarbeitungsweg.
- `domain/pipeline_recipes.py` und `application/recipe_builds.py` kennen konkrete
  Grafik-/Farb-/Frameoperationen. `pipelines/image_processing.py` implementiert
  deren Verzweigungen. Das ist eine feste Fachintegration, keine gleichberechtigte
  importierbare Skriptsammlung.
- `ui/pipeline_editor.py` erzeugt bereits Parameterfelder aus Manifestdaten,
  enthält aber auch Farb-/Timing-Sonderfälle und auf Bilder festgelegte Ports.
- `ui/asset_workspace.py` bindet `ui/reference_materials.py` direkt ein.
  Importierbare optionale UI-Dienste werden vom bestehenden Manifest nicht
  unterstützt. Ein weiterer fest eingebauter Maskeneditor würde das Problem
  vergrößern.

Weiterverwendbar sind Projektbesitz, stabile IDs, Canvas-Grundbedienung,
Speicherung, Undo/Redo, Quellenimport, Arbeitskopien, Jobs, Abbruch, Logs,
Ergebnisprüfung sowie Teile von Registrierung, Import und Parameterdarstellung.
Die vorhandenen Bildalgorithmen und CLI-Werkzeuge bleiben nutzbar.

## Zielbild und Zuständigkeiten

| Bestandteil | Aufgabe |
| --- | --- |
| Studio-Grundgerüst | Projekt/Canvas, Dateien, generische Parameter- und Ergebnisansicht, registrierte Aktionen, Jobs und Speicherung |
| Importierbares Pipeline-Paket | Python-Code, Manifest, Parameter, Ein-/Ausgaben, Vorlagen und optionale Bedienaktionen |
| Projekt-Rezept | Gewählte Paketversionen, Verbindungen, Einstellungen und Asset-Zuweisungen |
| Optionale Oberfläche | Vom Paket bereitgestellter Dialog oder Bereich, über eine allgemeine UI-Schnittstelle geöffnet |

Eingabefelder und Buttons bleiben möglich: Ihre fachliche Bedeutung kommt aus
dem Pipeline-Paket. Der Anwendungskern erhält keinen neuen Skalierungs-,
Farb- oder Masken-Spezialdialog für jedes Werkzeug.

Der gemeinsame Erweiterungsvertrag muss Bildgrößenänderungen, Frame-/Raster-
Metadaten, Ressourcen und mehrere ausdrücklich beschriebene Ergebnisse tragen
können. Der Host prüft diesen Vertrag und schützt Originale; die konkrete
Verarbeitung liegt im registrierten Python-Code. Bereits vorhandene v1-Rezepte
und Erweiterungen benötigen einen nachvollziehbaren Übergang.

Einfache Menüs entstehen aus deklarativen Parametern. Eigene interaktive
Oberflächen werden als optionale UI-Dienste desselben Pakets registriert und
bewusst geöffnet. Registrierung und bloßes Anzeigen eines Manifests führen
keinen fremden Code aus. UI-Code und Verarbeitungsjobs haben getrennte
Lebenszyklen; sie verwenden dieselben gespeicherten Projekt-/Rezeptdaten.
Vertrauensfreigabe, Originalschutz und Ergebnisprüfung bleiben im Grundgerüst.

## Ordner und Canvas

Die lesbare Ablage gehört zum normalen Projektablauf und wird nicht bis zu
einer vollständigen Godot-Freigabepipeline aufgeschoben. Fachliche Eltern und
Namen bestimmen den Pfad; freie Canvas-Positionen haben keine Pfadwirkung.
Pipeline-Karten gehören weiterhin direkt zum Projekt.

Präzisierung vom 28.09.2026: Das Pipeline-Rezept gehört zum Projekt; seine
Bildausgaben gehören zum jeweils verarbeiteten Asset. Geprüfte Ergebnisse
werden im Ordner dieses Assets gespeichert und dort nach Ausgabeart bzw.
Grafikprofil eingeordnet. Die bestehende Akt-/Kapitel-/Paket-Zugehörigkeit
bleibt erhalten; projektweite Assets behalten ihre Ablage unter `Projektweit`.
Auch bei einer Sammelausführung erhält jedes Asset seine eigenen Ergebnisse.
Der Ordner der Pipeline enthält deren Rezept und zugehörige Ressourcen; er
bildet keine zusätzliche Asset-Hierarchie für die erzeugten Bilder.

Beispiel für tatsächlich vorhandene Karten, keine verpflichtenden Zwischenebenen:

```text
Mein Projekt/
├── Skalierung/                 # Pipeline-Rezept und Ressourcen
├── Projektweit/
└── Akt 1/
    └── Kapitel 2/
        └── Tempelpaket/
            └── Wächter/
                ├── Quellen/
                └── Ergebnisse/
                    ├── comic_high/
                    └── comic_low/
```

Die gezeigten Profilordner sind Beispiele für angeforderte Ausgaben. Sie sind
keine zusätzlichen organisatorischen Karten und keine feste Profilliste.
Ergebnisse bleiben Ableitungen desselben Assets mit Verweis auf Quellstand,
Pipeline-Rezept und Profil. Sie werden nicht erneut als unabhängige Assets
importiert. Ein technischer Job-Ordner `output` dient zunächst der Verarbeitung;
erst nach erfolgreicher Ergebnisprüfung veröffentlicht der Host die Ausgaben
in der passenden Asset-Ablage.

Die technischen Innenordner eines Assets sind von organisatorischen Karten
unterscheidbar. Namen sind lesbar, Identitäten bleiben in Metadaten stabil.
Gemeinsam verwendete Assets besitzen eine kanonische Ablage beim Besitzer;
weitere Verwendungen verweisen darauf. Umbenennen und fachliches Verschieben
werden mit Dateiablage und Katalog konsistent übernommen, ohne Bildneubau.
Kollisionen und fremde Dateien werden berücksichtigt. Interne Jobs und Caches
können verborgen bleiben; fertige Ausgaben sind am Asset auffindbar.

## Beauftragter erster Umsetzungsschritt

Zunächst einen vollständigen Ablauf für **eine importierbare Skalierungspipeline**
beweisen. Keine erneute große Issue-Serie anlegen.

1. Aktuellen Code einschließlich uncommitteter Dateien dauerhaft als
   Wiederherstellungsstand sichern und Änderungen auf einem getrennten Branch
   gezielt bearbeiten. Die bisher angelegte Sitzungssicherung ist nur temporär.
2. Den vorhandenen Erweiterungsvertrag so ergänzen, dass `scale.py` Bildgröße
   und zugehörige Metadaten korrekt ändern darf. Den gemeinsamen Jobweg benutzen.
3. Paket importieren, im Projekt-Canvas anlegen, Asset zuweisen und Parameter
   aus seinem Manifest anzeigen. Ausführen, Vorschau und Ordner öffnen verwenden
   allgemeine Host-Aktionen. Eine optionale Paketaktion über denselben
   Registrierungsweg anbinden; keine fest codierte Skalierungs-Schaltfläche.
4. Geprüfte Ergebnisse im jeweiligen Asset-Ordner der tatsächlichen Projekt-/
   Akt-/Kapitel-/Paket-/Asset-Hierarchie speichern, nach Ausgabeart bzw. Profil
   einordnen und diese Zuordnung beim Neuladen erhalten.
5. Erst anhand dieses Ablaufs den weiteren Umbau eingrenzen. Vorhandene Fach-
   integrationen anschließend schrittweise als mitgelieferte Pakete herauslösen.
   Der Maskeneditor bleibt dabei eine mögliche Erweiterung, kein Pflichtausbau.

Abnahme dieses ersten Umbaus:

- Ein synthetisches 512×256-Bild wird durch importierten Python-Code mit Faktor
  0,5 zu 256×128; das Original bleibt bytegleich.
- Neue Paketparameter erscheinen ohne Änderung an der Studio-Oberfläche.
- Das Deaktivieren/Entfernen des Pakets entfernt dessen Bedienangebote; gespeicherte
  Rezepte mit fehlender Erweiterung bleiben verständlich erkennbar.
- Verarbeitung läuft im vorhandenen Hintergrundprozess mit Fehlern und Abbruch.
- Ordner entsprechen dem fachlichen Canvas-Besitz. Verschieben im Layout baut
  nichts neu; fachliches Umbenennen/Verschieben aktualisiert nur die Ablage.
- Dieselbe Pipeline verarbeitet zwei Assets aus unterschiedlichen Kapiteln;
  jedes Ergebnis liegt beim zugehörigen Asset und bleibt nach dem Neuladen
  dort zugeordnet. Dabei entstehen keine zusätzlichen Asset-Karten.
- Speichern/Neuladen und bestehende Projekte funktionieren weiter. Ein späteres
  zweites Skript kann über denselben Vertrag ergänzt werden.

## Rückbauentscheidung und Wiederherstellung

Empfehlung: gezielter Umbau auf dem vorhandenen Grundgerüst. Ein pauschaler
Reset auf einen alten Commit entfernt auch passende Pipeline-/Canvas-Arbeit
und spätere unabhängige Änderungen. Die uncommitteten Änderungen gehören nicht
zu einem solchen Commit und müssen separat erhalten werden.

In dieser Bestandsprüfung wurden keine Anwendungsdateien zurückgesetzt,
keine historischen Migrationen entfernt und keine Projektdaten gelöscht.
Vor einem späteren Rückbau werden betroffene Einstellungen und Datensätze
zugeordnet; veraltete Oberflächen sind kein Grund, ihre gespeicherten Inhalte
ungeprüft zu entfernen. Ein Neustart des gesamten Projekts ist durch den
geprüften Bestand nicht begründet.

## Fortschritt und Prüfungen dieser Entscheidung

- [x] Benutzerziel und Unterschied zu fest eingebauten Fachmenüs festhalten.
- [x] Benutzerpräzisierung festhalten: Ausgaben im jeweiligen Asset-Ordner
  kategorisieren; die Pipeline bleibt ein projektweites Rezept.
- [x] Git-Stand, bestehende Erweiterungsgrenzen und wiederverwendbare Teile prüfen.
- [x] Patch und alle 56 geänderten/neuen Dateien temporär außerhalb des
  Arbeitsbaums sichern; dies ersetzt keinen dauerhaften Git-Sicherungsstand.
- [x] Noch offene Planungs-Issues als `not_planned` schließen und nachprüfen;
  Inhalte, Kommentare und bereits geschlossene Issues erhalten.
- [x] Zugehörige Meilensteine stilllegen und aktive Dokumentation umstellen.
- [x] Dokumentationslinks, Diff und Integrität des historischen Plans prüfen.

Tatsächliches Ergebnis dieser Runde:

- **59 offene Planungs-Issues** geschlossen, jeweils mit `state_reason: not_planned`:
  #1, #3–#7, #20–#55 und #60–#76. **17 bereits geschlossene Issues** unverändert.
  Alle 76 Planungs-Issues erneut gelesen: Titel, Beschreibung, Kommentare,
  Labels, Zuständigkeiten und Meilensteinzuordnung gegenüber dem Ausgangsstand
  unverändert. [Studio-Historie](https://github.com/Blobbite/EtherFood/issues/1),
  [Szeneneditor-Historie](https://github.com/Blobbite/EtherFood/issues/60).
- **10 zugehörige Meilensteine** geschlossen; Titel, Beschreibung und Termine
  erhalten und nachgeprüft. Dies ist eine Stilllegung, keine Abschlussabnahme.
- Dokumentationsübersichten und `tools/AssetManager/works/AGENTS.md` verweisen
  auf diese Entscheidung. Frühere T-/SE-Startanweisungen sind historisch eingeordnet.
- `git diff --check` sauber. 112 lokale Links in den sechs geänderten/neuen
  Dokumenten auf vorhandene Ziele geprüft.
- `python3 tools/AssetManager/works/EtherFood_Codex_Aufgabenplan/pruefung/check_plan.py --json`:
  erfolgreich, 48 Aufgaben, 36 Anforderungen, 955 lokale Links und 81
  unveränderte geschützte Dateihashes.
- 41 bereits geänderte/neue Nicht-Markdown-Dateien mit der Sitzungssicherung
  verglichen: bytegleich. Kein Git-Reset, kein neuer Commit und keine Änderung
  an Anwendungslogik, CLI, Tests, Originalbildern oder Projektkatalogen.

In der vorherigen Bestandsrunde wurde ausschließlich die Planung korrigiert.
Skriptvertrag, UI-Dienst und Ordnerabgleich waren zu diesem Zeitpunkt noch
nicht implementiert. Anwendungs-, Bild-, GUI- und Godot-Tests wurden für diese
reine Entscheidungs-/Dokumentationsänderung nicht erneut ausgeführt.

## Umsetzung nach Benutzerfreigabe

28.09.2026, damaliger Sitzungsstand: Der erste Umbau ist beauftragt. Arbeitsbranch:
`refactor/studio-script-platform`. In dieser Sitzung wurde der lokale Sicherungsbranch
`backup/studio-before-script-platform-20260928` mit Commit `1be69ab` angelegt,
der alle 59 zuvor geänderten/neuen Dateien sowie den bisherigen HEAD enthielt.
Main und der bisherige Index wurden dabei nicht verändert; zu diesem Zeitpunkt
wurde nichts gepusht. Diese lokale Sicherung ist im aktuellen Clone nicht
vorhanden; verfügbare Git-Stände sind unten unter **Abschluss und Wiederherstellung**
aufgeführt.

- [x] Bestand geprüft und vollständigen lokalen Git-Wiederherstellungsstand angelegt.
- [x] Versionierten Skriptvertrag für Geometrie und Metadaten ergänzen.
- [x] Skalierungspaket über Canvas importieren, konfigurieren und ausführen;
  optionale Paketaktion über generischen Einstieg anbieten.
- [x] Fachliche Kartenhierarchie als lesbare Ordner abbilden; Quellen und
  geprüfte Ergebnisse beim Asset ablegen und Umbenennen/Umordnen unterstützen.
- [x] Integration, Kompatibilität, Fehlerfälle und Canvas-Bedienung prüfen.
- [x] Tatsächliche Bedienung und verbleibende Grenzen dokumentieren.

### Tatsächlich umgesetzt

- `studio-python-step-v2` erweitert den bestehenden Bildadapter um RGBA-Bilder
  mit geprüften Geometrie-/Frame-Metadaten. Der v1-Vertrag bleibt unverändert.
  Neue Felder haben ein deklaratives Schema; Registrierung und Projektöffnung
  importieren keinen fremden Python-Code.
- `examples/pipeline_scale/` enthält Manifest, echte proportionale Skalierung
  mit dem bestehenden Comic-Verfahren und eine optionale Paketoberfläche.
  Der Canvas-Import legt eine Projektkopie als Rezeptkarte an. Die gemeinsame
  Eigenschaftenansicht erzeugt Felder und Aktionen aus dem Manifest. Freigabe
  erfolgt getrennt; Widerruf und Entfernen blenden Paketaktionen aus.
- Eine Paketaktion verändert dieselben Parameter über die bestehende
  Undo-Historie. Der Editor zeigt beim ersten Öffnen beide Verarbeitungsknoten
  vollständig und wählt bei Skriptrezepten den importierten Schritt vor.
  Der bisherige Profildialog wird nur bei einem vorhandenen Grafikprofile-
  Schritt angeboten.
- Migration 8 ergänzt lokale Pfad-, Datei- und Veröffentlichungslisten.
  `ProjectFiles` bildet fachliche Eltern und Namen ab, nicht Canvas-Koordinaten.
  Pipeline-Code und Rezept liegen bei der Pipeline, Quellen und Bildausgaben
  beim zugehörigen Asset. Ein zusätzlicher Verwendungslink dupliziert nichts.
- Kopien werden überprüft und mit der äußeren Katalogtransaktion koordiniert.
  Ein Dateijournal unterstützt Fehler-Rücknahme und Wiederaufnahme nach einem
  Prozessabbruch. Namenskollisionen mit unverwalteten Ordnern führen bei neuer
  Ablage zu einem ID-Zusatz; Umordnen überschreibt keine vorhandenen Ziele.
  Eine Ablagefehler-Meldung ist ein unvollständiger Lauf, kein Veröffentlichungserfolg.
- Vollständige Bildläufe erzeugen `Ergebnisse/<Profil>/` und `aktuell.json`
  beim Asset. PNG und Metadaten bleiben versionierte Ableitungen; Bild- und
  Quellenrevisionen werden nicht als neue Asset-Karten angelegt. Ein beschädigter
  historischer Cache verhindert nicht das reguläre Öffnen des Projekts.
- **Ordner öffnen** steht im Karten-Kontextmenü bereit. Fachliches Umbenennen
  und Umordnen einschließlich Undo bewegen die Ablage mit, ohne Bildneubau.

### Prüfungen und Erkenntnisse

- `python3 tools/control.py asset-manager test`: **649 bestanden**.
- `python3 tools/control.py asset-manager pipeline-test`: **171 bestanden**.
- Nach der abschließenden Korrektur des Editor-Bildausschnitts:
  `test_script_platform_ui.py`, `test_pipeline_editor.py` und
  `test_pipeline_auxiliary.py`: **37 bestanden**. Die spätere Änderung betraf
  nur die UI; Worker und Bildalgorithmen wurden danach nicht verändert.
- 25 neue Testfälle beweisen unter anderem Skriptimport ohne Codeausführung,
  zwei Kapitel mit derselben Pipeline, 512×256 → 256×128, maximale Kante,
  kein Upscale, Frame-Raster/Timing, einen zweiten echten Frame-Skriptschritt,
  Paketaktionen, Parameter-Undo, Cache, Fehler, Abbruch, Codewiderruf,
  Schema, Dateikonflikte und Wiederaufnahme.
- Visuelle Qt-Prüfung mit einem synthetischen Projekt und echtem Bildbuild;
  keine Produktionsbilder verarbeitet. Dabei wurde der anfangs abgeschnittene
  zweite Pipeline-Knoten entdeckt und korrigiert.
- Drei bisherige Tests mussten an das ausdrücklich neue Verhalten angepasst
  werden: Karten legen nun Ordner/Journale an, aber weiterhin keine Bildjobs
  oder importierten Quellen. Ein zweites Snapshot-Projekt erhält einen eigenen
  Ordner statt eines zweiten Katalogs in derselben Projektwurzel.
- `python3 tools/control.py check`: **283 bestanden, 37 übersprungen,
  4 bekannte Fehler außerhalb dieses Umbaus**. Weiterhin fehlen die vorbereiteten
  Greenhero-Assetkategorien, `window/size/resizable=true` sowie die Spielentscheidungs-
  Übersicht/ADR-0008 mit den zugehörigen Verweisen. Der globale Stilcheck meldet
  weiterhin 1903 Bestandsbefunde. Geänderte Python-Zeilen wurden separat geprüft.
- **Godot-Import und Godot-Integration nicht ausgeführt:** Godot 4 ist in dieser
  Umgebung nicht installiert. Die zentralen Prüfungen melden dies ausdrücklich.
- Abschlussprüfung: `git diff --check` sauber; 24 geänderte Python-Dateien mit
  **0 Stilbefunden auf den geänderten Zeilen**, 62 lokale Links der geänderten
  Markdown-Dokumente erreichbar. Die historische Planintegrität ist weiterhin
  erfolgreich: 48 Aufgaben, 36 Anforderungen, 955 Links, 81 unveränderte Hashes.
  Von den 59 zuvor geänderten/neuen Dateien sind 49 bytegleich zur Sicherung;
  die übrigen zehn wurden gezielt für diesen Umbau weiterbearbeitet.

### Bedienung, Kompatibilität und nächster Schnitt

Die vollständige Bedienfolge und die v2-Schnittstelle stehen unter
[Skriptpakete und Asset-Ablage](../asset-studio/SKRIPTPAKETE.md).
Der erste beauftragte Ablauf ist implementiert. Die älteren fest integrierten
Grafik-, Farb- und Maskenoberflächen sind damit noch nicht vollständig in Pakete
ausgelagert; ihre gespeicherten Daten und CLI-Abläufe bleiben nutzbar. Eine
weitere Auslagerung wird anhand dieses funktionierenden Vertrags eingegrenzt.
Es wurden keine alten Issues wieder geöffnet oder neue Serien angelegt.

Aktuelle Grenzen: ein Python-Modul und ein Bildein-/ausgang je importiertem Paket,
keine allgemeinen Mehrfacheingänge oder frei andockbaren Erweiterungsfenster.
Der Rezept-Export enthält weiterhin keinen Python-Code und keine Freigaben.
Sichtbare Dateien bilden den Katalog ab; externe Ordneränderungen werden nicht
automatisch zurückimportiert. Historische Ausgaben und interne Jobs bleiben
erhalten; eine Bereinigung wurde nicht implementiert. Das äußere Projektverzeichnis
wird durch Umbenennen der Projektkarte nicht verschoben.

Der genannte lokale Sicherungsbranch war die Wiederherstellungsmöglichkeit
dieser damaligen Sitzung; seine Verfügbarkeit in anderen Clones ist nicht gegeben.
Zusätzlich erzeugt die Katalogmigration ihre reguläre SQLite-Sicherung.
Keine pauschale Rücksetzung, kein Löschen alter Projektdaten und keine Änderung
an produktiven Spielassets erfolgte.

## Fortsetzung: vollständiger Bedienweg und automatische Dokumentation

28.09.2026: Der Benutzer beauftragt den weiteren Umbau und präzisiert ihn mit
einem Canvas-Entwurf und einem Ordnerbaum. Akte sind Geschwister im Projekt;
Kapitel gehören zu ihrem Akt. Pipelines liegen projektlokal in `.pipelines`.
Assets werden innerhalb ihres Besitzbereichs unter `Assets/<Typ>/` eingeordnet;
Pakete bleiben erhalten. Ausgaben bleiben ausschließlich bei ihrem Asset.
Die bestehende Katalog-/Jobablage bleibt erhalten; `.db` im Entwurf beschreibt
technische Daten, keinen Auftrag zum Austausch der SQLite-Persistenz.

Jeder Bereich erhält einmalig ein Grunddokument. Strukturteile, Verweise und
Bildertabellen werden automatisch gepflegt, eigener Markdown-Text bleibt
erhalten. Mehrere Dokumente pro Bereich sind möglich. Eine Startseite verlinkt
Bereiche, Asset-Typen, Pipelines und Planungsinhalte. Notizen sowie Aufgaben und
Issues verwenden die vorhandenen Dokument-/Kanban-Dienste. Es entsteht keine
zweite konkurrierende Projektstruktur. Alte Planungs-Issues bleiben stillgelegt.

### Schritte und Abnahme dieser Fortsetzung

- [x] Bestand und Entwurf abgleichen, vorherigen Umsetzungsschritt im lokalen
  Branch `backup/studio-before-documentation-20260928` in der damaligen Sitzung
  sichern; Verfügbarkeit im aktuellen Clone siehe Abschluss und Wiederherstellung.
- [x] Typbezogene Asset-Ablage und `.pipelines` mit sicherer Bestandsübernahme,
  Umbenennen, Umordnen und Undo integrieren.
- [x] Grunddokumente, Startseite, Typ-/Asset-Indizes und Bildtabellen automatisch
  erstellen; weitere Dokumente und eigene Texte erhalten, Konflikte erkennen.
- [x] Vorhandene Fachaktionen über deklarierte Pipeline-Pakete und einen
  gemeinsamen UI-Einstieg bereitstellen; Skripte bleiben im gemeinsamen Runner.
- [x] Dokumentations-/Planungszugänge im Canvas verständlich verbinden;
  bestehende Guards, Revisionen und Projektgrenzen erhalten.
- [x] Synthetische Integrations- und UI-Tests einschließlich Wiederöffnung,
  Strukturänderung, echter Bildausgabe, Konflikten und manuellen Texten ausführen.
- [x] Bedienung, Kompatibilität, tatsächliche Testergebnisse und Grenzen dieser
  Fortsetzung dokumentieren.

Maßgebliche Nachweise: zwei Akte mit Kapiteln, Typen und Assets; dieselbe Pipeline
liefert echte Bilder ausschließlich an ihre Assets. Ein neuer Akt ergänzt den
Startindex, jeder Bereich hat genau ein automatisch angelegtes Grunddokument,
zusätzliche Dokumente bleiben möglich. Die Profilübersicht enthält relative
PNG-Links und Vorschaubilder. Verschieben/Umbenennen und Undo aktualisieren
Verweise ohne Bildneubau. Externe Dateien und eigene Markdown-Texte werden
nicht still überschrieben. Bestehende Rezepte, Quellen, Maskendaten und CLI-
Befehle bleiben benutzbar. Keine Produktionsassets neu berechnen.

### Umsetzung und Erkenntnisse der Fortsetzung

- `.pipelines/<Rezept>/` enthält Rezepte und Paketdateien. Die physische
  Asset-Ablage verwendet den tatsächlichen Typ aus der Asset-Definition;
  bestehende Pakete bleiben als Besitzer erhalten. Die Projekt-/Akt-/Kapitel-
  Zugehörigkeit und IDs ändern sich dadurch nicht.
- Migration 9 ergänzt die Dokument-Dateizuordnung. Pro Bereich gibt es eine
  stabile Grunddokument-ID; `Index.md`, Bereichs-, Typ- und Profilübersichten
  werden in der bestehenden Datei-/Katalogtransaktion gepflegt. Die Startseite
  enthält auch die lesbare Ordnerstruktur. Manuelle Texte, zusätzliche Dokumente,
  Notizen, Aufgaben und Issues bleiben in den vorhandenen Diensten.
- Bekannte Markdown-Dateien können extern bearbeitet werden. Automatikmarkierungen
  grenzen aktualisierbare Inhalte ein; konkurrierende Änderungen werden
  abgewiesen. Fehlende Marker und Schreibfehler führen zur Rücknahme, nicht zum
  stillen Überschreiben. Die Migration von Version 8 einschließlich SQLite-
  Sicherung und Ordnerübernahme wird explizit getestet.
- Grafik-/Frame-/Farbverarbeitung liegt in `packages/`; deklarative Manifeste
  liefern Vorlagen, Modusfelder und optionale Dienste. Der gemeinsame Bildadapter
  und die bestehenden PyGameTools-Algorithmen bleiben erhalten. Das Farbpaket
  bietet seine Referenz-/Maskenoberfläche nur für eine zugewiesene aktive
  Pipeline an. Fremde v2-Pakete können nach Freigabe ebenfalls Schritt-, Rezept-
  und Assetdienste anbieten. Ein zweites Frame-Beispiel nutzt denselben Vertrag.
- Die Hauptaktion öffnet den echten Pipeline-Dry-run. Die Cache-Diagnose ist
  ausdrücklich unter den technischen Werkzeugen einsortiert.
- Die erste breite Prüfung zeigte Canvas-Überlagerungen durch automatisch
  sichtbare Dokumentkarten. Grunddokumente bleiben deshalb standardmäßig beim
  Bereich im Baum und Dokumentreiter erreichbar; eine zusätzliche Canvas-Karte
  wird über das Dokument-Kontextmenü bewusst eingeblendet und ist rückgängig
  machbar. Bestehende Layouts bleiben unverändert. Die Suche zählt automatisch
  erzeugte Linktexte nicht mehrfach als Treffer.
- Die visuelle Prüfung zeigte außerdem einen veralteten, bereits geöffneten
  Startseitenstand. Unveränderte Editoren laden nun neue Dokumentrevisionen beim
  Aktualisieren und Öffnen nach. Ungespeicherte eigene Texte bleiben geschützt.
  Automatikmarkierungen sind in der gerenderten Vorschau unsichtbar; im
  Markdown-Quelltext bleiben sie erhalten.

Zwischenstand vor dem Sitzungsabbruch: 11 neue Service-/Migrationstests und
86 gezielte Prüfungen der betroffenen Bedienwege erfolgreich; die
171 PyGameTools-Tests bestanden. Der vollständige Studio-Lauf nach den
Korrekturen und der abschließende Bericht standen damals noch aus.

### Abschlussprüfung vom 28.09.2026

Ausgangsstand der Wiederaufnahme ist `4c075c8` auf `main`: PR #77 enthält mit
`04330f1` den vollständigen bisherigen Umbau. Bei Beginn war der Arbeitsbaum
sauber. In der Bestandsprüfung bestanden bereits alle **670 Studio-Tests**
und **171 PyGameTools-Tests**. Die letzte offene Prüflücke ist durch
`tools/AssetManager/tests/gui/test_studio_completion.py` geschlossen.

Der neue zusammenhängende Qt-Test ist einzeln erfolgreich ausgeführt
(**1 bestanden**, 9,45 s). Er belegt:

- Zwei gleichrangige Akte mit gleichnamigen Kapiteln, zwei Asset-Typen und einem
  Asset-Paket. Ein über das Canvas importiertes und bewusst freigegebenes
  Skalierungsskript verarbeitet beide Assets im gemeinsamen Sammellauf.
- Zwei echte 512×256-Quellen ergeben jeweils 256×128-PNGs. Geprüfte Ausgaben,
  Metadaten und Galerien liegen ausschließlich beim jeweiligen Asset;
  die ursprünglichen Dateien bleiben anhand ihrer Hashes unverändert.
- Jeder Bereich besitzt genau ein stabiles Grunddokument. Eine zusätzliche
  Anleitung und eigener Markdowntext bleiben erhalten. Ein neuer Akt erscheint
  auch auf der bereits geöffneten Startseite; relative Dokument- und PNG-Links
  sowie die tatsächlich geladenen Qt-Bildvorschauen funktionieren.
- Verschieben eines ganzen Pakets in den anderen Akt, Undo/Redo und Umbenennen
  eines Kapitels aktualisieren Ablage und Links. Build-IDs, Bildhashes, Metadaten
  und Jobdatensätze bleiben unverändert; keine zusätzliche Asset-Karte entsteht.
- Fremde Dateien und eigene Galerieabsätze bleiben erhalten. Gleichzeitige
  externe und interne Dokumentänderungen führen zu einem sichtbaren Konflikt;
  beide Texte bleiben verfügbar und lassen sich anschließend bewusst zusammenführen.
- Nach vollständigem Schließen und Öffnen in einer neuen Studio-Fensterinstanz
  bleiben Katalog, Grunddokument-IDs, lesbare Dateien, Zuordnungen und Ergebnisse
  identisch. Die Startseite öffnet das verschobene Dokument mit allen eigenen Texten.

Der erste vollständige Lauf mit dem neuen Test meldete 670 bestandene Tests
und einen sporadischen Fehler in der vorhandenen Drag-Hover-Prüfung des
Projektbaums: Der erwartete Ast war nach der festen Pause von 850 ms noch
nicht geöffnet. Im direkten Nachbarschaftslauf bestanden alle 18 Tests;
15 zusätzliche Wiederholungen des bisherigen Hover-Ablaufs waren ebenfalls
erfolgreich. Die Prüfung scrollt das Ziel nun bewusst sichtbar, verarbeitet
das ausstehende Layout, prüft die angenommenen Drag-Ereignisse und wartet
begrenzt auf das tatsächliche Qt-Aufklappsignal. Timer und Drag-Zustand
werden auch bei einem Fehler aufgeräumt. Der Produktcode bleibt unverändert.
Nach dieser Anpassung bestehen die 18 zusammen ausgeführten End-to-End- und
Baumansichtstests erneut (39,31 s). Die gezielten Control-, Community- und
Repository-Metadatenprüfungen bestehen ebenfalls: 98 Tests in 3,09 s.

Der abschließende vollständige Lauf
`python3 tools/control.py asset-manager check` ist nach dieser
Teststabilisierung erfolgreich (Exitcode 0), einschließlich echter
Qt-Offscreen-Prüfungen und synthetischer Bildjobs:

- **671 Studio-Tests bestanden**, 483,93 s; keine übersprungenen Tests.
- **171 PyGameTools-Tests bestanden**, 45,40 s.

Die sieben Schritte dieser Fortsetzung sind damit abgeschlossen. Die
Einstiegspunkte in README und Planübersicht verweisen auf diesen aktuellen
Stand statt auf die stillgelegte Ausbauplanung. Geänderte Markdown-Verweise,
beide Testdateien und der abschließende Diff sind separat geprüft.

Der unabhängig davon erneut ausgeführte Standardlauf
`python3 tools/control.py check` meldet **284 bestanden, 37 übersprungen,
3 Fehler**. Die verbleibenden Bestandsbefunde sind:

- `test_display_uses_reviewed_16_9_reference_contract`: In `game/project.godot`
  fehlt der erwartete ausdrückliche Eintrag `window/size/resizable=true`.
- Zwei Dokumentationsprüfungen: `docs/game/decisions/index.md` und
  `docs/game/decisions/ADR-0008-achtteiliger-spielablauf.md` fehlen;
  13 bestehende Verweise betreffen diese Dateien.
- Der globale Stilcheck meldet 1903 Bestandsbefunde. Beide in dieser
  Abschlussprüfung ergänzten beziehungsweise angepassten Testdateien haben
  keine Stilbefunde. Die historische Planprüfung ist erfolgreich:
  48 Aufgaben, 36 Anforderungen, 955 Links, 81 unveränderte geschützte Hashes.
- Godot 4 ist in dieser Umgebung nicht installiert; Ressourcenimport und
  Engine-Integration konnten daher nicht ausgeführt werden.

Die früher zusätzlich gemeldeten fehlenden Greenhero-Unterordner wurden im
aktuellen Standardlauf nicht mehr beanstandet. Die Studio-Abschlussprüfung
umfasst synthetische Daten und Qt-Offscreen-Bedienung. Persönliche Desktop-
Abnahme, produktive Bildfreigaben und Godot-Bereitstellung bleiben separate
Schritte; die bekannten Spiel-/Dokumentationsbefunde sind kein Teil dieses Umbaus.

### Abschluss und Wiederherstellung

Die Bedienung, Migrationen, Kompatibilität und Produktgrenzen stehen unter
[Skriptpakete und Asset-Ablage](../asset-studio/SKRIPTPAKETE.md). Es bleiben
ein Python-Modul sowie ein Bildein-/ausgang je importiertem Paket, bewusste
Codefreigabe, verwaltete Katalogablage und gesonderter Import externer Dateien.
Mehrfachausgaben, frei andockbare Erweiterungsfenster, automatisches Übernehmen
externer Ordneränderungen und Bereinigung alter Ausgaben sind keine
Abschlusskriterien dieser Fortsetzung.

Im aktuellen Clone existieren die beiden oben genannten lokalen
`backup/studio-before-*`-Branches und das Objekt `1be69ab` nicht. Sie dürfen
deshalb nicht als hier verfügbarer Wiederherstellungspunkt angegeben werden.
Verfügbar sind der ausgelieferte Umbau `04330f1`, sein Merge `4c075c8` sowie
der Vorgänger `fefe137`. Der Vorgänger bildet den Stand vor PR #77 ab, nicht
die fehlenden lokalen Zwischensicherungen. Zum Vergleichen einen getrennten
Checkout des gewünschten vorhandenen Commits verwenden. Benutzerprojekte
liegen außerhalb dieses Git-Codestands und benötigen ihre eigenen Sicherungen;
Katalogmigrationen erzeugen weiterhin die dokumentierten SQLite-Sicherungen.
