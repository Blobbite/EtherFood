# Struktur, Dokumente, Asset-Anforderungen und Status

## Karten und Verwendungen

`ProjectService` erstellt einen Projektkatalog mit globalem Rahmen. Akte
gehören zum Projekt, Kapitel zu Akten. Neben-, Asset- und Paketkarten haben
einen eindeutigen Besitzer; Verwendungen in anderen Kapiteln sind `uses`-
Beziehungen auf dieselbe UUID. Umbenennen, Sortieren, Umordnen und logisches
Archivieren bewegen keine Asset-Dateien. Nur explizite `depends_on`-Kanten
stellen fachliche Voraussetzungen dar; Aktreihenfolge sperrt keine Bearbeitung.

`ProjectService.demo()` erzeugt ausschließlich als Demo bezeichnete Karten:
globaler Held/Effekt, ein Akt, zwei Kapitel und Tempelpaket. Es übernimmt
keine erfundene Handlung in den Spielkanon. Projektimport/-öffnung prüft
Hierarchie, Eigentümer, Verknüpfungen und Zyklen; fehlende externe Wurzeln
bleiben gespeichert und werden als nicht verfügbar gemeldet.

Seit Zwischenpaket 6c erfolgt die Umordnung direkt per Drag-and-drop im
Projektbaum. Karten, Aufgaben, Issues und manuelle Dokumente behalten ihre IDs
und Daten; nur die Zuordnung ändert sich. Verwendungs-Verweise verschieben nur
die jeweilige Beziehung. Strg+Ziehen eines Assets/Pakets fügt eine Verwendung
hinzu. Validierung und Undo/Redo schützen vor ungültigen Ebenen, Zyklen und
zwischenzeitlichen Änderungen. [Bedienung](NOTIZEN_UND_ZUORDNUNG.md).

## Dokumente und Aufgaben

`DocumentService` speichert Markdown revisioniert im Katalog. Generierte
Berichte und manuelle Notizen sind verschiedene Dokumenttypen. Der normale
Editor darf Berichte nicht überschreiben. Anhänge werden über den sicheren
Blob-Import kopiert, Herkunftsnamen bleiben Metadaten. Markdown-Import
erhält die Originaldatei, protokolliert Name/Hash und erfordert bei gleichen
Titeln eine ausdrückliche Revisionsauswahl. Sieben neutrale Vorlagen enthalten
keine fertigen Abnahmen oder erfundene Geschichte.

Seit Zwischenpaket 6d legt **+ Dokumentation** mit einer Dokumentvorlage an;
neue Markdown-Importe verwenden die neutrale Vorlage Dokumentation. Bestehende
Notizvorlagen und ausdrückliche Revisionsimporte behalten ihre Klassifikation.
Dokumente erscheinen mit violettem Seitensymbol auch im Projekt-Canvas;
generierte Berichte bleiben schreibgeschützt. Keine Datenmigration.

`IssueService` unterstützt Aufgaben/Fehler, Priorität, optionale Zuständigkeit
und Aufgabenabnahme. Eine Fundstelle kann Asset/Build, Pose, Richtung,
Grafikprofil, Frames, Zeit/Frame und einen sicher importierten Screenshot
nennen. Titel-/Textsuche und Filter liefern stabile Karten-IDs; Kapitel-
Filter berücksichtigen auch gemeinsam verwendete Assets.
Eine erledigte Aufgabe ist ausdrücklich **keine** Build- oder Godot-Freigabe.

Seit Zwischenpaket 6a stehen dieselben Aufgaben/Issues direkt unter
**Asset-Menü → Dokumentation → Aufgaben & Issues** zur Verfügung. Die dortige
Suche ist auf das ausgewählte Asset begrenzt; im Hauptfenster bleibt die
projektweite Suche erhalten. Es gibt keine zweite Aufgabenablage oder kopierte
Aufgaben-ID. Notizen bleiben daneben im eigenen Reiter; Anhänge gehören zur
Dokumentation. Bereits vorhandene Notizanhänge werden nicht entfernt.

Seit Zwischenpaket 6b sind **Aufgaben-Kanban** und **Suche** im Hauptfenster
getrennt. Das Board folgt der ausgewählten Karte, gruppiert vorhandene Aufgaben
und Issues nach Herkunft und erlaubt Statuswechsel per Ziehen oder Schaltfläche.
Projektwurzel zeigt alle aktiven Aufgaben; verwendete Assets/Pakete und ihre
Unterkarten werden ohne Kopien berücksichtigt. Archivierte Eigentümerzweige
bleiben ausgeblendet. [Bedienung und Bereichsregeln](KANBAN.md).

Zwischenpaket 6c ergänzt **Notizen** zwischen Kanban und Dokumentation. Das
Dashboard zeigt dieselben manuellen Dokumente der Vorlagen Freie Notiz und
Testnotiz als Post-its. Optionale Felder `note_color` (sechs definierte Farben)
und `note_pinned` (Boolean) steuern nur die Darstellung. Alte Datensätze ohne
diese Felder sind gelb und nicht angeheftet. Der eingebettete Notizeditor im
Dashboard schreibt direkt auf den Post-its revisioniert auf dieselben IDs;
Alttexte und alte Anhänge bleiben erhalten. Neue/geänderte Notiztexte sind
auf 100 Wörter begrenzt. Farbe/Titel/Anheften können auch für unveränderte
lange Alttexte gespeichert werden. Die Dokumentationsauswahl zeigt keine Notizen mehr an.
Aufgaben, Issues und Notizen erscheinen zusätzlich als kleine Canvas-Symbole.

