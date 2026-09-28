# Projektweite, Canvas-integrierte Bildpipelines

Dieser Plan bewahrt Umsetzung und tatsächlich damalige Prüfergebnisse von
`2286d2f`/`f8c9991`. Die aktuelle Verteilung der Restarbeit auf bestehende Issues
ist in [PIPELINE-ALIGNMENT-V1](asset-studio-github-issues.md) verbindlich ergänzt.
Die folgende Ausgangslage ist historisch, nicht der heutige Funktionsstand.
Die dort erwähnte Agentenfreigabe gilt nicht für den späteren reinen
Planungsauftrag. Persönliche Pipeline-Sichtabnahme bleibt separat offen.

## Aktuelle Korrektur: Pipelines direkt am Projekt (28.09.2026)

Der Nutzer präzisiert die Besitzebene: Pipeline-Karten sind direkte Bestandteile
des geöffneten Projekts, als Geschwister von „Projektweit“. Diese Entscheidung
ersetzt die unten historisch beschriebene Ablage unter dem globalen Rahmen.
Es entsteht keine zusätzliche Global-Struktur und keine Anwendungsbibliothek.

Ausgangsbefund: Besitzregeln und Kontextmenüs erlauben Pipelines bisher nur unter
„Projektweit“; der Werkzeugleisteneintrag „Bildpipeline (später)“ ist deaktiviert.
Der Core-Testlauf scheitert unabhängig davon an der fehlenden Testabhängigkeit
`markdown-it-py`, die bereits für die GUI festgelegt ist.

1. [x] Besitzregeln, Menüwege, Katalogmigrationen und bestehende Tests prüfen.
2. [x] Direkte Projektzuordnung und gesicherte Migration vorhandener Rezepte
   und projektweiter Zuweisungen einschließlich Archiv und Revisionen umsetzen.
3. [x] Projekt-/Canvas-Menüs und Werkzeugleiste an dieselben Dienste anbinden.
4. [x] Migration, Erstellung, Import, Undo/Redo und Qt-Bedienung prüfen;
   vorhandene Markdown-Abhängigkeit für den Core-Testlauf bereitstellen.
5. [x] Bedienung/Architektur aktualisieren und tatsächliche Ergebnisse festhalten.

Die Migration verwendet die vorhandene Katalogsicherung und eine Transaktion.
IDs, Rezeptparameter, Quellen, Layouts, Asset-Zuweisungen und eingefrorene Builds
bleiben erhalten; Besitzänderungen erhalten einen zusätzlichen Historieneintrag.
Keine Bilder neu erzeugen und keine externen Issues ohne Auftrag verändern.
Zur Wiederherstellung steht der unveränderte Katalog vor der Migration als
`.studio-backup-*` neben dem Projektkatalog bereit.

Ergebnis: Neue und importierte Pipeline-Karten liegen direkt am Projekt.
Projektweite Zuweisungsregeln werden ebenfalls dem Projekt zugeordnet; explizite
Asset-Zuweisungen behalten ihren Besitzer. Kontextmenüs an Projektkarte und freier
Canvas-Fläche sowie der aktive Zahnradknopf **Pipelines …** führen zu denselben
Diensten. Baum und automatische Anordnung zeigen Pipelines vor „Projektweit“;
manuelle Positionen werden erhalten. Auch alte Metadaten-Snapshots werden beim
Import auf diese Besitzregeln übernommen.

Die neuen Menütests fanden zusätzlich einen bestehenden Fehler: Nach Rückgängig
der Pipeline-Erstellung versuchte die Statusanzeige, das archivierte Rezept zu
öffnen. Sie zeigt nun den Archivstatus an; die Ausführungssperre bleibt bestehen.
Der bisherige Dashboard-Test für einen deaktivierten Pipeline-Platzhalter ist
entsprechend dem neuen Verhalten aktualisiert.

Tatsächlich ausgeführte Abschlussprüfungen:

- `python3 tools/control.py asset-manager test --core`: **369 bestanden,
  3 Qt-Tests übersprungen** (zu diesem Zeitpunkt fehlende Systembibliotheken).
  Der Markdown-Abbruch ist behoben; die Abhängigkeit gehört nun zum Testpaket.
- Danach die benötigten Qt-Bibliotheken nur unter `/tmp` entpackt und per
  `LD_LIBRARY_PATH` für diese Docker-Sitzung bereitgestellt. Die zentrale
  Steuerung installiert weiterhin keine Betriebssystempakete automatisch.
