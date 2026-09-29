# Asset Studio: Pipeline-Dashboard und Posenlieferstand

## Zweck und Gesamtbild

Auftrag vom 28.09.2026: Das Projekt erhält ein festes, grau abgesetztes
Canvas-Element für Hell- und Dunkelmodus. Pipelines erscheinen als feste
Symbole und öffnen einen Arbeitsbereich, in dem Assets, Skripte und
Ausgabeziele über sichtbare Verbindungen zusammenarbeiten. Als durchgängiges
Beispiel entsteht eine GIF-Pipeline auf Grundlage von `PyImgGif.py`.

Posen definieren Namen, Richtungen, FPS und Anker. Quellen werden ausschließlich
unter Quellen / Revisionen gepflegt. Dort wird je Pose erkennbar, welche
Einzelbilder, Spritesheets, dazugehörigen Masken und Vorschauen vorliegen.
Die lesbare Asset-Ablage erhält `source/<Pose>`, `spritesheets/<Pose>`,
`masks/source/<Pose>`, `masks/spritesheets/<Pose>` sowie `previews/gif` und
`previews/video`.

## Ausgangslage

Der bestehende Dienst besitzt unveränderliche Quellenrevisionen, Maskenbindungen,
typisierte Rezeptverbindungen, einen geprüften Bild-Runner und transaktionale
Dateiprojektionen. Pipeline-Schritte liefern bisher PNG und Metadaten. Die
Oberfläche verwendet noch gewöhnliche Karten für Projekt und Pipeline sowie
zusätzliche Importknöpfe innerhalb der Posenkonfiguration.

Bei Beginn liegen fremde Änderungen an README, zwei bisherigen Plandokumenten
und zwei GUI-Testdateien vor. Diese bleiben erhalten. Der neue Auftrag ersetzt
die bisherigen Bedien- und Ablageentscheidungen nur im beschriebenen Umfang.

## Umfang und Nicht-Ziele

Der Umbau betrifft Studio, seine synthetischen Tests und technische Dokumentation.
Vorhandene Katalog-IDs, Revisionen, Skriptfreigaben, Originaldateien und historische
Builds bleiben erhalten. Keine Spielkanonänderung, produktive Assetfreigabe,
automatische Codefreigabe oder neue Abhängigkeit. Videoordner und Lieferstatus
werden vorbereitet; ein Videoencoder gehört nicht zum Auftrag.

## Schritte und Fortschritt

- [x] Dokumentation, Canvas, Quellenmodell und vorhandene Skripte untersuchen.
- [x] Feste Projekt-/Pipeline-Darstellung und Pipeline-Dashboard umsetzen.
- [x] Posenkonfiguration, zentralen Lieferstand und gespiegelte Asset-Ablage verbinden.
- [x] GIF-Skript als ausführbare Pipeline mit sichtbarem Asset und Ausgabeziel integrieren.
- [x] Gezielt prüfen, vollständige relevante Prüfungen ausführen und Bedienung dokumentieren.

## Entscheidungen

- Bestehenden Katalog und Runner erweitern. Verbindungslinien im Rezept bleiben
  echte Datenverbindungen; Asset-Zuweisungen werden sichtbar und ausdrücklich gespeichert.
- Einzelbildquellen und Spritesheets können für dieselbe Pose gleichzeitig
  vorhanden sein. Ihr Lieferstand wird getrennt von der Ausführbarkeit einer
  konkreten Pipeline dargestellt.
- GIF-Ausgaben werden im vorhandenen Worker erzeugt und vor der Veröffentlichung
  geprüft. Ergebnisse gehören weiterhin zum jeweiligen Asset.
- Verwaltete neue Ordner werden aus den Posen-Exportnamen abgeleitet. Änderungen
  an Bestandsdateien erfolgen ausschließlich über die vorhandenen Konflikt- und
  Transaktionsmechanismen.

## Erkenntnisse und Überraschungen

- Quellenrevisionen unterstützen bereits zusätzliche Einzelbilder einer animierten
  Pose; die bisherige Übersicht zeigt fehlende zusätzliche Einzelbilder nicht.
- Der vorhandene PNG-Vertrag ist auch Grundlage für nachfolgende Skripte. Eine
  GIF-Vorschau muss zusätzlich geprüft werden, ohne diese Verkettung aufzubrechen.
- Ein Asset kann ausdrücklich mehreren Pipelines zugewiesen sein. Der Start
  aus einem Dashboard wählt dessen Pipeline; die bestehende Rangfolge
  Asset-Zuweisung vor Typregel vor Projektstandard bleibt erhalten.
