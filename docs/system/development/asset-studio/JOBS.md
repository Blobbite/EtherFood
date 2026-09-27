# Aufträge und sichere Werkzeugprüfung (T017)

**Aufträge …** in der Projekt-Toolbar öffnet die Auftragsliste. Diagnose starten
prüft die technische Ausführung, nicht die Spielgrafiken. Wählbar sind Erfolg,
Exit 7, fehlende Ausgabe, langer Lauf und Lauf mit Kindprozess. **FramReduce
prüfen (--help)** startet den registrierten, mitgelieferten Starter lesend.
Fehlende Python-Module werden als Fehler im unveränderten stderr protokolliert;
es werden keine Abhängigkeiten automatisch nachinstalliert.

Terminal (in der vorbereiteten Tool-Umgebung):

```sh
etherfood-studio jobs --project /pfad/zum/studio-projekt
etherfood-studio jobs --project /pfad/zum/studio-projekt --run diagnostic
etherfood-studio jobs --project /pfad/zum/studio-projekt --run framreduce-help
etherfood-studio jobs --project /pfad/zum/studio-projekt --run diagnostic --mode slow --timeout 2
```

Strg+C fordert den sicheren Abbruch an. GUI-Abbruch beendet ebenfalls die
verwaltete Prozessgruppe einschließlich Kindprozessen. Erst danach wird der
Abschluss angezeigt. Projektwechsel sind während eigener Aufträge gesperrt;
beim Schließen kann man abbrechen und das Fenster schließt nach deren Ende.
Navigation und Notizen bleiben während eines Laufs benutzbar.

## Vertrag und Ablage

`pipelines/base.py` definiert den eingefrorenen `BuildRequest` für das ausdrücklich
separate Protokoll **studio-job-v1**. Das ist die technische Auftragshülle mit
registriertem Adapter, unveränderlichen Eingaben, JSON-Parametern, erwarteten
Ausgaben, tatsächlicher Argumentliste, Werkzeug-Hashes und Zeitlimit.
Der bestehende Bild-Austauschvertrag `contracts-v1.json` bleibt unverändert;
eine Diagnose erfüllt weder dessen Bildresultat noch eine Freigabe.

Jeder Auftrag hat eine UUID und eigenen Ordner
`.asset-studio/jobs/<uuid>/{input,output,logs}`. Quellen werden mit Hashprüfung
kopiert, nie verlinkt/verschoben. `request.json` und `result.json` sind einmalige
Nachweise. `logs/stdout.log` und `stderr.log` erhalten Originalbytes, während
`events.jsonl` getrennte, fortlaufend nummerierte Ereignisse enthält:
started, phase, progress, warning, error, finished. Die Anzeige begrenzt nur den
sichtbaren Logausschnitt auf 64 KiB; die Dateien bleiben vollständig.

Migration 4 speichert Jobs und Ereignisse lokal im Katalog. Zwei parallele
Aufträge sind erlaubt; derselbe logische Ergebnisbereich bekommt nur einen
Schreiber. Portable Snapshots übernehmen diese Ausführungsnachweise nicht.
Verwaiste Aufträge werden beim nächsten Öffnen der Auftragsverwaltung als
**interrupted**, niemals nachträglich als erfolgreich, markiert. Live-Aufträge
anderer Instanzen bleiben unangetastet. Der Supervisor beobachtet die genaue
PID-/Startzeitidentität seiner Elternanwendung und stoppt bei deren Ende.

## Grenzen und Sicherheit

Die Prozessverwaltung ist derzeit ausdrücklich **Linux mit `/proc`**. Andere
Plattformen werden vor dem Start abgewiesen, bis eine gleichwertige sichere
Kindprozessverwaltung existiert. Es gibt keine Shell-Interpolation und keine
beliebigen Skripte oder Argumente aus importierten Paketen. Die Isolation ist
eine Arbeitsraumtrennung, **keine Sicherheits-Sandbox für fremden Code**.
Registrierte Werkzeuge müssen vertrauenswürdig bleiben und dürfen nicht aus
der verwalteten Prozessgruppe ausbrechen.

Exit 0 oder das Wort „Fertig“ genügt nicht: Der Adapter prüft sämtliche
erwarteten Dateien und Berichte. Fehler, fehlende Resultate, Abbruch, Zeitlimit
und ungeklärter Prozessabschluss zählen nicht als Erfolg. Historische
Ergebnisse und unvollständige Arbeitsordner werden nicht automatisch gelöscht.

[Ergebnisbericht](task-results/T017.md) · [Arbeitsplan](../plans/asset-studio-paket-7.md)
