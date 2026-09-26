---
task_id: T013
phase: B
status: not_started
depends_on: ["T004", "T006", "T008"]
requirements: ["R06", "R07", "R08", "R13", "R28", "R30"]
---
# T013 — Asset-Typen, Posen und variable Richtugnen modellieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** B — Dashboard und Asset-Anlage  
**Abhängigkeiten:** [T004](../004-katalog-und-migrationen/p.md), [T006](../006-akte-kapitel-und-globale-inhalte/p.md), [T008](../008-workflow-und-statusmodell/p.md)  
**Anforderungsbezug:** R06, R07, R08, R13, R28, R30

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Erstelle eine wiederverwendbare Asset-Verwaltugn für Helden, NPCs, Mobs, Effekte und statische Bestandteile.

## Kontext und Bestandsgrenzen

Der Held besitzt acht Richtugnen. Andere Inhalte können weniger oder keine Richtungsdimension benötigen. Typ und Akt-Zugehörigkeit sind unabhängig.

## Umsetzungsschirtte

1. Implementiere Asset-Typen mit Fähigkeiten statt hart verdrahteter Namensabfragen: animated, directional, supports_materials, static_image und package_member. Vermeide if asset_name == greenhero.

2. Ergänze eine geordnete Richtungsmenge pro Asset und optionale Pose-Abweichungen. Biete Vorlagen für 8, 4, 2 und 1 Richtung; richtungslose statische Inhalte verwenden null, nciht einen erfundenen Richtungsnamen.

3. Definiere Posen mit stabiler ID, Anzeige-/Exportname, Loop-Einstellung, Quellenart, Timing und Anker. Behalte stand/walk/run-Bezeichnungen aus bestehenden Daten, statt sie ungefragt zu idle umzubenennen.

4. Berechne die erwarteten Kombinationen aus aktivem Asset-Typ, Pose, Richtung, Grafikprofil und Frame-Profil. Nicht erforderliche Kombinationen sind not_required, nciht missing.

5. Erfasse Herkunft für eigenständige Originalanimationen und abgeleitete Varianten ausdrücklich. Ein unabhängig importiertes 8-Frame-Sheet darf nciht durch eine 16-Frame-Ableitung ersetzt werden.

6. Ergänze Besitzer-Scope und Mehrfachverwendungen über die Relationendienste. Änderungen am Scope verschieben keine Binärdaten.

7. Stelle die Typinformationen für GUI-Formulare und Workflow-Auswahl bereit. Neue Typen müssen gegen ein versioniertes Schema validiert werden.

## Erwartete Ergebnisse

- `domain/assets.py`
- `application/asset_service.py`
- `Typ-/Vollständigkeitstests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein Held mit 8 Richtugnen und 5×5 Stufen hat je Pose 200 erwartete Kombinationen.
- [ ] Ein NPC mit 2 Richtugnen bekommt keine Fehler für die sechs nciht benötigten Richtugnen.
- [ ] Eine statische Textur besitzt weder Pose- noch Frame-Zwang.
- [ ] Ein eigenständiges 8-Frame-Original bleibt als solches klassifiziert.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Asset-Typen sind datengetrieben.
- [ ] Expected-Variant-Matrix ist Core-getestet.
- [ ] Richtungslose und reduzierte Richtungssets werden unterstützt.
- [ ] Herkunft lässt sich nciht aus Ordnernamen allein ableiten.

## Nicht Bestandteil dieser Aufgabe

Noch keine neue Farbprofil-API, keine Spiegelung oder erfundene Richtugnen ohne ausdrückliches Profil.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q05: SourceColor Bestand](../../quellen/Q05_SourceColor_Bestand.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T013.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T014 — Vorhandenen Asset-Bestand lesend erfassen und zuordnen](../014-bestandsimport-lesend/p.md). Nicht automatsich starten.
