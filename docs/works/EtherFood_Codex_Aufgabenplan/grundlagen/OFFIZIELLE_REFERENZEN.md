# Ergänzende technische Referenzen

Diese Links dienen ausschließlich der API-/Implementierungsprüfung. Sie ersetzen nciht die Nutzeranforderungen oder die beigefügten Bestandsquellen. Die Architektur im Plan ist ein Zielentwurf. Dokumentation abgerufen am 26.09.2026; Codex soll die zur tatsächlich installierten Version passende API erneut prüfen.

## W01 — Codex-Projektanweisungen

OpenAI beschreibt projektbezogene Anweisungen über `AGENTS.md`. Bestehende lokale Regeln zuerst lesen; dieses Planpaket enthält absichtlich keine Datei, die eine vorhandene Repository-`AGENTS.md` überschreiben soll.

https://developers.openai.com/codex/guides/agents-md

Die abgerufene Adresse leitete auf die offizielle ChatGPT-Learn-Dokumentation weiter:
https://learn.chatgpt.com/docs/agent-configuration/agents-md

## W02 — Qt-Arbeitsprozesse

`QProcess` ist der geprüfte Ausgangspunkt für Prozessstart, Ausgaben und Beendigungssignale. Die konkreten Abbruch-/Kindprozessregeln dieses Projekts sind eigene Implementierungsanforderungen, keine pauschale Sandbox-Garantie.

https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html

## W03 — Kartenansicht

Die Qt-Graphics-View-Dokumentation beschreibt Scene/View und interaktive grafische Elemente. Kartentypen, Beziehungen, Persistenz und Geschäftsregeln müssen darauf aufbauend entwickelt werden.

https://doc.qt.io/qtforpython-6/overviews/qtwidgets-graphicsview.html

## W04 — HTML-Vorschau

`QWebEngineView` dient als Grundlage zur HTML-Einbettung. Zugriffsbeschränkung, sichere Navigation und der kleine Auswahlvertrag zur Python-Anwendung sind zusätzliche Aufgaben des Projekts.

https://doc.qt.io/qtforpython-6/PySide6/QtWebEngineWidgets/QWebEngineView.html

## W05 — Godot-Aufrufe

Godots Kommandozeilendokumentation beschreibt unter anderem Import, Skriptstart und Headless-Betrieb. Ein erfolgreicher Start ersetzt keine projektspezifischen Tests.

https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html

## W06 — SpriteFrames

Die Klassenreferenz dokumentiert Animationsgeschwindigkeit und individuelle Frame-Dauern. Die konkrete Dauererhaltung bei reduzierten Sequenzen ist ein eigener Timingvertrag dieses Plans.

https://docs.godotengine.org/en/stable/classes/class_spriteframes.html

## W07 — Importablauf

Godot dokumentiert den Importcache und die zugehörige Importkonfiguration. Übertragbarkeit von Pfaden/UIDs und die wirksamen Einstellungen müssen für Test-/Runtime-Deployments gezielt geprüft werden.

https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/import_process.html

## W08 — ResourceSaver

Die ResourceSaver-Referenz beschreibt Speicheroptionen einschließlich relativer Pfade. Dass ein konkretes Paket zwischen zwei Projektbereichen ohne Referenzfehler funktioniert, muss zusätzlich getestet werden.

https://docs.godotengine.org/en/stable/classes/class_resourcesaver.html
