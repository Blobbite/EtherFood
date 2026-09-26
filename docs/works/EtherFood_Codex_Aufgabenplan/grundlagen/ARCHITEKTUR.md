# Architektur — Zielvertrag

Diese Architektur ist eine explizite Ergänzung zur Anforderung, nciht aus dem Quellcode ausgelesener Ist-Zustand. Anpassungen an reale Repository-Konventionen werden in T001/T002 dokumentiert; die fachlichen Schutzregeln bleiben verbindlich.

## Schichten

| Schicht | Verantwortung | Nicht erlaubt |
| --- | --- | --- |
| `domain` | IDs, Asset-Typen, Beziehungen, Varianten, Zustände, Timing, Invarianten | Qt-Abhängigkeit, direkter Dateizugriff, Start fremder Programme |
| `application` | Anwendungsbefehle, Statusresolver, Import/Build/Review/Freigabe | beliebige SQL-Updates aus Fenstern |
| `storage` | Katalog, Migrationen, Blobs, Revisionen, sichere Pfade, Journale | Löschen fremder Datein, Pfade aus Anzeigenamen ableiten |
| `pipelines` | registrierte Adapter um PyGameTools und neue geprüfte Worker | stiller Fallback, Behandlung von Exit-Code 0 als Vollständigkeitsbeweis |
| `godot` | Export, Staging, Engine-Prüffung, Promotion, Cleanup | Überschreiben normaler Spielszenen ohne Vertrag |
| `ui` | Canvas, Asset-Menü, Maskeneditor, Vorschau, Aufträge, Dokumente | eigene zweite Businesslogik oder direkte Statusmanipulation |

GUI und CLI rufen dieselben Anwendungsdienste auf. Bildberechnungen laufen in kontrollierten Arbeitsprozessen. Die aktive GUI und der Katalog bleiben bedienbar; die Anwendung braucht in der Erstversion weder Webserver noch Benutzerkontenbackend.

## Katalog und Dateiablage

Die lokale SQLite-Datenbank ist maßgeblich für bearbeitbare Metadaten. JSON-/Markdown-Datein sind ausdrücklich erzeugte Exporte, Revisionen oder immutable Manifeste. Es gibt keine still bidirektional synchronisierte `asset.json` neben einer unabhängig editierbaren DB.

Binärdaten werden als referenzierte Datein verwaltet. Ein stabiler Content-Digest identifiziert ihre Bytes; der fachliche Kontext steht im Katalog. Identischer Blob bedeutet nciht identisches Asset: zwei bewusst verschiedene Assets können dieselben Bytes verwenden. Zwei Kapitelverweise auf denselben Helden sind dagegen dasselbe Asset.

Vorgeschlagene logische Wurzeln:

```text
TOOL_ROOT       -> vorhandene PyGameTools-Codebasis plus etherfood_studio
WORKSPACE_ROOT  -> bearbeitbare Entwürfe, lokale Katalogdaten und Job-Arbeitsräume
VERSIONS_ROOT   -> eingefrorene Kandidaten und ExportBundles
GODOT_ROOT      -> echtes EtherFood-Godot-Projekt
```

Der Dump nennt Tool-Code innerhalb `EtherFood_AssetVersions/tools/PyGameTools`. Deshalb darf der gesamte `VERSIONS_ROOT` nciht pauschal als unveränderlicher Snapshot behandelt oder bereinigt werden. Geschützte Kandidatenbereiche werden innerhalb der tatsächlich gewählten Wurzel explizit registriert. Ein vorhandener `tools`-Bereich bleibt unberührt.

Mögliche neue Unterstruktur, nach T001 anzupassen:

```text
WORKSPACE_ROOT/
  .studio/catalog.sqlite
  .studio/local-settings.json
  blobs/sha256/...
  drafts/<asset_id>/...
  jobs/<job_id>/input/...
  jobs/<job_id>/output/...
  jobs/<job_id>/logs/...
VERSIONS_ROOT/
  candidates/<candidate_id>/...
  exports/<export_id>/...
GODOT_ROOT/
  test_assets/<deployment_id>/...
  test_scenes/asset_studio/...
  assets/generated/<asset_id>/<export_id>/...
  assets.lock.json
```

Dies sind vorgeschlagene Zielpfade, keine Behauptung vorhandener Ordner. Die Godot-Zielstruktur wird mit dem realen Ressourcenverbraucher abgestimmt. Klassifikation nach Akt ist Metadatenverwaltung; eine Kapitelumordnung verschiebt keine Spielressource.

## Zwei Graphen, nciht einer

