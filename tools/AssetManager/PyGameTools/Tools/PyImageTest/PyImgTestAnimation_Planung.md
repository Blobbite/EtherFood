# PyImgTestAnimation – Plan für spätere Umsetzung

## Status

Dieses Dokument ist eine fachliche und technische Vorplanung. Es wird noch
kein Animationstest implementiert. Profile, Grenzwerte und die genaue
Asset-Struktur müssen vor der Umsetzung mit echten Animationen überprüft
werden.

## Ziel

`PyImgTestAnimation.py` soll eine bereits zusammengestellte Animation als
zeitliche Sequenz prüfen. Die vorhandenen Werkzeuge bleiben für die
Einzelbilder zuständig:

1. `PyImgTestCompare.py` prüft Geometrie, Position, Alpha und Silhouette.
2. `PyImgTestPalette.py` prüft die Farbkonsistenz.
3. `PyImgTestBC.py` prüft Helligkeit und Kontrast.
4. Erst danach prüft `PyImgTestAnimation.py` Bewegung, zeitliche Übergänge und
   Schleifen.

Der Animationstest soll keine künstlerisch gewünschte Bewegung verhindern.
Er soll reproduzierbare technische Auffälligkeiten sichtbar machen und je
Animationstyp passende Regeln anwenden.

## Unterstützte Eingaben

Langfristig sollen drei Eingabeformen unterstützt werden:

### 1. Verzeichnis mit Einzelbildern

Dies ist die beste Form während der Erstellung. Die Reihenfolge muss über ein
Manifest angegeben werden. Eine alphabetische Sortierung darf höchstens ein
explizit gewählter Fallback sein.

### 2. Sprite-Sheet als PNG

Dies ist der wichtigste Testgegenstand, wenn genau dieses Sprite-Sheet in die
Engine importiert wird. Erforderliche Angaben:

- Breite und Höhe einer Zelle
- Zeilen- und Spaltenzahl
- Reihenfolge der Frames
- unbenutzte Zellen
- Pivot beziehungsweise Bodenanker
- Bildrate oder individuelle Frame-Dauern
- Schleifenverhalten
- Zuordnung von Clips und Richtungen

Diese Informationen können nicht zuverlässig allein aus den Pixeln erraten
werden.

### 3. Animiertes GIF, APNG oder WebP

Diese Form eignet sich zur Kontrolle einer fertigen Vorschau oder eines
tatsächlich ausgelieferten Animationsformats. Zusätzlich müssen Dauer,
Schleife, Transparenz und Frame-Disposal geprüft werden.

Ein GIF darf nicht automatisch als verlustfreie Referenz für HD-Assets gelten:
Seine Farb- und Transparenzbeschränkungen können Unterschiede verursachen oder
verdecken.

## Manifest statt Dateinamen-Auswertung

Dateinamen und Richtungswörter sollen keinen Messwert beeinflussen. Ein
explizites JSON-Manifest beschreibt stattdessen die fachliche Bedeutung der
Frames. Ein erster, noch unverbindlicher Entwurf:

```json
{
  "schema_version": 1,
  "source": {
    "type": "sprite_sheet",
    "file": "hero_animation.png",
    "frame_width": 256,
    "frame_height": 256,
    "columns": 8,
    "rows": 6
  },
  "clips": [
    {
      "id": "walk_north",
      "profile": "walk",
      "direction": "north",
      "frames": [0, 1, 2, 3, 4, 5, 6, 7],
      "fps": 12,
      "loop": true,
      "pivot": [128, 232],
      "root_motion": "in_place"
    }
  ]
}
```

`id` und `direction` dienen nur der Zuordnung und Darstellung. Das gewählte
`profile` aktiviert ausdrücklich die Regeln für den Animationstyp. Es wird
nicht aus dem Dateinamen abgeleitet.

## Gemeinsame Prüfungen für alle Animationstypen

Jedes Profil verwendet dieselbe Analysebasis:

- alle Frames lesbar, statisch dekodierbar und gleich groß
- korrekte Anzahl und Reihenfolge der Frames
- keine leeren oder unabsichtlich abgeschnittenen Frames
- Erkennung exakter Duplikate; erlaubte Halteframes müssen markierbar sein
- konsistente Alpha-Ränder und keine plötzlich auftauchenden Randpixel
- Veränderung von sichtbarer Fläche, Schwerpunkt und Bounding Box
- Position von Pivot, Bodenanker und Kontaktfläche
- registrierte Silhouetten-Überlappung benachbarter Frames
- Größe und Ort der Pixeländerung zwischen zwei Frames
- Geschwindigkeit und Beschleunigung der Schwerpunktbewegung
- zeitliches Flackern von Helligkeit, Kontrast und Palette
- Prüfung des Übergangs vom letzten zum ersten Frame bei Schleifen
- Beachtung individueller Frame-Dauern
- technische Prüfung von Sprite-Sheet-Zellen, Abständen und Randüberläufen

