# Asset Studio: umfangreiche Markdown-Bearbeitung

[Asset Studio](../asset-studio/index.md) · [Bedienung](../asset-studio/DOKUMENTATION.md)

## Zweck und Gesamtbild

Der Auftrag vom 29. September 2026 erweitert den vorhandenen Python-Editor
um die festgelegte Markdown-Syntax, Navigation, sichere Medien und direkte
Bearbeitung. Ein Markdown-Entwurf und der bestehende Dokumentdienst bleiben
maßgeblich. Gerenderter Inhalt wird niemals zum Speicherformat.

Die automatische Textgenerierung bleibt unverändert, sofern die Syntax keinen
Anpassungsbedarf verursacht. Keine neue Pipeline, Dokumentverwaltung, Datenbank,
Browseroberfläche oder eingebettete Fremdanwendung. Bestehende Issues werden
nicht geschlossen. Vorhandene fremde Arbeitsdateien bleiben unangetastet.

## Ausgangslage und Zuordnung vor der Umsetzung

Die Pfade in dieser Tabelle beziehen sich auf
`tools/AssetManager/src/etherfood_studio/`; Testnamen auf dessen `tests/`.
„Teilweise“ bedeutet ausdrücklich keine Abnahme des gesamten Abschnitts.
Vorhandene Tests sind zunächst gelesene Nachweise; ausgeführte Läufe stehen
gesondert unter Prüfungen. Praktische Prüfungen des neuen Umfangs waren zu
diesem Ausgangszeitpunkt offen; der Abschlussstatus steht weiter unten.

| Anforderung | Vorhandener Bereich / Bestand | Notwendige Ergänzung | Prüfung |
| --- | --- | --- | --- |
| 1 Integration | `ui/documents/`, `application/document_service.py`; teilweise | Gemeinsame Komponenten und Datenregeln erhalten | M25, bestehende Studio-/Pipeline-Suite |
| 2 Ein Quelltext | `live_markdown.py`; vorhanden, Modi-Tests | Gezielte Änderungen auch bei CRLF, Auswahl, Links und Medien | M01, M14, M19 |
| 3 Grundsyntax | Qt und `markdown_source.py`; teilweise | Einheitliche Block-/Inline-Auslegung, Escapes, Referenzen | M01–M04 |
| 4 Code | Gerenderte Blöcke; teilweise | Unverändertes Kopieren, horizontaler Überlauf, SVG-Vorschau | M02, M13 |
| 5 Links | `preview.py`, `editor.py`; teilweise | Linkkontext, Referenzen, vollständige URLs, Titel, sichere Bedienung | M04, M05, M10 |
| 6 Abschnitte/Kurzlinks | Fehlend | NFC-Kennungen, Kollisionen, Navigation, Mehrdeutigkeit | M05–M07 |
| 7 Bildsyntax | Eingeschränkte Projektbilder; teilweise | Referenz-/verlinkte Bilder, lokale Kurzform, alle Container | M08, M10, M15 |
| 8 Bild/GIF-Anzeige | `project_links.py` liest Standbilder; teilweise | Zustände, proportionale Darstellung, echte begrenzte Animation | M08, M09, M24 |
| 9 SVG | Fehlend | Statische sichere Vorschau, Original erhalten, Ressourcenlimits | M13, M14 |
| 10 Pfade | `DocumentService.resolve_link`, BlobStore; teilweise | Logische Basis, Projektgrenzen, Einzelfreigaben, URL-/Symlink-Prüfung | M21 |
| 11 Netzwerk | Automatisch gesperrt; teilweise | Dokumentfreigaben, Richtlinien, abbrechbare Abrufe, Limits | M11, M12, M22 |
| 12 Tabellenanzeige | `markdown_source.py`, `table_widgets.py`; teilweise | Medien/Links, begrenztes `<br>`, sichtbare verlustfreie Fehler | M15, M16, M18 |
| 13 Tabellenbearbeitung | `table_editor.py`; teilweise | Bestätigtes Entfernen, Ausrichtung, Tastatur, TSV | M17, M18, M23 |
| 14 Modi/Formatierung | `live_markdown.py`; teilweise, Modi-Tests | Gemeinsame Auswahl/Undo, Formatierung an Auswahl, Codegrenzen | M19 |
| 15 Einfügen | Vorlagen/Anhänge; teilweise | Link-/Bilddialog, getrennte Ziele, Vorschau, Clipboard/Drop | M20 |
| 16 Darstellung/Leistung | Themes, Blockeditor; teilweise | Generationen, Ressourcenfreigabe, Fokus und zugängliche Aktionen | M22, M24 |
| 17 Speicherung | DocumentService/Projektdateien; vorhanden, Konflikttests | Unverändertes Speichern ohne Revision; alle neuen Aktionen schützen | M03, M17, M23, M25 |
| 18 Nachweise | Quelltext- und echte Qt-Tests; teilweise | Synthetische Fixtures und M01–M25 inklusive Netzwerk/Animation | Neue automatisierte und GUI-Prüfungen |
| 19 Abschluss | Bestehende deutsche Dokumentation; teilweise | Syntax, Bedienung, Grenzen und tatsächliche Prüfergebnisse | Matrix und abschließender Diff |

