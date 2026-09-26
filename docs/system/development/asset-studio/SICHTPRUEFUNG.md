# Erste Sichtprüfung nach Paket 4

Stand: T001–T012 technisch umgesetzt. **Menschliche Sichtabnahme offen.**
Noch keine Bildpipeline, Maskenbearbeitung oder Godot-Bereitstellung freigeben.
Die ausgegrauten Schaltflächen sind absichtlich nicht verfügbar.

## Start

Im Repository-Stamm, mit Python 3.11 und funktionsfähigem Linux-Desktop:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e './tools/AssetManager[test,gui]'
.venv/bin/python tools/AssetManager/studio.py gui
```

Ein vorhandenes Studio-Projekt lässt sich mit `gui --project <projektordner>`
öffnen. Einen **neuen leeren Testordner außerhalb des Repositorys** verwenden,
nicht `game/assets`, `game/test_assets` oder einen Originalgrafikordner.
Optionale Wurzeln dürfen für diese erste Sichtprüfung frei bleiben.
Ein Studio-Projekt ist ein Verwaltungskatalog, nicht das Godot-Projekt selbst.

Bei fehlendem Qt/GL/EGL/XKB/D-Bus helfen die Hinweise in
[DEVELOPMENT.md](DEVELOPMENT.md). Die Container-Tests liefen offscreen mit
temporären Systembibliotheken; ein echter Desktop und andere Betriebssysteme
sind damit ausdrücklich noch nicht visuell abgenommen.

## Klickfolge und erwartetes Ergebnis

| Schritt | Prüfen | Erwartung |
| --- | --- | --- |
| 1 | Neues Projekt: Name und leerer Testordner; danach „Demo anlegen“ | Projektweiter Rahmen, ein Akt, zwei Kapitel, globaler Held/Effekt und Tempelpaket sichtbar |
| 2 | Akt im Baum ein-/ausklappen; Karte doppelklicken; Strg+Mausrad und Leerfläche ziehen | Nur Ansicht ändert sich; Karten gehen nicht verloren |
| 3 | Beide Heldenverweise unter den Kapiteln anklicken | Identische Asset-ID in den Eigenschaften, keine Kopie |
| 4 | Karte ziehen, Breite/Höhe ändern, Undo/Redo; Anordnen/Manuell | Ansicht reversibel, Besitz/Abhängigkeiten unverändert |
| 5 | Zielkarte wählen, uses oder depends_on explizit anlegen; Verbindung lösen und Undo | Eindeutige Beziehung; keine Dateien gelöscht; Zyklus wird abgewiesen |
| 6 | Dokumente: Notiz anlegen, Text schreiben, Karte wechseln | Speichern/Verwerfen/Abbrechen; Abbrechen erhält Text; Strg+S speichert |
| 7 | Markdown importieren, gleichen Titel erneut importieren; Anhang hinzufügen | Original unverändert; Konflikt erfordert bewusste Revision; Skripte werden nicht ausgeführt |
| 8 | Aufgabe/Issue anlegen, nach Akt/Kapitel/Status/Typ suchen | Treffer fokussiert richtige Karte; Kapitelumbenennung verliert Zuordnung nicht |
| 9 | Fenster schließen, Projekt über „Zuletzt verwendet“ öffnen | IDs, Notizen, Verbindungen und Ansicht bleiben erhalten |
| 10 | Verfügbarkeit und Status lesen | Fehlende Quellen/Prüfungen bleiben offen; nichts ist automatisch freigegeben |

Text-/JSON-Anhänge werden intern nur lesend angezeigt. Binär-/Skriptanhänge
werden sicher verwaltet, aber noch nicht mit externen Programmen geöffnet.
Der Undo-Stapel gilt für die laufende Sitzung; gespeicherte Ergebnisse bleiben
nach Neustart erhalten, der Aktionsverlauf selbst wird nicht wiederhergestellt.

## Rückmeldung

Bitte Betriebssystem, Bildschirmauflösung, ausgeführte Schritte und konkrete
Abweichungen nennen; bei Bedarf einen Screenshot. Besonders Schriftgröße,
übersichtliche Gruppierung, Bedienung und die Trennung der Verbindungstypen
prüfen. Erst nach dieser Rückmeldung sollte Paket 5 beginnen.

## Bereits automatisiert geprüft

Core: Transaktionen, Migrationen/Backups, Revisionskonflikte, Importabbrüche,
Pfadgrenzen, Dateiintegrität, gemeinsame Assets, Dokumente und Statusregeln.
GUI: Neuanlage-Dialog mit echten Buttonereignissen, Tastatureingabe,
Speichern/Wiederöffnen, Dirty-Dialog, Konflikte, Baumverweise, Canvas-Mausdrag,
Größe, Collapse, Suche, Beziehungen/Undo und fehlende Laufwerke.
Das ist keine künstlerische, produktive oder menschliche Sichtfreigabe.