Eine einfache Pixel-Differenz reicht nicht aus. Vor dem Vergleich müssen die
Frames am definierten Pivot ausgerichtet werden. Gewollte Gliedmaßenbewegung
darf nicht als Positionszittern der gesamten Figur bewertet werden.

## Prüfprofile je Animationstyp

Die Messalgorithmen sollen gemeinsam implementiert werden. Jeder
Animationstyp erhält jedoch ein eigenes Profil und einen eigenen pytest-Fall,
damit seine fachlichen Erwartungen unabhängig getestet werden können.

| Profil | Eigener pytest | Erwartete Besonderheiten |
| --- | --- | --- |
| Stehen / Idle | `test_animation_idle.py` | Schleife, sehr stabiler Pivot, geringe Gesamtverschiebung, kleine Bewegungen erlaubt |
| Laufen / Walk | `test_animation_walk.py` | periodische Schleife, erkennbare Fußkontakte, mittlere Frameänderung, In-place und Root-Motion getrennt |
| Rennen / Run | `test_animation_run.py` | größere und schnellere Änderungen erlaubt, kürzere Kontaktphasen, Schleifennaht weiterhin stabil |
| Springen / Jump | `test_animation_jump.py` | meist keine Schleife, vertikale Flugkurve erlaubt, Start und Landung getrennt prüfen |
| Angriff / Attack | `test_animation_attack.py` | starke Silhouettenänderung erlaubt, Phasen Antizipation–Aktion–Erholung, Rückkehrpose optional |
| Schleichen / Sneak | `test_animation_sneak.py` | niedrigeres Profil, geringe vertikale Unruhe, langsame periodische Bewegung |

Später mögliche Profile:

- Trefferreaktion
- Tod
- Zaubern
- Klettern
- Schwimmen
- Interaktion
- Übergang zwischen zwei Zuständen

Ein Profil besteht aus konfigurierbaren Grenzwerten. Neue Typen sollen ohne
Kopieren des gesamten Analysealgorithmus ergänzt werden können.

## Profilabhängige Regeln

### Stehen / Idle

- Bodenanker und Pivot müssen nahezu unverändert bleiben.
- Ein vollständig eingefrorener Clip kann optional als Hinweis erscheinen.
- Kleine Atem-, Haar- oder Stoffbewegungen sind erlaubt.
- Der Schleifenübergang darf nicht stärker springen als normale Übergänge.

### Laufen / Walk

- Es muss zwischen In-place-Animation und tatsächlicher Root-Motion
  unterschieden werden.
- Fußkontakte dürfen als markierte Ereignisse im Manifest stehen.
- Die Bewegung soll periodisch sein; Links-/Rechtsphasen dürfen nicht exakt
  symmetrisch erzwungen werden.

### Rennen / Run

- Größere Schwerpunkt- und Silhouettenänderungen sind normal.
- Bewertet werden Ausreißer gegenüber der clipinternen Bewegungsdynamik, nicht
  dieselben absoluten Grenzwerte wie beim Stehen.

### Springen / Jump

- Das Verlassen des Bodenankers ist gewollt und darf nicht als Zittern gelten.
- Start, Aufstieg, Scheitelpunkt, Fall und Landung können als optionale Phasen
  im Manifest markiert werden.
- Eine Schleifenprüfung ist standardmäßig deaktiviert.

### Angriff / Attack

- Sehr große Änderungen einzelner Frames können gewollt sein.
- Antizipation, Trefferphase und Erholung benötigen unterschiedliche
  Grenzwerte.
- Optional wird geprüft, ob die Endpose wieder zum Ausgangszustand passt.

### Schleichen / Sneak

- Eine dauerhaft niedrigere Figur ist korrekt.
- Unbeabsichtigtes vertikales Wippen und rutschender Bodenkontakt sind stärker
  zu gewichten als beim Rennen.

## Bewertung

Vorgesehene Teilwerte:

- technische Frame-Integrität
- Pivot- und Bodenanker-Stabilität
- Bewegungsfluss
- Silhouettenkontinuität
- zeitliche Farb- und Lichtstabilität
- Schleifenqualität, falls anwendbar
- profilspezifische Regeln

Der Gesamtscore darf nur vergleichbare Messwerte zusammenfassen. Nicht
anwendbare Werte, beispielsweise eine Schleifennaht beim Sprung, werden nicht
mit null bewertet; ihr Gewicht wird auf die übrigen Teilwerte verteilt.

Kritische technische Fehler sollen zusätzlich zum Score einen Status setzen,
zum Beispiel eine ungültige Sprite-Sheet-Zelle oder ein nicht dekodierbarer
Frame.

