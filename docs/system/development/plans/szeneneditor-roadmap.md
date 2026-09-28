# Szeneneditor: nachgelagerte Roadmap

**Stillgelegt am 28.09.2026 auf Benutzerwunsch.** Die SE-Roadmap bleibt
historisch erhalten; ihre früheren Startbedingungen sind kein aktueller
Auftrag. Zuerst gilt die [Skriptplattform-Korrektur](asset-studio-skriptplattform-korrektur.md).
Eine spätere Szenenfunktion wird daraus nicht automatisch neu beauftragt.

[Zur Asset-Studio-Übersicht](../asset-studio/index.md) ·
[Zu den Arbeitsplänen](index.md)

## Zweck und Gesamtbild

Das Asset Studio soll später einen auf EtherFoods 2D-Arbeitsablauf zugeschnittenen
Szeneneditor erhalten: Räume öffnen, Boden und Wände malen, Figuren und Objekte
platzieren, Ereignisse zuweisen und die Szene in Godot testen. Projekt-Canvas und
Spielbrett sind unterschiedliche Ansichten derselben verwalteten Inhalte.
Godot bleibt die Laufzeit; eine eigene universelle Engine ist nicht das Ziel.

**Stand 2026-09-27: ausschließlich Planung, keine Editor-Implementierung.**
Die neue Kennung `SE` hält diese Roadmap von `T001–T048` getrennt. Ein Hauptissue,
vier Phasen und zwölf Aufgaben werden mit echten Unterissues, Voraussetzungen
und vier Meilensteinen vorbereitet. Spätere technische Details werden nach dem
Architekturprototyp konkretisiert; es gibt noch keine belastbare Terminzusage.

## Ausgangslage und Startfreigabe

Die [Asset-Studio-Roadmap](asset-studio-github-issues.md) umfasst **48 Aufgaben
insgesamt**, nicht 48 zusätzliche offene Aufgaben. Im GitHub-Abgleich vom
2026-09-27 sind T001–T012 geschlossen und T013–T048 noch offen. Offene Issues
belegen nicht automatisch fehlenden Code: T017/T018 sind technisch bearbeitet,
ihre Bedienabnahme steht noch aus. Dieser Plan schließt keine Bestandsissues.

Vor **jeglicher SE-Umsetzung**, auch SE001, müssen folgende Punkte vorliegen:

- [ ] T001–T048 sind umgesetzt, geprüft und nachvollziehbar abgenommen; verbleibende
  Befunde sind ausdrücklich entschieden, nicht still übersprungen.
