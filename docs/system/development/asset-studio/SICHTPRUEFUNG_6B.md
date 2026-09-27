# Nachbriefing 6b – Aufgaben-Kanban

Deine Prüfungen 1–7 aus Zwischenpaket 6a sind bestätigt. Für diese Runde reicht
das bestehende Testprojekt; kein neuer Quellenimport und kein neues Projekt nötig.
Studio neu starten: `python3 tools/control.py asset-manager run`.

## Bitte diese sieben Punkte prüfen

1. **Aufteilung:** Projekt-Canvas, Aufgaben-Kanban, Dokumentation & Anhänge,
   Suche stehen in dieser Reihenfolge. Kanban zeigt Offen, In Arbeit, Blockiert,
   Erledigt. Die Canvas-Eigenschaften sind nur hier ausgeblendet; im Canvas
   weiterhin vorhanden. Bei kleinem Fenster gegebenenfalls seitlich scrollen.
2. **Bereiche:** Oben die Projektwurzel wählen: alle Aufgaben nach projektweiten
   Inhalten/Akten/Kapiteln gruppiert. Dann einen Akt, ein Kapitel und den Helden
   auswählen: jeweils nur passende Aufgaben. Verwendete Assets stehen mit ihrer
   Herkunft darin, ohne doppelte Aufgaben. Gruppen auf-/zuklappen.
3. **Anlegen und Öffnen:** Im Kapitel eine Aufgabe und ein Issue mit Beschreibung
   anlegen. Sie gehören zu diesem Kapitel und sind auch oben im Gesamtprojekt
   sichtbar. Klick zeigt Inhalt, ohne den Bereich zu wechseln; Doppelklick öffnet
   den Editor. **Zum Bezug** und **Gesamtes Projekt** bewusst ausprobieren.
4. **Status:** Eine Aufgabe nach In Arbeit und Blockiert ziehen, alternativ
   unten **Status setzen** benutzen. Zwei To-dos ergänzen: Solange einer offen
   ist, muss Erledigt abgelehnt werden. Danach beide abhaken und Erledigt setzen.
   Falls Aufgabenabnahme gewählt wurde, muss eine Bestätigung erscheinen.
5. **Filtern und Suchen:** Nur Aufgaben / Nur Issues / beide ausprobieren;
   Titel oder To-do-Text filtern. Strg+F öffnet die separate Suche. Dort eine
   Notiz und eine Aufgabe finden/öffnen. Kanban- und Suchfilter bleiben getrennt.
6. **Dieselben Daten:** Eine Aufgabe des Helden im Kanban bearbeiten und im
   Asset-Menü → Dokumentation → Aufgaben & Issues öffnen: gleicher Text,
   Status und To-do-Stand. Eine ungespeicherte Notiz darf dabei nicht verschwinden.
7. **Neustart:** Projekt schließen und erneut öffnen. Texte, Häkchen, Status
   und Zuordnung bleiben erhalten. Alte Aufgaben müssen weiterhin lesbar sein.

Rückmeldung als **✅ 1–7** oder **❗ Nummer: Befund** genügt.
Automatisierte Tests sind keine persönliche Bedienungsabnahme.

## Überspringen und nächste Kontrollinstanz

Rastererkennung, Quellenrevisionen, Posenersatz, Canvas-Zoom und Größenänderung
müssen diesmal nicht erneut vollständig getestet werden. Auch keine 200 Assets
anlegen und keine absichtlichen Datenkonflikte erzeugen; dafür gibt es Regressionstests.

Der interne Objektspeicher darf seine Hashnamen behalten. Godot-Export/
Testbereitstellung kommt später; bitte jetzt keine Originale manuell umsortieren.
Notiz-Icon gegenüber Notizsammlung bleibt eine offene Bedienentscheidung.

Nach dieser Abnahme schlagen wir T017/#24 (kontrollierte Pipeline-Prozesse) und
T018/#25 (Build-Abhängigkeiten und Veraltung) als nächstes Paket vor. Sie sind
noch nicht begonnen und brauchen vor der Umsetzung deine Freigabe.
