# Kurzes Briefing: Anforderungen und Canvas

Stand: 27.09.2026. Diese Runde ist bewusst kleiner als die vollständige
Paket-5-Liste. Der gewünschte Quellenworkflow ist
[konkret geplant](../plans/asset-studio-quellenworkflow-und-canvas.md);
der Button neben Anker Y und die automatische Erzeugung sind noch nicht
implementiert. Die Canvas-Anpassung gehört zum jetzigen Update.

## Jetzt wirklich prüfen

Studio neu starten: `python3 tools/control.py asset-manager run`.
Das vorhandene Testprojekt mit Walk und Stand verwenden; kein neues Projekt
und keine optionalen PyGameTools-/Archiv-/Godot-Wurzeln erforderlich.

1. **Anforderungen und Speichern:** Beide Posen als `spritesheet`, acht
   Richtungen, fünf Grafikprofile und Frames `8,10,12,14,16` ergeben **400**
   erwartete Varianten. Nur die FPS ändern: Die Zahl bleibt 400. Speichern,
   schließen und erneut öffnen; Werte und die beiden Exportnamen bleiben.
2. **Runde Karten und Bedienung:** Die Ecken sind leicht gerundet. Eine Karte
   anklicken und verschieben; die Auswahl ist erkennbar. Den Größenanfasser
   unten rechts kurz ziehen und mit Strg+Z zurücknehmen. Die vier Anschlüsse
   und vorhandene Verbindungslinien bleiben an den Karten.
3. **Mehr Platz zum Verschieben:** Mittlere Maustaste/Mausrad gedrückt halten
   und die Ansicht deutlich nach links, rechts, oben und unten ziehen – auch
   wenn der Startpunkt über einer Karte liegt. Die äußeren Karten lassen sich
   bis fast an den gegenüberliegenden Fensterrand schieben. Ein kleiner
   sichtbarer Kartenstreifen bleibt; danach ist Schluss, kein endloses Board.
   Die Anordnung der Karten untereinander darf dabei nicht verändert werden.
4. **Zoom und Fenstergröße:** Mit Strg+Mausrad heraus-/hineinzoomen und das
   Fenster vergrößern/verkleinern. Punkt 3 kurz wiederholen: Der nutzbare
   Freiraum passt sich an und darf nicht auf den alten kleinen Rand schrumpfen
   oder beim wiederholten Verschieben endlos wachsen.

Rückmeldung genügt als `✅ 1–4` oder `❗ 3: …` mit Screenshot/kurzen Schritten.
Bereits bestätigte Punkte müssen nicht erneut vollständig durchgetestet werden.

## Für diese Runde überspringen beziehungsweise zurückstellen

- Die vollständige Scan-/Übernahmerunde aus Paket 5: gesamter Walk-/Stand-
  Bestand, Teilordner, Altberichte, HTML-Verweise und Dubletten. Der Scanner
  bleibt verfügbar und automatisiert getestet; er ist nicht der künftige
  Hauptweg für neu erzeugte Assets. Seine persönliche Abnahme bleibt offen.
- Zusätzliche NPC-/Textur-Testkarten. Reduzierte Richtungen und statische
  Anforderungen bleiben in den automatisierten Tests; die nächste passende
  Benutzerprüfung erfolgt am neuen Anlage-/Quellenablauf.
- Alle bereits abgenommenen Paket-4a-Details erneut vollständig wiederholen.
  Hier reicht der kurze Bedienungscheck der jetzt geänderten Karten.
- Spritesheet-Importbutton, automatische Frame-/Grafikerzeugung, Farb-/Masken-
  Verarbeitung, Godot und Runtime. Diese Funktionen sind noch nicht Bestandteil
  dieses Updates und können deshalb nicht als bestanden getestet werden.

Überspringen bedeutet hier **zurückgestellt**, nicht erledigt oder freigegeben.
Issues #20/#21 werden durch diese Planänderung nicht automatisch geschlossen.

## Nächste Kontrollpunkte

Nach Umsetzung des Quellenimports: Button je Pose, mehrere Dateien/Richtungen,
Rasterprüfung, unvollständige Lieferung, sichere Kopie, Abbruch und Neustart.
Nach Anbindung der tatsächlichen Erzeugung: angeforderte Frames/Grafikprofile,
richtige Richtung und Pose, Anker/Timing, zentrale neue Version, unveränderte
Originale und keine falschen Erfolgsanzeigen bei Abbruch/Fehler.
Diese Prüfungen sind geplant, nicht bereits durchgeführt.
