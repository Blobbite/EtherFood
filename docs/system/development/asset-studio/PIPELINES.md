# Projektzuordnung und Pipelineverarbeitung

[Asset Studio](index.md) · [Python und aktuelle Dateien](SKRIPTPAKETE.md) ·
[Arbeitsplan und tatsächliche Prüfungen](../plans/asset-studio-zwei-editoren-und-automatik.md)

## Zwei Editorbereiche

Ganz links stehen **Projekt** und **Skripte & Pipelines**. Direkt daneben bleibt
die Bereichsnavigation an derselben Stelle. Strukturspalte und Arbeitsfläche
folgen rechts davon. Der Wechsel erhält die zuletzt geöffnete Ansicht und
Entwürfe. Beim tatsächlichen Verlassen einer bearbeiteten Datei gelten
Speichern, Verwerfen und Abbrechen; Abbrechen ist voreingestellt.

| Editor | Bereiche |
| --- | --- |
| Projekt | Projekt-Canvas, Aufgaben-Kanban, Notizen, Dokumentation & Anhänge, Suche |
| Skripte & Pipelines | Pipeline-Editor, Python-Editor, Suche |

Der Pipeline-Editor zeigt zunächst **Status · Pipeline · Verwendungen · Aktueller
Stand**. Bearbeiten öffnet den Canvas an derselben Arbeitsposition; **Übersicht**
führt zur Tabelle zurück. Parameter erscheinen beim ausgewählten Knoten unter
dem Canvas. Eine dauerhafte Karteneigenschaften-Spalte gibt es nicht mehr.

**Godot bereitstellen** bleibt deaktiviert unmittelbar links von Einstellungen.
Einstellungen enthält Darstellung und Tests. Aufgaben-Kanban, Notizen,
Markdown-Bearbeitung und Anhänge sind eigenständige Projektinhalte geblieben.
Die Dokumentationsstartseite ist über die Dokumentationsnavigation erreichbar.

## Definition erstellen, im Projekt verwenden

1. **Skripte & Pipelines → Pipeline-Editor → Neue Pipeline**: Namen eingeben und
   anlegen. Dafür wird kein Asset benötigt.
2. Eigene Python-Skripte anlegen oder ausdrücklich importieren. Ein Skript aus
   der Struktur auf den Canvas ziehen. Dies erstellt einen referenzierenden
   Knoten; mehrere Knoten dürfen dasselbe Skript verwenden.
3. Eingänge, Skripte und Folder über die Anschlüsse verbinden. Benannte Ports
   werden in der kompakten Bearbeitung gewählt; Parameter am Knoten einstellen.
4. **Speichern** aktualisiert die aktuelle Ablaufdatei. **Prüfen** führt einen
   Dry-run aus. Ein gültiger Ablauf ohne Verwendung ist prüfbar und freigebbar.
5. Im Projekt **Rechtsklick → Pipeline verwenden** wählen. Die vorhandene
   Definition auswählen und Eingabebereiche zuordnen.

Eine **Definition** enthält Skripte, interne Verbindungen, Parameter, Eingänge
und Folder. Eine **Verwendung** besitzt ihre eigene ID, verweist auf die
Definition und enthält Eingabezuordnungen, Ergebnisverbindungen, Reihenfolge
und Pausenzustand. Es entstehen keine versteckten Definitionskopien.

Einfachklick wählt die Verwendung im Projekt aus. Doppelklick bleibt dort.
Nur **Rechtsklick → Pipeline bearbeiten** wechselt ausdrücklich zum passenden
Pipeline-Canvas. Ein Projekt-Suchtreffer fokussiert die Projektverwendung.

Das Entfernen einer Karte entfernt ausschließlich die Verwendung. Gemeinsame
Definition und Skripte bleiben bestehen. Vor Änderung beziehungsweise Entfernen
einer gemeinsam verwendeten Definition werden ihre Verwendungen genannt.

## Eingaben und Reihenfolge

Ein zugeordnetes Asset liefert seine aktuellen registrierten Quellen. Ein Akt,
Kapitel oder anderer zulässiger Bereich liefert passende aktive Assets seiner
fachlichen Unterstruktur einschließlich Asset-/Paketverwendungen. Die
Projektwurzel steht für alle passenden aktiven Asseteingaben. Mehrere Verweise
auf dieselbe Assetidentität werden innerhalb einer Verwendung dedupliziert.
Archivierte Inhalte und Inhalte unter archivierten Besitzern bleiben ausgenommen.

Dies ist keine Suche nach beliebigen Dateien im Projektordner. Historische
Quellrevisionen, Datenbank, `.tools`, Sicherungen, Papierkorb und Ergebnisse sind
keine neuen Originaleingaben. Eine `.png`-Endung beweist kein Spritesheet;
Bildinhalt, Raster, Framezahl und Timing müssen zum deklarierten Eingang passen.
Der Dry-run unterscheidet passende, nicht passende und fehlerhafte Quellen.
Ohne passende Quellen zeigt die Übersicht **Keine passenden Eingaben**.

