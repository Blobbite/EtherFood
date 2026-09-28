# Architektur und Datenverträge (T002)

Für den aktuellen Umbau gilt die
[Korrektur zur skriptbasierten Canvas-Plattform](../plans/asset-studio-skriptplattform-korrektur.md).
Die frühere Issue-Reihenfolge ist stillgelegt. Der gemeinsame Unterbau bleibt
erhalten; vorhandene Dienste werden nicht parallel neu implementiert.

## Schichten und Zuständigkeiten

`tools/AssetManager/src/etherfood_studio/` ist ein eigenes Python-Paket.
Der bestehende `g2dtool`-Start und die PyGameTools-Starter bleiben erhalten.

| Schicht | Aufgabe | Zulässige Abhängigkeiten |
| --- | --- | --- |
| domain | Typen, Relationen, Statusregeln | Python-Standardbibliothek |
| application | Anwendungsdienste, Befehle, Konflikte | domain, storage-Schnittstellen |
| storage | SQLite, sichere Pfade, Blobs, Journale | domain, Standardbibliothek; Pillow bei Bildimport |
| pipelines | registrierte Adapter, Auftragsverträge und Supervisor | domain/storage; kein Qt |
| packages | deklarative Vorlagen, Python-Verarbeitung und bewusst aufgerufene UI-Dienste | Discovery: nur JSON; Verarbeitung: pipelines/domain; UI-Dienste: ui/application |
| godot | späterer Export/Deployment-Adapter | application/domain; kein Qt |
| ui | PySide6-Desktop | application; kein SQL in Widgets |

`domain.pipeline_recipes` liest ausschließlich deklarative mitgelieferte Manifeste.
Der gemeinsame Runner lädt die Verarbeitung erst bei der Ausführung. Der UI-Host
erzeugt Parameter und optionale Aktionen aus diesen Manifesten. Freier Python-Code
bleibt im gesonderten, hashgebundenen Pluginvertrag.

Migration 9 und `ProjectDocuments` ergänzen `ProjectFiles` um kataloggebundene
Markdown-Dateien. Grunddokumente besitzen eine feste Identität pro Besitzer;
Automatikblöcke und eigene Texte bleiben getrennt. Katalog, Kartenordner und
Dokumente werden gemeinsam mit dem vorhandenen Dateijournal abgeglichen.
Die genaue Ablage und Bedienung stehen unter [Skriptpakete](SKRIPTPAKETE.md).

CLI und GUI verwenden dieselben Dienste. Importe starten keine Arbeit.
Noch nicht implementierte Pipeline-/Godot-Aktionen werden deaktiviert.
Ein lokaler kontrollierter Schreiber nutzt kurze SQLite-Transaktionen,
`foreign_keys=ON`, `schema_version` und `revision_no` zur Konflikterkennung.
JSON-Snapshots sind keine zweite aktive Datenbank.

## Modell und Identität

Alle Objekte besitzen eine UUID, UTC-Zeiten und getrennte Anzeigenamen.
Project besitzt genau einen globalen Rahmen. Act gehört zum Projekt,
Chapter zum Act. Card-Typen umfassen außerdem Asset, Paket und freie Notiz.
`belongs_to` beschreibt Eigentümerschaft; `uses` verweist mehrfach auf
dasselbe Objekt; `depends_on` beschreibt echte Voraussetzungen und ist
zyklenfrei. CardLayout liegt separat; Position/Zoom/Größe sind keine
Build-Eingaben. Archivieren ist reversibel und löscht keine Bytes.

Spätere Modelle werden als versionierte Verträge vorbereitet, nicht als
bereits vorhandene Verarbeitung ausgegeben:

| Modell | Bindung / Invariante |
| --- | --- |
| Asset, Pose | Besitzer-ID, Typ; `stand`, Richtung und Timing getrennt |
| SourceRevision | Originaldigest, Länge, Typ, Herkunft; unveränderlich |
| ProfileRevision, MaskRevision | feste Inhaltsrevision; Maske zusätzlich an Quellhash gebunden |
| Build | konkrete Eingaberevisionen und Input-Fingerprint |
| Check | konkretes Build/Export, Kontext und tatsächliches Ergebnis |
| Review | exakte Build-ID, Scope und Entscheidung; niemals `latest` |
| Approval | festes Candidate/Export und überprüfte Nachweise |
| Deployment | Export-ID, Besitzliste und Wiederaufnahmejournal |

