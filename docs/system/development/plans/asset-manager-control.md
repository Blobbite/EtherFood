# Arbeitsplan: Asset Manager über Control steuern

## Zweck und Ausgangslage

2026-09-26: Der Asset Manager besitzt einen eigenen Starter. Gewünscht ist
statt direkter Python-/pip-Aufrufe der zentrale Einstieg über
`python tools/control.py asset-manager …`, entsprechend den Godot-Befehlen.
Die README-Ergänzung allein erfüllt diesen Wunsch nicht.

## Umfang und Nicht-Ziele

- Zentrale Befehle für Start, lokale Einrichtung, Diagnose und Tests.
- Beim ersten Start eine fehlende Repository-`.venv` anlegen und die bereits
  festgelegten Studio-Abhängigkeiten darin installieren; vorhandene passende
  Installation wiederverwenden. Keine manuelle Shell-Aktivierung notwendig.
- Keine Systempakete automatisch installieren, keine defekte Umgebung löschen,
  keine Bildpipelines oder Godot-Bereitstellung aus späteren Paketen vorziehen.
- Die Bedeutung von `import` wurde beim Benutzer nachgefragt. Ohne abweichende
  Rückmeldung ist es ausdrücklich ein Alias zur Vorbereitung der Tool-Umgebung,
  kein Asset-Import. Hilfe, README und Abschlussmeldung benennen diese Grenze.

## Schritte und Fortschritt

- [x] Control, Installer, Studio-CLI und bestehende Tests untersuchen.
- [x] Befehlsfamilie und sichere, bedarfsgesteuerte `.venv`-Vorbereitung umsetzen.
- [x] Automatisierte Tests für Dispatch, Bootstrap und Fehlerfälle ergänzen.
- [x] README und Start-/Sichtprüfungsanleitung auf Control umstellen.
- [x] Schnelle Prüfungen, Studio-/Pipeline-Tests und Standardcheck ausführen.

## Erkenntnisse und Entscheidungen

- Der allgemeine Installer richtet auch Godot/Systempakete ein und kann eine
  defekte `.venv` neu erstellen. Dies wird nicht automatisch vom Studio gestartet.
- `doctor` bleibt rein diagnostisch, ohne pip, Installation oder Projektanlage.
- Qt-Pythonpakete und fehlende native Qt-/Display-Bibliotheken müssen getrennt
  gemeldet werden; fehlende Systembibliotheken rechtfertigen keine pip-Schleife.
- Studio-GUI-Tests dürfen nicht unbemerkt übersprungen und als vollständig
  erfolgreich dargestellt werden. Ein expliziter Core-Test bleibt ohne Qt möglich.
- Einrichtung und Tests besitzen Zeitlimits; der interaktive Desktop bleibt
  entsprechend einem normalen Godot-Start bis zum Schließen geöffnet. Er wird
  nicht wegen eines Test-Zeitlimits mit möglicherweise ungespeicherten Daten beendet.
- Die schon vorhandene README-Änderung gehört zur selben Anforderung und wird
  durch den zentralen Einstieg ersetzt. Andere Änderungen bleiben unberührt.

## Prüfungen

- 101 gezielte Tests für Control/CLI/Installer einschließlich 56 neuer
  Bootstrap-Regressionen bestanden: simulierter Erststart, Wiederverwendung, Dry-run,
  Pfade mit Leerzeichen, defekte/externe `.venv`, Installations-/Qt-Fehler,
  Test-Rückgabecodes und explizite Core-Auswahl.
- Echter `doctor --core` und `install --core` erfolgreich; vorhandene passende
  Pakete werden ohne erneuten pip-Aufruf verwendet.
- `python3 tools/control.py asset-manager import --core`: erfolgreich, ohne
  erneute Installation bei bereits passenden Paketen.
- `python3 tools/control.py asset-manager test --core`: 45 Tests bestanden.
- `python3 tools/control.py asset-manager check`: 56 Studio-/GUI-Tests und
  171 Pipeline-Tests bestanden. Für Qt wurden wie bei Paket 4 temporäre native
  Testbibliotheken per Umgebung eingebunden; keine Systeminstallation oder
  mitgelieferten Binärdateien. Die Offscreen-Plattform wurde vorab echt geprüft.
- Ohne diese Testbibliotheken melden `doctor` und `run` konkret die fehlende
  `libGL.so.1` und stoppen; kein erfolgloser erneuter pip-Installationsversuch.
- Quellstil für `tools/src/g2dtool` und `tools/tests`: 41 Dateien, keine Verstöße.
- `git diff --check`: erfolgreich. Ursprünglicher Aufgabenplan unverändert:
  48 Aufgaben, 36 Anforderungen, 955 Links und 81 Dateihashes geprüft.
- Vollständiger `python3 tools/control.py check`: 257 Python-Tests bestanden,
  37 übersprungen und zwei bekannte Dokumentationstests fehlgeschlagen.
  Weiterhin fehlen `docs/game/decisions/index.md` und
  `docs/game/decisions/ADR-0008-achtteiliger-spielablauf.md`; dadurch 13 kaputte
  Bestandslinks. Zusätzlich unveränderte geerbte Stilprobleme und fehlendes Godot.
  Diese Bestandsfehler wurden nicht durch Änderungen am Spielkanon kaschiert.

## Wiederholbarkeit und Wiederherstellung

Installation ausschließlich in der ignorierten Repository-`.venv`; keine
Anmeldedaten, Rechnerpfade oder Binärdateien werden eingecheckt. Ein Abbruch
bleibt sichtbar und wird nicht durch Löschen/Rekreation kaschiert. Dry-run zeigt
die geplanten Befehle, ohne sie auszuführen. Originalassets bleiben unverändert.

