# Projektweite Bildpipelines

Die Pipeline-Karten ergänzen den vorhandenen Projektkatalog, Canvas und
Job-Runner. Sie ersetzen keine Originalbilder und sind keine Diagnose-Demo.
Ein erfolgreicher Bildlauf besteht aus geprüften PNG-Dateien und gebundenen
Geometrie-/Timing-Metadaten. Künstlerische Freigabe und Godot-Bereitstellung
bleiben davon getrennt.

Der neue Skriptablauf mit einem importierbaren Skalierungspaket ist unter
[Skriptpakete und Asset-Ablage](SKRIPTPAKETE.md) beschrieben. Die folgenden
Grafik-/Farb-/Framevorlagen werden von mitgelieferten Python-Paketen bereitgestellt.
Parameter und optionale Bedienaktionen stammen aus deren Manifesten.

## Einstieg und Bedienung

1. Studio wie bisher über `python tools/control.py asset-manager run` starten
   und ein Projekt öffnen. Im Baum **Projekt und Verwendungen** oder im Canvas
   die oberste **Projektkarte** rechtsklicken. Alternativ die freie Canvas-Fläche
   rechtsklicken oder oben **Pipelines …** wählen.
2. **Neue Pipeline …**, **Pipeline aus Vorlage …** oder **Pipeline importieren …**
   wählen. Die Zahnradkarte liegt direkt unter dem Projekt, auf derselben Ebene
   wie **Projektweit**, und gehört ausschließlich diesem Projekt. Andere
   Projekte übernehmen ein Rezept nur durch ausdrücklichen Import einer Kopie.
   Im Baum und in der automatischen Canvas-Anordnung stehen Pipelines vor
   „Projektweit“. Bereits gespeicherte manuelle Kartenpositionen bleiben erhalten.
3. Die Karte doppelklicken. Links stehen Verarbeitungsschritte und Bildfluss,
   rechts die Eigenschaften des ausgewählten Schrittes. Einen Knotenanschluss
   auf den nächsten Schritt ziehen. Technische Verbindungen werden auf
   Eingangs-/Ausgangstypen, Mehrfachbelegung und Zyklen geprüft.
4. Schritte hinzufügen, aktivieren/deaktivieren oder entfernen. Deaktivierte
   Schritte behalten ihre Parameter und reichen nur typverträglich durch.
   **Speichern**, **Rückgängig/Wiederholen**, Strg+S/Strg+Z und der
   Speichern-/Verwerfen-Dialog gelten auch hier. Knotenpositionen liegen
   getrennt vom versionierten Rezept. Verschieben baut keine Bilder neu.
5. Bei einer Grafikpipeline unter **Projektprofile …** gewünschte Grafikstufen konfigurieren. Im Editor
   können Zielprofile ausdrücklich ausgewählt werden; ohne Auswahl gelten die
   Anforderungen des jeweiligen Assets. Deaktivierte Projektprofile sind
   nicht angefordert. Stabile Schlüssel bleiben erhalten; Anzeigenamen dürfen
   geändert und zusätzliche Profile ergänzt werden.
6. Unter **Zuweisungen …** einzelne Assets, vorhandene Typen/Fähigkeiten oder
   den Projektstandard auswählen. Priorität: explizites Asset vor Typregel vor
   Projektstandard. Gleichrangige Treffer sind ein sichtbarer Konflikt, keine
   automatische Verkettung. Eine Regel erfasst auch neue passende Assets,
   startet aber niemals selbst einen Auftrag. NPC ist eine eigene Vorlage;
   bestehende Figuren werden nicht umklassifiziert.
7. **Dry-run / Ausführen …** zeigt betroffene, ausgeschlossene und blockierte
   Assets sowie geplante Ausgaben. Erst die ausdrückliche Ausführung verarbeitet
   Arbeitskopien. Fortschritt, Ereignisse, Ergebnisstatus und Abbruch laufen
   über die vorhandene Auftragsverwaltung im Hintergrund.
   Einzelne Schritte lassen sich für die geprüfte Bildvorschau und über
   **Auftragsprotokolle …** für begrenzte Auszüge der Rohprotokolle auswählen.

