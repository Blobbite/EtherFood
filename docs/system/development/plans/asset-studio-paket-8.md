# Paket 8 – freie Farbreferenzen und gebundene Materialmasken

## Auftrag und Ausgangslage

28.09.2026: Benutzer beauftragt T019/#26 und T020/#27 aus Phase C. Maßgeblich
sind die aktuellen Issues samt PIPELINE-ALIGNMENT-V1 und der vorhandene Code.
Die lokalen Control-/Pipeline-/Hierarchiekorrekturen bleiben erhalten.

Die vorhandenen PyGameTools erzeugen und laden drei Farbprofilarten, deren
Version 1 acht Stand-Richtungen verlangt. Studio hat echte Bildadapter,
unveränderliche Quellen, Blobstore und Rezeptressourcen. Masken werden technisch
geprüft; eigene Materialdefinitionen, Referenzwahl, Maskenrevisionen und getrennte
Sichtbestätigungen fehlen noch als zusammenhängender Bedienweg.

## Umfang und Entscheidungen

- Version 1 und bisherige CLI-Aufrufe unverändert erhalten. Neue Version 2 für
  ausdrücklich gewählte Farbreferenzen; Grafik-/Auflösungsprofile bleiben separat.
- Neue Referenzwahl speichert Quellenrevision, Hash, Pose/Richtung, Raster,
  Framezahl und gleiche Gewichtung je Referenz/Frame. Gemischte Raster vor der
  Profilbildung verständlich ablehnen. Keine künstlichen Referenzrichtungen.
- Materialdefinitionen und Masken über vorhandene unveränderliche Katalogtypen
  und Blobstore versionieren. Technische Prüfung und konkrete menschliche
  Sichtbestätigung bleiben getrennt. Alte oder importierte Masken erhalten keine
  automatische Bestätigung. L/P-Indexwerte und Originalbytes bleiben erhalten.
- Gemeinsame Loader, CLI, Studio-Dienste und vorhandene Bildadapter erweitern;
  keine zweite Ausführung. Auswahl-/Maskenänderungen wirken nur auf abhängige
  Farbschritte. Das Anlegen/Importieren startet keinen Bildbuild.
- Bedienung im Asset-Menü: Referenzen wählen, Profile erzeugen/zuweisen,
  Materialien definieren, Masken importieren/prüfen und Revisionen ansehen.
  Pixelmalwerkzeuge aus T021 und automatische Vorschläge aus T022 folgen separat.
- Keine Produktionsbilder bearbeiten, keine Game-Freigaben und kein Godot-Export.

## Arbeitsschritte und Fortschritt

1. [x] Aktuelle Issues, Datenmodell, alte Farbverträge und Bedienwege prüfen.
2. [x] Gemeinsames v2-Format, Profilbildung, Loader, CLI und Vergleich erweitern.
3. [x] Referenz-/Material-/Maskendienste mit Revisions- und Quellschutz umsetzen.
4. [x] Wirksame Ressourcen an den vorhandenen Build-/Cacheweg anbinden.
5. [x] Asset-Bedienung mit Vorschau, Revisionen und verständlichen Fehlern ergänzen.
6. [x] Synthetische Core-/CLI-/Bild-/GUI-Regressionen und zentrale Checks ausführen.
7. [x] Bedienung, Kompatibilität, Ergebnisse und konkrete Grenzen dokumentieren.

## Prüfungen und Wiederherstellung

Zuerst kleine synthetische PNGs: zwei Richtungen, statische Referenz, v1-Erhalt,
v2-Roundtrip, unbekannte Version, Quelländerung, Materialabdeckung, unbeschriftete
Entwürfe, P-PNG-Indizes, konkrete Frame-/Pixelbefunde, Revisionskonflikte und
fehlende Sichtbestätigung. Anschließend echte Bilderzeugung, selektiver Cache,
Neuladen und Qt-Bedienung. Vollständiger Standardlauf zuletzt; vorhandene
unabhängige Repository-Probleme getrennt berichten.

Unveränderliche Vorgängerrevisionen und Originale werden nicht überschrieben.
Übernahmen verwenden den bestehenden geprüften Blobimport und Katalogtransaktionen;
unvollständige Importe werden nicht aktiviert. Keine pauschale Bereinigung.

## Ergebnisse

Technisch umgesetzt. Abschließender Lauf über die zentrale Steuerung:
**624 Studio-Tests bestanden** (143,55 s), **171 Pipeline-Bestandstests bestanden**
(35,48 s). Darin 29 neue Core-/CLI-/Qt-Fälle einschließlich statischer Referenz,
exklusivem Datei-Export, Schemafehlern, echter Bildverarbeitung und Sichtstatus.
Qt-Offscreen-Ansichten für Referenzen und Masken mit synthetischen Bildern
zusätzlich geöffnet und visuell geprüft. Keine persönliche Bedienabnahme.

`python3 tools/control.py check` tatsächlich ausgeführt: **283 bestanden,
37 übersprungen, 4 bekannte Fehler**. Fehlende Greenhero-Unterordner,
fehlendes `window/size/resizable=true` und zwei Dokumentationsprüfungen wegen
fehlender Game-Entscheidungsdateien bleiben offen. Godot 4 fehlt; dessen
Integrationstest wurde nicht ausgeführt. Der globale Stilcheck meldet
1903 Bestandsbefunde in 332 Dateien; neue/geänderte Zeilen in den 38 veränderten
Python-Dateien ohne Befund. `git diff --check` sauber.

Die historische Planprüfung besteht unverändert: 48 Aufgaben, 36 Anforderungen,
955 lokale Links und 81 geschützte Dateihashes. Befehle und konkrete Nachweise
stehen in den Ergebnisberichten.

Erkenntnisse: Die vorhandenen unveränderlichen Katalogtypen reichen aus; keine
zusätzliche SQL-Migration nötig. `QDialog.finished` ist ein Qt-Signal und darf
nicht als Methodenname für den Workerabschluss überschrieben werden. Eine
Nullmasken-Vorlage bleibt auch bei vollständig transparenten Quellen ein Entwurf.

[Bedienung und Verträge](../asset-studio/REFERENZEN_UND_MASKEN.md),
[T019](../asset-studio/task-results/T019.md),
[T020](../asset-studio/task-results/T020.md). Persönliche Abnahme, T021-Malen,
automatische Vorschläge und Godot-Bereitstellung werden nicht vorweggenommen.
