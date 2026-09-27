# Darstellung und Markdown: aktuelles Bedienbriefing

[Asset Studio](index.md) · [Markdown-Bedienung](DOKUMENTATION.md) ·
[Arbeitsplan](../plans/asset-studio-markdown-feinschliff.md)

Die App vollständig schließen und neu starten. Das bestehende Testprojekt kann
weiterverwendet werden; für Löschversuche eine Testdokumentation anlegen.
Keine neue Abhängigkeit und keine Datenmigration.

## Was sich geändert hat

- **Nur Icons** verwendet 16-Pixel-Symbole und kompakte 28-Pixel-Aktionsbuttons.
  Das doppelte Issue-Symbol bleibt breiter. Tooltips und zugängliche Namen bleiben
  erhalten; Text + Icons und Nur Text lassen sich jederzeit wiederherstellen.
- Symbole wechseln passend zu Hell/Dunkel ihre Konturen und Farbhelligkeit.
  Projektbaum, Canvas, Suche, Filter, Dokumentauswahl und neue Dialoge verwenden
  dieselben kontrastabhängigen Icons, unabhängig vom Betriebssystem-Icon-Thema.
- Markdown-Tabellen zeigen keine Zeilen-/Spaltennummern oder dauerhafte
  Löschleiste. Kleine Griffe und Pluszeichen erscheinen bei Hover oder Fokus.
  Die Tabelle nutzt die Breite; Zelltext bricht mit passender Zeilenhöhe um.
- Die Dokumentationsfläche bleibt **immer voll breit**. Links/Mittig/Rechts
  richten gerenderte Inhalte darin aus. Kein zusätzlicher Vollbreite-Schalter
  und keine schmale 820-Pixel-Fläche mehr.
- Umschalten ändert weder Markdown-Quelle noch Revisionen oder offene Entwürfe.
  Code bleibt links, Tabellen behalten ihre eigenen Spaltenausrichtungen.

## Bitte diese sechs Punkte testen

1. **Kompakte Buttons:** Einstellungen → Nur Text → Nur Icons → Text + Icons.
   Nur Icons muss kompakter sein, Namen erscheinen als Tooltip. Auch im
   Asset-Menü und bei Speichern/Abbrechen prüfen.
2. **Kontrast:** Hell und Dunkel durchschalten. Symbole in Toolbar, Projektbaum,
   Canvas, Reitern, Suche und Dokumentauswahl bleiben gut sichtbar. Eine
   ungespeicherte Textänderung darf dabei nicht verloren gehen.
3. **Ruhige Tabelle:** Dokument öffnen, außerhalb der Tabelle klicken und Maus
   wegbewegen: keine Nummern, Griffe oder Löschbuttons. Darüberfahren oder per
   Tab hineingehen: kleine Griffe und `+` erscheinen ohne Positionssprung.
   Fenster schmaler/breiter ziehen: lange Zellen bleiben lesbar.
4. **Tabellen bearbeiten:** Zelle doppelklicken; am oberen/seitlichen Griff
   Spalte/Zeile verschieben. `+` an Griffen und rechts/unten ausprobieren.
   Ganze Spalte/Zeile am Griff markieren und mit Entf oder Rechtsklick entfernen.
   Strg+Z stellt sie wieder her. Kopfzeile/letzte Spalte bleiben geschützt.
5. **Drei Ausrichtungen:** Links/Mittig/Rechts bei breitem Fenster durchschalten.
   Die Fläche bleibt gleich breit, Überschrift/Text/Listen bewegen sich darin.
   Checkbox weiterhin anklickbar; Code und Tabellenspalten bleiben unverändert.
   Der Code-Modus zeigt keine durch Ausrichtung hinzugefügten Zeichen.
6. **Speichern und Asset-Menü:** Testdokument speichern, erneut öffnen; dieselben
   Funktionen im Asset-Menü prüfen. App-Neustart erhält Farbschema, Button-Modus
   und Inhaltsausrichtung. Generierte Berichte bleiben schreibgeschützt.

Bestätigte Spritesheet-, Masken-, Varianten-, Import-, Pinnwand-, Aufgaben-Popup-
und Canvas-Mausradtests können diesmal übersprungen werden. Godot-Export und
Szeneneditor gehören nicht zu diesem Paket. T017/T018 werden dadurch nicht
automatisch abgenommen oder geschlossen.

Rückmeldung bitte als `1 ✅` bis `6 ✅` oder mit der konkreten Abweichung.

## Technischer Prüfstand

- **413 Studio-Tests bestanden**, einschließlich echter Qt-Ereignisse und zwölf
  neuer Regressionen für diesen Feinschliff. 133 Studio-Quelltext-/Testdateien
  ohne Stilbefund; `pip check` und `git diff --check` bestanden.
- Hell/Dunkel, Hover-Tabellen, Inhaltsausrichtung und Nur-Icons wurden mit einem
  synthetischen Projekt visuell geprüft. Die Desktop-Abnahme bleibt separat.
- Gesamtcheck weiterhin nicht grün: Godot fehlt; 1.907 bestehende Stilbefunde
  außerhalb des Studio-Quellcodes. Toolsuite: 258 bestanden, 37 übersprungen,
  drei bekannte Fehler beim Godot-Fenstervertrag und fehlenden
  Game-Entscheidungsdokumenten/Links. Details im verlinkten Arbeitsplan.
