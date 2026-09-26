# Datenverträge und Invarianten

Alle Namen in diesem Dokument sind **neue Zielverträge**. Die tatsächliche Implementierung entsteht in den Aufgaben. Bestehende PyGameTools-Formate werden in den Quellen dokumentiert und nciht durch diese Entwurfsnamen ersetzt.

## Stabile Identitäten

| Objekt | Wesentliche Felder | Zentrale Regel |
| --- | --- | --- |
| Project | `id`, Name, Schema-Version, logische Wurzeln | Maschinenpfade nciht mit portablen IDs vermischen. |
| Act / Chapter | `id`, `parent_id`, Name, Reihenfolge | Umbenennen/Umordnen erhält Identität. |
| Card | `id`, Typ, Objektbezug, Dokumente | Eine Karte kann auf ein bestehendes Asset zeigen. |
| Relation | `id`, Typ, Quell-/Ziel-ID | `belongs_to`, `uses`, `depends_on` unterscheiden. |
| CardLayout | Karten-ID, Position, Gruppe, Ansicht | Hat keinen Einfluss auf Pixel-/Workflow-Fingerprints. |
| Asset | `id`, Typ, Scope-Besitzer, Konfiguration | Verwendung in Kapiteln ist eine eigene Beziehung. |
| Pose | `id`, Asset-ID, Name, Richtugnen, Timing, Anker | `stand` nciht ungefragt in `idle` umbenennen. |
| PackageRevision | Paket-ID, feste Mitgliedsrevisionen | Kein schwebendes `latest` in Freigaben. |
| SourceRevision | ID, logische Quelle, Datei-Digests, Importherkunft | Nach Registrierung unveränderlich. |
| ProfileRevision | ID, Format-/Schema-Version, Inhalt, Referenzen | Alte Profilsemantik erhalten. |
| MaskRevision | ID, Quelldigest, Raster, Materialdefinition, Labeldigest | Technische und visuelle Gültigkeit getrennt. |
| Build | ID, Input-Fingerprint, Resultat, Tool-/Rezeptrevision | Ergebnisbytes separat prüfen. |
| Candidate | ID, Buildbezug, Payload-Manifest, Herkunft | Inhalt unveränderlich; Abnahmen separat. |
| ExportBundle | ID, Candidate-ID, Exporter, Runtime-Payload | Darf Candidate nciht nachträglich verändern. |
| TestRun | ID, Export-/Deployment-ID, Kontext, Testfälle | `passed=true` ohne Kontext reicht nciht. |
| Review | ID, exakter Prüfgegenstand, Scope, Entscheidung | Gesehen ist nciht abgenommen. |
| Approval | ID, Candidate-/Export-ID, Nachweise, Entscheidung | Kein Bezug nur auf Assetname/latest. |
| Deployment | ID, Export, Ziel, Besitzliste, Journal | Test-/Runtime-/Cleanupstatus getrennt. |

IDs können UUIDs oder gleichwertige stabile Kennungen sein. Anzeigenamen und Dateipfade sind keine Identität. Metadatenzeiten werden eindeutig gespeichert; die GUI darf sie lokalisiert darstellen. Namen mit Umlauten, Leerzeichen, `#` oder `%` sind erlaubt, ohne daraus unsichere Pfade zu erzeugen.

## VariantKey

Animiert:

```json
{
  "asset_id": "EXAMPLE_ASSET_ID",
  "pose_id": "EXAMPLE_POSE_ID",
  "direction_id": "NW",
  "graphics_profile_id": "pixel_low",
  "frame_profile_id": "frames_8",
  "source_revision_id": "EXAMPLE_SOURCE_REVISION"
}
```

Statisch: `pose_id`, `direction_id` und `frame_profile_id` können gemäß Typvertrag `null` sein. Keine künstliche Pflichtanimation mit einem Frame erfinden, nur um dasselbe Formular zu nutzen. Ein statisches Bild kann intern als Raster `1x1` verarbeitet werden, ohne eine fachliche Frame-Dimension zu erhalten.

Expected-Variant-Mengen entstehen aus Assetanforderungen, nciht durch blindes Scannen beliebiger Ordner. Für eine Pose mit acht Richtugnen und 5×5 Stufen sind es 200 Kombinationen. Eine Pose mit zwei Richtugnen hat bei denselben Profilen 50. Nicht benötigte Richtugnen werden nciht als fehlend gezählt.

## Quelle, Referenz und Maske

SourceRevision speichert Originalbytes, Importmapping und Raster. Ein waagerechter 16er-Streifen besitzt `columns=16`, `rows=1`. Source-Einzelbilder sind eigene Eingaben; das Dashboard erzeugt daraus keine Originalanimation.

ReferenceSelection enthält eine geordnete, nciht leere Auswahl konkreter Quellenrevisionen mit Frame-/Richtungs-/Rasterangaben und Gewichtungsregel. Die Asset-Richtugnen und die Referenzmenge sind unterschiedliche Mengen. Ein Master kann gemeinsam wirken; die Vorschau zeigt nur echte Referenzen und erklärt Zuordnungen.

Der Bestandsvertrag für Labels bleibt: 8-Bit-PNG in L/P, bekannte Material-IDs `1..255`, Hintergrund `0`, vollständige Belegung bei Alpha > 0, passendes Raster und `pyimg_source_sha256`. Unbekannt wird nciht durch Umwidmen einer gültigen Material-ID versteckt. Entwürfe dürfen unvollständig gespeichert werden, aber nciht als fertige Materialeingaben gelten.

