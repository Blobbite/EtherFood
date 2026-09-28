# PIPELINE-ALIGNMENT-V1: Änderungs- und Abschlussnachweis

Stand: 28.09.2026. Dies ist ein Änderungsnachweis, keine zweite Roadmap.
Verbindlicher Einstieg bleibt die Ergänzung im vorhandenen
[GitHub-Aufgabenplan](../asset-studio-github-issues.md).

## 1. Tatsächlich angepasste Issues

35 Beschreibungen gespeichert und anschließend unabhängig erneut gelesen.
Keine Titeländerungen; alle vorhandenen Emojis bleiben. Die sechs übergeordneten
Issues #1 und #3–#7 erhalten aktuelle Zuständigkeiten, Fortschrittsabgrenzung,
Rückbauschutz und Verweise. Phase A/#2 bleibt unverändert.
Die übrigen 29 Änderungen:

| Issues / Plan | Tatsächliche Präzisierung | Nachweis / offener Rest |
| --- | --- | --- |
| [#20](https://github.com/Blobbite/EtherFood/issues/20) / T013 | Typen/Fähigkeiten und referenzbasierte Zuweisungsregeln am Asset; vorhandene Typverwaltung erweitern, keine NPC-Rezeptkopien. | Typen, Richtungen und Variantenmatrix sind technisch vorhanden (T013); NPC und Projektprofilauflösung in 2286d2f. Neue Prioritäts-/Projektgrenzenregression und persönliche Abnahme getrennt nachweisen. |
| [#21](https://github.com/Blobbite/EtherFood/issues/21) / T014 | Den vorhandenen lesenden Scanner an die gemeinsame Projektprofilauflösung anbinden; unbekannte Keys weiter als Konflikt behandeln. | T014 technisch abgehakt; 2286d2f erweitert Profilauflösung. Kein neuer Scanner, keine neuen aktuellen Tests behaupten. |
| [#22](https://github.com/Blobbite/EtherFood/issues/22) / T015 | Den vorhandenen Quellenimport erhalten und eine klar benannte Schnittstelle für stabile abgeschlossene Lieferungen bereitstellen. | T015 und 6a technisch vorhanden; Quellenbutton/Raster wurden vom Benutzer geprüft, daraus folgt keine neue Pipeline-Abnahme. Optionale Automatik noch separat offen. |
| [#23](https://github.com/Blobbite/EtherFood/issues/23) / T016 | Bestehendes Asset-Menü/Anlageassistent um wirksame Rezeptreferenz, Herkunft, Revision, Zielprofile, erlaubte lokale Abweichungen und Ergebnisstatus integrieren. | T016/e4166c8 und Zwischenpakete technisch vorhanden; 2286d2f liefert Pipeline-/Varianten-/Bildaktionen. Kein Neuaufbau der Asset-Verwaltung. |
| [#24](https://github.com/Blobbite/EtherFood/issues/24) / T017 | Bestehenden PipelineAdapter-/Job-/Worker-Vertrag erhalten; primär Manifest, Registrierung, Hashfreigabe und kontrollierte Python-Erweiterung verantworten. | 4ef37bd implementiert Prozessverwaltung; 2286d2f ergänzt echte Bildadapter und PluginService. Linux-/proc-Grenze bleibt. Persönliche Abnahme offen. |
| [#25](https://github.com/Blobbite/EtherFood/issues/25) / T018 | Vorhandene projektlokale Rezept-/Revisions-/Snapshot-Verträge und Übersetzung in den bestehenden technischen DAG verantworten; Cache/Invalidierung fortführen. | 4b16da4 liefert DAG/Cache; 2286d2f Rezeptintegration und echte Bildzweige. Keine erneute neunstufige Diagnose als Bildimplementierung. |
| [#26](https://github.com/Blobbite/EtherFood/issues/26) / T019 | Freie Masterreferenzen und neue Farbprofilformate weiter liefern; nicht mit projektweiten Auflösungsprofilen verwechseln. | Variable Referenz-/Profilbildung bleibt eigenständiger offener Umfang. Vorhandene Color-Adapter sind kein Nachweis dieser Erweiterung. |
| [#27](https://github.com/Blobbite/EtherFood/issues/27) / T020 | Materialdefinition, MaskRevision und technische versus menschliche Bestätigung im gemeinsamen Rezept-/Ressourcenvertrag weiter liefern. | Gebundene Maskenprüfung/-ressourcen vorhanden; vollständige Maskenrevision-/Sichtabnahmeverwaltung nicht daraus als fertig ableiten. |
| [#29](https://github.com/Blobbite/EtherFood/issues/29) / T022 | Deterministische, korrigierbare Maskenvorschläge mit offenen Unsicherheiten als optionalen Verarbeitungsschritt ergänzen. | Neue fachliche Vorschlagsfunktion weiterhin offen; echte Farbausführung ersetzt keine semantische Materialerkennung. |
| [#30](https://github.com/Blobbite/EtherFood/issues/30) / T023 | Wiederverwendbare SourceColor-/SpritesheetColor-Schritte und modusspezifische Parameter/Ressourcen in bestehende Bildadapter integrieren und regressionsprüfen. | Color-Schritte und echte Farbtests in 2286d2f vorhanden. Masterprofil-Erstellung und vollständige visuelle Maskenfreigaben bleiben Rest bei #26–#29. |
| [#31](https://github.com/Blobbite/EtherFood/issues/31) / T024 | Fram8-/Fram16-Aufbereitung und Legacy-Frameauswahl samt Raster, Zuschnitt, Quellindizes und Ankern im vorhandenen Adapter erhalten/ergänzen. | prepare8/prepare16/reduce und Geometrie in 2286d2f vorhanden; vollständige HTML-/Maskentransformations- und Originalkonfliktabnahme bleibt gesondert. |
| [#32](https://github.com/Blobbite/EtherFood/issues/32) / T025 | Timing-Vertrag mit Wiedergabe-FPS beibehalten / Animationsdauer beibehalten pflegen; variable Dauern, Pflichtframes und Ereigniszeitpunkte noch vervollständigen. | Gleichmäßiges keep_fps/preserve_duration und flüchtige Vorschau-FPS in 2286d2f vorhanden. Variable Dauern, geschützte Frames und Ereignisse nicht als erledigt ausgeben. |
| [#33](https://github.com/Blobbite/EtherFood/issues/33) / T026 | Gemeinsame Projektprofilquelle und proportionale Resolution-Verarbeitung verantworten; bestehende fünf Keys als Standards und zusätzliche Profile unterstützen. | ProfileService/domain.graphics und echte Skalierung in 2286d2f vorhanden, aktuell 1–64 Profile. Neue Verbraucher/Godot-Abnahme nicht behaupten. |
| [#34](https://github.com/Blobbite/EtherFood/issues/34) / T027 | Finale Farbgarantie und erforderliche diskrete Maskenableitung/Nachzuordnung nach Skalierung liefern; kein Duplikat von #30. | Reihenfolgeprüfung/fixed-Nachzuordnung existiert im Bildweg; vollständige materialtreue Grenzzuordnung und Runtime-Masterprüfung bleiben konkret zu prüfen/ergänzen. |
| [#35](https://github.com/Blobbite/EtherFood/issues/35) / T028 | Statischen Texturvertrag auf gemeinsamer Profil-/Rezeptquelle vervollständigen: Paketmaßstab, Kachelränder und unterstützte Bildarten. | Statische PNG-Skalierung vorhanden; reservierter --Textur-CLI und spezielle Kachel-/Datenkartenverträge nicht damit als abgeschlossen deklarieren. |
| [#36](https://github.com/Blobbite/EtherFood/issues/36) / T029 | Unveränderten Paketumfang liefern: gepinnte Mitglieder, Scope/Mehrfachverwendung, Rollen, Paketrevision und Prüfaufstellung. | Paketassistent, Mitgliederpinning und Abnahme weiterhin nach ursprünglichen Kriterien. Keine Erweiterung zur Szeneneditor-Roadmap. |
| [#37](https://github.com/Blobbite/EtherFood/issues/37) / T030 | Projektlokale Pipeline-Zahnradkarten und gemeinsamen Canvas-Editor mit vorhandener Auftragsbedienung integrieren; Queue/Priorität/Fortsetzen und Opt-in-Importautomatik vervollständigen. | Pipeline-Editor, Karten, Eigenschaften, echte Ausführung/Logs/Abbruch in 2286d2f vorhanden. Keine zweite Jobs-UI/Queue; gesamte Automatik und persönliche Abnahme bleiben offen. |
| [#38](https://github.com/Blobbite/EtherFood/issues/38) / T031 | Bestehende Ergebnisvorschau um sichere HTML-/GIF-/Versionsvergleiche ergänzen, keine zweite Ergebnisübersicht. | PNG-Vorschau/transiente FPS/Ergebnisprüfung vorhanden; QtWebEngine-/HTML-Integration und vollständige Vergleichsabnahme bleiben offen. |
| [#39](https://github.com/Blobbite/EtherFood/issues/39) / T032 | Vorhandene Variantenauflösung zur dynamischen Prüfmatrix und buildgebundenen Sichtabnahme ausbauen. | Anforderungsmatrix und Ergebnisstatus teilweise vorhanden; Reviews/Befundbindung/Tour/Abnahmemanagement nicht als erledigt ausgeben. |
| [#40](https://github.com/Blobbite/EtherFood/issues/40) / T033 | Kandidaten zusätzlich mit effektiver Rezeptrevision, Profilen, lokalen Parametern und Werkzeug-/Pluginhashes einfrieren. | Unveränderliche Buildsnapshots vorhanden; selbsttragendes Kandidatenarchiv weiterhin eigener offener Liefergegenstand. |
| [#41](https://github.com/Blobbite/EtherFood/issues/41) / T034 | Deterministische ausgewählte Metadatenexporte um Rezepte/Zuweisungen/Projektprofile ergänzen. | Git-Snapshot dieses Planungsauftrags ersetzt nicht den geplanten Manager-Gitdienst. |
| [#42](https://github.com/Blobbite/EtherFood/issues/42) / T035 | Godot-Übergabevertrag auf wirksame angeforderte Projektprofile und vollständige Bild-/Geometrie-/Zeitmetadaten abstimmen. | Studio liefert Metadaten; beliebige neue Keys im vorhandenen Godot-Menü/Loader sind noch kein nachgewiesener Support. |
| [#44](https://github.com/Blobbite/EtherFood/issues/44) / T037 | Godot-Checks auf tatsächlich angeforderte Profile und präzise Metadaten erweitern; persönliche Abnahme getrennt erhalten. | Godot-Prüfungen des Pipelinepakets nicht ausgeführt; synthetische Studio-Tests beweisen keine Engine-Abnahme. |
| [#48](https://github.com/Blobbite/EtherFood/issues/48) / T041 | Verlauf/Status um Rezeptrevision, wirksame Zuweisung, Parameter, Profile und Werkzeugversion ergänzen. | Vorhandene Revisions-/Jobanzeigen erhalten; globale Versions-/Freigabeübersicht weiter offener Umfang. |
| [#49](https://github.com/Blobbite/EtherFood/issues/49) / T042 | Bestehende Dokumentationsplanung um wirksame Pipeline-Rezepte, Zuweisungsherkunft und eingefrorene Parameter/Profile/Toolversionen ergänzen. | Bedien-/Prüfberichte vorhanden, automatische portable Dokumentgeneratoren nicht daraus als fertig ableiten. |
| [#50](https://github.com/Blobbite/EtherFood/issues/50) / T043 | Vorlagen-/Kartentypbibliothek, Revisionen und sicheren Rezept-/Vorlagenimport/export auf gemeinsamen Diensten vervollständigen. | Sechs Bildvorlagen plus leeres Rezept, sicherer JSON/ZIP-/Legacy-Austausch und Graustufenbeispiel in 2286d2f vorhanden. Vier ursprüngliche Typbeispiele und vollständiger Bibliotheksumfang bleiben zu prüfen. |
| [#51](https://github.com/Blobbite/EtherFood/issues/51) / T044 | Sicherung/Restore/Recovery um Rezepte, Ressourcen, Zuweisungen, variable Profile und Revisionsbindungen ergänzen. | Migrationssicherung und Job-Recovery vorhanden; vollständige portable Sicherung noch gesondert nachzuweisen. |
| [#52](https://github.com/Blobbite/EtherFood/issues/52) / T045 | Animierten E2E-Nachweis um projektlokale Rezepte, Regeln, variable Profile und echte Bild-/Fehler-/Cache-/Importfälle ergänzen. | Synthetische PNG-/Frame-/Farbtests des Pipelinepakets sind Teilnachweise, kein vollständiger Godot-/Promotion-/Pilotabschluss. |
| [#53](https://github.com/Blobbite/EtherFood/issues/53) / T046 | Statischen Paket-/Scope-E2E um variable Profile, portable Rezeptkopien und konsistenten Restore ergänzen. | Statische Einzelbildableitung vorhanden; Paketanschluss-/Godot-/Restore-E2E nicht dadurch bestanden. |

Die vollständigen Vorher-/Nachhertexte mit 47 fachlichen Textkorrekturen sowie
29 Kennzeichnungen historischer Quellen, ursprünglichen Checkboxen,
`updated_at`, Zuständigkeiten, Kommentaren und Beziehungen stehen in
[issue-updates.json](issue-updates.json). Neue Abschnitte verwenden eindeutige
Marker; es wurden keine Issue-Kommentare hinzugefügt. Zusätzlich zu den 306
unveränderten alten Checkboxen stehen 64 neue Integrations-/Abnahmepunkte
ausdrücklich offen. Das sind keine neuen Implementierungsissues.

## 2. Weiterhin gültige Anforderungen

Alle 36 R-Kennungen und 48 T-Kennungen mit ihren bisherigen Zuordnungen sind
in der [Matrix](requirements.json) erhalten. Insbesondere unverändert:
Raster-/Frameprüfung, eigenständige Originalvarianten, Quellhashbindung,
Anker/Crop/logischer Maßstab, echte Materialmasken und Sichtbestätigung,
variable Bilddauern, Pflichtframes, zeitbasierte Ereignisse, Loops,
Paketmaßstab/Kachelanschlüsse, Kandidatenbindung und sichere Godot-Promotion.
T027/#34 bleibt eigenständig neben T023/#30. T029/#36 bleibt ein
versioniertes Paket mit Prüfaufstellung, kein Szeneneditor.

## 3. Konkret ersetzte Vorgaben

- Fünf immer erforderliche Grafikprofile bzw. feste 5×5-Matrix → fünf
  Standardkeys plus tatsächlich angeforderte aktive Projektprofile;
  drei aktive und zusätzliche Profile, deaktiviert = nicht angefordert.
- Rezept am einzelnen NPC als Kopie → projektlokale Rezeptreferenz mit
  explizit > Typ/Fähigkeit > Projektstandard, gleichrangiger Konflikt sichtbar.
- T017/T018 als erneut zu bauende Diagnose-Erstversion → bestehender
  Adapter-/Job-/Graph-/Cacheweg plus bereits vorhandene echte Bildintegration.
- Ausschließlich eingebaute Worker in #50 → eingebaute sowie gesondert
  registrierte/hashfreigegebene Erweiterungen nach #24; Import führt nichts aus.
- Eigenständiger Vorlagen-Pipelineeditor → Bibliothek verwendet gemeinsamen
  Editor #37 und Rezept-/Profilverträge #25/#33.
- Fram16 bzw. Farbbearbeitung vor jedem Grafiklauf → passende Fram8/16-
  Alternative und ausdrücklich aktivierte Farbstufen, maskenfreier Standard.
- Pauschal „nicht begonnen“/„noch nicht committed“ → datierter tatsächlicher
  Bestand. Historische Kommentare/Originalberichte bleiben erhalten.

Die Originalformulierungen und jede Ersetzung sind einzeln in den Patches
nachvollziehbar; keine stillschweigende Streichung anderer Arbeitsschritte.

## 4. Endgültige Zuständigkeit

Die zwölf PA-Kennungen haben genau einen primären Integrationsverantwortlichen:
PA-01/#25, PA-02/#37, PA-03/#33, PA-04/#33, PA-05/#30, PA-06/#32,
PA-07/#20, PA-08/#25, PA-09/#37, PA-10/#24, PA-11/#50, PA-12/#42.
Angrenzende eigenständige Lieferungen stehen in der verbindlichen Tabelle:
insbesondere Frames #31 versus Timing #32, Grundfarbe #30 versus Endfarbe #34
und Pluginvertrauen #24 versus Bibliothek/Import #50. Das erzeugt keine
doppelten Implementierungszuständigkeiten.

## 5. Tatsächliche Beziehungen

**Keine Kante geändert.** Der erneut gelesene Bestand enthält 251 native
Blockadekanten über 76 Issues (davon 227 im ursprünglichen T-Plan) und
74 organisatorische Eltern-Kind-Kanten. Azyklisch, Textvoraussetzungen und
GitHub stimmen überein. #50 wird durch #37 blockiert, nicht umgekehrt.
Frühe Verträge liegen bereits auf main; Verweise darauf schaffen keine
zusätzlichen Rückwärtsblockaden. [Beziehungsbestand](relationships.json).

## 6. Geänderte Quellen und Wiederveröffentlichung

Die bestehende Datei `asset-studio-github-issues.md` enthält die verbindliche
Ergänzung, keine neue Gesamtarchitektur. Deklarative Matrix, Issue-Patches,
Beziehungen und Prüfnachweis liegen in diesem Unterordner.
README-Einstiege, Planungs-/Studioindex, aktive Architektur-/Inventurhinweise
sowie Pipeline-/Paket-7-/Quellenworkflowpläne verweisen darauf bzw. kennzeichnen
überholte Ausgangsstände. Unter `tools/AssetManager/works/` weisen README und
AGENTS vor allen Originalaufträgen auf die Ergänzung.

Das vollständige hashgeschützte Originalpaket inklusive `tasks.json`,
`START_HIER.md`, Matrix, Architektur und allen `p.md` blieb unverändert:
81 Hashes, keine zusätzliche Datei innerhalb des Pakets.
Kein Integritätscheck wurde abgeschwächt.

Es existiert kein ausführbarer Issue-Publisher im Repository. Ein älterer
externer/flüchtiger Publisher, der nur historische Rohtexte verarbeitet,
ist **nicht sicher verwendbar**. Erst nach Einbindung dieser Ergänzung,
frischem Live-Abgleich und Konflikterhalt darf er publizieren.
Die Dokumentationssperre ist keine technische Garantie gegen unbekannte
externe Skripte; kein Generatorcode wurde verändert.

## 7. Zusatzissues

Keine angelegt. Vorhandene Zuständigkeiten decken alle PA-Anforderungen ab;
für die frühen Verträge und Pythonfreigabe sind keine Doppelaufträge nötig.
Keine bestehenden Issues geschlossen, wieder geöffnet oder gelöscht.

## 8. Erhaltene Arbeiten und Nachweise

- Vorhandener Nutzerstand auf ausdrückliche Bestätigung vollständig und separat
  als `7546735` gesichert/gepusht: 142 Dateien, ältere Game-/Control-/PNG-Arbeit.
  Diese Arbeit wird nicht als eigene neue Implementierung ausgegeben.
- `2286d2f`/ `f8c9991`: echte Pipelineimplementierung und damalige Prüfergebnisse
  bereits auf main; ältere technische Berichte T013–T018 und alle Kommentare
  bleiben erhalten.
- Abfrage aller PR-Zustände vor/nach dem Abgleich: keine PRs. Keine PR-Aktion.
- 41 nicht betroffene Issues einschließlich #60–#76/Szeneneditor unverändert.
- Keine Pipelinefunktion, Anwendungstests, Migration, Godotdatei, Laufzeit-
  konfiguration oder Assets im anschließenden Planungsdiff verändert.
- Kein produktiver Build, keine Implementierungsagenten, kein Reset/Force-Push.

## 9. Ausgeführte Prüfungen

- Originalpaket wiederholt lesend geprüft:
  `.venv/bin/python tools/AssetManager/works/EtherFood_Codex_Aufgabenplan/pruefung/check_plan.py --json`
  → erfolgreich, 48 Aufgaben, 36 Anforderungen, 955 Links, 81 Hashes.
- Deklarative JSON-/R-/T-/PA-Prüfung: vollständige IDs/Originalzuordnungen,
  zwölf eindeutige PA-Verantwortungen; keine entfernte alte Checkbox.
- Native Eltern/Kind-/Blockadekanten und DAG unabhängig abgeglichen; bei allen
  geänderten Issues entsprechen Textvoraussetzungen den nativen Beziehungen.
- Vor jedem API-Schreiben vollständig neu gelesen, nur `body` geschrieben;
  danach einzeln und abschließend alle 76 Issues erneut gelesen.
  35 Nachhertexte exakt bestätigt; keine parallelen Konflikte festgestellt.
  Titel/Zustände/Bearbeiter/Labels/Meilensteine/Kommentare/Beziehungen unverändert.
- Lokale Markdown-Links sowie GitHub-Datei-/Issueverweise gegen Checkout,
  historische Git-Objekte und tatsächlich abgerufene Issues geprüft.
- `git diff --check` und begrenzte Dateityp-/Pfadkontrolle erfolgreich.
  Die finalen Zähler/Bodydigests stehen im [Prüfnachweis](verification.json).

**Nicht ausgeführt:** Anwendungstests, Pipeline-/Qt-/Godot-Tests, produktive
Asset-Builds und `python tools/control.py check`. Historische 581/123/48-Tests
sind keine neuen Testergebnisse dieses Planungsauftrags.

## 10. Grenzen und Abschluss

Keine ungelösten Issue-Textkonflikte oder fehlenden GitHub-Issue-Schreibrechte.
Für zusätzliche GitHub-Projects-Felder fehlt `read:project`; sie wurden nicht
gelesen oder verändert. Keine Behauptung einer dortigen Statussynchronisierung.
Der alte Rohtext-Publisher bleibt wie oben beschrieben unsicher/gesperrt.

**Planung angepasst**: eindeutige Ergänzung, synchronisierte gespeicherte Issues,
erhaltene Originalanforderungen und überprüfte Beziehungen.

**Funktionen noch umzusetzen oder abzunehmen**: insbesondere freie
Masterreferenzen/Maskenverwaltung/-vorschläge, variable Bilddauern/Pflichtframes/
Ereignisse, vollständige Material-Endgarantie, Textur-/Paketverträge,
Opt-in-Importautomatik/Queue-Rest, HTML-/Reviewintegration, Archiv-/Backup-/
Godot-/Gesamtabnahme. Bereits vorhandene Teilfunktionen sind zu verwenden,
nicht neu auszuschreiben. Die neue persönliche Pipeline-Sichtprüfung bleibt
offen. Nach diesem Planungsauftrag beginnt keine Implementierung automatisch.

