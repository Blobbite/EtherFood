---
task_id: T003
phase: A
status: not_started
depends_on: ["T002"]
requirements: ["R01", "R35"]
---
# T003 — Python-Paket, CLI und Testgerüst anlegen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** A — Grundlagen und Verwaltungskern  
**Abhängigkeiten:** [T002](../002-architektur-und-vertraege/p.md)  
**Anforderungsbezug:** R01, R35

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Erstelle ein startbares, testbares Anwendungspaket ohne produktive Seiteneffekte.

## Kontext und Bestandsgrenzen

Das neue Paket ergänzt PyGameTools. Bestehende CLI-Aufrufe müssen weiter funktionieren. Genannte Dateipfade sind Vorschläge und werden an T001 angepasst.

## Umsetzungsschirtte

1. Lege etherfood_studio mit getrennten Unterpaketen an. Ergänze eine Paketkonfiguration und einen lokalen Startbefehl, ohne bestehende Installer oder Importpfade zu entfernen.

2. Wähle anhand der vorgefundenen Umgebung kompatible Python-, PySide6- und Pillow-Versionen. Dokumentiere und fixiere die getestete Kombination; behaupte nciht automatsich Unterstützung jeder Version oder Plattform.

3. Implementiere eine minimale CLI mit help, version und einem lesenden doctor-Befehl. doctor zeigt fehlende Konfigurationen verständlich und startet keine Bildverarbeitung.

4. Führe eine zentrale typisierte Konfiguration, strukturierte Fehler und Logging mit Auftragskorrelation ein. Masken-/Profilinhalte, Maschinenpfade und Benutzernotizen dürfen nciht ungefragt an externe Dienste gesendet werden.

5. Lege synthetische Testdaten-Generatoren für kleine PNGs und Spritesheets in temporären Verzeichnissen an. Vermeide echte Heldenbilder als Voraussetzung für Unit-Tests.

6. Erstelle Core-Tests ohne Qt und einen gesonderten optionalen GUI-Testbereich. Fehlende GUI-Abhängigkeiten dürfen Core-Tests nciht verhindern, müssen aber als nciht ausgeführte GUI-Prüffung sichtbar bleiben.

7. Dokumentiere Entwicklungstart und Testaufrufe anhand der tatsächlich angelegten Datein. Prüfe alte Starter mit --help und geeigneten Bestandstests.

## Erwartete Ergebnisse

- `etherfood_studio/`
- `tests/asset_studio/`
- `Paketkonfiguration und Entwicklungsanleitung`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Paketimport verändert weder Arbeitsverzeichnis noch Projektdateien.
- [ ] help funktioniert ohne eingerichtetes Godot-Projekt.
- [ ] doctor meldet eine fehlende Pipeline-Installation als Befund.
- [ ] Alte Pipeline-Wrapper bleiben aufrufbar und behalten ihre bisherigen Standardwerte.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] CLI und Core-Testlauf funktionieren.
- [ ] GUI-Abhängigkeiten sind separat erkennbar.
- [ ] Synthetische Fixtures werden nach Tests aufgeräumt.
- [ ] Versionen und Startbefehle sind dokumentiert.

## Nicht Bestandteil dieser Aufgabe

Keine Bildalgorithmen neu schreiben; keine produktiven Aufträge beim Anwendungsstart.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)
- [Q03: Starter Bestand](../../quellen/Q03_Starter_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T003.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T004 — Projektkatalog und Datenmigrationen implementieren](../004-katalog-und-migrationen/p.md). Nicht automatsich starten.
