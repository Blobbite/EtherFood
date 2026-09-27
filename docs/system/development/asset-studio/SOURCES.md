# Quellenimport und aktive Lieferungen

Ein Asset benötigt zuerst gespeicherte Anforderungen. **Asset-Menü → Posen**
öffnet über den Quellenbutton neben **Anker Y** die Mehrfachauswahl für PNG-Dateien.
Das importiert geprüfte Kopien, nicht die späteren Grafik-/Framevarianten.
Das Asset-Menü öffnet sich per Rechtsklick auf ein Asset unter **Projekt und
Verwendungen** oder im Projekt-Canvas → **Asset-Menü öffnen …**. Die obere
Projekt-Toolbar enthält keine zusätzlichen Asset-/NPC- oder Asset-Menü-Buttons.
Der Zähler zeigt die Lieferung der gespeicherten
Anforderungen. Vor dem Import noch nicht gespeicherte Änderungen werden nur
nach ausdrücklicher Bestätigung übernommen.

Unter **Projekt und Verwendungen** auf Projektweit, einen Akt, ein Kapitel
oder ein Paket rechtsklicken → **Neues Asset …**. Derselbe Assistent für Assets
und NPCs führt über Name, Besitzer, Vorlage und Anforderungen zur Zusammenfassung.
Erst **Asset jetzt anlegen** schreibt Metadaten.
**Nur Konfiguration** kopiert Einstellungen mit neuen Pose-/Asset-IDs, keine
Quellen, Nachweise oder Freigaben. Bestehende Quellen lassen sich später ergänzen.
Im Asset-Menü sind Übersicht, Quellen/Revisionen, Posen und Dokumentation
nutzbar; die späteren Verarbeitungs-/Prüfreiter bleiben sichtbar deaktiviert.

1. PNG-Dateien auswählen. Pose, Richtung und Quellart je Zeile prüfen.
   Dateinamen schlagen eine eindeutig passende Richtung und Rasterangaben vor; fehlende
   Richtungen werden niemals durch andere Dateien aufgefüllt.
2. Rastervorschlag kontrollieren: **16×1 = 16 Frames nebeneinander**,
   **1×16 = untereinander**, **4×4 = vier Spalten und vier Zeilen**.
   Eindeutige Dateiangaben wie `_4x4_` werden eingetragen. Sonst prüft **Auto**
   beim Prüfschritt regelmäßige Transparenzabstände im Hintergrund. Undurchsichtige,
   widersprüchliche oder unklare Bilder erfordern eine manuelle Auswahl.
   Bildanalyse ist ein Vorschlag, keine künstlerische Abnahme; vor dem Import
   stehen das konkrete Raster und die Framezahl sichtbar in der Tabelle.
   Die Bildproportionen allein bestimmen nichts. Manuelle Angaben haben Vorrang.
   Source-Einzelbilder verwenden **1×1** und bleiben
   unabhängig von Animationslieferungen; es wird kein erster Frame ausgeschnitten.
3. **Auswahl prüfen** liest und decodiert die PNGs mit Grenzen. Höchstens 128
   Dateien je Lieferung, standardmäßig 64 MiB/Datei und 32 Millionen Pixel/Bild.
   Framezahl muss Spalten × Zeilen entsprechen; maximal 64 Quellframes.
4. **Geprüfte Quellen importieren** bestätigen. Ziel ist der bestehende
   SHA256-Objektspeicher `.asset-studio/objects` im Studio-Projekt.
   Originalname, Hash, Maße, Raster, Pose/Richtung, Importzeit und optionales
   externes Werkzeug werden in unveränderlichen Quellenrevisionen gespeichert.
5. **Auswahl und Prüfung** zeigt bereits gespeicherte Quellen als kompakte
   Posenbündel; nur neu ausgewählte Dateien erscheinen einzeln. Nach dem Import
   wird die neue Auswahl geleert, das gespeicherte Bündel bleibt auch beim
   erneuten Öffnen sichtbar.
6. **Lieferstand und Revisionen** bzw. **Asset-Menü → Quellen / Revisionen**:
   Pose aufklappen, dann einzelne Richtung für ihre historischen Revisionen.
   Aktive Dateien zeigen **Raster**, **Frames** und Importdatum unabhängig vom
   Dateinamen. Nicht gelieferte Pflichtquellen bleiben fehlend; unnötige Richtungen
   bleiben ausdrücklich nicht erforderlich. Keine globale lange Revisionsliste.
7. **Ersetzen …** an einer Richtung beschränkt die Lieferung auf diese Quelle.
   **Pose neu liefern …** fordert alle aktuell benötigten Richtungen der Pose
   gemeinsam; eine unvollständige Auswahl ändert nichts. Ersetzen benötigt weiter
   die bewusste Bestätigung. Andere Posen und Originale bleiben unberührt.
   Frühere Einzelrevisionen oder vollständige Lieferbündel lassen sich wieder
   aktivieren; eine beschädigte Quelle verhindert den gesamten Bündelwechsel.

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
