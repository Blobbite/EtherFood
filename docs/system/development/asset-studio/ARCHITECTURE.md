# Architektur und Datenverträge (T002)

## Schichten und Zuständigkeiten

`tools/AssetManager/src/etherfood_studio/` ist ein eigenes Python-Paket.
Der bestehende `g2dtool`-Start und die PyGameTools-Starter bleiben erhalten.

| Schicht | Aufgabe | Zulässige Abhängigkeiten |
| --- | --- | --- |
| domain | Typen, Relationen, Statusregeln | Python-Standardbibliothek |
| application | Anwendungsdienste, Befehle, Konflikte | domain, storage-Schnittstellen |
| storage | SQLite, sichere Pfade, Blobs, Journale | domain, Standardbibliothek; Pillow bei Bildimport |
| pipelines | spätere Adapter der Bestandswerkzeuge | application/domain; kein Qt |
| godot | späterer Export/Deployment-Adapter | application/domain; kein Qt |
| ui | PySide6-Desktop | application; kein SQL in Widgets |

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
