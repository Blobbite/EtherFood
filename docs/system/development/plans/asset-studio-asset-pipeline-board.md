# Asset Studio: Pipeline-Board im Asset-Menü

## Zweck und Gesamtbild

Folgeauftrag vom 28.09.2026: Unter **Pipeline / Werkzeuge** erhält jedes Asset
ein Board mit seinem eigenen Symbol, den zugewiesenen Projektpipelines, ihren
Skriptschritten, Regeln und Ausgabeordnern. Das Projekt-Dashboard bleibt die
gemeinsame Ansicht aller beteiligten Assets. Beide Ansichten verwenden dieselben
Rezepte und Zuweisungen.

Aktive Grafikziele wie Comic High/Mittel/Low und Pixel Art High/Low erhalten
sichtbare Ordnerzuweisungen. Diese Ordner werden beim Speichern der wirksamen
Konfiguration vorbereitet, auch wenn noch keine Bilder erzeugt wurden.

## Ausgangslage und Umfang

Der vorherige Umbau bietet bereits einen Pipeline-Canvas, ein GIF-Paket,
Quellenrevisionen und gespiegelte Posenordner. Im Asset-Menü fehlt bisher das
Board. Profilordner entstehen erst bei einer Veröffentlichung. Die bestehenden
Änderungen im Arbeitsbaum einschließlich fremder Änderungen bleiben erhalten.

Der Auftrag betrifft Asset Studio, seine Tests und technische Dokumentation.
Keine Spielkanonänderung, neue Abhängigkeit oder automatische Bild-/Codefreigabe.
Projektpipelines bleiben getrennte ausführbare Rezepte; ihre Darstellung erfindet
keine bisher nicht vorhandene Ausführungsabhängigkeit zwischen Rezepten.

## Schritte und Fortschritt

- [x] Bestehende Boards, Zuweisungen, Profilauflösung und Dateiablage untersuchen.
- [x] Gemeinsame Ableitung von Zuweisungsstatus und Profil-/GIF-Ausgabeordnern ergänzen.
- [x] Asset-Board und Ausgabeziele im Projekt-Dashboard integrieren.
- [x] Ordneranlage mit gespeicherten Profilen und Zuweisungen verbinden.
- [x] Bedienung und tatsächliche Ausgaben prüfen, Dokumentation abschließen.

## Entscheidungen

- Das Asset-Board zeigt ausschließlich das geöffnete Asset und seine passenden
  Zuweisungen. Explizite Zuweisung, Typ-/Fähigkeitsregel, Projektstandard,
  übersteuerte Regeln und Konflikte bleiben unterscheidbar.
- Das Board liest denselben Datenfluss wie der Runner. Änderungen am gemeinsamen
  Rezept erfolgen im bestehenden Projekt-Dashboard, Zuweisungen im Regel-Dialog.
- Profilordner verwenden stabile Profilschlüssel in der vorhandenen Asset-Ablage.
  Deaktivierung entfernt keine historischen Dateien oder bestehenden Ordner.
- Interne Elternprofile für Pixel Low werden von veröffentlichten Zielprofilen
  unterschieden. Ein ausschließlich internes Pixel High erhält keinen Ausgabeordner.

## Erkenntnisse und Überraschungen

- Der Runner unterstützt bereits mehrere ausdrücklich zugewiesene Pipelines und
  priorisiert Asset-Zuweisungen vor Typregeln und Projektstandards.
- Profilaktivierung und Rezept-Zielauswahl sind getrennte Einstellungen. Die
  Ordneransicht muss beide sowie die Anforderungen des einzelnen Assets beachten.
- Im vollständigen Lauf wurde ein Layoutfehler beim Ergänzen eines Assets sichtbar:
  Sortieren nach zufälligen IDs konnte ungespeicherte Symbolpositionen überlagern.
  Das Dashboard behält nun die Einfügereihenfolge. Die Regression erzwingt die
  betroffene ID-Reihenfolge und prüft die tatsächliche Mausbedienung.
- Der neue Reiter passt sein Board beim Einblenden an die tatsächliche Größe an;
  die zunächst verborgene Seite bestimmt nicht den späteren Zoom.
- Die Ordnerprojektion verarbeitet nur die unterstützte Asset-Modellversion.
  Unbekannte Versionen werden weiterhin beim regulären Projektöffnen abgewiesen;
  der neue Ordnerabgleich verschiebt diesen bestehenden Prüfpunkt nicht.

## Prüfungen

