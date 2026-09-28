<!-- PYGINDEX:NAVIGATION START -->
[Übergeordnete Übersicht](index.md)
<!-- PYGINDEX:NAVIGATION END -->

# Arbeitsplan: Blueprint-Tempeltexturen im F5-Labor

## Zweck und Ausgangslage

Stand: 27. September 2026.

Die 55 gelieferten PNGs unter `game/test_assets/environment/tilesets/temple/`
ersetzen den bisherigen Blueprint-Boden. Die fünf vorhandenen F5-Grafikstufen
sollen die jeweils passenden Tempeltexturen verwenden. Bisher reduziert die
Portalzuordnung diese fünf Stufen auf zwei alte Bildsätze. Neun Bodenmotive,
eine Wand und ein Dach liegen in jeder neuen Grafikstufe vor.

## Umfang und Entscheidungen

- Die bestehende gemeinsame Grafikauswahl für Figur und Labor bleibt erhalten.
  Jede der fünf Stufen lädt ihren eigenen Tempelbildsatz.
- Eine zusätzliche F5-Bodenauswahl macht alle neun Motive vergleichbar.
  Bodenmotiv und Grafikstufe bleiben bei Raumwechseln und Neustarts erhalten.
- Wand und Dach bilden den sichtbaren Rand der offenen Tempelfläche. Die
  Laufwege, Portale, Raumzustände, Kollisionen und Weltgrößen bleiben erhalten.
- Türen und Testobjekte verwenden ihre bisherigen Bildsätze, da das neue
  Paket dafür keine Ersatzgrafiken enthält. Die Anzeige benennt diese Zuordnung.
- Die PNGs bleiben unverändert unter `test_assets`. Es gibt keine Assetfreigabe
  und keine Änderung an Kanon, Gamedesign oder angenommenen Spielstandards.

## Schritte und Fortschritt

1. [x] Dokumentation, Szenen, Grafikstufen und alle gelieferten PNGs prüfen.
2. [x] Tempelzuordnung, Bodenmotive sowie Wand- und Dachrand einbauen.
3. [x] F5, Speicherung, Raumwechsel und verständliche Anzeigen verbinden.
4. [x] Asset- und Laufzeittests erweitern; Bedienung dokumentieren.
5. [x] Gezielte Prüfungen, Renderkontrolle und Standardlauf ausführen.

## Erkenntnisse und Überraschungen

Die nativen Größen unterscheiden sich zwischen den fünf Bildsätzen. Texturen
müssen deshalb dieselbe Weltfläche belegen. Der Arbeitsbaum enthält bereits
umfangreiche Benutzeränderungen, darunter die neuen PNGs und Laborstandards.
Diese Arbeit ergänzt die Integration und überschreibt keine dieser Änderungen.
Godot 4.7.2 ist als lokale Testinstallation vorhanden.

## Prüfungen

- Ausgangsstand: `tools/tests/test_portal_lab_assets.py`: 6 Tests bestanden.
- Ausgangsstand: Portalnavigation und bisherige F5-Grafiksuite bestehen ihre
  Erwartungen, melden aber bereits beim Instanziieren der Figur die fehlende
  Animation `stand_S`. Die globale Stilprüfung meldet vorhandene Fehler vor
  allem in den Werkzeugen unter `tools/AssetManager/`.
- Geplant: alle 55 Importe, echte F5-Auswahl, neun Motive, fünf Grafikstufen,
  Speicherung, Raumwechsel, Weltgrößen und unabhängige Texturfilter.
- Erweiterte Assettests: 8 bestanden. Portal-Grafik, Portalnavigation und
  F5-Menüsteuerung: jeweils keine fehlgeschlagenen Erwartungen. Alle neun
  Motive werden in allen fünf Stufen geladen; alle Räume erhalten die Auswahl.
- Die sieben geänderten Quelldateien bestehen die gezielte Stilprüfung.
  Die neu ergänzten Links sind erreichbar. Die globale Linkprüfung findet
  13 bereits vorhandene ungültige Verweise; zwei davon stehen im bisherigen
  Text der Laborbeschreibung. Alle 55 gelieferten PNGs sind unverändert.
- Acht Renderansichten bei 1280 × 720 zeigen das F5-Menü, die erreichbare
  Bodenauswahl einschließlich aller neun Einträge, Comic High, Pixel Art Low,
  den kreisförmigen Rand sowie einen rechteckigen Raum mit Comic Mittel.
  Die Dachstreifen lassen die begehbare Fläche sichtbar.

Der Standardlauf `python tools/control.py check` mit der lokalen Godot-Version
4.7.2 wurde ausgeführt: Doctor 12/12, Ressourcenimport erfolgreich, Python
259 bestanden, 37 übersprungen und zwei Fehler zur vorhandenen Dokumentation.
Die globale Stilprüfung meldet 1907 Verstöße außerhalb der geänderten Quellen.
Godot meldet 456 fehlgeschlagene Erwartungen, überwiegend zu den bestehenden
Laborstandards und Filtervorgaben. Ein zusätzlicher vollständiger Godot-Lauf
mit Kopien der ursprünglichen Szenen und Skripte außerhalb des Repositorys
liefert exakt dieselben 456 Fehlermeldungen; keine ist hinzugekommen.
Die bereits beim Ausgangstest gemeldete fehlende Animation `stand_S` bleibt
bestehen. Der Gesamtcheck ist daher nicht grün.

## Wiederholbarkeit und Wiederherstellung

Der Godot-Ressourcenimport erzeugt die portablen `.import`-Metadaten. Caches,
Testberichte und Renderaufnahmen bleiben lokal außerhalb versionierter Inhalte.
Die PNG-Prüfsummen werden vor und nach der Integration verglichen. Vorhandene
Änderungen bleiben erhalten; es werden keine Git-Rücksetzungen verwendet.

## Ergebnis und Rückblick

Die 55 Tempeltexturen sind mit eigenen nativen Importen eingebunden. F5
schaltet die fünf Grafikstufen gemeinsam mit der Figur um und bietet alle
neun Bodenmotive separat an. Wand und Dach rahmen die vorhandenen Räume ein.
Grafik- und Motivwahl bleiben über Raumwechsel und Neustarts erhalten.
Die gezielten Prüfungen bestehen; der globale Prüfstand bleibt wegen der
oben belegten Bestandsfehler rot. Die Assetfreigabe bleibt ausstehend.
