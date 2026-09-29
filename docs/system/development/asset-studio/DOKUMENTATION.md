# Dokumentation direkt im Markdown-Bereich

[Asset Studio](index.md) · [Bedienbriefing](DARSTELLUNG.md) ·
[Umsetzung und Prüfergebnisse](../plans/asset-studio-markdown-bearbeitung.md)

Der Markdown-Bereich bleibt Teil der Python-Anwendung. Hauptfenster und
**Asset-Menü → Dokumentation → Dokumente & Anhänge** verwenden denselben Editor,
dieselben Dokument-IDs und den vorhandenen Dokumentdienst. Die automatische
Dokumentgenerierung bleibt unverändert. Dokumentinhalte lösen keine Builds,
Python-Ausführung oder Änderungen an Pipeline, Canvas und Asset-Freigaben aus.

## Bearbeiten und speichern

**MD** zeigt Markdown und erlaubt gezielte Bearbeitung. Einen Absatz, eine
Überschrift oder einen Codeblock anklicken: An derselben Stelle erscheint dessen
Quelltext. Die Eingabe bleibt während des Tippens aktiv. Beim Verlassen des
Abschnitts erscheint wieder die Darstellung. Tabellen verwenden einen Zelleneditor;
Aufgaben haben direkt bedienbare Checkboxen. Links und Medienaktionen beginnen
keine Absatzbearbeitung.

**Code** zeigt den vollständigen Markdown-Quelltext in Festbreitenschrift.
Der gewählte Modus bleibt beim Speichern und Dokumentwechsel erhalten.
Beide Ansichten arbeiten auf genau einem Entwurf. Ansicht, Scrollen, Medienladen,
Ausrichtung und Moduswechsel verändern weder Text noch Textrevision.
Auswahl und Leseposition werden soweit möglich wiederhergestellt.

**Rechtsklick** bietet Fett, Kursiv, Durchstreichen, Inline-Code, Überschrift,
Liste, Aufgabenliste, Zitat, Link, Bild, Tabelle und Codeblock. Die Textaktionen
verwenden die Auswahl; ohne Auswahl wird ein markierter Platzhalter eingesetzt.
Für eine Auswahl über mehrere gerenderte Blöcke eignet sich **Code**.
Auswahlen in Codeblöcken werden gegen versehentliche Textformatierung geschützt.
Neue Überschriften verwenden `#`; Einfügungen interpretieren keine Sprachangabe
als Befehl. Bei einer neuen Tabelle werden Spalten und Datenzeilen abgefragt.

**Strg+Z / Wiederholen** verwenden einen gemeinsamen Verlauf über MD und Code
hinweg. Formatierungs-, Einfüge- und Tabellenbefehle sind zusammenhängende
Bearbeitungsschritte. Escape in einer Tabellenzelle verwirft ausschließlich ihre
noch nicht bestätigte Eingabe.

**Speichern / Strg+S** schreibt Änderungen über den bestehenden Dokumentdienst.
Unverändertes Speichern erzeugt keine Textrevision. Vor Dokumentwechseln gilt
weiterhin **Speichern / Verwerfen / Abbrechen**. Eine neuere fremde Revision wird
nicht überschrieben; der lokale Entwurf bleibt bei einem Konflikt erhalten.
Generierte Dokumente bleiben auch bei Checkboxen, Tabellen und Dialogen geschützt.
Die bisherigen Regeln für automatisch gepflegte Abschnitte gelten weiter.

Unberührte Quelltextteile bleiben exakt erhalten, einschließlich Referenzdefinitionen,
Escapes, BOM und Zeilenenden. Nur strukturelle Tabellenänderungen dürfen den
betroffenen Tabellenblock neu schreiben. HTML oder Rich Text werden niemals
zurück in das Speicherformat konvertiert. Die bisherigen Dateiprojektionen und
Anhangsregeln bleiben maßgeblich; es gibt keine zusätzliche Dokumentverwaltung.

## Text, Listen und Code