## Schritte und Fortschritt

- [x] Regeln, bestehende Komponenten, Tests und Arbeitsbaum erfassen.
- [x] Quelltexttreue Syntax, Abschnitte und Linkauflösung erweitern.
- [x] Sichere lokale/externe Medien und SVG mit begrenzten Ressourcen ergänzen.
- [x] Anzeige, Animation und Navigation in bestehende Qt-Flächen integrieren.
- [x] Tabellen, Formatierungen, Einfügen und gemeinsame Bearbeitung ergänzen.
- [x] Synthetische Fixtures, echte Qt-Ereignisse und Netzwerkfälle prüfen.
- [x] Regressionen, Dokumentation und Anforderungsstatus abschließen.
- [x] Eigene Änderungen und verbleibende Grenzen abschließend prüfen.

## Entscheidungen

- Die vorhandenen gebundenen Bibliotheken `markdown-it-py`, PySide6 und Pillow
  sind die erste Wahl. Zusätzliche Abhängigkeiten nur bei konkretem Bedarf.
- Der bestehende Katalog, Dokument-IDs, Revisionen, Anhänge, geschützte
  Automatikabschnitte und Projektdateidienst bleiben bestehen.
- Medienfreigaben und Ansichtsanimation sind lokale Anzeigezustände und ändern
  weder Markdown noch Pipeline-Rezepte oder Freigabestatus.
- Dokumentinhalte werden niemals ausgeführt. SVG wird nur als geprüfte
  Vorschaukopie an den statischen Renderer gegeben.
- Es werden keine neuen Bibliotheken benötigt. Der bereits gebundene Parser
  liefert Blockgrenzen und globale Referenzen; Qt zeichnet die daraus erzeugte
  sichere Ansicht. Pillow prüft Rasterformate, QtSvg die statische Vorschau.
- Tabellenzellen ändern gezielt ihren Quelltextbereich. Nur strukturelle
  Tabellenbefehle schreiben den betroffenen Block neu. Qt-Zeilenendennormalisierung
  wird beim Abgleich auf die tatsächlich geänderte Stelle begrenzt.
- GIFs verwenden Qt ohne vollständigen Frame-Cache. Vor dem Dekodieren werden
  Framegrenzen geprüft und ein gemeinsames Speicherbudget reserviert.

## Prüfungen

Am 29. September 2026 ausgeführt:

- `.venv/bin/python -m pytest -q tools/AssetManager/tests/test_markdown_source.py`:
  **7 bestanden** (Ausgangsstand).
- Vollständige Studio-Suite während der Umsetzung: **763 bestanden**.
- Danach erweiterter gezielter Markdown-Lauf: **115 bestanden**.
- Weitere GUI-Prüfungen zu Einfügen, Speicherbudget und Freigaben: zunächst
  **50 bestanden, 1 fehlgeschlagen**. Der Fehler betrifft die Lebensdauer eines
  Tabellen-Untermenüs. Durch explizite Qt-Elternschaft behoben; gezielte
  Wiederholungsprüfung bestanden.
- Nach weiteren Ergänzungen: **76 echte Qt-Tests bestanden**, einschließlich
  Dialogfokus, CRLF/Strg-Klick, endlicher GIF-Wiederholung, Hell/Dunkel,
  externer Dateiverknüpfung, Zwischenablage/Drop und vier begrenzten Abrufen.
