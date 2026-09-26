---
task_id: T004
phase: A
status: not_started
depends_on: ["T003"]
requirements: ["R20", "R34"]
---
# T004 — Projektkatalog und Datenmigrationen implementieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** A — Grundlagen und Verwaltungskern  
**Abhängigkeiten:** [T003](../003-python-grundgeruest/p.md)  
**Anforderungsbezug:** R20, R34

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Baue eine transaktionale, versionierte Datenhaltung für Karten, Assets und ihre Arbeitsstände.

## Kontext und Bestandsgrenzen

Die SQLite-Datenbank ist die aktive lokale Metadatenbasis. Exportierte JSON-Datein werden nciht unbemerkt zurücksynchronisiert.

## Umsetzungsschirtte

1. Implementiere Repository-Schnittstellen für die Modelle aus T002 und eine SQLite-Implementierung mit Fremdschlüsseln, Constraints und kurzen Schreibtransaktionen.

2. Ergänze schema_version und vorwärts gerichtete Migrationen. Sichere die Datenbank vor Migrationen mit einem konsistenten Sicherungsverfahren; kopiere nciht einfach eine laufende DB ohne zugehörigen Zustand.

3. Verwende einen kontrollierten Schreibzugang. Arbeitsprozesse melden Ergebnisse an den Anwendungsdienst statt dieselbe DB unkoordiniert zu öffnen.

4. Führe revision_no oder eine gleichwertige Konfliktkontrolle für bearbeitbare Objekte ein. Ein veralteter Dialog darf neuere Änderungen nciht still überschreiben.

5. Implementiere logisches Archivieren und Wiederherstellen. Das Entfernen einer Kapitelverwendung löscht keine Asset-Datein. Fremdschlüssel müssen verwaiste Referenzen verhindern.

6. Implementiere einen expliziten portablen Metadatenexport sowie dessen geprüften Import in ein neues Testprojekt. Ein Import legt keine bestandenen Prüfungen oder produktiven Deployments ohne verifizierbare Nachweise an.

7. Dokumentiere Grenzen: lokale Einzelbenutzer-Nutzung, kein paralleles Schreiben von mehreren Rechnern auf eine Netzlaufwerk-DB.

## Erwartete Ergebnisse

- `storage/sqlite_repository.py oder gleichwertig`
- `storage/migrations/`
- `Katalog- und Migrationstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Abbruch mitten in einer Transaktion erzeugt keinen halben Akt oder unvollständige Relation.
- [ ] Migration einer alten Testdatenbank erhält IDs und Dokumente; fehlerhafte Migration lässt eine wiederherstellbare Sicherung.
- [ ] Zwei veraltete Bearbeitungsstände erzeugen einen Konflikt statt Datenverlust.
- [ ] Export und Import bewahren Kartenstruktur und Asset-Zuordnungen.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Constraints werden tatsächlich aktiviert und getestet.
- [ ] Migrationen sind reproduzierbar.
- [ ] Archivieren ist von Dateilöschung getrennt.
- [ ] Portabler Export ist ausdrücklich ein Snapshot.

## Nicht Bestandteil dieser Aufgabe

Kein Git-Versionieren der laufenden DB, keine automatische Zusammenführung fremder Projektkataloge.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T004.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T005 — Sichere Pfade, Dateiablage und Importjournal bauen](../005-pfade-und-objektspeicher/p.md). Nicht automatsich starten.
