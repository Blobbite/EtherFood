# Paket 7 – Notizen trennen, Aufträge und Buildplanung

Historischer Paketbericht zu `4ef37bd`/`4b16da4`: Die damalige Begrenzung auf
Diagnose/Help ist durch das spätere Bildpipelinepaket `2286d2f` erweitert.
Aktuelle Restaufträge und Vertrauensgrenzen folgen
[PIPELINE-ALIGNMENT-V1](asset-studio-github-issues.md), nicht einem erneuten
Neubau oder Rückbau der vorhandenen Worker-/Graphdienste.

## Auftrag und Ausgangslage

Der Benutzer beauftragt am 27.09.2026 die vollständige Umsetzung von T017 und
T018 sowie die Korrektur der Notiznavigation. Notizen springen über Baum/Suche
noch in die Dokumentation; ihre Bearbeitung soll im Notiz-Dashboard liegen.
Grundlage sind T003/T005/T008/T013/T015, vorhandene Verträge und sichere
Originalablage. Bereits vorhandene Game-/Control-Änderungen bleiben unberührt.

## Umfang und Entscheidungen

- Ein gemeinsamer Notiz-Einstieg für Baum, Canvas, Suche und Kontext. Eingebettete
  Bearbeitung samt Anhängen im Dashboard; Dokumentation bleibt getrennt.
- T017: eingefrorene Aufträge, registrierte Adapter, getrennte Job-Arbeitsräume,
  persistente Zustände/Ereignisse/Logs, sichere Argumentlisten, Zeitlimit,
  Abbruch einschließlich Kindprozessen, Parallelitäts-/Schreibsperren, Recovery.
  Core ohne Qt, Qt-Prozesssteuerung ohne blockierendes Warten im Hauptthread.
- Zunächst synthetischer Prüflauf und lesende Help-/Dry-run-Aufrufe auf isolierten
  Kopien. Keine beliebigen importierten Skripte oder produktiven Bildläufe.
- T018: typisierter Buildgraph, inhaltliche Fingerprints, vollständig verifizierter
  Cache, Dry-run, gezielte transitive Veraltung, unveränderliche Historie und
  Vergleich von Plan und Ausführung. Keine Godot-/Künstlerfreigaben erfinden.
- Keine Umsetzung von T019 oder späteren Bildalgorithmen. Fehlende Adapter und
  fachliche Eingaben ehrlich als blockiert anzeigen.

## Arbeitsschritte

1. [x] Vorgänger, Schutzregeln und Issue-Verträge prüfen.
2. [x] Notiznavigation und eingebettete Bearbeitung korrigieren.
3. [x] Notiz-Regressionen prüfen, dokumentieren, committen und pushen (`8c3a561`).
4. [x] T017: Jobverträge, Ablage und Adapter implementieren.
5. [x] T017: Core-/Qt-Prozesssteuerung, Abbruch und Recovery implementieren.
6. [x] T017: GUI/CLI einbinden, testen, dokumentieren, committen und pushen (`4ef37bd`).
7. [x] T018: Graph, Fingerprints und verifizierten Cache implementieren.
8. [x] T018: Asset-Dry-run und Plan-/Ausführungsvergleich einbinden.
9. [x] T018: Veraltung, Cache-Schäden, Graphfehler und Wiederaufnahme testen.
10. [x] Gesamtläufe, echte Qt-Ansicht, Dokumentation und Briefing abschließen.
11. [x] T018 gezielt committen/pushen und Remote-Stand prüfen (`4b16da4`).

## Prüfungen und Erkenntnisse

Zuerst passende kleine Testgruppen. Danach zentraler Studio-/Pipeline-Check,
Stilprüfung, Repository-Standardcheck und synthetische Qt-Sichtprüfung. Echte
Prozessprüfungen müssen Exit 7, fehlende Ausgaben trotz Exit 0, Timeout, Abbruch
mit Kindprozess, freie GUI und Recovery belegen. Für T018 gezielte Masken- und
Masteränderungen, reine Umbenennung, defekte Cachedateien/Reports und Zyklen.
Ergebnisse und Entscheidungen werden während der Umsetzung ergänzt.

Notizkorrektur: 267 Studio-Tests bestanden, darunter alle vier Einstiege,
eingebettetes Speichern mit Strg+S, Anhänge, Konflikte und Entwurfsschutz.
Qt-Offscreen-Ansicht mit einem synthetischen Projekt tatsächlich geöffnet.
Notizen erscheinen nicht mehr in der Dokumentationsauswahl.

T017: 12 echte Prozess-/Qt-Prüfungen bestanden; gesamter Studio-Lauf 279
bestanden. 103 Quell-/Testdateien ohne Stilbefund. Abbruch mit Kindprozess,
Exit 7, Exit 0 ohne Datei, Zeitlimit, Startfehler, Elternabsturz, Recovery,
Schreibergrenzen, Originalschutz und echter FramReduce-Help-Aufruf geprüft.
Sichere Prozessgruppen zunächst Linux mit /proc; andere Plattformen werden
ehrlich abgewiesen. Kein unkontrollierter Ausweichstart.

T018: Gesamter Studio-Lauf 304 bestanden. Änderungen an Walk-/Mastermasken,
unabhängige Tempelzweige, Timing/Tool/Algorithmus/Quelländerung, Namens-/Layout-
Neutralität, beschädigte/fehlende/zusätzliche Cachedateien, Zyklen, Wiederaufnahme,
Neustart, Nur-Lese-CLI und unveränderte Historie geprüft. Qt-Namenskonflikt
mit QObject.event im Test gefunden, behoben und anschließend im gemeinsamen
Buildplan-/Canvas-Lauf sowie vollständigen Studio-Lauf verifiziert.

Abschlussprüfung: Zentraler Asset-Manager-Check 304 Studio- und 171 Pipeline-
Tests bestanden; nach Darstellungsnachbesserung 19 weitere passende Qt-Tests.
111 Studio-Dateien ohne Stilbefund. Vier echte Qt-Ansichten synthetischer
Projekte visuell geprüft. Standardcheck weiter rot: 259 bestanden, 37 skipped,
2 alte Dokumentationsfehler, 13 defekte Verweise, Godot 4 fehlt, 1907 geerbte
Stilbefunde. Keine zusätzlichen Studio-Befunde. Kurzes Briefing unter
`../asset-studio/SICHTPRUEFUNG_7.md`.

## Wiederholbarkeit und Schutz

Temporäre synthetische Projekte; Originale nur lesen/kopieren. Keine rekursive
Bereinigung unbekannter Daten, keine automatische Cachelöschung, keine Shell-
Interpolation. Laufende fremde Aufträge nicht pauschal töten. Nur eigene Pfade
stagen. Commits mit englischem Emoji-Titel, danach Push wie beauftragt.

## Ergebnis

Notizkorrektur (`8c3a561`), T017 (`4ef37bd`) und T018 (`4b16da4`) separat
committed und nach main gepusht. Remote-Hash für T018 stimmt mit lokalem HEAD
überein. Beide GitHub-Issues enthalten Ergebnisnachweise und das Testbriefing;
sie bleiben bis zur Benutzer-Prüfrunde offen. Persönliche Bedienprüfung und
spätere Produktivfreigaben bleiben von technischen Tests getrennt; nächste
Bildaufgaben nicht vorgezogen. Fremde Änderungen bleiben uncommitted erhalten.
