# Zwischenpaket 6c – Zuordnung im Projektbaum und Notiz-Dashboard

## Zweck und Ausgangslage

Der Benutzer hat alle sieben Nachtests von 6b bestätigt. Große Projektlisten
sollen nicht mehr über eine Hierarchie-Auswahlliste bedient werden. Neue
Arbeitsaufträge: Drag-and-drop im Projekt-/Verwendungsbaum, farbige Post-its
in einem eigenen Notizreiter, kompakte Inhaltssymbole und eindeutiges Asset-Icon.

## Umfang und Entscheidungen

- Originalkarten verschieben ihre Eigentümerschaft. Aufgaben, Issues und
  manuelle Dokumente lassen sich ebenfalls einer anderen aktiven Karte zuordnen.
- Verwendungs-Verweise verschieben nur die Verwendung, niemals das Original.
  Strg+Ziehen eines Assets/Pakets legt eine Verwendung an. Selbst-/Kreisbezüge,
  unzulässige Ebenen, Archivzweige und veraltete Stände werden abgelehnt.
- Neue Zuordnungen verwenden bestehende Dienste und Undo/Redo. Keine Dateien
  verschieben, keine zweite Datenbank, keine kopierten Aufgaben/Notizen.
- Reiter: Projekt-Canvas, Aufgaben-Kanban, Notizen, Dokumentation & Anhänge, Suche.
  Notizen sind bestehende manuelle Dokumente der Vorlagen Freie Notiz/Testnotiz.
  Farbe und Anheften sind optionale, validierte Darstellungsangaben. Dokumentation
  und sichere Anhänge bleiben erhalten, keine automatische Klassifikationsmigration.
- Der Benutzer hat die Rückfrage bestätigt: kompakte Aufgaben-/Notizsymbole
  gehören in den Projekt-Canvas; das abgenommene Aufgaben-Kanban bleibt bestehen.
- Neues Asset-Symbol im bestehenden Qt-Icon-System, keine Bitmap-Abhängigkeit.
- Keine T017/T018-Pipeline, Godot-Ausgabe oder Änderungen am Spielkanon.

## Schritte und Fortschritt

1. [x] Bestehende Dienste, Baum, Canvas und Notizspeicher untersuchen.
2. [x] Validierte, rücknehmbare Zuordnung von Karten und Inhalten ergänzen.
3. [x] Baum-Drag-and-drop und Verwendungssemantik einbinden; alte Umordnen-UI entfernen.
4. [x] Notiz-Dashboard und Bearbeitung mit Farben/Anheften implementieren.
5. [x] Kompakte Inhaltssymbole und Asset-Icon einbinden, Auslegung dokumentieren.
6. [x] Gezielte Dienste-/Qt-Tests, Gesamtprüfung und echte Ansicht prüfen.
7. [x] Abnahme 6b, Ergebnis und kurze Prüfliste 6c dokumentieren.
8. [ ] Eigene Änderungen abschnittsweise englisch mit Emoji committen/pushen.

## Prüfungen und Erkenntnisse

Geplant: zulässige/ungültige Zuordnungen, Verweise versus Original, Konflikte,
Undo/Redo, Notizen mit Anhängen, Texte/Checklisten unverändert, Notizfilter und
Farben, Entwurfsschutz, kleinere Canvas-Symbole, Zoom, Neustart und Icon-Erkennung.
Zuerst kleine Testgruppen, danach zentraler Studio-Check, Stil und Standardcheck.
Tatsächliche Ergebnisse werden während der Arbeit ergänzt.

Zwischenstand: 21 bestehende Diensttests bestanden. Erster Studio-Gesamtlauf:
208 bestanden; eine erwartete Reiterreihenfolge musste um Notizen ergänzt werden.
Ein Canvas-Klicktest deckte auf, dass automatisch ergänzte Symbole manuell
platzierte Karten verdecken konnten. Die automatische Symbolplatzierung sucht
nun freie Flächen, ohne bestehende Karten zu bewegen. Anschließend 35 gezielte
GUI-Regressionen zu Auswahl, Zoom, Notizschutz und Kanban bestanden.

Abschließend **244 Studio-Tests und 171 Pipeline-Tests bestanden** über
`python3 tools/control.py asset-manager check`. Darin 17 neue Diensttests und
17 neue Qt-Tests. Letztere stellen reale Drop-/Mausereignisse zu, ersetzen aber
die blockierende native `QDrag.exec`-Schleife. Qt ignoriert Standard-Hoverhilfen
für private MIME-Daten; eigene Aufklapp-/Scrolltimer sind separat geprüft.

Echte Qt-Screenshots bei 1440×900 und 1050×640 geprüft; Pin-Grafik nach Befund
schriftunabhängig gezeichnet. **88 Studio-Dateien ohne Stilbefund**;
`git diff --check` sauber. Standardcheck: **259 bestanden, 37 übersprungen,
2 bestehende Dokumentationsfehler** (Entscheidungsübersicht und ADR-0008 fehlen,
13 defekte Bestandslinks), Godot 4 fehlt, **1907 geerbte Stilbefunde in 254 Dateien**.
Nach den Dokumentationsänderungen bestätigt der erneute Standardcheck dieselben
Bestandsbefunde; keine zusätzlichen defekten Links.

## Wiederholbarkeit und Wiederherstellung

Synthetische Testprojekte und Screenshots nur temporär. Unverwandte vorhandene
Game-/Control-Änderungen erhalten und nicht mitstagen. Revisionen und Transaktionen
schützen gegen Teiländerungen; abgelehnte Drops ändern keine Daten oder Auswahl.
Bestehende Projekte bleiben ohne Migration verwendbar. Keine Geheimnisse kopieren.

## Ergebnis

Implementierung technisch geprüft. [Bedienung](../asset-studio/NOTIZEN_UND_ZUORDNUNG.md),
[Ergebnisbericht](../asset-studio/task-results/6c.md) und
[sieben kurze Nachtests](../asset-studio/SICHTPRUEFUNG_6C.md) angelegt.
Keine persönliche Abnahme für die neue Bedienung vorwegnehmen.
