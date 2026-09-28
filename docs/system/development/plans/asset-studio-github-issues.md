<!-- PYGINDEX:NAVIGATION START -->
[Zur Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Asset Studio: zusammenhängende GitHub-Issues

## PIPELINE-ALIGNMENT-V1 – verbindlicher aktueller Einstieg

Stand: 28.09.2026. Diese Ergänzung präzisiert die bestehenden R01–R36 und
T001–T048, ersetzt keine Gesamtroadmap und erteilt keinen Implementierungsauftrag.
Die separate Szeneneditor-Roadmap bleibt unverändert. Für weitere Arbeit zuerst
das aktuelle Issue samt Kommentaren, den Checkout und diese Ergänzung lesen.
Die folgenden ursprünglichen Veröffentlichungsabschnitte sind **historisch**;
ihre Angaben wie „alle offen“, „nicht begonnen“ oder „noch nicht committed“
sind keine aktuelle Statusquelle.

Fachliche Grundlage ist der ausführliche, vierzehnteilige Benutzerauftrag
„Projektweite, Canvas-integrierte Pipelines“. Die unten aufgeteilten PA-Verträge
schränken ihn nicht auf einen neuen Kurzauftrag ein. Der tatsächliche Unterbau
und seine Grenzen stehen in [Projektpipelines](../asset-studio/PIPELINES.md),
[Architektur](../asset-studio/ARCHITECTURE.md) und dem
[Implementierungs-/Prüfbericht](asset-studio-projektpipelines.md).

### Auftrag, Bestand und Fortschritt der Planungssynchronisierung

Nur Beschreibungen, Zuständigkeiten, Planungsdaten und notwendige Beziehungen
anpassen. Keine Anwendung, Tests, Laufzeitkonfiguration, Migrationen, Bilder oder
Pipelines ändern/ausführen; keine Implementierungsagenten starten. Keine Issues
schließen/öffnen, keine PRs verändern und keine Zuständigkeiten, Labels,
Meilensteine oder Statusfelder beiläufig setzen.

- [x] Vorhandenen Arbeitsbaum nach ausdrücklicher Benutzerbestätigung separat
  vollständig sichern: `7546735`, nach `main` gepusht und Remote-Hash bestätigt.
  Die darin enthaltenen älteren Game-/Control-/PNG-Änderungen sind keine
  Implementierung oder Testergebnisse dieses Planungsauftrags.
- [x] 76 Issues einschließlich Kommentaren, Eltern/Kindern und nativen
  Abhängigkeiten lesen; PR-Abfrage aller Zustände liefert keine PRs.
- [x] Unverändertes Originalpaket prüfen: 48 Aufgaben, 36 Anforderungen,
  955 Links, 81 Hashes; keine Fehler.
- [x] PA-/R-Zuordnung und 35 fokussierte aktuelle Issue-Texte abgleichen:
  zwölf eindeutige PA-Verantwortungen, alle 36 R-/48 T-Zuordnungen erhalten.
- [x] 35 Issues unmittelbar vor jedem Schreiben erneut lesen, sicher abgleichen,
  anschließend gespeicherte Inhalte und Beziehungen erneut prüfen.
- [x] Deklarative Quellen, Links, Abhängigkeiten und eigenen Diff prüfen;
  abschließend 76 Issues erneut lesen: 35 geändert, 41 unverändert.
- [ ] Ausschließlich eigene Planungsänderungen committen/pushen; Abschluss berichten.

Nachgewiesener `main`-Bestand vor diesem Auftrag: `2286d2f` enthält echte
Bildpipelines, `f8c9991` ihren Ergebnisbericht. T013/T014 sind bereits technisch
abgehakt; T015/T016 sowie T017/T018 besitzen technische Ergebnisberichte und
offene Issue-/Abnahmepunkte. Die historischen Berichte zu `4ef37bd`/`4b16da4`
beschreiben noch Diagnoseadapter; deren Begrenzung ist kein Rückbauauftrag für
die inzwischen vorhandenen Bildadapter. Dokumentierte frühere Tests
(581 Studio, 123 PyGameTools, 48 Resolution/CLI) wurden **hier nicht erneut
ausgeführt**. Die neue persönliche Pipeline-Sichtabnahme und Godot-Integration
sind nicht nachgewiesen. Abgehakte Altprüfungen bleiben erhalten; neue
Integrationsprüfungen werden separat offen geführt.

GitHub-Projects-Zusatzfelder sind mangels `read:project` nicht lesbar und
werden nicht verändert. Issue-Zustand, Bearbeiter, Labels, Meilenstein,
Checkboxen, Kommentare und native Beziehungen sind lesbar und zu schützen.

### Verbindliche Anforderungen und primäre Zuständigkeiten

Jede PA-Kennung hat genau einen primären Integrationsverantwortlichen.
Angrenzende Liefergegenstände werden ausdrücklich benannt, nicht doppelt
implementiert. R-/T-Kennungen bleiben unverändert. Die maschinenlesbare
[Zuordnungsmatrix](pipeline-alignment-v1/requirements.json) enthält für jede
alte Anforderung Behandlung, Bedeutung, Schnittstelle, Abnahme und Nachweis/Rest.

| Vertrag | Primär | Verbindlicher Umfang und angrenzende Lieferung |
| --- | --- | --- |
| PA-01 Projektgrenze | T018 / #25 | Rezept-/Projektbesitz und Revisionen; T030/#37 bietet den Zugang im bestehenden Global-/Skriptbereich, T043/#50 kopiert Vorlagen/Importe. Keine zweite Global-Struktur oder projektübergreifenden Live-Rezepte. |
| PA-02 Canvas | T030 / #37 | Zahnradkarten, Name/Kategorie/Aktivierung/Validierung/Buildstatus/Assetanzahl, Vorlagenanlage, Editor und Eigenschaften auf vorhandenen Canvas-Komponenten. Projektkanten, Zuweisung und typisierter Bildfluss getrennt; Auswahl/Zoom/Undo/Redo, Archivierung und Entwurfsschutz erhalten. Verschieben ändert nur Layout. |
| PA-03 Grafikprofile | T026 / #33 | Gemeinsame projektweite Profile; Standardkeys `comic_high`, `comic_mid`, `comic_low`, `pixel_high`, `pixel_low` erhalten, aber keine feste Fünfergrenze. Drei aktive und zusätzliche Profile, stabile IDs unabhängig von Name/Position, deaktiviert = `not_required`. T013/#20 und Verbraucher lesen dieselbe Quelle. |
| PA-04 Skalierung | T026 / #33 | Ein Faktor oder maximale Framekante; Maße nur zur Kontrolle. HD 1, Mid 0,5, Low 0,25; Pixel High maximal 128, standardmäßig bis 64 Farben; Pixel Low 0,9 der tatsächlichen High-Zelle, gleiche Palette ohne neue Mischfarben. Comic/High aus HD, Low aus High. Raster, Reihenfolge, Alpha, Crop, Anker und logische Weltgröße erhalten. |
| PA-05 Schaltbare Verarbeitung | T023 / #30 | Wiederverwendbare SourceColor-/SpritesheetColor-, Paletten-/Material-/Alpha-Schritte mit gespeicherten inaktiven Parametern. `soft`, `fixed`, `material` sind Alternativen mit echten Pflichtangaben; keine erfundenen Regler/CLI-Schalter. T027/#34 liefert separat finale Farbgarantie/Nachzuordnung, T020/#27 bestätigte Maskenrevisionen. |
| PA-06 Frames und Zeit | T025 / #32 | Quellframes, Zielauswahl, Wiedergabe-FPS, Vorschau-FPS, Dauer und Loop getrennt. T024/#31 liefert Fram8/Fram16 und Auswahl/Geometrie; T025 liefert Timing, variable Bilddauern, geschützte Frames und Ereigniszeitpunkte. Kein Zusammenlegen dieser Aufgaben. |
| PA-07 Zuweisung | T013 / #20 | Rezeptreferenz am Asset bzw. Typ/Fähigkeit, keine Rezeptkopie je NPC. Explizites Asset vor Typregel vor Projektstandard; gleichrangige Konflikte sichtbar. Reale Typen einschließlich NPC, bestehende Helden nicht umklassifizieren. T016/#23 liefert Asset-Bedienung, T030/#37 Dry-run und zentrale Bedienung. |
| PA-08 Technischer Unterbau | T018 / #25 | Vorhandene BuildGraph-/Planer-/Cache-Verträge und Rezeptübersetzung erweitern; T017/#24 liefert Adapter/Job-Ausführung. Keine zweite Queue, kein zweiter Runner/technischer Graph/Profilkatalog. Unveränderliche Snapshots, sichere Arbeitskopien und selektive Invalidierung. |
| PA-09 Automatik und Freigaben | T030 / #37 | Rezeptimport und Zuweisung starten keinen Build. Ausdrücklich aktiviertes Bauen nach stabilem Quellenimport bleibt gesonderte Funktion über T015/#22; nicht bereits als vorhanden ausgeben. Speichern, Bauen, technische Prüfung, menschliche Abnahme, Freigabe und Aktivierung getrennt. |
| PA-10 Python-Erweiterungen | T017 / #24 | Versionierter deklarativer Manifest-/Adaptervertrag, ausdrückliche Registrierung und Hashfreigabe, erneute Freigabe bei Codeänderung. T043/#50 verwendet ihn für Bibliothek/Austausch; kein zweiter Plugin-Runner. Keine Ausführung beim Öffnen/Import/Anzeigen, kein Shelltext/Autoinstall/ungefragtes Netz. Worker ist keine Sicherheits-Sandbox. |
| PA-11 Rezeptaustausch | T043 / #50 | JSON-Rezept und Paket mit deklarativen Ressourcen, echte Vorschau/Übernahme und neue konsistente IDs. Vorhandenen Austauschdienst/Editor aus T030 nutzen; fehlende Werkzeuge blockieren Entwürfe. Quellenimport und Codefreigabe sind andere Abläufe. Legacy-Canvas ist zunächst visuell, keine aus Pfeilen erfundene Ausführung. |
| PA-12 Kompatibilität/Verbraucher | T035 / #42 | Gemeinsamer Übergabevertrag für Profilidentität, Pfad, Raster, Frames, Timing, Anker, Crop und logische Größe. T018 erhält Rezeptrevisionen/Snapshots, T026 die Profilmigration, T031/T032 Vorschau/Matrix, T033/T034/T041/T042 Historie/Export/Doku, T044 Sicherung, T037/T045/T046 prüfen Verbraucher. Kein vollständiges Godot-Grafikmenü neu planen. |

Zusätzliche verbindliche Details des ursprünglichen Pipeline-Auftrags:

- Vorlagen A–F: Grafik-Assets (#33), Fram8 und Fram16 (#31), Frame-Reduktion
  mit Timing (#31/#32), SpritesheetColor und SourceColor (#30), zusätzlich
  leeres Rezept (#37). Sie sind veränderbare Ausgangskopien; Fram8/16 sind
  alternative Aufbereitungen passender Quellen, keine pauschale Kette.
- Bei maximaler Kante gilt `s = min(1, L / max(W, H))`, Dimension mindestens
  ein Pixel. Bestand verwendet deterministisches positives Half-up
  (`floor(v + 0.5)`, Decimal); Rundungsabweichungen dokumentieren. Keine
  Vergrößerung kleiner Quellen im Downscale-Modus, keine Null-/Negativ-/NaN-/
  Unendlich-Werte. Pixel-Verfahren nicht durch generisches Resize ersetzen.
- Grafikstandard funktioniert ohne Materialmasken; optionale Farbschritte ohne
  konfigurierte Referenzen bleiben aus. Erforderliche nachfolgende Eingaben
  beim Ausschalten entweder typverträglich durchreichen oder konkret blockieren.
  Pixel Low darf High intern benötigen, obwohl High nicht Ausgabeziel ist.
- Exakte Endfarben nach glatter Skalierung erfordern erneute Zuordnung/Prüfung
  (#34), nicht bloß den Hinweis auf eine frühere Farbkorrektur (#30). Labelmasken
  folgen derselben Frameauswahl/Geometrie ohne interpolierte IDs. Formatfremde
  Farbprofile nicht umdeuten, keine ungeprüfte Ersatzpalette oder Materialmaske.
- Legacy-Auswahl `floor(16*k/N)` für N = 8/10/12/14, identisch über Richtungen.
  Keine Zwischenbilder oder wiederholten Bilder als neue Animation ausgeben.
  16 Frames/8 FPS = 2 s; 8 Frames/4 FPS erhalten 2 s. Bestehendes Timing
  migriert unverändert. Vorschau-FPS sind flüchtig bis zur ausdrücklichen
  Übernahme. Statische Bilder erhalten keine Frames/FPS/Loops. Keine erfundene
  `--fps`-Option an Starter mit festem GIF-Timing übergeben.
- Auf Assets: wirksames Rezept, Herkunft, Revision, angeforderte Profile,
  freigegebene lokale Abweichungen und Ergebnisstatus. Neue passende Assets
  erben Typregeln ohne Build. Sammel-Dry-run nennt betroffene, ausgeschlossene,
  blockierte Assets und Ausgaben; keine Verkettung durch Kartenposition.
- Vor Verarbeitung Typen, fehlende Eingaben, Zyklen und Ausgabekollisionen
  prüfen. Echte PNG-Ergebnisse verifizieren; Exit 0/Diagnosedateien genügen nicht.
  Originale bytegleich halten, keine veränderbaren Hardlinks. Ableitungen bleiben
  beim selben Asset. Fortschritt, Logs, Timeout, Abbruch, Fehler, Wiederaufnahme
  und begrenzte Parallelität über den bestehenden nichtblockierenden Jobweg.
- Snapshot bindet Quellen, Rezeptrevision, Profile, aktive Parameter, Masken,
  Paletten und Werkzeug-/Pluginversionen bzw. Hashes. Laufende Jobs nicht durch
  spätere Änderungen umschreiben; bei fehlender passender Toolversion blockieren.
  Layout/inaktive Parameter invalidieren keine Bilder. Änderung nur an Comic
  Low betrifft nicht unabhängige Zweige; gemeinsame Palette alle Abhängigkeiten.
  Erst geprüfte vollständige Ergebnisse veröffentlichen, keine Fremddateien
  durch Ordnerbereinigung löschen.
- Manifest: ID, Name, Version, Beschreibung, Parameter, Ein-/Ausgabetypen,
  Fähigkeiten, Entry-Point und Abhängigkeiten. Eigenschaften aus Manifest,
  Ausführung durch registrierten Adapter. Beispiel Graustufen nach ausdrücklicher
  Hashfreigabe echt ausführbar, im Standard aus. v1 ist zunächst ein Bild hinein/
  heraus bei gleicher Geometrie; Erweiterungen dieses Vertrags ausdrücklich
  versionieren. Ohne zusätzliche Sandbox nur vertrauenswürdigen Code ausführen.
- Importvorschau nennt Schritte, Profile, Parameter, Ressourcen, fehlende Tools,
  Codebestandteile und Namens-/ID-Konflikte. Schema, Größen, referenzierte Pfade,
  ZIP-Traversal, Symlinks, Duplikate und Entpacklimits prüfen. Kein Export von
  Originalassets, privaten Absolutpfaden, Cache, Jobs, Zugangsdaten oder lokalen
  Codefreigaben. Historische Canvas-Pfade ohne Nummernpräfix gezielt auflösen
  und protokollieren; keine globale Textersetzung oder Ausführung referenzierter
  Skripte. Rezeptimport startet nicht automatisch und überschreibt nichts still.
- Profilmigration idempotent/transaktional mit bestehender Sicherung und
  Rollback. Alte Keys, Assetbindungen, CLI-Wege und Timing erhalten; unbekannte
  Keys nicht heimlich als Comic High lesen. Neue Studio-Keys gelten erst nach
  tatsächlicher Verbraucherprüfung als in Godot unterstützt. Statische
  Paketmaßstäbe/Kachelregeln und `game/test_assets/` → bewusste Freigabe →
  `game/assets/` bleiben unverändert.

### Ersetzte Vorgaben und erhaltene Anforderungen

| Altvorgabe / mögliche Fehlinterpretation | Aktive Regel / Eigentümer |
| --- | --- |
| Genau fünf Profile bzw. 5×5 immer Pflicht | Fünf Standards als Regression; Pflicht sind angeforderte aktive Profile und interne Abhängigkeiten. Freie Projektmenge; #33, Matrix #39. |
| Jedes NPC-Asset hat eigenes kopiertes Rezept | Projektlokale Rezeptreferenz und explizite Zuweisung; #20/#23. |
| T017/T018 erneut neu bauen, ausschließlich Diagnose | Bestehende Dienste und echte Bildadapter erhalten; nur belegte Restarbeit/Integration/Regression. #24/#25. |
| Ausschließlich eingebaute Worker (#50) | Eingebaute plus ausdrücklich registrierte, hashfreigegebene Erweiterungen nach #24. Import allein bleibt untrusted. |
| Unabhängiger Vorlageneditor/Runner (#50) | Vorlagenverwaltung nutzt Rezeptmodell aus #25, Profile #33, Editor #37 und Jobweg #24. |
| Fram16 bzw. korrigierte Quelle für jeden Grafiklauf | Passende Fram8/16-Aufbereitung, optionale Farbe, Quelle nach Rezept; #31/#33. |
| Kein automatischer Importlauf jemals / oder jeder Import startet | Kein Start durch Rezeptimport/Zuweisung; gesonderte Opt-in-Automatik nach stabilem Quellenimport mit Freigabeschranken bleibt #37. |
| Neuer Pipeline-Stand ersetzt ursprüngliche Detailprüfungen | Raster/Anker, unabhängige Originale, variable Dauern, Pflichtframes, Ereigniszeiten, Masken-Sichtabnahme, Paketmaßstab und sichere Promotion bleiben Pflicht. |

Die [Issue-Patches](pipeline-alignment-v1/issue-updates.json) protokollieren
konkrete ersetzte Textstellen und vollständige neue Beschreibungen. Alle nicht
benannten Absätze und alten Checkboxen bleiben erhalten. Eine Altprüfung ist
kein Nachweis ihrer Erweiterung. Zulässige Bugfixes und später ausdrücklich
angenommene Änderungen bleiben möglich; geschützt wird vor unbeabsichtigtem
Rückbau, nicht vor Entwicklung.

### Abhängigkeiten und Arbeitsreihenfolge

Frühe gemeinsame Verträge sind bereits auf `main`: #25 verantwortet
Rezept/Snapshot/Graph, #33 die gemeinsame Profilquelle, #20 die Zuweisung,
#24 Erweiterungs-/Ausführungssicherheit. Ihre spätere Nutzung ist nicht jeweils
eine neue Rückwärtsblockade. #37 verwendet diese Verträge ohne auf den gesamten
Bibliotheksabschluss #50 zu warten; #50 verwendet den Editor aus #37.

Die vorhandene Kante **#50 ist blockiert durch #37** bleibt erhalten; die
umgekehrte Kante existiert nicht und wird nicht angelegt. Auch die übrigen
Voraussetzungen bleiben: Material-/Timing-/Paket-Vollabnahmen sind weiterhin
für den gesamten Abschluss der jeweiligen Aufgabe erforderlich, blockieren
aber nicht nachträglich bereits vorhandene Teilfunktionen. Phasen sind
organisatorisch; ein fachlicher Querverweis ist keine native Blockade.
Der [Beziehungsbestand](pipeline-alignment-v1/relationships.json) hält Eltern,
Kinder und blockierende Kanten getrennt. Keine neue Aufgabe ist nötig; es
bleibt keine unbesetzte PA-Zuständigkeit und kein #37/#50-Zirkel.

### Aktuelle Arbeitsaufträge, historisches Archiv und Veröffentlichung

Das gesamte Paket `tools/AssetManager/works/EtherFood_Codex_Aufgabenplan/`
ist ein **unveränderliches historisches Original**, einschließlich `tasks.json`,
`FORTSCHRITT.md`, `START_HIER.md`, Architektur, Matrix und aller `p.md`.
Alle 81 Hashes und die exakte Dateimenge bleiben erhalten. Nichts hinzufügen,
umschreiben oder neu hashen. Seine `not_started`-Werte sind kein Ist-Status.
Die [vorgeschalteten Arbeitsregeln](../../../../tools/AssetManager/works/AGENTS.md)
und der [Planungseinstieg](../../../../tools/AssetManager/works/README.md) führen
von diesem Archiv zu dieser verbindlichen Ergänzung.

Aktueller Auftrag = unersetzte Originalanforderungen + konkrete Präzisierungen
in `PIPELINE-ALIGNMENT-V1` + neuester Issue-/Kommentar-/Checkout-Stand.
`issue-updates.json` ist die deklarative Veröffentlichungsergänzung, keine
zweite Anwendungsdatenbank und kein blind anwendbarer Statussnapshot.
Vor jedem erneuten Schreiben Live-Issue inklusive Checkboxen/Metadaten lesen,
mit `before` bzw. zuletzt verifiziertem `after` vergleichen und parallele
Änderungen erhalten. Marker aktualisieren statt duplizieren. Bei Konflikt nur
dieses Issue auslassen und den konkreten Konflikt berichten.

Im Repository wurde **kein ausführbarer Issue-Publisher** gefunden. Die
ursprüngliche Veröffentlichung verwendete flüchtige Sitzungsdaten. Ein alter
Publisher, der allein `tasks.json`/`p.md` benutzt, ist **nicht sicher verwendbar**
und darf nicht erneut publizieren. Er muss vorher die deklarative Ergänzung
und den Live-Vergleich berücksichtigen. Dies ist eine dokumentierte Sperre,
keine technisch erzwungene Sicherung gegen unbekannte externe Skripte.
Generatorcode wird in diesem Auftrag nicht geändert; historische
Integritätsprüfungen werden nicht abgeschwächt.

### Prüfungen, Wiederherstellung und Abschlussnachweis

Geplant sind ausschließlich lesende Archiv-, JSON-, Matrix-, Link-,
Checkbox-/Metadaten- und DAG-Prüfungen sowie Git-Diff-Kontrolle. Anwendungen,
Produktionsbuilds und Godot werden hier nicht getestet. Ausgangssnapshot und
Planungscommit bleiben getrennt; kein Reset, Force-Push oder pauschaler
Issue-Rollback. Eine nötige Korrektur wird gegen den dann aktuellen Inhalt
gezielt vorgenommen. Vorherwerte/Checkboxen/`updatedAt`, konkrete Ersetzungen
und nach erneutem Abruf bestätigte Nachherwerte stehen in den deklarativen
Issue-Patches. Historische Kommentare werden nicht editiert.

Ergebnis des unabhängigen GitHub-Rücklesens: 35 gespeicherte Beschreibungen
entsprechen den Patches; alle 306 alten Checkboxen sowie Titel, Zustände,
Bearbeiter, Labels, Meilensteine, Kommentare und Beziehungen sind unverändert.
41 weitere Issues einschließlich der Szeneneditor-Roadmap sind unverändert.
Keine neuen Issues/Kommentare/PRs, keine geänderten Abhängigkeitskanten.
Alle 251 nativen Blockadekanten im 76-Issue-Bestand sind azyklisch; darunter
unverändert 227 ursprüngliche T-Aufgabenabhängigkeiten. 74 Eltern-Kind-Kanten
bleiben getrennt davon erhalten. #50 → #37 besteht, #37 → #50 nicht.

Der vollständige [Änderungs-/Abschlussbericht](pipeline-alignment-v1/README.md)
und der [Prüfnachweis](pipeline-alignment-v1/verification.json) unterscheiden
Planung, historische Techniknachweise und weiterhin offene Funktion/Abnahme.
Anwendungs-, Pipeline-, Qt- und Godot-Tests sowie der volle Repository-Check
wurden in diesem reinen Planungsauftrag **nicht ausgeführt**.

## Historischer Veröffentlichungsbericht (unverändert zu lesen als damaliger Stand)

## Zweck und Gesamtbild

Den vorhandenen `EtherFood_Codex_Aufgabenplan` als nachvollziehbare,
deutschsprachige GitHub-Roadmap für das lokale Asset- und Verwaltungswerkzeug
veröffentlichen. Ein Hauptissue, sechs Phasen und 48 Aufgaben bilden eine
echte Unterissue-Hierarchie. Titel beginnen mit einem passenden Emoji.

## Ausgangslage

- Repository: `Blobbite/EtherFood`, Branch `main`.
- Plan im aktuellen Arbeitsbaum:
  `tools/AssetManager/works/EtherFood_Codex_Aufgabenplan/`.
- Bestehende Pipelines: `tools/AssetManager/PyGameTools/`.
- Die lokale Verschiebung ist noch nicht committed. Der veröffentlichte
  Planstand ist im Commit `59ae32d23e0c18075d6837c35895aa82c08682cd` unter
  `docs/works/EtherFood_Codex_Aufgabenplan/` erreichbar.
- Bei Beginn waren keine offenen oder geschlossenen Repository-Issues und
  keine Meilensteine vorhanden. Die 48 Planaufgaben stehen auf `not_started`.

## Umfang und Nicht-Ziele

Veröffentlicht werden Aufgaben, Tests, Abnahmekriterien, Voraussetzungen und
Phasenabschlüsse einschließlich der Einbindung in das bestehende Godot-Projekt.
Die Erstellung der Issues implementiert keine Planaufgabe und erteilt keine
Asset-Freigabe. Bestehende Arbeitsbaumänderungen werden weder committed noch
verändert. Die Dokumentation bleibt unter `docs/system/`; die Planvorschläge
`docs/asset-studio/` werden entsprechend angepasst.

## Schritte und Fortschritt

- [x] Repository, Authentifizierung, vorhandene Issues und lokale Pfade prüfen.
- [x] Alle Aufgabeninhalte, Anforderungsabdeckung und Abhängigkeiten aufbereiten.
- [x] Hauptissue, sechs Phasen, 48 Aufgaben und Meilensteine veröffentlichen.
- [x] Unterissues, Voraussetzungen und Navigation miteinander verbinden.
- [x] Veröffentlichte Inhalte und sämtliche Beziehungen erneut abrufen und prüfen.

## Erkenntnisse und Entscheidungen

- Die Hierarchie ist `Hauptissue → Phase → Aufgabe`; fachliche Voraussetzungen
  werden getrennt von dieser organisatorischen Zuordnung abgebildet.
- Unfreigegebene Engine-Assets bleiben unter `game/test_assets/`, Tests unter
  `game/test_scenes/`; Freigaben übernehmen die geprüften relativen Assetpfade
  nach `game/assets/`. T035 klärt den Loadervertrag anhand des Bestands.
- Das Werkzeug wird als lokale Python-Anwendung mit Godot-Anbindung geplant;
  es wird keine zusätzliche Web- oder Cloud-Infrastruktur vorausgesetzt.
- Die bisherigen Ignore-Regeln nennen noch `tools/PyGameTools/`. Die Folgen
  der lokalen Verschiebung werden in Bestandsaufnahme und Git-Aufgabe erfasst,
  bevor generierte Bildbestände versehentlich versioniert werden.
- Dauerhafte Quellenlinks zeigen auf den veröffentlichten Commit. Die
  Beschreibungen nennen zusätzlich die aktuellen lokalen Pfade.

## Prüfungen

Die lesende Planprüfung (`python3 pruefung/check_plan.py --json`) ist bestanden:
48 Aufgaben, 36 Anforderungen, 955 lokale Links und 81 Dateihashes. Die
Veröffentlichungsvorbereitung hat sechs Phasen mit je acht Aufgaben, 227
azyklische Voraussetzungen und 384 übernommene Test-/Abnahmepunkte geprüft.
Alle 48 Originalaufträge stimmen bytegenau mit dem gepinnten GitHub-Commit
überein. Es sind 55 Issue-Beschreibungen vorbereitet; die veröffentlichten
Inhalte und Beziehungen wurden anschließend vollständig mit GitHub abgeglichen.
Der erneute API-Abruf bestätigt ohne Abweichungen:

- 55 offene Issues mit den vorbereiteten Titeln und vollständigen Beschreibungen;
- 54 Eltern-Kind-Beziehungen einschließlich der richtigen Reihenfolge;
- 227 Aufgabenabhängigkeiten in der richtigen Richtung;
- sechs Meilensteine mit je einer Phase und acht Aufgaben;
- 69 unterschiedliche Quellenlinks auf vorhandene Dateien im gepinnten Commit.

`git diff --check -- docs/system/development/plans` war erfolgreich.
Anwendungstests werden für diesen reinen Planungsauftrag nicht als ausgeführt
oder bestanden dargestellt.

## Wiederholbarkeit und Wiederherstellung

Issues werden anhand stabiler Plan-IDs zugeordnet. Vor jedem erneuten Anlegen
werden bestehende Zuordnungen geprüft. Die temporären Veröffentlichungsdaten
liegen ausschließlich unter `/run/codex-session/`; sie enthalten keine Tokens.
Ein unterbrochener Lauf setzt bei fehlenden Inhalten oder Beziehungen fort.
Es werden keine fremden Issues geschlossen oder gelöscht.

## Ergebnis und Rückblick

Veröffentlicht: [Hauptissue #1](https://github.com/Blobbite/EtherFood/issues/1),
sechs Phasen (#2–#7), 48 Aufgaben (#8–#55) und sechs Meilensteine.
Die 54 Eltern-Kind-Beziehungen und 227 Voraussetzungen sind angelegt; Hauptissue
und Phasen besitzen vollständige Übersichtslinks. Der abschließende
GitHub-Abgleich ist erfolgreich. Neun ergänzende Labels kennzeichnen Vorhaben,
Phasen, Aufgaben und betroffene Arbeitsbereiche.

| Phase | GitHub-Issue | Aufgaben | Meilenstein |
| --- | --- | --- | --- |
| 🏗️ A: Grundlagen | [#2](https://github.com/Blobbite/EtherFood/issues/2) | T001–T008, #8–#15 | [Phase A](https://github.com/Blobbite/EtherFood/milestone/1) |
| 🖥️ B: Dashboard | [#3](https://github.com/Blobbite/EtherFood/issues/3) | T009–T016, #16–#23 | [Phase B](https://github.com/Blobbite/EtherFood/milestone/2) |
| 🎨 C: Verarbeitung | [#4](https://github.com/Blobbite/EtherFood/issues/4) | T017–T024, #24–#31 | [Phase C](https://github.com/Blobbite/EtherFood/milestone/3) |
| 🔍 D: Variantenprüfung | [#5](https://github.com/Blobbite/EtherFood/issues/5) | T025–T032, #32–#39 | [Phase D](https://github.com/Blobbite/EtherFood/milestone/4) |
| 🎮 E: Godot-Integration | [#6](https://github.com/Blobbite/EtherFood/issues/6) | T033–T040, #40–#47 | [Phase E](https://github.com/Blobbite/EtherFood/milestone/5) |
| 🏁 F: Betrieb und Pilot | [#7](https://github.com/Blobbite/EtherFood/issues/7) | T041–T048, #48–#55 | [Phase F](https://github.com/Blobbite/EtherFood/milestone/6) |

Einstieg: [T001 / #8](https://github.com/Blobbite/EtherFood/issues/8).
Alle Implementierungsaufgaben bleiben offen; die Veröffentlichung der Roadmap
setzt weder ihren Bearbeitungsstand noch einen Asset-Freigabestatus auf erledigt.
