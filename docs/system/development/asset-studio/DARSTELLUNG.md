# Darstellung und Markdown: Bedienbriefing

[Asset Studio](index.md) · [Markdown-Bedienung](DOKUMENTATION.md) ·
[Arbeitsplan](../plans/asset-studio-darstellung-und-markdown.md)

Die App vollständig schließen und neu starten. Das bestehende Testprojekt kann
weiterverwendet werden; für Löschversuche am besten eine Testdokumentation anlegen.
Es gibt keine neue Abhängigkeit und keine Datenmigration.

## Was sich geändert hat

- **Einstellungen** bleibt rechts oben erreichbar, auch bei schmalem Fenster.
  **Hell · Tag / Dunkel · Nacht** gilt für Hauptfenster, Canvas, Notizen, Kanban,
  Dokumentation und Dialoge. Eine Qt-Fusion-Darstellung sorgt für einheitliche
  Farben unabhängig vom Betriebssystem-Thema.
- **Text + Icons / Nur Icons / Nur Text** gilt für Aktionsbuttons und Bereichsreiter,
  auch im Asset-Menü. Nur-Icon-Schalter behalten Tooltips. Inhaltsbeschriftungen,
  Statusgruppen und Formularfelder verschwinden dadurch nicht.
- Darstellungseinstellungen bleiben lokal nach Neustart erhalten. Ansichtswechsel
  schreiben keine Projektinhalte oder Revisionen und verwerfen keine Entwürfe.
- Leere To-do-Bereiche von Aufgaben/Issues haben **To-dos hinzufügen …**. Der
  bestehende Aufgabeneditor öffnet direkt bei der Eingabe. Speichern/Abbrechen
  und der bisherige Revisionsschutz bleiben bestehen.
- Beim Canvas-Verschieben zählt die gehaltene mittlere Maustaste. Seitliches
  Mausradkippen, zusätzliche Seitentasten und Radimpulse verursachen währenddessen
  keine Sprünge. Außerhalb der Geste bleiben vertikales Scrollen und Strg+Rad-Zoom.
- Markdown besitzt Tabellenwerkzeuge, anklickbare Checkboxen, kompakte
  Überschriftbearbeitung und vier Schalter für die Inhaltsbreite/-ausrichtung.

## Bitte diese acht Punkte testen

1. **Leere Aufgabe und leeres Issue:** auswählen, **To-dos hinzufügen …** drücken.
   Direkt einen Punkt tippen und speichern. Punkt rechts sichtbar, leerer
   Hinzufügen-Button verschwunden. Dasselbe einmal abbrechen: keine Änderung.
2. **Hell/Dunkel:** umschalten, danach Canvas, Aufgaben, Notizen, Dokumentation
   und Asset-Menü ansehen. Keine weißen Kanban-Flächen im Dunkelmodus, alle
   Beschriftungen lesbar. Ein offener Textentwurf muss erhalten bleiben.
3. **Drei Button-Modi:** alle drei Einstellungen durchschalten. Auch Bereichsreiter
   wechseln mit. Bei Nur Icons über Symbole fahren: Namen als Tooltip. App
   neu starten: Farbschema und Button-Modus bleiben erhalten.
4. **Mausrad:** mittlere Taste halten und Canvas verschieben; dabei das Rad
   nach links/rechts kippen. Kein Sprung/Zoom und keine verschobene Karte.
   Mittlere Taste loslassen: normale Bedienung; Strg+Rad muss weiterhin zoomen.
5. **Tabelle:** Zelle doppelt anklicken und ändern. Obere/seitliche Leiste ziehen,
   `+` oben/rechts/links/unten testen. Eine ganze Spalte/Zeile auswählen und
   entfernen, Strg+Z testen. Speichern und Dokument neu öffnen.
6. **Überschrift und Checkbox:** Überschrift anklicken, ohne großen Höhensprung
   ändern. Markdown-To-do anklicken: Häkchen umschaltbar; Code-Modus zeigt
   `[ ]` bzw. `[x]`. Speichern/Neuladen und eine verschachtelte Liste testen.
7. **Vier Ansichten:** Links/Mittig/Rechts/Volle Breite bei breitem Fenster
   durchschalten. Inhaltsfläche wandert/ändert ihre Breite, Text bleibt gleich.
   Keine Absatzformatierung und kein Betriebssystem-Vollbildwechsel erwartet.
8. **Asset-Menü und Bericht:** dieselbe Dokumentation dort bearbeiten. Tabellen,
   Checkboxen und Schalter funktionieren identisch; ein generierter Bericht
   bleibt überall schreibgeschützt.

Bereits bestätigte Spritesheet-, Masken-, Varianten-, Import- und Pinnwand-
Positionierungstests können diesmal übersprungen werden. Godot-Export und
Szeneneditor gehören nicht zu diesem Paket. T017/T018 werden dadurch nicht
automatisch abgenommen oder geschlossen.

Rückmeldung bitte wieder als `1 ✅` bis `8 ✅` oder mit der konkreten Abweichung.

## Technischer Prüfstand

- **401 Studio-Tests bestanden**, einschließlich realer Qt-Ereignisse im
  Offscreen-Modus. Abgedeckt sind unter anderem Theme-/Moduspersistenz,
  Entwurfserhalt, Seitentasten während Canvas-Pan, Aufgaben-Popup-Fokus,
  Quelltexttreue bei CRLF/Emoji, Tabellenoperationen, Checkboxen und Undo/Redo
  ohne unbeabsichtigtes Zurücksetzen von Canvas-Positionen.
- **130 Studio-Quelltext-/Testdateien ohne Stilbefund**, `pip check` und
  `git diff --check` bestanden. Keine neue Abhängigkeit.
- Synthetisches Projekt in Hell/Dunkel geprüft: Notizen, Markdown, Kanban,
  Canvas und Nur-Icon-Navigation. Dies ersetzt nicht die persönliche Abnahme.
- Repository-Gesamtcheck weiterhin nicht grün: Godot fehlt im Container;
  1.907 bestehende Stilbefunde außerhalb des Studio-Quellcodes. Die Toolsuite
  meldet 258 bestanden, 37 übersprungen und drei bestehende Fehler beim
  Godot-Fenstervertrag bzw. den fehlenden Game-Entscheidungsdokumenten/Links.
