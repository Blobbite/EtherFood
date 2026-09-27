# Zwischenpaket 6a – Quellenbedienung und Aufgaben am Asset

## Auftrag und Ausgangslage

27.09.2026, nach Paket 6 (`e4166c8`). Benutzer bestätigt Quellenbutton und
Import mit 1×16 sowie 4×4. Die restlichen Paket-6-Prüfpunkte sind damit nicht
automatisch abgenommen. Der Bericht fordert erkennbare Raster, kompakte
Lieferbündel, aufklappbare Posen/Revisionen, gezieltes Ersetzen und nur einen
zentralen Einstieg über das Asset-Menü. Aufgaben/Issues sind im Dashboard
vorhanden (T007/T012/4a), fehlen aber am Asset; anklickbare To-do-Listen fehlen.

## Umfang und Nicht-Ziele

- Rastervorschlag aus eindeutigen Dateinamensangaben, sonst konservativer
  Transparenzanalyse. Unklare Bilder verlangen manuelle Auswahl; keine
  Ableitung nur aus dem Seitenverhältnis. Raster/Frames bleiben vor dem
  bestätigten Import sichtbar und überschreibbar.
- Auswahl/Prüfung zeigt gespeicherte Quellen als kompakte Posenbündel.
  Lieferstand/Revisionen enthält aufklappbare Pose → Richtung → Revision,
  Rasterspalte und Ersetzen einzelner Richtungen oder einer vollständigen Pose.
- Aktive/alte Quellen bleiben erhalten. Ganze Posen werden nur vollständig
  und atomar ersetzt, keine unbeabsichtigte Änderung anderer Posen/Richtungen.
- Anforderungen, Quellen und lesende Bestandserfassung nur im Asset-Menü;
  doppelte Toolbar-/Kontextaktionen entfernen, Dienste weiterverwenden.
- Dokumentation am Asset erhält bestehende Aufgaben-/Issue-Bedienung plus
  echte To-do-Punkte mit Revisionsschutz. Kein separates Aufgabenmodell.
- Notizdatenbank/Icon-Umbau ist vom Benutzer noch nicht entschieden und bleibt
  ausdrücklich Vorschlag. Kein T017/T018, keine Bild-/Godot-Pipeline.

## Schritte und Fortschritt

- [x] Bericht, tatsächliche UI, vorhandene Dienste und Issue-Stand abgleichen.
- [x] Rastervorschläge und kompakte Quellen-/Revisionsansicht implementieren.
- [x] Begrenzte Einzel-/Posenaktionen und zentralen Einstieg absichern.
- [x] Quellen-Tests/Dokumentation und englischen Emoji-Commit/Push vorbereiten.
- [x] Aufgaben/Issues am Asset und gespeicherte To-do-Listen ergänzen.
- [x] Dienste, echte Qt-Bedienung und Regressionen testen.
- [x] Dokumentation und zweiten englischen Emoji-Commit/Push vorbereiten.
- [x] Kurzes Nachbriefing mit tatsächlich offenen Punkten dokumentieren.

## Entscheidungen und Schutz

Quellen bleiben unveränderliche Revisionen im bestehenden Blobstore. Neue UI
schreibt über die vorhandenen Dienste. Rastererkennung erzeugt weder Dateien
noch Freigaben. Keine neuen Abhängigkeiten. Aufgabenänderungen wahren die
bestehende explizite Aufgabenabnahme und ersetzen keine Asset-Freigabe.
Der importierte Aufgabenplan bleibt historische Grundlage. Bestehende lokale
Control-/Doku-/Spiel-/Grafikänderungen werden nicht angefasst oder mitcommitted.

## Prüfstrategie

Zuerst synthetische PNGs (1×16/16×1/4×4, mehrdeutiges Raster, Dateinamenskonflikt),
Quellenhistorie und atomare Posenaktionen. Dann echte Qt-Events für erneutes
Öffnen, Bündel, Aus-/Einklappen, Rasterspalte, Einzel-/Posenersatz und bereinigte
Menüs. Aufgabenanlage/Checklisten/Filter am selben Asset, Revisionskonflikt,
Abbruch und Wiederöffnung. Abschließend Studio-/Pipeline-Prüfung, passende
Stilprüfung und Repository-Standardcheck; nur ausgeführte Ergebnisse melden.

## Wiederherstellung und Ergebnis

Originale/alte Quellen bleiben erhalten; Abbruch oder unvollständige Auswahl
ändert keine aktiven Zuordnungen. Bestehende Aufgaben ohne To-do-Liste bleiben
lesbar. Nur eigene Dateien gezielt committen. Ergebnisse werden während der
Umsetzung ergänzt; die persönliche Nachprüfung bleibt bis zum Briefing offen.

