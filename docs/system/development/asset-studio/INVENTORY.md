# Asset-Anforderungen und lesende Bestandserfassung

Paket 5 umfasst T013/#20 und T014/#21. Keine Originale werden kopiert,
verschoben, repariert oder verarbeitet. Es entsteht keine Freigabe.

## Bedienung

1. Asset-Karte auswählen (zum Beispiel den Demo-Helden).
2. **Asset-Anforderungen …** öffnen, Vorlage und Posen festlegen. Für den
   Walk-Bestand genügt die Figur-Vorlage mit Exportname `walk`. Weitere Posen
   ausdrücklich ergänzen; `slowwalk` ist nicht `walk`.
3. Richtungen in Reihenfolge, Grafikprofile und Frames wählen. FPS stehen
   separat je Pose. Pose-Anzeigenamen dürfen sich ändern, ihre IDs bleiben.
4. **Matrix prüfen**, anschließend speichern. Die Standardfigur erwartet
   200 Varianten je Spritesheet-Pose. Eine Textur erwartet fünf Grafikprofile,
   ohne Posen/Frames. Ein `single_image` wie Jump hat ein Bild, keine FPS/Loop.
5. **Bestand erfassen …**, gewünschten Ordner auswählen und **Lesend erfassen**.
   Der Scan läuft im Hintergrund und lässt sich abbrechen; kein automatischer
   Scan beim Projektstart. Die Anforderungen gehören zum ausgewählten Asset.
6. Vorschläge, erwartete Varianten und Probleme/Fremdberichte prüfen. Nur
   gewünschte Zeilen ankreuzen. Doppelte Varianten benötigen eine bewusste
   Einzelauswahl; unklare und nicht benötigte Zuordnungen bleiben gesperrt.
7. Herkunft zunächst **Unbekannt** lassen, wenn sie nicht bekannt ist.
   Original/Ableitung sind ausdrücklich eigene Angaben, keine Bildanalyse.
   Eine Ableitung benötigt den Quell-SHA256. Die Angabe gilt für die Auswahl.
8. Auswahl bestätigen. Dateien werden erneut geprüft; geändertem Bestand
   oder geänderten Anforderungen folgt keine teilweise Übernahme. Der
   schreibgeschützte Bericht erscheint bei der Asset-Karte unter Dokumente.

Wiederholung derselben Auswahl erzeugt keine doppelten Quellen/Reports.
Vorhandene Originalverweise werden nie durch Ableitungen ersetzt. Neue
Inhalte zur gleichen Variante bleiben als getrennte Beobachtungen erhalten.
Eine schon übernommene Herkunft wird durch einen erneuten Scan nicht verändert.
Für unbekannte Namen zuerst Anforderungen/Exportnamen prüfen und neu scannen;
der Scanner benennt Originale nicht um. Ein vollständiger Importassistent
und verwaltete Quellkopien sind Aufgaben T015/T016, nicht Teil dieses Pakets.

## Erkennung und Grenzen

Bekannt sind die Grafikordner `comic_high`, `comic_mid`, `comic_low`,
`pixel_high`, `pixel_low`, Frameordner `spritesheet-framN` und Dateiraster
`_4x2_` usw. Pose-Exportnamen und `N,NO,O,SO,S,SW,W,NW` werden als getrennte
Werte behandelt. Rasterprodukt und Frameordner müssen zusammenpassen.
Die gewählte Wurzel darf auch direkt ein Grafik-/Frameordner sein.

Optionales unkomprimiertes PNG-Textfeld `etherfood_variant` enthält ein
JSON-Objekt mit `pose`, `direction`, `graphics`, `frames`, `grid` (zwei
Ganzzahlen). Widersprüche zu Dateiname/Ordner bleiben Klärfälle. Andere
PNG-Metadaten werden nicht als fachliche Zuordnung interpretiert.
`PixelEng` oder ein Fram8-Ordner beweisen keine Originalherkunft.

Grenzen je Auftrag: 10.000 Verzeichniseinträge, Tiefe 16, je PNG 64 MiB und
32 Millionen Pixel, je Report/HTML 1 MiB. Symlinks werden nicht verfolgt;
versteckte Unterordner, `.import` und andere Nicht-PNG-Dateien werden nicht
als Bildvarianten importiert. Kleinere Wurzeln helfen bei großen Beständen.
PNG-Signatur, Chunk-Grenzen/CRC, Abmessungen und Raster sind Strukturprüfungen,
keine Pixel-, Animations-, semantische Richtungs- oder Sichtprüfung.

Historische `build-info.json`, `pruefung.json`, `color-build.json` sind
Fremdaussagen. Quell- und Ergebnis-Dateihashes müssen zu Dateien innerhalb
der ausgewählten Wurzel passen. Fehlende Ausgabehashes, alte absolute Pfade
außerhalb der Wurzel oder Abweichungen bleiben ungeprüft. Selbst eine passende
Bindung ist nur `historical_bound`, niemals ein aktueller Studio-Check.
Vergleichsseiten bleiben lokale Verweise mit Linkdiagnose; geöffnet wird nur
lesender HTML-Quelltext. Keine Skripte, externen Ressourcen oder Reparaturen.

## Ablage und Abgrenzung

Asset-Anforderungen und externe Beobachtungen liegen revisioniert im Katalog.
Migration 3 ergänzt `inventory_roots`; vorhandene Kataloge erhalten vorher
eine Sicherung. Wurzel-UUID und relative Pfade sind fachliche Verweise,
lokale absolute Wurzeln werden nicht in Metadaten-Snapshots exportiert.
Nach Übertragung auf einen anderen Rechner ist erneut zu erfassen; ein
alter Verweis beweist nicht, dass die Datei dort vorhanden oder freigegeben ist.
Der Workflow wartet weiterhin auf einen späteren verwalteten Quellimport.

`asset-manager import` in Control bleibt **Tool-Umgebung vorbereiten**. Diese
Bestandserfassung erfolgt innerhalb des Studios; die beiden Vorgänge sind
nicht gleichzusetzen. Quellenkopierimport, Pipeline, Godot und Runtime folgen
nur nach gesonderter Freigabe ihrer Aufgaben.
