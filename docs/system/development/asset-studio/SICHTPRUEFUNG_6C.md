# Nachbriefing 6c – Baumzuordnung und Notizen

Deine sieben Kanban-Tests aus 6b sind bestätigt. Das bestehende Testprojekt
reicht; Studio neu starten: `python3 tools/control.py asset-manager run`.
Die kleinen Aufgaben-/Notizsymbole gehören wie besprochen in den Projekt-Canvas.

## Bitte diese sieben Punkte prüfen

1. **Zuordnen:** Im Baum eine Asset-Karte in ein anderes erlaubtes Kapitel
   ziehen, anschließend eine Aufgabe und eine Notiz auf eine andere Karte.
   Baum, Canvas, Kanban bzw. Notizbereich folgen der neuen Zuordnung.
   Strg+Z und Strg+Umschalt+Z ausprobieren: Inhalt und To-dos bleiben erhalten.
   Bei eingeklappten Zielen kurz verweilen; am Baumrand muss Scrollen möglich sein.
2. **Gemeinsam verwenden:** Ein Asset mit Strg auf ein weiteres Kapitel ziehen.
   Das Original bleibt stehen, ein Verweis erscheint. Diesen Verweis ohne Strg
   auf ein anderes Kapitel ziehen: Nur die Verwendung wechselt. Auch dies
   rückgängig machen. Keine zweite Asset-Karte bzw. kopierte Aufgabe erwarten.
3. **Ungültiges Ziel:** Einen Akt auf sein eigenes Kapitel oder eine Karte auf
   sich selbst ziehen. Es darf keine neue Zuordnung entstehen; Hinweis unten
   in der Statusleiste. Die alte Hierarchie-Auswahlliste ist entfernt.
4. **Canvas-Symbole:** Aufgaben/Issues und Notizen sind deutlich kleiner als
   Asset-/Kapitelkarten. Assets haben einen Würfel. Symbole bei verschiedenen
   Zoomstufen auswählen/verschieben: kein Springen. Doppelklick öffnet jeweils
   genau einen passenden Aufgaben- oder Notizeditor; Kanban bleibt unverändert.
5. **Notiz-Dashboard:** Zwischen Aufgaben-Kanban und Dokumentation liegt
   **Notizen**. Zwei Notizen anlegen, Farbe ändern, eine oben anheften.
   Text-/Farbfilter, Kapitelbereich und **Gesamtes Projekt** ausprobieren.
   Post-its zeigen Titel, Textauszug und Herkunft; bei Bedarf wird gescrollt.
6. **Dieselben Inhalte und Entwurfsschutz:** Eine Notiz über **Dokument / Anhänge**
   öffnen. Text und vorhandene Anhänge müssen dieselben sein. Text ändern und
   vor dem Speichern einen Baum-Drag beginnen: Abbrechen lässt alles stehen;
   Speichern übernimmt den Text. Einen geänderten Post-it-Editor schließen:
   ebenfalls Speichern/Verwerfen/Abbrechen, kein stiller Datenverlust.
7. **Neustart:** App schließen und Projekt erneut öffnen. Zuordnungen,
   Verwendungen, Texte, Farben, angeheftete Notizen und verschobene Symbole
   bleiben erhalten. Bestehende Dokumente und alte Notizen weiterhin öffnen.

Rückmeldung als **✅ 1–7** oder **❗ Nummer: Befund** genügt. Automatisierte
Qt-Tests ersetzen den persönlichen Eindruck beim Ziehen und Lesen nicht.

## Diesmal überspringen

Kein neues Projekt, kein erneuter Quellen-/Spritesheet-Import, kein kompletter
Raster-/Revisionsdurchlauf. Auch nicht alle Kanban-Statusregeln erneut prüfen.
Die neuen Symbole kurz bei anderem Zoom anklicken reicht; der alte Canvas muss
nicht vollständig neu abgenommen werden. Keine 200 Testassets anlegen und keine
absichtlichen Mehrbenutzerkonflikte erzeugen.

Nach deiner Rückmeldung bleiben T017/#24 (kontrollierte Pipeline-Prozesse) und
T018/#25 (Build-Abhängigkeiten und Veraltung) der Vorschlag für das nächste Paket.
Sie sind nicht begonnen. Godot-Export und das Aufbereiten der internen
Hashablage in lesbare Spielpfade kommen ebenfalls erst in späteren Paketen.