Dokumente besitzen unveränderliche Textrevisionen. Generierte Berichte sind
ein anderer Dokumenttyp als Benutzertext. Tasks/Issues beziehen sich per ID
auf Karten; Fundstellen können Build/Pose/Richtung/Profil/Frame nennen.

## Austauschverträge

Das versionierte [JSON-Schema](../../../../schemas/asset-studio/contracts-v1.json)
definiert VariantKey, BuildRequest, BuildResult, RuntimePayload,
DeploymentJournal und Review. Unbekannte Felder/Versionen werden abgelehnt.
Optionale Dimensionen statischer Assets sind `null`, keine erfundene Animation.
Input-Fingerprint, SHA-256 der Ausgabebytes und Deployment-Payload-Digest
haben getrennte Felder. Geometrie/Raster und Timing gehören zum jeweiligen
Ergebnis, volatile Logzeiten nicht zum Fingerprint.

## Fehler, Sicherheit und Grenzen

Strukturierte Fehler: `validation`, `conflict`, `unavailable`, `integrity`,
`cancelled`, `storage`. Meldung und technische Details sind getrennt;
Logeinträge tragen eine Auftrags-ID. Keine Telemetrie und kein Geheimnisexport.
Standardgrenzen: 64 MiB Importdatei, 32 Millionen Bildpixel, 1 MiB Markdown,
64 MiB Metadaten-Snapshot; vor Kopieren zusätzlich freier Speicher prüfen.
Größere echte Produktionsassets benötigen später eine bewusste Konfiguration.

Schreibwurzeln müssen existieren, symlinkfrei und ohne Überlappung sein. Jeder
Schreibzugriff prüft seine Grenze erneut. Importe kopieren über Laufwerke,
prüfen Hash/Länge und registrieren danach; sie behaupten keine atomare
Cross-Device-Verschiebung. Journale und verwaiste Dateien werden nur gemeldet.
Keine Sicherheitsgarantie gegen einen bösartigen zweiten OS-Benutzer;
lokale Einzelbenutzerdaten, kein gemeinsam beschreibbares Netzlaufwerk.

Statuswerte: `not_started`, `waiting_external`, `ready`, `running`, `blocked`,
`failed`, `cancelled`, `passed`, `stale`, `not_required`. Letzteres erfordert
einen Typgrund. `skipped` oder fehlende Tools zählen nie als Erfolg.
Bearbeitung, Build, Sichtabnahme, Godot-Test und Runtime bleiben getrennt.
Neue Entwürfe entwerten keine historische Freigabe eines alten Builds.

## Ergänzung Paket 5

Asset-Anforderungen verwenden [Schema Version 1](../../../../schemas/asset-studio/asset-definition-v1.json)
und zusätzliche semantische Domain-Prüfungen. Pose-UUIDs und externe
Bestandsbeobachtungen gehören zur Asset-Karte; sie sind keine Build-Ergebnisse.
Der [lesende Scanner](INVENTORY.md) darf ausdrücklich ausgewählte Unterordner
einer bestehenden Wurzel erfassen, legt dort aber nichts an. Diese Lesewurzeln
sind in Migration 3 separat lokal gebunden und fehlen im portablen Snapshot.
Qt-Lesearbeiter schreiben nicht in SQLite; die kurze, explizite Übernahme
erfolgt nach erneuter Datei-/Revisionsprüfung über den Anwendungsdienst.

## Ergänzung T017

