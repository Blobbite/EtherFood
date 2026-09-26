# Festfarben umgesetzt

Stand: 24.09.2026. Arbeitsverzeichnis: `/workspace`.

Die bestehende Color-Pipeline unterstützt jetzt `soft`, `fixed` und `material`.
Alte Aufrufe behalten den weichen Farbtransform. Neue Profile, Materialmasken,
CLI-Kombinationen und vorhandene Ausgaben werden vor dem Schreiben geprüft.
Gemeinsamer Code liegt in `Pipline/PiplineToos/PyImgFixedColors.py` und ist im
Installer registriert. Die gültigen Optionen stehen in der [README](README.md).

## Vorhandene Ergebnisse

| Ergebnis | Inhalt |
| --- | --- |
| [Materialvergleich](../../spritesheet-material/farbvergleich.html) | 32 eingefärbte Sheets mit festen Materialfarbreihen, acht bytegleiche Stand-Kopien; insgesamt 40 PNG-/GIF-Paare. |
| [Festfarbenvergleich](../../spritesheet-fixed/farbvergleich.html) | 32 eingefärbte Sheets mit gemeinsamer 64-Farben-Palette, acht bytegleiche Stand-Kopien; insgesamt 40 PNG-/GIF-Paare. |
| [Maskenansicht](../../spritesheet/materialmasken/masken-vorschau.html) | Alle 40 Masken einschließlich Stand, 640 Frames, acht Material-IDs und Hintergrund. |
| [Masken und Farbreihen](../../spritesheet/materialmasken/README.md) | Dateien, konkrete Zielfarben, Bearbeitungshinweise und Befehle für die weitere Arbeit. |
| [Abschlussprüfung](../../spritesheet/materialmasken/abschluss-pruefung.json) | Technische Prüfungen, Canvas-Backups und Browserergebnisse. |

`spritesheet/` enthält weiterhin die 40 unveränderten Original-PNGs.
`spritesheet-color/` mit dem früheren Soft-Ergebnis blieb vollständig erhalten.
Die Masken liegen im neuen Unterordner `spritesheet/materialmasken/`; die
Quellsuche verarbeitet diese Unterordner nicht als Original-Sheets.

## Materialmasken: Entwürfe

Die Masken sind ausgefüllt und technisch gültig. Sie wurden aus betrachteten
Stand-Farbproben und der Silhouette jedes einzelnen Frames vorgeschlagen.
Eine Stand-Maske wurde nicht auf andere Animationen kopiert. Raster und
Quellhash binden jede Maske an das jeweilige Original.

Die künstlerische Materialzuordnung ist **noch nicht vollständig bestätigt**.
Insbesondere Metall/Stoffbesatz, Haut/helles Leder, dunkle Umhangfalten und
Materialgrenzen benötigen eine gezielte Sichtprüfung. Dieser offene Punkt ist
in den Maskenmetadaten und Berichten als Entwurfsstatus dokumentiert. Eine
gültige Material-ID ist kein Nachweis der richtigen semantischen Zuordnung.

Die acht Materialfarbreihen enthalten zusammen 45 Stufen. Sie wurden aus allen
acht gelabelten Stand-Richtungen abgeleitet und übernehmen die Unsicherheit der
Masken. Die globale 64-Farben-Palette benötigt keine Materialmasken.

## Durchgeführte Prüfungen

- 160 Tests bestanden: 113 Projekttests und 47 Resolution-Tests, darunter 38 neue Festfarben-/Materialtests.
- Beide tatsächlichen Ausgaben geprüft: zusammen 80 PNGs und 80 GIFs.
- Jeder eingefärbte sichtbare PNG-Pixel gehört exakt zur jeweiligen Zielpalette oder Materialfarbreihe.
- Alpha, unsichtbares RGB und Bildgröße erhalten; alle Sheets weiterhin 16x1 mit 10240×640 Pixeln.
- Alle 16 Stand-Kopien der beiden neuen Ausgaben bytegleich zu ihren Originalen.
- Alle GIFs mit 16 Quellframes, 2000 ms Zyklusdauer und Endlosschleife.
- Alle 123 Dateien des bisherigen Original-/Soft-Bestands per SHA-256 unverändert bestätigt.
- Drei HTML-Ansichten in Chromium geprüft: jeweils 40 Sheets mit Frames 0, 7 und 15, insgesamt 360 Frameprüfungen; Wiedergabe, Maskenpositionen und Alpha synchron, keine JavaScript- oder Ladefehler.
- Alle fünf Canvas-Dateien vor Änderungen als `.canvas.bak` gesichert; nur die Color-Canvas angepasst.

Die Testumgebung verwendete Python 3.11 und Pillow 12.3. Die Pipeline benötigt
weiterhin Python ab 3.10 und Pillow ab 10.3. Playwright/Chromium waren nur
Prüfwerkzeuge und sind keine zusätzliche Pipeline-Abhängigkeit.

## Weiterarbeit

Zuerst die [Maskenansicht](../../spritesheet/materialmasken/masken-vorschau.html)
und den [Materialvergleich](../../spritesheet-material/farbvergleich.html)
beurteilen. Nach Änderungen an Stand-Masken die Materialfarbreihen erneut
exportieren und die Materialausgabe mit `--dry-run --overwrite` prüfen.
Die konkreten Befehle stehen in der Masken-README. Originale weiterhin als
Quellen verwenden.

`SpritesheetResolution --palette-profile` liest weiterhin das bisherige
`reference-colors.json`; neue Festfarben-/Materialprofile sind ein anderes
Format. Comic-Skalierung kann Mischfarben erzeugen und benötigt für erneut
exakte RGB-Werte einen ausdrücklichen weiteren Festfarbenabgleich.
