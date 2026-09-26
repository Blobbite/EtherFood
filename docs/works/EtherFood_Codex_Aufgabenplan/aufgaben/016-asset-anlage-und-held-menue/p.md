---
task_id: T016
phase: B
status: not_started
depends_on: ["T008", "T009", "T013", "T015"]
requirements: ["R07", "R08", "R09", "R17"]
---
# T016 — NPC-Anlage, Vorlagen und Held-Menü implementieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** B — Dashboard und Asset-Anlage  
**Abhängigkeiten:** [T008](../008-workflow-und-statusmodell/p.md), [T009](../009-gui-und-projektstart/p.md), [T013](../013-assettypen-posen-und-richtungen/p.md), [T015](../015-quellen-und-spritesheet-import/p.md)  
**Anforderungsbezug:** R07, R08, R09, R17

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Ermögliche das Anlegen eines neuen Charakters vollständig im Dashboard und führe durch seine erforderlichen Schritte.

## Kontext und Bestandsgrenzen

Ein NPC ist ein eigener Datensatz mit Quellen und Rezept, nciht eine Sammlung manuell anzulegender Variantenordner.

## Umsetzungsschirtte

1. Baue den Anlageassistenten mit Typ, Name, Scope, Richtungsset, Posen und Vorlagenwahl. Generiere eine stabile ID und erlaube spätere Umbenennung ohne neue Identität.

2. Zeige eine Zusammenfassung der geplanten Anforderugnen vor dem Anlegen. Der Assistent erstellt Metadaten, nciht 200 leere Ausgabeordner je Pose.

3. Binde die Source-/Animationsimporte aus T015 ein und kennzeichne den externen Arbeitsschritt. Quellen können später ergänzt werden, ohne das Asset neu anzulegen.

4. Implementiere das Held-/NPC-Menü mit Reitern Übersicht, Quellen, Posen, Farben/Masken, Varianten, Prüfungen, Versionen und Dokumentation. Noch fehlende Funktionen bleiben sichtbar deaktiviert.

5. Zeige oben die Schrittkette aus T008 mit konkreten Sperrgründen und nächsten Aktionen. Ein Tooltip oder Detailpanel erklärt, welche Eingabe fehlt.

6. Erlaube das Ableiten eines neuen NPCs aus einer Konfigurationsvorlage. Quellbilder und Freigaben werden nciht automatsich als eigene neue Quellen oder bestätigte Ergebnisse dupliziert.

7. Erstelle einen GUI-Test: NPC mit vier Richtugnen anlegen, zwei Posen festlegen, einen Teil der Lieferung importieren und nach Neustart korrekt als unvollständig sehen.

## Erwartete Ergebnisse

- `ui/asset_wizard.py`
- `ui/asset_workspace.py`
- `Asset-Anlage-GUI-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein neuer NPC mit vier Richtugnen fordert genau diese vier an.
- [ ] Abbruch des Assistenten hinterlässt keinen halbfertigen Asset-Datensatz.
- [ ] Eine Vorlage überträgt Einstellungen, aber keine fremde Freigabe.
- [ ] Das Held-Menü zeigt einen fehlenden Animationsimport verständlich.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] NPCs sind ohne manuelle Ordneranlage erstellbar.
- [ ] Schrittkette ist mit echten Zuständen verbunden.
- [ ] Asset- und Projektansicht öffnen denselben Datensatz.
- [ ] Ein vollständiger GUI-Anlagetestszenario ist dokumentiert.

## Nicht Bestandteil dieser Aufgabe

Keine funktionierenden Build-/Godot-Knöpfe vortäuschen, bevor ihre Dienste implementiert sind.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T016.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T017 — Arbeitsprozesse und gemeinsame Pipeline-Adapter bauen](../017-worker-und-pipeline-adapter/p.md). Nicht automatsich starten.
