# Asset Studio: Darstellung, Eingaben und Markdown-Werkzeuge

[Asset Studio](../asset-studio/index.md)

## Zweck und Ausgangslage

Nach dem MD/Code- und Pinnwand-Paket werden die gemeinsam genutzten
Oberflächen verbessert. Leere Aufgabenlisten erklären derzeit nur, dass
To-dos fehlen. Farben sind teils fest verdrahtet. Seitliches Mausrad-Kippen
wird beim Canvas-Verschieben als Scrollen verarbeitet. Markdown-Tabellen
werden noch als gesamter Textblock bearbeitet; Checkboxen sind nicht interaktiv.

## Umfang und Entscheidungen

- Leere To-do-Bereiche von Aufgaben und Issues öffnen über einen Button den
  vorhandenen, revisionsgeschützten Aufgabeneditor direkt bei den To-dos.
- Einstellungen oben rechts: Hell/Dunkel sowie Text + Icons / nur Icons /
  nur Text für Aktionsschaltflächen. Lokale Einstellungen bleiben nach Neustart
  erhalten. Inhalte, Statusbeschriftungen und Feldnamen bleiben lesbar.
- Gemeinsame Qt-Palette und angepasste Canvas-/Post-it-/Kanban-Farben; auch
  bereits offene Ansichten und Dialoge reagieren ohne Verlust von Entwürfen.
- Canvas-Pan ausschließlich mit gehaltener mittlerer Maustaste; währenddessen
  keine Rad-/Kipp-/Seitentasten-Sprünge. Vertikales Scrollen und Strg+Rad-Zoom
  außerhalb dieser Geste bleiben verfügbar.
- Tabellen im MD-Modus: Zellen bearbeiten, Spalten/Zeilen über Kopf-/Randleisten
  auswählen und umordnen, hinzufügen und entfernen. Markdown bleibt die Quelle;
  außerhalb der bearbeiteten Tabelle bleibt der Originaltext erhalten. Kein HTML-
  Roundtrip und keine zusätzliche Abhängigkeit.
- Markdown-To-dos direkt anklicken; Listenstruktur, Codeblöcke und unberührte
  Zeichen bleiben erhalten. Generierte Berichte bleiben schreibgeschützt.
- Überschriftbearbeitung ohne künstliche zusätzliche Leerzeilenhöhe.
- Vier Ansichtsbuttons: links / mittig / rechts / volle Breite. Vorläufige
  Annahme: Ausrichtung der Dokumentationsfläche, nicht Markdown-Erweiterungen
  zur Absatzformatierung; dazu ist eine nicht blockierende Rückfrage gestellt.

Keine neue Bildpipeline, keine Freigaben oder Änderungen am Spielkanon,
keine fremden Arbeitsbaumänderungen im Commit.

## Schritte und Fortschritt

- [x] Gemeinsame Komponenten, Datenflüsse und vorhandene Prüfungen untersucht.
- [x] To-do-Einstieg und Canvas-Eingabefilter implementieren.
- [x] Zentrale Darstellungseinstellungen und konsistente Themes ergänzen.
- [x] Quelltexttreuen Tabelleneditor implementieren.
- [x] Anklickbare Markdown-Checklisten und Überschriftenhöhe korrigieren.
- [x] Vier Ausrichtungsbuttons und gemeinsame Asset-Ansicht integrieren.
- [x] Ereignis-/Speicher-/Regressionsprüfungen und Bedienbriefing ergänzen.
- [x] Eigene Änderungen für englischen Emoji-Commit und Push prüfen.

## Prüfungen

Zuerst fokussierte Dienst-/Qt-Tests, danach vollständige Studio-Suite,
Studio-Stilprüfung und `git diff --check`. Szenarien umfassen persistierte
Einstellungen, Kontrast, schreibgeschützte Dokumente, Sonderzeichen in Tabellen,
Listen in Codeblöcken, Undo/Redo und echte kombinierte Maus-/Radereignisse.
Der bekannte Repository-Gesamtcheck ist separat zu bewerten (fehlendes Godot,
bestehende Stil- und Dokumentationsbefunde). Nur ausgeführte Ergebnisse berichten.

