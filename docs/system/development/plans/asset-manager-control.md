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
