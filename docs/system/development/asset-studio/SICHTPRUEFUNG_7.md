# Briefing Paket 7 – Notizen, Aufträge und Buildplan

Status: technische Tests durchgeführt, **deine Bedienabnahme noch offen**.
Ein vorhandenes Testprojekt reicht; ein neues Projekt ist nicht erforderlich.
Die Anwendung nach Aktualisierung vollständig neu starten.

1. **Notiz öffnen:** Im Canvas einfach auf das Notizsymbol klicken. Dieselbe
   Notiz auch im Baum und über die Suche öffnen. Jedes Mal muss **Notizen**
   aktiv sein und der richtige Text unten im eingebetteten Editor stehen.
2. **Notiz bearbeiten:** Titel, Markdown, Farbe und Anheften ändern; Strg+S.
   Andere Notiz wählen und zurückkehren, danach Projekt neu öffnen. Alles
   bleibt erhalten. Ungespeicherter Wechsel bietet Speichern/Verwerfen/Abbrechen.
   Notizen stehen nicht mehr in der Dokumentationsauswahl; Dokumentation bleibt
   dort separat bearbeitbar. Optional einen kleinen Textanhang an einer Notiz testen.
3. **Aufträge:** Toolbar → Aufträge → Diagnose „Erfolg“ starten. Danach „Fehler
   (Exit 7)“ und „Ausgabe fehlt“. Nur der erste darf erfolgreich sein. Für jeden
   Auftrag sind Status, Argumente, Ereignisse und Rohlogs einsehbar.
4. **Weiterarbeiten/Abbruch:** „Langer Lauf“ starten, währenddessen Notizen oder
   Kanban öffnen. Die Oberfläche bleibt bedienbar. Unter Aufträge abbrechen;
   Abschluss muss „Abgebrochen“ sein. Optional „FramReduce prüfen (--help)“:
   vorhandene Installation liefert Hilfe; fehlende Module müssen ehrlich als
   Fehler erscheinen, ohne ungefragte Installation.
5. **Asset-Dry-run:** Ein vorhandenes Asset → Asset-Menü → Buildplan / Dry-run.
   Stimmen Variantenanzahl und Gründe für fehlende Quellen? „Produktiver Adapter
   folgt …“ bzw. fehlende Master-/Maskenrevision ist hier **erwartet**, kein
   neuer Fehler. Es dürfen keine Spielgrafiken oder Godot-Dateien entstehen.
6. **Cache-Diagnose:** Im Buildplan „Technische Cache-Diagnose“ wählen → Dry-run
   → Diagnoseplan ausführen → erneut Dry-run. Nach dem ersten Lauf müssen alle
   neun Schritte wiederverwendbar sein. Erneut ausführen: Vergleich zeigt
   „Wiederverwendet“, keine weiteren Werkzeugaufträge. Nach Neustart erneut prüfen.

**Überspringen:** erneuter Kompletttest aller Raster/Posen/Canvas-Layouts,
manuelles Beschädigen des Caches, echte Masken-/Farbbearbeitung, Godot-Export
und Laufzeitfreigaben. Cache-Schäden, Kindprozessende und transitive Veraltung
sind automatisiert geprüft. Künstlerische Freigaben werden dadurch nicht ersetzt.

Bitte zurückmelden: `1 ✅ … 6 ✅` oder Punkt + Beobachtung. Erst danach die
nächsten Issues auswählen; naheliegend sind **T019 Masterreferenzen/Profilversionen**
und anschließend **T020 Materialmasken**. Diese sind hier nicht mit umgesetzt.
