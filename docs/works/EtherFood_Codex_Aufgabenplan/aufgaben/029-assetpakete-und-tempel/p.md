---
task_id: T029
phase: D
status: not_started
depends_on: ["T006", "T013", "T016", "T028"]
requirements: ["R06", "R28", "R29"]
---
# T029 — Asset-Pakete und Tempel-Arbeitsbereich umsetzen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** D — Varianten, Texturen und Sichtprüfung  
**Abhängigkeiten:** [T006](../006-akte-kapitel-und-globale-inhalte/p.md), [T013](../013-assettypen-posen-und-richtungen/p.md), [T016](../016-asset-anlage-und-held-menue/p.md), [T028](../028-statische-texturpipeline/p.md)  
**Anforderungsbezug:** R06, R28, R29

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Verwalte zusammengehörige statische Bestandteile als Paket mit gemeinsamer Version, Dokumentation und Prüffung.

## Kontext und Bestandsgrenzen

Der Tempel ist ein aktbezogenes Beispielpaket mit Boden, Decke und Säulen. Seine Verwendung kann sich auf mehrere Kapitel erstrecken.

## Umsetzungsschirtte

1. Implementiere Package mit stabiler ID, Scope, Mitgliedsreferenzen, gemeinsamen Profilen und optionalen ausdrücklich markierten Ausnahmen. Mitglieder werden referenziert, nciht bei jeder Verwendung kopiert.

2. Baue den Paket-Assistenten und einen Importbereich für mehrere Bestandteile. Jeder Bestandteil behält Quellenherkunft und Rolle wie floor, ceiling oder column.

3. Erzeuge eine Paketrevision mit exakt festgehaltenen Mitgliedsrevisionen. Ein schwebender Verweis auf jeweils neueste Mitglieder ist kein freigabefähiges Paket.

4. Zeige gemeinsame Maße, Anker, Grafikstufen und offene Befunde in einer Übersicht. Fehlende Pflichtmitglieder blockieren die Paketabnahme; optionale Bestandteile bleiben ausdrücklich optional.

5. Ergänze eine einfache Zusammenstellungs-/Kachelvorschau mit frei gesetzten Testpositionen und gemeinsamem Maßstab. Das ist eine Prüfaufstellung, kein neuer vollständiger Level-Editor.

6. Binde Paket-Workflow, Dokumentation und Mehrfachverwendungen in den Projektcanvas ein. Änderungen an einem global verwendeten Bestandteil müssen ihre betroffenen Pakete/Entwürfe anzeigen.

7. Erstelle ein synthetisches Tempelpaket unter Akt 1 → Kapitel 1 und verknüpfe es zusätzlich mit Kapitel 2.

## Erwartete Ergebnisse

- `application/package_service.py`
- `ui/package_workspace.py`
- `Paket-/Verwendungstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Dasselbe Tempelpaket wird in zwei Kapiteln ohne doppelte Quellen verwendet.
- [ ] Eine neue Säulenrevision verändert nciht rückwirkend eine eingefrorene Paketrevision.
- [ ] Fehlender Pflichtboden verhindert Freigabereife.
- [ ] Grafikstufen eines Pakets werden im gemeinsamen Maßstab geprüft.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Pakete sind versionierte Zusammenstellungen.
- [ ] Mitglieder und Scope sind getrennt.
- [ ] Statische Prüfansicht ist nutzbar.
- [ ] Keine Frame-Verarbeitung wird bei statischen Paketen eingeplant.

## Nicht Bestandteil dieser Aufgabe

Keine prozedurale Levelgenerierung und kein automatisches Umsortieren bestehender Spielordner.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T029.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T030 — Automatische Schrittketten und Auftragsbedienung integrieren](../030-pipeline-bedienung-im-dashboard/p.md). Nicht automatsich starten.