- Abschließender Kern-/Netzwerklauf: **49 bestanden**, einschließlich eines
  zusätzlichen Randfalls mit maskiertem letztem Tabellenstrich ohne Außenrahmen.
- Abschließender vollständiger Studio-Lauf
  `.venv/bin/python -m pytest -x -q tools/AssetManager/tests`:
  **817 bestanden in 588,84 Sekunden**. Danach wurden der zusätzliche
  Tabellen-Randfall und die tatsächlichen gerenderten GIF-Pixel separat geprüft.
- Abschließender gezielter Qt-Lauf vor der Pixel-Ergänzung: **87 bestanden**.
- Letzter kombinierter Lauf der Markdown-Kern-/Netzwerkprüfungen und der vier
  zugehörigen Qt-Testmodule: **136 bestanden in 29,17 Sekunden**. Enthalten sind
  die abschließende Tabellenkorrektur und der Vergleich der tatsächlich
  gerenderten GIF-Bildflächen einschließlich eingefrorener Anzeige bei Pause.
- Zusätzlich echte Klick-/Speicher-/Kopierprüfungen: **3 bestanden** für das
  verlinkte Bild, Checkbox mit Undo und Wiederöffnen sowie unverändertes
  Codekopieren mit eigenem horizontalem Überlauf.
- `.venv/bin/python -m pytest -q tools/AssetManager/PyGameTools/.tests
  tools/AssetManager/PyGameTools/Pipline/2-SpritesheetResolution-Pipline/tests`:
  **171 bestanden**.
- `.venv/bin/python -m pip check`: **keine inkonsistenten Abhängigkeiten**.
- `git diff --check`: **bestanden**.
- Stilprüfung der eigenen geänderten Python-Dateien: **0 Befunde**.
  Gesamter Bestand: **1.905 Befunde**, identisch zu den mit denselben Regeln
  aus `HEAD` gelesenen Dateien.
- `python3 tools/control.py check`: **283 bestanden, 37 übersprungen,
  4 fehlgeschlagen** in `tools/tests`; Doctor/Godot-Import scheitern an fehlendem
  Godot 4, der Stil-Gate am vorhandenen Bestand. Die vier Testfehler betreffen
  fehlende vorbereitete Testassetordner, `window/size/resizable=true`, zwei fehlende
  Game-Entscheidungsseiten und daraus folgende 13 Dokumentationslinks. Abgleich
  mit `HEAD` bestätigt alle vier Ursachen bereits im Ausgangsstand; die Änderungen
  ergänzen keine fehlenden Dokumentationsziele. Diese fachfremden Bereiche bleiben
  unverändert.
- Abschließender Arbeitsbaumabgleich: **20 eigene Python-Dateien ohne Stilbefund**,
  alle 25 Fixtures mit Quelltext und Erwartung, keine neuen fehlenden relativen
  Dokumentationslinks. Automatische Dokumentgenerierung, Pipeline-/Canvas-Code
  und vorhandene fremde Arbeitsdateien sind unverändert. Keine Issues geschlossen
  und keine zusätzlichen Abhängigkeiten eingeführt.

Der abschließende vollständige Studio-Lauf besteht nach den GUI-Korrekturen.
Qt läuft dabei mit `QT_QPA_PLATFORM=offscreen` und den
Systembibliotheken der Testumgebung. TLS-Negativtests erzeugen mit der vorhandenen
OpenSSL-CLI ein temporäres selbstsigniertes Zertifikat. Ohne diese CLI wird
ausschließlich dieser TLS-Fixturetest ausdrücklich übersprungen.
Screenshots allein gelten nicht als Nachweis für Animation, Undo oder Speicherintegrität.

## Erkenntnisse und Überraschungen

Die vorhandene Dokumentationsseite beschreibt noch pauschal gesperrte lokale
Bilder. Der aktuelle Code lädt bereits ausgewählte verifizierte Projektbilder,
allerdings als Standbild; Tabellenzellen haben noch keinen Medienpfad.
Quelltextbearbeitung verwendet Qt-Textfelder, deren Normalisierung bei CRLF
gezielte Verlustfreiheit verlangt.

