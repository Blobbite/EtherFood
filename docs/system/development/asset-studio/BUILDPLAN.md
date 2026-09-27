# Buildplan, Cache und Änderungsfolgen (T018)

**Buildplan …** in der Toolbar oder **Buildplan / Dry-run …** im Asset-Menü
öffnet dieselbe Planung. Der Asset-Modus liest gespeicherte Anforderungen,
aktive Originalrevisionen und deren tatsächliche Bytes. Er zeigt die
Variantenanzahl und für jeden technischen Schritt einen nachvollziehbaren Grund.
Ungespeicherte Formularänderungen gehören noch nicht zu diesem Entwurf.

Ein **Dry-run** verändert keine Asset-, Build- oder Godot-Dateien. Er prüft
gegebenenfalls vorhandene Cachedateien vollständig und läuft im Hintergrund.
Im Terminal öffnet er den Katalog ausdrücklich nur lesend. Ein älterer Katalog
muss zunächst regulär geöffnet/migriert werden; der Dry-run migriert ihn nicht.

```sh
etherfood-studio build-plan --project /pfad/zum/studio-projekt --asset ASSET-ID
etherfood-studio build-plan --project /pfad/zum/studio-projekt --diagnostic
etherfood-studio build-plan --project /pfad/zum/studio-projekt --diagnostic --execute-diagnostic
```

## Was die Zustände bedeuten

| Zustand | Bedeutung |
| --- | --- |
| Neu | Kein vollständiger lokaler Ergebnisnachweis für den Schritt. |
| Wiederverwendet | Sämtliche Dateien, Berichte und Abhängigkeitsergebnisse geprüft. |
| Veraltet | Früheres Ergebnis vorhanden, aber Eingaben/Abhängigkeiten oder Dateien passen nicht. |
| Blockiert | Fachliche Eingabe, registrierter Adapter oder Voraussetzung fehlt. |
| Nicht erforderlich | Das Anforderungsprofil benötigt diese Variante/Phase nicht. |

Die Zusammenfassung zählt **Varianten**, nicht jede interne Arbeitsphase.
Die Tabelle darunter erklärt die einzelnen Phasen. Die Liste verwendet die
Posennamen aus dem Projekt statt kryptischer IDs. Ein Klick auf einen Schritt
zeigt den vollständigen Grund, technischen Schlüssel, Input-Fingerprint und
Ergebnisdigest. Statische Bilder erhalten
keine künstliche fachliche Frame-Dimension; die Framephase ist nicht erforderlich.
Zusätzliche Bestandsvarianten außerhalb der Anforderungen zählen ebenfalls
als nicht erforderlich, nicht als fehlende Pflichtlieferung.

## Technischer Ablauf

Der gerichtete Graph enthält typisierte Eingaben/Ausgaben und die neun Phasen
Profilbildung, Maskenprüfung, Farbe, Frame-Auswahl, Geometrie/Zuschnitt,
Grafikableitung, Vorschau, Checks und Paketbildung. Fehlende Knoten, fremde
Ausgabetypen, unsichere Zielpfade und Zyklen werden vor Ausführung abgewiesen.
Der technische Graph ist unabhängig von `belongs_to`, Canvas-Pfeilen und Layout.

Der Input-Fingerprint berücksichtigt Quell-/Masken-/Profilinhalte, relevante
Parameter einschließlich Timing, Algorithmusversion, Tool-Hashes und benötigte
Vorgänger. Anzeigenamen, Kapitel, Position, Zeitstempel und reine Revisions-IDs
gehören nicht zur Pixelidentität. Konkrete Revisionen bleiben im Entwurfsplan
als Herkunft erhalten. Lokale Werkzeugpfade werden protokolliert, aber nur
Werkzeugnamen/Hashes gehen in den Inhaltsfingerprint ein.

Ausgabedigest und Input-Fingerprint bleiben getrennt. Ein Nachfolger bindet
zusätzlich die **tatsächlichen Ergebnisdigests** seiner Vorgänger. Eine neue
oder beschädigte Voraussetzung verhindert den blinden Cache-Treffer ihrer
Nachfolger, auch wenn deren alte Dateien noch existieren.

Beispiel: Walk-Zielmaske → nur Walk-Farbe und Folgeergebnisse. Mastermaske →
Profil/Palette und alle davon abhängigen Posen. Ein davon unabhängiges
Tempelpaket bleibt unverändert. Ein umbenanntes Kapitel erzeugt keinen Neubau.

## Cache und Historie

Migration 5 führt den lokalen Index `build_cache` ein. Nur erfolgreich beendete,
verifizierte eigene Aufträge dürfen dort registriert werden. Jeder Lookup
prüft die vollständige Ausgabeliste, Dateilängen, SHA256, Reports, zusätzliche
unregistrierte Dateien und konkrete Abhängigkeitsergebnisse erneut. Vor der
tatsächlichen Wiederverwendung wird nochmals geprüft. Eine defekte Datei
wird nicht repariert/gelöscht, sondern der Treffer wird verworfen.

Alte `spritesheet-fram*`-Teilordner, Dateinamen mit „Fertig“ und importierte
Metadaten-Snapshots sind kein vertrauenswürdiger Cache. Lokale Jobs/Cachebindungen
werden nicht aus Snapshots übernommen. Nach Abbruch dürfen nur vollständig
verifizierte Zwischenschritte wiederverwendet werden.

Builds und der Vergleich **Plan / tatsächlicher Ablauf** sind unveränderliche
Katalogeinträge (`studio-build-v1`, `studio-build-run-v1`). Änderungen erstellen
einen neuen Entwurf (`studio-build-plan-v1`), ändern aber keine historischen
Builds oder Freigaben. Es gibt keine automatische Bereinigung alter Ergebnisse.

## Was bereits ausführbar ist – und was bewusst noch fehlt

**Technische Cache-Diagnose** durchläuft alle neun Phasen mit synthetischen
JSON-Artefakten. Erster Lauf: neu gebaut. Neuer Dry-run: wiederverwendet.
Der Vergleich zeigt pro Schritt Plan, tatsächlichen Zustand und Buildbindung.
Die Ausführung ist ausdrücklich ein zusätzlicher Schreibauftrag; erst der
Button **Diagnoseplan ausführen** bzw. `--execute-diagnostic` startet sie.

Echte Asset-Dry-runs verwenden bereits die Projektanforderungen und Originale.
Produktive Bildadapter, Masterauswahl und Maskenbearbeitung sind aber noch
Folge-Issues T019/T020 und danach. Solche Schritte werden **blockiert** angezeigt,
nicht als simuliert erfolgreich. Die aktuellen synthetischen Builds erzeugen
weder neue Spielgrafiken noch künstlerische Prüfungen oder Godot-Freigaben.
Der Graph-/Cachevertrag ist für diese nachfolgenden Adapter vorbereitet.

[Manuelles Briefing](SICHTPRUEFUNG_7.md) · [Ergebnisbericht](task-results/T018.md)
