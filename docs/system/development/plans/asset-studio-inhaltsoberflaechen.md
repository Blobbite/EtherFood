# Asset Studio: direkte Inhaltsbearbeitung und Canvas-Bedienung

[Asset Studio](../asset-studio/index.md)

## Zweck und Gesamtbild

Den Bedienbericht nach Paket 7 umsetzen. Notizen werden direkt auf Post-its
bearbeitet, Dokumentation erhält eine gemeinsame Markdown-Einzelansicht und
Aufgaben zeigen ihre To-dos rechts neben dem Kanban. Dieselben Dienste und
Editoren gelten im Asset-Menü. Der Szeneneditor und T019/T020 bleiben außerhalb
dieses Zwischenpakets; T017/T018 werden nicht ohne Benutzerabnahme geschlossen.

## Ausgangslage

Notiz-Karten aus älteren Projekten sind Container ohne automatisch sichtbares
Notizdokument. Der Notiz-Editor liegt bisher unter der Kartenliste und bietet
Anhänge. Dokumentation besitzt Quelltext und Vorschau nebeneinander. Aufgaben
zeigen unabhängig vom Status einen grünen Haken; das Asset-Menü verwendet noch
eine flache Aufgabenliste. Canvas-Verbindungen enden bislang nur an vorhandenen
Karten, und Anordnung betrifft immer das gesamte Projekt.

## Umfang und Nicht-Ziele

- Post-its fester Größe, direktes Schreiben, automatische revisionierte
  Speicherung, Rechtsklick für Farbe/Anheften. Leerer Bereich zeigt eine gelbe
  Schreibkarte; bloßes Öffnen legt keinen Datensatz an. Neue Texte maximal
  100 Wörter; vorhandene längere Texte und alte Anhänge bleiben erhalten.
- Ein Markdown-Bereich: gerenderte Blöcke, beim Anklicken Quelltext direkt an
  derselben Stelle; Kontextaktionen für Tabelle, Code, Überschriften und Listen.
  CommonMark/GFM-Grundformen einschließlich Tabellen, durchgestrichenem Text,
  Aufgabenlisten und Code. Kein HTML-/Skriptstart oder automatisches Nachladen
  externer/lokaler Bilder. Original-Markdown bleibt maßgeblich.
- Vier kompakte Kanban-Spalten links, festes Detailpanel mit To-dos oben und
  Zusatzinformationen darunter rechts. Offen: offener Kreis, In Arbeit: blauer
  Punkt, Blockiert: X, Erledigt: grüner Haken. Issues tragen zusätzlich ein
  Ausrufezeichen. Dieselben Symbole im Canvas, Baum und in Listen.
- Leerer Canvas-Verbindungsendpunkt bietet passende neue Inhalte/Karten an;
  Anlegen und Zuordnen sind atomar und rückgängig machbar. Zulässige Hierarchie,
  Abbruch und Zyklenschutz bleiben bestehen. Ausgewählte Karten lassen sich
  als Kreis oder Linie anordnen; andere Karten bleiben unberührt.
- Asset-Menü verwendet denselben Dokumenteditor und dieselben Post-its, dort
  untereinander. Aufgaben/Issues stehen in vier schlanken, aufklappbaren
  Statusgruppen und lassen sich zwischen diesen ziehen.

Keine Datenlöschung, keine zweite Inhaltsdatenbank, keine automatische Freigabe.
Bestehende fremde Arbeitsbaumänderungen bleiben unangetastet.

## Schritte und Fortschritt

- [x] Bestand, Routing, Datenverträge und vorhandene GUI-Tests prüfen.
- [x] Notizkarten und sicheres Speichern inklusive leerer Altcontainer umsetzen.
- [x] Gemeinsame Markdown-Einzelansicht und Kontextaktionen implementieren.
- [x] Kanban, Statusicons und kompakte Asset-Aufgaben vereinheitlichen.
- [x] Canvas-Erstellung am Endpunkt und ausgewählte Anordnungen ergänzen.
- [x] Integrations-, Regressions- und reale Qt-Ereignistests durchführen.
- [x] Dokumentation und Bedienbriefing ergänzen.
- [x] Eigenen Commitumfang geprüft und Abschlussübergabe vorbereitet.

## Erkenntnisse und Entscheidungen

Die Notizgrenze betrifft neue/geänderte Texte, nicht das Laden alter Projekte.
Lange Alttexte werden weder abgeschnitten noch automatisch umgeschrieben.
Filter dürfen Entwürfe nicht verlieren. Gemeinsame Views verwenden dieselben
IDs und Revisionsprüfungen. Statuswechsel erfüllen weiterhin To-do- und
Abnahmebedingungen; ein anderes Icon ersetzt keine fachliche Prüfung.