Unterstützt werden Überschriften von `#` bis `######` und alternative Überschriften
mit `===` beziehungsweise `---`. Der Blockkontext unterscheidet die alternative
Überschrift von einer Trennlinie. Neue Absätze benötigen eine Leerzeile. Ein
gewöhnlicher Zeilenwechsel bleibt im selben Absatz; zwei Leerzeichen oder ein
Backslash am Zeilenende erzeugen einen sichtbaren Zeilenumbruch.

```markdown
# Titel
## Abschnitt

**Fett**, __auch fett__, *kursiv*, _auch kursiv_, ***beides***,
~~durchgestrichen~~ und `Inline-Code`.

Erste Zeile\
Zweite Zeile

\*Kein kursiver Text\* und \# keine Überschrift

> Zitat
>
> > Verschachteltes Zitat

- Eintrag
  - Untereintrag

3) Dritter Schritt
4) Vierter Schritt

- [ ] Offen
- [x] Erledigt
- [X] Ebenfalls erledigt

---
```

Listen erkennen `-`, `*`, `+`, nummerierte Marker mit `.` oder `)` sowie
eingerückte Fortsetzungen und Unterlisten. Der nummerierte Startwert bleibt
sichtbar. Checkboxen sind per Klick oder Tab/Leertaste bedienbar. Nur ihr Zustand
ändert sich im Text; Umschalten ist rückgängig zu machen und muss gespeichert
werden. In geschützten Dokumenten sind sie gesperrt.

Code wird eingerückt oder mit mindestens drei Backticks beziehungsweise Tilden
abgegrenzt. Der Abschluss benötigt dasselbe Zeichen und mindestens dieselbe
Länge. Inline-Code und Codeblöcke interpretieren darin enthaltenes Markdown nicht.
Sprachangaben wie `python`, `json`, `yaml`, `markdown`, `text` und unbekannte Namen
bleiben gültig. Die Darstellung bietet Festbreitenschrift, eigenen horizontalen
Überlauf und **Code kopieren** mit dem ursprünglichen Inhalt. Sprachabhängige
Syntaxfärbung und Programmausführung sind nicht Bestandteil dieser Erweiterung.

## Links, Abschnitte und interne Kurzlinks

```markdown
[Bedienbriefing](DARSTELLUNG.md)
[Zum Abschnitt](#text-listen-und-code)
[Webseite](https://example.org "Ergänzender Hinweis")
[Datei mit Leerzeichen](<https://example.org/NPC Beschreibung.md>)
[URL-kodiert](https://example.org/NPC%20Beschreibung.md)

[Zum Grafikprofil][grafik]
[grafik][]
[grafik]

[grafik]: DARSTELLUNG.md "Grafikprofil"

<https://example.org>
https://example.org/hilfe

[[NPC]]
[[dokumente/NPC.md]]
[[NPC#animationen]]
[[NPC|NPC-Beschreibung]]
[[NPC#animationen|Zu den Animationen]]
```

Referenzen gelten im ganzen Dokument, auch wenn ihre Definition weit entfernt
steht. Namen sind unabhängig von Groß-/Kleinschreibung und zusammengefasstem
Leerraum; die erste gültige Definition gewinnt. Nicht auflösbare Referenzen
bleiben Quelltext. Klammern und gültige Escapes in Zielen bleiben erhalten.
Automatische HTTP-/HTTPS-Links berücksichtigen abschließende Satzzeichen und
balancierte Klammern. Titel erscheinen ergänzend als Hinweis.

Einfacher Klick folgt einem Link in MD; in Code dient er der Texteingabe.
**Strg+Klick** kann dort einem erkannten Link folgen. Ziehen zur Textauswahl
navigiert nicht. Im Link-Kontextmenü stehen **Öffnen**, **Ziel kopieren**,
**Bearbeiten** und **Verknüpfung entfernen** zur Verfügung. Entfernen erhält den
sichtbaren Inhalt, auch ein darin enthaltenes Bild.

