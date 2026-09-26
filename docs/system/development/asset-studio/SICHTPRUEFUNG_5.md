# Briefing: Paket 5 – Asset-Anforderungen und Bestand

Stand: 26.09.2026. T013/#20 und T014/#21 sind technisch umgesetzt.
Die persönliche Sichtprüfung steht aus; beide Issues bleiben bis zur
Rückmeldung offen. Pakete 1–4 einschließlich 4a sind bereits abgenommen.

## Vorbereitung

Studio schließen und mit `python3 tools/control.py asset-manager run` neu
starten. Ein Test-/Demoprojekt verwenden. Der Scan darf echte Quelldateien
lesen, übernimmt aber nur Metadatenverweise. Keine Originale verschieben,
keine `.import` löschen und keine Legacy-Pipeline hierfür ausführen.

## Acht kurze Prüfpunkte

1. **Anforderungen speichern:** Demo-Held auswählen → Rechtsklick oder
   Werkzeugleiste → **Asset-Anforderungen …**. Die Figur-Vorlage mit `walk`,
   acht Richtungen, fünf Grafikprofilen und Frames `8,10,12,14,16` muss
   **200 erwartete Varianten** anzeigen. Speichern, erneut öffnen; die Werte
   bleiben. Nur den sichtbaren Posennamen in „Gehen“ ändern: Exportname
   `walk` bleibt. Die Pose behält ihre Identität.
2. **Reduzierte Richtungen:** Auf einer separaten Test-Asset-Karte die
   Figur-Vorlage laden und den Richtungsbutton **2** drücken. Erwartung:
   `O,W`, bei einer Pose **50 Varianten**, keine Forderung nach den anderen
   sechs Richtungen. Alternativ in einer Posenzeile eigene Richtungen
   `O,W` eintragen; leer bedeutet Vererbung der Asset-Richtungen.
3. **Frames und FPS getrennt:** In der Acht-Richtungs-Figur Frames auf
   `8,16` ändern → **80 Varianten**. FPS der Walk-Pose von 8 auf 12 ändern:
   weiterhin **80 Varianten**, nur anderes Tempo. Danach für die folgenden
   Scans Frames wieder auf `8,10,12,14,16` setzen. `walk` und `slowwalk`
   müssen bei zusätzlichen Posen getrennte Exportnamen behalten.
4. **Statischer Typ:** Auf einer weiteren Test-Asset-Karte Vorlage **Textur**
   laden und speichern. Keine Posen, Frames, FPS oder Richtungen erforderlich;
   fünf Grafikvarianten. In den Karteneigenschaften sind Materialmaske,
   Materialfarben und Frame-Ableitung nicht erforderlich. Keine Freigabe.
5. **Echten Walk-Bestand anzeigen:** Wieder den Acht-Richtungs-Walk wählen →
   **Bestand erfassen …** → Ordner
   `game/test_assets/characters/heroes/greenhero/spritesheets/walk` wählen →
   **Lesend erfassen**. Im vollständigen Bestand sind 200 Vorschläge sichtbar.
   Eine SW-Zeile muss `SW` und den tatsächlichen `_SW_`-Dateinamen nennen,
   nicht SO oder slowwalk. Eine andere Pose ohne passende Anforderung darf
   nicht still Walk zugeordnet werden. Herkunft zunächst **Unbekannt**.
6. **Teilbestand ehrlich melden:** Nur den Unterordner
   `walk/comic_high/spritesheet-fram8` erfassen. Bei acht vorhandenen
   Richtungsdateien und unveränderter 200er-Anforderung: acht gefunden,
   **192 fehlen**. Im Reiter „Erwartete Varianten“ sind die fehlenden
   Kombinationen sichtbar. „Gefunden“ bedeutet nie „abgenommen“.
7. **Bewusste Übernahme:** Eine passende SW-Zeile ankreuzen und als Verweis
   übernehmen. Ohne Häkchen darf nichts übernommen werden. „Gespeicherte
   Verweise“ zeigt Pfad, SHA256 und Herkunft. Nach Schließen liegt unter
   **Dokumente & Anhänge** ein schreibgeschützter Bestandsbericht mit
   übernommenen, ausgelassenen und zu klärenden Elementen. Keine Quellkopie
   und kein erfolgreicher Pipeline-/Godot-Status werden behauptet.
8. **Wiederholung, Abbruch, Neustart:** Dieselbe Datei nochmals erfassen und
   auswählen → „Schon vorhanden“, keine zweite Quelle. Einen noch laufenden
   Scan abbrechen oder schließen → keine Teilübernahme. Studio neu starten,
   Projekt öffnen → Anforderungen und gespeicherte Verweise bleiben erhalten.

Bitte Rückmeldung mit Nummern, zum Beispiel `✅ 1–8` oder
`❗ 5: falsche Zuordnung; gewählter Ordner …; Screenshot …`.
Wenn alle Punkte passen, schließen wir #20/#21 nach deiner Abnahme ab.
Danach kommt ein Vorschlag für T015/#22 und T016/#23; diese wurden nicht begonnen.

## Zusatzfälle und Grenzen

Doppelte Varianten benötigen eine ausdrückliche Einzelauswahl. Unbekannte
PixelEng-Dateien bleiben ungeklärt. Historische Reports ohne passende Quell-
und Ergebnisdateihashes sind ungeprüft; auch passende Hashes erteilen keine
Freigabe. Vergleichsseiten öffnen nur als lesender HTML-Quelltext, ohne
Skripte. Kaputte Verweise bleiben sichtbar und werden nicht repariert.
Diese Sonderfälle wurden mit synthetischen Fixtures automatisiert geprüft;
der vorhandene Walk-Ordner enthält hier keine Reports oder HTML-Seiten.

Einzelbildposen wie Jump lassen sich mit `source_kind = single_image`,
Loop `nein` und leerer FPS anlegen. Ein vollständiger Importassistent und
Animationsvorschau gehören nicht zu Paket 5. Weitere Bedienhinweise stehen
unter [Bestandserfassung](INVENTORY.md).
