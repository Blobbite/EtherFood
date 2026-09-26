---
task_id: T005
phase: A
status: not_started
depends_on: ["T004"]
requirements: ["R19", "R32", "R33"]
---
# T005 — Sichere Pfade, Dateiablage und Importjournal bauen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** A — Grundlagen und Verwaltungskern  
**Abhängigkeiten:** [T004](../004-katalog-und-migrationen/p.md)  
**Anforderungsbezug:** R19, R32, R33

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Stelle sicher, dass alle späteren Importe und Builds nur in den vorgesehenen Bereichen schreiben und nach Abbrüchen nachvollziehbar bleiben.

## Kontext und Bestandsgrenzen

Drei Datenwurzeln bleiben erhalten. Ein Verzeichnisname wie PixelEng ist kein zuverlässiger Herkunftsnachweis und kein Freibrief zum Überschreiben.

## Umsetzungsschirtte

1. Implementiere konfigurierbare Aliase für TOOL_ROOT, WORKSPACE_ROOT, VERSIONS_ROOT und GODOT_ROOT. Maschinenpfade liegen in lokaler Konfiguration, portable Projektverweise bleiben relativ zu einer benannten Wurzel.

2. Prüfe reale Pfade auf Überlappung, Symlinks, Traversal, Groß-/Kleinschreibungskollisionen, Unicode-Normalisierung und reservierte Zielnamen. Weise unsichere Schreibziele zurück; Pfadprüfung muss auch unmittelbar vor dem Schreiben gelten.

3. Implementiere inhaltsadressierte Blob- oder Revisionsablage mit SHA-256, Länge, Dateityp und Herkunftsdatensatz. Keine Hardlinks zwischen veränderlichen Arbeitskopien und geschützten Originalen.

4. Kopiere Importe zuerst in temporäre Datein im Ziel-Dateisystem, prüfe Inhalt und Hash und registriere sie erst danach im Katalog. Ein Journal beschreibt die Kopier-/Registrierschritte, damit DB und Dateisystem nach einem Absturz abgeglichen werden können.

5. Schreibe neue Ausgaben exklusiv oder in neue Revisionsordner. Ein späteres Überschreiben benötigt einen ausdrücklich verwalteten Zielbestand, niemals einen pauschalen rekursiven Löschlauf.

6. Behandle getrennte Laufwerke als Kopieren, Prüfen, Registrieren und erst später Aufräumen. Versprich keine atomare Operation über mehrere Dateisysteme.

7. Füge freien Speicher, Datei-/Pixelgrenzen, Abbruch und eine lesende Integritätsprüfung hinzu. Verwaiste temporäre Datein werden gemeldet, aber nciht ungefragt entfernt.

## Erwartete Ergebnisse

- `storage/paths.py`
- `storage/blob_store.py`
- `storage/operation_journal.py`
- `Pfad- und Ausfalltests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] ../, Symlink-Ziele und verschachtelte Quell-/Ausgabewurzeln werden abgelehnt.
- [ ] Stromausfall-Simulation zwischen Dateikopie und DB-Commit hinterlässt rekonstruierbare Journaleinträge.
- [ ] Zwei gleichzeitige Importe derselben Bytes erzeugen keine widersprüchlichen Blob-Datensätze.
- [ ] Eine volle Zielplatte lässt Quellen und bestehende Freigaben unverändert.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Schreiboperationen verwenden gemeinsame Schutzfunktionen.
- [ ] Originale werden vor und nach einem Fixture-Import per Hash verglichen.
- [ ] Cross-Device-Fälle sind getestet.
- [ ] Keine versteckte Löschung oder automatisches Symlink-Folgen.

## Nicht Bestandteil dieser Aufgabe

Noch keine Produktions-Promotion und keine automatische Speicherbereinigung.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q06: Gemeinsame Schreibregeln](../../quellen/Q06_Gemeinsame_Schreibregeln.md)
- [Q07: Workspace Skizze](../../quellen/Q07_Workspace_Skizze.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T005.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T006 — Akte, Kapitel und globale Inhalte als Dienste umsetzen](../006-akte-kapitel-und-globale-inhalte/p.md). Nicht automatsich starten.
