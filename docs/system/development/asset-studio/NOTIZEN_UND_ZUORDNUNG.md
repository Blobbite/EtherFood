# Projektbaum, Inhaltssymbole und Notizen

Zwischenpaket 6c ergänzt die abgenommene Aufgabenverwaltung. Reiterfolge:
**Projekt-Canvas → Aufgaben-Kanban → Notizen → Dokumentation & Anhänge → Suche**.
Aufgaben bleiben im Kanban; die kleinen Symbole sind eine zusätzliche Ansicht
im Projekt-Canvas. Es entstehen keine Kopien von Aufgaben oder Dokumenten.

## Zuordnung im Projekt- und Verwendungsbaum

Die bisherige Hierarchie-Auswahlliste entfällt. Direkt auf eine Zielkarte ziehen:

| Gezogener Eintrag | Wirkung |
| --- | --- |
| Originalkarte | Verschiebt den Eigentümer innerhalb der zulässigen Hierarchie. |
| Aufgabe, Issue, manuelles Dokument oder Notiz | Ordnet denselben Inhalt einer anderen aktiven Karte zu. |
| Verwendungs-Verweis | Verschiebt nur diese Verwendung; das Original behält seinen Eigentümer. |
| Asset/Paket mit gedrückter Strg-Taste | Fügt eine Verwendung hinzu, ohne das Original zu verschieben. |

Ein zulässiges Ziel erhält einen blauen Rahmen. Beim kurzen Verweilen klappt es
auf; am oberen/unteren Baumrand wird gescrollt. Ablegen zwischen Einträgen
sortiert keine Geschwister: Entscheidend ist die Zielkarte selbst. Anhänge,
Quellen und externe Verzeichnisse werden dabei weder verschoben noch kopiert.

**Strg+Z / Strg+Umschalt+Z** nehmen Zuordnungen und Verwendungen zurück bzw.
stellen sie wieder her. Zwischenzeitliche Textänderungen bleiben erhalten.
Selbst-/Kreisbezüge, ungültige Hierarchieebenen, doppelte Verwendungen,
archivierte Zweige und veraltete Bearbeitungsstände werden zurückgewiesen.
Ein manuelles Dokument darf am Ziel keinen bereits vergebenen Titel verdrängen;
generierte Berichte sind nicht frei umhängbar. Ungespeicherte Dokumente lösen
vor dem Ziehen den vorhandenen Speichern/Verwerfen/Abbrechen-Dialog aus.

Die Beziehungen **Verwendung** und **Abhängigkeit** bleiben über ihre bisherigen
Werkzeuge erreichbar. Im Canvas lassen sich Eigentümer weiterhin über die
Pfeilziele ändern; bei Inhaltssymbolen gilt dieselbe Prüfung wie im Baum.

## Kleine Symbole im Projekt-Canvas

Aufgaben, Issues, Notizen und seit 6d auch Dokumentation erscheinen als kompakte
Icon-Karten mit kurzem Titel und vollständigem Tooltip. Ihre Besitzerverbindungen werden aus der
vorhandenen Zuordnung abgeleitet. Ein Doppelklick öffnet eine Aufgabe im
Kanban-Editor bzw. Dokumentation im Dokumenteditor. Bei Notizen genügt ein
einfacher Klick: Sie öffnen ausschließlich im Notiz-Dashboard.
Auswahl verändert nicht den Zoom. Dokumentation besitzt einen violetten
Hintergrund und ein passendes Seitensymbol; generierte Berichte bleiben nur lesbar
und können nicht frei einer anderen Karte zugeordnet werden.

Die Symbole lassen sich verschieben und besitzen Anschlussstellen, aber keinen
Größengriff. Neue automatische Positionen meiden bestehende Karten. Gespeicherte
Positionen bleiben erhalten. Einklappen oder Archivieren des Eigentümerzweigs
blendet auch seine Inhalte aus. Alte Notiz-Karten bleiben kleine Sammelcontainer;
ein Doppelklick zeigt ihre enthaltenen Notizdokumente im Dashboard.

