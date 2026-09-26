---
task_id: T045
phase: F
status: not_started
depends_on: ["T016", "T022", "T023", "T024", "T025", "T026", "T027", "T030", "T031", "T032", "T033", "T034", "T035", "T036", "T037", "T038", "T039", "T040", "T041", "T044"]
requirements: ["R07", "R09", "R15", "R24", "R35"]
---
# T045 — Gesamtablauf für Held und NPCs mit weniger Richtugnen testen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** F — Betrieb und Gesamtprüfung  
**Abhängigkeiten:** [T016](../016-asset-anlage-und-held-menue/p.md), [T022](../022-automatische-maskenvorschlaege/p.md), [T023](../023-farbkorrektur-pipeline/p.md), [T024](../024-frameableitung-und-geometrie/p.md), [T025](../025-timing-und-animationsevents/p.md), [T026](../026-grafikstufen-spritesheets/p.md), [T027](../027-materialfarben-nach-skalierung/p.md), [T030](../030-pipeline-bedienung-im-dashboard/p.md), [T031](../031-integrierte-vorschauen/p.md), [T032](../032-variantenpruefung-und-fehlerkarten/p.md), [T033](../033-kandidaten-und-versionsarchiv/p.md), [T034](../034-git-und-quellenrevisionen/p.md), [T035](../035-godot-exportvertrag/p.md), [T036](../036-godot-testbereitstellung/p.md), [T037](../037-godot-tests-und-abnahmeszene/p.md), [T038](../038-freigabe-und-pruefbindungen/p.md), [T039](../039-runtime-promotion-und-rollback/p.md), [T040](../040-testbereich-sicher-aufraeumen/p.md), [T041](../041-versionsvergleich-und-projektfortschritt/p.md), [T044](../044-backup-recovery-und-speicherpflege/p.md)  
**Anforderungsbezug:** R07, R09, R15, R24, R35

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Beweise den vollständigen animierten Arbeitsweg mit synthetischen Fixtures und nachvollziehbaren Prüfnachweisen.

## Kontext und Bestandsgrenzen

Die Anwendung wurde schrittweise aufgebaut. Jetzt muss der komplette Weg ohne manuelle Dateiverwaltung funktionieren; Testbestätigungen gelten ausschließlich für synthetische Testdaten.

## Umsetzungsschirtte

1. Erzeuge einen synthetischen Helden mit acht Richtugnen, mindestens zwei Posen, Source-Einzelbildern und getrennt gelieferten 16×1-Sheets. Die Testfixture simuliert das externe Animationstool, nciht eine neue Produktfunktion.

2. Lege den Helden im globalen Rahmen an und verknüpfe ihn in zwei Kapiteln. Importiere, wähle Masterreferenzen, erzeuge Maskenvorschläge, korrigiere gezielt einen Konflikt und führe die passende Farb-/Variantenpipeline aus.

3. Prüfe jede erwartete Kombination sowie die Anzeige in der Matrix. Teste sowohl Legacy-Timing als auch preserve_duration und die gewählte Farbgarantie.

4. Führe Kandidat, Export, Godot-Test, explizite synthetische Testabnahme, Promotion und Cleanup durch. Prüfe anschliesend, dass Runtime keine Testpfade benötigt und Payload-Hashes übereinstimmen.

5. Ändere eine Quellmaske und baue einen neuen Entwurf. Die alte Freigabe und aktive Spielversion bleiben erhalten. Führe einen fehlgeschlagenen Test und einen erfolgreichen erneuten Durchlauf aus.

6. Wiederhole den Kernweg für NPCs mit zwei und vier Richtugnen. Es dürfen weder acht Pflichtreferenzen noch acht Pflichtansichten aus versteckten Konstanten übrig bleiben.

7. Erzeuge einen ausführlichen Ergebnisbericht mit tatsächlichen Testbefehlen, Engine-/Python-Version, Screenshots der GUI-Prüffung und verbleibenden Blockern. Fehlende grafische oder Godot-Umgebung ist skipped/blocked, nciht passed.

## Erwartete Ergebnisse

- `tests/asset_studio/e2e/test_character_flow.py`
- `Synthetische Charakterfixtures`
- `E2E-Protokoll und GUI-/Godot-Nachweise`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Zwei Posen × 8 Richtugnen × 5 Grafikstufen × 5 Frame-Stufen ergeben 400 erwartete Heldenkombinationen.
- [ ] Maskenkonflikt, beschädigter Cache und fehlgeschlagener Godot-Test blockieren jeweils an der richtigen Schranke.
- [ ] Nach Promotion und Cleanup bleiben Kandidat, Historie und Rollback intakt.
- [ ] Zwei-/Vier-Richtungs-NPCs durchlaufen denselben generischen Weg.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Mindestens ein kompletter animierter E2E-Lauf ist ausgeführt.
- [ ] Ergebniszahlen stimmen mit den Asset-Anforderugnen überein.
- [ ] Keine produktiven Originalbilder werden als Testmaterial verändert.
- [ ] Offene reale Sichtabnahmen werden nciht als erledigt markiert.

## Nicht Bestandteil dieser Aufgabe

Keine Freigabe des echten Greenhero nur aufgrund synthetischer Tests.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T045.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T046 — Tempelpaket, globale Effekte und gemeinsame Verwendung testen](../046-e2e-tempel-und-globale-verwendung/p.md). Nicht automatsich starten.
