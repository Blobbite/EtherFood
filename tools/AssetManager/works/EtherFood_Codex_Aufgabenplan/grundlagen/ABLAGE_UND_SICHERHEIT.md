# Ablage- und Schutzregeln

## Grundsatz

Die Anwendung darf Dateistrukturen verwalten, aber nciht Originale, manuelle Korrekturen oder fremde Datein als wegwerfbare Ausgaben behandeln. Alle schreibenden Schritte sind auf bekannte Wurzeln und Besitzlisten begrenzt.

## Quellen und Arbeitskopien

Quellenimport kopiert geprüfte Bytes in eine neue Revision. Unterprozesse arbeiten auf isolierten Kopien. Keine Hardlinks aus beschreibbaren Jobs auf geschützte Blobs. Vor und nach importkritischen Schritten werden Hashes geprüft. Ein laufender externer Export wird nciht halb übernommen.

Der vorhandene Fram8-/Fram16-Controller kann Datein nach PixelEng verschieben. Deshalb ist seine Quellwurzel beriets eine dafür erzeugte Arbeitskopie, niemals das einzige Original. Die normale FramReduce-Skipregel ersetzt keine Wiederaufnahmeprüfung.

## Pfade

Verwende benannte Wurzeln und relative Nutzdatenpfade. Wehre Traversal, Links, unzulässige Zieltypen und überlappende Ein-/Ausgabebereiche ab. Prüfe Pfade nciht nur beim Formularausfüllen, sondern erneut beim Schreiben. Dateinamen mit Sonderzeichen müssen korrekt behandelt und in HTML/JSON escaped werden.

Nur Quell-Datein aus bekannten Importtypen lesen. Keine freien Shellstrings aus Namen. Keine HTML-/Markdown- oder Assetpaketdatei als ausführbares Plugin behandeln. Registry-Einträge sind vertrauenswürdiger installierter Code.

## Transaktionen über Datein und Katalog

Eine DB-Transaktion kann ein ganzes Verzeichnis nciht magisch mittransaktionieren. Neue Datein zuerst temporär am Ziel schreiben und prüfen. Ein OperationJournal dokumentiert Kopie, Registrierung und Aktivierung. Ein Wiederanlauf gleicht den realen Zustand ab.

Bei verschiedenen Datenträgern gilt Kopieren → Prüfen → Registrieren/Aktivieren → später Aufräumen. Ein Dateisystem-rename über Laufwerksgrenzen ist keine allgemeine Lösung. Alte bestätigte Inhalte werden erst entfernt, wenn ein ausdrücklich erlaubter Retentions-/Cleanupplan sie nciht mehr benötigt.

## Test und Runtime

Testexports liegen isoliert unter verwalteten Teilbereichen. Gemeinsame test_scenes sind Infrastruktur. Produktive Szenen werden nciht automatsich durch Testvarianten ersetzt.

Promotion verwendet das beriets geprüfte ExportBundle. Nur deploymentabhängige Import-/Loaderdetails werden gemäß Vertrag aufgelöst und separat nachgeprüft. Neue aktive Zuordnung erst nach finaler Prüffung. Testcleanup folgt der Aktivierung und betrifft ausschließlich owned_files ohne andere Nutzer.

## Sicherung und Git

Die laufende DB wird konsistent gesichert, nciht einfach kopiert, während unberücksichtigte Journale offen sind. Backup muss die tatsächlich referenzierten Quellen und Archive enthalten. Restore zuerst in einen neuen Bereich.

Git bekommt bewusst exportierte Projektstände und Code, nciht ungefragt die laufende DB oder alle Cache-/Bildordner. Keine ungefragten Pushes, fremden Staging-Einträge oder Historienänderungen. Bestehende Repo-/LFS-Regeln werden zuerst gelesen.

## Protokolle

Protokolliere relevante Vorgänge und konkrete Fehler. Geheimnisse oder private lokale Pfade dürfen nciht ungefragt in portable Dokumentation exportiert werden. Das lokale Audit ist nachvollziehbar, aber ohne zusätzliche Infrastruktur nciht als manipulationssicheres Compliance-System zu bezeichnen.
