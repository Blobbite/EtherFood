# Nachbriefing 6a – Quellenübersicht und Aufgaben am Asset

Der Bericht aus Paket 6 bestätigt Quellenbutton und Import mit 1×16/4×4.
Dieses Zwischenpaket setzt die konkreten Bedienwünsche um; eine endgültige
Abnahme aller übrigen Paket-5-/Paket-6-Kriterien wird nicht daraus abgeleitet.

Studio neu starten: `python3 tools/control.py asset-manager run`.
Das vorhandene Testprojekt und der bestehende Held reichen aus. Originale und
alte Lieferungen bleiben erhalten. Keine 200 Dateien für den Test nötig.

## Bitte diese sieben Punkte prüfen

1. **Rastervorschlag:** Walk → Spritesheets hinzufügen. Dateien mit `_1x16_`
   und `_4x4_` sollen das passende Raster sofort eintragen. Ohne Raster im
   Namen bleibt **Auto**: **Auswahl prüfen** erkennt klare Transparenzabstände
   oder verlangt eine manuelle Angabe. Ergebnis/Frames vor dem Import prüfen;
   Raster bleibt überschreibbar. Undurchsichtige/unklare Sheets müssen nicht
   automatisch erkannt werden.
2. **Gespeicherte Bündel:** Importdialog schließen und wieder öffnen. Oben
   bleibt eine kompakte Zeile pro bereits belieferter Pose samt Zähler sichtbar;
   die leere Dateiauswahl darunter bezeichnet nur den nächsten Import.
3. **Quellenübersicht:** Asset-Menü → Quellen / Revisionen. Pose auf-/zuklappen,
   Richtung öffnen. Raster und Frames stehen in eigenen Spalten, auch bei
   frei benannten Dateien. Alte Revisionen liegen unter der jeweiligen Richtung,
   frühere Lieferbündel unter der Pose; keine riesige globale Auswahlliste.
4. **Einzelersatz:** Bei Walk-SW **Ersetzen …**, neue SW-Datei auswählen,
   Zuordnung/Raster prüfen und Ersetzen ausdrücklich bestätigen. SO und die
   anderen Richtungen dürfen unverändert bleiben. Ältere SW-Revision bewusst
   wieder aktivieren und den Stand kontrollieren.
5. **Ganze Pose:** **Pose neu liefern …** erwartet alle benötigten Richtungen
   dieser Pose. Abbrechen oder nur eine Teilmenge liefern darf nichts ersetzen.
   Ein vollständiges Bündel gemeinsam importieren; danach ist die frühere
   vollständige Lieferung als ganze Pose wieder aktivierbar.
6. **Ein Einstieg:** Toolbar und Rechtsklick der Asset-Karte bieten nur noch
   **Asset-Menü**, keine separaten Anforderungen-/Quellen-/Bestandsaktionen.
   Anforderungen sind unter **Posen**, die lesende Bestandserfassung unter
   **Quellen / Revisionen** weiterhin erreichbar.
7. **Aufgaben und Issues:** Asset-Menü → Dokumentation → Aufgaben & Issues.
   Aufgabe und Issue mit Beschreibung anlegen, zwei To-dos hinzufügen, eines
   abhaken, Text bearbeiten und suchen. Mit offenen Punkten darf **Erledigt**
   nicht gesetzt werden. Im Hauptfenster dieselbe Aufgabe öffnen; nach
   Projektneustart bleiben Text, Häkchen, Zuordnung und Notizen erhalten.

Rückmeldung als `✅ 1–7` oder `❗ Nummer: kurzer Befund` genügt.
Ein vollständiger Posenersatz benötigt die Richtungen der aktuellen Anforderungen,
nicht alle Grafik-/Framevarianten. Falls die Neuanlage-/Vorlagen-/Abbruchtests
aus Paket 6 noch nicht durchgeführt wurden, bleiben sie separat offen.

## Überspringen und offen lassen

- Canvas-Zoom, Verschieben und alte Filter nicht komplett wiederholen.
- Keine absichtliche Dateibeschädigung und keine 200 Revisionen anlegen;
  große Historien, Abbruch, unvollständige Lieferungen und Konflikte sind getestet.
- Notiz-Icon im Canvas gegenüber einer Notizsammlung ist noch eine offene
  Bedienentscheidung. Die vorhandenen Notizdokumente wurden nicht umgebaut.
- Noch keine automatische Farb-/Masken-/Frame-/Grafik-Erzeugung und kein Godot.
  T017/#24 und T018/#25 sind weiterhin nicht begonnen. Nach dem Briefing
  entscheiden wir über deren Freigabe und die gewünschte Notizdarstellung.
