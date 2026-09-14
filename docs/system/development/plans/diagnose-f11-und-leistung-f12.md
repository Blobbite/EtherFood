<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: Spieldiagnose auf F11 und Leistungsanzeige auf F12

## Zweck und Ausgangslage

Die bisherige F3-Diagnose des visuellen Testlabors mischt Spielzustand und
FPS in einem umrahmten Panel. Gewünscht sind zwei unabhängig schaltbare
Anzeigen mit ausschließlich weißem Text: die bisherigen Spiel- und
Darstellungswerte auf F11, Leistungs- und Technikwerte auf F12, ohne
Dopplungen. Die vorherigen Arbeiten an den vier Hero-Grafikvarianten und
Testassets bleiben erhalten.

## Umfang und Schritte

1. Bestehende Eingaben, Anzeige, Tests und verfügbare Messquellen prüfen.
2. F11/F12, rahmenlose Anzeigen und beide Schalter im F5-Menü integrieren.
3. FPS, Framezeiten, RAM, VRAM, Datenträger-I/O und weitere technische
   Messwerte mit eindeutiger Herkunft und Verfügbarkeitsanzeige ergänzen.
4. Verhalten und Messwertberechnung gezielt prüfen; Bedienung dokumentieren.
5. Standardprüfung ausführen, Änderungen gegen vorhandene Fehler abgleichen
   und Ergebnis festhalten.

Nicht enthalten sind Änderungen an Spielregeln, Grafikassets oder
versionierten Spielstandards sowie externe Hardware-Monitoring-Abhängigkeiten.

## Fortschritt

- [x] Eingaben, Darstellung, Tests und Godot-Messquellen geprüft.
- [x] Anzeigen und Menü integriert.
- [x] Technische Messung integriert.
- [x] Gezielte Prüfungen und Dokumentation abgeschlossen.
- [x] Standardprüfung und Abschlusskontrolle durchgeführt.

## Erkenntnisse und Entscheidungen

- F11 behält `dev_diagnostics_toggle` einschließlich Controller-Back.
  `dev_performance_toggle` wird als unabhängige F12-Aktion ergänzt.
- Beide Anzeigen starten verborgen, blockieren keine Spieleingaben und
  werden nicht gespeichert. Die Kontur und Fläche des alten Diagnosepanels
  entfallen; das F5-Menü behält seine bisherige Gestaltung.
- Godots Monitore liefern FPS, Framezeiten und die vom Spiel verwendeten
  Renderressourcen. VRAM wird als Godot-Belegung angezeigt, nicht als
  prozentuale Gesamtauslastung der Grafikkarte.
- System-RAM und freier Datenträgerplatz kommen aus Godots OS-/DirAccess-API.
  Unter Linux liefern `/proc/self/status` und `/proc/self/io` zusätzlich
  Prozess-RAM und tatsächliche Datenträger-Lese-/Schreibzähler. Fehlende
  Werte werden ausdrücklich als nicht verfügbar angezeigt. Es werden keine
  Hilfsprozesse oder zusätzlichen Abhängigkeiten gestartet.
- F12 aktualisiert nur bei sichtbarer Anzeige und in begrenztem Takt. Für
  I/O-Raten ist eine zweite Probe erforderlich; erneutes Einblenden setzt
  die Messbasis zurück.

## Prüfungen

- Godot-Import einschließlich der neuen Skript-UIDs erfolgreich.
- Gezielte Godot-Suiten `input_map_test`, `visual_lab_performance_test` und
  `visual_lab_controls_test`: ohne Fehler. Geprüft wurden unabhängige Tasten,
  weißer Text ohne Panel, getrennte Spalten, Menü, fortlaufende Bewegung,
  verborgene Anzeigen ohne Messung, I/O-Neustart beim Einblenden,
  nicht gespeicherte Sichtbarkeit, I/O-Berechnung und echter Linux-procfs-Zugriff.
- `python -m unittest tools.tests.test_godot_project -q`: 21 Tests bestanden.
- `python tools/control.py style`: 88 Dateien ohne Stilabweichungen.
- `git diff --check`: erfolgreich.
- `python tools/control.py check`: Doctor und Stilprüfung erfolgreich,
  211 Python-Tests bestanden, ein bereits vorhandener Strukturfehler durch
  den ignorierten lokalen Ordner `docs/concept/.obsidian/`. Godot-Import
  erfolgreich, anschließend dieselben 75 Godot-Erwartungsfehler wie im
  vorherigen Lauf, überwiegend zu geänderten Spielstandards. Der Vergleich
  aller Fehlermeldungen einschließlich ihrer Häufigkeiten ergab keine
  hinzugefügten oder entfallenen Fehler.

Die Prüfungen liefen mit Godot im Headless-Modus. Textfarben, fehlender
Panel-Hintergrund und Spaltengeometrie sind automatisiert geprüft; eine
Sichtprüfung auf echter GPU und Messungen auf anderen Betriebssystemen
wurden in dieser Sitzung nicht ausgeführt.

## Wiederholbarkeit und Wiederherstellung

Die Tests verwenden isolierte `user://`-Konfigurationen. Anzeigen lassen
sich durch erneutes Drücken von F11/F12 wieder ausblenden. Es werden keine
Messprotokolle oder dauerhaften Systemdaten geschrieben. Korrekturen
beschränken sich auf die geänderten Diagnose-, Menü-, Test- und
Dokumentationsdateien; vorhandene Arbeitsbaumänderungen werden nicht
zurückgesetzt.

## Ergebnis und Rückblick

F11 und F12 sind unabhängig bedienbar und zeigen ausschließlich weißen Text.
FPS und die zusätzlichen Leistungsdaten befinden sich nur auf F12; die
bisherigen Spiel- und Darstellungswerte bleiben auf F11. Beide Schalter sind
auch im F5-Menü erreichbar. Quellen und Plattformgrenzen der technischen
Werte stehen in der aktualisierten Testlabor-Dokumentation. Die bestehenden
Grafikvarianten und Spielstandards wurden durch diese Arbeit nicht verändert.
