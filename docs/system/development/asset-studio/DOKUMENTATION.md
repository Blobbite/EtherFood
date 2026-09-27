# Dokumentation direkt im Markdown-Bereich

[Asset Studio](index.md) · [Aktuelles Bedienbriefing](SICHTPRUEFUNG_INHALTE.md)

Dokumentation zeigt nur noch eine Inhaltsfläche, nicht Quelltext und Vorschau
nebeneinander. Einen gerenderten Absatz, eine Überschrift, Tabelle oder einen
Codeblock anklicken: An derselben Stelle erscheint der bearbeitbare Markdown-
Quelltext dieses Blocks. Überschriften behalten dabei ihre Darstellungsgröße;
die `#`-Zeichen werden sichtbar. Beim Verlassen wird wieder gerendert.

**Rechtsklick** bietet Überschrift, Tabelle, Codeblock, Liste, Aufgabenliste,
Zitat und Link an. Bei Tabellen werden Spalten und Datenzeilen abgefragt.
Neue Blöcke werden hinter dem angeklickten Block eingefügt. Für Änderungen
über Blockgrenzen hinweg gibt es im selben Menü **Gesamten Markdown-Quelltext
bearbeiten**. Die Gesamtquelle erscheint ebenfalls in derselben Fläche.
**Speichern / Strg+S** schreibt eine Revision; ungespeicherte Dokumente behalten
den bisherigen Speichern/Verwerfen/Abbrechen-Schutz. Anders als Post-its werden
Dokumente nicht automatisch gespeichert.

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

## Daten und Abhängigkeit

`markdown-it-py==4.0.0` ist eine versioniert gebundene GUI-Abhängigkeit für
Quelltextpositionen; Qt übernimmt die Darstellung. Die `[gui]`-Installation
installiert sie mit. Es gibt keine Konvertierung zurück aus Rich Text:
Nur tatsächlich bearbeitete Quelltextblöcke werden ersetzt. Unbearbeitete
Markdown-Bereiche, Referenzen und Metadaten bleiben erhalten.

Hauptfenster und **Asset-Menü → Dokumentation → Dokumente & Anhänge** verwenden
denselben Editor und dieselben Dokument-IDs. Generierte Berichte bleiben
schreibgeschützt. Notizen werden weiterhin ausschließlich im Notiz-Dashboard
bearbeitet. Die Trennung benötigt keine Katalogmigration.