- `python3 tools/control.py asset-manager test`: **595 bestanden**, keine
  übersprungenen oder fehlgeschlagenen Tests (130,98 s), einschließlich Qt,
  echter Bildverarbeitung, Migration/Backup/Rollback, Archiv, Import und Undo/Redo.
- Qt-Hauptfenster mit synthetischem Projekt als Screenshot geöffnet und geprüft:
  Pipeline und Projektweit sind Geschwister; Pipeline-Knopf ist aktiv und zeigt
  das Zahnrad. Persönliche Desktop-/Wayland-Abnahme **nicht ausgeführt**.
- Stilprüfung aller 20 geänderten Python-Dateien ohne Befund;
  `git diff --check` ohne Befund.
- `python3 tools/control.py check`: **283 bestanden, 37 übersprungen,
  4 fehlgeschlagen**. Bereits vorhandene Befunde: fehlende Asset-Kategorien,
  Godot-Fensterkonfiguration sowie fehlende Game-Decision-Dateien und deren Links.
  Die betroffenen Game-/Testdateien sind gegenüber `HEAD` unverändert.
  Zusätzlich 1907 bestehende Stilbefunde außerhalb der Änderung.
  Godot-Import/-Integration **nicht ausgeführt**, da Godot 4 fehlt.

Keine bestehenden Originalbilder oder Produktionsassets verändert. Die Änderungen
liegen lokal im Arbeitsbaum; kein Commit, Push oder externer Issue-Kommentar.

Bedienhinweis nachgezogen: Auch das Asset-Menü verweist bei fehlender Zuweisung
jetzt auf **Projektkarte → Rechtsklick → Pipeline aus Vorlage …**.

## Auftrag und Bestandsaufnahme

Der neue Auftrag ersetzt die zurückgestellte Bedienplanung für T017/T018.
Maßgeblich ist der lokale Arbeitsstand nach `01f3061`. Bestehende fremde
Game-, Control-, Dokumentations- und Bildänderungen bleiben unangetastet.

Vorhanden sind SQLite-Katalog und Revisionen (Migration 5), genau ein globaler
Projektrahmen, separate Canvas-Layouts/Undo, Quellkopien mit SHA256, ein typisierter
BuildGraph und ein kontrollierter Linux-Job-Supervisor mit Abbruch und geprüftem
Cache. Produktive Bildadapter fehlen bisher. Die bisherigen fünf Grafikschlüssel
sind in Domain, Formularen, Scanner und Schemas fest vorgegeben.

Die geprüften PyGameTools enthalten gemeinsame API-Funktionen für Grid/Crop,
Frameauswahl, Comic-Skalierung, Pixel-High-Quantisierung, Pixel-Low-Nearest-
Ableitung und Farbmodi. Starter können Originale verschieben oder Nebenprodukte
schreiben. Studio ruft diese Algorithmen ausschließlich mit Arbeitskopien auf;
die vorhandenen CLI-Einstiege bleiben bestehen.

## Entscheidungen und Schnittstellen

- Pipeline-Karten gehören nur unter den vorhandenen globalen Rahmen. Keine
  zweite Global-Struktur. Rezeptdaten und technische Verbindungen stehen getrennt
  von organisatorischen Relationen und Asset-Zuweisungen im Katalog.
- Projektprofile behalten feste Schlüssel und getrennte Anzeigenamen. Bestehende
  fünf Profile und Timing werden idempotent übernommen; Deaktivierung macht Ziele
  nicht erforderlich, verhindert aber keine nötigen internen Berechnungen.
- Rezepte enthalten versionierte Schritte, typisierte Ports, Parameter,
  Aktivierung, Ziele und Anwendbarkeit. Vorlagen werden beim Anlegen kopiert.
  Layout und reine Vorschau-FPS sind keine Bildparameter.
- Zuweisung: explizites Asset vor Typregel vor Projektstandard; gleichrangige
  Treffer werden Konflikte. Keine implizite Verkettung über Projektpfeile.
- Übersetzung in den vorhandenen BuildGraph; vorhandener JobService/Supervisor
  und BuildCache werden erweitert, kein zweiter Runner. Reale PNGs plus geprüfte
  Geometrie-/Timing-Metadaten sind Ausgaben; Diagnose ist kein Bildnachweis.