Am einzelnen Asset führen **Pipeline / Farben**, **Varianten** und
**Bilder erzeugen …** in dieselben Dienste. Angezeigt werden wirksames Rezept,
Zuweisungsherkunft, Revision, Profile und lokale Abweichungen. Nur im Rezept
freigegebene Parameter dürfen lokal überschrieben werden. Eine organisatorische
Projektkante ist niemals eine Pipeline-Zuweisung oder ausführbarer Bildfluss.
Unter **Varianten → Ergebnisstatus prüfen (ohne Build)** wird der letzte
vollständige Ergebnisstand erneut gegen Dateien und aktuelle Anforderungen
geprüft: aktuell, veraltet, ungültig oder noch kein vollständiger Lauf.
Die Prüfung läuft im Hintergrund und erzeugt keine Bilder. Nach einem echten
Lauf aus dem Asset-Menü wird sie ebenfalls angestoßen. Die ältere allgemeine
Workflow-/Sichtabnahmeanzeige wird dadurch nicht als persönliche Freigabe gesetzt.

## Vorlagen und vorhandene Algorithmen

Eigene Farbprofile und gebundene Masken werden im Asset-Menü unter
**Pipeline / Farben → Masterreferenzen / Materialien / Masken …** verwaltet.
Im Rezept kann ein Farbschritt seine Ressourcen **aus diesem Asset** beziehen.
Der [Bedien- und Versionsvertrag](REFERENZEN_UND_MASKEN.md) beschreibt freie
Referenzen, Maskenrevisionen und die getrennte Sichtbestätigung.

| Vorlage | Tatsächliche Verarbeitung |
| --- | --- |
| Grafik-Assets | Comic- und Pixelprofile aus derselben Quelle, pro Frame skaliert |
| Spritesheets mit 8 Frames | Passende acht Quellframes gemeinsam beschneiden und in 4×2 anordnen |
| Spritesheets mit 16 Frames | Passende sechzehn Quellframes gemeinsam beschneiden und in 4×4 anordnen |
| Frame-Reduktion und Timing | Vorhandene Frames auswählen; keine Zwischenbilder erzeugen |
| Spritesheet-Farbverarbeitung | Wahlweise `soft`, `fixed` oder `material` |
| Source-Farbverarbeitung | Dieselben passenden Farbverfahren für Einzelbilder, keine Animationserzeugung |
| Leeres Rezept | Projektquelle als Ausgangspunkt für eigene Schritte/Verbindungen |

Fram8 und Fram16 sind Alternativen für passende Quellen, keine verpflichtende
Schrittkette. Die Adapter verwenden gemeinsame Funktionen der bestehenden
PyGameTools. Die CLI-Starter bleiben unverändert benutzbar. Studio übergibt
keine erfundenen CLI-Schalter und führt verschiebende Starter nicht auf
Originalen aus.

Die fünf übernommenen Profilidentitäten:

- `comic_high`: Faktor 1, unveränderte Frameauflösung.
- `comic_mid`: Faktor 0,5 relativ zum HD-Eingang.
- `comic_low`: Faktor 0,25 relativ zum HD-Eingang.
- `pixel_high`: längste Framekante höchstens 128 Pixel; bestehendes
  BOX-/vormultipliziertes Alpha-Verfahren, binäre Transparenz und standardmäßig
  höchstens 64 Palettenfarben ohne Dithering.
- `pixel_low`: Faktor 0,9 relativ zur tatsächlichen Pixel-High-Zelle;
  Nearest-Ableitung ohne neue Farbmischung. Aus 128 werden 115 Pixel.

Pixel High bleibt als interne Voraussetzung berechenbar, wenn nur Pixel Low
als Ausgabe angefordert ist. Zusätzliche Profile sind Studio-Profile; dadurch
unterstützt das vorhandene Godot-Grafikmenü noch keine beliebigen neuen Keys.

## Größen, Geometrie und Timing

Eine Größe ist entweder **Faktor** oder **maximale Kantenlänge**, niemals zwei
unabhängige Breiten-/Höhenfelder. Die Vorschau zeigt die resultierenden Maße.
Es gilt Downscale ohne automatische Vergrößerung. Faktoren müssen endlich und
größer als null, in diesem Modus höchstens eins sein. Maximale Kantenlängen
sind positive ganze Pixelzahlen bis 16384.

Für die maximale Kante `L` gilt `s = min(1, L / max(W, H))`. Beide Dimensionen
werden mit `s` multipliziert und für positive Werte deterministisch **half-up**
gerundet, mindestens auf einen Pixel. Das entspricht dem vorhandenen
CLI-Verfahren `floor(v + 0.5)`; Decimal vermeidet binäre Gleitkomma-Tiefehler.
Ganzzahlige Pixel können geringfügig vom idealen Seitenverhältnis abweichen.
Skalierung gilt für Frame-Zellen, nicht für die Gesamtbreite des Spritesheets.

