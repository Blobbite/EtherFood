# Paket 7 – Notizen trennen, Aufträge und Buildplanung

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
6. [ ] T017: GUI/CLI einbinden, testen, dokumentieren, committen und pushen.
7. [ ] T018: Graph, Fingerprints und verifizierten Cache implementieren.
8. [ ] T018: Asset-Dry-run und Plan-/Ausführungsvergleich einbinden.
9. [ ] T018: Veraltung, Cache-Schäden, Graphfehler und Wiederaufnahme testen.
10. [ ] Gesamtläufe, echte Qt-Ansicht, Dokumentation und Briefing abschließen.
11. [ ] T018 gezielt committen/pushen und Remote-Stand prüfen.

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

## Wiederholbarkeit und Schutz

Temporäre synthetische Projekte; Originale nur lesen/kopieren. Keine rekursive
Bereinigung unbekannter Daten, keine automatische Cachelöschung, keine Shell-
Interpolation. Laufende fremde Aufträge nicht pauschal töten. Nur eigene Pfade
stagen. Commits mit englischem Emoji-Titel, danach Push wie beauftragt.

## Ergebnis

In Arbeit. Persönliche Bedienprüfung und spätere Produktivfreigaben bleiben
von technischen Tests getrennt.
