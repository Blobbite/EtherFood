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

Aufgaben, Issues und Notizen erscheinen als kompakte Icon-Karten mit kurzem
Titel und vollständigem Tooltip. Ihre Besitzerverbindungen werden aus der
vorhandenen Zuordnung abgeleitet. Ein Doppelklick öffnet eine Aufgabe im
Kanban-Editor bzw. die Notiz im Notiz-Dashboard. Auswahl verändert nicht den Zoom.

Die Symbole lassen sich verschieben und besitzen Anschlussstellen, aber keinen
Größengriff. Neue automatische Positionen meiden bestehende Karten. Gespeicherte
Positionen bleiben erhalten. Einklappen oder Archivieren des Eigentümerzweigs
blendet auch seine Inhalte aus. Alte Notiz-Karten bleiben kleine Sammelcontainer;
ein Doppelklick zeigt ihre enthaltenen Notizdokumente im Dashboard.

Assets erhalten einen blauen Würfel, Notizen ein gelbes Haftnotizsymbol. Beide
Icons werden in Qt gezeichnet; keine zusätzlichen Bilddateien oder Schriftfonts
sind nötig.

## Post-its im Notiz-Dashboard

Das Dashboard zeigt vorhandene manuelle Dokumente der Vorlagen **Freie Notiz**
und **Testnotiz**. Andere Dokumentvorlagen und generierte Berichte bleiben in
der Dokumentation. Alte freie Notizen ohne explizite Vorlage bleiben lesbar.

- **+ Notiz** erstellt einen Eintrag an der ausgewählten Karte. Doppelklick
  oder **Notiz bearbeiten** öffnet Titel, Text, sechs Farben und **Oben anheften**.
- Angeheftete Notizen stehen zuerst, danach wird nach Titel sortiert. Die Farbe
  ist unabhängig von Aufgabenstatus oder Asset-Freigabe.
- Bereich und Herkunft bleiben sichtbar. Text-/Farbfilter sowie **Gesamtes
  Projekt** helfen bei größeren Sammlungen. Akt/Kapitel berücksichtigen auch
  verwendete Assets/Pakete und deren Unterkarten, ohne doppelte Notizen.
- **Dokument / Anhänge** öffnet exakt denselben Datensatz im bisherigen Editor.
  Markdown, Revisionen, Herkunft und sichere Anhänge bleiben erhalten.
- Abbrechen/Schließen mit geändertem Text fragt nach Speichern oder Verwerfen.
  Revisionskonflikte überschreiben keine andere Fassung und behalten den Entwurf.

`note_color` und `note_pinned` sind optionale Darstellungsfelder im bestehenden
Dokumentdatensatz. Fehlende Werte entsprechen Gelb und nicht angeheftet.
Katalogöffnung validiert die Werte; eine Datenmigration ist nicht nötig.

Keine Bildpipeline, Godot-Ausgabe oder Asset-Freigabe wurde ergänzt.
[Kurze Nachprüfung](SICHTPRUEFUNG_6C.md) · [Ergebnisbericht](task-results/6c.md) ·
[Arbeitsplan](../plans/asset-studio-notizen-und-zuordnung.md)
