# Freie Masterreferenzen und Materialmasken

Paket 8 ergänzt T019/T020 an den vorhandenen Bildpipelines. Die Bedienung liegt
im **Asset-Menü → Pipeline / Farben → Masterreferenzen / Materialien / Masken …**.
Ein Farbprofil beschreibt die gewünschten Farben. Die projektweiten Grafikprofile
wie `comic_low` beschreiben weiterhin Auflösung und Grafikverfahren.

## Referenzen wählen und Farben verwenden

1. Quellen wie bisher über das Asset-Menü importieren. Unter **Masterreferenzen /
   Farbprofile** eine oder mehrere konkrete Quellen ankreuzen und die gemeinsame
   Vorschau-Referenz ausdrücklich auswählen.
2. **Auswahl speichern** erstellt eine unveränderliche Referenzrevision. Pose,
   Richtung, Quellenrevision, SHA-256, Bildmaße, Raster und Framezahl bleiben
   gebunden. Eine einzige Referenz kann für alle Richtungen eines NPC dienen;
   es werden keine fehlenden Richtungen erfunden.
3. Farbmodus auswählen und **Farbprofil aus gespeicherten Referenzen erzeugen**
   ausführen. `soft` und `fixed` benötigen keine Materialmasken. `material`
   benötigt die unten beschriebenen Definitionen und bestätigten Referenzmasken.
4. Den gewünschten vorhandenen Farbschritt eines Projekt-Rezepts auswählen und
   **Gewählten Rezeptschritt auf Asset-Farbprofil umstellen** betätigen.
   Dieses Rezept verwendet danach für jedes zugewiesene Asset dessen eigenes
   Farbprofil; andere zugewiesene Assets brauchen ebenfalls eine Konfiguration.
5. Im normalen Pipeline-Dialog den Dry-run prüfen und den Bildlauf ausdrücklich
   starten. Eine Referenzauswahl, Profilbildung oder Zuweisung startet keinen
   Bildbuild. **Farbprofil exportieren …** schreibt ein eigenständiges JSON für
   die vorhandenen CLI-Werkzeuge; bestehende Dateien werden nicht überschrieben.

Alle Frames der gewählten Referenzen fließen ein. Referenzen und Frames werden
gleich gewichtet, innerhalb eines Frames zählt Alpha anteilig; unsichtbares RGB
fließt nicht ein. Leere Referenzframes werden abgelehnt. In Version 2 müssen die
gewählten Quellen dasselbe Raster haben; verschiedene Framegrößen sind möglich.
Für Materialfarben zählen die Frames, in denen das jeweilige Material gelabelt
sichtbar ist. Ein Material ohne Referenzpixel blockiert die Profilbildung.

**Vorlage: acht Stand-Sheets** wählt ausdrücklich die acht vorhandenen Stand-
Richtungen samt allen Frames. Sie setzt eine Stand-Pose und diese Quellen voraus.
Die freie Auswahl bleibt davon unabhängig. Frühere Auswahlen können als Entwurf
geladen und neu gespeichert werden, sofern ihre Quellen noch aktiv sind.

## Materialien, Entwürfe und Sichtbestätigung

Unter **Materialdefinitionen** IDs, Namen und die gewünschte Anzahl Farbstufen
festlegen oder eine vorhandene `pyimg-material-definitions`-Datei importieren.
**Als neue Revision speichern** erhält ältere Definitionen. ID 0 ist Hintergrund,
IDs 1–255 bezeichnen Materialien. Die bunten Masken-Vorschaufarben zeigen nur
die IDs; sie sind keine Zielfarben. Ziel-Farbreihen entstehen aus den tatsächlich
gelabelten Referenzpixeln.

Unter **Masken / Revisionen** eine konkrete Quelle wählen:

- **Unbeschriftete Vorlage anlegen** erzeugt eine L8-Nullmaske mit Raster- und
  Quellhash-Metadaten. Sie ist ein Entwurf. Über **Maske exportieren …** kann sie
  in einem externen Werkzeug beschriftet werden, das PNG-Labelindizes und die
  Metadaten erhält. Die Malwerkzeuge des integrierten Maskeneditors folgen in T021.
- **L/P-Maske importieren …** übernimmt die Bytes unverändert als neue Revision.
  Auch vorhandene Greenhero-Masken erhalten dabei zunächst keine Sichtbestätigung.
  Palettenindizes eines P-PNG sind Material-IDs; gleiche Vorschau-RGB-Werte
  vereinigen keine unterschiedlichen Materialien.
- **Prüfen / Vorschau** zeigt Quelle und ID-Vorschau für den gewählten Frame.
  Gemeldet werden Pose/Richtung, Frame und Pixelbereich bei unbeschrifteten
  sichtbaren Pixeln, unbekannten IDs oder Material auf transparentem Hintergrund.
  Größe, Raster, PNG-Modus und Quellhash müssen ebenfalls passen.
