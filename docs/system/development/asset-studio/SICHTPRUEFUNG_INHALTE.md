# Briefing: direkte Inhalte und Canvas-Bedienung

[Asset Studio](index.md) · [Arbeitsplan](../plans/asset-studio-inhaltsoberflaechen.md)

Status: technische Umsetzung und automatisierte Prüfungen abgeschlossen;
persönliche Sichtabnahme noch offen. T017/T018 bleiben bis zur gesonderten
Abnahme offen. Dieses Zwischenpaket startet weder neue Bildpipelines noch
den Szeneneditor.

## Vorbereitung

Die App vollständig schließen und neu starten, damit der neue Python-Code
geladen wird. Bei bestehender Installation die GUI-Abhängigkeiten aktualisieren:

```bash
.venv/bin/python -m pip install -e 'tools/AssetManager[test,gui]'
```

Falls der zentrale Control-Einstieg im eigenen Checkout bereits vorhanden ist,
erledigt `python tools/control.py asset-manager import` diese Vorbereitung.
Kein neues Studio-Projekt nötig; für Lösch-/Konfliktexperimente eine Testkopie nutzen.

## Sechs gezielte Tests

1. **Notizen:** einen bisher leeren Notizbereich öffnen. Die gelbe Karte muss
   sofort sichtbar sein. Titel und Stichpunkte direkt dort eingeben, kurz
   warten und Bereich wechseln. Zurückkehren und App neu starten: Text vorhanden,
   keine Umleitung zur Dokumentation und kein zusätzlicher Editor darunter.
2. **Notizregeln:** Rechtsklick → Farbe ändern und anheften. Über 100 Wörter
   eingeben: Hinweis und ungespeicherter Entwurf bleiben sichtbar, nichts wird
   abgeschnitten. Auf höchstens 100 Wörter kürzen und speichern. Bestehende
   lange Alttexte dürfen beim bloßen Öffnen/Farbwechsel nicht verloren gehen.
3. **Dokumentation:** Markdown mit Überschrift, Tabelle, Liste und Code öffnen.
   Überschrift anklicken, sichtbare `#`-Zeichen/Text ändern und wegklicken.
   Rechtsklick → Tabelle/Codeblock einfügen, speichern und erneut öffnen.
   Es gibt nur eine Inhaltsfläche; Berichte bleiben schreibgeschützt.
4. **Aufgaben und Issues:** eine Aufgabe mit To-dos auswählen. Vier kompakte
   Spalten links, To-dos rechts, Zusatztext darunter. Statuswechsel prüfen:
   offener Kreis → blauer Punkt → X → grüner Haken; beim Issue zusätzlich `!`.
   Baum und Canvas müssen dasselbe Symbol zeigen. Offene To-dos verhindern Erledigt.
5. **Canvas:** einen Anschluss auf freie Fläche ziehen, passende Notiz oder
   Dokumentation anlegen, Position/Zuordnung kontrollieren, Strg+Z und Wiederholen.
   Dasselbe abbrechen: keine neue Karte. Mehrere Karten mit Strg+Klick markieren,
   Rechtsklick → Auswahl anordnen → Kreis/Linie. Anker und übrige Karten bleiben
   stehen. Gemeinsam ziehen sowie Undo bei vergrößerter/verkleinerter Ansicht testen.
6. **Asset-Menü:** denselben Inhalt dort öffnen. Dokumente verwenden dieselbe
   Markdown-Fläche, Notizen stehen als bearbeitbare Karten untereinander.
   Aufgaben/Issues liegen in vier schmalen aufklappbaren Statusgruppen.
   Auch auf eine eingeklappte Statuszeile ziehen; Änderung anschließend im
   Hauptfenster kontrollieren. IDs/Inhalte dürfen nicht doppelt entstehen.

Nicht erneut erforderlich: Spritesheet-Import, Masken, Varianten, Godot-Export
oder Szeneneditor. Diese gehören nicht zu diesem UI-Paket.

## Technischer Nachweis

- 343 Studio-Tests bestanden, einschließlich realer Qt-Ereignisse im Offscreen-Modus.
- 56 vorhandene Control-/Asset-Manager-Tests nach Ergänzung der Parser-Testversion bestanden.
- Studio-Quelltext-/Teststilprüfung und `pip check` bestanden;
  `git diff --check` ohne Befund.
- Screenshots aus einem synthetischen Projekt für Notizen, Dokumentation,
  Haupt-Kanban und kompakte Asset-Aufgaben geprüft. Das ersetzt keine Benutzerabnahme.
- Repository-Gesamtcheck **nicht grün**: Godot fehlt im Container; bestehende
  Stilbefunde außerhalb des Studio-Quellcodes. Der separate Tool-Testlauf meldet
  258 bestanden, 37 übersprungen und drei Fehler: geänderter Godot-Fenstervertrag,
  zwei fehlende Entscheidungsdokumente und 13 darauf bezogene Dokumentationslinks.
  Keine Änderungen am Spielkanon oder an fremden Game-Arbeiten vorgenommen.

Bitte den Bericht als `1 ✅`, `2 ✅` usw. mit konkreter Abweichung pro Punkt
zurückgeben. Erst danach folgt die nächste Abnahme-/Issue-Entscheidung.
