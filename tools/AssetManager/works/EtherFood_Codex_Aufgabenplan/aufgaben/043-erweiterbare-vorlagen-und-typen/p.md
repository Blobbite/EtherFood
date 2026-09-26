---
task_id: T043
phase: F
status: not_started
depends_on: ["T008", "T013", "T018", "T029", "T030", "T041"]
requirements: ["R30"]
---
# T043 — Erweiterbare Kartentypen und Pipeline-Vorlagen bereitstellen

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** F — Betrieb und Gesamtprüfung  
**Abhängigkeiten:** [T008](../008-workflow-und-statusmodell/p.md), [T013](../013-assettypen-posen-und-richtungen/p.md), [T018](../018-buildplan-cache-und-invalidation/p.md), [T029](../029-assetpakete-und-tempel/p.md), [T030](../030-pipeline-bedienung-im-dashboard/p.md), [T041](../041-versionsvergleich-und-projektfortschritt/p.md)  
**Anforderungsbezug:** R30

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Ermögliche neue verwaltete Inhaltstypen, ohne für jeden NPC oder jedes Paket eigene Skriptkopien anzulegen.

## Kontext und Bestandsgrenzen

Neue Inhalte sollen weitgehend aus Daten entstehen. Neue Verarbeitungsverfahren brauchen weiterhin implementierten und getesteten Code.

## Umsetzungsschirtte

1. Veröffentliche ein versioniertes Schema für Kartentypen, Fähigkeiten, Formfelder, Pflichtschritte, Prüfkriterien und bekannte Pipeline-Rezepte.

2. Implementiere eine Registry ausschließlich vertrauenswürdiger eingebauter Worker. Eine Vorlagendatei darf keine Shell-Befehle, eval-Ausdrücke oder beliebig importierbaren Python-Code enthalten.

3. Baue einen einfachen Vorlageneditor für Name, Geltungsbereich, Richtungs-/Posenpreset, Grafik-/Frameprofile und aktivierte Schritte. Zeige inkompatible Kombinationen vor dem Speichern.

4. Erhalte die verwendete Vorlagenrevision an jedem Asset. Eine globale Vorlagenänderung zeigt einen Änderungsplan, migriert bestehende Assets aber nciht still.

5. Ergänze Beispiele für globalen animierten Effekt, statischen Hintergrund, NPC mit zwei Richtugnen und aktbezogenes Tempelpaket. Verwende dieselben Dienste und keine namensabhängigen Sonderwege.

6. Implementiere Export/Import von Vorlagen mit Schema-Prüffung. Unbekannte Worker oder Schema-Versionen machen die Vorlage nciht ausführbar und werden verständlich gemeldet.

7. Dokumentiere den Erweiterungsvertrag für Entwickler: Adapter, Ein-/Ausgabeschema, Vorschau, Prüfschritte und Regressionstests. Keine dynamische Plugin-Plattform als Voraussetzung aufbauen.

## Erwartete Ergebnisse

- `domain/template_registry.py`
- `ui/template_editor.py`
- `Vorlagenbeispiele und Erweiterungsanleitung`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Ein globaler animierter Effekt nutzt Frame-Verarbeitung unabhängig vom Scope.
- [ ] Ein statischer Hintergrund hat keine künstliche Animationspflicht.
- [ ] Eine neue Vorlagenrevision verändert alte Assets erst nach bewusster Übernahme.
- [ ] Eine importierte Vorlage mit fremdem Shell-Befehl wird abgelehnt.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Vorlagen sind praktisch editierbar und versioniert.
- [ ] Fähigkeiten bestimmen die Verarbeitung.
- [ ] Unbekannte Verfahren werden nciht als verfügbar ausgegeben.
- [ ] Es gibt mindestens vier unterschiedliche geprüfte Typvorlagen.

## Nicht Bestandteil dieser Aufgabe

Kein Plugin-Marktplatz, keine automatsich nachinstallierten Worker und keine externen KI-Dienste.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

Diese Aufgabe konkretisiert den [Projektbrief](../../grundlagen/PROJEKTBRIEF.md) und die [Zielarchitektur](../../grundlagen/ARCHITEKTUR.md). Sie behauptet keine beriets vorhandene Implementierung.

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T043.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T044 — Sicherung, Wiederherstellung und Speicherpflege absichern](../044-backup-recovery-und-speicherpflege/p.md). Nicht automatsich starten.
