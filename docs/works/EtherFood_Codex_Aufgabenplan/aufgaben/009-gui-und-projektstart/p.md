---
task_id: T009
phase: B
status: not_started
depends_on: ["T003", "T004", "T006", "T008"]
requirements: ["R01"]
---
# T009 — Desktop-GUI und Projektstart implementieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** B — Dashboard und Asset-Anlage  
**Abhängigkeiten:** [T003](../003-python-grundgeruest/p.md), [T004](../004-katalog-und-migrationen/p.md), [T006](../006-akte-kapitel-und-globale-inhalte/p.md), [T008](../008-workflow-und-statusmodell/p.md)  
**Anforderungsbezug:** R01

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Erstelle die erste bedienbare PySide6-Anwendung mit Projektwahl und echter Datenanbindung.

## Kontext und Bestandsgrenzen

Das Dashboard ist eine Desktop-Anwendung. Es ersetzt keine Animationserzeugung und darf beim Öffnen weder Builds noch Migrationen produktiver Bilddaten starten.

## Umsetzungsschirtte

1. Baue ein Hauptfenster mit Projektwahl, Navigation, zentralem Arbeitsbereich, Eigenschaftenpanel und Status-/Auftragsbereich. Nutze die Anwendungsdienste statt direkter SQL- oder Dateizugriffe aus Widgets.

2. Implementiere Neues Projekt, Projekt öffnen und zuletzt verwendete Projekte. Prüfe Katalogversion und verfügbare Wurzeln; fehlende externe Laufwerke erscheinen als nciht verfügbar, nciht als leeres Projekt.

3. Binde die Struktur aus T006 sowie Statusinformationen aus T008 lesend ein. Noch nciht implementierte Aktionen sind erkennbar deaktiviert, nciht als erfolgreiche Dummys vorhanden.

4. Speichere Fensterzustand und lokale Anzeigepräferenzen getrennt von Asset-Revisionen. Ein Zoomwechsel oder eine andere Fenstergröße darf keinen Build ungültig machen.

5. Ergänze Fehlerdialoge mit verständlicher Meldung und technischen Details. Nicht gespeicherte Dokumentänderungen benötigen einen sichtbaren Speichern-/Verwerfen-/Abbrechen-Ablauf.

6. Versieh wichtige Widgets mit stabilen Test-IDs, Tastaturfokus und beschreibenden Namen. Nutze zusätzlich zur Farbe Text oder Symbole für Status.

7. Erstelle GUI-Smoke-Tests für Projekt öffnen, Navigation, beschädigten Katalog und fehlende Pfade. Dokumentiere, welche Tests eine grafische Umgebung benötigen.

## Erwartete Ergebnisse

- `ui/main_window.py`
- `ui/project_dialog.py`
- `GUI-Smoke-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein neues synthetisches Projekt kann erstellt, geschlossen und wieder geöffnet werden.
- [ ] Ein fehlendes USB-Laufwerk löscht keine gespeicherten Verweise.
- [ ] Ein Fehler in einer Vorschau verhindert nciht das Öffnen der Projektnavigation.
- [ ] Beim Programmstart werden keine Bilddateien verändert.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Ein startbares Fenster nutzt echte Katalogdaten.
- [ ] Fehlende Funktionen sind nciht als erledigt simuliert.
- [ ] Bedienung funktioniert per Maus und Tastatur.
- [ ] GUI-Tests sind von Core-Tests getrennt.

## Nicht Bestandteil dieser Aufgabe

Noch keine Canvas-Interaktion, keine Hintergrund-Daemon-Infrastruktur und kein Browser-Frontend.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T009.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T010 — Karten-Canvas für globale Inhalte, Akte und Kapitel bauen](../010-canvas-hierarchie/p.md). Nicht automatsich starten.
