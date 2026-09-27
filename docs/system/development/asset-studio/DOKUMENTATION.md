# Dokumentation direkt im Markdown-Bereich

[Asset Studio](index.md) · [Aktuelles Bedienbriefing](SICHTPRUEFUNG_INHALTE.md)

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
- Obere Spaltenleiste bzw. linke Zeilenleiste anklicken: ganze Spalte/Zeile
  auswählen. Leiste ziehen: komplette Spalte/Zeile umordnen. Die Kopfzeile
  bleibt oben; die Links-/Mitte-/Rechtsausrichtung einer Spalte wandert mit.
- `+` an jeder Leiste fügt danach eine Spalte/Zeile ein. Rechts ergänzt `+`
  eine letzte Spalte, unten **+ Zeile** eine letzte Datenzeile.
- **Spalten entfernen / Zeilen entfernen** löscht die vollständige Auswahl.
  Kopfzeile und letzte Spalte sind geschützt. Mehrfachauswahl ist mit Strg möglich.
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

## Breite und Ausrichtung der Dokumentationsfläche

Vier Schalter über dem Dokument wählen **Links**, **Mittig**, **Rechts** oder
**Volle Breite**. Die ersten drei verwenden eine Lesebreite von höchstens 820
logischen Pixeln, begrenzt durch den verfügbaren Platz. Volle Breite nutzt den
gesamten Dokumentationsbereich; kein Betriebssystem-Vollbildmodus.

Dies richtet die Inhaltsfläche aus, nicht einzelne Markdown-Absätze. Die Wahl
wird lokal für den nächsten Editor/Neustart gespeichert, schreibt keine
Dokumentrevision und gilt ebenso für den Code-Modus und das Asset-Menü.

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
