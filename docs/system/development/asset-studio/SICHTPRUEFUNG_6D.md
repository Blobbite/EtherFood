# Ergänzung 6d – Dokumentation und Icons

Bestehendes Testprojekt verwenden und Studio neu starten:
`python3 tools/control.py asset-manager run`.

## Vier kurze Prüfungen

1. **Dokumentation erstellen:** Unter Dokumentation & Anhänge steht
   **+ Dokumentation**, daneben weiterhin **Markdown importieren**. Mit der
   Vorlage Dokumentation einen Text anlegen und speichern. Er erscheint nicht
   als Post-it im Notiz-Dashboard. Dort bleibt **+ Notiz** erhalten. Im Asset-Menü
   ist derselbe Dokumentationsbutton unter Dokumente & Anhänge verfügbar.
2. **Markdown:** Eine kleine vorhandene `.md`-Datei importieren. Text und Vorschau
   bleiben lesbar; die Originaldatei bleibt unverändert. Im Canvas erscheint
   der Import als Dokumentation, nicht als neue gelbe Notiz.
3. **Canvas und Icons:** Dokumentation ist ein kleines violettes Symbol mit
   Blatt-Icon. Doppelklick öffnet den Text in Dokumentation & Anhänge. Verschieben
   und Anklicken bei anderem Zoom dürfen keine Sprünge erzeugen. Aufgaben haben
   nur einen kräftigeren grünen Haken als Icon; der Aufgabenstatus bleibt separat.
4. **Bestehendes und Neustart:** Eine alte Notiz und einen vorhandenen Anhang
   öffnen; beide müssen erhalten sein. Nach App-Neustart bleiben neuer Text,
   Zuordnung und verschobene Dokumentposition gespeichert.

Rückmeldung **✅ 1–4** oder **❗ Nummer: Befund** genügt. Quellenraster,
Spritesheets und vollständige Kanban-Statusabläufe diesmal überspringen.
Schreibschutz generierter Berichte und Revisionskonflikte wurden automatisiert
geprüft. Die noch nicht ausdrücklich bestätigte [6c-Prüfliste](SICHTPRUEFUNG_6C.md)
bleibt davon unabhängig.

## Vorschlag für das nächste Paket

Als nächster freizugebender Abschnitt bietet sich **Paket 7: Ausführungsgrundlage**
innerhalb von [Phase C](https://github.com/Blobbite/EtherFood/issues/4) an:

- **⚙️ T017 / [#24](https://github.com/Blobbite/EtherFood/issues/24): Arbeitsprozesse
  und gemeinsame Pipeline-Adapter.** Aufträge mit Logs, Fortschritt, Abbruch und
  geprüften Ergebnissen ausführen, ohne die Oberfläche zu blockieren. Zuerst
  synthetische Aufträge und lesende Werkzeugprüfungen; keine ungeprüften
  produktiven Läufe auf Originalen.
- **♻️ T018 / [#25](https://github.com/Blobbite/EtherFood/issues/25): Buildplan,
  Cache und Änderungsfolgen.** Vorab zeigen, welche Varianten fehlen, veraltet
  oder blockiert sind. Ergebnisse nur nach Inhaltsprüfung wiederverwenden;
  betroffene Abhängigkeiten gezielt neu berechnen statt alles erneut zu bauen.

Beide Issues am 27.09.2026 lesend als offen bestätigt. Nach Umsetzung folgt
ein eigenes Briefing zu Auftragsstart/Abbruch, Logs und Plananzeige. Diese
Empfehlung startet die Issues noch nicht. Farb-/Maskenverarbeitung und Godot-Export
kommen erst nach ihren eigenen Voraussetzungen und Freigaben.
