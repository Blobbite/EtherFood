# Gezielte Animations-Fixes

Dieser Ordner kann allein übernommen oder aus dem bisherigen Projekt herausgelöst
werden. Beide Python-Dateien sind vollständige Programme. Sie importieren weder
die Animationstests noch einander. Die lokale `venv.txt` enthält alle Pakete:
`numpy`, `pillow`, `opencv-python-headless`. OpenCV wird nur für die Interpolation
im Hauptfix benötigt; die Notfallvariante funktioniert auch nur mit NumPy/Pillow.

```bash
python3 -m pip install -r venv.txt
```

## Hauptfix: Framezahl erhalten

Bei `… 15 → 16 (= 1) → 1 …` wird die Startpose zwei Framezeiten lang angezeigt.
`PyImgAnimFix.py --fix duplicate-end` entfernt die Schlusskopie aus der
Bewegungsgrundlage und erzeugt daraus wieder genau die ursprüngliche Anzahl
Frames. Raster, Zellgröße und bekannte Framezeiten bleiben erhalten.

| Eingabe | Hauptfix | Separater Notfall-Fix |
| --- | --- | --- |
| 16 Frames, letzter doppelt | 16 Frames, ursprüngliches Raster | 15 Frames |
| 12 Frames, letzter doppelt | 12 Frames, ursprüngliches Raster | 11 Frames |
| 10 Frames, letzter doppelt | 10 Frames, ursprüngliches Raster | 9 Frames |
| 8 Frames, letzter doppelt | 8 Frames, ursprüngliches Raster | 7 Frames |

Unterstützt werden 3 bis 24 Eingabeframes. Für die Interpolation müssen nach Abzug
der Schlusskopien mindestens drei Posen übrig sein. Mehrere direkt aufeinander
folgende Schlusskopien werden gemeinsam berücksichtigt.

```bash
# Erst nur prüfen und den geplanten Fix im Terminal anzeigen:
python3 PyImgAnimFix.py --fix duplicate-end -f 16 --grid 4x4 bild.png

# Geprüftes Ergebnis als neue PNG samt Metadaten speichern:
python3 PyImgAnimFix.py --fix duplicate-end -f 16 --grid 4x4 --apply bild.png

# Weitere Framezahlen:
python3 PyImgAnimFix.py --fix duplicate-end -f 12 --grid 4x3 --apply bild.png
python3 PyImgAnimFix.py --fix duplicate-end -f 10 --grid 5x2 --apply bild.png
python3 PyImgAnimFix.py --fix duplicate-end -f 8 --grid 4x2 --apply bild.png
```

Als installierter Linux-Wrapper können dieselben Argumente beispielsweise an
`PyImgAnimFix` übergeben werden. Die Programme verwenden den aktuellen
Arbeitsordner für die automatische PNG-Suche, unabhängig vom Installationsort.

Die Interpolation schätzt die Bewegung zwischen benachbarten Posen in beiden
Richtungen mit [OpenCV/Farneback](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html).
Die Bildwerte werden entlang dieser Bewegung [neu abgetastet](https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html)
und mit berücksichtigter Transparenz verbunden. Der gesamte zyklische Ablauf wird
neu aufgeteilt; die doppelte Pose wird dadurch nicht einfach an eine andere
Stelle verschoben. Der erste Frame bleibt erhalten, andere Frames können sich
ändern.

**Das sind geschätzte Zwischenbilder.** Besonders bei Verdeckungen, wechselnden
Details, harten Pixelrastern oder großen Formänderungen können Fehler entstehen.
Das Programm prüft Bewegungsübereinstimmung, sichtbaren Rekonstruktionsfehler,
Flächenverlust und zusätzliche Doppelbilder. Diese Prüfungen ersetzen keine
Sichtprüfung der erzeugten Animation. Bei unzuverlässiger Interpolation endet
der Hauptfix ohne neue Dateien mit Exitcode 3; er reduziert die Framezahl nie
automatisch.

`--sampling nearest` verwendet eine stärkere Bindung an das Pixelraster, kann aber
weiterhin gemischte Farben/Alpha-Werte erzeugen. `linear` ist der Standard.
`--max-warp-error` steuert die erlaubte Abweichung der Bewegungsschätzung
(Standard 0.20); ein größerer Wert akzeptiert auch unsicherere Zwischenbilder.

## Separater Notfall-Fix: Schlussframe entfernen

