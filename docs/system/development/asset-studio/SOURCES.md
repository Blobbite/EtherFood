# Quellenimport und aktive Lieferungen

Ein Asset benötigt zuerst gespeicherte Anforderungen. **Quellen importieren …**
in Werkzeugleiste oder Kontextmenü öffnet die Mehrfachauswahl für PNG-Dateien.
Das importiert geprüfte Kopien, nicht die späteren Grafik-/Framevarianten.
Im **Asset-Menü → Posen** und im Anforderungsdialog steht derselbe Import
direkt neben **Anker Y**. Der Zähler zeigt die Lieferung der gespeicherten
Anforderungen. Vor dem Import noch nicht gespeicherte Änderungen werden nur
nach ausdrücklicher Bestätigung übernommen.

**Neues Asset / NPC …** führt über Name, Besitzer, Vorlage und Anforderungen
zur Zusammenfassung. Erst **Asset jetzt anlegen** schreibt Metadaten.
**Nur Konfiguration** kopiert Einstellungen mit neuen Pose-/Asset-IDs, keine
Quellen, Nachweise oder Freigaben. Bestehende Quellen lassen sich später ergänzen.
Im Asset-Menü sind Übersicht, Quellen, Posen, Quellenversionen und Dokumentation
nutzbar; die späteren Verarbeitungs-/Prüfreiter bleiben sichtbar deaktiviert.

1. PNG-Dateien auswählen. Pose, Richtung und Quellart je Zeile prüfen.
   Dateinamen schlagen nur eine eindeutig passende Richtung vor; fehlende
   Richtungen werden niemals durch andere Dateien aufgefüllt.
2. Raster bewusst wählen: **16×1 = 16 Frames nebeneinander**, **1×16 = untereinander**,
   beispielsweise **4×4** oder ein anderes teilbares Raster. Die Bildproportionen
   bestimmen das Raster nicht. Source-Einzelbilder verwenden **1×1** und bleiben
   unabhängig von Animationslieferungen; es wird kein erster Frame ausgeschnitten.
3. **Auswahl prüfen** liest und decodiert die PNGs mit Grenzen. Höchstens 128
   Dateien je Lieferung, standardmäßig 64 MiB/Datei und 32 Millionen Pixel/Bild.
   Framezahl muss Spalten × Zeilen entsprechen; maximal 64 Quellframes.
4. **Geprüfte Quellen importieren** bestätigen. Ziel ist der bestehende
   SHA256-Objektspeicher `.asset-studio/objects` im Studio-Projekt.
   Originalname, Hash, Maße, Raster, Pose/Richtung, Importzeit und optionales
   externes Werkzeug werden in unveränderlichen Quellenrevisionen gespeichert.
5. Unter **Lieferstand und Revisionen** fehlen nicht gelieferte Pflichtquellen
   weiterhin. Nicht benötigte Richtungen werden getrennt angezeigt. Neue
   Lieferungen ersetzen aktive Zuordnungen nur mit ausdrücklicher Bestätigung.
   Eine ältere Revision kann bewusst wieder aktiviert werden.

Der Katalog unterscheidet Quelle, Entwurfsstand und Freigabe. Eine aktive
Quellenrevision ist keine Sichtabnahme, kein fertiger Build und keine
Godot-Bereitstellung. Neue Quellenbindungen machen dazu unpassende technische
Nachweise veraltet, ohne historische Revisionen oder Nachweise umzuschreiben.
Eigene 8-/10-/12-/14-Frame-Originale bleiben ebenfalls als Revisionen erhalten;
pro Pose/Richtung/Quellart ist jeweils eine Lieferung aktiv.

## Abbruch, Änderungen und Wiederherstellung

Prüfung und Kopieren laufen im Hintergrund mit eigener Katalogverbindung.
**Vorgang abbrechen** oder Schließen fordert Abbruch an und wartet auf einen
sicheren Endpunkt. Eine schon abgeschlossene Registrierung wird ehrlich als
Import angezeigt. Vor Abschluss gibt es keine halbe neue aktive Lieferung.

Wird eine Datei oder die Asset-Konfiguration zwischen Prüfung und Übernahme
geändert, muss die Auswahl erneut geprüft werden. Bei Fehlern bleiben alte
Zuordnungen und Originale erhalten. Geprüfte, noch unzugeordnete Blobs und
unterbrochene Operationen können im bestehenden Importjournal verbleiben;
keine automatische Löschung fremder oder vorheriger Dateien. Erneuter Import
verwendet vorhandene identische Blobbytes nach Integritätsprüfung wieder.

Metadaten-Snapshots enthalten keine PNG-Bytes oder lokalen Quellpfade.
Nach Snapshot-Import sind Quellenverweise ausdrücklich ungeprüft; sie zählen
nicht als vollständige Lieferung. Dateien erneut bewusst importieren.

## Noch nicht enthalten

Keine Animationserzeugung, Frameinterpolation, Farb-/Maskenberechnung,
Grafikvarianten, automatische Pipeline, Godot-Bereitstellung oder Freigabe.
Der lesende Bestandsscanner bleibt getrennt: Seine Beobachtungen sind keine
verwalteten Quellenkopien.
