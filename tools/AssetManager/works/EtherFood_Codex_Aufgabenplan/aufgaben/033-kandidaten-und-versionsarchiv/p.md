---
task_id: T033
phase: E
status: not_started
depends_on: ["T005", "T018", "T029", "T032"]
requirements: ["R19", "R20", "R25"]
---
# T033 — Unveränderliche Kandidaten und Versionsarchiv implementieren

**Arbeitsauftrag an Codex:** Führe ausschließlich diese Aufgabe aus. Implementiere die genannten Ergebnisse innerhalb des Scopes, prüfe sie tatsächlich und dokumentiere offene Punkte. Arbeite nciht automatsich an späteren Aufgaben weiter.

**Phase:** E — Versionen und Godot-Freigabe  
**Abhängigkeiten:** [T005](../005-pfade-und-objektspeicher/p.md), [T018](../018-buildplan-cache-und-invalidation/p.md), [T029](../029-assetpakete-und-tempel/p.md), [T032](../032-variantenpruefung-und-fehlerkarten/p.md)  
**Anforderungsbezug:** R19, R20, R25

## Vor dem Start lesen

Lies gültige lokale Repository-Anweisungen, [Arbeitsregeln](../../grundlagen/ARBEITSREGELN_CODEX.md), [Projektbrief](../../grundlagen/PROJEKTBRIEF.md), [Architektur](../../grundlagen/ARCHITEKTUR.md) und [Datenverträge](../../grundlagen/DATENVERTRAEGE.md). Prüfe die tatsächliche Implementierung und Berichte der angegebenen Vorgänger. Fehlende Voraussetzungen werden konkret dokumentiert, nciht durch erfundene Datein oder erfolgreiche Tests ersetzt.

## Ziel

Friere geprüfte Asset- und Paketstände so ein, dass sie unabhängig von späteren Workspace-Änderungen nachvollziehbar bleiben.

## Kontext und Bestandsgrenzen

EtherFood_AssetVersions ist der gewünschte Bereich für ausgewählte Versionen. Ein Kandidat ist ein unveränderlicher Inhaltssnapshot; Prüfungen und Freigaben werden als eigene Datensätze daran angehängt.

## Umsetzungsschirtte

1. Definiere Candidate mit Asset-/Paket-ID, Build-ID, vollständiger Dateiliste, Ergebnisdigests, Rezept-/Tool-Versionen, Quellen-/Profil-/Maskenbezügen und Prüfstand zum Einfrierzeitpunkt.

2. Erstelle selbsttragende Kandidatenpakete oder eine verifizierte Archivablage mit sämtlichen referenzierten Blobs. Ein frei werdender Cache oder umbenannter Workspace darf eine freigegebene Version nciht unbrauchbar machen.

3. Kopiere Kandidaten zuerst in einen temporären Zielbereich auf dem Archiv-Dateisystem. Prüfe Vollständigkeit und Hashes, registriere anschliesend das unveränderliche Ergebnis; keine Veränderung eines vorhandenen Kandidaten.

4. Berechne einen kanonischen Payload-Digest ohne selbstreferenziellen Hash und ohne volatile Zeitstempel. Der vollständige Snapshot enthält zusätzlich ein Herkunftsmanifest und Erstellungsdaten.

5. Behandle ExportBundle als späteres, ebenfalls unveränderliches Derivat eines Kandidaten. Es darf den Kandidaten nciht durch nachträglich hineingeschriebene Godot-Datein verändern.

6. Erzeuge portable Vorschau-/Dokumentationspakete aus mitgenommenen Quellen und Ergebnissen. Führe vorhandene relative HTML-Verweise zusammen oder generiere die Ansicht vor dem Einfrieren neu; keine Verweise auf flüchtige Arbeitsordner.

7. Ermögliche lesendes Öffnen und Vergleichen alter Kandidaten. Weiterbearbeiten erstellt einen neuen Entwurf mit expliziter Herkunft.

## Erwartete Ergebnisse

- `application/candidate_service.py`
- `storage/version_archive.py`
- `Kandidaten-/Portabilitäts-Tests`

Die Pfade sind Zielvorschläge, sofern T001 keinen konkreten Bestandspfad festgelegt hat. Passe sie an die reale Codebasis an und dokumentiere die Zuordnung. Benenne bestehende Pipeline-Datein nciht allein wegen dieser Vorschläge um.

## Verbindliche Tests

- [ ] Eine Workspace-Maskenänderung verändert keine Kandidatendatei.
- [ ] Ein Kandidat bleibt nach Verschieben oder Entfernen des Build-Caches vollständig prüfbar.
- [ ] Gleiche kanonische Nutzdaten ergeben denselben Payload-Digest trotz anderer Erstellungszeit.
- [ ] Abbruch beim Archivieren hinterlässt keinen vermeintlich vollständigen Kandidaten.

Ergänze die relevanten Regressionstests des Bestands. Ein nciht ausgeführter GUI-/Godot-Test bleibt ausdrücklich offen. Technische Testfixtures dürfen keine echten künstlerischen oder produktiven Freigaben erzeugen.

## Abnahmekriterien

- [ ] Kandidaten sind inhaltlich unveränderlich.
- [ ] Jede archivierte Datei ist per Hash überprüfbar.
- [ ] Quell-/Profil-/Maskenherkunft ist vollständig.
- [ ] HTML- und Dokumentationspakete bleiben portabel.

## Nicht Bestandteil dieser Aufgabe

Keine automatische Produktivfreigabe und kein pauschales Kopieren des gesamten Workspace.

## Daten- und Rückbauschutz

Nutze die gemeinsamen Pfad-, Besitz- und Revisionsregeln. Bei Abbruch bleiben Originale und bestätigte Vorgängerstände erhalten. Entferne nur eindeutig eigene temporäre Test-/Arbeitsdateien; dokumentiere unvollständige Operationen und ihre Wiederaufnahme. Kein pauschaler Repository- oder Ordnerreset.

## Quellen und technische Grundlage

- [Q01: FramReduce Bestand](../../quellen/Q01_FramReduce_Bestand.md)
- [Q02: Resolution Bestand](../../quellen/Q02_Resolution_Bestand.md)
- [Q04: Farbpipeline Bestand](../../quellen/Q04_Farbpipeline_Bestand.md)
- [Q07: Workspace Skizze](../../quellen/Q07_Workspace_Skizze.md)

Ergänzende API-Dokumentation steht unter [offizielle Referenzen](../../grundlagen/OFFIZIELLE_REFERENZEN.md). Die passende installierte Version ist im Checkout zu prüfen.

## Abschluss und Übergabe

Schreibe `docs/asset-studio/task-results/T033.md` nach der [Ergebnisvorlage](../../vorlagen/ERGEBNISBERICHT.md). Nenne tatsächlich geänderte Datein, Verträge, ausgeführte Testbefehle, Ergebnisse und verbleibende Blocker. Setze `done` nur bei erfüllten Abnahmekriterien; andernfalls `partial` oder `blocked`. Die Abschlussmeldung endet mit den konkret erfüllten Voraussetzungen für eine Folgeaufgabe, nciht mit einer fingierten Gesamtfreigabe.

Nächste Aufgabe in der empfohlenen Reihenfolge: [T034 — Git-Anbindung und Quellenrevisionen ergänzen](../034-git-und-quellenrevisionen/p.md). Nicht automatsich starten.
