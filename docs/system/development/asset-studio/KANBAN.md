# Aufgaben-Kanban und getrennte Suche

Seit Zwischenpaket 6b lautet die Reihenfolge im Hauptfenster:
**Projekt-Canvas → Aufgaben-Kanban → Dokumentation & Anhänge → Suche**.
Bestehende Projekte bleiben ohne Migration verwendbar. Aufgaben und lokale
Issues sind dieselben Katalogeinträge wie zuvor, keine GitHub-Synchronisierung.

## Bereich und Gruppen

Das Board folgt der im Projektbaum oder Canvas ausgewählten Karte. Der
Bereich steht oberhalb der Spalten; neue Aufgaben/Issues gehören genau dorthin.

- **Projektwurzel:** alle aktiven Aufgaben, gruppiert nach projektweiten
  Inhalten, Akten, Kapiteln und Eigentümern. Gruppen lassen sich zuklappen.
- **Akt/Kapitel:** Aufgaben dieses Bereichs und seiner Unterkarten, außerdem
  Aufgaben verwendeter Assets/Pakete. Paketunterkarten werden mit einbezogen.
- **Asset:** Aufgaben dieses Assets und seiner Unterkarten.
- Gemeinsam verwendete Assets erscheinen pro Bereich nur einmal. Unter
  **Verwendete Assets (Herkunft)** bleibt der echte Eigentümer erkennbar;
  es werden weder Aufgaben kopiert noch Verwendungsbeziehungen geändert.
- Archivierte Aufgaben sowie archivierte Eigentümerzweige werden ausgeblendet.
  `depends_on` erweitert den Aufgabenbereich nicht.

**Gesamtes Projekt** wählt die Projektwurzel. Ein einfacher Aufgabenklick zeigt
Beschreibung, Fundstelle und To-dos unter dem Board, ohne den Bereich zu wechseln.
**Zum Bezug** navigiert ausdrücklich zur Eigentümerkarte. Doppelklick oder
Eingabetaste öffnet den vorhandenen Bearbeitungsdialog genau einmal.

## Spalten, Filter und Speicherung

Vier Spalten entsprechen den gespeicherten Status: **Offen**, **In Arbeit**,
**Blockiert**, **Erledigt**. Der Typfilter trennt Aufgaben und Issues; das Textfeld
filtert Titel, Beschreibung und To-dos innerhalb des aktuellen Bereichs.
Innerhalb einer Eigentümergruppe stehen höhere Prioritäten zuerst, danach Titel.
Spaltenzähler beziehen sich auf den aktuellen Filter. Vollständige Titel und
Herkunft sind im Tooltip und der Detailansicht lesbar.

Ziehen in eine andere Spalte oder **Status setzen** schreibt über denselben
`IssueService`. Auch ein Ablegen auf einer fremden Gruppe ändert ausschließlich
den Status – niemals Eigentümer, ID oder Canvas-Position. Ziehen innerhalb
derselben Spalte erzeugt keine neue Revision. Ablegen fremder Dateien oder aus
einem anderen Board wird nicht als Aufgabenänderung akzeptiert.

Offene To-dos verhindern **Erledigt**. Eine verlangte Aufgabenabnahme muss
ausdrücklich bestätigt werden und ist keine Asset-/Build-/Godot-Freigabe.
Parallel geänderte Aufgaben führen zu einem Revisionskonflikt statt Überschreiben;
das Board zeigt anschließend den gespeicherten Stand. Abhaken, Bearbeiten und
Neuanlage bleiben mit **Asset-Menü → Dokumentation → Aufgaben & Issues** verbunden.

Die kartenspezifische Eigenschaftenleiste wird im Kanban ausgeblendet, damit die
vier Spalten Platz haben; im Canvas bleibt sie unverändert verfügbar. Bei sehr
wenig Platz ist das Board horizontal scrollbar. Details/Board sind höhenverstellbar.

## Suche, Notizen und interne Dateien

**Suche** bzw. **Strg+F** öffnet die unabhängige projektweite Suche. Ihre Bereichs-,
Status-, Typ- und Assettypfilter ändern keine Kanban-Filter. Dokumente lassen sich
von dort im Dokumentationsreiter öffnen, Aufgaben im gemeinsamen Editor.
Ungespeicherte Notizen behalten ihren bisherigen Speichern/Verwerfen/Abbrechen-
Schutz beim Wechsel zu einer anderen Karte.

`.asset-studio/objects` ist ein hashadressierter, unveränderlicher Quellenspeicher.
Die Namen dort sind keine vorgesehenen Godot-Assetnamen. Geprüfte, portable
Godot-Pakete mit Posen, Richtungen, Grafik-/Framestufen und Laufzeitpfaden folgen
erst mit Exportvertrag T035, Testbereitstellung T036 und Runtime-Übernahme T039.
Dieser Arbeitsschritt erzeugt oder verschiebt keine Game-Assets.

[Kurze persönliche Nachprüfung](SICHTPRUEFUNG_6B.md) ·
[Ergebnisbericht](task-results/6b.md) · [Arbeitsplan](../plans/asset-studio-kanban.md)
