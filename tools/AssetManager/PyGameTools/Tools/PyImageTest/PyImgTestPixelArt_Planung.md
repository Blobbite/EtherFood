# PyImgTestPixelArt / Pixel-Pipeline – offene Planung

## Status

Dieses Dokument sammelt mögliche Ziele und Umsetzungswege. Es wird bewusst
noch kein Pixel-Art-Test implementiert, weil zuerst geklärt werden muss, ob
die HD-Grundassets, das konvertierte Zwischenprodukt oder das tatsächlich von
Godot gerenderte Ergebnis die verbindliche Referenz bilden.

## Ausgangslage

Die Grundassets sollen hochauflösende HD-Pixel-Art-Bilder sein. Die endgültige
Darstellung beziehungsweise weitere Pixel-Art-Umwandlung geschieht in der
Engine. Vorgesehene Farbprofile sind unter anderem 64 und 24 Farben.

Ein klassischer Test wie „jede Kante muss bereits im Quellbild auf einem
niedrig aufgelösten Pixelraster liegen“ wäre deshalb möglicherweise falsch.
Er könnte hochwertige Quelldetails beanstanden, obwohl die Engine sie erst im
nächsten Schritt korrekt reduziert.

## Wichtige begriffliche Trennung

`PyImgTestPalette.py --palette-colors 64` bedeutet:

- höchstens 64 repräsentative CIELAB-Analysetöne werden für den
  Konsistenzvergleich ausgewählt;
- die Auswahl kann früher enden, wenn mindestens 95 Prozent Farbdeckung
  erreicht sind;
- zusätzlich warnt das Werkzeug, wenn tatsächlich mehr als 64 sichtbare
  RGB-Quellfarben gefunden werden.

Es ist weiterhin kein vollständiger Engine-Exporttest und keine Garantie,
dass Godot genau eine gewünschte 64- oder 24-Farben-Palette rendert.

Ein späterer harter Farbtest muss deshalb ausdrücklich festlegen:

- ob die Grenze für Quelle, Konvertergebnis oder Engine-Ausgabe gilt;
- ob halbtransparente Pixel als eigene Farbvarianten zählen;
- ob eine feste Palette oder nur eine maximale Farbanzahl verlangt wird;
- ob Dithering erlaubt ist;
- ob vollständig transparente Pixel und deren versteckte RGB-Werte zählen.

## Drei mögliche Testebenen

### Ebene A – HD-Quellasset

Ein leichter, engine-unabhängiger Test könnte prüfen:

- unterstütztes verlustfreies Dateiformat
- Abmessungen und Alpha-Kanal
- vollständig transparente Randbereiche
- unerwartete Alpha-Halos
- sichtbare RGB-Farbanzahl mit Profil 64 oder 24
- unbeabsichtigte JPEG-Artefakte
- konsistente Farb- und Transparenzregeln innerhalb einer Assetgruppe

Diese Ebene darf keine niedrige Zielauflösung oder Engine-Filterung
voraussetzen. Sie ergänzt die drei vorhandenen Bildtests, überschneidet sich
aber teilweise mit ihnen.

### Ebene B – deterministisches Konvertergebnis

Falls ein eigener Konverter oder Importprozess die HD-Quelle reduziert, sollte
dessen Ausgabe separat getestet werden:

- korrekte Zielauflösung
- harte Einhaltung von 64 beziehungsweise 24 sichtbaren Farben
- erwartete Palette oder erlaubte Farbtoleranzen
- gewünschtes Dithering
- Erhalt von Silhouette und wichtigen Kanten
- kein unbeabsichtigtes Weichzeichnen
- keine neuen Alpha-Halos
- keine verlorenen kleinen, als wichtig markierten Details
- deterministische Ausgabe bei identischer Eingabe

Diese Ebene ist gut mit Python und pytest automatisierbar, sofern der
Konvertierungsschritt außerhalb oder unabhängig von Godot reproduzierbar ist.

### Ebene C – tatsächlicher Godot-Import und Render

Dies ist die aussagekräftigste, aber aufwendigste Ebene. Ein kleines
Godot-Testprojekt importiert die Assets mit denselben Einstellungen wie das
Spiel und rendert sie headless in definierte Referenzszenen.

Mögliche Prüfungen:

- tatsächlich verwendete Textur-Importeinstellungen
- keine unerwünschte lineare Filterung
- korrektes Verhalten bei ganzzahliger und nicht ganzzahliger Skalierung
- Mipmapping und Kompression entsprechend dem Projektprofil
- keine Farbmischung oder Randblutung im Atlas
- korrekte Sprite-Region, Pivotposition und Zuschnitt
- Alpha-Ränder auf hellen und dunklen Hintergründen
- sichtbare Farbanzahl im gerenderten Ergebnis
- Übereinstimmung zwischen Editor-, Headless- und Zielplattform-Render
- reproduzierbare Screenshots für Regressionstests