- Größen gelten pro Frame. Deterministische Rundung und ursprüngliche logische
  Größe/Anker/Crop werden dokumentiert. Pixel Low benutzt dieselbe quantisierte
  High-Palette, auch wenn High kein angefordertes Ausgabeprofil ist.
- Manifeste sind rein deklarativ. Python-Code wird nur nach gesonderter,
  hashgebundener lokaler Freigabe im Worker geladen. Kein automatisches Installieren
  oder Netzwerk, keine Behauptung einer Sicherheits-Sandbox.
- JSON-/Paketimport ist ein Vorschau-/Übernahmeablauf mit Größen-/Pfadprüfung,
  neuen Identitäten und ohne Codefreigaben. Legacy-Canvas bleibt bei unklarer
  Semantik blockiert; Dateizuordnungen werden gezielt protokolliert.

## Arbeitspakete und Fortschritt

1. [x] Regeln, Architektur, Arbeitsstand und vorhandene Verfahren prüfen.
2. [x] Datenmodell, Projektprofile, Migration und Zuweisungsdienste implementieren.
3. [x] Rezept-Canvas, Eigenschaften, Projektzugang und Asset-Zuweisung integrieren.
4. [x] Echte Bildadapter, Snapshot-Graphen, Timing und selektiven Cache integrieren.
5. [x] Erweiterungsvertrag, Vertrauensablauf und Import/Export einschließlich Legacy ergänzen.
6. [x] Synthetische End-to-End-, Fehler-, Migrations- und UI-Tests ausführen.
7. [x] Bedienung/Grenzen dokumentieren, eigene Änderungen prüfen, committen/pushen.

Die Paketgrenzen dienen der nachvollziehbaren Integration, nicht der Ausgabe
unfertiger Diagnosefunktionen als produktive Pipeline. Jede Teilumsetzung muss
ihre tatsächlichen Grenzen offen ausweisen.

## Prüfplan

Gezielt zuerst Domain-/Diensttests, danach Worker- und Qt-Tests. Nachweise:
Projektgrenzen, Undo/Archiv/Neustart, drei/fünf/eigene Profile, proportionale
Framegrößen, 128 → 115, interne Pixel-High-Abhängigkeit, 16 → 8/10/12/14,
FPS-/Dauertrennung, echte Farbmodi mit falschen/fehlenden Masken, Originalhashes,
gezielte Invalidierung, Abbruch/Fehler ohne Veröffentlichung, sichere Imports
und nicht ausgeführter Fremdcode beim bloßen Öffnen.

Abschließend Studio-Suite, bestehende PyGameTools-Prüfungen soweit ausführbar,
Stil, Abhängigkeiten und Standardcheck. Bekannte Ausgangsbefunde separat:
fehlendes Godot, geerbte Stilbefunde und drei Toolsuite-Fehler außerhalb dieser
Aufgabe. Nicht ausgeführte Prüfungen ausdrücklich benennen.

## Wiederherstellung und Grenzen

Schemaänderungen verwenden bestehende Katalogsicherungen und Transaktionen.
Originale werden nicht verschoben, überschrieben oder verlinkt. Job-Arbeitsräume
bleiben zur Diagnose bestehen; keine fremden Dateien bereinigen. Keine automatischen
Asset-Neugenerierungen, keine Godot-Grafikmenü-Neuentwicklung, keine Freigabe
von Bildern durch technische Tests. Persönliche Abnahme bleibt separat.

## Ergebnisse und offene Befunde

- Datenmodell: fünf idempotente Standardprofile, zusätzliche stabile Profilkeys,
  Deaktivierung und NPC-Preset; Anforderungen/Formulare/Scanner nutzen die
  Projektauflösung. Pipelinebesitz nur im vorhandenen globalen Rahmen.
- Rezepte und Zuweisungen liegen getrennt von Projektkanten; explizites Asset
  vor Typ/Fähigkeit vor Standard, gleichrangige Treffer sind Konflikte.
  Ungültig gewordene lokale Abweichungen blockieren die Ausführung, nicht das
  Öffnen des gesamten Projekts.
- Erste echte PNG-Läufe und Cacheprüfung: 7 Tests erfolgreich; zusätzlich
  5 Modell-/Migrationsprüfungen und 4 neue Canvas-Editor-Tests erfolgreich.
  54 bestehende Domain-/Speichertests und 6 Asset-Menü-Tests erfolgreich.