## CLI-Entwurf

```text
PyImgTestAnimation.py INPUT
  --manifest DATEI
  --profile {idle,walk,run,jump,attack,sneak,custom}
  --frame-size BREITExHÖHE
  --fps ZAHL
  --loop | --no-loop
  --no-color
  --no-report
  --version
```

CLI-Werte dürfen Manifestwerte nur bewusst und sichtbar überschreiben. Der
Report muss die effektiv verwendete Konfiguration vollständig speichern.

## Ausgabe und Verlauf

Vorgesehene Dateien:

```text
.compare/animation_figure_<UTC-ID>.png
.compare/animation_report_<UTC-ID>.md
.compare/animation_report_<UTC-ID>.json
```

Die Figur soll mindestens Kontaktbogen, Schwerpunktverlauf, Frame-Differenzen
und Schleifennaht darstellen. Der Report enthält Gesamt- und Einzelwerte je
Übergang.

Ein Vorher-Nachher-Vergleich ist nur zulässig bei:

- identischem Clip und Framebestand
- identischer Reihenfolge und Dauer
- identischem Profil und Grenzwerten
- identischem Analysemodell

`--no-report` darf `.compare` weder lesen noch verändern und zeigt deshalb
keinen Verlauf.

## Vorgesehene pytest-Struktur

```text
tests/animation/
  test_animation_decode.py
  test_animation_manifest.py
  test_animation_idle.py
  test_animation_walk.py
  test_animation_run.py
  test_animation_jump.py
  test_animation_attack.py
  test_animation_sneak.py
  test_animation_history.py
  test_animation_cli.py
```

Jeder Profiltest benötigt kleine synthetische Positiv- und Negativbeispiele:

- sauberer Clip
- Pivot-Zittern
- einzelne extreme Frameänderung
- Helligkeits- oder Farbflackern
- schlechte Schleifennaht
- absichtlich erlaubte profilspezifische Bewegung

Zusätzlich sind später echte Projektclips als nicht öffentliche
Regressionsdaten sinnvoll.

## Umsetzungsphasen

### Phase 1 – Eingabevertrag festlegen

- tatsächliche Asset- und Sprite-Sheet-Struktur erfassen
- Manifestformat festlegen
- Mindestliste der Animationstypen bestimmen
- Pivot-, Root-Motion- und Loop-Regeln festlegen

### Phase 2 – Neutraler Sequenzkern

- Frames aus Ordner, Sprite-Sheet und animiertem Format extrahieren
- gemeinsame Zeitachse aufbauen
- technische Validierung und Registrierung implementieren
- neutrale Übergangsmetriken erzeugen

### Phase 3 – Profile

- Idle zuerst als einfachstes Profil
- Walk und Run danach
- Jump und Attack erst mit echten Beispielen kalibrieren
- Sneak und weitere Profile ergänzen

### Phase 4 – Reports und Verlauf

- Terminalanzeige mit Emoji und ANSI-Farben
- Markdown, JSON und Diagnosefigur
- sicherer Vergleich zum vorherigen Report

### Phase 5 – Projektkalibrierung

- Grenzwerte an echten guten und schlechten Clips prüfen
- Fehlalarme dokumentieren
- erst danach CI-relevante Rückgabecodes festlegen

## Noch offene Entscheidungen

- Welche Animationstypen existieren tatsächlich im Projekt?
- Liegen Richtungen in Zeilen, Spalten, getrennten Sheets oder getrennten
  Dateien?
- Welche Clips laufen in-place und welche enthalten Root-Motion?
- Sind Pivots als Engine-Metadaten verfügbar?
- Welche Bildrate und welche individuellen Halteframes sind beabsichtigt?
- Müssen Übergänge zwischen unterschiedlichen Clips geprüft werden?
- Welche Fehler sollen nur warnen und welche den CI-Lauf fehlschlagen lassen?
- Welches Format ist die verbindliche Quelle: Einzelbilder, Sprite-Sheet oder
  Engine-Import?

## Definition of Done für eine spätere Implementierung

- Alle vereinbarten Eingabeformen werden deterministisch dekodiert.
- Kein Animationstyp wird aus einem Dateinamen erraten.
- Jedes aktive Profil besitzt eigene pytest-Positiv- und Negativtests.
- Gewollte Bewegung wird durch profilabhängige Regeln berücksichtigt.
- Schleifen und Nicht-Schleifen werden korrekt getrennt.
- Terminal, Markdown, JSON und Diagnosefigur stimmen überein.
- Verlaufsvergleiche werden nur bei vollständig vergleichbaren Läufen gezeigt.
- `--no-report` hinterlässt keine Dateien und liest keine Reporthistorie.