```bash
python3 PyImgAnimFixDropEnd.py -f 16 --grid 4x4 bild.png
python3 PyImgAnimFixDropEnd.py -f 16 --grid 4x4 --apply bild.png
```

`PyImgAnimFixDropEnd.py` entfernt nur die erkannten Schlusskopien. Bei einem
doppelten Schlussframe wird aus 16 beispielsweise 15. Die verbleibenden
RGBA-Bildpixel werden unverändert kopiert. Das neue Raster enthält genau einen
Platz pro Frame; aus einem 4×4-Raster wird für 15 Frames standardmäßig 5×3.
`--output-grid` erlaubt ein anderes passendes Raster.

Der Player muss anschließend die neue Framezahl und das neue Raster verwenden.
Bei gleicher FPS wird der Loop um die entfernte Framezeit kürzer. Mit bekannten
Zeiten kann `--keep-duration` stattdessen die Gesamtdauer erhalten, indem es die
verbleibenden Framezeiten verlängert:

```bash
python3 PyImgAnimFixDropEnd.py -f 16 --grid 4x4 --fps 8 --keep-duration --apply bild.png
```

## Erkennung, Zeiten und Ausgabedateien

Standardmäßig werden Schlusskopien anhand exakt gleicher sichtbarer RGBA-Werte
erkannt. Unterschiedliche RGB-Werte vollständig transparenter Pixel werden
ignoriert. Eine komplett statische Folge wird nicht automatisch umgebaut.
Bei nur optisch gleicher Pose mit leicht anderen Pixeln kann der Benutzer den
Schlussframe mit `--end-is-duplicate` ausdrücklich als Kopie bestätigen.

Ohne `--apply` werden keine Dateien oder Ordner geschrieben. Ohne Dateiangabe
werden die PNGs im aktuellen Arbeitsordner bearbeitet, ohne Rekursion;
bereits erzeugte `*_loopfix.png` werden bei dieser automatischen Suche übersprungen.
Explizit angegebene Dateien sind einzeln auswählbar.

Die Original-PNG und ihre Metadaten bleiben erhalten. Der Hauptfix schreibt zum
Beispiel `bild_loopfix.png` und `bild_loopfix.anim.json`. Die Notfallvariante
verwendet `*_dropend_loopfix.png`, aktualisiert Rasterhinweise im Dateinamen und
schreibt eine passende `.anim.json`. `--output-dir` wählt den Zielordner;
`--replace-output` erlaubt das Ersetzen bereits vorhandener Fix-Ergebnisse.

Framezahl, Raster und Zeiten können aus `<Dateistamm>.anim.json` gelesen werden:
`frames`, `grid` als `"4x4"` oder `{"cols":4,"rows":4}`, `fps` oder `durations_ms`.
CLI-Zeitangaben über `--fps` beziehungsweise `--durations` haben Vorrang. Ohne
bekannte Zeiten wird keine FPS angenommen oder in die Ausgabe geschrieben.
Die neuen Metadaten enthalten Framezahl, Raster, bekannte Framezeiten, die
Fix-Beschreibung und gegebenenfalls `regions_profile`. Andere ursprüngliche
Metadaten bleiben in der Originaldatei; sie werden nicht ungeprüft auf die
geänderte Animation übertragen.

## Andere gezielte Korrektur: Position

Die bisherige geometrische Korrektur ist explizit als `--fix position` erreichbar:

```bash
python3 PyImgAnimFix.py --fix position --region bottom --strength 0.7 -f 16 --grid 4x4 bild.png
python3 PyImgAnimFix.py --fix position --region bottom --strength 0.7 -f 16 --grid 4x4 --apply bild.png
```

Sie verschiebt die gewählte Zone (`top`, `middle`, `bottom`, `full`, optional
heuristisch `auto`) schrittweise. Sie behebt weder doppelte Posen noch allgemeine
Form- oder Texturfehler und wird nicht zusammen mit dem Schlussframe-Fix angewendet.
Ohne `--fix` zeigt der Hauptaufruf nur einen Befund an.

| Exitcode | Bedeutung |
| --- | --- |
| 0 | Prüfung/gewählter Fix erfolgreich oder keine Schlusskopie gefunden |
| 1 | Grundlegende Python-Pakete fehlen |
| 2 | Ungültige Eingabe, fehlendes OpenCV oder Schreibfehler |
| 3 | Keine verlässliche Korrektur mit der gewählten Methode |
| 130 | Vom Benutzer abgebrochen |