## Wiederherstellung und Risiken

Alle Inhaltsänderungen verwenden den vorhandenen Entwurf und seine Revisions-
prüfung. Ansichtswechsel schreiben keine Dokumentrevision. Tabellenoperationen
sind rückgängig machbar; nicht sicher interpretierbare Syntax bleibt über Code
bearbeitbar. Tests verwenden ausschließlich temporäre synthetische Projekte.
Darstellungseinstellungen ändern keine Projekt- oder Asset-Daten.

## Erkenntnisse und Ergebnis

Bestehende fokussierte Qt-Läufe nach den ersten Änderungen: 18 Tests für Kanban
und Canvas, 29 für Live-Inhalte/Pinnwand/Kanban und 16 für Live-Markdown/MD-Code
bestanden. Neue gezielte Regressionstests für dieses Paket sind ergänzt.

Gezielte neue Prüfungen laufen ebenfalls erfolgreich: Quellpositionen einschließlich
CRLF/Emoji, native Zelleingaben, Kopf-/Rand-Plus, Zeilen-/Spaltenwechsel, Undo/Redo,
Checkboxen und Codeblöcke, schreibgeschützte Tabellen, Überschriftenhöhe, Ausrichtung,
persistierte Darstellung, Entwurfserhalt sowie kombinierte Mittel-/Seiten-/Radtasten.
Die vollständige Studio-Suite und die Sichtkontrolle sind gestartet.

Die Sichtkontrolle fand zwischengespeicherte helle Qt-Stylesheet-Paletten im
Kanban. Diese werden vor dem erneuten Anwenden semantischer Farben aktualisiert;
ein eigener Test prüft jetzt die tatsächlichen Viewport-/Textpaletten. Auch die
Bereichsreiter folgen der Icon-/Text-Einstellung. Der To-do-Fokus wird beim
Öffnen gesetzt und nach Fensteraktivierung bestätigt. Ein vorhandener
Prozesstest wartet nun explizit auf seine drei Timerereignisse, statt diese
aus der zeitlich unabhängigen Meldung „child-ready“ abzuleiten.

Vollständiger Abschlusslauf: **401 Studio-Tests bestanden**. Zusätzlich wurde
der Fokuswechsel Überschrift → Tabellenzelle abgesichert: der neu
fokussierte Zelleneditor bleibt beim Rendern der Überschrift erhalten; bloße
Modifikatortasten lenken den Fokus nicht in den ersten Textblock um.
Das Hauptfenster erkennt den Dokumentfokus auch in Tabellen/Checkboxen und
wendet Undo dort nicht versehentlich auf den Canvas an.

Studio-Stilprüfung: 130 Dateien ohne Befund; `pip check` und `git diff --check`
bestanden. Screenshots aus einem synthetischen Projekt: Hell-/Dunkel-Markdown,
beide Notizthemen, dunkles Kanban/Canvas und Nur-Icon-Navigation kontrolliert.
Repository-Standardlauf erneut ausgeführt: Godot fehlt; bestehende Stilbefunde
außerhalb des Studio; Toolsuite 258 bestanden, 37 übersprungen, drei bestehende
Fehler (Godot-Fenstervertrag, zwei fehlende Game-Entscheidungsdokumente und
zugehörige Dokumentationslinks). Fremde Arbeiten bleiben unangetastet.

Abschlussumfang: nur die zugehörigen Studio-UI-Dateien, Tests und die passende
deutsche Dokumentation. Keine PNGs, Importdaten, Control- oder Game-Änderungen.
Das [aktuelle Bedienbriefing](../asset-studio/DARSTELLUNG.md) benennt acht kurze
Benutzerprüfungen und überspringbare ältere Tests.

Die Tabellenbearbeitung erhält rohe Zellinhalte und Ausrichtungstrenner; nicht
eindeutig interpretierbare oder sehr große Tabellen bleiben im Quelltextmodus
bearbeitbar. Checkboxen erhalten Quellpositionen nur aus echten Listeneinträgen;
Codeblöcke werden nicht zu interaktiven Aufgaben umgedeutet.

Die persönliche Abnahme und T017/T018 bleiben von diesem technischen Zwischenpaket
getrennt.
