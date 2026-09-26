---
task_id: T030
phase: D
status: not_started
depends_on: ["T016", "T017", "T018", "T023", "T024", "T025", "T026", "T027", "T028", "T029"]
requirements: ["R01", "R13", "R14", "R21"]
---
# T030 — Automatische Schrittketten und Auftragsbedienung integrieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** D — Varianten, Texturen und Sichtprüfung  
**Abhängigkeiten:** [T016](../016-asset-anlage-und-held-menue/p.md), [T017](../017-worker-und-pipeline-adapter/p.md), [T018](../018-buildplan-cache-und-invalidation/p.md), [T023](../023-farbkorrektur-pipeline/p.md), [T024](../024-frameableitung-und-geometrie/p.md), [T025](../025-timing-und-animationsevents/p.md), [T026](../026-grafikstufen-spritesheets/p.md), [T027](../027-materialfarben-nach-skalierung/p.md), [T028](../028-statische-texturpipeline/p.md), [T029](../029-assetpakete-und-tempel/p.md)  
**Anforderungsbezug:** R01, R13, R14, R21

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Verbinde die fachlichen Schritte mit echten Build-Aufträgen und einer bedienbaren Fortschrittsanzeige.

## Kontext und Bestandsgrenzen

Die GUI soll Abläufe steuern, nciht Python-Details voraussetzen. Nach Import und erforderlicher Bestätigung können zulässige Folgephasen automatsich laufen.

## Umsetzungsschirtte

1. Baue Plan prüfen, Bauen und prüfen, Abbrechen, Verifiziert fortsetzen und Neu aufbauen als unterschiedliche Aktionen. Zeige vor einem schreibenden Lauf die betroffenen Assets und Ziele.

2. Binde Build-Graph und Arbeitsprozesse an die Schrittkette. Automatische Fortsetzung läuft nur über erfüllte Voraussetzungen und stoppt an externen oder menschlichen Prüfpunkten.

3. Erlaube eine ausdrückliche Einstellung für automatisches Bauen nach stabilem Import. Quellenänderungen während eines laufenden Jobs erzeugen einen neuen Entwurfsstand; der Job behält seine eingefrorenen Eingaben.

4. Zeige Fortschritt, aktuelle Phase, Fehlerfundstelle, verwendete Werkzeuge und wiederverwendete Varianten. Nicht verfügbare Tools ergeben blocked statt einer Endlosschleife.

5. Führe eine Auftragswarteschlange mit begrenzter Parallelität und sichtbarer Priorität ein. Das Schließen der GUI muss laufende Aufträge kontrolliert beenden oder einen tatsächlich implementierten Wiederaufnahmeweg nutzen; keinen nciht vorhandenen Hintergrunddienst behaupten.

6. Ein automatischer Build darf weder Masken-Sichtabnahme noch Godot-Freigabe erteilen. Einstellungen wie Speichern, Bauen und Freigeben bleiben separate Befehle.

7. Verknüpfe Fehler mit Aufgaben/Nebenkarten. Ein Klick öffnet das betroffene Asset und dessen Phase.

## Erwartete Ergebnisse

- `ui/build_queue.py`
- `ui/workflow_panel.py`
- `Durchgängige GUI-/Buildtests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Import → Maskenprüfung → Farbkorrektur → Varianten stoppt korrekt bei einer offenen manuellen Maskenabnahme.
- [ ] Doppelklick auf Bauen erzeugt keinen doppelten Schreibauftrag.
- [ ] GUI-Neustart zeigt unterbrochene Aufträge korrekt.
- [ ] Automatisches Bauen erteilt keine Freigabe.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Alle sichtbaren Build-Aktionen sind an echte Dienste gebunden.
- [ ] Fortschritt und Fehler bleiben nachvollziehbar.
- [ ] Unveränderliche Eingaben gelten auch während GUI-Bearbeitung.
- [ ] Abbruch-/Wiederaufnahmeweg ist getestet.

## Nicht Bestandteil dieser Aufgabe

Keine unkontrollierte Vollautomatik über manuelle Prüfschranken hinweg.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T030.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T031 — HTML-Vergleiche im Asset-Menü sicher wiederverwenden](../031-integrierte-vorschauen/p.md). Nicht automatsich starten.
