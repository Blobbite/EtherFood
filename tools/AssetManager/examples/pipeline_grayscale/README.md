# Optionale Graustufen-Erweiterung

Dieses Beispiel wird **nicht** beim Öffnen registriert, freigegeben oder in
Standardrezepten aktiviert. `apply(image, parameters)` liefert ein RGBA-Bild
gleicher Größe; Alpha, Frame-Raster und Reihenfolge bleiben erhalten.

1. Im Pipeline-Editor die Python-Erweiterungsverwaltung öffnen.
2. „Python-Schritt hinzufügen / aktualisieren …“ wählen und `manifest.json`
   sowie ausdrücklich `grayscale.py` auswählen. Das Studio speichert eine
   geprüfte Kopie im aktuell geöffneten Projekt, ohne sie auszuführen.
3. Quelltext und Abhängigkeit prüfen. „Codeversion freigeben …“ zeigt den
   vollständigen SHA-256. Warnung bestätigen und genau diesen Hash eingeben.
4. Den registrierten Schritt `python:grayscale` selbst zum Rezept hinzufügen,
   den Bildeingang verbinden und `amount` einstellen: 0 = unverändert,
   1 = Graustufen. Ein Build startet nur nach ausdrücklicher Ausführung.

Manifest Version 1 erlaubt Zahlen, ganze Zahlen, Schalter, Text und Auswahllisten.
Ein-/Ausgabe ist ein RGBA-Bild gleicher Geometrie, kein freier Dateipfad.
Parameter werden aus dem Manifest dargestellt; eine eigene Spezial-UI ist
nicht nötig. `Pillow==12.1.1` entspricht der Studio-Abhängigkeit. Fehlende oder
abweichende Abhängigkeiten blockieren; es gibt keine automatische Installation.

Ein geändertes Manifest oder neu registrierter Code widerruft die Freigabe.
Eine beschädigte registrierte Kopie wird anhand des Hashes abgelehnt. Änderungen
an der ursprünglich ausgewählten Datei verändern die gespeicherte Kopie nicht;
für eine neue Version erneut registrieren. Freigaben bleiben lokal und werden
nicht mit Rezepten exportiert. JSON-/Paketimporte enthalten keinen Python-Code.

Der Worker hat Zeitlimit und Abbruch, ist aber **keine Sicherheits-Sandbox**.
Vertrauenswürdiger Python-Code läuft mit den Benutzerrechten der Anwendung.
Schutz gegen versehentliche Netzwerk-/Prozesszugriffe ist keine Isolation gegen
bösartigen Code. Nur selbst geprüften, ausdrücklich vertrauenswürdigen Code
freigeben; keine Zugangsdaten in Parametern hinterlegen.
