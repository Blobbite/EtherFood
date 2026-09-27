# Briefing nach Paket 6 – Quellen und Asset-Menü

Rückmeldung: Quellenbutton sowie 1×16- und 4×4-Import bestätigt. Gewünschte
Bedienkorrekturen und Aufgabenintegration werden in
[Zwischenpaket 6a](../plans/asset-studio-paket-6a.md) bearbeitet. Die übrigen
Prüfpunkte gelten dadurch nicht pauschal als abgenommen.

T015/#22 und T016/#23 sind technisch implementiert. Der vorherige
Canvas-Nachtest ist vollständig vom Benutzer bestätigt. Jetzt geht es nur
um Quellenimport und Anlage; automatische Bildverarbeitung kommt später.

Studio neu starten: `python3 tools/control.py asset-manager run`.
Das vorhandene Testprojekt genügt. Keine optionalen PyGameTools-/Archiv-/Godot-
Wurzeln erforderlich. Für die kleine NPC-Probe eine zusätzliche Testkarte
anlegen, kein zweites Projekt und keine manuelle Variantenordnerstruktur.

## Sechs kurze Prüfpunkte

1. **Vorhandenen Helden öffnen:** Karte auswählen → **Asset-Menü …** → **Posen**.
   Rechts neben **Anker Y** steht je Pose **Spritesheets hinzufügen …** samt
   Lieferzähler der gespeicherten Anforderungen. Änderungen erst speichern
   oder beim Import die Speicherung bewusst bestätigen.
2. **Eine Richtung importieren:** Beispielsweise das richtige Walk-SW-PNG
   auswählen. Pose `walk`, Richtung `SW` kontrollieren. Für ein **4×4-Sheet
   mit 16 Frames ausdrücklich `4x4` wählen**; `16x1` ist nur der horizontale
   Streifen, `1x16` der vertikale. **Auswahl prüfen**, dann **Geprüfte Quellen
   importieren** bestätigen. Dateiname/Zuordnung stehen unter **Quellen**;
   der Posen-Lieferzähler steigt um eins. Originaldatei bleibt erhalten.
3. **Teilstand und fehlende Funktionen:** Nicht gelieferte Richtungen bleiben
   **Fehlt**, nicht benötigte **Nicht erforderlich**. Oben stehen tatsächliche
   Sperrgründe. Farben/Masken, Varianten und Prüfungen sowie Erzeugen/Godot
   sind erkennbar noch nicht bedienbar. Es darf keine fertige Erzeugung oder
   Freigabe behauptet werden.
4. **NPC anlegen und abbrechen:** **Neues Asset / NPC …**, vier Richtungen
   `N,O,S,W`, Posen Walk und Stand jeweils als `spritesheet`, fünf Grafikprofile
   und Frames `8,10,12,14,16` wählen. Zusammenfassung: **8 Quellen / 200 geplante
   Varianten**. Einmal abbrechen: keine neue Karte. Danach bewusst anlegen:
   genau eine Karte unter dem gewählten Besitzer, keine leeren Variantenordner.
5. **Vorlage und neue Lieferung:** Eine vorhandene Figur als
   **Nur Konfiguration** laden. Neuer NPC hat eigene Identität und zunächst
   keine importierten Quellen/Freigaben. Beim erneuten Import derselben
   Pose/Richtung muss Ersetzen bestätigt werden; die alte Revision bleibt
   unter **Versionen** bzw. **Quellen → Aufbewahrte Revisionen** erhalten.
6. **Wieder öffnen:** Projekt schließen und erneut öffnen. Quellenzuordnung,
   aktive Revision, Teilstand und Asset-ID bleiben erhalten. Eine Notiz im
   Asset-Menü ist auch beim selben Asset im Projektbaum unter Dokumenten
   vorhanden. Keine zweite Asset-Kopie entsteht.

Rückmeldung genügt als `✅ 1–6` oder `❗ 2: …` mit kurzem Ablauf/Screenshot.
Bei zwei Posen mit acht Richtungen sind 16 Quellen nötig; nach einem einzigen
Import ist der Gesamtstand also **1/16**, nicht 1/400. Quellenzahl und geplante
Variantenzahl sind bewusst verschiedene Werte.

## Für diese Runde überspringen

- Canvas, FPS-/Frame-Anforderungen und alte Such-/Filterfunktionen nicht
  vollständig wiederholen; sie sind bereits geprüft.
- Keine 200/400 Varianten importieren. Für den Quelltest genügt eine oder
  wenige Richtungen derselben Masterlieferung, nicht alle fünf Grafikstufen.
- Keine PNGs absichtlich beschädigen oder während Import überschreiben.
  Limits, Korruption, Änderungsrennen und Abbruch sind automatisiert geprüft.
- Keine Farben/Masken, automatische Varianten, Godot-Tests oder Freigaben:
  Sie sind noch nicht implementiert. Auch alte Bestandsabnahmen werden dadurch
  nicht nachträglich als bestanden erklärt.

## Danach vorgesehen

T017/#24 und T018/#25: ausführbare Aufträge/Pipeline-Anbindung und nachvollziehbarer
Buildplan mit Abhängigkeiten, geprüftem Cache, Abbruch und Wiederaufnahme.
Danach folgen die benötigten echten Farb-/Masken-/Frame-/Grafikschritte.
Die nächste Umsetzung startet erst nach Rückmeldung/Freigabe, nicht automatisch.