Metadaten erhalten Raster, ursprüngliche Frameindizes, Profilkey, Quellrevision
und Quellhash, Anker, Crop-Offset/-Größe, logische Größe und Darstellungsmaßstab.
So bleibt die Figur trotz unterschiedlicher Bildauflösung gleich groß und am
gleichen logischen Ort. Die Bildprüfung bindet Metadaten an den PNG-Hash.

**Frames und FPS sind getrennt.** Bei 16→N gilt die bestehende Auswahl
`index(k) = floor(16 * k / N)`. Alle Richtungen benutzen dieselbe Vorschrift.
**Wiedergabe-FPS beibehalten** verkürzt bei weniger Frames die Dauer.
**Animationsdauer beibehalten** passt die FPS proportional an: 16 Frames bei
8 FPS und 8 Frames bei 4 FPS dauern beide zwei Sekunden. Quellenraster,
Quellframezahl und ausgewählte Framezahl bleiben unterscheidbar. Einzelbilder
haben weder Frame-Reduktion noch FPS/Loop-Einstellungen. Vorschau-FPS im
Ergebnisdialog sind vorübergehend und verändern weder Rezept noch PNGs.
Im Modus **Animationsdauer beibehalten** ist die gespeicherte FPS-Eingabe
deaktiviert: die Ausgabefrequenz wird aus der tatsächlichen Eingangsdauer
berechnet. Beim Zurückwechseln bleibt der frühere manuelle Wert erhalten.

## Farbe und Ressourcen

Die Standard-Grafikvorlage benötigt keine Materialmasken. Ein Farbschritt
wird bewusst ergänzt; unvollständige aktivierte Schritte blockieren den Dry-run.
Im Editor werden nur die Parameter des gewählten Farbmodus gezeigt:

- `soft`: das Referenzprofil im vorhandenen PyGameTools-Format, Stärke und
  maximale Farbdistanz. Andere, ähnlich benannte JSON-Farbprofile werden
  nicht stillschweigend umgedeutet.
- `fixed`: eine gültige feste Palette; exakte Zuordnung nach glatter
  Skalierung platzieren, da glatte Skalierung Mischfarben erzeugen kann.
- `material`: Materialprofil und zur Quelle gebundene Labelmaske.
  Maske, Raster, Quellhash, Labelwerte, Transparenz und Geometrie müssen passen.
  Labelmasken dürfen nicht wie normale Farbbilder interpoliert werden.

Für mehrere Quellen/Richtungen können mehrere gebundene Masken importiert
und bei Labelmaske **Nach Quellbindung (importierte Masken)** ausgewählt werden.
Der Dry-run sucht je Quelle genau eine passende Maske anhand ihrer eingebetteten
Quellhash-Bindung. Fehlende oder mehrdeutige Treffer blockieren. Ein ausdrücklich
gewählter einzelner Maskenverweis wird nicht heimlich durch einen anderen ersetzt.
Exakte Farbzuordnung vor einem späteren farbmischenden Schritt erfordert eine
erneute exakte Zuordnung danach; eine ungeeignete Reihenfolge wird blockiert.

Ressourcen werden ausdrücklich als geprüfte Kopien in den Projekt-Objektspeicher
übernommen. Rezepte speichern deren Hashes und Namen, keine privaten absoluten
Dateipfade. Projektpfeile ersetzen keine Ressourcenbindung.

## Cache, Aufträge und Originalschutz

Ein Dry-run friert Rezeptrevision, Profile, aktive Parameter, Quellen und
Werkzeug-/Erweiterungsversionen in einem Buildplan ein. Spätere Änderungen
schreiben alte Aufträge nicht um. Veränderte Werkzeuge erfordern einen neuen
Plan; sie werden nicht unbemerkt unter einem alten Hash ausgeführt.

Der vorhandene `BuildGraph` wird vom vorhandenen `BuildPlanner` geplant;
`JobService`, Supervisor und `BuildCache` bleiben die einzige Ausführungskette.
Jeder Auftrag erhält echte Dateikopien, keine veränderbaren Hardlinks.
Originale und historische Quellrevisionen bleiben unverändert. Arbeitsausgaben
liegen intern unter `.asset-studio/jobs/<Auftrag>/output`. Vollständige geprüfte
Läufe veröffentlichen ihre Bilder zusätzlich unter `Ergebnisse/<Profil>/`
im Ordner des jeweiligen Assets. Die Ablage folgt dessen Akt-/Kapitel-/Paket-
Besitz. Ergebnisse bleiben Ableitungen desselben Assets.

