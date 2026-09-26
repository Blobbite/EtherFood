# Entscheidungen, offene Punkte und Grenzen

## Bereits durch Nutzeranforderung festgelegt

Ein gemeinsames Dashboard statt verstreuter manueller Ordnerpflege. Projektweiter Rahmen, Akte, Kapitel und Nebenkarten. Globale und akt-/kapitelbezogene Inhalte. Variable Richtungszahlen. Source-Einzelbilder und extern erstellte Spritesheets. Automatisierte Farb-, Masken-, Frame- und Grafikverarbeitung mit Prüfschritten. Godot-Testbereich, anschließende Freigabe und Übernahme mit Test-Cleanup. Statische Pakete ohne Animationspflicht. Erweiterbarkeit und integrierte Dokumentation.

## Entscheidungen dieses Plans

| Entscheidung | Warum hier gewählt | Aufgabe |
| --- | --- | --- |
| Lokale Python/PySide6-Anwendung | Passt zur vorhandenen Python-Verarbeitung; keine zusätzliche Serverpflicht. | T002–T003, T009 |
| Eigenes Paket bei PyGameTools, kein neues Repo vorausgesetzt | Vorhandene Integration erhalten; tatsächliche Git-Grenzen zuerst prüfen. | T001–T002 |
| SQLite für aktive Metadaten, explizite portable Exporte | Eine lokale Wahrheit statt widersprüchlicher Dateikopien. | T004, T034 |
| Unveränderliche Quellen/Kandidaten und separate Arbeitskopien | Wiederaufbau und Freigaben nachvollziehbar halten. | T005, T015, T033 |
| Bestehende HTML-Prüfansichten wiederverwenden | Vorhandene Funktion nciht parallel neu erfinden. | T031 |
| Regelbasierte Maskenvorschläge als erster Ansatz | Korrigierbar, testbar und ohne neuen Cloud-Dienst nutzbar. | T022 |
| Bestehendes Timing erhalten; neue Dauergarantie explizit | Keine stille Änderung von Animationen. | T025 |
| Portabler Godot-Manifest-/Loadervertrag bevorzugt | Test-/Runtime-Wurzeln trennen und Payload unverändert halten. | T035 |
| Freigabe getrennt von produktiver Aktivierung | Neue Entwürfe und Tests können neben dem stabilen Spielstand existieren. | T038–T040 |

Diese Entscheidungen sind nciht als aus dem Dump bewiesene vorhandene Implementierung zu lesen. Notwendige Abweichungen werden begründet dokumentiert und mit ihren betroffenen Aufgaben abgeglichen.

## Erst im echten Checkout zu prüfen

**Repository und Tools:** tatsächliche Wurzeln, installierte Python-Umgebung, nummerierte/unnummerierte Skriptordner, lokales Testsystem und beriets vorhandene Änderungen. T001 liefert die Auflösung, ohne Daten zu verschieben.

**Godot:** Version, bestehende Runtime-Ressourcen, Anker-/Namenskonventionen, Import-/Renderregeln und Exportfilter. T035 ergänzt den Adapter nur nach Prüffung. Kein erfundener .tscn-Pfad wird zur Pflicht gemacht.

**Farben und Materialien:** konkrete Masterquellen, tatsächliche Materiallabels und ihre Semantik. Der bekannte Greenhero-Referenzsatz bleibt Vorlage; neue Nutzerentscheidungen werden gespeichert, nciht erraten.

**Texturen:** konkrete Kachel-/Maßstabsregeln. T028 implementiert den statischen Farbbildweg; Datenkarten und 3D-Ressourcen erhalten ohne eigene Regeln keine falsche Standardverarbeitung.

**Plattformen:** die erste unterstützte Laufzeit folgt der tatsächlichen Umgebung. Andere Plattformen sind erst nach Installations-/GUI-/Godot-Prüffung zugesichert.

## Wichtige Risiken und Gegenmaßnahmen

Unvollständige Altordner werden als vollständig interpretiert → vollständige erwartete Dateimengen und Hashes prüfen. Feste acht Richtugnen bleiben versteckt → Profilloader, Matcher und HTML-Payload gemeinsam erweitern. Neue Materiallabels werden als sicher erklärt → Entwurfs-/Sichtstatus beibehalten. Skalierung zerstört Festfarben → explizite Endfarbpolitik und Tests. Zuschnitt verändert Standpunkt → Anchor-Transformationsvertrag. Testpfade gelangen ins Spiel → paketrelative Ressourcen und finaler Ladetest. Cleanup löscht fremde Arbeit → Besitz-/Hash-/Referenzlisten. Git nimmt fremde Änderungen mit → explizite Auswahl und Konfliktabbruch. Backup enthält nur DB → referenzierte Binärdaten und Journale mit sichern.

## Bewusst nciht festgelegt

Keine Liefertermine, Zeit-/Kostenversprechen, pauschalen Performancezahlen, tatsächlichen Materialfarben, realen Testergebnisse oder allgemeine Plattformfreigabe. Aufgabenstatus im Planpaket ist durchgehend `not_started`.
