# Dokumentation direkt im Markdown-Bereich

[Asset Studio](index.md) · [Aktuelles Bedienbriefing](DARSTELLUNG.md)

Dokumentation zeigt eine Inhaltsfläche mit zwei Schaltern darüber:

- **MD** zeigt gerendertes Markdown. Einen Absatz, eine Überschrift
  oder einen Codeblock anklicken: An derselben Stelle erscheint der bearbeitbare
  Quelltext dieses Blocks. Überschriften behalten ihre Darstellungsgröße; die
  `#`-Zeichen werden sichtbar. Beim Verlassen wird wieder gerendert.
  Tabellen verwenden den unten beschriebenen Zelleneditor; Aufgabenlisten
  enthalten direkt anklickbare Checkboxen.
- **Code** zeigt die gesamte Markdown-Quelle in Festbreitenschrift. Dieser Modus
  bleibt auch beim Wegklicken, Speichern und Wechseln des Dokuments aktiv, bis
  wieder **MD** gewählt wird. Code bedeutet hier Markdown-Quelltext, keine
  Programmausführung.

Beide Modi bearbeiten denselben Entwurf. Umschalten speichert nicht automatisch,
erzeugt keine Revision und verändert den Text nicht. Ungespeicherte Änderungen
und Rückgängig/Wiederholen bleiben beim Wechsel erhalten. Beim erneuten Start
der App ist zunächst MD aktiv. Generierte Berichte lassen sich in beiden Modi
lesen und kopieren, bleiben aber schreibgeschützt.

**Rechtsklick** bietet Überschrift, Tabelle, Codeblock, Liste, Aufgabenliste,
Zitat und Link an. Bei Tabellen werden Spalten und Datenzeilen abgefragt.
Neue Blöcke werden hinter dem angeklickten Block eingefügt. Für Änderungen
über Blockgrenzen hinweg gibt es im selben Menü **Gesamten Markdown-Quelltext
bearbeiten**. Das aktiviert denselben dauerhaften **Code**-Modus.
**Speichern / Strg+S** schreibt eine Revision; ungespeicherte Dokumente behalten
den bisherigen Speichern/Verwerfen/Abbrechen-Schutz. Anders als Post-its werden
Dokumente nicht automatisch gespeichert.

## Tabellen und Checkboxen

Im **MD**-Modus sind Tabellen ohne Wechsel zum gesamten Quelltext bearbeitbar:

- Zelle doppelt anklicken oder auswählen und tippen. Zellinhalt darf Markdown
  wie `**fett**` oder einen Link enthalten; außerhalb der Eingabe wird er gerendert.
- Kleine Griffe und `+` erscheinen beim Darüberfahren oder Tastaturfokus in der
  Tabelle. Ohne Fokus/Hover bleibt der Rand ruhig, ohne Nummern oder zusätzliche
  Beschriftungen. Die Tabelle verschiebt sich beim Einblenden nicht.
- Oberen Spaltengriff bzw. linken Zeilengriff anklicken: ganze Spalte/Zeile
  auswählen. Griff ziehen: komplette Spalte/Zeile umordnen. Die Kopfzeile
  bleibt oben; die Links-/Mitte-/Rechtsausrichtung einer Spalte wandert mit.
- `+` an jedem Griff fügt danach eine Spalte/Zeile ein. Rechts ergänzt `+`
  eine letzte Spalte, unten `+` eine letzte Datenzeile.
- Nach Auswahl am Griff löscht **Entf/Rücktaste** die ganze Spalte/Zeile.
  Alternativ am Rand rechtsklicken und im Kontextmenü entfernen. Es gibt keine
  dauerhaften Löschbuttons. Eine nur ausgewählte Zelle löscht keine Struktur.
  Kopfzeile und letzte Spalte sind geschützt. Mehrfachauswahl ist mit Strg möglich.
- Spalten teilen sich die verfügbare Breite; lange Inhalte brechen um und
  vergrößern die Zeilenhöhe. Viele Spalten bleiben horizontal scrollbar, anstatt
  unter 120 logische Pixel pro Spalte zusammengeschoben zu werden.
- Strg+Z und Wiederholen gelten nach abgeschlossener Zelleingabe auch für
  Strukturänderungen; MD und Code teilen sich denselben Entwurf und Verlauf.