- [ ] [T048 / #55](https://github.com/Blobbite/EtherFood/issues/55) enthält den
  Pilot- und Abschlussbericht mit Sicherung, Wiederherstellung und Godot-Nachweisen.
- [ ] Der Benutzer hat den Asset-Studio-Abschluss und den Start von SE-A bestätigt.

Das neue Hauptissue, SE-A und SE001 werden technisch durch T048 blockiert.
Ein geschlossenes GitHub-Issue allein ersetzt die menschliche Startfreigabe nicht.
Zwischen den SE-Phasen gibt es erneut ein Briefing mit Testbericht und Freigabe.
Ein unerfüllter Pflichtpunkt stoppt den Übergang; bei Architekturproblemen in
SE-A wird vor zusätzlicher Umsetzung neu entschieden.

## Umfang, Grenzen und Wiederverwendung

| Bereits zuständiger Bestand | Was der Szeneneditor später ergänzt |
| --- | --- |
| T013–T016: Assets, Quellen, Anforderungen | Typdefinitionen und konkrete Platzierungen, keine zweite Asset-Datenbank |
| T017/T018: Aufträge, Buildplan, Cache | kontrollierte Szenenprüfungen über bestehende Dienste |
| T025–T029: Timing, Varianten, statische Pakete | Verwendung geprüfter Varianten und Texturen im Raum |
| T033–T037: Kandidaten, Export, Testbereitstellung | Szenenkomposition auf dem vorhandenen Export-/Loadervertrag |
| T038–T040: Freigabe, Übernahme, Aufräumen | szenenspezifische Prüfbindung, keine zweite Freigabe-Pipeline |
| T044/T047/T048: Wiederherstellung, Betrieb, Pilot | Szenendaten in Sicherung, Control-Diagnose und Abschlussprüfung einbeziehen |

Feste Leitplanken für alle SE-Issues:

- **Asset → Typdefinition → Instanz:** Bilddaten und Animationen werden referenziert,
  nicht pro Lampe oder Figur kopiert. Assetrevision, Grafikstufe, Frames und FPS
  bleiben unterscheidbar. Ein Variantenwechsel darf keine Richtung vertauschen.
- **Ein maßgeblicher Datenbestand:** stabile IDs für Raum, Ebene, Instanz und
  Ereignis; Canvas-Layout und Raumkoordinaten sind getrennt. Beide Ansichten
  bearbeiten dieselben Entitäten über gemeinsame Befehle und Revisionen.
- **Einfache Oberfläche, getrennte Daten:** zunächst die Arbeitsgruppen
  „Boden/Wände“ und „Objekte/Ereignisse“. Grafikreihenfolge, Kollision, Licht und
  Ereignisdaten sind intern nicht auf zwei vermischte Ebenen beschränkt.
- **Kein zweiter Level-Renderer aus Karten:** Bodenfelder werden nicht als
  Tausende Canvas-Karten gespeichert. Der Canvas zeigt Räume, wichtige Objekte
  und Ereignisbezüge; das Spielbrett lädt sichtbare Bereiche bedarfsgerecht.
- **Rückgängig von Anfang an:** Szenenbefehle, atomare Speicherstände und einfache
  Undo/Redo-Tests gehören bereits in SE002/SE003, nicht erst in die Endprüfung.
- **Klare Schreibzuständigkeit:** generierte Godot-Ergebnisse und manuell
  gepflegte Skripte bleiben getrennt. Kein versprochener bidirektionaler Import
  beliebiger `.tscn`-Änderungen; Konflikte werden gemeldet statt überschrieben.
- **Sichere Vorschau:** Testgrafiken unter `game/test_assets/`, Szenen und Hilfen
  unter `game/test_scenes/`; keine automatische Übernahme nach `game/assets/`.
  Fehlende Engine, Quelle oder Freigabe wird blockiert, nicht als Erfolg verbucht.

Nicht-Ziele: eigene Render-/Physik-Engine, 3D, Multiplayer, Cloud-Zusammenarbeit,
ein universeller visueller Skriptbaukasten und vollständiger Godot-Ersatz.
Native Qt/Godot-Einbettung wird nicht vorausgesetzt; SE001 prüft, welche
Editoroberfläche und Prozessanbindung sich tatsächlich zuverlässig betreiben lässt.
Ein optionaler Skript-Einstieg verwendet eigene, bewusst aktivierte Erweiterungen;
importierte Projekte führen keinen fremden Code automatisch aus.

„Flur 1“, Tür und Lampe sind unten ausschließlich synthetische Testbeispiele,
keine Ergänzungen von Spielkanon oder Gamedesign.

## Phasen und Kontrollinstanzen

### 🧭 SE-A · Architektur und durchgehender Prototyp

Voraussetzungen: T048.

Aufgaben: SE001, SE002, SE003. Zuerst den Start vom Studio über einen kleinen Raum
bis zur echten Godot-Testvorschau beweisen. Architekturentscheidung, versionierter
Datenvertrag und minimaler Rückgängig-/Speicherweg sind nachprüfbare Ergebnisse.

Abnahme: „Flur 1“ im Projekt öffnen, eine referenzierte Testlampe platzieren,
speichern, neu öffnen und in Godot sehen. Eine Verschiebung lässt sich rückgängig
machen. Fehlende Godot-Installation wird verständlich gemeldet. Danach entscheidet
der Benutzer über die Oberfläche und gibt erst dann SE-B frei.

### 🎨 SE-B · Spielbrett, Figuren und Objektplatzierung

Voraussetzungen: SE-A.

Aufgaben: SE004, SE005, SE006. Boden/Wände malen und füllen, zugewiesene Assets in
der Seitenpalette finden, daraus wiederverwendbare Typen und Instanzen anlegen.

Abnahme: kleiner Testraum mit Boden, Wand, zwei Lampen und einer Figur; Malzug
rückgängig machen, Instanzen unabhängig verschieben, Kollision und Anker prüfen.
Speichern/Neuladen bleibt verlustfrei. Erst nach Bericht folgt SE-C.

### ⚡ SE-C · Ereignisse, Canvas-Verknüpfung und Spieltest

Voraussetzungen: SE-B.

Aufgaben: SE007, SE008, SE009. Ein überschaubarer Satz typisierter Ereignisse
verbindet das Spielbrett mit Projektübersicht und testbarer Laufzeit.

Abnahme: Testfigur betritt eine Zone, eine zugeordnete Tür reagiert. Dasselbe
Ereignis aus Canvas und Spielbrett bearbeiten, keine Dublette erzeugen. Neustart
setzt den Testzustand zurück; defekte Zielbezüge zeigen konkrete Fehler.
Danach bewusste Freigabe für SE-D.

### 🛡️ SE-D · Wiederherstellung, Größenprüfung und Pilotabnahme

Voraussetzungen: SE-C.

Aufgaben: SE010, SE011, SE012. Den durchgehenden Arbeitsablauf mit großen
synthetischen Beständen, Abbrüchen und bestehender Freigabe-Pipeline absichern.

Abnahme: Projekt aus Sicherung öffnen, Szenenänderung nachvollziehbar prüfen,
Godot-Test über Control starten, alte freigegebene Fassung unverändert erhalten.
Messwerte, Grenzen und offene Befunde dokumentieren. Abschluss erst nach
automatisierten Nachweisen und menschlichem Pilotbericht.

## Vorbereitete Aufgaben

### 🧭 SE001 · Editoroberfläche und Integrationsweg erproben

Phase: SE-A. Voraussetzungen: T048. Bereich: area:core.

Ziel: Einen nachgewiesenen, wartbaren Weg zwischen Studio und Godot auswählen.

Umfang: Nach Startfreigabe reale Studio-/Godot-Version und T035–T037 prüfen.
Godot-Haupteditor-Erweiterung und getrennte Studio-/Godot-Oberfläche anhand eines
kleinen Versuchs vergleichen; native Fenstereinbettung nur bei belastbarem
Nachweis wählen. Start, Szenen-ID-Übergabe, Fokus, Rückkehr und Fehlerkanal prüfen.
Eine technische Entscheidung mit Alternativen, Aufwandstreibern, Prozessgrenzen
und messbaren Größen-/Reaktionszielen für SE011 festhalten.

Tests und Abnahme:

- [ ] Ein Versuch öffnet aus dem Studio genau die ausgewählte synthetische Szene;
  Rückkehr und erneuter Start erzeugen keinen verwaisten Prozess.
- [ ] Fehlende Engine, Pfade mit Leerzeichen und Prozessabbruch werden geprüft.
- [ ] Benutzer bestätigt die demonstrierte Oberfläche; Entscheidung begründet
  Godot als Laufzeit und benennt explizit nicht unterstützte Funktionen.

Nicht-Ziele: produktiver Maleditor, eigene Engine oder ungeprüfte Qt-Einbettung.

### 🧱 SE002 · Raumdaten, Ebenen und gemeinsame Änderungsbefehle modellieren

Phase: SE-A. Voraussetzungen: SE001. Bereich: area:core.

Ziel: Eine eindeutige, versionierte Grundlage für Raum und Projektbezüge schaffen.

Umfang: Room unter bestehendem Projekt-/Akt-/Kapitelkontext, Layer, TypeReference,
Instance und spätere EventReference mit stabilen IDs modellieren. Position,
Maßeinheiten, Rasterursprung, Z-Reihenfolge und getrennte Kollisions-/Lichtdaten
festlegen. Befehle, Revisionskonflikte, Speichern und Undo/Redo zentral halten;
Canvas-Positionen bleiben reine Ansichtsdaten. Bestehende Projekte bleiben lesbar.

Tests und Abnahme:

- [ ] Umbenennen/Umordnen ändert keine IDs oder Raumpositionen; zwei Lampen
  verwenden dieselbe Typreferenz mit unabhängigen Instanzdaten.
- [ ] Speichern/Neuladen und Undo/Redo sind verlustfrei; falsche Versionen,
  ungültige Bezüge und konkurrierende Änderungen werden verständlich abgelehnt.
- [ ] Ein Projekt ohne Szeneneditor-Daten wird ohne erzwungene Inhaltsänderung geöffnet.

Nicht-Ziele: neue Asset-Datenbank, Tile-Karten im Projekt-Canvas, beliebiger `.tscn`-Import.

### ▶️ SE003 · Minimalen Raum bis zur Godot-Vorschau durchgängig umsetzen

Phase: SE-A. Voraussetzungen: SE002. Bereich: area:godot.

Ziel: Den gewählten Integrationsweg vor Ausbau der Oberfläche praktisch beweisen.

Umfang: Synthetischen „Flur 1“ mit einem Bodentyp und einer platzierbaren Lampe
öffnen, verschieben, speichern und über bestehende T035–T037-Dienste testen.
Einen minimalen szenenspezifischen Kompositionsadapter ergänzen, keinen zweiten
Assetexporter. Revisionen und Testbericht an die konkrete Szenenfassung binden.

Tests und Abnahme:

- [ ] Gespeicherte Platzierung erscheint an derselben Stelle in Godot; Undo/Redo
  und Neustart bewahren Referenzen, Anker und Raumkoordinaten.
- [ ] Wiederholtes Bereitstellen überschreibt keine fremden Dateien; ein fehlendes
  Asset oder Godot erzeugt einen Blocker und niemals einen Erfolgseintrag.
- [ ] Testdateien bleiben in den erlaubten Testwurzeln; Pflichtdemo aus SE-A ist abgenommen.

Nicht-Ziele: produktive Freigabe, umfassender Pinsel oder Ereignisbaukasten.

### 🎨 SE004 · Boden und Wände mit Pinsel, Füllen und Radierer bearbeiten

Phase: SE-B. Voraussetzungen: SE003, SE-A. Bereich: area:ui.

Ziel: Einen begrenzten 2D-Raum direkt und nachvollziehbar bemalen können.

Umfang: Arbeitsgruppe Boden/Wände mit Ebenenwahl, Sichtbarkeit, Sperre, Raster,
Pinsel, Füllwerkzeug und Radierer. Wanddarstellung und Kollisionsbelegung getrennt
halten. Ein Malzug ist ein rückgängig machbarer Befehl. Kartenränder, Zoom/Pan
und Eingabekoordinaten sind vom Projekt-Canvas unabhängig.

Tests und Abnahme:

- [ ] Gleicher Klick trifft bei verschiedenen Zoomstufen dasselbe Weltfeld;
  Schwenken verschiebt keine bereits gemalten Inhalte.
- [ ] Füllen bleibt in verbundenem Bereich und Raumgrenze; gesperrte Ebenen
  ändern sich nicht. Ein Undo entfernt genau einen Malzug, Redo stellt ihn wieder her.
- [ ] Speichern/Neuladen bewahrt Raster, Ebenenreihenfolge und Kollisionsbelegung.

Nicht-Ziele: unendliche Welt, Autotiling-Komplettsystem oder Geländegenerator.

### 🧍 SE005 · Figuren- und Objekttypen aus zugewiesenen Assets bilden

Phase: SE-B. Voraussetzungen: SE003, SE-A. Bereich: area:core.

Ziel: Geprüfte Assetlieferungen als wiederverwendbare Figuren und Objekte nutzen.

Umfang: Typdefinitionen mit festen Asset-/Exportrevisionen, Anker, Größe und
zulässigen Animationszuständen; statische Lampe benötigt keine Laufanimation.
Palette rechts zeigt lokale und gemeinsam verwendete Assets mit Herkunft und
Verfügbarkeit. Stand/Walk/Slowwalk, Richtungen, Frames, FPS und Grafikstufen
aus vorhandenen Verträgen übernehmen, keine Varianten still erfinden.

Tests und Abnahme:

- [ ] Zwei Instanzen teilen einen Typ, aber keine Position; Profil-/Assetwechsel
  ist ausdrücklich und zeigt betroffene Szenen vor Übernahme.
- [ ] Acht-Richtungs-Figur und Figur mit weniger Richtungen funktionieren gemäß
  ihrem Vertrag; SW wird nicht als SO oder Walk als Slowwalk ersetzt.
- [ ] Fehlende/archivierte Revisionen sind als konkrete Blocker erkennbar;
  derselbe Typ bleibt nach Umbenennen des Assets gültig.

Nicht-Ziele: Animationserzeugung, neue Farb-/Maskenpipeline, automatische Neufreigabe.

### 🖱️ SE006 · Instanzen platzieren, auswählen und räumlich bearbeiten

Phase: SE-B. Voraussetzungen: SE004, SE005. Bereich: area:ui.

Ziel: Figuren, Lampen und weitere zugewiesene Objekte intuitiv im Raum bearbeiten.

Umfang: Drag-and-drop und Kontextplatzierung aus der Palette, Auswahl,
Mehrfachauswahl, Verschieben, Duplizieren, Entfernen und Eigenschafteninspektor.
Rasterfang, Anker, Z-Reihenfolge, unterstützte Transformationen und zugehörige
Kollisions-/Lichtparameter verständlich zeigen; Nichtunterstütztes deaktivieren.

Tests und Abnahme:

- [ ] Platzierung und Auswahl stimmen bei Zoom/Pan; Markieren allein verändert
  keine Position. Mehrfachverschiebung lässt sich gemeinsam rückgängig machen.
- [ ] Duplizieren erzeugt neue Instanz-IDs, nicht neue Assetbytes; Löschen einer
  Instanz zerstört weder Typ noch Schwesterinstanzen.
- [ ] Figur, Wandkollision und Lampenparameter stimmen in Godot mit dem Editor
  überein; SE-B-Demo einschließlich Speichern/Neuladen ist abgenommen.

Nicht-Ziele: Mesh-/3D-Editor, Physikengine oder stille Änderung der Quellgrafiken.

### ⚡ SE007 · Typisierte Ereigniszonen und begrenzte Aktionen ergänzen

Phase: SE-C. Voraussetzungen: SE006, SE-B. Bereich: area:core.

Ziel: Einfache Interaktionen ohne freie Skripte über nachvollziehbare Blöcke definieren.

Umfang: Zunächst „Bereich betreten“ als Auslöser und „Türzustand ändern“ sowie
„Testtext anzeigen“ als Aktionen. Stabile Ziel-IDs, Parameterprüfung, einmalig/
wiederholt, Zustandsrücksetzung und begrenzte Ereignisausführung definieren.
Erweiterungen werden registriert und bewusst aktiviert, nicht aus Importen ausgeführt.

Tests und Abnahme:

- [ ] Einmaliger Trigger löst einmal aus; wiederholter Trigger erst nach definiertem
  erneutem Betreten. Testneustart setzt den Zustand reproduzierbar zurück.
- [ ] Gelöschtes Ziel, unbekannter Block, ungültige Parameter oder unzulässiger
  Ereigniszyklus verhindern die Ausführung mit konkreter Fundstelle.
- [ ] Szenenimport startet weder Aktion noch Skript; die synthetische Tür reagiert
  nur auf die tatsächlich zugewiesene Zone.

Nicht-Ziele: universelle visuelle Programmiersprache, Quest-/Dialogsystem oder neuer Kanon.

### 🔗 SE008 · Szenen und Ereignisse gemeinsam in Canvas und Spielbrett öffnen

Phase: SE-C. Voraussetzungen: SE007. Bereich: area:ui.

Ziel: Planung und Szenenbearbeitung ohne doppelte Datensätze verbinden.

Umfang: Raumkarte öffnet das Spielbrett. Ereignisse und ausdrücklich relevante
Instanzen erscheinen als verknüpfte Canvas-Inhalte; Bodenfelder bleiben intern.
Auswahl, Name, Zuordnung und Fehlermeldungen verweisen in beiden Ansichten auf
dieselbe ID. Die vorhandenen Baum-/Verwendungsregeln und Notiz-/Dokumenttrennung
weiterverwenden; Canvas-Layout ist keine Weltkoordinate.

Tests und Abnahme:

- [ ] Ereignis im Spielbrett anlegen, im Canvas öffnen/umbenennen und zurückkehren:
  genau eine Entität, derselbe Inhalt, unveränderte Raumposition.
- [ ] Canvas-Karte verschieben/zoomen verändert das Spielbrett nicht; Umordnen
  innerhalb zulässiger Hierarchie bewahrt Bezüge.
- [ ] Löschen oder veralteter Bearbeitungsstand erzeugt einen sichtbaren Konflikt
  statt einer Dublette; Notizen bleiben im Notiz-Dashboard.

Nicht-Ziele: jede Kachel als Karte, zweite Aufgabenverwaltung oder automatische Kanonänderung.

### 🧪 SE009 · Spielvorschau mit Ereignisdiagnose und sauberem Neustart ausbauen

Phase: SE-C. Voraussetzungen: SE007, SE008. Bereich: area:godot.

Ziel: Die aktuelle Szene spielen und Fehler direkt zur bearbeitbaren Quelle verfolgen.

Umfang: Teststart/Stop/Neustart mit eingefrorener Szenen- und Assetrevision,
sichtbaren Triggern/Kollisionen und Protokoll mit Szene/Instanz/Ereignis-ID.
Änderungen während der Vorschau markieren den Test als veraltet. Kontrollierter
Rücksprung zur Fundstelle; Abbruch und fehlende Engine bleiben ehrliche Ergebnisse.

Tests und Abnahme:

- [ ] Raum → Zone → Tür kann gespielt und im Protokoll nachverfolgt werden;
  Fehlerlink öffnet genau den zugehörigen Editorinhalt.
- [ ] Wiederholter Start/Stop hinterlässt keine Prozesse oder veränderten Quellen;
  temporärer Spielzustand wird nicht unbemerkt in den Entwurf gespeichert.
- [ ] Eine Entwurfsänderung entwertet den aktuellen Testnachweis; SE-C-Demo ist
  mit konkreter Szenenrevision abgenommen, nicht automatisch für Runtime freigegeben.

Nicht-Ziele: neue Auftragsverwaltung oder Übernahme des Tests in produktive Szenen.

### 💾 SE010 · Szenenänderungen, Sicherung und Wiederherstellung absichern

Phase: SE-D. Voraussetzungen: SE009, SE-C. Bereich: area:core.

Ziel: Die schon vorhandenen Befehls-/Speichergrundlagen auch unter Abbruch absichern.

Umfang: Komplexe Undo/Redo-Folgen über beide Ansichten, Speichertransaktionen,
Wiederanlauf und Versionsmigration für Szenendaten prüfen. Bestehende T044-Sicherung
um Szenenbezüge erweitern, keinen parallelen Sicherungsdienst anlegen. Grenzen
von Sitzungshistorie und dauerhaft gespeicherten Revisionen verständlich dokumentieren.

Tests und Abnahme:

- [ ] Malen, Platzieren, Verknüpfen und Löschen rückwärts/vorwärts ergibt dieselben
  Inhalte; Undo nach Vorschau verwechselt Testzustand nicht mit Entwurfsdaten.
- [ ] Abbruch während Speichern lässt einen vollständigen alten oder neuen Stand;
  eine verifizierte Sicherung stellt Szene und ihre Assetreferenzen wieder her.
- [ ] Unbekannte Schema-Version und Revisionskonflikt werden ohne Datenverlust
  abgelehnt; Migration ist wiederholbar und behält einen Wiederherstellungspfad.

Nicht-Ziele: pauschale Projektmigration oder Löschen von alten Originalbeständen.

### 📏 SE011 · Große Räume und Assetbestände mit festen Budgets prüfen

Phase: SE-D. Voraussetzungen: SE009, SE010. Bereich: area:quality.

Ziel: Größenlimits mit Messwerten belegen, bevor ein großer Bestand übernommen wird.

Umfang: SE001-Budgets auf dokumentierter Referenzumgebung prüfen. Mindestens
1.000 synthetische Assetdefinitionen, 100 Räume und ein Raum mit 100.000 Zellen
sowie 2.000 Instanzen als Lastfälle; nicht alle Grafikvarianten gleichzeitig laden.
Sichtbereichsabhängiges Laden, begrenzte Vorschaubild-Caches, Abschnittsladen und
ressourcenschonende Ereignisanzeige messen. Begrenzungen statt unbelegter Zusagen.

Tests und Abnahme:

- [ ] Öffnungszeit, Eingabelatenz und Spitzen-RAM sind mit Bestand, Hardware und
  Messbefehl dokumentiert und erfüllen die vorher vereinbarten Budgets.
- [ ] Inaktive Räume/Varianten werden nicht vollständig geladen; wiederholter
  Raumwechsel zeigt keinen fortlaufenden Speicheranstieg.
- [ ] Lasttest bewahrt Auswahlpositionen, Bezüge und Undo/Redo; Überschreiten
  eines sicheren Limits wird verständlich behandelt, nicht still als Erfolg gewertet.

Nicht-Ziele: unbegrenzte Welten, garantierte Leistung auf jeder Hardware oder eigene Engine.

### 🏁 SE012 · Control-Integration und vollständige Szenen-Pilotabnahme abschließen

Phase: SE-D. Voraussetzungen: SE011. Bereich: area:quality.

Ziel: Den gesamten Szenenworkflow bedienbar, überprüfbar und rückbaubar übergeben.

Umfang: In vorhandene Control-Start-/Diagnose-/Testwege integrieren, installierte
Abhängigkeiten ehrlich prüfen und Bedienhilfe ergänzen. Synthetischen Pilot über
Raumaufbau, Figur, Ereignis, Vorschau, Wiederherstellung und bestehenden
T035–T040-Export-/Freigabeweg führen. Produktive Übernahme nur separat autorisiert;
der Test selbst liefert keine künstlerische Freigabe. Bekannte Grenzen festhalten.

Tests und Abnahme:

- [ ] Der dokumentierte Control-Weg startet und prüft Editor und Godot; fehlende
  Voraussetzungen liefern konkrete Maßnahmen statt eines grünen Scheinstatus.
- [ ] Wiederholter Export, Fremddateikonflikt, blockierte Freigabe und Rollback
  verwenden den Bestandsvertrag; manuelle Skripte und Originalassets bleiben erhalten.
- [ ] Automatisierte Prüfungen und kompletter menschlicher Pilotbericht liegen
  vor; Paketbericht nennt Versionen, Messwerte, offene Befunde und Startbefehle.

Nicht-Ziele: allgemeine Spielveröffentlichung oder ungeprüfte Migration aller Assets.

## Bearbeitungs- und Abnahmeregeln

Jedes SE-Issue enthält seine Phase, echte Voraussetzungen, Umfang, Tests,
Nicht-Ziele und Rückbauschutz. Phasenabschluss heißt: zugehörige Aufgaben technisch
geprüft **und** zugehöriges Briefing abgenommen. Parent-Issues oder Tests werden
nicht allein aufgrund einer Codeänderung geschlossen. Das Label `status:planned`
bleibt bis zum ausdrücklich freigegebenen Arbeitsbeginn bestehen.

Pro späterem Umsetzungspaket: Bestand prüfen, kleinen technischen Arbeitsplan
pflegen, umsetzen, schnellste passende Tests ausführen, Ergebnis dokumentieren,
englischen Commit mit vorangestelltem Emoji erstellen und pushen. Danach die
konkrete Bediencheckliste und verbleibende Grenzen nennen. Weitere Phasen nicht
automatisch starten; offen gemeldete Befunde zuerst einordnen.

## Planungsschritte und Fortschritt

- [x] Bestehende 48 Aufgaben, GitHub-Stand und Überschneidungen prüfen.
- [x] Vier Folgephasen, zwölf Aufgaben, Grenzen und Teststopps formulieren.
- [x] IDs, lokale Links und zyklenfreie Voraussetzungen prüfen.
- [x] GitHub-Meilensteine, Hauptissue und Phasen-/Aufgabenissues veröffentlichen.
- [x] Inhalte, Hierarchie und Abhängigkeiten über erneuten Abruf verifizieren.
- [x] Eigene Dokumentation für Commit/Push und aktuelles T017/T018-Briefing vorbereiten.

## Erkenntnisse und Entscheidungen

- Für diese Vorbereitung wird „48 Issues“ als bestehender Gesamtplan T001–T048
  verstanden. Es werden keine 48 neuen Szeneneditor-Aufgaben und keine doppelten
  Godot-Exportissues angelegt; weitere Umsetzungspakete folgen erst nach Briefing.
- Der aktuelle Arbeitsbaum enthält bereits andere Änderungen. Dieses Paket
  nimmt ausschließlich seine eigene Planungsdokumentation in den Commit auf.
- Die Studio-Oberfläche ist kein belegter Level-Renderer. SE-A ist deshalb eine
  echte Architektur- und Bedienentscheidung; B–D sind davon abhängige Zielpakete.
- Aktuelle Detailbefunde werden beim nächsten T017/T018-Briefing eingeordnet.
  Dieser Plan ändert weder Notizen noch Pipeline- oder Godot-Verhalten.

## Prüfungen

Die lokale Planprüfung ist bestanden: 17 Issue-Definitionen, vier Phasen,
zwölf Aufgaben mit 36 konkreten Abnahmepunkten, 24 zyklenfreie Voraussetzungen
und 38 vorhandene lokale Links in Plan und Asset-Studio-Index. Die Zyklusprüfung
berücksichtigt auch, dass Phasen erst nach ihren Unteraufgaben abschließen können.
Die Bestandsprüfung `python3 tools/AssetManager/works/EtherFood_Codex_Aufgabenplan/pruefung/check_plan.py --json`
ist ebenfalls bestanden: 48 Aufgaben, 36 Anforderungen, 955 Links, 81 Hashes.
Der anschließende vollständige GitHub-Abgleich ist bestanden:

- 17 offene Issues mit exakt den vorbereiteten Titeln, Texten und Labels;
- 16 native Eltern-Kind-Beziehungen mit richtiger Reihenfolge und Elternzuordnung;
- 24 native Blocker in der richtigen Richtung, einschließlich T048 als Startgrenze;
- vier offene Meilensteine mit jeweils einer Phase und drei Aufgaben, ohne Terminzusage;
- T017 / #24 und T018 / #25 bleiben offen; keine automatische Bedienabnahme.

`git diff --check` für die eigenen Dokumentationsdateien ist bestanden. Der
Commitumfang besteht ausschließlich aus diesem Plan und seinem Link im
Asset-Studio-Index. Anwendungstests und der vollständige Standardlauf sind für
die reine Planung nicht erneut ausgeführt; Szeneneditor-Tests existieren hier
als Abnahmeanforderungen, nicht als bereits bestandene Prüfungen.

## Wiederholbarkeit und Wiederherstellung

Stabile Kennungen `SE-ROADMAP`, `SE-A` bis `SE-D` und `SE001` bis `SE012`
verhindern doppelte Issues. Vor jedem Anlegen bestehende Issues einschließlich
geschlossener Einträge prüfen. IDs/Nummern nach dem Anlegen erneut abrufen;
Unterissues und Blocker in der richtigen Richtung verifizieren. Wiederaufnahme
ergänzt nur fehlende eigene Einträge; bei fremden Abweichungen erst klären.
Keine bestehenden Issues löschen, verschieben oder automatisch schließen.
Temporäre Veröffentlichungsdaten enthalten keine Zugangsdaten und bleiben
außerhalb des Repositorys. Rücknahme von veröffentlichten Planungen erfolgt
nach ausdrücklicher Entscheidung mit nachvollziehbarer Kennzeichnung.

## Ergebnis und Rückblick

Veröffentlicht: [🗺️ Hauptissue #60](https://github.com/Blobbite/EtherFood/issues/60),
vier Phasen, zwölf Aufgaben und vier Meilensteine. Die Verknüpfungen sind
vollständig angelegt und durch erneuten GitHub-Abruf nachgewiesen. Das
Planungspaket ist damit inhaltlich abgeschlossen; es enthält keine funktionale
Änderung am Studio. Die Umsetzung des Szeneneditors bleibt unabhängig vom
Planungsabschluss gesperrt. Bis dahin wird zuerst der bestehende
Asset-Studio-Ablauf weitergeführt.

| Phase | Phasenissue | Aufgabenissues | Meilenstein |
| --- | --- | --- | --- |
| 🧭 SE-A: Prototyp | [#61](https://github.com/Blobbite/EtherFood/issues/61) | [SE001 / #65](https://github.com/Blobbite/EtherFood/issues/65), [SE002 / #66](https://github.com/Blobbite/EtherFood/issues/66), [SE003 / #67](https://github.com/Blobbite/EtherFood/issues/67) | [SE-A](https://github.com/Blobbite/EtherFood/milestone/7) |
| 🎨 SE-B: Spielbrett | [#62](https://github.com/Blobbite/EtherFood/issues/62) | [SE004 / #68](https://github.com/Blobbite/EtherFood/issues/68), [SE005 / #69](https://github.com/Blobbite/EtherFood/issues/69), [SE006 / #70](https://github.com/Blobbite/EtherFood/issues/70) | [SE-B](https://github.com/Blobbite/EtherFood/milestone/8) |
| ⚡ SE-C: Ereignisse und Canvas | [#63](https://github.com/Blobbite/EtherFood/issues/63) | [SE007 / #71](https://github.com/Blobbite/EtherFood/issues/71), [SE008 / #72](https://github.com/Blobbite/EtherFood/issues/72), [SE009 / #73](https://github.com/Blobbite/EtherFood/issues/73) | [SE-C](https://github.com/Blobbite/EtherFood/milestone/9) |
| 🛡️ SE-D: Absicherung | [#64](https://github.com/Blobbite/EtherFood/issues/64) | [SE010 / #74](https://github.com/Blobbite/EtherFood/issues/74), [SE011 / #75](https://github.com/Blobbite/EtherFood/issues/75), [SE012 / #76](https://github.com/Blobbite/EtherFood/issues/76) | [SE-D](https://github.com/Blobbite/EtherFood/milestone/10) |

Aktuelle Kontrollinstanz:
[Paket 7 – sechs Tests für Notizen, T017 und T018](../asset-studio/SICHTPRUEFUNG_7.md).
Nach dessen Testbericht sind T019 (Masterreferenzen/Profilversionen) und T020
(Materialmasken/Quellbindung) die nächsten zusammenhängenden Kandidaten;
sie werden nicht in diesem Planungspaket umgesetzt.
