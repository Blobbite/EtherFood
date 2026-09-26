# Bestandsaufnahme (T001)

Ausgangsrevision: `59ae32d23e0c18075d6837c35895aa82c08682cd`, Branch `main`.
GitHub: `Blobbite/EtherFood`. Die vorhandenen Umzüge des Aufgabenplans und
von PyGameTools nach `tools/AssetManager/` werden in Paket 1 übernommen,
nach byteweisem Vergleich der bereits verfolgten Dateien gegen HEAD.
Nicht verfolgte Grafikbestände werden nicht pauschal aufgenommen.

## Pfade und Schreibgrenzen

Die maschinenunabhängige [Pfadkarte](PATH_MAP.json) benennt reale Quellpfade.
`TOOL_ROOT` bezeichnet PyGameTools. `GODOT_ROOT` ist `game/`, also der
Ursprung von `res://`. `WORKSPACE_ROOT` und `VERSIONS_ROOT` für Benutzerdaten
sind noch nicht konfiguriert; insbesondere werden keine unbekannten
externen Laufwerke angenommen. Datenwurzeln müssen getrennt sein.
Arbeitskopien, Quellen, Versionsarchiv und Godot sind keine austauschbaren
Ausgabeziele. Alle aktuellen Spielgrafiken bleiben ausschließlich lesbar.

Namen mit Leerzeichen, Umlauten, `#` oder `%` bleiben Anzeigenamen;
interne Dateinamen werden nicht daraus konstruiert. CLI-Aufrufe erfolgen
als Argumentlisten, nicht durch Shell-Interpolation.

## Tatsächlicher Pipelinebestand

- Die Starterordner tragen `0-`, `1-`, `2-` und `3-` vor ihren Namen.
  `PyGameTools.py` erwartet für die Installation dagegen teils unnummerierte
  Ordner. Das ist ein bestehender Installer-Befund; es wurde nichts installiert.
- `PyImgColorMatch.DIRECTIONS` ist fest `N, NO, O, SO, S, SW, W, NW`.
  Die Farb-Referenzprüfung verlangt genau diese geordnete Referenzmenge.
- `save_template()` erzeugt schwarze L-Masken (alle Labels 0).
  Solche leeren Vorlagen sind keine bestätigten Materialmasken.
- FramReduce hat fest `FPS = 8`; die Frame-Auswahl ist davon unabhängig.
- Der Resolution-Schalter `--Textur` wird ausdrücklich als reserviert und
  nicht implementiert zurückgewiesen.
- Aus Dokumentation oder Canvas-Dateien wird kein ausführbarer Erfolg abgeleitet.

## Ausgeführte Ausgangsprüfungen

Python 3.11.2, vorhandene `.venv` mit pytest 8.4.2. Godot 4, Pillow und
PySide6 fehlen zu Beginn. Kein GUI-/Godot-Erfolg wird daraus abgeleitet.

| Prüfung | Ausgangsergebnis |
| --- | --- |
| `gh auth status --hostname github.com` | Angemeldet; flüchtige Konfiguration |
| `.venv/bin/python tools/control.py check` | 201 bestanden, 37 übersprungen, 2 fehlgeschlagen |
| Stilprüfung innerhalb des Gesamtchecks | 1.985 bestehende Befunde in 167 Dateien |
| Godot-Import/Headless | Godot fehlt; nicht ausgeführt |
| FramReduce-Starter `--help` | Exit 0, Standardframes 8/10/12/14 |
| PyGameTools `.tests` | 8 Collection-Fehler: Pillow fehlt |

Die zwei Python-Fehler betreffen fehlende Dateien
`docs/game/decisions/index.md` und
`docs/game/decisions/ADR-0008-achtteiliger-spielablauf.md` sowie deren Links.
Diese fachfremden Ausgangsfehler werden nicht mit erfundenen Entscheidungen
repariert. Nach Installation der geprüften Entwicklungsabhängigkeiten werden
die Pipeline-Tests in Paket 2 erneut ausgeführt.

## Schutz und Folgerungen

Vorher-/Nachher-SHA-256-Prüfung der vorhandenen PNGs, GIFs und Godot-Quellen
liegt außerhalb des Repositorys im temporären Prüflauf. Die neue
Ignore-Ergänzung schützt die verschobenen `greenhero`, `.pipeline-build`,
`.compare` und `media-*`-Ausgaben sowie lokale Studio-Kataloge.
Keine Importdateien oder Assets werden gelöscht oder neu erzeugt.
