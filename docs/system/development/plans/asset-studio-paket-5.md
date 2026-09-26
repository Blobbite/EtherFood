# Arbeitsplan: Asset Studio, Paket 5

## Zweck und Ausgangslage

26.09.2026: Paket 4a wurde vom Benutzer in allen acht Sichtprüfpunkten ohne
Mängel abgenommen. Freigegeben sind nun ausschließlich T013/#20 und T014/#21:
Asset-Anforderungen modellieren und vorhandene Dateien lesend erfassen.
Ausgangscommit: `ba1c01c`. Katalog, Pfadschutz, Beziehungen, Statusresolver und
Desktop sind vorhanden. Die neuen Funktionen erweitern diese Dienste.

## Umfang und Nicht-Ziele

- Versionierte, datengetriebene Asset-Typen, Posen mit stabilen IDs, geordnete
  Richtungen, Grafik-/Frameprofile, getrennte FPS und ausdrücklich erfasste Herkunft.
- Erwartete Varianten: bei 8 Richtungen und fünf Grafik-/Frameprofilen 200 je
  animierter Pose; statische Inhalte ohne erfundene Pose-/Framepflicht.
- Expliziter, begrenzter, abbrechbarer Scan gewählter Ordner; PNG-/Rasterprüfung,
  Konflikte, Dubletten, externe historische Reports und sichere Vergleichsverweise.
- Bewusste Übernahme ausschließlich von Katalogmetadaten und Herkunftsverweisen;
  Originaldateien bleiben unverändert. Vollständigkeit ist keine Freigabe.

Kein Quellenkopierimport (T015), vollständiger Anlageassistent/Held-Menü (T016),
Bildverarbeitung, neue Animation, automatische Richtungserkennung aus Bildinhalten,
Godot-Bereitstellung oder produktive Asset-Freigabe. Keine Änderungen an Spielkanon.
Vorhandene lokale Control-, Dokumentations- und Grafikänderungen bleiben erhalten
und werden nicht in Paket-5-Commits aufgenommen.

## Schritte und Fortschritt

- [x] 4a-Abnahme dokumentieren, Issues #56–#59 abschließen und Basis prüfen.
- [x] T013: Modelle, Schema, Dienste und kleine Konfigurationsoberfläche testen.
- [x] T014: lesenden Scanner und externe Nachweis-/Linkprüfung testen.
- [x] T014: Übernahmeprüfung, explizite Katalogübernahme und GUI-Ablauf testen.
- [x] Wiederholung, Abbruch, Revisionsschutz und tatsächlichen Bestand lesend prüfen.
- [x] Studio-/Pipeline- und Repository-Prüfungen mit tatsächlichen Ergebnissen.
- [x] Ergebnisberichte, Commit/Push, Issues und nächstes Benutzerbriefing.

## Entscheidungen und Erkenntnisse

- Domain bleibt Qt- und dateisystemfrei; Originale werden weder umbenannt noch
  verschoben oder korrigiert. Es wird kein Legacy-Starter auf Originalen ausgeführt.
- `walk` und `slowwalk`, `SW` und `SO`, Frames und FPS sind unterschiedliche Werte.
  Der Scanner macht nachvollziehbare Vorschläge aus Namen, Raster und Metadaten;
  semantische Laufrichtung und Bewegungsqualität benötigen eine Sichtprüfung.
- Unklare Herkunft bleibt unklar. `PixelEng` oder ein Fram8-Ordner beweisen nicht,
  ob eine Animation ein eigenständiges Original oder eine Ableitung ist.
- Alte Reports bleiben historische Fremdaussagen, selbst bei passenden Hashes.
  Unpassende oder nicht prüfbare Bindungen werden sichtbar, nie als Erfolg importiert.
- Je abgeschlossenen Abschnitt: gezielte Tests, englischer Emoji-Commit und Push.
  Menschliche Abnahme und technische Fertigstellung werden getrennt ausgewiesen.
- Asset-Anforderungen liegen als ein versionierter Satz im bestehenden Asset-
  Datensatz. Pose-UUIDs bleiben bei Änderungen erhalten; kein zweiter editierbarer
  Dateikatalog entsteht. Erkannte Varianten sind Beobachtungen, keine Builds.

## Prüfstrategie und Rückbauschutz

