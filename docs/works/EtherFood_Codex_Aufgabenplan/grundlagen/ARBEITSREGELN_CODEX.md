# Gemeinsame Arbeitsregeln für jede Codex-Aufgabe

## Arbeitsumfang

Führe jeweils genau eine ausdrücklich ausgewählte `p.md` aus. Lies zuerst gültige lokale Repository-Anweisungen, danach den Projektbrief, die Architektur und die für diese Aufgabe genannten Vorgängerberichte. Starte nciht selbstständig die ganze Roadmap.

Die Aufgaben dieses Pakets sind Implementierungsaufträge. Nach T001/T002 genügt keine neue allgemeine Konzeptantwort: liefere Code, passende Tests und einen tatsächlichen Ergebnisbericht innerhalb des jeweiligen Scopes. Platzhalter dürfen nur für ausdrücklich spätere Funktionen existieren und müssen deaktiviert/erkennbar sein.

## Vor dem Schreiben

Prüfe tatsächliche Dateipfade, Git-Zustand, lokale Konventionen und vorhandene Funktionen. Im Quelldump sind teilweise nummerierte und unnummerierte Pipelinepfade gemischt. Eine README-Beispielzeile ist kein Beweis des vorhandenen Checkoutpfads.

Wenn eine Voraussetzung fehlt, suche sie im verfügbaren Projektkontext. Dokumentiere begründete nciht destruktive Annahmen. Fehlen echte Eingaben, Engine oder nötige künstlerische Entscheidungen, arbeite am sicheren unabhängigen Teil weiter und dokumentiere den konkreten Blocker. Erfinde keine Eingaben oder Freigaben.

## Verbindlicher Schutz

Originalquellen, manuell erstellte Framevarianten, fremde Datein und bestehende Nutzeränderungen bleiben erhalten. Keine pauschalen `git reset`, `git clean`, `git add -A`, keine ungefragten Pushes und keine massenhaften Ordnerumbauten.

Tests verwenden synthetische Fixtures oder ausdrücklich ausgewählte Kopien. Neue Worker erhalten eigene Arbeitsbereiche. Die alten Fram16-/Fram8-Abläufe können direkte Quellen nach PixelEng verschieben; niemals ungeprüft auf Original-/Archivordnern starten.

Alte CLI-Standardwerte und Profilformate bleiben kompatibel. Neue Funktionen sind über neue explizite Verträge einzuführen. Kein stiller Fallback von Materialkorrektur zu Soft, von fehlenden Richtugnen zu Duplikaten oder von Godot-Fehlern zu Erfolg.

## Prüfungen

Schreibe Tests für positive, negative und Wiederholungs-/Abbruchfälle. Ein grüner Core-Testlauf ersetzt keine GUI-, QtWebEngine- oder Godot-Prüffung. Eine vorhandene Datei ersetzt keine Inhaltsprüfung. Ein alter Report ersetzt keinen neuen passenden Nachweis.

Führe die Tests tatsächlich aus, soweit die Umgebung das erlaubt. Dokumentiere exakte Befehle, Ergebnis und nciht ausgeführte Prüfungen. Historische Zahlen aus den Quellen werden nciht als eigene Testergebnisse ausgegeben.

Automatisierte Tests dürfen synthetische Reviews als Testfixture modellieren. Sie dürfen keine reale menschliche Sichtabnahme von Greenhero, Materialmasken oder Spielgrafiken erzeugen. Produktive Zustände bleiben offen, bis die vorgesehenen Entscheider handeln.

## Abschluss pro Aufgabe

Schreibe `docs/asset-studio/task-results/TNNN.md` anhand der mitgelieferten Ergebnisvorlage. Der Bericht enthält Scope, geänderte Datein, Verträge/Entscheidungen, ausgeführte Befehle, Prüfergebnisse, offene Punkte und genau die Voraussetzung für den nächsten Schritt.

Markiere eine Aufgabe nur dann `done`, wenn ihre Abnahmekriterien erfüllt und notwendige Prüfungen ausgeführt sind. Andernfalls nutze `partial` oder `blocked` mit Begründung. Ein Dokumentations-/Codeabschluss ist von einer noch nötigen realen Benutzerfreigabe ausdrücklich zu unterscheiden.

Kein Commit oder Push ist Pflicht dieses Planpakets. Ein Commit erfolgt nur gemäß den tatsächlich geltenden Projektregeln oder einer ausdrücklichen Anweisung und umfasst ausschließlich passende Änderungen.
