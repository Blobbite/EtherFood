# Zwischenpaket 6b – Aufgaben-Kanban und getrennte Suche

## Zweck und Ausgangslage

Die persönliche Nachprüfung 6a (Punkte 1–7) wurde am 27.09.2026 vom Benutzer
bestätigt. Aufgaben und Issues besitzen bereits Beschreibungen, Fundstellen,
revisionierte To-do-Listen und vier Status. Bisher teilen sie sich jedoch einen
Reiter mit der Dokumentensuche. Der neue Auftrag trennt diese Arbeitsbereiche.

## Umfang und Grenzen

- Reiter: Projekt-Canvas, Aufgaben-Kanban, Dokumentation & Anhänge, Suche.
- Ein Board für vorhandene Aufgaben und Issues, Typfilter und vier Spalten:
  Offen, In Arbeit, Blockiert, Erledigt. Die aktuelle Karte bestimmt den Bereich.
- Projektwurzel zeigt alle Aufgaben, gruppiert nach projektweiten Inhalten,
  Akten, Kapiteln und Eigentümern. Verwendete Assets bleiben dieselben Datensätze.
- Statuswechsel über Ziehen und Schaltfläche; bestehende To-do-, Abnahme- und
  Revisionsregeln gelten auch dabei. Keine Änderung der Eigentümerschaft.
- Suche separat; vorhandene Asset-Aufgabenansicht verwendet dieselben Dienste
  und Bearbeitungsaktionen. Keine zweite Datenbank, keine Migration.
- Kein Umbau der Notizdarstellung, keine Bildpipeline und keine Godot-Ausgabe.
  T017/T018 beginnen erst nach einem weiteren freigegebenen Briefing.

## Schritte und Fortschritt

1. [x] Istzustand, Repository-Grenzen und Abnahme 6a erfassen.
2. [x] Gemeinsame Aufgabenaktionen und bereichsbezogene Board-Projektion umsetzen.
3. [x] Kanban, Navigation und getrennte Suche einbinden.
4. [x] Dienst- und echte Qt-Regressionstests ausführen; Bedienansicht prüfen.
5. [x] Gesamtläufe, Dokumentation und kurze Nachprüfung abschließen.
6. [ ] Eigene Änderungen gezielt committen, pushen und Remote-Stand prüfen.

## Entscheidungen und Erkenntnisse

- Ein Klick auf eine Kanban-Aufgabe liest den Inhalt, ohne den Projektbereich
  automatisch auf den Eigentümer zu verkleinern. Navigation erfolgt ausdrücklich.
- Gruppen sind abgeleitete Ansichten der stabilen Eigentümer-IDs. Verschieben
  zwischen Spalten ändert ausschließlich den Status, auch bei gemeinsamem Einsatz.
- `.asset-studio/objects` bleibt unveränderlicher, hashadressierter Quellenspeicher.
  Lesbare Godot-Pakete sind Gegenstand von T035/T036/T039, nicht dieser UI-Arbeit.
- Bereits vorhandene Änderungen an Control-Tools, Spielgrafiken, Testlabor und
  zugehöriger Dokumentation bleiben erhalten und außerhalb dieses Commits.

## Prüfungen

Geplant: Hierarchie/Verwendungen, Filter, Gruppierung nach Umbenennung,
Statuswechsel mit Konflikten/offenen To-dos/Abnahme, getrennte Suche, schmutzige
Notizen, Neuanlage, Wiederöffnen; anschließend vollständige Studio-/Pipeline-
Prüfung, Studio-Stilcheck und Repository-Standardcheck. Ergebnisse folgen hier.

Zwischenstand: 51 bisherige Dienst-/GUI-Tests und 10 neue Projektionstests
bestanden. Acht von neun neuen Qt-Tests bestanden sofort. Der neunte deckte
Qt-Autoaufklappen bei wiederhergestellter Auswahl auf: Der eingeklappte Zustand
wird nun nach der Auswahl wieder angewendet. Neue Qt-Tests prüfen echte Drop-
Events; nur die native blockierende `QDrag.exec`-Mausschleife ist dabei ersetzt.

Erster vollständiger Studio-Lauf: **209 bestanden**, anschließend zentraler
Asset-Manager-Check mit **209 Studio- und 171 Pipeline-Tests bestanden**.
Zusätzlicher Regressionstest gegen doppelte Editoröffnung bei Doppelklick:
**10 neue Qt-Tests bestanden**. Die zuerst kollidierenden Testmodulnamen wurden
vor dem Gesamtlauf eindeutig benannt; keine Tests übersprungen.

Echte Qt-Screenshots mit synthetischen Daten in 1440×900 und 1050×640 geprüft.
Auswahltext zunächst schlecht lesbar: explizite Auswahlfarben und zweizeilige,
nicht umbrechende Kartenzeilen mit vollständigem Tooltip korrigieren dies.
Die Canvas-Eigenschaftenleiste ist nur im Kanban ausgeblendet. Ein Regressionstest
prüft ihre Rückkehr beim Wechsel zum Canvas. Aktuelle Studio-Stilprüfung:
**81 Dateien ohne Befund**. Abschließender zentraler Wiederholungslauf:
**210 Studio-Tests und 171 Pipeline-Tests bestanden**.

Repository-Standardcheck tatsächlich ausgeführt: **259 bestanden, 37 übersprungen,
2 bestehende Dokumentationstests fehlgeschlagen**. Es fehlen weiterhin die
Entscheidungsübersicht und ADR-0008 unter `docs/game/decisions/`; außerdem fehlen
Godot 4 und es bestehen **1907 geerbte Stilbefunde in 247 geprüften Dateien**.
Kein Studio-Stilbefund; diese fremden Baustellen bleiben unverändert.

## Wiederholbarkeit und Wiederherstellung

Nur synthetische Projekte in temporären Verzeichnissen testen. Bestehende
Aufgaben bleiben ohne Datenmigration lesbar. Fehlgeschlagene Statuswechsel
dürfen weder Karte noch Revision verändern; UI wird aus dem Katalog erneuert.
Keine Originalbilder oder Git-Historie löschen. Eigene Pfade einzeln stagen.

## Ergebnis

Implementierung und technische Prüfung abgeschlossen. [Ergebnisbericht](../asset-studio/task-results/6b.md)
und [sieben kurze Nachtests](../asset-studio/SICHTPRUEFUNG_6B.md) dokumentiert.
Commit/Push steht als letzter Übergabeschritt an. Persönliche Nachprüfung 6b
erfolgt nach der Übergabe; die bestätigte Nachprüfung 6a schließt keine früher
zurückgestellten Kriterien. Spätere Pipeline-Issues nicht begonnen.