Interne Markdown-Dokumente öffnen innerhalb des AssetManagers. Vor Navigation
greift der Schutz ungespeicherter Änderungen. Ein genauer relativer Pfad hat
Vorrang vor einer Namenssuche. Namenssuche ohne Endung sucht Markdown-Dokumente;
mehrere Treffer benötigen eine Auswahl. Kurzlinks erzeugen weder Dateien noch
Projektbeziehungen. Maskierte Kurzlinks und Kurzlinks in Code bleiben Text.

HTTP-/HTTPS-Links benötigen eine Bestätigung vor dem Öffnen im Standardbrowser.
`mailto:` benötigt ebenfalls Bestätigung und öffnet nur das Mailprogramm.
Andere Protokolle werden nicht ungeprüft an das Betriebssystem weitergegeben.

Abschnittskennungen entstehen aus sichtbarem Überschriftentext: NFC, Kleinschreibung,
Leerraum als Bindestrich; Buchstaben, Ziffern, kombinierende Zeichen, `_` und `-`
bleiben erhalten. Andere Zeichen und äußere Bindestriche entfallen. Ein leerer
Name wird `abschnitt`. Kollisionen erhalten die nächste freie Endung `-1`, `-2`
usw., unter Berücksichtigung aller zuvor vergebenen Namen. **NPC Animationen**
wird beispielsweise `#npc-animationen`. **Abschnittslink kopieren** steht an
Überschriften bereit. Navigation scrollt zum Ziel und hebt es kurz hervor;
ein fehlender Abschnitt erzeugt einen Hinweis. Kennungen werden nicht in den
Quelltext geschrieben.

## Bilder und GIFs

```markdown
![Externes Bild](https://example.org/npc.png "NPC-Vorschau")
[![Vorschau](https://example.org/npc.png)](DARSTELLUNG.md)

![NPC-Vorschau][npc-bild]
[npc-bild]: bilder/npc.png "NPC"

![[bilder/npc.png]]
![[bilder/npc-idle.gif]]
![[bilder/pipeline.svg]]
```

Die Beispiele mit `bilder/` setzen entsprechende Dateien im eigenen Projekt
voraus. Der Bilddialog erzeugt denselben normalen Markdown-Bildverweis auch für
lokale Dateien. Referenzbilder können ebenfalls innerhalb eines Links stehen.
Bilder funktionieren in Absätzen, Listen, Zitaten und Tabellenzellen. Alternativtext
dient als zugängliche Beschreibung und Ersatzanzeige, nicht als verpflichtende
Bildunterschrift. Bei verlinkten Bildern steuert die innere Quelle die Anzeige;
erst ein gesonderter Klick folgt dem äußeren Ziel.

PNG, JPEG/JPG, statisches WebP, animiertes GIF und geprüfte statische SVG werden
anhand ihres Inhalts erkannt. Rasterbilder behalten ihr Seitenverhältnis und
werden in der normalen Darstellung höchstens in natürlicher Größe gezeigt.
Breite Bilder passen sich dem Container an. Transparenz erhält ein Schachbrett;
**Bildansicht** bietet Zoom, ohne die Quelldatei oder Pipeline zu verändern.

Die Medienleiste unterscheidet **noch nicht freigegeben**, **wird geladen**,
**angezeigt**, **pausiert**, **ausgeblendet**, **Quelle fehlt**, **Format nicht
unterstützt**, **Laden fehlgeschlagen** und **blockiert**. Sie zeigt Alternativtext
oder Quelle, eine Begründung und passende Aktionen wie **Erneut versuchen**,
**Quelle ändern**, **Zugriff erlauben** und **Ausblenden**.

GIFs spielen tatsächlich mehrere Frames mit ihren eigenen Zeiten und Wiederholungen
ab. **Pause / Fortsetzen** hält nach Möglichkeit die bisherige Position;
**Ausblenden** beendet Laden und Wiedergabe. **Animationen automatisch abspielen**
und **Reduzierte Bewegung** sind lokale Einstellungen. Reduzierte Bewegung startet
Animationen pausiert. Dokument- und Fensterschließen beenden Medienarbeit.
Bildergebnisse eines früheren Dokuments gelangen nicht in das aktuelle Dokument.
Nachladen verändert weder Fokus noch Textauswahl.

## SVG-Vorschau

