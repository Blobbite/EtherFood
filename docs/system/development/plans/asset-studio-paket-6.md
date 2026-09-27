# Arbeitsplan: Paket 6 – Quellenimport und Asset-Anlage

## Zweck und Ausgangslage

27.09.2026, Basis `f2690f0`, Issues T015/#22 und T016/#23. Der Benutzer hat
die drei Canvas-Nachtests bestätigt und dieses nächste Paket freigegeben.
Ziel: Anforderungen festlegen, Quellen je Pose auswählen und zentral sicher
registrieren; neue Figuren mit derselben Oberfläche anlegen und verwalten.
Die automatische Varianten-Erzeugung bleibt ausdrücklich späteren Paketen
vorbehalten. Vorgänger T005/T008/T009/T013/T014 sind technisch vorhanden.

Gelesen: Repository-Regeln, Aufgaben, Arbeitsregeln, Projektbrief, Architektur,
Datenverträge und Vorgängerberichte. Bestandsbeobachtungen aus T014 sind keine
verwalteten Quellen. Bestehende Control-/Doku-/Grafikänderungen bleiben separat.

## Umfang und Schritte

- [x] Aufgaben, Vorgänger und tatsächliche Dienste prüfen; Canvas-Abnahme festhalten.
- [x] T015: begrenzte Bildprüfung, unveränderliche Quellenrevisionen, aktive Zuordnung.
- [x] T015: Importdialog mit explizitem Raster, Konflikten, Teilstand und Abbruch.
- [x] T015: negative/Core-/Qt-Tests, Bericht, englischer Emoji-Commit und Push.
- [x] T016: Anlageassistent/Vorlagen mit Zusammenfassung und atomarer Anlage.
- [x] T016: Asset-Menü, Posenbutton neben Anker Y, echte Status-/Quellenanzeige.
- [x] T016: End-to-End-NPC-Nachweis, Gesamtprüfung und Bericht; Commit/Push vorbereiten.
- [x] Kurzes Benutzerbriefing und sichtbare offene Folgeaufgaben dokumentieren.

## Verträge und Entscheidungen

- PNG-Originale bleiben unberührt. Nur geprüfte Kopien im bestehenden
  SHA256-Blobstore unter WORKSPACE_ROOT, keine Variantenordner oder Spielablage.
- Raster immer Spalten × Zeilen und explizit gewählt: 16×1, 1×16, 4×4 oder
  benutzerdefiniert. Keine Entscheidung anhand der längeren Bildseite.
- Einzelbild und Animationssheet sind unabhängige Quellenarten. Ein Einzelbild
  ersetzt keine fehlende Animationslieferung und wird nicht daraus ausgeschnitten.
- Importplan bindet Asset-Revision, Quellenbytes und Zuordnung; geänderte,
  beschädigte oder unvollständige Dateien führen nicht zu einer Teilregistrierung.
- Mehrere Lieferungen bleiben unveränderliche Revisionen. Eine bestehende aktive
  Zuordnung wird nur ausdrücklich ersetzt; ältere Originale bleiben auswählbar.
- Vorlagen kopieren nur Konfiguration und erhalten neue Pose-/Asset-IDs;
  keine Quellen, Nachweise oder Freigaben. Scope bleibt eine Besitzerrelation.
- Hintergrundimport nutzt eine eigene Katalogverbindung; Widgets schreiben
  keine SQL-Statuswerte. Keine Verarbeitung externer Programme und keine
  vorgetäuschten Pipeline-/Godot-Erfolge.

## Prüfstrategie

Synthetische PNGs und temporäre Projekte. Zuerst Core: 16×1, alternative Raster,
Limits/Teilbarkeit, doppelte Zuordnung, veränderte Quelle, Abbruch, unveränderliche
Vorgänger, aktive Revisionen, Snapshot ohne ungeprüfte Quellfreigabe, Invalidation.
Dann echte Qt-Events: Datei-/Mehrfachauswahl, Raster, Teilimport, Schließen/Abbruch,
NPC mit vier Richtungen/zwei Posen, Neustart und identische Asset-ID.
Abschließend Studio-, bestehende Pipeline- und passende Stilprüfungen sowie
Repository-Standardcheck; vorhandene Fremdbefunde bleiben als solche gemeldet.

## Wiederherstellung

Importfehler lassen Originale und aktive Vorgänger unberührt. Staging-/Blob-
Operationen bleiben im vorhandenen Journal sichtbar; keine pauschale Löschung.
Erneut prüfen und bewusst importieren. Keine automatische Reparatur bestehender
Kartenlayouts. Nur aufgabeneigene Dateien gezielt committen und pushen.

## Erkenntnisse, Prüfungen und Ergebnis

Katalog kennt bereits unveränderliche `source_revision`-Objekte;
eine neue Datenbank oder parallele Asset-Metadatenablage ist nicht erforderlich.
Persönliche Import-/Anlageabnahme folgt erst nach dieser Umsetzung.

T015-Kern: 53 fokussierte Core-/Vorgängertests bestanden. Danach 22 Tests für
Quellenkern, echten Qt-Importdialog und bestehenden Anforderungsdialog bestanden.
PNG-Dateigrenze 64 MiB, Pixelgrenze 32 Millionen, höchstens 128 Dateien pro
Lieferung; alte kleinere Frame-Originale bleiben als separate Revisionen erhalten.
Snapshots exportieren Metadaten, keine Bildbytes: importierte Verweise sind
ungeprüft und werden nicht als vollständige aktive Lieferung gewertet.

T015 abschließend: **154 Studio-Tests bestanden**, **66 Dateien ohne
Stilbefund**, `git diff --check` sauber. [Ergebnisbericht](../asset-studio/task-results/T015.md).
Keine Game-Originale verwendet oder geändert; keine zusätzlichen Abhängigkeiten.
T015 committed und gepusht als `e1c88b8`. T016 beginnt mit einem gemeinsam
verwendeten Anforderungsformular; Vorlage und Import besitzen keine zweite
abgewandelte Definition derselben Asset-Einstellungen.

T016 gezielt: 21 vorhandene Modell-/Formulartests sowie 13 Tests für
Konfigurationsvorlagen, neuen NPC-Ablauf, Quellenbutton, Wiederöffnen,
Dokumentzuordnung, Abbruch und bestehende Dashboard-Kontextaktionen bestanden.
Archivierte Assets mit Quellen bleiben wieder öffnungsfähig; ihre Importaktion
bleibt gesperrt. Benutzerbestätigung für ungespeicherte Posen und Notizen vorhanden.

Abschluss T016: Control-Asset-Check erfolgreich mit 158 Studio- und 171
Pipeline-Tests. Nach zusätzlichem Test der Speicherbestätigung **159 Studio-
Tests bestanden**; **70 Dateien ohne Stilbefund**. Reale Qt-Screenshots von
Posen, Quellen und Anlageassistent mit synthetischen Testdaten geprüft.
Der Standardcheck bleibt mit zwei bekannten Dokumentationsfehlern
(257 bestanden/37 übersprungen), fehlendem Godot 4 und 1907 geerbten
Stilbefunden in 236 Dateien rot. Kein neuer Studio-Befund.

[Ergebnis T016](../asset-studio/task-results/T016.md) und
[sechs aktuelle manuelle Prüfpunkte](../asset-studio/SICHTPRUEFUNG_6.md).
T015/T016 sind technisch fertig; persönliche Paket-6-Abnahme und alte bewusst
zurückgestellte Bestandsprüfungen bleiben offen. Kein Folgepaket gestartet,
keine Bildverarbeitung oder Spielintegration als fertig behauptet.
