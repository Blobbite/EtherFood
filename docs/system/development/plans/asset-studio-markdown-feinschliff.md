# Asset Studio: kompakte Symbole und ruhige Markdown-Bedienung

[Asset Studio](../asset-studio/index.md)

## Zweck und Ausgangslage

Das Feedback zu `b78a7fb` verlangt kleinere Nur-Icon-Schalter, sichere Kontraste
und eine weniger technische Tabellenansicht. Die bisherigen festen 150-Pixel-
Spalten sowie die 820-Pixel-Lesefläche passen nicht zum gewünschten Editor.

## Entscheidungen und Umfang

- Kleinere Aktionssymbole und kompakte Nur-Icon-Schalter. Monochrome Aktionen
  erhalten dunkle Konturen im Hellmodus und helle im Dunkelmodus; semantische
  Typ-/Statusfarben bleiben erkennbar. Keine neuen Bilddateien/Abhängigkeiten.
- Keine sichtbaren Zeilen-/Spaltennummern und keine permanente Tabellen-
  Aktionsleiste. Griffe/Pluszeichen erscheinen bei Hover oder Tastaturfokus,
  ohne dass die Tabelle dadurch springt. Ganze Zeilen/Spalten weiterhin über
  Randgriffe auswählen/ziehen; Entfernen über Entf/Rücktaste oder Rechtsklick.
- Tabelle nutzt die verfügbare Breite. Zelltext wird umgebrochen und die
  Zeilenhöhe angepasst; viele Spalten bleiben horizontal scrollbar.
- Die neue ausdrückliche Vorgabe ersetzt die frühere Breitenentscheidung:
  Dokumentation immer voll breit, kein eigener Vollbreite-Schalter mehr.
  Links/Mittig/Rechts richtet gerenderte Inhalte innerhalb dieser Fläche aus.
  Markdown-Quelle, Code-Modus und eigene Tabellenspaltenausrichtung bleiben
  unverändert. Alte Einstellung `full` entspricht künftig links.
- Gemeinsamer Editor im Asset-Menü, Entwurfs-/Revisionsschutz und Undo bleiben
  erhalten. Keine Änderungen an fremden Game-/Control-/Asset-Arbeiten.

## Schritte

- [x] Bestehende Komponenten, Anforderungen und Arbeitsbaum geprüft.
- [x] Kompakte Buttons und themeabhängige Icons umsetzen.
- [x] Dezente Tabellensteuerung und flexible Zellgrößen umsetzen.
- [x] Vollbreite mit drei Inhaltsausrichtungen integrieren.
- [x] Qt-/Regressionsprüfungen, Sichtkontrolle und aktuelles Briefing ergänzen.
- [ ] Eigene Änderungen prüfen, englischen Emoji-Commit erstellen und pushen.

## Prüfungen und Wiederherstellung

Zuerst gezielte echte Qt-Ereignisse für Modi/Größen, Icon-Kontrast, Hover ohne
Positionssprünge, Auswahl/Entf, Zellumbruch, Undo und breite Dokumentflächen.
Danach vollständige Studio-Suite, Studio-Stilprüfung, `pip check` und
`git diff --check`. Standardlauf separat ausweisen; bekannte Godot-/Altbefunde
nicht als neue UI-Fehler behandeln. Nur synthetische Projekte verwenden.

Ansichtswechsel erzeugen keine Revision. Quelltextänderungen verwenden weiterhin
den bestehenden Verlauf und können vor dem Speichern verworfen werden. Eine
Datenmigration ist nicht nötig; alte Darstellungswerte werden lesend aufgefangen.

## Erkenntnisse und Ergebnis

- 413 Studio-Tests bestanden, darunter zwölf neue Regressionen zu tatsächlichen
  Buttongrößen, Pixelkontrast, Icon-Aktualisierung ohne Entwurfsverlust, Hover,
  Tastaturfokus, Quelltextschutz, Zeilenumbruch, horizontalem Scrollen, alter
  Breitenpräferenz und Checkbox-Treffern nach Inhaltsausrichtung.
- 133 Studio-Quelltext-/Testdateien ohne Stilbefund; `pip check` und
  `git diff --check` bestanden. Keine neue Abhängigkeit.
- Synthetisches Projekt als echte Qt-Oberfläche geprüft: Hell/Dunkel,
  Links/Mittig/Rechts, Tabellen mit/ohne Hover und Nur-Icon-Canvas. Tabellenraster
  und Eckbereich verwenden ebenfalls die Theme-Palette. Die Canvas-Aktionsreihe
  bleibt zusammen, statt kleine Symbole über die gesamte Breite zu verteilen.
- Qt-Header benötigen explizite Header-Items, damit unsichtbare zugängliche
  Zeilen-/Spaltennamen erhalten bleiben; nur `setHeaderData` reicht hier nicht.
  Diese Namen werden getestet, aber nicht als technische Nummern angezeigt.
- Gesamtcheck erneut ausgeführt: Godot fehlt; 1.907 bereits bestehende
  Stilbefunde außerhalb des Studio-Quellcodes. Toolsuite: 258 bestanden,
  37 übersprungen, drei bekannte Fehler beim Godot-Fenstervertrag und fehlenden
  Game-Entscheidungsdokumenten/Links. Keine Ausweitung dieses UI-Pakets darauf.
- Aktuelles Nutzerbriefing: [Darstellung](../asset-studio/DARSTELLUNG.md).
  Die persönliche Benutzerabnahme bleibt separat; T017/T018 bleiben unverändert.