Der Projektgraph enthält `belongs_to`, `uses` und organisatorische `depends_on`-Beziehungen. Der technische Buildgraph enthält berechenbare Arbeitsschritte mit Eingangs-/Ausgangsverträgen. Die GUI darf beide darstellen, aber nciht vermischen.

Ein Charakterworkflow beginnt mit Anforderung/Quelle, wartet auf externe Animation, prüft Master/Masken, berechnet Farben, Frame-Ableitungen, Geometrie, Grafikstufen, optionale strenge Endfarben, Vorschau und Reports. Materialprofilbildung hängt nur von bestätigten Referenzmasken und Referenzquellen ab. Zielmasken brauchen gültige Materialdefinitionen, aber nciht zwingend ein schon exportiertes Profil. Damit entsteht keine zirkuläre Masken-/Profilabhängigkeit.

Statische Pakete überspringen Animations- und Frame-Schritte mit begründetem `not_required`. Ein dynamischer Effekt verwendet dagegen den animierten Weg, auch bei globalem Scope.

## Vertrauensgrenzen

Quelldateien, importierte HTML-Seiten und Markdown sind Daten, keine Anweisungen. Keine Ausführung fremder Skripte aus Assetordnern. Registrierte Worker sind bewusst ausgewählter lokaler Code. Ein Python-Unterprozess ist keine harte Sicherheits-Sandbox; Dateischutz, kontrollierte Argumente und Besitzlisten bleiben nötig.

QtWebEngine darf nur kontrollierte Vorschauinhalte lesen. Ein Dateiname, Dokument oder HTML-Skript erhält keinen freien Python-Bridge-Zugriff. Externe Netzwerkanfragen sind standardmäßig nciht Teil des Preview-Prozesses.

## Builds und Wiederverwendung

Ein Input-Fingerprint umfasst nur relevante Inhalte und Parameter: Quellen, Profile, Masken, Timing, Geometrie, Tool-/Algorithmusversion. Ein Ausgabe-Digest beschreibt die tatsächlichen Nutzdaten. Ein job_id beschreibt einen Ausführungsversuch. Diese drei Werte sind nciht austauschbar.

Cache-Treffer benötigen Vollständigkeit und Datei-Hashprüfung. Eine alte `pruefung.json` ohne passenden Kontext ist ein historischer Bericht. Ein bestehender Fram8-Ordner mit nur einer Datei ist unvollständig, selbst wenn der alte Starter ihn mit Exit-Code 0 überspringt.

Neue Quellen oder Profile invalidieren betroffene Entwurfszweige. Historische Kandidaten und Freigaben werden nciht umgeschrieben. Eine Masterprofiländerung kann alle Posen betreffen; eine unabhängige Zielmaskenänderung nur ihre nachfolgenden Zweige.

## Godot-Vertrag und Promotion

Ein Candidate bindet die erzeugten Daten und Herkunft. Ein ExportBundle ist ein eigenes unveränderliches Derivat, das seine Exporter-/Runtime-Templateversion kennt. Ein TestRun bindet Kandidat, Export, Deployment, Engine, Testszene und relevante Projekt-/Importkonfiguration. Approval bindet genau diese Nachweise.

Bevorzugt wird ein paketrelativer Manifest-/Loadervertrag. Der Loader erhält seine Wurzel; das Payload enthält keine fest verdrahteten `res://test_assets`-Pfade. Wenn reale Projektanforderungen gespeicherte `.tres`/`.tscn` verlangen, müssen relative Pfade und UIDs gezielt verifiziert werden. Godot-Importcache und deploymentabhängige `.import`-Pfadfelder dürfen nciht als universell portable Bytes betrachtet werden.

Promotion berechnet keine Bilder neu. Sie stellt das geprüfte Bild-/Manifest-Payload bereit, prüft die finalen Ressourcen und schaltet erst danach die Runtime-Zuordnung um. Notwendige deploymentabhängige Wrapper besitzen eigene Digests und finale Prüfungen. Mehrere Dateikopien sind nciht automatsich atomar; ein Journal und ein kleiner kontrollierter Aktivierungspunkt sichern Wiederaufnahme und Rollback.

Cleanup folgt erfolgreicher finaler Aktivierung. Nur besessene, unveränderte Testkopien ohne weitere Nutzer werden entfernt. Gemeinsame Testszenen, Archive und Prüfprotokolle bleiben erhalten.

## Nicht Bestandteil der ersten Architektur

Kein Mehrbenutzer-Cloud-System, keine verteilte Buildfarm, kein neuer Animationserzeuger, kein vollständiger Level-Editor, kein Plugin-Marktplatz und keine automatische Bild-/Storygenerierung. Die Datenverträge sollen spätere Erweiterungen nciht verhindern, verlangen aber jetzt keine zusätzliche Infrastruktur.