Die genauen Importoptionen dürfen erst nach Festlegung der verwendeten
Godot-Version benannt und festgeschrieben werden. Sie können sich zwischen
Engine-Versionen und Renderern unterscheiden.

## Empfehlung: hybrider Test statt reiner Python- oder Godot-Lösung

Voraussichtlich ist eine Aufteilung am sinnvollsten:

1. Godot importiert und rendert die echten Assets in einem minimalen,
   versionierten Testprojekt.
2. Godot exportiert Diagnosebilder und strukturierte Metadaten in einen
   temporären Ordner.
3. Python analysiert Farbanzahl, Alpha, Kanten, Rastertreue und Abweichungen.
4. pytest startet den Ablauf und prüft die erwarteten Ergebnisse.

Dadurch entscheidet Godot über Import und Rendering, während die bestehenden
Python-Bildmetriken wiederverwendet werden können.

## Vorläufige Profile

### Profil `hd64`

- HD-Quelle bleibt erhalten.
- Die verbindliche Prüfstufe muss noch festgelegt werden.
- Zielausgabe besitzt höchstens 64 sichtbare RGB-Farben, falls dies eine harte
  Projektanforderung ist.
- Dithering- und Alpha-Regeln sind konfigurierbar.

### Profil `hd24`

- dieselben Grundregeln wie `hd64`
- höchstens 24 sichtbare RGB-Farben auf der festgelegten Prüfstufe
- strengere Prüfung auf Detailverlust und Zusammenfallen wichtiger Farbtöne

### Profil `custom`

- frei angegebene Palette oder maximale Farbanzahl
- Zielauflösung, Skalierung, Alpha- und Ditheringregeln aus einem Manifest

Die Profile dürfen nicht automatisch aus Dateinamen abgeleitet werden.

## Möglicher Manifestentwurf

```json
{
  "schema_version": 1,
  "engine": {
    "name": "godot",
    "version": "noch-festzulegen",
    "renderer": "noch-festzulegen"
  },
  "profile": "hd64",
  "source": "hero_hd.png",
  "expected_output": {
    "width": 128,
    "height": 128,
    "maximum_visible_rgb_colors": 64,
    "alpha_policy": "noch-festzulegen",
    "dithering": "noch-festzulegen",
    "integer_scale": true
  }
}
```

Das Manifest ist nur ein Diskussionsentwurf. Insbesondere Engine-Version,
Renderer und Konvertierungsstufe dürfen nicht mit Platzhaltern in eine echte
CI-Prüfung übernommen werden.

## Sinnvolle Bildmetriken

Quelle und Ziel besitzen möglicherweise unterschiedliche Auflösungen. Ein
direkter Pixel-für-Pixel-Vergleich wäre daher unbrauchbar. Nach einer klar
definierten Normalisierung kommen folgende Messungen infrage:

- Silhouetten-IoU und Veränderung der sichtbaren Fläche
- Abstand und Erhalt markierter Konturen
- Kantenrichtung und Kantendichte
- CIELAB-Abstand wichtiger Farbbereiche
- Anteil verlorener kleiner Komponenten
- Alpha-Fransen auf mehreren Hintergrundfarben
- Block- beziehungsweise Rasterkonsistenz
- Zahl echter sichtbarer RGB-Werte
- Verteilung der Zielpalette

Ein hoher Ähnlichkeitswert allein genügt nicht: Ein kleines Auge, eine
Waffenspitze oder ein Fußkontakt kann spielerisch wichtig sein, obwohl er nur
wenige Pixel umfasst. Solche Regionen müssten optional im Manifest markiert
werden.

## pytest- und Projektstruktur als Möglichkeit

```text
tests/pixel_pipeline/
  test_source_assets.py
  test_hd64_profile.py
  test_hd24_profile.py
  test_palette_budget.py
  test_alpha_edges.py
  test_scaling_filter.py
  test_atlas_bleeding.py
  test_godot_import.py
  test_godot_headless_render.py
  test_pixel_pipeline_history.py

test-projects/godot-pixel-pipeline/
  project.godot
  scenes/
  scripts/
```

Das Godot-Testprojekt sollte klein sein und ausschließlich die im echten
Projekt verwendeten Import- und Renderbedingungen nachbilden.

## Reports und Verlauf

Falls der Test umgesetzt wird, soll er dieselbe Bedienlogik wie die anderen
Werkzeuge erhalten:

```text
.compare/pixel_pipeline_figure_<UTC-ID>.png
.compare/pixel_pipeline_report_<UTC-ID>.md
.compare/pixel_pipeline_report_<UTC-ID>.json
```

Ein Verlauf ist nur vergleichbar bei identischer Quelle, Zielkonfiguration,
Engine-Version, Renderer, Farbprofil und Bewertungsmodell. Ein Wechsel von 64
auf 24 Farben ist eine Konfigurationsänderung und kein Fortschritt oder
Rückgang.

`--no-report` darf keine Historie lesen und keine Reportdateien erzeugen.

