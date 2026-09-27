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
Dokumentation ein violettes Blatt. Aufgaben zeigen einen kräftigen grünen Haken
ohne Rahmen oder Hintergrund. Der Haken kennzeichnet den Typ Aufgabe, nicht
deren Erledigungsstatus. Alle vier Icons werden in Qt gezeichnet; keine
zusätzlichen Bilddateien oder Schriftfonts sind nötig.

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
deren Markdown und Anhänge werden direkt im Notiz-Dashboard bearbeitet.

## Post-its im Notiz-Dashboard

Das Dashboard zeigt vorhandene manuelle Dokumente der Vorlagen **Freie Notiz**
und **Testnotiz**. Andere Dokumentvorlagen und generierte Berichte bleiben in
der Dokumentation. Alte freie Notizen ohne explizite Vorlage bleiben lesbar.

- **+ Notiz** erstellt einen Eintrag an der ausgewählten Karte. Ein Klick auf
  ein Post-it lädt darunter den eingebetteten Editor mit Titel, Markdown,
  Vorschau, sechs Farben, **Oben anheften** und Anhängen. Doppelklick oder
  **Notiz bearbeiten** fokussiert diesen Editor, ohne Reiterwechsel.
- Angeheftete Notizen stehen zuerst, danach wird nach Titel sortiert. Die Farbe
  ist unabhängig von Aufgabenstatus oder Asset-Freigabe.
- Bereich und Herkunft bleiben sichtbar. Text-/Farbfilter sowie **Gesamtes
  Projekt** helfen bei größeren Sammlungen. Akt/Kapitel berücksichtigen auch
  verwendete Assets/Pakete und deren Unterkarten, ohne doppelte Notizen.
- **Speichern** oder **Strg+S** speichert die aktive Notiz revisioniert.
  Baum, Canvas, Suche und Kontextmenü öffnen denselben Datensatz im Dashboard.
  Im Asset-Menü gibt es dafür einen eigenen Unterreiter **Notizen**.
- Abbrechen/Schließen mit geändertem Text fragt nach Speichern oder Verwerfen.
  Das gilt auch beim Wechseln der Notiz, des Bereichs oder des Projekts.
  Revisionskonflikte überschreiben keine andere Fassung und behalten den Entwurf.

`note_color` und `note_pinned` sind optionale Darstellungsfelder im bestehenden
Dokumentdatensatz. Fehlende Werte entsprechen Gelb und nicht angeheftet.
Katalogöffnung validiert die Werte; eine Datenmigration ist nicht nötig.

Keine Bildpipeline, Godot-Ausgabe oder Asset-Freigabe wurde ergänzt.
[Ergänzende Nachprüfung Dokumentation/Icons](SICHTPRUEFUNG_6D.md) ·
[Kurze Nachprüfung](SICHTPRUEFUNG_6C.md) · [Ergebnisbericht](task-results/6c.md) ·
[Arbeitsplan](../plans/asset-studio-notizen-und-zuordnung.md)
