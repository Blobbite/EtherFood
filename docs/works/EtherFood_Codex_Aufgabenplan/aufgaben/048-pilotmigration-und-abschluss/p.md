---
task_id: T048
phase: F
status: not_started
depends_on: ["T001", "T014", "T034", "T039", "T040", "T041", "T042", "T044", "T045", "T046", "T047"]
requirements: ["R32", "R35", "R36"]
---
# T048 — Pilotmigration und abschließende Projektabnahme vorbereiten

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** F — Betrieb und Gesamtprüfung  
**Abhängigkeiten:** [T001](../001-bestand-und-schreibgrenzen/p.md), [T014](../014-bestandsimport-lesend/p.md), [T034](../034-git-und-quellenrevisionen/p.md), [T039](../039-runtime-promotion-und-rollback/p.md), [T040](../040-testbereich-sicher-aufraeumen/p.md), [T041](../041-versionsvergleich-und-projektfortschritt/p.md), [T042](../042-automatische-dokumentation-und-export/p.md), [T044](../044-backup-recovery-und-speicherpflege/p.md), [T045](../045-e2e-held-und-npc/p.md), [T046](../046-e2e-tempel-und-globale-verwendung/p.md), [T047](../047-paketierung-ci-und-betrieb/p.md)  
**Anforderungsbezug:** R32, R35, R36

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Führe den vorhandenen Bestand kontrolliert in das neue Dashboard ein und dokumentiere den tatsächlich erreichten Stand.

## Kontext und Bestandsgrenzen

Der vollständige Codeplan ersetzt keine reale Sichtprüfung von Greenhero, Masken oder Tempelgrafiken. Ein vorhandener Originalbestand wird zuerst lesend bewertet und gesichert.

## Umsetzungsschirtte

1. Erstelle aus T001 und dem aktuellen Scanner einen konkreten Migrationsplan für einen ausgewählten Helden und ein statisches Pilotpaket. Zeige Quellen, bekannte und unbekannte Herkunft, Zielpfade, erwartete Varianten und offene Abnahmen.

2. Erzeuge eine verifizierte Sicherung und führe den Import zuerst in einen neuen Pilot-Workspace aus. Bestehende Originalordner bleiben erhalten; die ursprüngliche Ablage wird nciht pauschal aufgelöst.

3. Übernimm vorhandene Quellen und nachprüfbare Berichte mit korrektem Status. Unbestätigte Greenhero-Materialmasken bleiben visuell offen; alte passed-Felder werden nur mit passendem Inhalt/Prüfumfang als historische Nachweise übernommen.

4. Prüfe Dashboard-Hierarchie, Dokumente, globale Verwendungen, NPC-Anlage, Buildplanung und Vorschau am Pilotbestand. Erstelle einen Delta-Bericht zwischen altem und verwaltetem Bestand.

5. Bereite den realen Godot-Testlauf vor. Produktive Promotion oder Altdatei-Löschung erfolgt nur nach den tatsächlich erbrachten technischen und menschlichen Freigaben; ohne diese Voraussetzungen bleibt die Pilotversion im Testzustand.

6. Schreibe den Abschlussbericht mit implementierten Funktionen, ausgeführten Tests, offenen manuellen Abnahmen, bekannten Grenzen, Startbefehlen und Wiederherstellungspfad. Kein fertiges Produkt behaupten, wenn Pflichtteile nur als Platzhalter existieren.

7. Aktualisiere die Anforderungsmatrix und Aufgabenberichte. Folgeaufgaben müssen konkrete reproduzierbare Befunde enthalten; der Grundplan bleibt als nachvollziehbare Versionsgrundlage erhalten.

## Erwartete Ergebnisse

- `docs/asset-studio/PILOT_MIGRATION.md`
- `docs/asset-studio/RELEASE_READINESS.md`
- `Aktualisierte Nachweise und Anforderungsmatrix`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Vorher-/Nachher-Hashes bestätigen unveränderte Originalbestände.
- [ ] Pilotimport ist wiederholbar, ohne Dubletten oder stille Freigaben.
- [ ] Ein unsicherer Maskenbefund blockiert die reale Materialabnahme.
- [ ] Der Pilot lässt sich aus der Sicherung vollständig wiederherstellen.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Der reale Pilotstand ist dokumentiert, nciht nur angekündigt.
- [ ] Offene Prüfungen bleiben sichtbar.
- [ ] Keine unkontrollierte produktive Mutation.
- [ ] Jede ursprüngliche Anforderung ist implementiert, getestet oder als konkreter offener Punkt ausgewiesen.

## Nicht Bestandteil dieser Aufgabe

Keine automatische Komplettmigration aller Assets und kein Löschen alter Ordner als Aufräumschritt.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q07: Workspace Skizze](../../quellen/Q07_Workspace_Skizze.md)
- [Q09: Masken Profilregeln Bestand](../../quellen/Q09_Masken_Profilregeln_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T048.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.
