# Kurzes Briefing: Anforderungen und Canvas

Stand: 27.09.2026. Diese Runde ist bewusst kleiner als die vollständige
Paket-5-Liste. Der gewünschte Quellenworkflow ist
[konkret geplant](../plans/asset-studio-quellenworkflow-und-canvas.md);
der Button neben Anker Y und die automatische Erzeugung sind noch nicht
implementiert. Die Canvas-Anpassung gehört zum jetzigen Update.

## Bestätigt und aktueller Nachtest

Der Benutzer hat die vier ursprünglichen Punkte am 27.09.2026 mit **✅ 1–4**
bestätigt. Zusätzlich wurde ein Positionssprung beim Anklicken nach Zoom
gemeldet. Ursache: Der Klick zentrierte die Ansicht mitten in einem möglichen
Drag und verfälschte dadurch den Verschiebeweg. Canvas-Auswahl und gezielte
Navigation sind jetzt getrennt; ein Klick im Canvas zentriert nicht mehr.

Studio neu starten: `python3 tools/control.py asset-manager run`.
Das vorhandene Testprojekt mit Walk und Stand verwenden; kein neues Projekt
und keine optionalen PyGameTools-/Archiv-/Godot-Wurzeln erforderlich.

**Nur diese drei Punkte erneut prüfen:**

1. **Zoomen und anklicken:** Weit herauszoomen, normal zoomen und weit
   hineinzoomen. Jeweils mehrere unterschiedliche Karten nacheinander
   anklicken, auch kurz gedrückt halten. Ohne bewusstes Ziehen dürfen weder
   Karten noch Sichtausschnitt springen; ihre Abstände bleiben gleich.
2. **Gezielt ziehen und zurücknehmen:** Eine noch nicht ausgewählte Karte
   anklicken und ein Stück ziehen. Sie folgt ohne Sprung der Maus; die anderen
   Karten bleiben stehen. Strg+Z nimmt genau diesen Weg zurück. Kurz mit
   gedrücktem Mausrad verschieben: Nur die Ansicht bewegt sich.
3. **Wieder öffnen und navigieren:** Eine Karte bewusst umsetzen und das
   Projekt schließen/erneut öffnen. Die gewählte Anordnung bleibt erhalten.
   Eine andere Karte über den Projektbaum oder die Suche auswählen: Dort
   wird sie weiterhin gezielt ins Bild geholt, ohne ihre Position zu ändern.

Rückmeldung genügt als `✅ Nachtest 1–3` oder `❗ Nachtest 1: …` mit kurzen
Schritten und gegebenenfalls Screenshot. Die bisherigen Anforderungen,
Grafikstufen, Rundungen und Bestandsimporte müssen nicht erneut durchlaufen
werden. Der Benutzer hat am 27.09.2026 auch diese drei Nachtests vollständig
bestätigt. Die Canvas-Fehlerkorrektur ist damit persönlich abgenommen.

## Bereits bestätigte Punkte als Referenz

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

Als nächstes zusammenhängendes Paket ist **Quellenimport und Asset-Anlage**
vorgesehen (T015/#22 und T016/#23):

- **Spritesheets hinzufügen …** direkt neben Anker Y je Pose; mehrere Dateien
  auswählen, Pose, Richtung und Raster vor dem Import prüfen.
- Geprüfte Quellkopien zentral im Studio-Projekt verwalten. Originale bleiben
  unverändert; unvollständige Lieferungen, Konflikte und Herkunft bleiben
  sichtbar. Quellen dürfen später ergänzt werden.
- Asset-/NPC-Vorlagen und Held-Menü mit diesen Anforderungen und Lieferungen
  verbinden. Danach folgt ein eigenes Briefing für Auswahl, Validierung,
  sichere Kopie, Abbruch und erneutes Öffnen.

Dieses Paket wird nicht in der Canvas-Fehlerkorrektur mit umgesetzt.
Automatische Varianten-Erzeugung folgt danach mit den nötigen Auftrags-,
Masken-/Farb- und Frame-/Grafikschritten; der Quellenbutton allein ist noch
keine fertige Erzeugungspipeline.

Nach Anbindung der tatsächlichen Erzeugung: angeforderte Frames/Grafikprofile,
richtige Richtung und Pose, Anker/Timing, zentrale neue Version, unveränderte
Originale und keine falschen Erfolgsanzeigen bei Abbruch/Fehler.
Diese Prüfungen sind geplant, nicht bereits durchgeführt.
