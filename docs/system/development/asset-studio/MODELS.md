# Struktur, Dokumente und Status (Pakete 1–3)

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

## Dokumente und Aufgaben

`DocumentService` speichert Markdown revisioniert im Katalog. Generierte
Berichte und manuelle Notizen sind verschiedene Dokumenttypen. Der normale
Editor darf Berichte nicht überschreiben. Anhänge werden über den sicheren
Blob-Import kopiert, Herkunftsnamen bleiben Metadaten. Markdown-Import
erhält die Originaldatei, protokolliert Name/Hash und erfordert bei gleichen
Titeln eine ausdrückliche Revisionsauswahl. Sechs neutrale Vorlagen enthalten
keine fertigen Abnahmen oder erfundene Geschichte.

`IssueService` unterstützt Aufgaben/Fehler, Priorität, optionale Zuständigkeit
und Aufgabenabnahme. Eine Fundstelle kann Asset/Build, Pose, Richtung,
Grafikprofil, Frames, Zeit/Frame und einen sicher importierten Screenshot
nennen. Titel-/Textsuche und Filter liefern stabile Karten-IDs; Kapitel-
Filter berücksichtigen auch gemeinsam verwendete Assets.
Eine erledigte Aufgabe ist ausdrücklich **keine** Build- oder Godot-Freigabe.

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