Fingerprints berücksichtigen aktive Eingaben/Parameter, Ressourcen,
Abhängigkeiten und Werkzeughashes. Layout, Anzeigenamen und Parameter
deaktivierter Schritte sind keine Bildinputs. Eine isolierte Änderung an
`comic_low` berechnet unabhängige Comic-/Pixelzweige nicht neu. Eine gemeinsame
Palette betrifft dagegen alle tatsächlich davon abhängigen Schritte.
Cache-Nutzung prüft Ausgabeliste, Größen, Hashes und Abhängigkeiten erneut.
Ein Exitcode null ohne gültiges PNG ist kein Erfolg. Unvollständige/abgebrochene
Läufe veröffentlichen keinen neuen vollständigen Ergebnisstand. Bestehende
Dateien werden nicht durch eine pauschale Ordnerbereinigung entfernt.

## Import, Export und eigener Python-Code

**Exportieren …** schreibt ein versioniertes JSON-Rezept oder ein Paket mit
deklarativen Ressourcen. **Pipeline importieren …** zeigt vor Übernahme
Schritte, Profile, Parameter, Ressourcen, Konflikte und fehlende Werkzeuge.
Die Übernahme erstellt neue Rezept-/Schrittidentitäten; interne Kanten werden
konsistent neu zugeordnet. Bestehende Rezepte werden nicht still überschrieben.
Ein Import startet keinen Build. Fehlende Ressourcen oder Erweiterungen lassen
einen sichtbaren, blockierten Entwurf zurück.

Original-Assets, Cache, Jobs, Zugangsdaten, lokale Freigaben und private absolute
Pfade gehören nicht in ein Pipeline-Paket. Zip-Pfade, Symlinks, doppelte Namen,
Schemas und Größen werden geprüft. Legacy-`.canvas`-Import übernimmt erkennbare
Karten/Layout und protokolliert bekannte Werkzeugzuordnungen, auch historische
Ordnernamen ohne Nummernpräfix. Visuelle Pfeile werden nicht automatisch
ausführbar; unklare Zuordnungen müssen bewusst geklärt werden.
Übernommene visuelle Legacy-Verbindungen erscheinen grau gestrichelt, getrennt
von technischen Kanten. Karten behalten ihre Beschriftungen und Informationen.
Rückgängig nach dem Import archiviert die neue Rezeptkarte; ergänzte stabile
Projektprofile und unveränderliche Ressourcen bleiben für andere Verbraucher
erhalten. Der Import entfernt keine fremden Daten.

Unter **Python-Erweiterungen …** Manifest und Python-Datei ausdrücklich
registrieren und anschließend die konkrete Codeversion freigeben. Bloßes
Öffnen des Projekts oder Anzeigen des Manifests führt keinen fremden Code aus.
Manifestparameter speisen dieselbe Eigenschaftenoberfläche; der registrierte
Adapter benutzt denselben Worker-/Timeout-/Abbruchablauf. Abhängigkeiten werden
geprüft, nicht automatisch installiert. Es gibt keine freien Shell-Befehle in
Rezeptparametern und keine ungefragten Netzwerkaufrufe.

**Ein Worker ist keine Sicherheits-Sandbox.** Nur ausdrücklich
vertrauenswürdigen Python-Code freigeben. Der v1-Bildvertrag erwartet ein
RGBA-Bild gleicher Geometrie zurück; beliebige Dateien, Shell-Prozesse oder
unbekannte Geometrieänderungen sind keine gültige Erweiterungsausgabe.
Das Beispiel unter `tools/AssetManager/examples/pipeline_grayscale/` zeigt
einen optionalen Graustufen-Schritt. Es wird nicht automatisch in Standardrezepte
aktiviert. Änderungen am Code/Manifest verlangen eine erneute Freigabe.

Der ergänzende [v2-Vertrag](SKRIPTPAKETE.md) erlaubt Bildgrößenänderungen und
gebundene Metadaten sowie ausdrücklich geöffnete Paketaktionen. Das importierbare
Skalierungsbeispiel liegt unter `tools/AssetManager/examples/pipeline_scale/`.

Die versionierten Austauschverträge liegen unter
`schemas/asset-studio/pipeline-{recipe,export,manifest}-v1.json`.
Ergänzende Dienstvalidierungen prüfen Graph, Profilbezüge und Dateiinhalte;
ein formal gültiges JSON-Schema allein ist keine Ausführungsfreigabe.

## Kompatibilität und Abnahme

