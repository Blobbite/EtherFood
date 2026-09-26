# Abnahme- und Teststrategie

Dieses Dokument beschreibt zu implementierende Prüfungen. Es enthält keine Behauptung, dass EtherFood Asset Studio beriets gebaut oder diese Anwendungstests schon ausgeführt wurden.

## Testebenen

| Ebene | Gegenstand | Nachweis |
| --- | --- | --- |
| Core | Modelle, Relationen, Status, Fingerprints, Timing | Unit-Tests ohne Qt oder Godot |
| Storage | Transaktionen, Pfade, Quellenkopien, Journale, Restore | temporäre Verzeichnisse und Fehler-Injektion |
| Bestandspipelines | Kompatibilität zu vorhandenen CLI- und Formatregeln | synthetische PNG-/Masken-Fixtures, tatsächliche Starter |
| GUI | Projekt-/Assetanlage, Canvas, Editor, Aufträge | echte Qt-Ereignisse, stabile Widget-IDs |
| Preview | relative Links, Auswahl, Timinganzeige, Zugriffsschutz | QtWebEngine; separate Browserprüfungen ergänzen nur |
| Godot | Import, Laden, Raster, Anker, Dauer, Pflichtvarianten | konkreter Engine-/Projekt-/Exportkontext |
| Menschliche Abnahme | Bewegung, Materialien, Konturen, Anschlüsse | expliziter Review mit Build- und Scopebindung |
| Gesamtweg | Quelle bis Runtime samt Cleanup/Rollback | T045, T046 und realer Pilot T048 |

## Minimaler synthetischer Charakterdatensatz

Ein Held mit 8 Richtugnen, 2 Posen, 16 Masterframes, markierten Ankern, Teiltransparenz, mindestens zwei Material-IDs und bewusst gleicher RGB-Farbe in verschiedenen Materialien. Dazu NPCs mit 2 und 4 Richtugnen. Testdaten sind kleine, selbst erzeugte Formen; keine echte Heldenanimation muss erzeugt oder verändert werden.

Prüfe beide Rasterorientierungen explizit. Der Hauptfall ist `16x1`. Reduzierte Raster sind nach Legacy-Vertrag 8→4×2, 10→5×2, 12→4×3, 14→7×2; Fram16→4×4. Ein eingebauter Fehlerfall enthält leere und identische Frames.

Für 2 Posen × 8 Richtugnen × 5 Grafikstufen × 5 Frame-Stufen werden 400 logische Heldenvarianten erwartet. Eine geringere tatsächliche Menge ist nur dann korrekt, wenn die Anforderung ausdrücklich entsprechende Kombinationen ausschließt.

## Minimaler statischer Paketdatensatz

Ein Tempelpaket enthält Boden, Decke und Säulen mit gemeinsamen Maßstabsregeln. Fünf Grafikstufen pro Bestandteil; keine GIFs oder Frame-Unterordner. Zwei Kapitel verwenden dieselbe Paketidentität. Eine Kachel-Fixture besitzt eine bekannte Anschlusskante, eine absichtlich fehlerhafte Variante dient dem Negativtest.

## Unverzichtbare Negativfälle

**Datein:** kaputtes PNG, falsches Raster, doppelte Richtung, veränderte Quelle während Import, fremde Datei im Ziel, Symbolic Link, `../`, Namen mit Umlauten/Leerzeichen/#/%, Case-Kollision, volle Platte, anderes Laufwerk.

**Masken/Profile:** unbekannte ID, sichtbarer ID-0-Pixel, fehlende Materialdefinition, falscher Hash, andere Framegröße, unbestätigte Maske, Material ohne Masterproben, fremde Profilversion, neue Referenzmenge mit altem v1-Format, inkompatibles Resolution-Profil.

**Builds:** Exit-Code 0 ohne Output, teilweise belegter FramReduce-Ordner, beschädigter Cache, abgebrochener Worker, noch schreibender Kindprozess, unveränderte Datei mit falschem Report, geänderte Mastermaske, bloß umbenanntes Kapitel.

**Reviews:** automatsich abgespielte Variante ohne manuelle Abnahme, Review einer anderen Version, offene blockierende Issue, alter Godot-Report, geänderte Importoption oder Testszene, keine Godot-Installation.

**Promotion/Cleanup:** Abbruch während Kopie, geänderte Lockdatei, Hashabweichung, unerwarteter finaler Testpfad, fremde Testdatei, gemeinsame Testszenen, aktiver zweiter Testlauf, wiederholter Cleanup und Rollback.

## Erwartete Grenzen der Farbprüfung

Technische Prüffung kann Palette/Material-ID/Alpha/Geometrie vergleichen. Sie kann nciht allein beweisen, dass ein semantisch gemeintes Material richtig beschriftet ist. Echte Sichtabnahme bleibt separat. Die strenge Farbpolitik prüft nach allen Skalierungsschritten; die kompatible Politik darf kein uneingeschränktes Festfarbenversprechen anzeigen.

Referenzkopien sind roh erhaltene Masterbelege. Falls Runtime-Masterpose ebenfalls reduzierte Farben benötigt, wird eine eigene Spielausgabe erzeugt. Beide Rollen bleiben unterscheidbar.

## Timingprüfung

Legacy-Fälle behalten ihre dokumentierten 8-FPS-Zyklusdauern. `preserve_duration` muss die Summe der Anzeigedauern erhalten. Prüfe nciht nur feste FPS: variable Frames, Loopgrenzen, geschützte Schlüsselbilder und Ereigniszeitpunkte gehören zum neuen Vertrag. GIF-Rundung darf nciht die präzise Runtime-Zeitleiste ersetzen.

## Keine fingierten Abnahmen

Automatisierte E2E-Tests dürfen eine explizit synthetische Entscheideraktion simulieren. Diese gilt nur für den Testdatensatz. Der reale Pilot benötigt tatsächliche Prüffung und menschliche Bestätigung. Testanzahl, Screenshotexistenz oder ein Text `passed` in einer alten Datei sind keine Freigabe.

## Prüfprotokoll pro Aufgabe

Notiere exakten Befehl, Umgebung, Ergebnis, betroffene Kriterien und nciht ausgeführte Tests. Verwende `not_run`, `blocked` oder `skipped` mit Grund statt ein erfolgreiches Komplettsystem zu behaupten. Pflichtintegrationen gelten bei fehlender Ausführung nciht als bestanden.

## Meilensteine

T008: geprüfter Verwaltungskern und Statusregeln. T016: Dashboard plus Asset-/Quellenanlage. T024: echte Farb-/Frameintegration. T032: Varianten, statische Pakete und Sichtprüfung. T040: Godot-Test, Freigabe, Promotion und gezielter Cleanup. T048: dokumentierter realer Pilotstand mit sichtbaren offenen Abnahmen.