`ProjectService.content_scope` löst für Aufgaben, Suche und Notizen einheitlich
aktive Unterkarten und rekursive Paket-/Assetverwendungen auf. Archivierte
Eigentümerzweige sind ausgeschlossen; keine inhaltliche Vervielfältigung.

Aufgaben und Issues können eine To-do-Liste besitzen. Im Anlage-/Bearbeitendialog
Punkte ergänzen, per Doppelklick umbenennen oder gezielt entfernen. Häkchen in
der Detailansicht speichern unmittelbar über denselben Revisionsdienst.
Noch nicht per **+ Punkt** übernommener Eingabetext wird beim Speichern ergänzt.
Die Suche findet auch To-do-Texte. Höchstens 200 Punkte mit je 500 Zeichen;
leere, doppelte oder ungültige Einträge werden abgelehnt.

To-dos sind das optionale Datenfeld `checklist` des bestehenden Datensatzes:
Liste aus `{id, text, done}` mit stabilen UUIDs, Text und echtem Boolean.
Alte Aufgaben ohne Feld entsprechen einer leeren Liste; keine DB-Migration.
Katalogöffnung und Snapshot-Import prüfen diese Daten. Ein Schreibkonflikt
überschreibt keine fremden Änderungen. Bei Editorfehlern bleiben lokale
Eingaben erhalten, bei fehlgeschlagenem direktem Häkchen wird der tatsächliche
Katalogstand wieder angezeigt.

Offene To-dos verhindern **Erledigt**. Alle Häkchen setzen den Aufgabenstatus
nicht automatisch und bestätigen auch keine benötigte Aufgabenabnahme.
Eine erneut geöffnete Teilaufgabe setzt einen erledigten Task zurück auf offen;
Inhaltsänderungen heben wie bisher eine frühere Aufgabenabnahme auf.
Der Asset-Workflow und Spiel-/Godot-Freigaben bleiben davon getrennt.

## Asset-Anforderungen (Paket 5 / T013)

`asset_definition` im Asset-Datensatz enthält Version 1 mit datengetriebenem
Typ und Fähigkeiten (`animated`, `directional`, `supports_materials`,
`static_image`, `package_member`). Das Schema liegt unter
`schemas/asset-studio/asset-definition-v1.json`; der Domain-Validator prüft
zusätzlich Zusammenhänge und Grenzen. Vorlage und Anzeigename sind keine
Asset-spezifische Pipeline-Sonderbehandlung.

Die Asset-Karte öffnet über **Asset-Menü → Posen** das gemeinsame Anforderungsformular.
Posen besitzen stabile UUID, Anzeigename, Exportname, Quellart, Loop, optional
eigene geordnete Richtungen, FPS und normalisierten Anker. Namen wie `walk`
und `slowwalk` sind getrennt. Frames (Bilderanzahl) sind keine FPS (Tempo).
8 Richtungen × 5 Grafikprofile × 5 Frameprofile ergeben 200 Varianten je
Spritesheet-Pose. Einzelbildposen wie `jump` erwarten nur ein Bild; statische
Texturen haben weder Pose noch Richtung noch Frames/FPS. Richtungs- und
Materialfähigkeiten steuern die Anforderungen: unnötige Schritte/Varianten
sind `not_required`, nicht fehlgeschlagen.

`inventory_sources` sammelt externe Beobachtungen ohne Ersetzen bestehender
Originale. Ein unabhängiges 8-Frame-Original bleibt neben einer späteren
Ableitung erhalten; unterschiedliche Inhalte zur gleichen Variante werden
als Konflikt sichtbar. Vorhandensein ersetzt keine Prüfung oder Freigabe.

## Workflow-Version 1

Vorlagen: `animated`, `effect`, `static`, `document`. Der reine Resolver
berechnet Zustand und Sperrgrund aus Eingaben und exakten Nachweisen.
Eingaben sind bereits geprüfte Revisions-/Digest-Verweise, keine beliebigen
Dateinamen. Masken brauchen zusätzlich die passende Quellbindung.

- Figuren/Effekte warten auf externe Quellen; sie erzeugen keine Animation.
- Statischer Inhalt begründet `frames = not_required`.
- `skipped`, unbekannt, blockiert oder fehlgeschlagen zählt nicht als bestanden.
- Ein Nachweis benötigt passenden Input-Fingerprint und exakte Build-ID.
- Neue Quelle/Maske macht aktuelle Folgeergebnisse veraltet; historische
  Nachweise bleiben unverändert an ihren damaligen Build gebunden.
- Namen, Reihenfolge, Layout und Zoom gehören nicht zu Pixel-Fingerprints.
- Fortschritt zählt nur explizit geforderte Kriterien, nicht beliebige Haken.

`StatusService` liefert bis zur späteren Pipeline-Anbindung bewusst keine
erfundenen Build-/Sicht-/Godot-/Runtime-Erfolge. Das Dashboard kann Status
nicht beliebig überschreiben. Pipelineausführung und echte Freigaben sind
nicht Bestandteil der ersten vier Pakete.
