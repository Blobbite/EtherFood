# Briefing: Nachprüfung von Zwischenpaket 4a

Stand: 2026-09-26. Nachbesserungen aus der ersten Sichtprüfung, zu
[#56](https://github.com/Blobbite/EtherFood/issues/56),
[#57](https://github.com/Blobbite/EtherFood/issues/57),
[#58](https://github.com/Blobbite/EtherFood/issues/58) und
[#59](https://github.com/Blobbite/EtherFood/issues/59).
Technisch umgesetzt und vom Benutzer vollständig abgenommen: Rückmeldung
„1 bis 8 sind alle check keine Mängel“ am 26.09.2026. Issues #56–#59 abgeschlossen.

## Vorbereitung

Studio vollständig schließen und mit `python3 tools/control.py asset-manager run`
neu starten. Ein Testprojekt verwenden; bei Bedarf eine synthetische Demo anlegen.
Keine Originalgrafiken importieren oder verschieben. Die Prüfungen betreffen
Verwaltungsdaten und Ansichten, nicht die Freigabe von Spielassets.

## Kleine Checkliste

1. **Aufgaben und Issues lesen/bearbeiten:** Unter „Aufgaben & Suche“ einen Eintrag
   anklicken. Beschreibung, Status, Zuständigkeit, Priorität und gegebenenfalls
   Fundstelle müssen rechts sichtbar sein. Über „Bearbeiten / Öffnen“ oder
   Doppelklick Text und Titel ändern, speichern, erneut öffnen. „Abbrechen“ bietet
   Speichern/Verwerfen/Abbrechen. Inhaltsänderungen heben eine alte Aufgabenabnahme
   auf; eine abnahmepflichtige erledigte Aufgabe wird wieder offen.
2. **Rechtsklick und Notizen:** Im Baum und auf einer Canvas-Karte Rechtsklick →
   „Neue Notiz“. Text schreiben, speichern. Im Baum öffnen und per Rechtsklick
   umbenennen. Der Inhalt muss erhalten bleiben. Mit ungespeichertem Text auf einen
   anderen Inhalt wechseln und „Abbrechen“ wählen: Der Entwurf bleibt sichtbar.
3. **Typicons:** Notizkarte, Dokument, Aufgabe und Issue müssen anhand von Symbol
   und Klartext unterscheidbar sein. Baum, Suchergebnisse, Typfilter und Canvas
   verwenden passende Symbole. Freie Labels/Tags sind noch nicht enthalten.
4. **Kartengröße:** Unten rechts am ◢-Griff ziehen. Breite und Höhe müssen folgen.
   Karte verschieben, mit Strg+Z rückgängig und Strg+Umschalt+Z wiederholen.
   Das verändert die Ansicht, nicht eine Asset- oder Pipelinefreigabe.
5. **Verbindungen:** Von einem der vier Kreise auf eine andere Karte ziehen und
   den Typ ausdrücklich wählen. „Verwendet“ verknüpft ein vorhandenes Asset/Paket;
   „Benötigt“ ist eine Voraussetzung; „Gehört zu“ ordnet die Startkarte der Zielkarte
   als Elternort zu. Eine Linie oder ihre Beschriftung anklicken und den gelben
   Endpunkt auf eine andere Karte ziehen. Bei Hierarchien ist nur das Eltern-Ziel
   umhängbar. Undo/Redo und Abbruch prüfen. Eine Voraussetzung A → B → A sowie
   Selbstbezüge müssen abgelehnt werden, ohne vorhandene Verbindungen zu verlieren.
6. **Lesbare Linienbeschriftungen:** Karten so verschieben, dass Linien kreuzen;
   auch zoomen und Größen ändern. Text darf nicht von einer Linie durchgestrichen
   werden. Bei dichtem Layout werden Striche unter dem Text ausgespart. Der Tooltip
   nennt Start und Ziel; ein Klick hebt die betreffende Verbindung hervor.
7. **Gemeinsame Assets und Status:** Beim Demo-Helden beide Kapitelverweise `↪`
   anklicken: Rechts muss dieselbe ID stehen. Unter „Eigentümer / Herkunft“ und
   „Verwendet in …“ müssen Originalort und beide Kapitel erscheinen. Zusätzlich
   kann eine neue Asset-Karte unter „Projektweit“ angelegt und über Rechtsklick auf
   beide Kapitel → „Vorhandenes Asset verwenden“ verknüpft werden. Keine Kopien.
   Rechts oben steht der deutsche Status mit Grund. Eine fehlende Quelle und eine
   fehlende Sichtabnahme dürfen nicht als erfolgreich angezeigt werden.
8. **Neustart:** App schließen, Projekt wieder öffnen. Texte, Umbenennungen,
   Kartengrößen, Positionen und Verwendungen müssen erhalten bleiben. Die Undo-
   Historie selbst ist sitzungsbezogen und wird nicht über Neustarts fortgesetzt.

Bitte Rückmeldung mit Nummern: `✅ 1–4, 7–8`; bei Problemen etwa
`❗ 5: Endpunkt lässt sich nicht greifen, Schritte …` und möglichst Screenshot.
Diese Prüfliste ist vollständig abgenommen; Paket 5 wurde anschließend freigegeben.

## Abgrenzung und technische Nachweise

🔹 Später: echte Bild-/Spritesheetimporte, Asset-spezifische Menüs, Pipelinejobs,
Maskenbearbeitung, Vorschau, Godot-Bereitstellung und produktive Freigabe. Eine
gemeinsam verwendete **Katalogkarte** ist noch kein importiertes Grafikasset.
Freie Tags/Labels sind separat zu planen; es gibt hier keine versteckte Umsetzung.

✅ `python3 tools/control.py asset-manager check`: 71 Studio-Tests einschließlich
Qt-GUI-Tests und 171 bestehende Pipeline-Tests bestanden. Qt wurde im Container
mit temporär bereitgestellten Systembibliotheken und ohne Display ausgeführt.
45 Studio-Quell-/Testdateien ohne Stilbefund; synthetische Screenshots geprüft.
Das ersetzt keine Sichtabnahme auf dem Benutzerrechner.

❗ `python3 tools/control.py check` ist nicht vollständig grün: Godot 4 fehlt in
dieser Sitzung; zwei bestehende Dokumentationsprüfungen scheitern an fehlenden
Spielentscheidungsdateien/13 defekten Verweisen; außerdem bestehen geerbte
Stilbefunde außerhalb der Studio-Änderungen. Python-Standardtests:
257 bestanden, 37 übersprungen, 2 fehlgeschlagen. Diese Probleme wurden nicht als
behoben ausgegeben und nicht durch Änderungen am Spielkanon verdeckt.

[Arbeitsplan und Verlauf](../plans/asset-studio-paket-4a.md)