Migration 6 erweitert den bestehenden SQLite-Katalog um die Pluginregistrierung.
Migration 7 hebt vorhandene Pipeline-Karten und projektweite Zuweisungsregeln
aus „Projektweit“ direkt unter das Projekt. IDs, Rezepte, Layouts, Asset-Zuweisungen
und eingefrorene Build-Snapshots bleiben erhalten; die Besitzänderung wird als
neue Revision protokolliert. Historische Revisionen bleiben unverändert.
Die vorhandene Migrationssicherung und Transaktionen bleiben erhalten. Fehlen Projektprofile,
werden die bisherigen fünf Schlüssel einmalig ergänzt. Asset- und Pose-IDs,
Quellen, FPS und bestehende Layouts werden nicht neu erzeugt. Unbekannte
Profilkeys werden nicht ersatzweise als `comic_high` verarbeitet.

Kein Teil dieser Integration ändert automatisch Godot-Produktionsassets oder
das Grafikmenü. Für einen späteren Godot-Export bleiben die benötigten Bild-,
Geometrie- und Timinginformationen verfügbar. Automatisierte Prüfungen ersetzen
keine persönliche Sichtabnahme. Der konkrete Prüflauf und verbleibende Befunde
werden im [Arbeitsplan](../plans/asset-studio-projektpipelines.md) dokumentiert.

Konkrete Grenzen dieser Version:

- Die sichere Prozessverwaltung bleibt wie bisher auf Linux mit `/proc`
  beschränkt; andere Betriebssysteme werden vor dem Auftrag abgewiesen.
- Höchstens 64 projektweite Profile und 128 Schritte je Rezept; ein
  Verarbeitungsschritt hat im v1-Erweiterungsvertrag einen Bildeingang und
  einen Bildausgang. Mehrere technische Zweige sind möglich, beliebige
  Mehrfacheingangs-/Dateiproduzenten noch nicht.
- Studio erzeugt PNGs mit Geometrie-/Timingmetadaten und eine gemeinsame
  animierte Vorschau. Separate GIF-/HTML-Dateien bleiben bei den vorhandenen
  CLI-Werkzeugen; Studio ruft keine erfundenen Starteroptionen auf.
- Die UI-Vorschau ist auf 64 Millionen Bildpixel und 256 Frames begrenzt.
  Der Worker-Timeout beträgt derzeit 300 Sekunden je Schritt.
- Dry-run/Ergebnisprüfung bleiben außerhalb des GUI-Threads; eine laufende
  Datei-/Hashprüfung wird nicht mitten im Lesezugriff unterbrochen. Beim
  Schließen wird ihr Abschluss abgewartet. Bildjobs selbst sind abbrechbar.
- Profil- und Zuweisungsdialoge besitzen ihre eigene Undo-Historie;
  gespeicherte Rezept-/Kartenänderungen nutzen die Canvas-Historie.
- Zusätzliche Studio-Profilkeys sind noch keine automatische Erweiterung
  bestehender Godot-Verbraucher. Es gibt keinen automatischen Produktions-Export
  oder eine automatische Sichtabnahme.

Für die Sichtprüfung reicht ein Testprojekt:

1. Grafikvorlage direkt unter dem Projekt anlegen, Karte öffnen, bewegen, speichern,
   Projekt neu öffnen; Karte und Einstellungen müssen erhalten bleiben.
2. Einer kleinen importierten Quelle zuweisen, Dry-run prüfen und wirklich
   ausführen. PNG-Ergebnisse/Profilmaße ansehen; Original muss unverändert sein.
3. Zwei Projektprofile deaktivieren und ein eigenes ergänzen. Keine deaktivierte
   Ausgabe darf als fehlgeschlagene Pflichtausgabe erscheinen.
4. Nur Comic Low ändern: der neue Dry-run muss unabhängige Ergebnisse
   wiederverwenden. Danach nur eine Karte verschieben: keine Bildneuberechnung.
5. Mit einem 16-Frame-Testsheet Framezahl und FPS getrennt verändern und beide
   Timingmodi vergleichen. Vorschau-FPS ändern, Dialog schließen: Rezept bleibt gleich.
6. Ein Paket exportieren und in ein anderes Testprojekt importieren. Die Kopie
   darf sich unabhängig ändern; fehlende Werkzeuge müssen sichtbar blockieren.
7. Einen längeren Lauf abbrechen. Kein neuer vollständiger Erfolgsstand darf
   erscheinen; Logs und bisherige Originale bleiben erhalten.
8. Optional das Graustufen-Beispiel registrieren: vor Freigabe blockiert, nach
   bewusster Freigabe echte Graustufenausgabe. Unbekanntem Code nicht vertrauen.