- Nach Prüfung aller Frames die ausdrückliche Sichtbestätigung markieren,
  Namen/Prüfprofil eintragen und **Nur diese Maskenrevision bestätigen** verwenden.
  Die Angabe dokumentiert die Erklärung des Benutzers; sie authentifiziert keine
  Person und bestätigt keine anderen Masken oder Spielassets.

Unvollständige Masken sind speicherbare Entwürfe. Die verwaltete Material-
Verarbeitung akzeptiert nur technisch gültige und ausdrücklich bestätigte
Masken für die jeweils aktive Quelle. **Diese Revision verwenden** reaktiviert
einen passenden älteren Stand; alte Revisionen werden nicht überschrieben.
Quellen- oder Materialänderungen machen ihre Bindung veraltet. Der Quellhash wird
nicht umgeschrieben, um eine alte Maske scheinbar wieder gültig zu machen.

## Speicherung und Buildbindung

`ReferenceService` und `MaskService` verwenden den vorhandenen Katalog und
Blobstore. `profile_revision` speichert Referenzauswahl, Materialdefinition oder
erzeugtes Farbprofil mit getrennten Vertragskennungen; `mask_revision` speichert
Maskenherkunft, Bindung und technischen Prüfstand. Die separate `review` bindet
die Sichtbestätigung an Masken-ID/-Hash, Quellenrevision/-Hash, Raster und
Materialdefinitionsrevision. Ein Metadatenimport überträgt keine Bestätigungen.
Die bereits vorhandenen Katalogtypen reichen aus; es ist keine SQL-Migration nötig.

Der Ressourcenwert `@asset` im Pipeline-Editor löst ein verwaltetes Farbprofil
beziehungsweise die zur Quelle passende Maske auf. Der Dry-run bindet die
aufgelösten Dateien und Revisionen an den bestehenden Buildgraph. Ein laufender
Auftrag behält diesen Snapshot. Neue Referenzen oder Masken machen betroffene
Farbzweige veraltet; unabhängige Grafikzweige verwenden ihren Cache weiter.
Nicht aktivierte Farbschritte fordern keine Masken oder Profile an.

Der bisherige Import expliziter JSON-/PNG-Rezeptressourcen und `@source` bleiben
kompatibel. Ihre technische Verarbeitung stellt keine verwaltete Masken-
Sichtbestätigung her. Neue verwaltete Materialeingaben über `@asset` prüfen diese
Bestätigung zusätzlich. Rezeptimport übernimmt keine fremden Asset-Bindungen:
das Zielprojekt muss seine Referenzen und Masken selbst konfigurieren.

## Farbprofil-Versionen und CLI

Die alten Version-1-Formate und Aufrufe behalten ihren Acht-Richtungs-Vertrag.
Neue Profile verwenden Version 2 derselben Formatkennungen:
`pyimg-reference-colors`, `pyimg-fixed-palette`, `pyimg-material-colors`.
Loader und Matcher der bisherigen Starter lesen beide Versionen; unbekannte
Versionen werden zurückgewiesen.

Der neue CLI-Schalter `--reference-selection DATEI.json` ersetzt bei der
Profilbildung die automatische Acht-Richtungs-Suche. Die JSON-Datei verwendet
`format: pyimg-reference-selection`, `version: 1`, die dokumentierte Gewichtung,
eine ausdrückliche `preview_reference` und ein bis 32 Referenzeinträge. Ihre
Bildpfade sind relativ zur Auswahl-Datei und werden gegen die Quellhashes geprüft.
Die formalen Schemata stehen unter
[`PiplineToos/schemas/`](../../../../tools/AssetManager/PyGameTools/Pipline/PiplineToos/schemas/).
Zusätzliche semantische Prüfungen sichern eindeutige IDs, Pfade, gemeinsame
Raster und die gewählte Vorschau-Referenz.

Beispiel mit selbst erstellter Auswahl-Datei und separatem Ausgabeziel:

```bash
.venv/bin/python tools/AssetManager/PyGameTools/Pipline/SourceColor-Pipline/PyPiplineStart-SourceColor.py \
  QUELLORDNER --reference-selection REFERENZEN/selection.json \
  --export-fixed-palette AUSGABE/fixed-palette.json
```

Die erzeugten/exportierten Profile werden wie bisher mit `--profile`,
`--fixed-palette` oder `--material-profile` verwendet. Materialexport benötigt
zusätzlich `--material-definitions` und `--mask-dir`; dessen relative Maskenpfade
entsprechen den Referenzpfaden. In der HTML-Vorschau ist die bewusst gewählte
gemeinsame Referenz beschriftet; die Anzeige behauptet keine acht vorhandenen
Richtungen oder gleiche Ziel-/Referenzrichtung. Fehlt die Referenzdatei beim
Weitergeben eines reinen Profils, bleibt dies sichtbar; das Profil selbst
enthält weiterhin seine verbindlichen Farben und Herkunftsdaten.

Technische Nachweise: [T019](task-results/T019.md), [T020](task-results/T020.md).
