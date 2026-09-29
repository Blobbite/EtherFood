# AssetManager: Bericht zum gesicherten Zwischenstand

Stand: 29.09.2026. Die Umsetzung wurde auf Benutzerwunsch gestoppt. Dieser
Bericht hält die vorhandenen Änderungen und offenen Punkte für den Commit fest;
er bescheinigt keine vollständige Abnahme. Der AssetManager bleibt im Repository.
Eine Auslagerung oder Entfernung wurde nicht vorgenommen.

## Enthaltene Umsetzung

- Native Oberfläche mit den Haupteditoren **Projekt** und **Skripte & Pipelines**,
  gemeinsamer Anordnung, Pipelineübersicht, Pythoneditor und zwei Suchbereichen.
  Die dauerhafte rechte Eigenschaftenleiste und alte Auftragseinstiege wurden
  entfernt. Die ausdrückliche Demo liegt unter Einstellungen → Tests.
- Getrennte Pipelinedefinitionen und Projektverwendungen. Aktuelle Skripte liegen
  unter `.tools/scrips/`, Definitionen unter `.tools/piplins/`. Eingabebereiche,
  benannte Ergebnisverbindungen, Folder-Ausgaben und Freigaben sind implementiert.
- Eigene serielle Pipelineausführung mit eingefrorenen Dateien, Phasengrenzen,
  Ergebnisprüfung, Cache, Pause und Abbruch. Alte Auftragsdienste wurden abgelöst.
- Archiv und 30-Tage-Papierkorb, Wiederherstellung, kontrollierte Bereinigung
  und Migration mit Sicherung und Dateijournal sind implementiert.
- Die bereits erweiterte Markdown-Bearbeitung ist enthalten: gemeinsamer
  Quelltext, Tabellenbearbeitung, Links, sichere Bild-/SVG-Anzeige und animierte
  GIFs. Bedienungsdokumentation, Fixtures und automatisierte Tests wurden ergänzt.

## Tatsächlich ausgeführte Prüfungen

Die Zahlen stammen aus den letzten Läufen vor dem Stopp. Nachfolgende kleine
Änderungen wurden nur gezielt geprüft; ein vollständig grüner Gesamtlauf des
jetzigen Arbeitsstands liegt noch nicht vor.

| Prüfung | Ergebnis |
| --- | --- |
| AssetManager-Backend, ohne `tests/gui` | **442 bestanden**, 297,83 s |
| Vollständige Qt-Suite unter Linux mit `QT_QPA_PLATFORM=offscreen` | **268 bestanden, 2 fehlgeschlagen**, 303,22 s |
| Anschließende gezielte Nachprüfung von Suche, Verwendungen, Skriptbaum und Dateigrundlage | **20 bestanden, 1 fehlgeschlagen**, 15,60 s; die beiden vorherigen GUI-Fehler bestanden danach |
| PyGameTools-Bildverarbeitung und SpritesheetResolution-Pipeline | **171 bestanden**, 38,28 s |
| `python3 tools/control.py check` | Nicht bestanden: **283 Pythonprüfungen bestanden, 4 fehlgeschlagen, 37 übersprungen**; zusätzliche Stil-/Umgebungsbefunde; Godot 4 fehlt |
| Tatsächliche Qt-Ansichten | Projekt, Übersicht, Pipeline- und Pythoneditor bei 1100×700 und 1500×960 in hell/dunkel erzeugt; ausgewählte Ansichten visuell geprüft und Layoutmängel korrigiert |

Die verwendeten Tests liegen unter `tools/AssetManager/tests/` und
`tools/AssetManager/PyGameTools/`. Einzelne Läufe und die Abnahmezuordnung sind im
[Arbeitsplan](../plans/asset-studio-zwei-editoren-und-automatik.md) dokumentiert.
Ein Screenshot gilt nicht als Nachweis von Speicherung, Undo oder Animation.

## Noch offen

1. Der neue Qt-Test
   `test_script_tree_context_order_and_view_specific_structure` schlägt beim
   Rückgängigmachen einer Skriptbaum-Umsortierung fehl. Ursache und Undo-Verhalten
   müssen geklärt und anschließend erneut geprüft werden.
2. Abschließender Gesamtlauf nach den letzten Änderungen sowie vollständiger
   Abgleich aller verbindlichen Abnahmekriterien, einschließlich des Rückbaus
   alter Auftragsabhängigkeiten. Die Arbeitsschritte 7 und 8 bleiben im Plan offen.
3. Praktische Prüfungen auf weiteren Desktopplattformen sowie native Browser-/
   Mailprogramm-Übergaben, Bildschirmleser und Skalierung. Qt-Offscreen-Tests
   ersetzen diese Prüfungen nicht.
4. Die unabhängigen Repository-Fehler bleiben bestehen: vorbereitete
   Assetverzeichnisse fehlen, ein Godot-Fenstervertrag weicht ab,
   Dokumentationsstruktur/-links schlagen fehl, bestehende Stilbefunde und die
   fehlende Godot-Laufzeit verhindern einen grünen Standardcheck.

## Daten und Bestandsübernahme

Migration und Bereinigung wurden ausschließlich an isolierten temporären
Testprojekten geprüft. Die implementierte Migration sichert den Katalog und
ausdrücklich verwaltete Dateien, übernimmt benötigte Ergebnisse und Referenzen
und kann nach Unterbrechung fortgesetzt werden. Alte Freigaben werden nicht
ungeprüft übernommen.

Das lokale Projekt `schemas/Test-Projekt/` wurde nicht migriert, verändert oder
in diesen Commit aufgenommen. Spielinhalte wurden nicht umgebaut. Es wurden
keine neuen Anwendungsabhängigkeiten ergänzt.
