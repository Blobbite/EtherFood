---
task_id: T007
phase: A
status: not_started
depends_on: ["T006"]
requirements: ["R04", "R05", "R18", "R31"]
---
# T007 — Dokumentation, Anhänge und Fehlerkarten verwalten

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** A — Grundlagen und Verwaltungskern  
**Abhängigkeiten:** [T006](../006-akte-kapitel-und-globale-inhalte/p.md)  
**Anforderungsbezug:** R04, R05, R18, R31

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Führe Anforderugnen, Notizen, Entscheidungen und konkrete Auffälligkeiten direkt an den jeweiligen Projektkarten zusammen.

## Kontext und Bestandsgrenzen

Dokumentation ist Teil des Dashboards. Freier Benutzertext darf nciht durch technische Berichte überschrieben werden.

## Umsetzungsschirtte

1. Implementiere Dokumente in Markdown mit Entwurfsrevisionen, Titel, Bezugskarte, Inhalt und Änderungsdatum. Halte manuell geschriebene Dokumente und generierte Berichte in verschiedenen Datenfeldern oder Dokumenttypen.

2. Ergänze sichere Anhänge über T005. Erhalte Ursprungsnamen als Metadaten; nutze keine frei eingegebenen Anzeigenamen als Schreibpfade.

3. Implementiere Aufgaben und Issues mit Status, Priorität, benötigter Abnahme, optionaler Zuständigkeit und Relation zur betroffenen Karte. Keine Benutzerkontenplattform für die lokale Erstversion aufbauen.

4. Führe für Asset-Issues eine optionale präzise Fundstelle ein: Asset-ID, Build-ID, Pose, Richtung, Grafikprofil, Frame-Anzahl, Zeit/Frame und Screenshot-Referenz. Felder dürfen vor dem ersten Build leer sein.

5. Implementiere Titel-/Textsuche und Filter nach Akt, Kapitel, Asset-Typ und Aufgabenstatus. Berichte und Notizen bleiben unterscheidbar.

6. Stelle Textvorlagen für Aktbeschreibung, Kapitelanforderung, Asset-Briefing, Testnotiz und Entscheidung bereit. Automatisches Dokumentieren übernimmt bekannte Fakten, erfindet aber keine Story oder Abnahme.

## Erwartete Ergebnisse

- `application/document_service.py`
- `application/issue_service.py`
- `Dokumentvorlagen und Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Eine generierte Build-Zusammenfassung verändert keinen Nutzerabsatz.
- [ ] Das Verschieben der Bezugskarte erhält Anhänge und Dokumenthistorie.
- [ ] Eine Issue-Fundstelle öffnet nach Serialisierung wieder dieselben IDs und Auswahlwerte.
- [ ] HTML/Script-Text in Notizen oder Dateinamen wird nciht als ausführbarer Inhalt behandelt.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Dokumente und Issues sind dauerhaft gespeichert.
- [ ] Suche liefert stabile Bezüge statt nur Dateinamen.
- [ ] Anhangsimport verwendet den sicheren Dateidienst.
- [ ] Vorlagen enthalten keine fingierten fertigen Prüfungen.

## Nicht Bestandteil dieser Aufgabe

Kein Dialog-/Quest-Editor mit Spiellogik; keine automatische inhaltliche KI-Textgenerierung als Pflichtfunktion.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T007.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T008 — Typabhängige Schrittketten und Freigabestatus modellieren](../008-workflow-und-statusmodell/p.md). Nicht automatsich starten.