Assets erhalten einen blauen Würfel, Notizen ein gelbes Haftnotizsymbol und
Dokumentation ein violettes Blatt. Aufgaben zeigen ihren gespeicherten Status:
offener Kreis (Offen), blauer Punkt (In Arbeit), rotes X (Blockiert), kräftiger
grüner Haken (Erledigt). Issues besitzen zusätzlich ein gelbes Ausrufezeichen.
Die Symbole stimmen mit Baum, Suche und Kanban überein. Sie werden in Qt
gezeichnet; zusätzliche Bilddateien oder Schriftfonts sind nicht nötig.

Eine Anschlussstelle auf freie Canvas-Fläche ziehen bietet **Notiz,
Dokumentation, Aufgabe, Issue** sowie hierarchisch passende **Assets,
Ordner/Pakete, Kapitel oder Akte** an. Der Menü-Kopf nennt den Eigentümer.
Von einem Inhaltssymbol aus entstehen Geschwister unter dessen Eigentümer,
keine erfundene Unterhierarchie innerhalb eines Dokuments. Anlegen, Zuordnung
und Position sind ein rückgängig machbarer Schritt. Abbruch verändert nichts;
beim Umhängen einer bestehenden Verbindung auf freie Fläche entsteht keine Karte.
Neue Assets erhalten die bisherigen Standardanforderungen, anpassbar im Asset-Menü.

**Strg+Klick** oder ein Auswahlrahmen markiert mehrere Karten. Rechtsklick auf
die Ankerkarte → **Auswahl anordnen → Kreis / Linie** ordnet die ausgewählten
Nachbarkarten an. Die Ankerkarte und nicht ausgewählte Karten bleiben stehen;
die Auswahl kann auch gemeinsam verschoben werden. **Strg+Z** nimmt den ganzen
Layoutschritt zurück. Verschieben der Ansicht bleibt auf der mittleren Maustaste.

## Dokumentation anlegen und importieren

**Dokumentation & Anhänge → + Dokumentation** erstellt ein Dokument mit der
neutralen Vorlage Dokumentation oder einer anderen Dokumentvorlage. Freie Notiz
und Testnotiz werden hier nicht angeboten; diese bleiben über das Notiz-Dashboard
bzw. **Neue Notiz** im Kontextmenü verfügbar. Im Asset-Menü heißt der gleiche
Unterreiter **Dokumente & Anhänge** und bietet denselben Dokumentationsbutton.

**Markdown importieren** bleibt bestehen. Neue Importe zählen als Dokumentation;
Quelltext (auch leerer Inhalt), Originaldatei und Herkunft bleiben erhalten.
Ein ausdrücklicher Revisionsimport in eine vorhandene Notiz oder Dokumentation
behält deren Typ, ID und Anhänge. Bestehende Notizen und frühere Importe werden
nicht rückwirkend umklassifiziert. Die Dokumentauswahl blendet Notizen aus;
deren Text wird direkt auf den Notizkarten bearbeitet. Alte Anhänge bleiben
im Katalog erhalten; das Notiz-Dashboard bietet keine Anhangsaktionen mehr.
Die neue [Markdown-Einzelansicht](DOKUMENTATION.md) gilt für Dokumentation
im Hauptfenster und Asset-Menü.

## Post-its im Notiz-Dashboard

Das Dashboard zeigt vorhandene manuelle Dokumente der Vorlagen **Freie Notiz**
und **Testnotiz**. Andere Dokumentvorlagen und generierte Berichte bleiben in
der Dokumentation. Alte freie Notizen ohne explizite Vorlage bleiben lesbar.

- Ein leerer Bereich, auch eine alte leere Notiz-Sammelkarte, zeigt sofort
  eine gelbe Schreibkarte. Bloßes Öffnen schreibt noch keinen Datensatz.
  **+ Notiz** bietet eine weitere leere Karte an; Titel und Text werden direkt
  in der 320 × 270 Pixel großen Karte bearbeitet. Es gibt keinen unteren
  Zweiteditor, keine separate Vorschau und keine Anhangsschaltflächen.
