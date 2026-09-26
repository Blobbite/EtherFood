---
task_id: T006
phase: A
status: not_started
depends_on: ["T004", "T005"]
requirements: ["R02", "R03", "R04", "R06"]
---
# T006 — Akte, Kapitel und globale Inhalte als Dienste umsetzen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** A — Grundlagen und Verwaltungskern  
**Abhängigkeiten:** [T004](../004-katalog-und-migrationen/p.md), [T005](../005-pfade-und-objektspeicher/p.md)  
**Anforderungsbezug:** R02, R03, R04, R06

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Ermögliche das Anlegen und Umordnen der Spielstruktur mit eindeutig getrennten Inhalts- und Abhängigkeitsbeziehungen.

## Kontext und Bestandsgrenzen

Gewünscht sind ein oberer projektweiter Rahmen sowie Akte und Kapitel darunter. Derselbe Held und dieselben Effekte können mehrfach verwendet werden.

## Umsetzungsschirtte

1. Implementiere Projekt, globalen Rahmen, Akt, Kapitel und freie Nebenkarten über Anwendungsdienste. Ergänze sinnvolle Vorlagen mit Namen, Beschreibung, Sortierreihenfolge und stabiler ID.

2. Implementiere belongs_to als kontrollierte Hierarchie ohne Elternzyklen. Akte gehören zum Projekt; Kapitel zu einem Akt. Freie Karten dürfen über klare erlaubte Typkombinationen angehängt werden.

3. Implementiere uses separat und erlaube mehrere Kapitelverwendungen desselben Assets. Eigentümerschaft kann global, akt- oder kapitelbezogen sein und unabhängig von Verwendungen geändert werden.

4. Implementiere fachliche depends_on-Beziehungen mit Zyklusprüfung nur dort, wo sie echte Voraussetzungen darstellen. Eine rein visuelle Verbindung darf keine technische Sperre erzeugen.

5. Ergänze Umbenennen, Verschieben, Sortieren, Archivieren und Wiederherstellen ohne automatische Dateiverschiebungen. Zeige vor dem Entfernen einer verwendeten Karte die betroffenen Beziehungen.

6. Erstelle ein synthetisches Demoprojekt mit globalem Helden, globalem Effekt, Akt 1, zwei Kapiteln und einem Tempelpaket. Noch keine Aussage über tatsächlich vorhandene Spielinhalte treffen.

## Erwartete Ergebnisse

- `application/project_service.py`
- `domain/relations.py`
- `Demo-Fixtures und Strukturtests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Kapitelwechsel ändert keine Asset-ID und keinen Blob-Pfad.
- [ ] Ein globaler Held erscheint als Verwendung in zwei Kapiteln und nur einmal als Asset.
- [ ] Ein Elternzyklus und ein technischer Abhängigkeitszyklus werden zurückgewiesen.
- [ ] Akt 2 kann bearbeitet werden, während Akt 1 offen ist.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Alle Strukturaktionen sind über Dienste testbar.
- [ ] Zugehörigkeit und Verwendung sind getrennt.
- [ ] Demodaten sind klar als synthetisch gekennzeichnet.
- [ ] Archivieren erhält gemeinsame Assets.

## Nicht Bestandteil dieser Aufgabe

Keine GUI und keine Asset-Verarbeitungsaufträge aus Kartenpositionen ableiten.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T006.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T007 — Dokumentation, Anhänge und Fehlerkarten verwalten](../007-dokumente-notizen-und-aufgaben/p.md). Nicht automatsich starten.
