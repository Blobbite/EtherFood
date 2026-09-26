# Prüffung des ausgelieferten Planpakets

**Prüfumfang: ausschließlich Planung und Archivstruktur.** Keine EtherFood-Anwendung wurde im Rahmen dieses ZIP-Auftrags implementiert oder mit Godot getestet. Das Repository und die Originaluploads wurden nciht verändert.

Bei der Paketerstellung werden folgende Kontrollen tatsächlich ausgeführt:

- 48 eindeutige, lückenlos nummerierte Aufgaben T001 bis T048.
- Genau eine `p.md` je Aufgabenordner.
- Abhängigkeiten existieren und zeigen ausschließlich auf frühere Aufgaben; damit ist der Aufgabenplan azyklisch.
- Alle 36 Anforderugnen/Schutzregeln sind Aufgaben zugeordnet; die Rückverweise sind symmetrisch.
- Jede Aufgabe enthält mindestens sechs konkrete Arbeitsschritte sowie Tests, Abnahmekriterien, Grenzen und Übergabe.
- Lokale Markdown-Verlinkungen innerhalb der Planung zeigen auf existierende Paketdateien.
- Neun unveränderte Quellen-Auszüge sind vorhanden und mit den ursprünglichen Dateizeilen versehen.
- Alle JSON-Datein sind syntaktisch lesbar. Beispielkonfigurationen sind ausdrücklich noch kein implementiertes Produktformat.
- Alle Paketdateien außer dem Manifest selbst sind im SHA-256-Manifest aufgeführt und werden inhaltlich geprüft.
- ZIP-CRC und eine erneute Prüffung nach Entpacken werden durchgeführt.

Das Paket wird nur bereitgestellt, wenn diese Kontrollen erfolgreich sind. Nach eigenen Änderungen können die ursprünglich mitgelieferten Hashes erwartungsgemäß abweichen. Für spätere reine Strukturkontrolle steht `python3 pruefung/check_plan.py --structure-only` bereit.

## Wiederholbare vollständige Kontrolle

```bash
python3 pruefung/check_plan.py
```

## Maschinenlesbare Ausgabe

```bash
python3 pruefung/check_plan.py --json
```

Die tatsächlichen Anwendungsprüfungen sind Aufträge in den jeweiligen `p.md`-Datein und bleiben bis zur Umsetzugn `not_started`.
