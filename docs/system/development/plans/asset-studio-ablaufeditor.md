# Asset Studio: vollständiger Ablaufeditor und Werkzeugpakete

## Zweck und Gesamtbild

Der Nutzer hat am 28.09.2026 den vollständigen Umbau beauftragt. Kleine
Python-Bausteine erledigen jeweils eine Aufgabe. Importierbare Werkzeugpakete
enthalten Bausteine, Hilfsmodule und wiederverwendbare Abläufe. Der Ablaufeditor
verbindet sie, zeigt deklarierte Ausgabeordner und übernimmt Prüfung, Ausführung
und Veröffentlichung. Paketinhalt, Python-Code und Umgebungen sind von dort
erreichbar. Neue kompatible Bausteine benötigen keine Änderung am Anwendungskern.

## Ausgangslage

Der Arbeitsbaum enthält bereits umfangreiche, uncommittete Änderungen an
Dashboard, GIF-Verarbeitung und Asset-Ablage. Diese sind die Arbeitsgrundlage
und werden erhalten. Der HTML-Entwurf beschreibt die gewünschte Navigation,
ist aber keine implementierte Desktopfunktion.

Es bestehen ein Bildadapter mit einem Bildpaar je Schritt, ein sicherer
Job-Lebenszyklus, Buildgraph/Cache, projektlokale Registrierung einzelner
Python-Dateien und eine verwaltete Asset-Ablage. Grafikprofile sind zusätzlich
in Posen, Assetdialogen und im Projektmodell verankert. Sie beeinflussen bisher
auch die erwarteten Varianten. Diese Zuständigkeit muss mit umziehen.

## Umfang und Nicht-Ziele

Zum Auftrag gehören Mikrobausteine, mehrteilige Werkzeugpakete, typisierte
Ein-/Ausgänge und mehrere Ergebnisdateien, verschachtelte Abläufe, vollständiger
Import/Export mit Diagnose, verwaltete Bibliotheksumgebungen, Python-Entwürfe mit
Vergleich/Prüfung/Testlauf sowie die neue Desktopbedienung. Alle bisherigen
Verarbeitungsschalter und separaten Startaktionen werden aus den Asset- und
Posenansichten entfernt. Bestehende Daten und Verarbeitung bleiben migrierbar.

Godot-Spielmenüs, Produktionsfreigaben und eine automatische Verbindung zu einem
externen KI-Dienst gehören nicht dazu. Der Editor stellt Fehlerkontext zum
Kopieren und bearbeitbare Dateien für eingefügte Vorschläge bereit.

## Schritte und Fortschritt

- [x] Repositoryregeln, Bestand und bestehenden Arbeitsbaum erfassen.
- [x] Paket-/Schrittvertrag, Versionierung, Abläufe und Diagnosen implementieren.
- [x] Verwaltete Python-Umgebungen und generischen Worker integrieren.
- [x] Bestehende Bildverfahren als einzeln verwendbare Bausteine bereitstellen.
- [x] Planung, Dateiveröffentlichung, Cache und Import/Export integrieren.
- [x] Ablauf-, Paket- und Python-Editor einschließlich Navigation verbinden.
- [x] Alte Oberflächen und versteckte Zielvorgaben migrieren/entfernen.
- [x] Funktions-, Integrations- und GUI-Prüfungen abschließen.
- [x] Benutzerdokumentation abschließen, Standardcheck ausführen und Befunde dokumentieren.

## Entscheidungen

- Der vorhandene Buildplaner, Job-Runner und Cache bleiben die Ausführungskette.
- Paketdateien und Ablaufverwendungen erhalten unveränderliche Inhaltshashes.
  Bearbeitungen entstehen als Entwurf; alte Verwendungen wechseln nicht still
  auf neuen Code. Lokale Ausführungsfreigaben werden nicht exportiert.
- Typisierte Ergebnisdateien werden mit Metadaten übergeben. Die Projektablage
  veröffentlicht nur geprüfte Ergebnisse eines vollständig erfolgreichen Laufs.
- Umgebungen werden lokal nach ihrem festgelegten Bibliotheksbestand verwaltet.
  Die Studio-Umgebung wird durch eine Paketinstallation nicht geändert.
- Ein Paket ist eine Lieferung; ausführbar sind seine gewählten Schritte oder
  Ablaufeinstiege. Teilabläufe haben ausdrücklich benannte Anschlüsse.
- Posen behalten Quelle, Richtung, Anker und Ausgangstiming. Erzeugte Profile,
  Framevarianten und Exportparameter gehören zu den Verarbeitungsschritten.

## Erkenntnisse und Überraschungen

- Die bisherige Quell-/Anforderungsmatrix verlangte eine Grafikliste. Schema 2
  trennt jetzt Quelldefinitionen von den expliziten Verarbeitungsschritten.
- Qt ist in der lokalen Python-Umgebung vorhanden; native GL-/EGL-Bibliotheken
  fehlten im Container. Isoliert entpackte Distributionspakete ermöglichten die
  GUI-Verifikation ohne Änderungen an System oder Projektabhängigkeiten.
