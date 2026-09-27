# Arbeitsplan: Quellenworkflow und Canvas-Nachbesserung

## Zweck und Ausgangslage

27.09.2026, Basis `1038a17`: Der Benutzer möchte als Zielablauf Anforderungen
festlegen, direkt bei einer Pose Spritesheets auswählen und die angeforderten
Varianten zentral neu erzeugen lassen. Dazu wird jetzt der nächste
Umsetzungsplan zugeschnitten, nicht die gesamte Pipeline ungeprüft vorgezogen.
Zusätzlich ausdrücklich zur Umsetzung freigegeben: leicht abgerundete Karten
und ein größerer, aber begrenzter Verschiebebereich im Canvas.

Paket 5 ist technisch umgesetzt; seine persönliche Sichtprüfung ist noch
nicht vollständig bestätigt. Der Bestandsleser ist ein optionales Hilfsmittel,
kein Ersatz für den kommenden Quellenimport. Bestehende fremde Control-,
Dokumentations- und Grafikänderungen bleiben erhalten und ungepusht.

## Umfang, Schritte und Fortschritt dieses Abschnitts

- [x] Regeln, aktuellen Canvas, Tests und nächste Planaufgaben prüfen.
- [x] Nächsten Quellen-/Erzeugungsablauf und die Kontrollpunkte konkretisieren.
- [ ] Karten runden; endlichen Freiraum und explizites Mitteltasten-Panning umsetzen.
- [ ] Qt-Regressionsprüfungen, Grenzfälle und Ansichten tatsächlich prüfen.
- [ ] Kurze neue Prüfliste, Ergebnisdokumentation, englische Emoji-Commits und Push.

Keine Quellbilder bearbeiten, keine Freigabe übertragen, keine neuen
Animationen erzeugen. Der Quellenbutton und die Pipeline werden in diesem
Abschnitt geplant, nicht durch einen funktionslosen Knopf vorgetäuscht.

## Nächster durchgängiger Arbeitsablauf (noch nicht implementiert)

1. Anforderungen bleiben am Asset: Posen, geordnete Richtungen, Grafikprofile,
   Framezahl und FPS getrennt. Neben **Anker Y** erhält jede Posenzeile
   **Spritesheets hinzufügen …** mit Lieferstatus, z. B. „6/8 Richtungen“.
2. Mehrfachauswahl mit explizitem Raster, Pose und Richtung je Datei. Dateiname
   und Metadaten schlagen vor, Konflikte/fehlende Richtungen bleiben sichtbar.
   Die Importbestätigung zeigt Quelle, Ziel und erwartete Variantenanzahl.
3. Geprüfte Kopien als unveränderliche SourceRevision im Studio-Projekt
   registrieren; Quelle, Hash und Importzeit bleiben nachvollziehbar. Ein
   Stand-Einzelbild und eine Stand-Animationslieferung sind unterschiedliche
   Quellarten. Ein SW-Sheet ersetzt keine anderen Richtungen.
4. **Importieren & Varianten erzeugen** plant anschließend alle konfigurierten,
   technisch ableitbaren Ergebnisse. Die Verarbeitung startet erst nach
   Bestätigung und vorhandenen Voraussetzungen, mit Fortschritt und Abbruch.
   Fehlende Eingaben erhalten einen konkreten Sperrgrund, keinen grünen Haken.
5. Alte externe Variantenordner sind weder Ziel noch stillschweigender Cache.
   Neu erzeugte Ergebnisse liegen zentral in einem eigenen versionierten
   Build. **Alles neu erzeugen** erlaubt einen bewussten vollständigen Lauf;
   geprüfte Wiederverwendung bleibt eine separate, sichtbare Planentscheidung.
6. Vorherige Builds und unabhängige 8-/10-/12-/14-Frame-Originale bleiben
   erhalten. Die Verarbeitung arbeitet nur auf isolierten Arbeitskopien.
   Zentral heißt eine verwaltete Quelle der Wahrheit, nicht ungeprüfte
   Duplikation jeder Datei. Automatische Asset-/Godot-Freigabe gibt es nicht.

