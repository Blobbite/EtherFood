<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: Portal-Turm für das Testlabor

## Zweck und Ausgangslage

Der Benutzer ersetzt die bisherige gemeinsame Testfläche durch einen
erweiterbaren Portalraum. Der Held startet in der Mitte eines runden Turms;
statische Türportale führen in getrennte Testraumszenen. Jedes Ziel besitzt
ein Rückportal zum zugehörigen Eingang im Turm. Der Testbereich bleibt eine
Entwicklungsfunktion ohne Änderung von Kanon oder Spielregeln.

Die vorhandene Route `visual_lab`, Bewegungssteuerung, F5-Einstellungen,
Grafikvarianten und rahmenlosen Anzeigen F11/F12 bleiben die gemeinsame
Grundlage. Die bisher gemeinsam gezeigten Vorschauen werden räumlich getrennt.

## Umfang und Schritte

1. Szenen, Vorschauen, Einstellungsverwaltung und bisherige Tests prüfen.
2. Acht Blau-Grau-Farben, Blueprint-Boden und statische HD-Platzhalter erstellen.
3. Raumkatalog, kreisförmige Portalanordnung und sichere Rückwege integrieren.
4. Lampen-, Sprite-, Monster-, Shader-, Objekt-, Partikel-, Nebel-,
   Tageszeit- und Weltzustandsraum anlegen.
5. Vorhandene Testfunktionen zuordnen und gemeinsame Einstellungen erhalten.
6. Tests für Navigation, Erweiterung, Gestaltung und getrennte Effekte ergänzen.
7. Dokumentation und Erweiterungsanleitung aktualisieren.
8. Gezielte Prüfungen, visuelle Kontrolle und Standardprüfung durchführen.

## Fortschritt

- [x] Bestehende Szenen und Testfunktionen untersucht.
- [x] Blueprint-Gestaltung und Platzhalter erstellt.
- [x] Portalnavigation und Raumkatalog integriert.
- [x] Neun getrennte Testraumszenen erstellt.
- [x] Gemeinsame Steuerung und getrennte Vorschauen integriert.
- [x] Automatische Prüfungen aktualisiert.
- [x] Dokumentation aktualisiert.
- [x] Abschlussprüfung und Sichtkontrolle abgeschlossen.

## Entscheidungen und offene Punkte

- „Spiceraum“ wird als Sprite-Testraum umgesetzt. Auf die optionale Rückfrage
  kam keine andere Zuordnung; die spätere HD-Ergänzung ist berücksichtigt.
- Der Portalraum erhält höchstens acht Blau-Grau-Grundfarben. Seine Portale
  bleiben einfache Türen ohne Shader, Partikel oder Animationen. Vorhandene
  Figuren und die Inhalte der Fachräume behalten ihre eigenen Testgrafiken.
- Wiederverwendbare SVG-Platzhalter und eine gezeichnete Rasterfläche halten
  die Palette exakt und lassen den Boden über die bestehende Tilegröße ändern.
- Die Ergänzung des Benutzers verlangt HD auch für Texturen und Assets.
  Alle sechs neuen SVG-Texturen besitzen deshalb mindestens 1024 Pixel auf
  der längeren Seite, feinere Konturen und eine separate Weltskalierung.
  Eine wiederholbare HD-Bodenplatte ergänzt das einstellbare Raster.
- Ein versionierter Raumkatalog bildet die Erweiterungsstelle. Jeweils eine
  Zielszene ist aktiv. Portalwechsel bewahren gemeinsame Testeinstellungen.
- Sichere Ankunftspunkte außerhalb der Tür verhindern sofortiges Zurückspringen;
  Portale werden nach dem Loslassen der Bewegung wieder freigegeben.
- Nebel, Tageszeit und Wiederherstellung erhalten jeweils eigene sichtbare
  Vorschauen. Im Turm sind diese Effekte ausgeschaltet.

## Prüfungen und bekannte Ausgangslage

Abgeschlossen am 11. September 2026:

- Godot-Import aller Szenen und sechs HD-Texturen erfolgreich.
- Neue Portal-Laufzeitsuite bestanden: echte Hin-/Rückwege durch jede Tür,
  korrekte Rückkehrpunkte, kein Wechsel durch andere Körper oder beim
  Ankommen, Erweiterung auf 33 Räume, HD-Texturen, statische Türen,
  Rastergrößen, gemeinsame Einstellungen und getrennte Raumeffekte.
- Bestehende Kollisions-, Pixel-Snap-, Filter-, Maßstabs- und
  Atmosphärentests auf die zugehörigen Räume angepasst. Die gezielte
  Pixel-Snap-Suite besteht; beim Filter bleiben zwei schon zuvor vorhandene
  Erwartungen zu den Zoomstandards unverändert fehlerhaft.
- Drei Python-Tests für HD-Auflösung, Palette, statische Vektorgeometrie und
  verlustfreie Importe bestanden. Stilprüfung für 98 Dateien bestanden.
- Portalturm und alle neun Räume in Godot mit Software-OpenGL ES in
  1920 × 1080 gerendert und visuell geprüft. Die Kontrolle führte zu
  gleichmäßig sichtbaren Rasterlinien, näheren Ankunftspunkten und einem
  eigenen freien Rückweg rechts im Objekt-Testraum. Renderbilder und
  zusätzliche Renderwerkzeuge bleiben ausschließlich flüchtig.
- Vollständiger Lauf `python tools/control.py check`: Doctor 12/12,
  Stilprüfung bestanden, Python 227 bestanden / 1 Fehler. Der Python-Fehler
  bleibt die schon vorhandene zusätzliche Dokumentationsebene durch den
  ignorierten lokalen Ordner `docs/concept/.obsidian/`.
- Godot im Standardlauf: dieselben 75 Erwartungsfehler wie vor dem Umbau,
  überwiegend zu bereits geänderten Bewegungs-, Maßstabs- und Zoomstandards.
  Der Vergleich der Fehlermeldungen einschließlich Häufigkeit ergab keine
  zusätzliche Meldung. Keine Script-, Parse- oder anderen Laufzeitfehler.

Die Standardprüfung bleibt wegen dieser Bestandsfehler insgesamt rot.
Die Fehler wurden nicht durch das Entfernen lokaler Benutzerdaten oder eine
Änderung angenommener Spielstandards verdeckt.

## Wiederholbarkeit und Wiederherstellung

Alle Platzhalter bleiben unter `game/tests/assets/`. Keine Grafikfreigabe,
keine neuen Projektabhängigkeiten und keine Änderungen an Git-Zugangsdaten.
Vorhandene Arbeitsbaumänderungen bleiben erhalten. Eine flüchtige Sicherung
der zuvor bearbeiteten Labordateien dient dem gezielten Vergleich.

## Ergebnis und Rückblick

Die Route `visual_lab` öffnet den erweiterbaren Portalturm. Neun Fachräume
haben echte Rückwege; Nebel, Tageszeit und Weltzustand sind getrennt. Der
Blueprint-Aufbau verwendet acht Grundfarben und sechs skalierbare
HD-Texturen. Lampen und Partikel besitzen schaltbare Proben, der Tagesraum
einen Hell-Dunkel-Zyklus. Monster und Shaderflächen sind statische
Vorbereitungen für kommende Tests. Die frühere gemischte Fläche ist ersetzt;
ihre weiterhin nutzbaren Vergleichsfunktionen liegen im jeweiligen Fachraum.