- Sechs vorhandene Modell-/Asset-Erstellungsprüfungen bestanden.
- 29 vorhandene Dashboard-/Asset-Menü-Prüfungen bestanden.
- Neun neue Prüfungen bestanden: getrennte Asset-Ansichten in beiden Farbschemata,
  geerbte Zuweisungen im Projektboard, Regeln und Konflikte, gemeinsame Rezeptbearbeitung,
  Profilwechsel aus dem Asset-Menü, Ordneranlage vor Import/Build und Dateikonflikte.
  Statische Asset-Anforderungen und deaktivierte Grafikschritte sind ebenfalls geprüft.
- 70 gezielte Regressionen für Pipeline-Dashboard, Asset-Board und vorhandene
  Canvas-Gesten bestanden.
- Nach der Anpassung des Tabwechsels: neun Asset-Menü-/Board-Bedienprüfungen bestanden.
  Abschließende Sichtprüfung mit zwei Pipelines in Hell- und Dunkelmodus durchgeführt.
- Nach der Korrektur des Modellversionsfalls: 26 Asset-Modell-/Ordnerprüfungen bestanden.
- Ein realer Lauf mit Comic High, internem Pixel High, Pixel Low und anschließendem
  GIF-Schritt veröffentlicht seine PNGs und GIFs in genau den angezeigten Ordnern.
  Für ausschließlich internes Pixel High wird kein Ausgabeordner veröffentlicht.
- `python3 tools/control.py check`: 284 bestanden, 37 übersprungen, drei bestehende
  Fehler außerhalb dieses Umbaus (`window/size/resizable=true`, fehlende
  `docs/game/decisions/index.md` und `ADR-0008-achtteiliger-spielablauf.md`).
  Godot 4 ist nicht installiert; Engine-Prüfungen konnten nicht starten.
  Die globale Stilprüfung meldet unverändert 1903 Bestandsbefunde. Die 40
  geänderten/neuen Python-Dateien haben keine Stilbefunde auf geänderten Zeilen.
- Der erste vollständige Studio-Lauf fand die beiden oben beschriebenen Regressionen.
  Nach deren Korrektur sind alle 695 Studio-Tests und 171 Bildwerkzeugtests in
  getrennten vollständigen Läufen bestanden:
  - `.venv/bin/python -m pytest -q tools/AssetManager/tests/gui`: 242 bestanden.
  - `.venv/bin/python -m pytest -q tools/AssetManager/tests --ignore=tools/AssetManager/tests/gui`:
    453 bestanden.
  - `.venv/bin/python -m pytest -q tools/AssetManager/PyGameTools/.tests tools/AssetManager/PyGameTools/Pipline/2-SpritesheetResolution-Pipline/tests`:
    171 bestanden.
  Die GUI-Prüfungen verwenden `QT_QPA_PLATFORM=offscreen` und die temporäre
  Qt-Laufzeit der Testsitzung.
- Relative Verweise in den vier geänderten/neuen technischen Dokumenten geprüft:
  keine ungültigen Ziele. `git diff --check` erfolgreich.

## Wiederholbarkeit und Wiederherstellung

Synthetische temporäre Projekte und vorhandene Dateijournale verwenden. Die neue
Ordneranlage bleibt Teil der bestehenden Katalogtransaktion; Dateikonflikte werden
nicht durch Überschreiben gelöst. Ein fehlgeschlagener Speichervorgang nimmt seine
Dateischritte zurück. Anzeigen und Zoomen des Boards verändern keine Katalogdaten.

## Ergebnis und Rückblick

Das Asset-Menü zeigt unter **Pipeline / Werkzeuge** das geöffnete Asset mit
seinen passenden Pipelines, Skriptschritten, Zuweisungsregeln und Ausgabeordnern.
Das Projekt-Dashboard zeigt weiterhin die beteiligten Assets gemeinsam und
berücksichtigt jetzt auch Zuweisungen durch Typregeln und Projektstandards.
Beide Ansichten greifen auf dieselben Rezepte zurück.

Aktive Comic-/Pixel-Ziele und konfigurierte GIF-Ziele erzeugen ihre Verzeichnisse
beim Speichern. Inaktive Ziele und interne Verarbeitungsschritte bleiben
unterscheidbar; bestehende Dateien werden bei Deaktivierung erhalten.
Die gezielten Prüfungen, alle Studio- und Bildwerkzeugtests sowie die Sichtprüfung
sind abgeschlossen. Die oben aufgeführten Bestandsfehler der projektweiten
Gesamtprüfung bleiben außerhalb dieses Auftrags.