## Ergebnis und Rückblick

Der zentrale Einstieg ist umgesetzt und geprüft. `run` verwendet automatisch
die lokale `.venv`; `doctor` bleibt lesend. `install`/`import`, Studio- und
Pipeline-Tests sowie der kombinierte Check besitzen eigene Control-Befehle.
README und Sichtprüfungsanleitung verwenden jetzt diesen Einstieg.
Keine späteren Studio-Arbeitspakete, Originalassets oder Godot-Szenen geändert.
Die echte Sichtprüfung am Benutzer-Desktop und andere Betriebssysteme bleiben
offen; automatisierte Offscreen-Tests ersetzen diese Abnahme nicht.

## Ergänzung 2026-09-28: pip-Reparatur und Upgrade über Control

### Ausgangslage und Ziel

Eine vorhandene `.venv` ohne pip besteht die Interpreterprüfung, blockiert aber
bisher selbst `asset-manager install`. Der Benutzer möchte die Einrichtung
vollständig über Control bedienen. Die gemeinsame Vorbereitung soll fehlendes
pip mit dem eigenen Interpreter und `ensurepip --upgrade` ergänzen. Ein neuer
Befehl `asset-manager upgrade` aktualisiert pip aus dem Python-Bestand und
installiert die im Studio festgelegten Paketversionen mit `pip install --upgrade`.

### Schritte und Fortschritt

- [x] Vorhandene Vorbereitung, Diagnose, Tests und Stilregeln prüfen.
- [x] Interpreterprüfung von pip-Verfügbarkeit trennen und Reparatur einbauen.
- [x] Upgrade-Befehl einschließlich Core-Auswahl und Dry-run ergänzen.
- [x] Regressionen für Reparatur, Upgrade, Fehler und Wiederholung prüfen.
- [x] Befehle dokumentieren und Gesamtprüfung mit ihren Grenzen auswerten.

### Entscheidungen und Grenzen

Die Interpreterprüfung erfolgt vor jeder Reparatur. Eine passende vorhandene
Umgebung wird weiterverwendet; fehlendes pip ist ein reparierbarer Zustand.
`install`, `import`, `run` und Tests verwenden denselben Vorbereitungsweg.
`doctor` bleibt lesend, Dry-run zeigt auch den Bootstrap-Befehl ohne Ausführung.
Upgrade verwendet die bestehenden Paketvorgaben und legt keine neuen
Abhängigkeiten fest. Systempakete, Spielinhalte und Studio-Projektdaten gehören
nicht zu dieser Änderung.

### Prüfungen und Erkenntnisse

Vor der Änderung bestanden alle 56 Control-Tests für den Asset Manager.
Die vorherige Projektsichtung meldete 1907 bestehende Stilprobleme. Zu Beginn
fehlten in dieser Docker-Sitzung Godot und die Studio-Pakete. Für die echte
Core-Prüfung wurden die bereits vorgegebenen Studio-Pakete anschließend über
den neuen Upgrade-Befehl in der lokalen `.venv` installiert.

- 82 gezielte Asset-Manager-Control-Tests bestanden. Darunter wird eine echte
  temporäre `.venv` ohne pip offline repariert; der zweite Installationslauf
  verwendet sie ohne erneuten Bootstrap. Die Studio-Pakete sind in diesem
  einzelnen Test simuliert, `venv`, `ensurepip` und Umgebungsproben sind echt.
- Geprüft sind außerdem Upgrade trotz bereits passender Pakete, Core-Auswahl,
  Bootstrap-/Installationsfehler, falscher Interpreter, Dry-run mit und ohne
  vorhandene `.venv`, lesender Doctor und erhaltene vorhandene Dateien.
- Erweiterte Prüfung mit `test_asset_manager_control.py`, `test_cli.py`,
  `test_install.py` und `test_control.py`: insgesamt 127 Tests bestanden.
- Echter `python3 tools/control.py asset-manager upgrade --core`: erfolgreich,
  einschließlich `ensurepip`, Paketinstallation, Versions-/Checkout-Prüfung,
  `pip check` und Modulimporten. Anschließendes `install --core` erfolgreich
  ohne erneute Installation. Eine Qt-Oberfläche wurde dabei nicht gestartet.
- CLI-Hilfe und `upgrade --dry-run` erfolgreich. Alle vier geänderten
  Python-Dateien ohne Stilbefund; `git diff --check` erfolgreich.
- Vollständiger `python3 tools/control.py check`: 283 Tests bestanden,
  37 übersprungen, vier Fehler im unveränderten Spiel-/Dokumentationsbestand:
  erwartete Asset-Unterordner fehlen, explizite Fenstereinstellungen fehlen,
  zwei Entscheidungsdokumente fehlen und dadurch sind 13 Links ungültig.
  Die betroffenen Spiel-/Kanondateien und Tests stimmen mit `HEAD` überein.
  Zusätzlich bestehen die 1907 Stilbefunde fort; Godot fehlt weiterhin, daher
  konnten Ressourcenimport und Godot-Integration nicht ausgeführt werden.

### Wiederholbarkeit und Ergebnis

Die Reparatur ergänzt pip in der bestehenden `.venv`. Fehler stoppen weitere
Einrichtung und Start; erneutes Ausführen erfolgt über denselben Control-Befehl.
`install` und `run` behandeln damit den gemeldeten Fall ohne direkten
`ensurepip`-Aufruf durch den Benutzer. `upgrade` ist als eigener Control-Befehl
verfügbar; Einstiegshilfe, beide READMEs und Entwicklungsanleitung beschreiben
den Ablauf. Die gezielten Prüfungen und echten Core-Einrichtungen bestehen;
der Gesamtcheck bleibt wegen der oben aufgeführten Bestandsbefunde rot.