- Der Nutzer hat parallele Teilagenten ausdrücklich freigegeben. Getrennte
  Schreibbereiche: Austausch/Erweiterungssicherheit, Bildverarbeitung/Runner
  sowie ergänzende Profil-/Zuweisungs-/Ausführungsdialoge. Hauptintegration und
  Abschlussprüfung bleiben im Hauptarbeitsstrang.
- Bildverarbeitung einschließlich Qt: 144 Tests im Teilpaket erfolgreich;
  zusätzlich 48 unveränderte Resolution-/CLI-Prüfungen erfolgreich.
- Import-/Pluginpaket: 88 Tests erfolgreich; Editor: 16 Tests erfolgreich.
  Der erste Gesamtprobelauf hatte 457 erfolgreiche Tests und zwei Befunde
  (Werkzeugänderung während eingefrorenem Auftrag und ungeeignete Farbfixture).
  Die Abschlussregression läuft nach Stabilisierung aller Werkzeugdateien.
- Abschlussregression nach den letzten Integrationskorrekturen: **581 Tests
  bestanden** (153,12 s). Keine Tests übersprungen, keine fehlgeschlagen.
- Zusätzlich: **123 PyGameTools-Tests bestanden** (26,32 s) sowie **48 bestehende
  Resolution-/CLI-Tests bestanden** (18,92 s). `.venv/bin/python -m pip check`
  meldet keine defekten Abhängigkeiten. Studio-Code, Tests und Beispielerweiterung
  haben keine Stilbefunde; `git diff --check` für das Änderungspaket ist sauber.
- Offscreen-Qt-Dialog als Screenshot geöffnet und visuell geprüft; die persönliche
  interaktive Desktop-/Wayland-Sichtabnahme des Nutzers ist **nicht ausgeführt**.
  Godot-Import und Godot-Integration sind **nicht ausgeführt**, da die Engine in
  dieser Sitzung fehlt.
- Standardcheck `.venv/bin/python tools/control.py check`: **258 bestanden,
  37 übersprungen, 3 fehlgeschlagen**. Unveränderte externe Befunde:
  `window/size/resizable=true` fehlt im bestehenden Godot-Projekt; vorhandene
  Game-Decision-Dateien fehlen, dadurch scheitern Struktur- und Linkprüfung
  (13 bestehende Verweise). Außerdem 1907 geerbte Stilbefunde außerhalb des
  Studio-Pakets. Keine ungefragte Reparatur dieser fremden Arbeitsbereiche.
- Letzte Integration: fehlende Python-Schritte behalten deklarative lokale
  Parameterfreigaben und bleiben blockierte Entwürfe. Legacy-Pfeile sind nur
  visuell; Import-Undo archiviert die neue Karte. Eigene Pixelprofile nutzen
  in der Vorschau das eingefrorene Verfahren statt eines Namenspräfixes.
  Ausgeschaltete Zielprofile werden auch im Einzelassetdialog ausgeschlossen.
- Die Bedienung, acht Sichtprüfpunkte und konkreten Grenzen stehen in
  [Projektpipelines](../asset-studio/PIPELINES.md). Offen bleibt die persönliche
  Abnahme, nicht eine simulierte Bilderzeugung. Das fokussierte Paket ist als
  `2286d2f` (`✨ Add project-local canvas image pipelines`) nach `main` gepusht.
  Bereits vorhandene fremde Game-, Control-, README- und Asset-Änderungen bleiben
  unverändert und wurden nicht in diesen Commit aufgenommen.

## Wiederholbare Abschlussprüfungen

In der vorbereiteten Projekt-`.venv` (für Qt-Headless mit `QT_QPA_PLATFORM=offscreen`;
in dieser Docker-Sitzung wurden fehlende Qt-Systembibliotheken nur flüchtig ergänzt):

```sh
.venv/bin/python -m pytest tools/AssetManager/tests -q
.venv/bin/python -m pytest tools/AssetManager/PyGameTools/.tests -q
.venv/bin/python -m pytest tools/AssetManager/PyGameTools/Pipline/2-SpritesheetResolution-Pipline/tests/test_pipeline.py tools/AssetManager/PyGameTools/Pipline/2-SpritesheetResolution-Pipline/tests/test_cli_modes.py -q
.venv/bin/python -m pip check
.venv/bin/python tools/control.py check
```

Keine Produktionsbilder oder vorhandenen Originale wurden neu erzeugt. Alle
Bildnachweise verwenden kleine synthetische Fixtures in temporären Verzeichnissen.
