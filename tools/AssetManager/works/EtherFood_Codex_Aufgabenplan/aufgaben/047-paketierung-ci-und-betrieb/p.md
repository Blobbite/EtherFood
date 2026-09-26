---
task_id: T047
phase: F
status: not_started
depends_on: ["T003", "T009", "T031", "T042", "T043", "T044", "T045", "T046"]
requirements: ["R35"]
---
# T047 — Installation, automatisierte Prüfungen und Betrieb dokumentieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** F — Betrieb und Gesamtprüfung  
**Abhängigkeiten:** [T003](../003-python-grundgeruest/p.md), [T009](../009-gui-und-projektstart/p.md), [T031](../031-integrierte-vorschauen/p.md), [T042](../042-automatische-dokumentation-und-export/p.md), [T043](../043-erweiterbare-vorlagen-und-typen/p.md), [T044](../044-backup-recovery-und-speicherpflege/p.md), [T045](../045-e2e-held-und-npc/p.md), [T046](../046-e2e-tempel-und-globale-verwendung/p.md)  
**Anforderungsbezug:** R35

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Liefere eine reproduzierbar startbare Anwendung mit nachvollziehbarer Test- und Installationsanleitung.

## Kontext und Bestandsgrenzen

Die Zielplattformen sind erst nach Prüffung der echten Umgebung festzulegen. Ein erfolgreicher Linux-Lauf beweist keine Windows-/macOS-Unterstützung.

## Umsetzungsschirtte

1. Ergänze eine lokale Installation in isolierter Python-Umgebung und einen dokumentierten Startweg. Bestehende PyGameTools-Wrapper müssen nach Installation und Update weiter funktionieren.

2. Fixiere die tatsächlich getesteten Abhängigkeiten und dokumentiere QtWebEngine-Komponenten, Ressourcen und Godot-Pfadkonfiguration. Benötigte Fremdkomponenten werden nciht ungefragt systemweit installiert.

3. Richte automatisierte Testgruppen für Core, Pipelines, GUI, QtWebEngine und Godot ein. Pflicht-Jobs dürfen fehlende Abhängigkeiten nciht als grünen Komplettlauf verschleiern.

4. Ergänze einen reproduzierbaren Demo-Projektstart mit ausschließlich synthetischen Inhalten. Die Demo verändert keine vorhandenen produktiven Wurzeln.

5. Prüfe Paketstart außerhalb des Quellverzeichnisses, Pfade mit Sonderzeichen, read-only-Projektanzeige und ein Upgrade mit vorhandener Testdatenbank.

6. Erstelle Betriebsdokumentation für Erstkonfiguration, tägliche Arbeit, Maskenprüfung, Versionen, Godot-Abnahme, Rollback, Backup und bekannte Einschränkungen.

7. Erfasse Abhängigkeits-/Lizenzhinweise und Unterstützungsstand ohne rechtliche Vollständigkeitsgarantie. Kein Remote-Upload, keine Telemetrie und keine produktiven Assets im Distributionspaket als Standard.

## Erwartete Ergebnisse

- `Installations-/Startkonfiguration`
- `CI-Workflow falls Repository vorhanden`
- `Betriebsanleitung und Release-Checkliste`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Eine frische isolierte Umgebung startet die Demo mit dokumentierten Befehlen.
- [ ] Core-Tests benötigen keine grafische Sitzung; separate GUI-/Godot-Jobs melden ihren tatsächlichen Zustand.
- [ ] Update erhält Katalog, Quellen und vorhandene Freigaben.
- [ ] Paketstart funktioniert auch außerhalb des Repository-Root.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Installation und Update sind nachvollziehbar.
- [ ] Teststufen sind transparent.
- [ ] Demodaten sind vollständig getrennt.
- [ ] Nur tatsächlich getestete Plattformen gelten als unterstützt.

## Nicht Bestandteil dieser Aufgabe

Keine automatische Veröffentlichung, keine kostenpflichtigen Dienste und kein ungefragtes System-Setup.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T047.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T048 — Pilotmigration und abschließende Projektabnahme vorbereiten](../048-pilotmigration-und-abschluss/p.md). Nicht automatsich starten.
