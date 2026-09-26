---
task_id: T012
phase: B
status: not_started
depends_on: ["T007", "T009", "T010"]
requirements: ["R05", "R18", "R31"]
---
# T012 — Dokumentationseditor und Aufgabenansicht integrieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** B — Dashboard und Asset-Anlage  
**Abhängigkeiten:** [T007](../007-dokumente-notizen-und-aufgaben/p.md), [T009](../009-gui-und-projektstart/p.md), [T010](../010-canvas-hierarchie/p.md)  
**Anforderungsbezug:** R05, R18, R31

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Ermögliche die Bearbeitung und Suche von Dokumentation direkt im Dashboard.

## Kontext und Bestandsgrenzen

Manuelle Notizen, generierte Berichte und konkrete Fehlerkarten sind unterschiedliche Objekte mit gemeinsamen Projektbezügen.

## Umsetzungsschirtte

1. Baue einen Markdown-Editor mit Vorschau, Speichern und sichtbarem Änderungsstatus. Nutze Dokumentrevisionen und Konflikterkennung statt blindem Überschreiben.

2. Ergänze Dokumente und Anhänge als Reiter an Akt-, Kapitel-, Paket- und Asset-Karten. Öffnen von Anhängen ist eine ausdrückliche Aktion; Skripte werden nciht automatsich ausgeführt.

3. Binde Aufgabenliste, Issue-Anlage und Filter nach Status, Akt, Kapitel und Inhaltstyp ein. Ein Klick auf ein Suchergebnis fokussiert die passende Karte.

4. Stelle dokumentierte Vorlagen bereit und erlaube freie Nebennotizen. Generierte technische Berichte sind als solche markiert und zunächst schreibgeschützt.

5. Schütze die Vorschau gegen ausführbares HTML und unerwartete externe Netzwerkanfragen. Externe Links werden nur bewusst geöffnet.

6. Implementiere einen kontrollierten Import vorhandener Markdown-Dokumente als neue Dokumentrevisionen mit Herkunftsangabe. Überschreibe weder die Originaldatei noch einen gleichnamigen vorhandenen Text ohne Konfliktauflösung.

7. Ergänze Tastaturnavigation, Suche und verständliche Leer-/Fehlerzustände.

## Erwartete Ergebnisse

- `ui/documents/`
- `ui/tasks/`
- `Dokument-GUI-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ungespeicherter Text geht beim Kartenwechsel nciht still verloren.
- [ ] Ein Script-Tag in einer Notiz wird nciht ausgeführt.
- [ ] Der Import einer README behält die Originaldatei unverändert.
- [ ] Eine Aufgabe bleibt nach dem Umbenennen des Kapitels zugeordnet.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Dokumente sind direkt im Dashboard bearbeitbar.
- [ ] Suche und Aufgabenfilter funktionieren mit echten Katalogdaten.
- [ ] Berichte können keine Benutzertexte überschreiben.
- [ ] Mindestens ein End-to-End-GUI-Test erfasst Anlegen, Speichern und Wiederöffnen.

## Nicht Bestandteil dieser Aufgabe

Keine automatische Story-Erfindung oder Überschreibung vorhandener Projektanweisungen.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T012.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T013 — Asset-Typen, Posen und variable Richtungen modellieren](../013-assettypen-posen-und-richtungen/p.md). Nicht automatsich starten.
