---
task_id: T041
phase: F
status: not_started
depends_on: ["T006", "T007", "T008", "T032", "T033", "T034", "T038", "T039", "T040"]
requirements: ["R01", "R02", "R06", "R18", "R20"]
---
# T041 — Versionsverlauf, Vergleich und Dashboard-Fortschritt vervollständigen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** F — Betrieb und Gesamtprüfung  
**Abhängigkeiten:** [T006](../006-akte-kapitel-und-globale-inhalte/p.md), [T007](../007-dokumente-notizen-und-aufgaben/p.md), [T008](../008-workflow-und-statusmodell/p.md), [T032](../032-variantenpruefung-und-fehlerkarten/p.md), [T033](../033-kandidaten-und-versionsarchiv/p.md), [T034](../034-git-und-quellenrevisionen/p.md), [T038](../038-freigabe-und-pruefbindungen/p.md), [T039](../039-runtime-promotion-und-rollback/p.md), [T040](../040-testbereich-sicher-aufraeumen/p.md)  
**Anforderungsbezug:** R01, R02, R06, R18, R20

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Zeige jederzeit, was bearbeitet, gebaut, getestet, freigegeben und tatsächlich im Spiel verwendet wird.

## Kontext und Bestandsgrenzen

Das Dashboard soll den Ordnerwust ersetzen. Eine einzige grüne fertig-Markierung reicht nciht für diese verschiedenen Zustände.

## Umsetzungsschirtte

1. Baue eine Versionsansicht mit Entwurfsrevisionen, Builds, Kandidaten, ExportBundles, Reviews, Freigaben und Deployments. Zeige stabile IDs und ihre Beziehungen statt nur Dateinamen oder Zeitstempel.

2. Implementiere einen Vergleich zweier konkreter Stände: Quellen, Referenzauswahl, Masken, Parameter, Varianten, Prüfungen und Dokumente. Veränderte Bildinhalte sind per ausgewählter Vorschau aufrufbar.

3. Zeige am Asset gleichzeitig aktive Entwurfsrevision, letzter erfolgreicher Build, zuletzt freigegebener Kandidat und tatsächlich aktive Spielversion. latest darf diese Unterscheidung nciht ersetzen.

4. Ergänze Projektfilter für fehlende Quellen, wartende externe Animationen, Maskenkonflikte, veraltete Builds, offene Sichtprüfungen, Godot-Fehler und ausstehendes Aufräumen.

5. Aggregiere Akt-/Kapitelstand anhand erforderlicher Inhalte und Kriterien aus T008. Eine globale Asset-Aktualisierung zeigt alle betroffenen Verwendungen; historische Kapitelstände werden nciht heimlich überschrieben.

6. Baue einen lesbaren Auditverlauf mit Aktion, vorherigem/nachherigem Bezug, Zeitpunkt und lokaler Entscheiderangabe. Keine manipulationssichere Mehrbenutzer-Auditgarantie behaupten.

7. Verknüpfe jede Warnung mit der zuständigen Karte und nächsten zulässigen Aktion. Freigabe widerrufen und Rollback starten bleiben ausdrücklich bestätigte Aktionen.

## Erwartete Ergebnisse

- `ui/history/`
- `ui/dashboard_filters.py`
- `Fortschritts- und Vergleichstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Entwurf 13, freigegebener Kandidat 12 und aktive Spielversion 11 sind gleichzeitig korrekt sichtbar.
- [ ] Ein Akt mit offenem Pflichtasset wird nciht als vollständig angezeigt.
- [ ] Ein globales Asset wird in der Bibliothek nur einmal gezählt, seine Verwendungen aber einzeln gezeigt.
- [ ] Ein Versionsvergleich verändert keine verglichenen Inhalte.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Der Nutzer kann Zustände ohne Dateisystemsuche unterscheiden.
- [ ] Fortschritt folgt echten Kriterien.
- [ ] Audit und Bildvergleich sind konsistent.
- [ ] Filter öffnen die korrekten Fundstellen.

## Nicht Bestandteil dieser Aufgabe

Keine pauschale rückwirkende Freigabe importierter Altstände.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T041.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T042 — Projekt- und Asset-Dokumentation automatisch erzeugen](../042-automatische-dokumentation-und-export/p.md). Nicht automatsich starten.
