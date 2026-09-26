---
task_id: T040
phase: E
status: not_started
depends_on: ["T005", "T036", "T038", "T039"]
requirements: ["R27", "R33"]
---
# T040 — Testbereitstellungen nach erfolgreicher Übernahme gezielt aufräumen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** E — Versionen und Godot-Freigabe  
**Abhängigkeiten:** [T005](../005-pfade-und-objektspeicher/p.md), [T036](../036-godot-testbereitstellung/p.md), [T038](../038-freigabe-und-pruefbindungen/p.md), [T039](../039-runtime-promotion-und-rollback/p.md)  
**Anforderungsbezug:** R27, R33

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Entferne nur die nciht mehr benötigten Testkopien eines erfolgreich übernommenen Kandidaten.

## Kontext und Bestandsgrenzen

Der Nutzer möchte Testassets nach Abnahme aus dem Testbereich entfernen. Archiv, Prüfberichte, gemeinsame Testszene und andere laufende Tests bleiben bestehen.

## Umsetzungsschirtte

1. Erstelle CleanupPlan ausschließlich aus einem erfolgreichen abgeschlossenen PromotionJournal. Voraussetzung sind gültiger finaler Ladetest und aktive Zuordnung zum freigegebenen Payload.

2. Prüfe für jede Testdatei Besitz, aktuellen Hash und Pfadgrenze. Wurde eine Datei manuell verändert oder ist sie fremd, melde einen Konflikt und lasse sie erhalten.

3. Prüfe aktive Testläufe und Referenzen anderer Kandidaten. Gemeinsam genutzte Testszenen und Template-Datein werden nciht pro Asset gelöscht.

4. Entferne beziehungsweise verschiebe in einen verwalteten Wiederherstellungsbereich nur die owned_files der ausgewählten Testbereitstellung. Ein wiederholter Cleanup muss sicher und idempotent sein.

5. Erhalte Kandidatenarchiv, ExportBundle, Prüfberichte, Screenshots und Freigabehistorie. Der Testcache ist nciht der einzige Speicherort des abgenommenen Pakets.

6. Führe nach Cleanup erneut eine Prüffung auf produktive Verweise in test_assets/test_scenes durch. Benötigt der finale Stand doch noch Testpfade, gilt die Übernahme als fehlerhaft und muss wiederherstellbar bleiben.

7. Zeige im Dashboard getrennt übernommen, Testkopie noch vorhanden und aufgeräumt. Ein fehlgeschlagener Cleanup darf nciht die beriets gültige Runtime-Version zerstören.

## Erwartete Ergebnisse

- `godot/cleanup_service.py`
- `Cleanup-Dialog/Status`
- `Besitz-, Referenz- und Wiederholungstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Eine fremde Datei neben verwalteten Testassets bleibt unverändert.
- [ ] Eine manuell bearbeitete Testdatei wird nciht still gelöscht.
- [ ] Ein zweiter Testkandidat behält seine Datein und gemeinsamen Szenen.
- [ ] Wiederholtes Aufräumen erzeugt keine Fehler und löscht keine Archivdaten.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Cleanup folgt erfolgreicher Promotion, nciht umgekehrt.
- [ ] Besitz-/Hashprüfung ist verbindlich.
- [ ] Historie und Rückkehrmöglichkeit bleiben erhalten.
- [ ] Produktive Ressourcen sind vom Testbereich unabhängig.

## Nicht Bestandteil dieser Aufgabe

Kein pauschales shutil.rmtree(test_assets) und kein automatisches Löschen von Originalen.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q07: Workspace Skizze](../../quellen/Q07_Workspace_Skizze.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T040.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T041 — Versionsverlauf, Vergleich und Dashboard-Fortschritt vervollständigen](../041-versionsvergleich-und-projektfortschritt/p.md). Nicht automatsich starten.