## Mögliche CI-Strategie

Die Prüfungen sollten nach Schwere getrennt werden:

- Warnung: HD-Quelle enthält mehr Farben als das gewünschte Zielprofil.
- Fehler: verbindliches Konvertergebnis überschreitet sein hartes Farblimit.
- Fehler: falsche Abmessungen, fehlende Frames oder ungültiges Alpha.
- Fehler: Godot rendert mit einer verbotenen Filter- oder Importkonfiguration.
- Warnung oder Fehler nach Kalibrierung: zu großer Detail- oder
  Silhouettenverlust.

Die jetzige Warnung in `PyImgTestPalette.py` bleibt bewusst score-neutral, bis
geklärt ist, auf welcher Pipeline-Stufe das Farblimit verbindlich gilt.

## Umsetzungsoptionen

### Option 1 – Nur Quellasset-Test

Vorteile:

- einfach und schnell
- keine Godot-Abhängigkeit
- gut für frühe Warnungen

Nachteile:

- prüft nicht das tatsächliche Spielergebnis
- kann gewünschte HD-Eigenschaften fälschlich beanstanden

### Option 2 – Nur Godot-Integrationstest

Vorteile:

- prüft den echten Import- und Renderweg
- erkennt engine-spezifische Fehler

Nachteile:

- komplexerer CI-Aufbau
- abhängig von Godot-Version und Renderer
- Ursachenanalyse ohne zusätzliche Python-Metriken schwieriger

### Option 3 – Hybride Pipeline

Vorteile:

- prüft die reale Engine-Ausgabe
- detaillierte und wiederverwendbare Bildanalyse
- klare Trennung zwischen Importfehler und Bildabweichung

Nachteile:

- größter anfänglicher Implementierungsaufwand

Vorläufige Empfehlung: Option 3 untersuchen, aber erst nach einem kleinen
Machbarkeitstest verbindlich auswählen.

## Umsetzungsphasen

### Phase 0 – Entscheidung und Machbarkeit

- verwendete Godot-Version und Renderer erfassen
- echte Importkonfiguration dokumentieren
- klären, wo die Farbquantisierung stattfindet
- je ein repräsentatives 64- und 24-Farben-Beispiel auswählen
- headless Import und Screenshot im Zielsystem ausprobieren

### Phase 1 – Regeln festlegen

- verbindliche Pipeline-Stufe bestimmen
- Farb-, Alpha-, Dithering- und Skalierungsregeln festlegen
- Warnungen und CI-Fehler trennen

### Phase 2 – Kleiner Prototyp

- ein Asset durch die echte Pipeline führen
- Godot-Ausgabe automatisiert speichern
- sichtbare Farbanzahl, Alpha und Skalierung prüfen
- Laufzeit und Reproduzierbarkeit messen

### Phase 3 – Testprofile und pytest

- `hd64`, `hd24` und `custom` implementieren
- Positiv- und Negativ-Fixtures anlegen
- Godot- und Python-Fehler getrennt berichten

### Phase 4 – Reports und CI

- Terminal, Markdown, JSON und Diagnosefigur ergänzen
- sicheren Vorher-Nachher-Vergleich einbauen
- erst nach Projektkalibrierung harte CI-Grenzen aktivieren

## Noch offene Entscheidungen

- Welche Godot-Version und welcher Renderer werden verbindlich verwendet?
- Konvertiert Godot selbst, ein Shader, ein Import-Plugin oder ein externes
  Werkzeug?
- Werden die konvertierten Texturen gespeichert oder nur zur Laufzeit erzeugt?
- Gilt das 64-/24-Farben-Limit für jede Datei, jede Animation, jeden Atlas oder
  die gesamte Figur?
- Ist die Palette frei oder projektweit fest vorgegeben?
- Ist Dithering erlaubt, erforderlich oder verboten?
- Welche Alpha-Werte sind zulässig?
- Welche Zielauflösungen und Skalierungsfaktoren gelten?
- Müssen mehrere Zielplattformen oder Renderer verglichen werden?
- Welche kleinen Details sind spielerisch unverzichtbar?
- Soll der Pixel-Pipeline-Test später Teil von `PyImgTestAll.py` werden oder
  als engine-spezifische Stufe getrennt bleiben?

## Entscheidungskriterium für eine spätere Implementierung

Der Test sollte erst gebaut werden, wenn mindestens folgende Angaben feststehen:

- verbindliche Engine-Version
- verbindliche Prüfstufe
- Zielauflösung
- Profil 64 oder 24 und dessen genaue Bedeutung
- Alpha- und Ditheringregeln
- automatisierbarer Zugriff auf ein reproduzierbares Engine-Ergebnis

Bis dahin liefern die drei vorhandenen Bildtests plus die neue
Quellfarbenwarnung eine sinnvolle frühe Kontrolle, ohne noch ungeklärte
Engine-Regeln als Fehler festzuschreiben.

