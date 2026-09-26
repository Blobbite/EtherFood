---
task_id: T002
phase: A
status: not_started
depends_on: ["T001"]
requirements: ["R01", "R34"]
---
# T002 — Architektur und gemeinsame Datenverträge festschreiben

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** A — Grundlagen und Verwaltungskern  
**Abhängigkeiten:** [T001](../001-bestand-und-schreibgrenzen/p.md)  
**Anforderungsbezug:** R01, R34

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Verwandle den Projektbrief in eindeutige Schnittstellen und überprüfbare Invarianten, bevor mehrere Teilbereiche unabhängig implementiert werden.

## Kontext und Bestandsgrenzen

Die folgenden Modellnamen und Speicherentscheidungen sind Zielentwürfe dieses Plans, keine behaupteten vorhandenen APIs. Die lokale Einzelbenutzer-Anwendung steht im Mittelpunkt.

## Umsetzungsschirtte

1. Bestätige anhand T001 den Einbauort als eigenständiges Python-Paket bei PyGameTools. Erhalte bestehende Skriptpfade und Wrapper. Lege kein neues Repository an; bei abweichender realer Struktur dokumentiere den angepassten Paketpfad.

2. Definiere getrennte Schichten domain, application, storage, pipelines, godot und ui. Domain und Anwendungsdienste dürfen keine Qt- oder Godot-Imports benötigen. GUI und CLI verwenden dieselben Anwendungsdienste.

3. Lege SQLite als lokale maßgebliche Projekt-Metadatenhaltung und JSON/Markdown als ausdrücklich erzeugte Austausch-/Versionssnapshots fest. Vermeide gleichzeitig editierbare asset.json- und DB-Kopien mit konkurrierender Wahrheit. Quellen, Masken und Builds sind getrennte, referenzierte Datein.

4. Definiere Project, Act, Chapter, Card, Relation, Asset, Pose, SourceRevision, ProfileRevision, MaskRevision, Build, Check, Review, Approval und Deployment. Verknüpfe über stabile IDs; Anzeigenamen und Canvas-Koordinaten sind keine IDs.

5. Trenne belongs_to, uses und depends_on. Eine Akt-Reihenfolge ist Planung, keine automatsich blockierende technische Abhängigkeit. Asset-Eigentümerschaft und Verwendung sind getrennte Felder.

6. Definiere versionierte Verträge für BuildRequest, BuildResult, VariantKey, RuntimePayload und DeploymentJournal. Unterscheide Input-Fingerprint, Ergebnis-Prüfsummen und Bereitstellungs-Prüfsummen.

7. Lege Fehlerkategorien, Datumsformat, Größenlimits, Ressourcenbesitz und Teststatus fest. Schreibe Architekturentscheidungen und Schema-Beispiele; versehe alle neuen Bezeichner mit dem Status Zielvertrag.

## Erwartete Ergebnisse

- `docs/asset-studio/ARCHITECTURE.md`
- `docs/asset-studio/decisions/`
- `schemas/asset-studio/`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein globaler Held kann von zwei Kapiteln referenziert werden, ohne zwei Asset-Identitäten zu erzeugen.
- [ ] Ein statisches Asset hat keine künstlich erzeugte Frame-Dimension; eine nciht benötigte Richtung ist nciht fehlend.
- [ ] Das Verschieben einer Karte ändert weder Build-Abhängigkeiten noch Dateipfade.
- [ ] Ein Review verweist auf einen exakten Build, nciht auf einen beweglichen latest-Verweis.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Alle Schichten und Verantwortlichkeiten sind beschrieben.
- [ ] Eine einzige lokale Metadaten-Wahrheit ist benannt.
- [ ] Schemas enthalten Versionsfelder und Pflicht-/Optionalfelder.
- [ ] Offene Annahmen sind ausdrücklich dokumentiert.

## Nicht Bestandteil dieser Aufgabe

Noch keine umfassende Umsetzugn aller Modelle; kein Mehrbenutzer-Server, Cloud-Sync oder generisches Plugin-Marktplatzsystem.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q07: Workspace Skizze](../../quellen/Q07_Workspace_Skizze.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T002.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T003 — Python-Paket, CLI und Testgerüst anlegen](../003-python-grundgeruest/p.md). Nicht automatsich starten.