Migration 4 und [Auftragsverwaltung](JOBS.md) halten lokale Ausführungsnachweise
von transportierten Metadaten getrennt. CLI und QProcess benutzen denselben
Supervisor und den eingefrorenen Vertrag `studio-job-v1`. Registrierung,
Hashprüfung und sichere Argumentlisten ersetzen keine Sandbox für fremde
Werkzeuge. Im ursprünglichen Paket waren ausschließlich Diagnose und lesender
Help-Aufruf freigegeben. Projektpipelines ergänzen inzwischen den geprüften
Bildadapter; Godot-Bereitstellung bleibt separat gesperrt.

## Ergänzung T018

Der [Buildplan](BUILDPLAN.md) ist ein eigener typisierter DAG, keine Ableitung
aus Canvas-Positionen oder Projekt-Hierarchie. Migration 5 registriert nur
lokal geprüfte Ergebnisse im Cache; portable Snapshots bringen keine
Cache-Vertrauensstellung mit. Input-Fingerprint, vollständige Ausgabedigestliste
und Digests der tatsächlichen Vorgängerresultate werden separat geprüft.
Dry-run ist schreibfrei, in der CLI sogar mit SQLite-Nur-Lese-Verbindung.
Die neun Diagnosephasen bleiben als technische Selbstprüfung ausführbar.
Echte Bildrezepte verwenden inzwischen denselben Buildplan und Cache.

## Ergänzung: projektweite Canvas-Pipelines

Migration 6 ergänzt die lokale, hashgebundene Pluginregistrierung. Projektprofile
liegen versioniert am bestehenden Projektobjekt. Rezepte sind `pipeline`-Karten
direkt unter dem Projekt, als Geschwister des einzigen globalen Rahmens;
`pipeline_assignment`-Objekte verweisen auf sie. Projektstandard- und Typregeln
gehören zum Projekt, explizite Zuweisungen zum jeweiligen Asset. Migration 7
übernimmt ältere Besitzer transaktional mit Sicherung und zusätzlicher Revision;
IDs, Rezeptdaten und historische Snapshots bleiben erhalten. Knotenlayouts
bleiben in `layouts`, technische Verbindungen und Parameter
im Rezept. Projektbeziehungen erhalten keine ausführbare Bedeutung.

`PipelineService`/`ProfileService` verwalten Revisionen und Zuweisungsprioritäten.
`RecipeBuildService` übersetzt in den bestehenden DAG, `studio-image` führt echte
PyGameTools-Bildalgorithmen über `JobService`/Supervisor aus. `RecipeResultService`
prüft veröffentlichte Ableitungen desselben Assets und deren Aktualität. GUI-
Arbeiter führen diese Dienste außerhalb des UI-Threads aus, kein zweiter Runner.

`PluginService` liest ausschließlich deklarative Manifeste; fremder Code läuft
erst nach ausdrücklicher Freigabe im Worker. `PipelineExchange` übernimmt geprüfte,
eigenständige Rezeptkopien ohne Assets, Jobs oder lokale Codefreigaben. Details,
Austauschschemata und tatsächliche Grenzen: [Projektpipelines](PIPELINES.md).

## Ergänzung: Skriptpakete und lesbare Asset-Ablage

`studio-python-step-v2` ergänzt den bestehenden Bildadapter um ein echtes
Python-Ergebnis mit Geometrie-Metadaten. Parameter und optionale Bedienaktionen
kommen aus dem Paketmanifest. Der generische UI-Einstieg lädt freigegebenen
Paketcode ausschließlich bei ausdrücklichem Aufruf. Verarbeitung und optionale
GUI-Aktionen haben getrennte Lebenszyklen; v1 bleibt kompatibel.

Migration 8 ergänzt `card_paths`, `managed_files`, `asset_publications` und
`file_commits`. `ProjectFiles` bildet fachlichen Besitz als Ordner ab. Die äußere
Katalogtransaktion koordiniert Änderungen mit einem wiederaufnehmbaren
Dateijournal. Layoutänderungen lösen keinen Ordnerabgleich oder Bildbuild aus.
Vollständige Bildläufe veröffentlichen geprüfte Kopien beim Asset; der gemeinsame
Job-Cache bleibt erhalten. Bedienung und Grenzen: [Skriptpakete](SKRIPTPAKETE.md).