Nur eine ausdrückliche Ergebnisverbindung **PA → PB** gibt Daten weiter. Ausgang
und kompatibler Eingang werden benannt. PB erhält die verbundenen Ergebnisse,
keinen stillen Rückgriff auf Originalquellen. Mehrfachanschlüsse benötigen eine
entsprechende Deklaration. Selbstverbindungen, Kreise, widersprüchliche
Quellen-/Ergebniszuordnungen und falsche Anschlüsse werden abgewiesen.

PA verarbeitet zunächst die gesamte gewählte Auswahl. Erst nach erfolgreicher
Veröffentlichung dieser Phase beginnt PB. Asset-, Posen- und Quellherkunft
bleiben an den Ergebnissen. Unverbundene Ketten folgen ihrer gespeicherten
Reihenfolge. **Reihenfolge: nach oben/unten** ändert diese fachliche Reihenfolge;
freies Verschieben, Zoom und automatische Anordnung ändern sie nicht.

## Folder und Ergebnisse

Folder sind Ausgabebausteine im Pipeline-Canvas. Sie wählen **keine**
Projekt-Eingabebereiche. Ein Folder benennt einen verbundenen Ausgang und einen
relativen Zielordner. Standard ist die Ablage beim jeweiligen Asset:

```text
<Asset>/Ergebnisse/<Verwendungs-ID>/<Folder-Ziel>/…
Ergebnisse/Projekt/<Verwendungs-ID>/<Asset-ID>/<Folder-Ziel>/…
```

Die zweite Form entsteht nur durch die ausdrückliche gemeinsame Projektablage.
IDs und Inhaltskennungen verhindern Kollisionen. Mehrere Ausgänge können
verschiedene Folder besitzen. Der Dry-run zeigt Zielstruktur und noch offene
Platzhalter. Ohne notwendiges Ausgabeziel wird nicht veröffentlicht.

Skripte schreiben zunächst in einen kontrollierten Laufbereich. Vollständige
Ergebnisse werden auf Vertrag, Hash, tatsächlichen Typ und Bildmetadaten geprüft
und erst danach über das Dateijournal veröffentlicht. Elternpfade, absolute
Ziele, Symlink-Auswege und das Überschreiben geschützter Quellen sind gesperrt.
Ein Folder verschiebt keine Assetkarte und ändert keinen Besitzer.

PA- und PB-Ergebnisse bleiben getrennt auffindbar. **Asset-Menü → Varianten**
prüft ihre Aktualität. Generierte Ergebnisgalerien verwenden die jeweilige
Verwendungs-ID; bestehender eigener Markdown-Text bleibt erhalten.

## Prüfen, Freigeben und Automatik

| Ampel | Bedeutung |
| --- | --- |
| Gelb | Neu, importiert, übernommen oder ausführungsrelevant geändert; Prüfung/Freigabe nötig |
| Rot | Konkreter Prüf-, Eingabe- oder Verarbeitungsfehler; Ursache wird angezeigt |
| Grün | Aktueller ausführbarer Gesamtstand geprüft und ausdrücklich lokal freigegeben |

Farbe, Symbol und Text gehören zusammen. **Aktueller Stand** zeigt davon getrennt
Wartet, Läuft mit Fortschritt, Aktuell, Pausiert oder Keine passenden Eingaben.
Grün allein behauptet weder eine laufende Verarbeitung noch vorhandene Bilder.

**Prüfen** kontrolliert Dateien, Syntax, Imports/Bibliotheken, Parameter,
Anschlüsse, Graph, Eingabeauswahl und Ausgabeziele. Es startet keine Verarbeitung,
installiert nichts und veröffentlicht keine Ergebnisse. Sein Prüfstatus darf
lokal gespeichert werden. Erst **Freigeben** erlaubt den geprüften Stand.
Der ausdrückliche Python-Testlauf ist davon getrennt und veröffentlicht nichts.

Die Automatik arbeitet nur während das Projekt geöffnet ist. Sie läuft seriell
außerhalb des GUI-Threads. Die erste Freigabe verarbeitet vorhandene passende
Eingaben ohne gültiges Ergebnis. Weitere Läufe berücksichtigen nur relevante
Änderungen und notwendige Folgeschritte. Inhaltshashes, relevante Metadaten,
Code, Hilfsdateien, Bibliotheksbestand, Parameter und Vorgängerergebnisse bilden
den Fingerprint. Gleiche Bytes nach erneutem Speichern erzeugen keinen Neulauf.
Beschädigte oder fehlende Ergebnisdateien sind kein Cachetreffer.

Bekannte Quellen und Werkzeugdateien werden beobachtet; schnelle Ereignisse
werden gebündelt. Externe Änderungen aktueller Quellkopien werden erst geprüft
und dann als neue unveränderliche Quellrevision übernommen. **Aktualisieren**
stößt den Abgleich ausdrücklich an. Eigene Ausgaben werden nicht zu Eingaben.