Die Checkbox einer Markdown-Aufgabe `- [ ] …` anklicken oder per Tab/Leertaste
bedienen: nur das Häkchen im Quelltext ändert sich. Verschachtelung, CRLF-Zeilenenden
und andere Blöcke bleiben erhalten. Gleich aussehender Text in Codeblöcken wird
nicht als Aufgabe behandelt. Auch diese Änderungen benötigen **Speichern**.
Generierte Berichte erlauben weder Zelländerungen noch Checkbox-Umschaltung.

Bei Überschriften bleibt die Schriftgröße beim Anklicken erhalten. Die leeren
Trennzeilen im Quelltext erzeugen dabei keine zusätzlichen leeren Editorzeilen
unter der Überschrift; der Originaltext wird nicht abgeschnitten.

## Volle Breite und Inhaltsausrichtung

Die Dokumentationsfläche nutzt immer die gesamte verfügbare Breite. Der frühere
Schalter **Volle Breite** und die Begrenzung auf 820 logische Pixel entfallen.
Drei Schalter wählen **Links**, **Mittig** oder **Rechts** für die gerenderten
Überschriften, Absätze und Listen innerhalb dieser vollen Fläche.

Dies ist eine lokale Anzeigeeinstellung, keine Markdown-Formatänderung. Code
bleibt links ausgerichtet; Tabellen behalten ihre eigenen Spaltenausrichtungen
aus der Quelle. Die Wahl wird für den nächsten Editor/Neustart gespeichert,
schreibt keine Dokumentrevision und gilt ebenso im Asset-Menü. Die alte lokale
Einstellung `full` wird als links interpretiert. MD und Code bleiben voll breit.

## Unterstützte Formen und bewusste Grenzen

Die Darstellung verwendet Qts GitHub-Markdown-Dialekt: Überschriften, Absätze,
Hervorhebungen, Durchstreichen, verschachtelte Listen, Aufgabenlisten, Tabellen,
Zitate, Trennlinien, Links und Codeblöcke. Referenzlinks bleiben auch zwischen
getrennt angezeigten Blöcken auflösbar. Codeblöcke werden als Code dargestellt,
nicht ausgeführt; eine sprachabhängige Syntaxfärbung ist kein Bestandteil.

„Markdown“ hat keinen einzigen vollständigen Standard für sämtliche Erweiterungen.
Mermaid, LaTeX-Mathematik, Fußnoten-Erweiterungen und ausführbares HTML werden
nicht als zusätzliche Interpreter eingebaut. Nicht unterstützte Syntax bleibt
im Originaltext erhalten. HTML/Skripte werden nicht ausgeführt; lokale und
entfernte Bilder werden nicht automatisch geladen. Weblinks verlangen vor dem
Öffnen eine Bestätigung. Anhänge bleiben über die bestehenden sicheren
Dokumentationsaktionen erreichbar, nicht über automatisch geladene Ressourcen.

Der bestehende Markdown-Grenzwert bleibt 1 MiB. Über 200 Blöcken wird eine
zusammenhängende Fläche verwendet, damit große Dokumente nicht Tausende
Qt-Widgets erzeugen. Dabei wird beim Anklicken die gesamte Quelle bearbeitet.
Tabellen mit uneindeutigen überzähligen Zellen, mehr als 50 Spalten oder mehr
als 3.000 Zellen einschließlich Trennerzeile werden nicht automatisch zu
Zellenwidgets umgebaut. Sie bleiben vollständig über **Code** bearbeitbar;
es werden keine Zellen stillschweigend entfernt.

## Daten und Abhängigkeit

`markdown-it-py==4.0.0` ist eine versioniert gebundene GUI-Abhängigkeit für
Quelltextpositionen; Qt übernimmt die Darstellung. Die `[gui]`-Installation
installiert sie mit. Es gibt keine Konvertierung zurück aus Rich Text:
Im MD-Modus werden nur tatsächlich bearbeitete Quelltextblöcke ersetzt;
im Code-Modus wird unmittelbar die gesamte Quelle bearbeitet. Metadaten und
Referenzen werden nicht aus der gerenderten Ansicht zurückgewonnen.

Hauptfenster und **Asset-Menü → Dokumentation → Dokumente & Anhänge** verwenden
denselben Editor und dieselben Dokument-IDs. Generierte Berichte bleiben
schreibgeschützt. Notizen werden weiterhin ausschließlich im Notiz-Dashboard
bearbeitet. Die Trennung benötigt keine Katalogmigration.