Die Qt-Laufzeit benötigte zusätzliche Systembibliotheken der Testumgebung.
Diese wurden außerhalb des Repositories bereitgestellt; Paketbindungen des
Projekts bleiben unverändert. Die GUI-Tests verwenden echte Qt-Ereignisse mit
dem Offscreen-Plattformtreiber. Ein gefundenes Problem bei leeren Qt-Textblöcken
ist durch Prüfung des Fragment-Iterators vor dem Zugriff behoben.

Die Hell-/Dunkel-Sichtprüfung mit einem synthetischen Dokument zeigte zunächst
unverändert dunkle Qt-Linkfarben nach dem Themewechsel. Links und transparente
Bildhintergründe folgen jetzt der bestehenden Palette, ohne Neuaufbau des Entwurfs.
Ein gesamter Studio-Testlauf deckte außerdem eine veraltete Testattrappe der
Vorschaumethode auf; sie akzeptiert nun den zusätzlichen Referenzkontext. Ein
gezielter Dialogabbruch-Test führte zur Korrektur der Fokuswiederherstellung,
auch wenn ein anderes Fenster zuvor aktiv war.

Der wiederholte Gesamtlauf fand einen tatsächlichen GIF-Lebenszyklusfehler:
Qt 6.10 meldet beim normalen Dateiende eines vollständig abgespielten GIF-Zyklus
`UnknownError` und setzt danach selbst die Wiederholung fort. Erst andere
GUI-Module registrierten den dazugehörigen Enum-Typ, weshalb ein isolierter
Lauf diesen Callback zuvor nicht zuverlässig erreichte. Der Renderer importiert
den Enum-Typ jetzt ausdrücklich und behandelt nur diesen nachgewiesenen
Dateiende-Fall nach dem letzten tatsächlich angezeigten, zuvor strukturell
geprüften Frame als Wiederholungsgrenze. Echte Decoderfehler bleiben sichtbar.
Das Schließen des Eingabepuffers erfolgt bei Fehlern erst außerhalb des laufenden
Decoder-Callbacks. Die zwei Framefarben sowie endliche und endlose Wiederholung
wurden danach erneut in **63 Qt-Tests erfolgreich geprüft**.

Alternativtexte und Sprachangaben werden in Qt-Labels ausdrücklich als Klartext
gesetzt. Inhalte in Tabellen-Bestätigungen werden maskiert. Qt darf solche
Dokumentdaten nicht durch seine automatische HTML-Erkennung als Ressourcen laden.

## Wiederholbarkeit und Wiederherstellung

Alle Tests verwenden synthetische temporäre Projekte und kontrollierte lokale
Server. Keine fremden Bildserver, Benutzerprojekte oder Arbeitsdateien werden
für Tests verändert. Bearbeitungen bleiben über den gemeinsamen Undo-Verlauf
rückgängig; Revisionskonflikte erhalten den lokalen Entwurf. Vorschauen erzeugen
keine dauerhaften Anhänge und kein zweites Speicherformat.

## Ergebnis und Rückblick

Die Erweiterung ist im vorhandenen Editor umgesetzt. Der gemeinsame Quelltext,
die Dokumentverwaltung und die automatische Textgenerierung bleiben erhalten.
Die ursprünglichen Lücken bei Medien, direkter Bearbeitung und sicherem Zugriff
sind durch die nachfolgend zugeordneten Tests geprüft. Der allgemeine
Repository-Gate bleibt wegen der bestätigten Altbefunde und fehlendem Godot
nicht grün. Native Desktop-Übergaben und Bildschirmleser sind unten ausdrücklich
von den bestandenen Qt-Prüfungen abgegrenzt. Der letzte gezielte Abschlusslauf
und die Arbeitsbaumprüfung sind bestanden. Nicht geprüfte native Übergaben werden
nicht als praktisch abgenommen ausgegeben.

## Abnahmematrix M01–M25

Die Fixtures enthalten jeweils Quelltext und Soll-Ergebnis. Die Zuordnung benennt
zusätzlich die tatsächlich notwendigen Verhaltensprüfungen; bloßes Rendern des
Fixturetexts gilt nicht als deren Ersatz.