Code-/Hilfsdatei-/Parameter-/Folderänderungen benötigen neue Prüfung und
Freigabe. Eine geänderte Projektzuordnung benötigt eine neue Planprüfung,
keine erneute Freigabe unveränderten Codes. Nach Korrektur eines Eingabefehlers
kann derselbe freigegebene Code weiterarbeiten.

**Automatik pausieren/fortsetzen** verhindert beziehungsweise erlaubt neue
Starts. **Abbrechen** beendet einen laufenden Durchgang kontrolliert. Bei
Projektwechsel oder Schließen wartet die Oberfläche auf das sichere Ende.
Fehlerhafte unveränderte Fingerprints werden nicht endlos wiederholt;
**Erneut versuchen** oder eine relevante Korrektur ermöglicht einen neuen Versuch.
Abhängige Schritte bleiben blockiert, unabhängige gültige Ketten dürfen weiterlaufen.

Ein Start friert aktuelle gespeicherte Eingaben, Skripte und Hilfsdateien ein.
Änderungen währenddessen gelten erst für den nächsten Durchgang. Vor
Veröffentlichung wird der wirksame Stand erneut geprüft; ein veralteter Lauf
wird nicht als aktuelles Ergebnis ausgegeben.

## Archiv und Papierkorb

Die untere Strukturablage trennt **Archiv** und **Papierkorb**, auch für
Verwendungen sowie Skripte/Pipelines. Archivieren macht inaktiv und hat kein
Ablaufdatum. Entfernen ist nach Bestätigung für exakt **30 × 24 Stunden** ab
UTC-Entfernungszeit wiederherstellbar. Angezeigte Termine verwenden lokale Zeit.
Abbrechen ist in der Bestätigung voreingestellt. Entf im Canvas verwendet
dieselbe Entfernung; in Texteditoren bearbeitet Entf weiterhin Text.

Wiederherstellen ist als Kontextaktion oder Drag-and-drop an ein gültiges Ziel
möglich. Wiederherstellung und neue Zuordnung bilden einen Undo-Schritt. Ein
ungültiges Ziel lässt den Ausgangszustand bestehen. Unabhängig archivierte
Unterobjekte werden nicht mitaktiviert. Bei einer Verwendung bleibt das
Original unverändert; bei einem Original zeigt die Bestätigung auch betroffene
Inhalte und Verwendungen.

Beim Öffnen und während des Betriebs bereinigt die App fällige Inhalte. Sie
beendet vorher eine betroffene laufende Verarbeitung. Gelöscht werden nur
zugehörige verwaltete Dateien, Datensätze und nicht mehr benötigte Revisionen.
Gemeinsame Dateien und fremde Dateien bleiben erhalten. Nach Bereinigung wird
kein Undo zur Wiederherstellung gelöschter Inhalte angeboten. Eine geschlossene
App löscht nichts; getrennte Sicherungen sind kein App-Papierkorb.

## Suche, Demo und Übernahme

Beide Suchansichten öffnen tatsächliche Objekte. Projekt-Suche umfasst Inhalte,
Assets, Aufgaben/Issues, Notizen, Dokumente und Verwendungen. Die Werkzeugsuche
umfasst Skripte und Definitionen einschließlich geeigneter Dateiinhalte.
Archiv und Papierkorb sind ausdrücklich wählbare Suchzustände.

Ein neues Projekt besitzt **0 Skripte und 0 Pipelines**. Nur
**Einstellungen → Tests → Demo anlegen** ergänzt die synthetischen Beispiele.
Wiederholung erkennt bereits angelegte Demoinhalte. Die Beispielpipelines
starten Gelb und laufen erst nach Prüfung, Freigabe und gültiger Zuordnung.

Die Bestandsübernahme sichert Katalog und verwaltete Dateien vor dem Rückbau.
Unterschiedliche gebundene Skriptfassungen bleiben zunächst eigene Skripte.
Wirksame alte Prioritätszuordnungen werden übernommen; unklare Fälle bleiben
sichtbar inaktiv. Alte Freigaben gelten nicht automatisch. Historische Ergebnisse
und Herkunftsbelege werden gesichert übernommen, bevor ausschließlich alte
Auftragsdaten und Ausführungswege entfernt werden. Details und tatsächliche
Prüfergebnisse stehen im verlinkten Arbeitsplan.

## Grenzen

Der kontrollierte Prozessabbruch benötigt derzeit Linux mit `/proc`.
Windows/macOS-Ausführung ist nicht abgenommen. Verwaltete Python-Umgebungen
sind keine Sicherheits-Sandbox. Godot-Bereitstellung bleibt deaktiviert.
JSON-Felder für Parameterbeschreibungen, zusätzliche Eingänge und Ressourcen
sind technische Bearbeitungshilfen; es gibt keinen allgemeinen Regeleditor.
Für die aktuelle Abnahme gilt ausschließlich der dokumentierte Teststand,
nicht die historischen Sichtprüfungsberichte.
