---
task_id: T008
phase: A
status: not_started
depends_on: ["T002", "T006", "T007"]
requirements: ["R21", "R30"]
---
# T008 — Typabhängige Schrittketten und Freigabestatus modellieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** A — Grundlagen und Verwaltungskern  
**Abhängigkeiten:** [T002](../002-architektur-und-vertraege/p.md), [T006](../006-akte-kapitel-und-globale-inhalte/p.md), [T007](../007-dokumente-notizen-und-aufgaben/p.md)  
**Anforderungsbezug:** R21, R30

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Baue die Regeln, die Kartenfortschritt und ausführbare Arbeitsschritte verlässlich voneinander trennen.

## Kontext und Bestandsgrenzen

Charaktere benötigen externe Animation und Frame-Ableitungen; statische Pakete nciht. Technische Prüffung, Sichtprüfung und Godot-Freigabe sind unterschiedliche Nachweise.

## Umsetzungsschirtte

1. Definiere versionierte Workflow-Vorlagen für animierte Figuren, statische Bilder/Texturpakete, animierte Effekte und reine Dokumentationskarten. Hinterlege benötigte Eingaben und erlaubte nächste Aktionen.

2. Implementiere Schrittzustände not_started, waiting_external, ready, running, blocked, failed, cancelled, passed, stale und not_required mit erklärbaren Übergängen. Ein technisches skipped wird nciht automatsich zu passed.

3. Implementiere einen reinen Zustandsresolver: Aus Anforderugnen, vorhandenen Quellen, Build-Ergebnissen und Nachweisen ergibt sich der sichtbare Zustand. Die GUI kann nciht beliebige Statuswerte direkt in die DB schreiben.

4. Trenne Bearbeitungsstand, technischen Buildstatus, manuelle Sichtabnahme, Godot-Teststatus und Produktivbereitstellung. Ein alter freigegebener Build bleibt freigegeben, während ein neuer Entwurf offen ist.

5. Definiere, welche Änderungen welche Schritte ungültig machen. Eine neue Maske betrifft Farb- und Folgeergebnisse; ein umbenanntes Kapitel nciht die Pixel.

6. Berechne Kapitel-/Aktfortschritt nur aus ausdrücklich erforderlichen Kriterien. Unbekannte, nciht ausgeführte oder blockierte Tests zählen nciht als bestanden; not_required muss begründet sein.

7. Lege die Tests für verbotene Übergänge vor der GUI-Integration an. Stelle eine lesbare Diagnose bereit, warum ein Schritt gesperrt ist.

## Erwartete Ergebnisse

- `domain/workflows.py`
- `application/status_service.py`
- `Workflow-Vorlagen und Übergangstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein NPC wartet auf externe Spritesheets, statt fiktiv eine Animation zu erzeugen.
- [ ] Eine Textur besitzt keinen offenen Frame-Reduktionsschritt.
- [ ] Ein pauschaler erledigt-Haken kann einen fehlgeschlagenen Pflichtcheck nciht überstimmen.
- [ ] Neue Quellen machen abhängige Entwurfsresultate stale, nciht historische Freigaben.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Vorlagen und Statusresolver sind als Core-Funktionen getestet.
- [ ] Sperrgründe sind für Nutzer verständlich.
- [ ] Fortschritt kann nciht durch reine Kartenposition verändert werden.
- [ ] Der Kern ist ohne Qt ausführbar.

## Nicht Bestandteil dieser Aufgabe

Keine Auftragsausführung und keine echte Freigabe; diese Aufgabe baut deren überprüfbare Regeln.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T008.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T009 — Desktop-GUI und Projektstart implementieren](../009-gui-und-projektstart/p.md). Nicht automatsich starten.
