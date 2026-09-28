# Arbeitsplan: Quellenworkflow und Canvas-Nachbesserung

Fortschreibung: Der Canvas-Nachtest ist vom Benutzer vollständig bestätigt.
Abschnitt A (T015/#22 und T016/#23) ist inzwischen in
[Paket 6](asset-studio-paket-6.md) technisch umgesetzt. Die nachfolgenden
Abschnitte B–D sind durch das Pipelinepaket `2286d2f` teilweise technisch
umgesetzt; Worker, Buildgraph und echte Bildadapter nicht erneut neu bauen.
Vollständige Master-/Maskenverwaltung, variable Timingdetails und ausdrücklich
aktivierbare Importautomatik bleiben gesonderte Restarbeit nach
[PIPELINE-ALIGNMENT-V1](asset-studio-github-issues.md).
Die folgenden Ausgangs-/Ergebnisabschnitte dokumentieren den damaligen Stand.

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
- [x] Karten runden; endlichen Freiraum und explizites Mitteltasten-Panning umsetzen.
- [x] Qt-Regressionsprüfungen, Grenzfälle und Ansichten tatsächlich prüfen.
- [x] Kurze neue Prüfliste, Ergebnisdokumentation, englische Emoji-Commits und Push.

Keine Quellbilder bearbeiten, keine Freigabe übertragen, keine neuen
Animationen erzeugen. Der Quellenbutton und die Pipeline werden in diesem
Abschnitt geplant, nicht durch einen funktionslosen Knopf vorgetäuscht.

## Ursprünglich geplanter Arbeitsablauf (historischer Ausgangsstand)

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

Die Plananpassung ist als `cbf2e8a` committed. Canvas-Code umgesetzt;
8 neue Qt-Tests und 20 bestehende Qt-Bedienungstests bestanden. Getestet sind
Rundung/Auswahl, Mitteltasten-Drag, vier Anschläge, Zoom 0,25/0,8/1/2,5,
Fenstergrößenwechsel, leeres Board, Kartengröße/-position und Verbindungs-
vorschau ohne unbegrenztes Wachstum. Vollständiger Studio-Lauf: **117 Tests
bestanden**. **58 Studio-Quell-/Testdateien ohne Stilbefund** und `git diff
--check` ohne Befund. Tatsächliche Qt-Screenshots von Board und Pan-Anschlag
geprüft; nur temporäre synthetische Projektdateien, keine Spielgrafik geändert.

`python3 tools/control.py check` tatsächlich ausgeführt: weiterhin **257
bestanden, 37 übersprungen, 2 fehlgeschlagen** (bestehende Dokumentationslücken/
13 Verweise), Godot 4 nicht vorhanden und 1907 bestehende Stilbefunde in
224 geprüften Dateien. Kein neuer Studio-Stilbefund. Pipeline-Bestandstests
werden bei dieser reinen Canvas-Änderung nicht als erneut ausgeführt behauptet.

Die neue kurze Prüfliste trennt „jetzt prüfen“ von „zurückgestellt“;
ausgelassene persönliche Prüfungen gelten ausdrücklich nicht als abgenommen.
Aktuelle Benutzerübergabe: [vier Prüfpunkte](../asset-studio/SICHTPRUEFUNG_CANVAS.md).

Abgeschlossen sind die Planpräzisierung und die Canvas-Implementierung.
Die präzisierte Bedienung wurde bei den vorhandenen Issues #22/#23 als
Planung ergänzt; beide bleiben offen. Der Quellenbutton und die automatische
Erzeugung wurden nicht implementiert und werden nicht als testbereit ausgegeben.
Bei dieser Übergabe waren persönliche Canvas-Sichtprüfung und zurückgestellte
Paket-5-Punkte noch offen; die neuere Rückmeldung steht im nächsten Abschnitt.
Kein bestehender Benutzerstand, Originalbild oder fremder Git-Diff entfernt.

## Nachprüfung: Positionssprung nach Zoom

27.09.2026, Basis `1d2eb0e`: Der Benutzer bestätigt die vier kurzen Prüfpunkte
mit Haken, meldet aber einen zusätzlichen Fehler: Je nach Zoom verschieben
sich Karten beim Anklicken gegeneinander. Die bestätigten Punkte bleiben
angenommen; nur der neue Auswahl-/Bewegungsfehler benötigt einen Nachtest.
Die zurückgestellten Bestands- und Pipelineprüfungen bleiben zurückgestellt.

### Schritte und Fortschritt

- [x] Auswahl, Zentrierung, Mausbewegung und bisherige Tests untersuchen.
- [x] Fehler mit echten Qt-Mausereignissen bei mehreren Zoomstufen nachstellen.
- [x] Ursache gezielt korrigieren; bewusste Navigation und Drag/Undo erhalten.
- [x] Regressionen und Studio-Prüfungen ausführen, Ergebnis dokumentieren.
- [x] Nachtest und nächstes Paket dokumentieren; nur eigene Dateien für Commit/Push bereitstellen.

Ursache durch acht fehlschlagende Qt-Regressionen vor der Korrektur belegt:
Die Canvas-Auswahl verwendet denselben zentrierenden Navigationspfad wie
der Projektbaum. Eine Zentrierung zwischen Mausklick und Mausbewegung
verändert den Bezugspunkt des laufenden Drags. Bei Zoom 0,25 wurden im
Test nach 40 Pixel Mausweg x=195 statt x=455 gespeichert. Auch ein reiner
Klick verschob unbeabsichtigt den Sichtausschnitt. Gezielte Trennung:
Canvas-Auswahl ohne Zentrierung; Navigation über den Baum oder die Suche
darf weiterhin die Zielkarte ins Bild holen. Die verzögerte Verarbeitung
zum Schutz beim Speichern einer offenen Notiz bleibt erhalten.

Nur Canvas-Auswahl und die zugehörigen Prüfungen ändern. Kein automatisches
Neuanordnen bestehender Projekte, keine Originalbilder oder fremden Änderungen
übernehmen. Als Nächstes bleibt Abschnitt A (T015/#22, T016/#23) vorgesehen;
Quellenimport und Varianten-Erzeugung werden in dieser Fehlerkorrektur nicht
zusätzlich implementiert.

### Tatsächlich ausgeführte Nachprüfungen

- Vor der Korrektur: acht reproduzierbare Fehler in
  `tests/gui/test_canvas_selection.py`, jeweils bei Zoom 0,25/0,8/1/2,5.
- Nach der Korrektur: 16 neue Qt-Fälle für reinen Klick, kleine und größere
  Bewegung nach gedrückter Auswahl, Undo/Redo, unveränderte Asset-Daten,
  Wiederöffnen, Baum-/Suchnavigation sowie Speichern/Abbrechen offener Notizen.
- Fokussierter Lauf mit `test_canvas_selection.py`, `test_canvas_workspace.py`,
  `test_review_ui.py` und `test_dashboard.py`: **44 bestanden**.
- `QT_QPA_PLATFORM=offscreen .venv/bin/python -X faulthandler -m pytest -q
  tools/AssetManager/tests`: **133 bestanden**; vorhandene temporäre
  Qt-Systembibliotheken über `LD_LIBRARY_PATH` verwendet.
- Stilprüfung der Studio-Quellen und -Tests: **59 Dateien, keine Befunde**.
  `git diff --check` ohne Befund.
- `python3 tools/control.py check` erneut ausgeführt: **257 bestanden,
  37 übersprungen, zwei Dokumentationstests fehlgeschlagen**. Weiterhin fehlen
  Godot 4 und die bekannten Dokumentationsziele; 1907 vorhandene Stilbefunde
  in jetzt 225 geprüften Dateien. Kein neuer Studio-Befund.

Die Nachtestliste trennt drei kleine manuelle Prüfungen von den bereits
bestätigten vier Punkten und nennt Quellenimport/Asset-Anlage als nächstes
Paket. Die persönliche Nachprüfung des Fixes bleibt offen. Bestehende
Anordnungen werden nicht automatisch verändert oder nachträglich repariert;
nur bewusstes Ziehen darf künftig neue Positionswerte speichern.