Für quelltexttreue Markdown-Blockgrenzen wurde `markdown-it-py==4.0.0` als kleine,
versioniert gebundene GUI-Abhängigkeit geprüft und eingebunden; Qt übernimmt die sichere
Darstellung. Keine Konvertierung des gesamten Dokuments zurück aus Rich Text.
Referenzen: [Parser-Dokumentation](https://markdown-it-py.readthedocs.io/en/latest/using.html),
[Paketquelle](https://pypi.org/project/markdown-it-py/4.0.0/),
[Qt-Markdown](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QTextDocument.html).

## Prüfungen

Am 27.09.2026 ausgeführt:

- `pytest tools/AssetManager/tests -q`: 343 bestanden, einschließlich echter
  Qt-Ereignisse mit `QT_QPA_PLATFORM=offscreen`. Die schon vorhandenen lokalen
  Qt-Bibliotheken wurden ausschließlich über einen Sitzungs-Library-Pfad eingebunden.
- Gezielte neue Tests: leere Altcontainer über vier Einstiege, Autospeicherung,
  Wortgrenze/Alttexte/Altanhänge, Entwürfe bei Filtern und Konflikten, Markdown-
  Blockgrenzen/Referenzlinks/Tabellen/Undo/Neustart/Leseschutz, kompakte Statusdrops,
  gleiche Icons in mehreren Ansichten, Canvas-Neuanlage/Abbruch/Atomarität,
  Mehrfachziehen/Anordnen/Undo bei Zoom 0,3, 1 und 2,5.
- Stilprüfung für 118 Studio-Quelltext- und Testdateien, `pip check` sowie
  `git diff --check` bestanden.
- Vier synthetische Qt-Screenshots geprüft: Post-its, Markdown, Haupt-Kanban und
  kompakte Asset-Aufgaben. Keine Benutzer-Sichtabnahme daraus abgeleitet.
- Vorhandene, noch ungetrackte Control-Testdatei nur um die neue Parser-Version
  in ihrer Paket-Testfixture ergänzt: 56 Control-Tests bestanden. Dieser lokale
  Anschluss verbleibt bei der bereits vorhandenen Control-Arbeit; sie wird nicht
  als vollständiges Fremdpaket in den UI-Commit aufgenommen.
- `python tools/control.py check` über den vorhandenen `.venv`-Interpreter
  ausgeführt: nicht bestanden (Godot fehlt, 1907 Stilbefunde außerhalb des
  Studio-Quelltexts, weitere Repo-Testbefunde). Nach Parser-Fixturekorrektur:
  `pytest tools/tests -q --tb=line` = 258 bestanden, 37 übersprungen, drei Fehler
  (Godot-Fenstervertrag, fehlende Entscheidungsdokumente, 13 Dokumentationslinks).

Die neue Abhängigkeit erforderte genau eine Ergänzung der bereits vorhandenen
Control-Testfixture; der reale Control-Paketcheck liest die Manifestpins bereits
dynamisch. Die übrigen bestehenden Arbeitsbaumänderungen wurden nicht bearbeitet.

## Wiederholbarkeit und Wiederherstellung

Originaldaten bleiben im bestehenden Katalog; keine pauschale Migration und
kein Entfernen alter Anhänge. Neue Funktionen verwenden Transaktionen und
Revisionskontrolle. UI-/Markdown-Entwürfe bleiben bei Fehlern sichtbar. Canvas-
Anordnung verändert ausschließlich Layoutdaten und bleibt rückgängig machbar.
Für Tests werden ausschließlich temporäre synthetische Projekte verwendet.

## Ergebnis und Rückblick

Die fünf UI-Bereiche sind umgesetzt; die persönliche Prüfung steht unter
[Briefing Inhaltsoberflächen](../asset-studio/SICHTPRUEFUNG_INHALTE.md).
Notiz-Sammelcontainer erzeugen beim Öffnen nur eine sichtbare Schreibfläche,
keinen leeren Katalogeintrag. Alte Anhänge werden weder angezeigt noch gelöscht.
Markdown bewahrt Originalquelle statt Rich-Text-Rückkonvertierung; nicht
unterstützte Dialekterweiterungen bleiben als Quelle erhalten.

Erkenntnisse aus den Ereignistests: Erneutes Anwählen derselben Notiz darf keinen
Entwurf verwerfen; mehrere Canvas-Auswahlsignale dürfen die Mehrfachauswahl nicht
zurücksetzen. Qt-Untermenüs brauchen explizite Elternbindung. Quelltext-Tastendrücke
werden direkt behandelt, um rekursive Weiterleitung zwischen Elterneditor und
Kindwidget zu vermeiden. Alle vier Punkte sind durch Regressionstests abgesichert.

T017/T018 und spätere Pakete werden mit diesem Ergebnis nicht abgenommen oder
geschlossen. Produktive Bildverarbeitung und Szeneneditor bleiben ausdrücklich offen.