- Optionale Ausgänge dürfen ohne Datei erfolgreich sein. Dieser Fall benötigt
  dieselbe Behandlung bei Ergebnisprüfung, Veröffentlichung und Cacheabruf.

## Prüfungen

Abschließend bestehen **711 unterschiedliche Asset-Studio-Tests**:

- Backend-Gesamtlauf: 462 bestanden, drei Qt-abhängige Tests zunächst übersprungen.
  Diese drei Tests bestehen im gesonderten Lauf mit verfügbaren Qt-Bibliotheken.
- GUI-Gesamtlauf: 245 bestanden, einschließlich bestehender Oberflächen und
  des vollständigen Ablaufs über zwei Akte, Verschieben, Undo und Wiederöffnen.
- Der anschließend ergänzte Integrationstest für leere optionale Ausgänge besteht.
  Nach der Korrektur bestehen alle 16 Paket-/Ablauf-/Schema- und neuen GUI-Tests
  im gemeinsamen Nachlauf.
- Zusätzlich bestehen alle **123 PyGameTools-Tests** der vorhandenen Bildverfahren.

Reale Bildketten prüfen Raster → Comic Low → Frameauswahl → GIF → Posenvergleich.
Der verschachtelte Auflösungsablauf erzeugt fünf PNG-Varianten und HTML-Vergleich.
Weitere Prüfungen decken mehrere Dateien, relative Hilfsimporte, benannte
Sammeleingänge, fehlende Dateien/Imports, Umgebungsreparatur, geerbte Zuweisungen,
transitive Paketexporte, Versionsbindung, ungültige Archive und Fehler/Abbruch
ohne Veröffentlichung ab. Originale und bisherige Ergebnisse bleiben erhalten.
Die Bildtests verwenden eine aus dem bereits installierten Pillow erstellte
lokale Wheel-Datei und benötigen keinen Paketindex.

Canvas, Bibliothek, Python-Editor und bereinigtes Asset-Menü wurden in der echten
Qt-Anwendung offscreen geöffnet und visuell geprüft. Lesbarkeit, Zoom und die
Auswahl des geöffneten Python-Bausteins wurden dabei nachgebessert. Geänderte
Dokumentationslinks sind gültig; `git diff --check` besteht. Der Stilvergleich
gegen den Arbeitsbaum zu Sitzungsbeginn ergibt keine neuen Befunde.

Die Studio-Prüfungen wurden mit `.venv/bin/python -B -m pytest` ausgeführt,
getrennt für `tools/AssetManager/tests/gui`, die übrigen Studio-Tests und
`tools/AssetManager/PyGameTools/.tests`. Qt lief mit `QT_QPA_PLATFORM=offscreen`
und den temporär bereitgestellten nativen Bibliotheken.

Der vollständige Repository-Standardcheck `python tools/control.py check` wurde
mit vorhandenem Godot aus `.ci-bin` im Suchpfad ausgeführt: Doctor 12/12 und
Ressourcenimport erfolgreich; allgemeine Python-Tests 284 bestanden,
37 übersprungen und drei bestehende Fehler. Diese betreffen fehlende
`docs/game/decisions/`-Dokumente und explizite Displaywerte in `game/project.godot`.
Der Godot-Integrationstest meldet bestehende Abweichungen bei VisualLab-
Einstellungen, Kamera und Heldenmaßstab; der globale Stilcheck bestehende
Altbefunde. Diese Spielbereiche wurden nicht geändert. Der Standardcheck ist
deshalb insgesamt weiterhin rot; die Studio- und Bildwerkzeugtests bestehen.

## Wiederholbarkeit und Wiederherstellung

Schemaänderungen verwenden die vorhandene SQLite-Sicherung und Transaktionen.
Alte Rezept- und Buildrevisionen bleiben erhalten. Kein zerstörerischer
Git-Befehl, kein Ersetzen fremder Arbeitsbaumänderungen und keine automatische
Löschung von Originalen oder früheren Ausgaben. Generierte Umgebungen,
Testprojekte und Bildschirmbilder gehören nicht ins Repository.

## Ergebnis und Rückblick

Abgeschlossen am 28.09.2026. Unter **Verarbeitung → Ablaufeditor** lassen sich
Bausteine importieren, im Canvas verbinden, im Python-Editor bearbeiten, in
getrennten Umgebungen ausführen und mit Code und Hilfsdateien wieder exportieren.
Grafikziele und Framevarianten sind aus Asset-/Posenansichten entfernt; die
Migration erhält ihre wirksamen Einstellungen als sichtbare Abläufe.

Die [Bedienanleitung](../asset-studio/PIPELINES.md) und
[Python-Schnittstelle](../asset-studio/SKRIPTPAKETE.md) beschreiben den fertigen
Stand. `tools/AssetManager/examples/tool_report/` enthält ein direkt importierbares
Mehrdatei-Beispiel ohne zusätzliche Bibliotheken. Bekannte, auftragsfremde
Standardcheck-Befunde stehen oben und bleiben ausdrücklich offen.
