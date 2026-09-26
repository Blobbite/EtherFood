# Bestandsquellen und belegte Grenzen

Diese Auszüge stammen aus den vom Nutzer hochgeladenen Datein. Sie wurden für dieses Planpaket nur ausgewählt und mit ursprünglichen Dateizeilen versehen, nciht als Programme ausgeführt. Die vollständigen Originaluploads werden nciht dupliziert.

Der Upload ist ein zusammengefügter Quell-/Dokumentationsdump, kein vollständiger nachweislich lauffähiger Checkout. Historische Testzahlen und Dateibaum-Einträge sind keine in dieser Sitzung ausgeführten Prüfungen. Neu geplante Funktionen stehen im Projektbrief und in den Aufgaben.

| ID | Quelle im Paket | Originaldatei / Zeilen | Relevanz |
| --- | --- | --- | --- |
| Q01 | [FramReduce Bestand](Q01_FramReduce_Bestand.md) | `allsummary(1).md`: 1342–1471, 1211–1251 | Frame-Stufen, Raster, feste 8 FPS, Skipverhalten und technische Berichte. |
| Q02 | [Resolution Bestand](Q02_Resolution_Bestand.md) | `allsummary(1).md`: 4377–4712 | Grafikprofile, Einzelbilder, HTML-Vergleiche, Palettenbeschränkung und reservierter Texturmodus. |
| Q03 | [Starter Bestand](Q03_Starter_Bestand.md) | `allsummary(1).md`: 3–19, 474–490 | Vorhandene Fram16-/Fram8-Starter und ihre Zielraster. |
| Q04 | [Farbpipeline Bestand](Q04_Farbpipeline_Bestand.md) | `allsummary(1).md`: 7386–7712 | Aktueller dokumentierter Farbvertrag: soft/fixed/material, Masken, Profile und Schreibregeln. |
| Q05 | [SourceColor Bestand](Q05_SourceColor_Bestand.md) | `allsummary(1).md`: 11864–11964 | Einzelbild-Farbkorrektur ohne Animationserzeugung; keine automatische Materialerkennung behauptet. |
| Q06 | [Gemeinsame Schreibregeln](Q06_Gemeinsame_Schreibregeln.md) | `allsummary(1).md`: 11660–11845 | Schreibprüfung und gemeinsamer Controller einschließlich Verschieben direkter Quellen nach PixelEng. |
| Q07 | [Workspace Skizze](Q07_Workspace_Skizze.md) | `Eingefügtes Markdown.md`: 1340–1449 | Vorgeschlagener Workspace → AssetVersions → Godot-Test → Freigabe → Runtime-Ablauf. |
| Q08 | [Referenzauswahl Bestand](Q08_Referenzauswahl_Bestand.md) | `allsummary(1).md`: 9028–9064 | reference_files: feste Richtungsprüfung im existierenden Code. |
| Q09 | [Masken Profilregeln Bestand](Q09_Masken_Profilregeln_Bestand.md) | `allsummary(1).md`: 9636–9805, 8216–8290, 7100–7109 | Feste acht Profilreferenzen, Maskenmetadaten und dokumentierter offener Sichtstatus; historischer Fortführungstext gekennzeichnet. |

## Nicht als schon umgesetzt behandeln

Freie Referenzmengen sind eine Erweiterung: der Bestand enthält Acht-Richtungs-Prüfungen. Maskenvorlagen sind noch keine fertigen automatischen Materiallabels. Der Texturmodus ist reserviert. Die sichere Godot-Integration, Projektverwaltung, Canvas-GUI und Freigabedatenbank werden mit diesem Plan erst entwickelt.

Die Farb-README beschreibt vorhandene `fixed`-/`material`-Funktionen; der ältere Fortführungsprompt ist im Upload selbst ausdrücklich als historischer Vorzustand markiert. Deshalb wird nciht aus seiner alten Optionsliste auf den heutigen dokumentierten Vertrag geschlossen.

Absolutpfade und konkrete Repository-Grenzen sind im echten Checkout zu prüfen. Der Quellenkopf nennt PyGameTools innerhalb `EtherFood_AssetVersions/tools`, nciht automatsich ein separates Repository.