Maskenrevisionen unterscheiden `suggested`, `edited`, technisch gültig und visuell bestätigt. Eine Änderung der Quellbytes macht eine alte Quellenbindung prüfpflichtig. Ein neues Hashfeld allein repariert keine alte räumliche Zuordnung.

## Geometrie und Timing

Je Bild-/Frameausgabe werden Originalgröße, Auswahlindizes, Crop-Box, Zielzellgröße und Anchor-Transformation gespeichert. Ein Anker im ursprünglichen Frame wird um den Crop-Offset korrigiert und nach dem definierten Skalierungsvertrag abgebildet. Das muss über Posen und Varianten prüfbar bleiben.

`frame_count`, `fps` und `duration` sind getrennt. `legacy_fixed_fps` erhält den Bestand. `preserve_duration` definiert eine Zeitleiste mit positiven Anzeigedauern und konstanter Gesamtdauer. Ereignisse werden optional auf dieser Zeitachse gespeichert. Vorschau-FPS ist nur eine Ansichtseinstellung.

GIF-Zeitquantisierung und zusammengefasste identische Bilder dürfen nciht mit der logischen PNG-/Runtime-Sequenz verwechselt werden. PNG bleibt die maßgebliche Bildquelle. Timingänderung ist ein neuer Buildparameter.

## BuildRequest und BuildResult

BuildRequest wird vor Start eingefroren und nennt Job/Asset, Quellen, Profil-/Maskenrevisionen, Rezeptrevision, Algorithmusversion, gewählte VariantKeys und erlaubte Wurzeln. Spätere GUI-Änderungen erzeugen einen anderen Entwurf.

BuildResult enthält pro Ausgabe relativen Pfad, Länge, SHA-256, VariantKey, Raster, Geometrie, Timing, Erzeugungsschritt und Prüfresultate. Pro Schritt werden Ausführung, Warnungen, Fehler und tatsächliche Toolargumente erfasst. Ein Exit-Code ohne vollständige Ergebnisse kann nciht `succeeded` bedeuten.

Volatile Logzeiten liegen außerhalb des kanonischen Input-/Payload-Fingerprints. Hash einer Eingabe, Hash eines Ergebnisses und Hash einer Bereitstellung sind unterschiedliche Informationen. Aus Identität der Eingaben folgt kein ungeprüfter Erfolg.

## Status und Übergänge

Arbeitsstatus: `not_started`, `waiting_external`, `ready`, `running`, `blocked`, `failed`, `cancelled`, `passed`, `stale`, `not_required`. Ein separates `interrupted` kann einen beim Neustart erkannten Auftrag kennzeichnen. Nur tatsächlich implementierte Übergänge verwenden; keine freien SQL-Statusupdates aus Widgets.

Assetlebenszyklus ist kein einziges Feld. Der aktuelle Entwurf kann offen sein, während ein älterer Kandidat freigegeben und noch ein anderer Export aktiv ist. Historische Nachweise bleiben unverändert. Widerruf ist ein zusätzliches Ereignis.

Für Pflichtchecks zählen `missing`, `skipped`, `not_run` und `blocked` nciht als bestanden. `not_required` ist nur aufgrund einer gültigen Typ-/Anforderungsregel erlaubt. Testabdeckung und manuelle Prüfabdeckung werden getrennt angezeigt.

## Testbindung

Ein Godot-Nachweis bindet mindestens:

```text
candidate_id + export_id + deployment_id
+ payload_digest + runtime_template_digest
+ engine_version + test_scene_digest
+ relevant_project_settings_digest + effective_import_settings_digest
+ checks + manual_review_scope
```

Ein Bericht mit anderem Kontext ist historisch oder ungültig für diese Freigabe. Ein Review darf auf einzelne Varianten, Sheets, Masken oder einen expliziten Gesamtumfang beschränkt sein. Eine automatsich abgespielte Tour ist lediglich gesehen, nciht akzeptiert.

## Ablage-/Deploymentmanifest

Payload-Pfade bleiben relativ. Das Manifest darf nciht aus dem Paket herauszeigen. Jede verwaltete Datei besitzt einen Besitzer und einen erwarteten Hash. `.godot` ist lokal erzeugter Cache; Importoptionen werden in ihrer wirksamen Semantik geprüft. Deploymentabhängige Pfad-/UID-Felder sind kein portabler Payloadnachweis.

Die Runtime-Lockdatei pinnt konkrete Exporte je Asset und ihre Prüfsummen. Andere Einträge bleiben bei einer Promotion erhalten. Der Aktivierungsdienst prüft die erwartete Lockrevision, um gleichzeitige Änderungen nciht zu verlieren.

Ein DeploymentJournal hält geplante Datein, Kopierstatus, Prüfergebnisse, alten/neuen Lockbezug, Aktivierung und Cleanup fest. Restore/Cleanup handeln nur auf diesen geprüften Besitzlisten. Keine globale Löschfunktion allein auf Basis eines Ordnernamens.

## Formatentwicklung

Jeder neue Vertrag erhält eine Version. Bestehende `pyimg-reference-colors`, `pyimg-fixed-palette` und `pyimg-material-colors` bleiben getrennt. Die Erweiterung auf variable Referenzmengen erfolgt über einen ausdrücklichen neuen Vertragsweg. Unbekannte Versionen werden kontrolliert zurückgewiesen. Migrationen erhalten Herkunft und behandeln Benutzeränderungen sichtbar.
