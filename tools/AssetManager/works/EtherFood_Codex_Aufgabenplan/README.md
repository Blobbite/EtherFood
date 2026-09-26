# EtherFood — Codex-Aufgabenplan

**48 einzeln bearbeitbare Aufgaben in 6 Phasen. Pro Aufgabe ein eigener Ordner mit genau einer `p.md`.** Dieses ZIP enthält die komplette Planung und Prompts, nciht eine beriets implementierte Anwendung.

## Start

Öffne [START_HIER.md](START_HIER.md). Darin steht der erste kopierbare Auftrag für Codex. Gib Codex Zugriff auf den echten EtherFood-/PyGameTools-Checkout und auf diesen entpackten Planordner. Der Quelltextdump allein ist kein Ersatz für einen lauffähigen Checkout.

Danach wird jeweils eine Aufgabe aus dem [Aufgabenindex](AUFGABENINDEX.md) bearbeitet. Lies den Ergebnisbericht und prüfe die Abnahmekriterien, bevor du die nächste Aufgabe beauftragst. Die Reihenfolge ist T001 bis T048. Zusätzliche Abhängigkeiten stehen in jeder `p.md` und in [tasks.json](tasks.json).

## Enthaltene Phasen

| Phase | Aufgaben | Inhalt |
| --- | --- | --- |
| A | T001–T008 | Bestand, Architektur, Katalog, sichere Ablage, Akte/Kapitel, Dokumente, Schrittketten |
| B | T009–T016 | Desktop-Dashboard, Canvas, Nebenverbindungen, Dokumenteditor, Asset-/Quellenanlage |
| C | T017–T024 | Arbeitsprozesse, Buildcache, Masterreferenzen, Maskeneditor/-vorschläge, Farben und Frames |
| D | T025–T032 | Timing, Grafikstufen, exakte Endfarben, Texturen, Tempelpakete, Vorschau und Sichtprüfung |
| E | T033–T040 | Kandidaten, Git, Godot-Export und -Test, Freigabe, Runtime-Übernahme und Cleanup |
| F | T041–T048 | Historie, automatische Dokumentation, Vorlagen, Backup, E2E-Tests, Installation und Pilot |

## Wegweiser

[Projektbrief](grundlagen/PROJEKTBRIEF.md) beschreibt das Ziel. [Architektur](grundlagen/ARCHITEKTUR.md) und [Datenverträge](grundlagen/DATENVERTRAEGE.md) verhindern widersprüchliche Teilimplementierungen. [Arbeitsregeln](grundlagen/ARBEITSREGELN_CODEX.md) gelten in jedem einzelnen Prompt.

Die [Anforderungsmatrix](grundlagen/ANFORDERUNGSMATRIX.md) ordnet 36 Anforderugnen und Schutzregeln den Aufgaben zu. [Teststrategie](grundlagen/TESTSTRATEGIE.md), [Entscheidungen und Risiken](grundlagen/ENTSCHEIDUNGEN_UND_RISIKEN.md) und [Ablageregeln](grundlagen/ABLAGE_UND_SICHERHEIT.md) ergänzen die Aufgaben.

[Quellenindex](quellen/QUELLENINDEX.md) enthält gezielte, unveränderte Auszüge aus deinen Uploads mit Originalzeilen und SHA-256 der Ausgangsdateien. [Offizielle Referenzen](grundlagen/OFFIZIELLE_REFERENZEN.md) sind davon getrennte API-Hilfen.

[FORTSCHRITT.md](FORTSCHRITT.md) ist die anfänglich leere Fortschrittsliste. Die [Ergebnisvorlage](vorlagen/ERGEBNISBERICHT.md) vereinheitlicht Codex-Übergaben. Der [Folgeauftrag](vorlagen/FOLGEAUFGABE_STARTEN.md) hilft beim Start einzelner späterer Aufgaben.

## Beispielstruktur

```text
EtherFood_Codex_Aufgabenplan/
  README.md
  START_HIER.md
  AUFGABENINDEX.md
  FORTSCHRITT.md
  ABHAENGIGKEITEN.md
  tasks.json
  MANIFEST.json
  grundlagen/
  quellen/
  beispiele/
  vorlagen/
  pruefung/
  aufgaben/
    001-bestand-und-schreibgrenzen/p.md
    002-architektur-und-vertraege/p.md
    ...
    048-pilotmigration-und-abschluss/p.md
```

## Was in jedem Prompt steht

Konkretes Ziel, benötigte Vorgänger, Einordnung des vorhandenen Codes, nummerierte Arbeitsschritte, erwartete Ergebnisse, verpflichtende Tests, Abnahmekriterien, ausdrückliche Nicht-Ziele und ein Ergebnisbericht. Codex soll genau diese Aufgabe implementieren, nciht ungefragt die gesamte Anwendung in einem Durchgang.

Die Planung erhält vorhandene Python-Pipelines. Neue Funktionen wie variable Masterreferenzen, sichere Maskenvorschläge, Texturmodule und Godot-Freigaben sind ausdrücklich neue Entwicklungsaufgaben. Reale Sichtabnahmen werden niemals durch einen erfundenen Teststatus ersetzt.

## Paket prüfen

```bash
python3 pruefung/check_plan.py
```

Das Prüfskript ist nur für dieses Planpaket. Es prüft Aufgabenanzahl, Abhängigkeiten, lokale Verlinkungen, Anforderungsabdeckung und Dateihashes. Es startet keine Pipeline, verändert kein Repository und prüft nciht eine schon existierende Anwendung. Nach eigenen Änderungen am Plan passen die ursprünglichen Integritätshashes erwartungsgemäß nciht mehr.

Details des bei Erstellung ausgeführten Paketchecks stehen in [PAKETPRUEFUNG.md](pruefung/PAKETPRUEFUNG.md).
