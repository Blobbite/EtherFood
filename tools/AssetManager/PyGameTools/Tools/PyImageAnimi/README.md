# PyImgAnimTest

Die vier Einzelprüfungen sind jeweils vollständige Python-Programme. Jede Datei
enthält ihre Eingabeprüfung, Berechnungen und Berichte und kann allein kopiert,
installiert und durch einen Linux-Wrapper gestartet werden.

| Programm | Aufgabe |
| --- | --- |
| `PyImgAnimTestLoopBild.py` | Bildähnlichkeit zwischen letztem und erstem Frame |
| `PyImgAnimTestLoopFluss.py` | Bewegungs- und Bildfortsetzung an der Loop-Naht |
| `PyImgAnimTestBewegungsruhe.py` | Kurze Rückschritte im gesamten Loop |
| `PyImgAnimTestDetails.py` | Lokale Textur- und Konturfortsetzung |
| `PyImgAnimTestAll.py` | Die vier Programme nacheinander starten und die Gesamtnote berechnen |
| `PyImgAnimTest.py` | Derselbe vollständige Sammelaufruf unter dem bisherigen Namen |

Eigenständige Korrekturprogramme samt eigener Paketliste liegen im abtrennbaren Ordner
[`PyImageAnimiFix`](PyImageAnimiFix/README.md).

## Pakete und Installation

Die benötigten Pakete stehen ausschließlich in `venv.txt`: NumPy und Pillow.
Die vorhandene Installations-Pipeline kann diese Liste für ihre venv verwenden.
Für eine manuell angelegte venv lautet der Paketaufruf:

```bash
python3 -m pip install -r venv.txt
```

Die Einzelprogramme importieren keine anderen Projektdateien. Sie funktionieren
auch mit `PYTHONSAFEPATH=1` und einem Arbeitsordner außerhalb ihres Installationsorts.
PNG-Dateien werden im aktuellen Arbeitsordner gesucht; explizite Dateipfade sind
ebenfalls möglich.

Der Sammelaufruf sucht jede Einzelprüfung zunächst neben seiner eigenen, über
`__file__` aufgelösten Datei. Dort startet er sie mit demselben Python-Interpreter.
Andernfalls sucht er den installierten Befehl im `PATH`, zuerst ohne `.py`, dann
mit `.py`. Ein solcher Wrapper verwendet seine eigene konfigurierte venv.
Argumente werden ohne Shell weitergegeben, und der Arbeitsordner bleibt erhalten.

## Aufrufe

```bash
python3 PyImgAnimTestLoopFluss.py -f 16 --grid 4x4 bild.png
python3 PyImgAnimTestBewegungsruhe.py -f 16 --grid 4x4 bild.png
python3 PyImgAnimTestAll.py -f 16 --grid 4x4 bild.png

# Nach Installation als Wrapper, beispielsweise:
PyImgAnimTestAll -f 16 --grid 4x4 bild.png

# Bisheriger Einstieg, einschließlich Auswahl einer Einzelprüfung:
python3 PyImgAnimTest.py --test loop-image -f 16 --grid 4x4 bild.png
```

`--test` ist bei den Sammelaufrufen verfügbar: `all`, `loop-image`, `loop-flow`,
`calmness` und `details`. Die Einzelprogramme führen jeweils ihre eigene Prüfung aus.
Die übrigen Optionen für Raster, Zeiten, Metadaten und Bereiche sind erhalten;
`--help` zeigt sie an. Ohne Dateiangabe werden PNGs im aktuellen Arbeitsordner
geprüft; `*_loopfix.png` wird erst mit `--include-fixed` einbezogen.

## Berichte und Rückgabewerte

Die Original-PNGs werden nur gelesen. Berichte entstehen unter `.compare/` oder
`--output-dir`. `--no-report` schreibt keine Dateien oder Ordner, auch beim
Sammelaufruf. Dieser übernimmt die Ergebnisse seiner Unterprogramme direkt über
deren Standardausgabe und erzeugt seine Berichte selbst.

Einzelberichte enthalten nur die jeweilige Prüfung, beispielsweise
`bild_animtest_loop_flow.json` und `animtest_loop_flow_index.html`. Der Gesamtlauf
behält `bild_animtest.json` und `animtest_index.html`. Die Namen kollidieren nicht.
Bewertungsformeln und Gesamtbericht entsprechen weiterhin der bisherigen Fassung.

| Exitcode | Bedeutung |
| --- | --- |
| 0 | Analyse erfolgreich |
| 2 | Eingabe, Unterprogramm oder Bericht fehlerhaft |
| 3 | `--fail-below` unterschritten oder verlangte Wertung nicht bewertbar |
| 130 | Durch Benutzer abgebrochen |

Bei Einzelprüfungen gilt `--fail-below` nur für deren Wertung. Bei `TestAll` gelten
wie bisher Gesamt, Loop-Fluss, Bewegungsruhe und konfigurierte Details. Eine
niedrige Wertung stoppt die nachfolgenden Prüfungen nicht.

## Detailbereiche

Der Detailtest verwendet weiterhin `detail_regions` in einem über `--regions`
angegebenen JSON-Profil oder im `regions_profile` der `.anim.json`-Metadaten:

```json
{
  "space": "subject",
  "regions": {},
  "detail_regions": {
    "cloth": {"label": "Stoff", "box": [0.2, 0.2, 0.8, 0.8]}
  }
}
```

Die Koordinaten beziehen sich auf das gemeinsame Motiv-Rechteck. Ohne ausgewählte
Bereiche ist die Detailwertung nicht bewertbar. Bewegungsruhe und Details
benötigen mindestens sechs Frames für eine Wertung.