| Fälle | Nachweis |
| --- | --- |
| M01–M02 | Gemeinsamer Parser, echte Qt-Darstellung, exakte Ansichtswechsel, Codekopieren und horizontaler Überlauf |
| M03 | Echter Checkboxklick, Undo/Redo, Speichern/Wiederöffnen, gesperrte Checkbox |
| M04 | Entfernte und doppelte globale Referenzen, Darstellung in getrennten Blöcken |
| M05–M07 | Echter Linkklick, interne Navigation, fehlende Abschnitte, reproduzierbare Slugs, Auswahl bei Mehrdeutigkeit, Strg-Klick/Drag in Code |
| M08 | Dekodierte lokale PNG/JPEG/WebP/SVG, Größenanpassung, fehlende Quellen |
| M09 | Zwei verschiedenfarbige GIF-Frames, Pixelvergleich der tatsächlich gerenderten Qt-Fläche, individuelle Verzögerungen, Pause/Fortsetzen und endliche Wiederholung |
| M10 | Bildquelle laden ohne Navigation, separater tatsächlicher Klick auf verlinktes Bild, gezielt verknüpfte externe Datei |
| M11–M12 | Kontrollierte lokale HTTP-/TLS-Server: keine Anfrage ohne Freigabe, begrenzte private Freigabe, Weiterleitungen, Protokolle, Abbruch, Inaktivität, Gesamtfrist einschließlich DNS/Antwortkopf, Größen- und Parallelitätsgrenzen |
| M13–M14 | SVG-Datei und Codeblock in Qt; Skripte, Fremdressourcen, Entitäten, Zyklen und unbekannte Elemente abgelehnt; Original und Markdown unverändert |
| M15–M16 | Zellen mit Inline-Code, Links, Bildern, Ausrichtungen und maskierten Strichen; überlange Zeile vollständig als Fehleransicht |
| M17–M18 | Echte Zelleingabe/F2, Escape, Tab, Shift+Enter, Zeilen/Spalten/Ausrichtung, TSV-Bestätigung und Undo; unveränderte Textwerte nach Speichern |
| M19 | MD/Code-Wechsel, CRLF/BOM/Unicode, Auswahl, gemeinsamer Entwurf und Undo/Redo, mehrzeilige Formatierung |
| M20 | Abgebrochener modaler Dialog mit Fokus/Auswahl, keine Anhänge, temporäres Clipboardbild gelöscht; bestätigter Import über bestehenden Dienst; URL als Text und Bild-Drop |
| M21 | Leerzeichen/Umlaute, einmalige Dekodierung, Projektwurzel, Traversal-/Symlink-Sperre und Hashprüfung geänderter externer Datei |
| M22 | Verspätete Arbeit eines früheren Dokuments verworfen; Bildnachladen erhält Fokus und Auswahl |
| M23 | Revisionskonflikt erhält Entwurf; Tabellen-/Checkbox- und Dialog-Schreibschutz |
| M24 | Wiederholtes Öffnen/Schließen, freigegebener Medienspeicher, begrenztes Dekodierbudget und responsive Qt-Ereignisse |
| M25 | Bestehende Studio-, Asset-, Canvas- und Pipeline-Tests; unveränderter Katalog-Snapshot beim Ansichtswechsel |

Testquellen: [Kern und Pfade](../../../../tools/AssetManager/tests/test_markdown_contract.py),
[Netzwerk](../../../../tools/AssetManager/tests/test_markdown_network.py),
[Qt-Verhalten](../../../../tools/AssetManager/tests/gui/test_markdown_contract_ui.py),
[Fixtures](../../../../tools/AssetManager/tests/fixtures/markdown/README.md).

## Status je Anforderungsabschnitt

Diese Einordnung gilt für die implementierte Python-/Qt-Funktion. Die Abnahme
benennt Desktop-Grenzen ausdrücklich; sie ersetzt keine Freigabe einer neuen
Zielplattform. Die tatsächlichen Zahlen des Gesamtlaufs stehen oben.

