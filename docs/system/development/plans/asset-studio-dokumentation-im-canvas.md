# Zwischenpaket 6d – Dokumentation im Canvas

## Zweck und Ausgangslage

Nach 6c bleiben Notizen und Dokumentation getrennte Arbeitsbereiche. Der Benutzer
möchte im Dokumentationsreiter **+ Dokumentation** statt **+ Notiz**, weiterhin
Markdown-Import, sichtbare Dokumente mit eigener Farbe/Symbol im Projekt-Canvas
und einen kräftigeren, ausschließlich grünen Aufgabenhaken. Anschließend sollen
die nächsten Issues vorgeschlagen, aber noch nicht umgesetzt werden.

Die bisherige Dokumentanlage verwendet standardmäßig die Vorlage Freie Notiz;
der Canvas zeigt bisher nur Notizdokumente, Aufgaben und Issues. Ein bloßer
Textwechsel würde neue Dokumentation fälschlich als Post-it einsortieren.

## Umfang und Entscheidungen

- Neue neutrale Vorlage Dokumentation; der Dokumentationsbutton bietet nur
  Dokumentvorlagen an. Notiz-Anlage über Dashboard/Kontext bleibt erhalten.
- Neue Markdown-Importe sind Dokumentation. Ausdrückliche Revisionen bestehender
  Dokumente/Notizen behalten ihren Typ, ihre UUID und Anhänge. Keine Migration
  oder automatische Umdeutung bestehender Inhalte.
- Alle aktiven Dokumente erhalten kompakte Canvas-Symbole. Notizfarben bleiben,
  übrige Dokumente erhalten violette Seitenicons und einen eigenen Hintergrund.
  Generierte Berichte bleiben schreibgeschützt und nicht frei umhängbar.
- Ein gemeinsamer Qt-gezeichneter grüner Haken ohne Hintergrund ersetzt das
  plattformabhängige Aufgaben-Icon. Keine neue Bilddatei oder Abhängigkeit.
- Keine Game-/Control-Änderungen, Pipeline-Ausführung oder Godot-Bereitstellung.
  Vorhandene fremde Arbeitsstände nicht mitstagen.

## Schritte und Fortschritt

1. [x] Bestehende Anlage, Klassifikation, Canvas und nächste Plan-Issues prüfen.
2. [x] Dokumentanlage und Markdown-Import konsistent trennen.
3. [x] Dokumente im Canvas und gemeinsame Icons ergänzen.
4. [x] Gezielte Tests, Studio-/Standardcheck und Qt-Ansicht prüfen.
5. [x] Bedienungsdokumentation, kurze Prüfliste und Folgeempfehlung aktualisieren.
6. [ ] Eigene Änderungen englisch mit Emoji committen, pushen und verifizieren.

## Prüfungen und Erkenntnisse

Geplant: echte Buttonanlage, Dokument-/Notizklassifikation, Markdown-Inhalt und
Revisionsimport, Canvas-Farbe und Icon, Doppelklick, Verschieben/Undo/Neustart,
Entwurfsschutz sowie schreibgeschützte Berichte. Bestehende Notiz-/Kanban-Tests
mitprüfen. Ergebnisse werden während der Umsetzung ergänzt.

Erster gezielter Lauf: **52 bestehende Dienst-/Qt-Tests bestanden**. Der neue
Dokumenttyp ist nur die neutrale Vorlage Dokumentation, kein neues Datenbankschema.
Auch leere Markdown-Quellen behalten beim Import jetzt ihren exakten Inhalt.

**17 neue Tests** (fünf Diensttests, zwölf Qt-Tests inklusive Parametrisierungen)
bestanden. Zentraler Abschlusslauf: **261 Studio-Tests und 171 Pipeline-Tests
bestanden**. Tatsächliche Qt-Screenshots bei 1440×900 und 1050×640 geprüft;
Dokumente, Notizen und Aufgaben sind durch Icon/Farbe unterscheidbar.
**90 Studio-Dateien ohne Stilbefund**, `git diff --check` sauber.

Standardcheck tatsächlich ausgeführt: **259 bestanden, 37 übersprungen,
2 bestehende Dokumentationsfehler**, 13 defekte Bestandslinks wegen fehlender
Entscheidungsübersicht/ADR-0008. Godot 4 fehlt; **1907 geerbte Stilbefunde in
256 Dateien**, kein Studio-Befund. Bestehende Probleme nicht verdeckt.

## Wiederholbarkeit und Wiederherstellung

Nur synthetische Projekte und Screenshots in temporären Verzeichnissen. Alte
Dokumente und Notizen bleiben unverändert; neue optionale Vorlage benötigt keine
Schemaänderung. Revisions-/Anhangschutz weiterverwenden. Eigene Dateien einzeln
stagen, keine Geheimnisse oder Rechnerpfade übernehmen.

## Ergebnis und nächste Kontrollinstanz

Implementierung und technische Prüfung abgeschlossen.
[Vier Nachtests und Folgeempfehlung](../asset-studio/SICHTPRUEFUNG_6D.md),
[Ergebnisbericht](../asset-studio/task-results/6d.md) und
[Bedienung](../asset-studio/NOTIZEN_UND_ZUORDNUNG.md) aktualisiert.

Nach der kurzen Bedienprüfung Vorschlag für Paket 7: T017/#24 (kontrollierte
Arbeitsprozesse) und T018/#25 (Buildplan, Cache und Veraltung). Beide Issues und
Phase C/#4 wurden lesend auf GitHub als offen bestätigt. Keine persönliche
Abnahme von 6c/6d und keine Pipeline-Freigabe vorwegnehmen.
