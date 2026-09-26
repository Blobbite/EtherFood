# Projektbrief — EtherFood Asset Studio

Status: **Zielentwurf für die Implementierung**, nciht Beschreibung einer schon fertigen Anwendung.
Grundlage: die Anforderugnen des Nutzers in dieser Unterhaltung und die beigefügten PyGameTools-/Strukturunterlagen. Stand des Planpakets: 26.09.2026.

## Gewünschtes Ergebnis

Eine lokale Python-Desktop-Anwendung verbindet die Planung von EtherFood mit Asset-Verarbeitung, Dokumentation, Versionierugn und Godot-Freigabe. Der Nutzer bedient Karten, Assets und Entscheidungen. Die Anwendung verwaltet Arbeitsdateien und reproduzierbare Verarbeitungsschritte.

Das Dashboard besitzt ganz oben einen projektweiten Rahmen für Held, allgemeine Effekte, Hintergründe, Gestaltungsregeln und Grunddokumente. Darunter stehen Akte in ihrer Reihenfolge. Akte enthalten Kapitel; Kapitel verknüpfen NPCs, Mobs, Umgebungen, Pakete, Aufgaben und freie Nebenkarten. Neue Akte, Kapitel, Karten und Dokumente sind direkt dort anlegbar.

Der Canvas bietet aufklappbare Gruppen und erkennbare Verbindungen. Daneben bleibt eine Baum-/Listenansicht verfügbar. Ein grafischer Knoten ist keine Dateikopie; 200 Varianten einer Heldenpose werden im Asset-Menü geprüft, nciht als 200 Projektkarten dargestellt.

## Die drei Arten von Beziehungen

**Gehört zu:** organisatorische Struktur von Projekt, Akt, Kapitel und Karten. **Verwendet:** ein Kapitel nutzt einen schon vorhandenen Helden oder ein Paket. **Benötigt vorher:** eine echte Voraussetzung für eine Aufgabe oder einen Verarbeitungsschritt.

Die Akt-Reihenfolge ist nciht automatsich eine Sperre für parallele Arbeit. Canvas-Koordinaten bestimmen weder Dateipfade noch Ausführungsreihenfolgen. Ein globaler Held hat eine Asset-Identität, auch wenn zehn Kapitel ihn nutzen.

## Animierter Arbeitsweg

1. Asset anlegen: Typ, globaler/akt-/kapitelbezogener Besitzer, Posen und tatsächliche Richtugnen festlegen. Der Held nutzt acht Richtugnen; andere Assets können weniger benötigen.
2. Source-Einzelbilder zuordnen und erhalten. Die Animation entsteht ausdrücklich im vorhandenen externen Animationstool.
3. Fertige Spritesheets importieren. Der typische waagerechte Streifen hat 16 Frames und technisch das Raster `16x1` (Spalten × Zeilen).
4. Die Masterreferenz für die Farben auswählen. Für Greenhero wird die bekannte Acht-Stand-Richtungs-Vorlage angeboten; neue Assets können explizit andere Referenzen wählen.
5. Materialien festlegen, Masken vorschlagen lassen, unklare Bereiche korrigieren und Masken bewusst abnehmen. Vorschlagserstellung und semantische Bestätigung sind getrennt.
6. Farbkorrektur automatsich ausführen; danach Frame-Stufen und Grafikstufen ableiten. Die fünf Frame-Stufen lauten `8, 10, 12, 14, 16`; die Grafikprofile heißen `comic_high`, `comic_mid`, `comic_low`, `pixel_high`, `pixel_low`.
7. Im Asset-Menü Pose, Richtung, Grafik und Frames beliebig kombinieren. Original, korrigiertes Ergebnis und eine vorherige Version vergleichen. Fehler direkt mit präziser Fundstelle erfassen.
8. Einen konkreten Kandidaten einfrieren, in Godot-Testbereiche bereitstellen und dort technisch sowie manuell prüfen.
9. Exakt die geprüfte Version freigeben und in den regulären Spielbereich übernehmen. Erst nach erfolgreicher finaler Prüffung die zugehörigen Testkopien aufräumen.

Eine Pose mit acht Richtugnen und 5 × 5 Stufen besitzt 200 logische Varianten. Die Anzahl gehört in den Vollständigkeitsprüfer, nciht in die manuelle Ordnerpflege.

## Statischer Arbeitsweg

Ein Tempelpaket kann Boden, Decken, Säulen und weitere Bauteile enthalten. Es hat dieselbe Verwaltugn, Dokumentation, Versionierugn und Freigabe, aber keine Animations- oder Framepflicht. Seine Grafikstufen werden automatsich berechnet. Gemeinsamer Maßstab, Anker und gegebenenfalls Kachelanschlüsse gehören zu seinen Prüfregeln.

Ein globaler Effekt ist nciht automatsich statisch. Die Verarbeitung folgt dem Inhaltstyp, nciht dem Akt-Scope. Neue Typvorlagen sollen hinzukommen können; neue Algorithmen müssen dennoch implementiert und getestet werden.

## Dokumentation und Verwaltungsfunktionen

Jede Karte kann Briefing, Anforderugnen, Notizen, Entscheidungen, Anhänge, Aufgaben und Befunde erhalten. Technische Berichte werden aus echten Quellen-, Profil-, Build- und Prüfdaten erzeugt. Automatische Berichte überschreiben keinen selbst geschriebenen Text. Projekt-, Akt-, Kapitel- und Asset-Dokumentation kann als Markdown/HTML-Paket exportiert werden.

Gesucht werden nciht nur Namen, sondern Arbeitszustände: fehlende Quellen, wartende Animation, offene Masken, veraltete Builds, fehlgeschlagene Tests, ausstehende Sichtprüfung und noch vorhandene Testkopien.

## Verbindliche Grenzen

Die Anwendung erzeugt keine neuen Originalanimationen. Ein fehlendes Sheet bleibt fehlend. Eine korrekte Material-ID ist noch keine bewiesene richtige Haar-/Lederzuordnung. Ein erfolgreicher Import ist noch kein bestandener Godot-Test. Ein Test ist noch keine manuelle Freigabe. Eine Freigabe ist noch keine aktive Spielversion.

Originale, eigene 8/10/12/14-Frame-Animationen und bestätigte Kandidaten bleiben geschützt. Die drei benannten Bereiche `EtherFood_Workspace`, `EtherFood_AssetVersions` und `EtherFood` werden über konfigurierbare Wurzeln angebunden, nciht durch einen ungeprüften Komplettumbau ersetzt.

## Technische Planentscheidungen — keine behaupteten Bestandsfunktionen

Python/PySide6, ein unabhängiger Anwendungskern, lokale SQLite-Metadaten, portable JSON-/Markdown-Snapshots, sichere Dateiablage und Prozessadapter sind Entscheidungen dieses Implementierungsplans. Der Paketcode wird nach Bestandsprüfung bei der PyGameTools-Codebasis ergänzt; ein neues Repository wird nciht vorausgesetzt.

Die tatsächliche Python-/Godot-Version, Git-Grenze und spielseitige Ressourcenschnittstelle werden in T001 und T035 überprüft. Konkrete Masterfarben, Materiallabels und künstlerische Abnahmen kommen aus realen Quellen und Nutzerentscheidungen, nciht aus erfundenen Beispieldaten.