| Abschnitt | Status und praktische Grenze |
| --- | --- |
| 1 Bestand und Integration | Erfüllt und geprüft: bestehender Editor/Dokumentdienst erweitert; keine Änderungen an Generator, Pipeline-Steuerung oder Projektstruktur. Studio- und Pipeline-Gesamtläufe bestanden. |
| 2 Ein Quelltext | Erfüllt und geprüft: gemeinsame Quelle, gezielte Änderungen, reine Ansicht ohne Revision, CRLF/BOM/Referenzen erhalten. |
| 3 Grundsyntax | Erfüllt und geprüft: Kontextparser und Qt-Darstellung, Checkboxklick mit Undo und Schreibschutz. |
| 4 Codeblöcke | Erfüllt und geprüft: beide Einzäunungen, Einrückung, unverändertes Kopieren, eigener Überlauf; Sprachangaben führen nichts aus. |
| 5 Hyperlinks | Internes Verhalten erfüllt und geprüft. Native Browser-/Mailprogramm-Übergabe umgesetzt, aber noch nicht praktisch auf Desktop-Betriebssystemen geprüft. Bestätigung und Protokollprüfung sind vorhanden. |
| 6 Abschnittsziele/Kurzlinks | Erfüllt und geprüft: NFC-Kollisionen, Auswahl statt zufälligem Treffer, interne Navigation und kurz hervorgehobenes Ziel. |
| 7 Bildsyntax | Erfüllt und geprüft: normale, referenzierte, verlinkte Bilder und definierte lokale Kurzform; getrennte Bildquelle und Navigation. |
| 8 Bilder/GIF | Erfüllt und geprüft: echte Frames, Framezeiten/Wiederholung, Pause, Bewegungseinstellung, Zustände und Ressourcenfreigabe. |
| 9 SVG | Erfüllt und geprüft innerhalb des statischen Mindestumfangs und der dokumentierten Grenzen; Datei/Code unverändert, aktive/externe Inhalte abgelehnt. |
| 10 Pfade | Erfüllt und geprüft: logische Basis, Projektgrenzen, einmalige Dekodierung, Symlink-Sperre, begrenzte Einzelfreigabe und Anhangsintegrität. |
| 11 Netzwerk | Erfüllt und geprüft: ausdrückliche Freigaben, Richtlinien, lokale Server/TLS, Weiterleitungsprüfung, Abbruch, Zeit-/Größen-/Parallelitäts-/Speichergrenzen. |
| 12 Tabellenanzeige | Erfüllt und geprüft: Ausrichtung, Inline-Inhalte, Bilder, maskierte Striche und verlustfreie Fehleransicht. |
| 13 Tabellenbearbeitung | Erfüllt und geprüft: Zelle/Struktur/Ausrichtung, Tastatur, bestätigtes Entfernen/TSV, Undo und geschützte Dokumente. |
| 14 Modi/Bedienung | Erfüllt und geprüft: gemeinsamer Entwurf und Verlauf, Auswahl soweit abbildbar, Formatierung und stabile aktive Eingabe. |
| 15 Einfügen/Clipboard | Erfüllt und geprüft: gemeinsame Dialoge, Import erst nach OK, temporäre Vorschau aufgeräumt, getrennte Ziele, Textpaste und Bild-Drop. |
| 16 Darstellung/Zugänglichkeit/Leistung | Qt-Funktion erfüllt und geprüft: Hell/Dunkel-Sichtprüfung, Fokus/Selektion, Tastatur, benannte Aktionen, Generationen und begrenzte Ressourcen. Bildschirmleser und native Skalierung auf weiteren Desktops umgesetzt, aber noch nicht praktisch geprüft. |
| 17 Speicherung/Konflikte | Erfüllt und geprüft: vorhandener Dienst, Revisionen, unverändertes Speichern, Konflikte und Schreibschutz auch bei direkter Bearbeitung. |
| 18 Prüffälle | Erfüllt und geprüft: synthetische M01–M25-Fixtures, echte Qt-/Netzwerktests sowie Studio- und Pipeline-Gesamtläufe bestanden. |
| 19 Dokumentation/Abschluss | Erfüllt und geprüft: Syntax, Bedienung, Zugriff, Grenzen und tatsächliche Ergebnisse dokumentiert; Altbefunde und offene native Desktop-Prüfungen ausgewiesen. |

Keine geforderte Funktion wird allein durch einen Screenshot oder eine
Quelltext-Ersatzansicht als vollständig abgenommen. Die gekennzeichnete
Quelltextansicht für übergroße/uneindeutige Inhalte ist der vereinbarte
verlustfreie Rückfall. Die oben genannten nativen Desktop-Prüfungen bleiben
offen; in dieser Docker-Sitzung wurde kein Browser oder Mailprogramm gestartet.