## Zuordnung zu vorhandenen Issues und Kontrollpunkten

Keine doppelten Ersatz-Issues anlegen und keine vorhandenen Voraussetzungen
entfernen. Folgende zusammenhängenden Abschnitte führen zum Ziel:

| Abschnitt | Vorhandene Aufgaben | Kontrollpunkt für den Benutzer |
| --- | --- | --- |
| A: Quellen an der Pose | T015/#22, T016/#23 | Button neben Anker Y; mehrere Richtungen importieren, fehlende Lieferungen sehen, Projekt wieder öffnen |
| B: Verlässlicher Auftrag | T017/#24, T018/#25 | Plan erklärt Erzeugen/Wiederverwenden/Blockiert; UI bleibt bedienbar; Abbruch und Wiederaufnahme ehrlich |
| C: Korrekte Eingaben/Farben | T019–T023/#26–#30 | Referenz-/Masken-/Farbvoraussetzungen im gewählten Rezept sichtbar; keine stillen Farbänderungen |
| D: Frames und fünf Grafikstufen | T024–T026/#31–#33 | 16 sowie 14/12/10/8 aus derselben Quelle; Grafikstufen, FPS/Timing und Anker stimmen; bewusster Neubau bleibt getrennt |

Das Ziel ist die zusammenhängende Bedienung, nicht das Überspringen der
Schutz- und Profilvoraussetzungen. Ein früher Teilstand von Abschnitt A darf
noch keine funktionierende automatische Gesamterzeugung versprechen. Es wird
je Abschnitt geprüft, committed und gepusht. T027 und Godot-Integration bleiben
eigene spätere Aufgaben; ein erzeugter Build ist nicht automatisch spielbereit.

## Canvas-Entscheidungen

- Dezenter Eckenradius von 10 Szeneneinheiten. Zeichnung und Trefferfläche
  verwenden dieselbe Rundung; Auswahl bleibt sichtbar. Größenanfasser leicht
  nach innen versetzen, damit er die Rundung nicht wieder eckig übermalt.
- Statt fester 60/100er-Ränder etwa eine sichtbare Fensterbreite/-höhe als
  Freiraum je Seite. Am Anschlag reicht der äußere Kartenbereich bis auf
  einen kleinen sichtbaren Streifen an den gegenüberliegenden Fensterrand.
- Grenzen werden aus Kartenpositionen und aktueller Fenster-/Zoomgröße
  berechnet, nie aus dem bereits verschobenen Sichtausschnitt. Reines Panning
  vergrößert den Bereich nicht endlos. Linienvorschauen vergrößern ihn nicht.
- Gedrückte mittlere Maustaste verschiebt ausschließlich die Ansicht, auch
  über einer Karte. Linksklick-Verschieben, Anschlüsse, Größenänderung,
  Undo/Redo und Einklappen bleiben erhalten. Ansicht ist keine Asset-Revision.

## Prüfstrategie und Wiederherstellung

Zuerst fokussierte echte Qt-Tests: runde Trefferfläche/Rendering, sichtbare
Auswahl, Mitteltasten-Drag ohne Karten-/Revisionsänderung, begrenzter Weg in
alle vier Richtungen, unveränderte Grenzen bei wiederholtem Panning, Zoom,
Fenstergröße und unterschiedliche Kartenlagen. Danach bestehende Canvas-
Tests für Ports, Größenanfasser, Verbindungen, Einklappen und Undo/Redo sowie
gesamte Studio-Tests. Neue Quell-/Testdateien auf Stil prüfen; Gesamtcheck
mit vorhandenen externen Problemen ehrlich melden.

Nur temporäre Testprojekte/Screenshots; keine Bilder im Spielbestand ändern.
Gezieltes Staging ausschließlich eigener Dateien, keine destruktiven Git-
Befehle. Änderungen an der Ansicht lassen bestehende Katalogdaten kompatibel.

## Ergebnis und Rückblick

In Arbeit. Die neue kurze Prüfliste trennt „jetzt prüfen“ von „zurückgestellt“;
ausgelassene persönliche Prüfungen gelten ausdrücklich nicht als abgenommen.
