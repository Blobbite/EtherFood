---
task_id: T032
phase: D
status: not_started
depends_on: ["T007", "T008", "T013", "T025", "T027", "T029", "T031"]
requirements: ["R11", "R17", "R18", "R25", "R36"]
---
# T032 — Variantenmatrix, Prüfcheckliste und Sichtbefunde implementieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** D — Varianten, Texturen und Sichtprüfung  
**Abhängigkeiten:** [T007](../007-dokumente-notizen-und-aufgaben/p.md), [T008](../008-workflow-und-statusmodell/p.md), [T013](../013-assettypen-posen-und-richtungen/p.md), [T025](../025-timing-und-animationsevents/p.md), [T027](../027-materialfarben-nach-skalierung/p.md), [T029](../029-assetpakete-und-tempel/p.md), [T031](../031-integrierte-vorschauen/p.md)  
**Anforderungsbezug:** R11, R17, R18, R25, R36

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Mache die vollständige Sichtprüfung eines Helden oder Pakets übersichtlich und nachvollziehbar.

## Kontext und Bestandsgrenzen

Für den Helden sind Grafik- und Frame-Stufen kombinierbar; Richtugnen und Posen werden separat gewählt. Automatisches Öffnen aller Kombinationen beweist keine menschliche Sichtabnahme.

## Umsetzungsschirtte

1. Baue je Pose eine 5×5-Matrix der vorhandenen Grafik-/Frameprofile und eine Richtungswahl. Nutze tatsächlich konfigurierte Profilmengen; statische Assets bekommen eine passende eindimensionale Übersicht.

2. Zeige für jede erwartete Variante missing, stale, built, technical_failed, technical_passed, visual_pending oder visual_reviewed mit Textkennzeichnung. Nicht erforderliche Kombinationen bleiben separat.

3. Ergänze tatsächliche Maße, Dateigröße, Dauer, Anker und relevante Prüfresultate. Technische Palettenzugehörigkeit darf nciht als richtige Materialsemantik beschriftet werden.

4. Ermögliche eine geführte Tour durch alle vorgesehenen Kombinationen. Speichere gesehen und ausdrücklich akzeptiert getrennt; eine Wiedergabe oder ein Screenshot erteilt keine Abnahme.

5. Implementiere Auffälligkeit melden mit vorgefüllter Fundstelle, optionalem Screenshot und Schweregrad. Offene blockierende Befunde verhindern den Übergang zur Kandidatenprüfung.

6. Erlaube eine bewusst bestätigte Sammel-Sichtabnahme mit exakt benannter Build-ID und Prüfumfang. Speichere Kriterien, Person/Profil und Zeitpunkt, ohne automatische Identitätsbehauptungen.

7. Erhalte alte Befunde und Reviews beim Neubau. Ein neuer Build übernimmt keine Abnahme, außer eine explizit implementierte und dokumentierte Regel bestätigt identische geprüfte Inhalte; Standard ist erneute Prüffung.

## Erwartete Ergebnisse

- `ui/variant_matrix.py`
- `application/review_service.py`
- `Review-/Issue-Integrationstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Alle 200 Kombinationen einer 8-Richtungs-Pose sind adressierbar, ohne 200 Canvas-Karten.
- [ ] Eine vollständig abgespielte Tour bleibt ohne Bestätigung visual_pending.
- [ ] Ein Issue öffnet später genau dieselbe Version und Auswahl.
- [ ] Eine neue Maske entzieht nciht die historische Abnahme, macht aber den neuen Build prüfpflichtig.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Vollständigkeit und Sichtprüfung sind getrennt.
- [ ] Konkrete Auffälligkeiten sind direkt verwaltbar.
- [ ] Prüfumfang und Buildbindung sind gespeichert.
- [ ] Statische Pakete nutzen passende Checklisten.

## Nicht Bestandteil dieser Aufgabe

Noch keine Godot-Freigabe oder produktive Dateiübernahme.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)
- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T032.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T033 — Unveränderliche Kandidaten und Versionsarchiv implementieren](../033-kandidaten-und-versionsarchiv/p.md). Nicht automatsich starten.
