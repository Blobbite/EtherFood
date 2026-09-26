# Arbeitsplan: Asset Studio, Zwischenpaket 4a

## Zweck und Ausgangslage

2026-09-26: Die erste Benutzersichtung bestätigt Projektanlage, Hierarchie,
Kartenverschiebung, Zahlenfelder für Größe, grundlegende Verbindungen,
Dokumentimport, Aufgabenanlage/Filter/Status sowie Speichern/Wiederöffnen.
Aufgabenbeschreibungen sind gespeichert, aber nicht sichtbar. Linienbeschriftungen
überlappen die Linien. Direkte Canvas-Bedienung, Kontextaktionen und gut erkennbare
Status-/Verwendungsanzeigen fehlen. Der Benutzer hat Zwischenpaket 4a freigegeben.

## Umfang und Nicht-Ziele

Vier verknüpfte Nachbesserungsissues unter Phase B, mit Bezug zu T009–T012:

1. Aufgaben/Issues lesen und revisionssicher bearbeiten.
2. Canvas: Größen-Griff, vier Anschlusspunkte, Verbindungen anlegen/umhängen,
   lesbare Beschriftungen, Undo/Redo und unveränderter Hierarchie-/Zyklusschutz.
3. Kontextaktionen in Baum/Canvas, direkter Dokumentzugriff und einheitliche Typicons.
4. Verständliche Statusgründe, Herkunft und gemeinsame Asset-Verwendungen.

Keine freien Tags/Labels, Bildimporte/-verarbeitung, Maskeneditor, Vorschaupipeline
oder Godot-Bereitstellung. T013 und spätere Pakete werden nicht vorweggenommen.
Die bereits offenen Control-Änderungen gehören nicht in die 4a-Commits.

## Schritte und Fortschritt

- [x] Abnahmebefunde als vier referenzierte GitHub-Issues erfassen:
  [#56](https://github.com/Blobbite/EtherFood/issues/56) Aufgaben,
  [#57](https://github.com/Blobbite/EtherFood/issues/57) Canvas,
  [#58](https://github.com/Blobbite/EtherFood/issues/58) Navigation,
  [#59](https://github.com/Blobbite/EtherFood/issues/59) Status/Verwendungen;
  als Unterissues von Phase B (#3).
- [x] Aufgaben-/Issue-Details und Bearbeitung einschließlich Konfliktschutz (#56).
- [x] Canvas-Bedienung und kollisionsfreie Beschriftung (#57).
- [ ] Kontextaktionen, Baum-Inhalte und Typicons.
- [ ] Verständlicher Status und gemeinsame Verwendungen.
- [ ] Regressionstests, echte Qt-Ereignisse, Pipeline- und Standardcheck.
- [ ] Prüfanleitung und Übergabe zum nächsten Briefing.

## Entscheidungen und Erkenntnisse

- Änderungen an Aufgabeninhalten dürfen bestehende Aufgabenabnahmen nicht
  still auf einen geänderten Text übertragen. Asset-Freigaben bleiben unabhängig.
- Geometrie bleibt Ansichtszustand; Verbindungstypen werden bewusst gewählt.
  Umhängen erhält die Relations-ID und erfolgt atomar mit Rückgängig/Wiederholen.
- Beschriftungen werden neben Linien platziert; zusätzliche Maskierung hält
  Text auch bei dichter Anordnung frei von durchlaufenden Linien.
- Kontextmenüs verwenden dieselben Dienste wie die bestehenden Schaltflächen.
- Standard-Qt-Icons benötigen keine zusätzlichen Bilddateien/Abhängigkeiten.
- Jeder Abschnitt wird gezielt geprüft, mit englischem Emoji-Commit committed
  und gepusht. Die neuen Issues bleiben bis zur menschlichen Sichtabnahme offen.

## Prüfungen

Geplant: Aufgabeninhalt nach Auswahl und Neustart, Revisionskonflikt und Abbruch;
echter Größen-/Verbindungsdrag; kein Datenverlust bei ungültigen Verbindungen;
Umhängen/Undo mit stabilen IDs; Labels bei überkreuzten Linien und Größenänderung;
Kontextnavigation ohne Verlust ungespeicherten Textes; gleiche Asset-ID über zwei
Verwendungen; deutsche Statusgründe ohne erfundene Freigaben.
Nur tatsächlich ausgeführte Tests werden als bestanden dokumentiert.

Abschnitt 4a.1: 60 Studio-Tests bestanden, einschließlich neuer Qt-Tests für
Detailauswahl, Speichern, Abbruch, Revisionskonflikte und Dokumentnavigation.
Der erste Gesamtlauf endete nach 60 erfolgreichen Tests mit einem nativen
Qt-Prozessfehler beim Beenden; Einzelprüfung und Wiederholung mit Faulthandler
beendeten sich regulär (Exit 0). Im abschließenden Gesamtlauf erneut prüfen.

Abschnitt 4a.2: 64 Studio-Tests bestanden. Echte Mausereignisse prüfen Größen-Griff,
Port-Drag, Beschriftungsauswahl, Endpunkt-Drag und Zyklus-/Abbruchschutz; Diensttests
prüfen Relations-ID, atomare Ablehnung, Hierarchieumordnung und Undo/Redo.
Beschriftungen werden neben Linien platziert; bei dichter Anordnung werden
durchlaufende Striche unter der Beschriftung maskiert. Tooltip und Auswahl zeigen
die zugehörige Verbindung. Synthetischen Canvas-Screenshot geprüft.
Der Qt-Testabbau gibt native Widgets jetzt explizit vor QApplication frei;
die anschließenden Gesamtläufe beenden sich regulär. 43 Quelldateien/Testdateien
ohne Stilbefund geprüft.

## Wiederholbarkeit und Wiederherstellung

Alle Tests mit synthetischen Projekten in temporären Verzeichnissen. Keine
Originalgrafiken oder Benutzerkataloge ändern. Keine pauschalen Git-Rücksetzungen.
Neue Metadaten müssen bestehende Kataloge ohne Datenverlust weiterverwenden.
Arbeitsverzeichnis-spezifische Pfade, Qt-Bibliotheken und Credentials bleiben lokal.

## Ergebnis und Rückblick

In Arbeit. Nach Abschluss folgt eine nummerierte Sichtprüfungs-Checkliste.
