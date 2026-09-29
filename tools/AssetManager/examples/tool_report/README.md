# Mehrteiliges Werkzeugpaket: Dateibericht

Im Asset Manager **Verarbeitung → Importieren** öffnen und `manifest.json`
wählen. Das Paket enthält `report.py` und das Hilfsmodul `helper.py`.
Es benötigt Python 3.11 und keine zusätzlichen Bibliotheken.

Im Paketeditor die Umgebung einrichten, den Code prüfen und freigeben.
Einen Ablauf anlegen, **Dateibericht erzeugen** einfügen und seinen Eingang
mit einem Asset verbinden, das eine importierte Bildquelle besitzt.
Nach dem Ausführen liegt der JSON-Bericht im Asset unter `Ergebnisse/Berichte`.

**Exportieren** überträgt das vollständige Paket. Änderungen im Python-Editor
werden als Entwurf gespeichert und unter einer neuen Version übernommen.
Die Anleitung zur Schnittstelle steht unter
[Werkzeugpakete](../../../../docs/system/development/asset-studio/SKRIPTPAKETE.md).