- Der Lieferstand prüft GIFs gegen die aktuellen Verarbeitungsparameter.
  Eine unveränderte Quelldatei allein genügt nach einer FPS-Änderung nicht.
- Die Container-Umgebung besaß anfangs nicht alle Qt-Laufzeitbibliotheken.
  Für die Offscreen-Prüfung wurden offizielle Debian-Pakete ausschließlich
  unter einem temporären Verzeichnis entpackt. Keine Repository-Abhängigkeit
  oder Binärdatei wurde ergänzt.

## Prüfungen

- Gezielte neue Integrations- und Bedienprüfungen ausgeführt: gespiegelte
  Posenordner, Quellen-/Maskenrevisionen, Umbenennen, Migration aus `Quellen`,
  Port-Verbindungen mit Mausereignissen, Speichern, Undo/Redo und Wiederöffnen.
  Projektgröße und Pipeline-Symbole wurden in Hell- und Dunkelmodus geprüft.
- Echte GIF-Ausführung mit acht synthetischen Frames, 7,5 FPS und deaktivierter
  Schleife: acht GIF-Frames und insgesamt 1070 ms geprüft. PNG-Raster und
  Originalhash bleiben erhalten; Cache-Wiederverwendung und beschädigte
  Veröffentlichungen werden erkannt. Nachfolgende Skripte erhalten weiterhin PNG.
- Nach der Korrektur von Aktualitätsstatus und Auswahlpriorität bestehen die
  17 zugehörigen Integrations-, Modell- und Bedienprüfungen. Zusätzlich bestehen
  23 Dashboard-Bedienprüfungen nach der Korrektur des Umhängens einer Asset-Kante:
  Ein anderes Asset ersetzt die vorherige Zuweisung; Undo/Redo stellt sie wieder
  her.
- Vollständiger Studio-Testlauf mit `python3 tools/control.py asset-manager check`:
  685 Tests bestanden; anschließend 171 Tests der bestehenden Bildwerkzeuge
  bestanden. Der Befehl endet erfolgreich mit Exitcode 0.
- `python3 tools/control.py check` ausgeführt: 284 bestanden, 37 übersprungen,
  drei bestehende Fehler außerhalb dieses Umbaus: fehlendes explizites
  `window/size/resizable=true` sowie fehlende
  `docs/game/decisions/index.md` und `ADR-0008-achtteiliger-spielablauf.md`.
  Godot 4 fehlt in der Umgebung, daher kein Engine-Import-/Integrationstest.
  Die globale Stilprüfung meldet 1903 bestehende Befunde; die Prüfung der
  geänderten Python-Zeilen meldet keine neuen Befunde.
- `git diff --check` erfolgreich. Bedienablauf und Ablage sind in
  [Skriptpakete](../asset-studio/SKRIPTPAKETE.md) und
  [Pipelines](../asset-studio/PIPELINES.md) dokumentiert. Relative Verweise
  aller vier geänderten/neuen technischen Dokumente geprüft: keine ungültigen
  Ziele. Abschließende Ansichten von Dashboard, Projekt und Lieferübersicht
  mit einem temporären NPC-Projekt geprüft.

## Wiederholbarkeit und Wiederherstellung

Tests verwenden temporäre Projekte und synthetische Bilder. Bestehende
SQLite-Sicherungen und Dateijournale bleiben maßgeblich. Historische Quellen und
Ergebnisse werden nicht pauschal gelöscht oder überschrieben. Änderungen lassen
sich anhand des Git-Diffs und dieses Plans gezielt nachvollziehen; fremde lokale
Änderungen bleiben unangetastet.

## Ergebnis und Rückblick

Abgeschlossen. Feste Projekt- und Pipeline-Elemente, das Dashboard mit sichtbaren
Asset-Verbindungen und Ausgabeziel, getrennte Posenkonfiguration und Quellenpflege
sowie die gespiegelte Posenablage sind umgesetzt. Die mitgelieferte GIF-Pipeline
erzeugt geprüfte Vorschauen unter `previews/gif` und lässt sich mit weiteren
Skripten verbinden. Bestehende Revisionen und Zuordnungen bleiben nachvollziehbar.

Die vorhandenen Dienste konnten um diese Abläufe erweitert werden. Der
Videoordner ist vorbereitet; Videoerzeugung ist weiterhin nicht implementiert.
Die oben genannten bestehenden Probleme des Repository-Gesamtchecks bleiben
als separate Aufgaben bestehen.