Zuerst Core-Tests mit temporären synthetischen Dateien, dann echte Qt-Ereignisse.
Negative Fälle: falsche Version/Felder, fehlende/unnötige Varianten, doppelte Namen,
Rasterwiderspruch, beschädigte PNGs, Größenlimits, Symlinks, Traversal, veraltete
Reports, geänderte Dateien nach Scan, Wiederholung ohne Dubletten, Abbruch und
Konflikte ohne halbe Katalogübernahmen. Nur tatsächlich ausgeführte Tests melden.
Reale Grafikdateien höchstens lesend prüfen; Hashvergleich vor/nach dem Scan.
Keine pauschalen Git-Rücksetzungen, keine automatischen Reparaturen oder Löschungen.

## Ergebnis und Rückblick

Technische Umsetzung abgeschlossen. Paket endet mit einer neuen Prüfliste,
nicht mit dem Start von T015. Persönliche Sichtprüfung noch offen.

Zwischenprüfung T013: 35 gezielte Tests bestanden (Modelle, Dienste, echter
Qt-Dialog). 200 Varianten, zweigerichtete Pose, statische Textur, getrennte
Frames/FPS, Konflikt-/Versionsschutz, persistente Pose-ID und Erhalt eines
eigenständigen 8-Frame-Originals geprüft. Noch kein Scan implementiert.

Zwischenprüfung T014: 102 Studio-Tests bestanden; darunter reales Qt-Scannen,
bewusste Einzelauswahl, erneute Übernahme ohne Dubletten und Abbruch/Schließen
bei laufendem Leser. Migration 3 speichert lokale Wurzeln getrennt von
portablen Snapshot-Daten. Fremdberichte sind nie aktuelle Prüfungen; HTML
wird ausschließlich als sicherer Text gelesen. Scanner und Dialog heißen
`inventory_scan.py`, `inventory_service.py` und `ui/inventory.py`.

Vertiefung: 107 Studio-Tests bestanden, zusätzlich Rollback bei Reportfehler
und spätem Abbruch, unabhängiges 8-Frame-Original gegen neue Ableitung,
PNG-Header/CRC und veränderte Berichtquellen. Echter Walk-Bestand: 200 PNGs
als 200 Varianten erkannt, 200 `.import` ausgelassen; alle 400 Datei-SHA256
vorher/nachher identisch. Keine Quellenübernahme in einen produktiven Katalog.
Qt-Oberflächen zusätzlich als temporäre Screenshots geprüft; Spaltenbreiten
angepasst. Das ersetzt nicht die persönliche Sichtabnahme auf dem Zielrechner.

Abschließende Prüfung:

- `python3 tools/control.py asset-manager check`: **109 Studio-Tests und
  171 Legacy-Pipeline-Tests bestanden**; Qt offscreen mit temporären nativen
  Bibliotheken. Auch sichere HTML-Textansicht und unbekannte Modellversion
  beim Projektöffnen geprüft. Keine neuen Abhängigkeiten ergänzt.
- Gezielte Stilprüfung: **57 Studio-Quell-/Testdateien, 0 Befunde**.
- `python3 tools/control.py check`: **257 bestanden, 37 übersprungen,
  2 fehlgeschlagen** (bestehende Dokumentationslücken/13 Verweise); Godot 4
  fehlt; **1907 bestehende Stilbefunde in 223 Dateien**. Kein neuer Studio-
  Stilbefund und keine Umgehung durch Eingriffe in Kanon oder Gamedesign.
- Alle 400 Dateien des tatsächlichen Walk-Bestands per SHA256 unverändert;
  kein produktiver Quellimport und keine automatische Freigabe.

Bereits gepushte Abschnitte: `856a448` (4a-Abnahme/Umfang), `1fe73e3`
(T013), `7bc50fb` (T014), `fc4ec30` (Schutzfälle und reale Bestandsprüfung).
Ergebnisberichte T013/T014 und SICHTPRUEFUNG_5 bilden den abschließenden
Dokumentationsabschnitt. Issues #20/#21 erhalten technische Nachweise und
bleiben bis zur persönlichen Rückmeldung offen. #22/#23 bleiben unbegonnen.

Die technischen Checklisten von #20/#21 sind mit den tatsächlich geprüften
Kriterien aktualisiert; eine eigene offene Sichtprüfungszeile trennt die
Benutzerabnahme ausdrücklich davon. Handoff: [SICHTPRUEFUNG_5](../asset-studio/SICHTPRUEFUNG_5.md).