- Neue/geänderte Notiztexte sind auf **100 Wörter** begrenzt. Zähler und
  Speicherzustand stehen in der Karte. Überlange Entwürfe bleiben sichtbar,
  werden aber nicht gespeichert. Längere Texte gehören in die Dokumentation.
  Bestehende lange Notizen werden niemals abgeschnitten; Farbe, Titel und
  Anheften lassen sich bei unverändertem Alttext weiterhin speichern.
- Rechtsklick bietet sechs Farben und **Oben anheften** an. Im Asset-Menü
  werden dieselben bearbeitbaren Notizkarten untereinander angezeigt.
- Das Dashboard ist eine warme, farbige **Pinnwand**. Auch die Schreibfelder
  verwenden die jeweilige Notizfarbe; sie sind keine weißen Kästen.
  An der oberen **Verschieben**-Leiste lassen sich Karten frei platzieren,
  auch überlappend. Textfelder bleiben zum Schreiben und Markieren da.
  Die Position wird beim Loslassen automatisch im Projekt gespeichert.
  **Esc** bricht einen laufenden Zug ab. Bei einem Schreibfehler wird die
  vorherige Position wiederhergestellt und eine Fehlermeldung angezeigt.
- Filter, Fenstergröße, Titel-/Farbwechsel und Neustart ordnen gespeicherte
  Positionen nicht neu. Der Bereich ist scrollbar und bietet Platz hinter der
  letzten Karte. Die Canvas-Position des Notizsymbols bleibt unabhängig davon.
  Eine noch leere Schreibkarte behält ihren gewählten Platz während des
  Arbeitens und speichert ihn zusammen mit ihrem ersten Inhalt.
- Anheften bestimmt die Reihenfolge in der gestapelten Asset-Ansicht und bei
  der ersten Standardanordnung; bereits platzierte Pinnwand-Karten springen
  dadurch nicht um. Die Farbe ist unabhängig von Aufgabenstatus oder Asset-Freigabe.
- Bereich und Herkunft bleiben sichtbar. Text-/Farbfilter sowie **Gesamtes
  Projekt** helfen bei größeren Sammlungen. Akt/Kapitel berücksichtigen auch
  verwendete Assets/Pakete und deren Unterkarten, ohne doppelte Notizen.
- Nach etwa 0,9 Sekunden Schreibpause wird revisioniert gespeichert.
  **Strg+S** oder **Jetzt speichern** im Kontextmenü speichert sofort.
  Baum, Canvas, Suche und Kontextmenü öffnen denselben Datensatz im Dashboard.
  Im Asset-Menü gibt es dafür einen eigenen Unterreiter **Notizen**.
- Abbrechen/Schließen mit geändertem Text fragt nach Speichern oder Verwerfen.
  Das gilt auch beim Wechseln der Notiz, des Bereichs oder des Projekts.
  Revisionskonflikte überschreiben keine andere Fassung und behalten den Entwurf.

`note_color` und `note_pinned` sind optionale Darstellungsfelder im bestehenden
Dokumentdatensatz. Fehlende Werte entsprechen Gelb und nicht angeheftet.
Katalogöffnung validiert die Werte; eine Datenmigration ist nicht nötig.
Pinnwand-Koordinaten liegen als optionales `note_board: {x, y}` im vorhandenen
Layoutdatensatz der Notiz. Sie gehören zum Projekt und zum Metadatensnapshot,
nicht zur lokalen Rechnerkonfiguration. Verschieben erzeugt keine Textrevision
und überschreibt weder Textentwürfe noch die getrennten Canvas-Koordinaten.
Auch Rückgängig/Wiederholen einer Canvas-Anordnung erhält neuere Pinnwand-Positionen.
Die kompakte Asset-Ansicht verändert diese Pinnwand-Anordnung nicht.

Keine Bildpipeline, Godot-Ausgabe oder Asset-Freigabe wurde ergänzt.
[Ergänzende Nachprüfung Dokumentation/Icons](SICHTPRUEFUNG_6D.md) ·
[Kurze Nachprüfung](SICHTPRUEFUNG_6C.md) · [Ergebnisbericht](task-results/6c.md) ·
[Arbeitsplan](../plans/asset-studio-notizen-und-zuordnung.md)