Quellenteil: Dateinamen werden sofort als Vorschlag eingetragen; ansonsten
prüft der Hintergrundprozess regelmäßige Transparenzabstände. Bei Unsicherheit
gibt es keine stumme 16×1-Vorgabe. Raster/Frames sind anschließend sichtbar.
Ganze Posen benötigen alle aktuellen Richtungen; alte vollständige Bündel können
atomar reaktiviert werden. Einzelne Richtungen ändern keine Nachbarn.
Auswahl/Prüfung zeigt nur neue Dateien plus gespeicherte Posenbündel. Die
globale Revisions-Auswahlliste und der redundante Versionen-Reiter entfallen.

Quellen-Nachweise: 40 gezielte Tests bestanden, danach **174 Studio-Tests
bestanden**. **71 Studio-Quell-/Testdateien ohne Stilbefund** und
`git diff --check` sauber. Echte Qt-Screenshots für Posenbaum und gespeicherte
Bündel geprüft. Frühere Testläufe mit zu knapper Qt-Worker-Wartezeit abgebrochen;
die Testschleife gibt nun den Python-Worker ausdrücklich frei. Danach vollständiger
Lauf erfolgreich. Keine originale Spielgrafik verändert.

Quellenabschnitt als `82dd3d9` separat committed und gepusht. Aufgaben/Issues
nutzen nun denselben `TasksPanel`/`IssueService` im Asset-Menü und Hauptfenster.
Die Asset-Ansicht ist fest auf dieses Asset begrenzt. To-dos sind revisionierte
optionale Daten derselben Aufgaben, keine zweite Datenbank; alte Aufgaben bleiben
lesbar. Änderungen an abgenommenen Inhalten heben deren Aufgabenabnahme auf.
Offene Punkte verhindern Erledigt; alle Häkchen ersetzen weder den bewussten
Statuswechsel noch eine nötige Abnahme. Ungespeicherte Notizen bleiben beim
Aufgaben-Refresh erhalten. 35 bestehende Dienst-/GUI-Tests und 16 neue gezielte
To-do-/Asset-Aufgabentests bestanden; Gesamtprüfung folgt.

Abschlussprüfungen: `python3 tools/control.py asset-manager check` erfolgreich,
**190 Studio-Tests und 171 Pipeline-Tests bestanden**. **75 Studio-Dateien ohne
Stilbefund**, echte Quellen-/Bündel-/Aufgabenansichten per Qt-Screenshot geprüft.
`python3 tools/control.py check` zweimal tatsächlich ausgeführt; abschließend
259 Tests bestanden, 37 übersprungen, zwei bekannte Doku-Prüfungen fehlgeschlagen.
Weiterhin fehlen Godot 4 und Dokumentationsziele (13 bestehende defekte Links);
die abschließende Stilprüfung meldet 1907 geerbte Befunde in 241 Dateien, aber
keinen im Studio. `git diff --check` sauber. Keine ursprünglichen Spielbilder
oder fremden Änderungen verändert; keine zusätzliche Abhängigkeit.

[Ergebnisbericht](../asset-studio/task-results/6a.md) und
[sieben kurze Nachprüfpunkte](../asset-studio/SICHTPRUEFUNG_6A.md) vorbereitet.
Notizdarstellung und persönliche Nachabnahme bleiben offen; T017/T018 nicht
begonnen. Commit-/Push-Nachweise der beiden Arbeitsabschnitte stehen im
Git-Verlauf und den zugehörigen Issue-Kommentaren; keine pauschale Benutzerabnahme.

Aufgabenabschnitt als `0923553` committed und gepusht. Abschließende
Quellen-Regression ergänzt: Nach Verkleinern des Richtungssets bleibt bei einer
bereits importierten, nun optionalen Richtung sowohl **Nicht erforderlich** als
auch ihr tatsächlicher Lieferstand sichtbar. Keine Änderung ihrer Revision.
Erneuter vollständiger Studio-Lauf danach: **190 bestanden**, Stilprüfung
weiterhin **75 Dateien ohne Befund**.

Nachtrag 27.09.2026: Der Benutzer bestätigt alle sieben persönlichen Nachtests
von 6a. Die darin nicht geprüften älteren Kriterien bleiben separat offen.
Neuer Auftrag: [Zwischenpaket 6b – Kanban und getrennte Suche](asset-studio-kanban.md).