Normale Bildverweise unterstützen sichere SVG-Dateien. Ein ausdrücklich mit
`svg` markierter Codeblock bietet zusätzlich **SVG-Vorschau**; erneutes Umschalten
zeigt wieder seinen kopierbaren, bearbeitbaren Code.

````markdown
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">
  <rect x="5" y="5" width="90" height="50" rx="8" fill="#5078a0"/>
</svg>
```
````

Die statische Vorschau unterstützt ViewBox, Größe, Gruppen, Transformationen,
Pfade, Grundformen, Füllung, Kontur, Deckkraft, einfache Farbverläufe, Text mit
lokalen Schriften und begrenzte interne Referenzen. Bereinigung erfolgt nur an
einer Vorschaukopie. Originaldatei und Codeblock bleiben unverändert.

Skripte, Ereignisse, `foreignObject`, Fremddokumente, externe Ressourcen, DTDs,
XML-Entitäten und aktive Stile sind gesperrt. Statische Stilattribute werden nur
aus einer erlaubten Auswahl übernommen. Zyklen, fehlende Referenzen, unbekannte
wesentliche Elemente und zu komplexe Inhalte erzeugen eine sichtbare Ablehnung.
Es gibt keine allgemeine HTML-Freigabe und keine zugesicherte SVG-Animation.

## Dateizugriff und Netzwerk

Relative Ziele beziehen sich auf den tatsächlichen Dokumentordner beziehungsweise
die vorhandene Dateizuordnung des Katalogs. `./` und `../` bleiben auf das Projekt
begrenzt; ein führender `/` bezeichnet dort die Projektwurzel. Ohne geöffnetes
Projekt wird keine Projektwurzel erfunden. Leerzeichen, Umlaute und URL-Kodierung
werden berücksichtigt; Pfade werden nur einmal dekodiert. Symbolische Links werden
abgelehnt, geänderte freigegebene Dateien müssen erneut geprüft werden.

Absolute externe Pfade und `file:` werden nicht automatisch geladen. Eine gezielte
Dateiauswahl gibt genau diese Datei mit geprüftem Inhalt frei. Sie erlaubt keinen
Ordnerzugriff. Solche Freigaben bleiben Anzeigezustand der Sitzung; nach erneutem
Start kann eine externe Verknüpfung wieder eine Auswahl benötigen. Projektanhänge
verwenden den bestehenden Anhangsdienst und dessen Integritätsprüfung.

Die Richtlinie steht oberhalb des Dokuments:

| Richtlinie | Wirkung |
| --- | --- |
| Nachfragen | Externe Bilder benötigen eine ausdrückliche Freigabe. Voreinstellung. |
| HTTPS-Bilder automatisch laden | Muss ausdrücklich aktiviert werden; gilt für öffentliche HTTPS-Ziele. HTTP bleibt bestätigungspflichtig. |
| Externe Bilder blockieren | Beendet laufende externe Abrufe und entfernt deren aktive Anzeige. |

Freigaben sind dokumentbezogen. Ein gezielt eingegebenes Bildziel gibt nur diese
Adresse frei. Weiterleitungen auf eine neue Herkunft oder von HTTPS nach HTTP
benötigen eine neue Freigabe. Lokale Netzwerke und Loopback benötigen eine eigene,
auf Herkunft und Dokument begrenzte Erlaubnis. Ein Cache erteilt keine Freigabe.
Indexieren, Suchen und Auflisten rufen keine Bilder ab.

Abrufe laufen außerhalb des GUI-Hauptablaufs, sind abbrechbar und prüfen TLS.
Sie übernehmen weder Browser-Cookies noch Zugangsdaten oder Referrer. URLs mit
Zugangsdaten werden abgelehnt. Geprüfte DNS-Adressen werden für die Verbindung
festgehalten. Daten werden nicht automatisch dauerhaft im Projekt gespeichert.

**Mediengrenzen …** erlaubt die Anpassung der anfänglichen Grenzen:

| Grenze | Voreinstellung |
| --- | --- |
| Übertragung je Bild | 16 MiB |
| Pixel je Frame | 32 Millionen |
| Gleichzeitige Abrufe je Medienfenster | 4 |
| Weiterleitungen | 5 |
| Inaktivität / gesamte Abrufdauer | 15 / 60 Sekunden, einschließlich DNS und Antwortkopf |
| Dekodierte Bilder und Animationsspeicher | 128 MiB gemeinsam in der Medienansicht |

Der Speicher wird vor dem Dekodieren reserviert. GIFs verwenden keinen unbegrenzten
Frame-Cache. Blockierte oder unvollständige Ressourcen bleiben mit Begründung
sichtbar. Ausblenden gibt ihren Speicher frei.

## Link- und Bilddialog, Zwischenablage

**Link einfügen** enthält Anzeigetext, Ziel und optionalen Titel sowie die Auswahl
eines internen Dokuments und seiner vorhandenen Abschnitte. Die Zielvorschau
öffnet nichts. Abbruch ändert keinen Text.

**Bild einfügen** bietet Projektbild, vorhandenen Anhang, gezielte Dateiauswahl,
URL, Alternativtext und Titel. Ein anklickbares Bild erhält ein getrenntes
**Linkziel**. **Vorschau ausdrücklich laden** löst die Vorschau aus; bloßes
Eingeben lädt nichts. Die Bildvorschau erteilt keine Erlaubnis für das Linkziel.

**Datei verknüpfen** erzeugt einen Verweis und lässt die Datei an ihrem Ort.
**Datei ins Projekt übernehmen** verwendet erst nach OK den vorhandenen Import-
und Anhangsweg. Es überschreibt keine gleichnamige Quelldatei. Referenzen auf
übernommene Dateien bleiben nach Speichern und Wiederöffnen gültig.

Text aus der Zwischenablage bleibt Text beziehungsweise Markdown. Bilddaten und
kopierte Bilddateien öffnen denselben ausdrücklichen Bilddialog wie Drag-and-drop.
Zwischenablagebilder werden erst nach Bestätigung übernommen; temporäre Vorschauen
werden bei Abbruch aufgeräumt. Temporäre Pfade werden nicht als dauerhafter
Markdown gespeichert. Dialoge kehren zur aufrufenden Eingabe zurück.

## Tabellen

```markdown
| Name | Faktor | Aktiv |
|:-----|-------:|:-----:|
| High | 1.0 | Ja |
| Medium | 0.5 | Ja |
| Low | 0.25 | Nein |
```

Kopf- und Trennzeile müssen gleich viele Spalten haben. Äußere `|` sind optional;
ein Bindestrich je Trennzelle genügt beim Lesen, neue Tabellen verwenden mindestens
drei. `:---`, `---:` und `:---:` bestimmen links, rechts und Mitte; ohne Doppelpunkt
gilt links. Quelltextpolsterung verändert keine Daten.

Zellen zeigen Fett, Kursiv, Durchstreichen, Inline-Code, normale und referenzierte
Links/Bilder sowie verlinkte Bilder. `\|` bleibt ein Zellinhalt, auch in Inline-Code.
Nur `<br>`, `<br/>` und `<br />` erzeugen einen sichtbaren Zellumbruch; andere
HTML-Tags bleiben nicht aktiver Text. Kürzere Zeilen erhalten leere Anzeigezellen.
Überlange Zeilen werden als prüfbedürftig mit vollständigem Quelltext gezeigt.
`001`, `1.0`, Datumsangaben und `=1+1` bleiben Textwerte.

- Doppelklick oder **F2** bearbeitet die aktive Zelle, auch eine Kopfzelle.
  Ein einfacher Klick auf einen Link öffnet ihn. Enter bestätigt; Escape verwirft
  nur die noch unbestätigte Änderung.
- **Tab / Shift+Tab** bestätigt und wechselt vor/zurück. Tab hinter der letzten
  Datenzelle kann eine neue Zeile ergänzen. **Shift+Enter** erzeugt einen Zellumbruch,
  der als `<br>` gespeichert wird. Eingegebene senkrechte Striche werden maskiert,
  vorhandene gültige Maskierungen nicht verdoppelt.
- Das Kontextmenü ergänzt Zeilen oberhalb/unterhalb, Spalten links/rechts,
  Ausrichtung, Zellformatierung und Link-/Bildaktionen. Griffe und `+` erscheinen
  bei Hover oder Fokus. Die bestehende ausdrücklich bediente Umordnung per Griff
  bleibt erhalten; es wird nicht automatisch sortiert oder umgeordnet.
- Entfernen nicht leerer Zeilen/Spalten zeigt die betroffenen Inhalte und verlangt
  eine Bestätigung. Kopfzeile und letzte Spalte bleiben geschützt.
- Mehrere Zellen lassen sich als tabulator-/zeilengetrennte Werte kopieren und
  einfügen. Überschreiben und Erweiterung zeigen vorab Zielbereich und Inhalt.
  Abbruch erhält die Tabelle; Bestätigen ist ein gemeinsamer Undo-Schritt.

Die Kopfzeile ist hervorgehoben, Zellgrenzen und Innenabstände bleiben sichtbar.
Lange Texte umbrechen, Bilder passen in ihre Zelle und breite Tabellen scrollen
horizontal. Geschützte Dokumente erlauben nur Auswahl, Kopieren, Navigation und
Anzeigeaktionen. Tabellenänderungen erteilen keine neuen Medienfreigaben und laden
vorhandene Bilder nicht pauschal erneut.

## Darstellung und Grenzen

Helles und dunkles Erscheinungsbild verwenden die bestehenden App-Einstellungen.
Links sind unterstrichen, Checkboxen per Tastatur erreichbar und Medienaktionen
benannt. Inhaltsausrichtung **Links / Mittig / Rechts** ist eine lokale Ansicht;
Code bleibt links, Tabellen behalten ihre eigenen Spaltenausrichtungen. Schrift-
und Darstellungsänderungen erzeugen keine Quelltextänderung.

Der bestehende Dokumentgrenzwert bleibt 1 MiB. Mehr als 200 gerenderte Blöcke
führen zu einer gekennzeichneten, verlustfreien Quelltextansicht. Tabellen mit
mehr als 50 Spalten oder 3.000 Zellen einschließlich Trennerzeile sowie ungültige
Tabellen bleiben vollständig über **Code** bearbeitbar. Diese Ersatzansichten
sind ausdrücklich keine vollständige gerenderte Darstellung.

Die SVG-Vorschau begrenzt Struktur auf 4.096 Elemente, Tiefe auf 32 und expandierte
Referenzen auf 16.384 Schritte. Umfangreiche Geometrie wird begrenzt; die
Vorschaurasterung nutzt höchstens 2.048 × 2.048 Pixel. GIFs mit mehr als 10.000
Frames oder Frames außerhalb ihrer geprüften Bildfläche werden abgelehnt.
Ein Speicherlimit kann ein ansonsten unterstütztes Bild blockieren.

Nicht neu unterstützt werden ausführbares HTML, Tabellenformeln, verbundene oder
verschachtelte Tabellen, Audio/Video, beliebige Browser-SVG-Funktionen, Mermaid,
eine vollständige mathematische Formelsprache oder Plugins. Unbekannte Syntax
bleibt im Original erhalten. Bildschirmleser und native Browser-/Mailübergabe
auf sämtlichen Desktop-Betriebssystemen benötigen gesonderte praktische Abnahme;
die vorhandenen Qt-Prüfungen sind im Arbeitsplan ausdrücklich abgegrenzt.

Die Erweiterung nutzt die bereits gebundenen Bibliotheken `markdown-it-py==4.0.0`,
PySide6 und Pillow. Es wurden keine zusätzlichen Laufzeitabhängigkeiten ergänzt.
Konkrete Quelltextfixtures und erwartete Ergebnisse stehen in den
[Abnahmefixtures M01–M25](../../../../tools/AssetManager/tests/fixtures/markdown/README.md).
Der [Arbeitsplan](../plans/asset-studio-markdown-bearbeitung.md) enthält den
Anforderungsstatus, ausgeführte Prüfungen und verbleibende praktische Grenzen.
