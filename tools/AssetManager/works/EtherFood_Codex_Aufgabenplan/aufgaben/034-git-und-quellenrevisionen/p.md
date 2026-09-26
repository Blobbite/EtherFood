---
task_id: T034
phase: E
status: not_started
depends_on: ["T001", "T004", "T015", "T033"]
requirements: ["R20", "R32", "R34"]
---
# T034 — Git-Anbindung und Quellenrevisionen ergänzen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** E — Versionen und Godot-Freigabe  
**Abhängigkeiten:** [T001](../001-bestand-und-schreibgrenzen/p.md), [T004](../004-katalog-und-migrationen/p.md), [T015](../015-quellen-und-spritesheet-import/p.md), [T033](../033-kandidaten-und-versionsarchiv/p.md)  
**Anforderungsbezug:** R20, R32, R34

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Verknüpfe nachvollziehbare Projekt-/Quellenstände mit Git, ohne eine zweite widersprüchliche Asset-Wahrheit zu schaffen.

## Kontext und Bestandsgrenzen

Git ergänzt die lokale Revisionierung; es ersetzt weder Ergebnisdigests noch Build- und Freigabeprotokolle. Ein Commit allein beschreibt keine uncommitteten Bildänderungen.

## Umsetzungsschirtte

1. Implementiere einen lesenden Git-Statusdienst für die tatsächlich ermittelten Repository-Wurzeln. Speichere Commit-ID, Dirty-Status und erfasste Inhalte als getrennte Herkunftsinformationen.

2. Führe explizite Exporte für relevante Projektkonfigurationen, Dokumentrevisionen und Asset-Metadaten in deterministische JSON-/Markdown-Datein ein. Die laufende SQLite-Datenbank, Cache, Maschinenpfade und Godot-.godot-Verzeichnisse werden nciht als normale Git-Artefakte behandelt.

3. Ermögliche einen bewusst ausgelösten Commit ausschließlich ausgewählter eigener Projektdateien. Fremde beriets vorgemerkte Änderungen dürfen nciht in einen Manager-Commit geraten; bei nciht sicher trennbarem Indexzustand blockieren statt alle Änderungen zu committen.

4. Erhalte eine funktionierende lokale SourceRevision auch ohne Git-Installation oder Remote. Ein Build bindet seine tatsächlichen Eingabehashes, unabhängig vom Git-Zustand.

5. Prüfe vorhandene .gitattributes/.gitignore-Regeln. Große Binärquellen können nach ausdrücklicher Projektentscheidung über LFS verwaltet werden; keine automatische Repository-Migration oder nachträgliche Historienumschreibung.

6. Biete Versionierugn als Entwurf speichern, Quellenstand sichern und optional Git-Commit an. Diese Aktionen sind nciht gleichbedeutend mit Asset-Freigabe.

7. Dokumentiere den Umgang mit mehreren vorhandenen Repositories: Referenzen getrennt festhalten, keinen atomaren Multi-Repository-Commit behaupten.

## Erwartete Ergebnisse

- `application/git_service.py`
- `Versionierte Metadatenexporte`
- `Git-Index- und Offline-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein fremder staged Change wird nciht in den Manager-Commit eingeschlossen.
- [ ] Ein Build aus Dirty-Quellen ist anhand tatsächlicher Hashes eindeutig zugeordnet.
- [ ] Ohne Git funktionieren lokale Revisionen und Kandidaten weiter.
- [ ] Kein Push oder Remote-Schreibzugriff erfolgt ohne ausdrückliche Aktion.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Git und lokale Revisionen haben klare Rollen.
- [ ] Keine pauschalen git add -A oder History-Resets.
- [ ] Exporte sind deterministisch und maschinenpfadfrei.
- [ ] Git-Fehler werden als Fehler gezeigt, nciht als erfolgreiche Sicherung.

## Nicht Bestandteil dieser Aufgabe

Kein automatischer Remote-Push, keine neue Repo-Anlage und kein Git-Reimplementieren.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T034.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T035 — Godot-Export und portable Runtime-Ressourcen implementieren](../035-godot-exportvertrag/p.md). Nicht automatsich starten.
