# Entscheidung 0001: lokaler Katalog mit getrennten Ansichten

Status: angenommen für Pakete 1–4. Keine Änderung des Spielkanons.

SQLite ist die aktive Metadatenbasis: Fremdschlüssel, kurze Transaktionen,
Migrationen mit SQLite-Backup und Revisionskonflikte werden benötigt.
Ein Netzwerk-/Mehrbenutzerdienst würde den beauftragten Umfang überschreiten.
Lesbare JSON-Snapshots sind ausdrücklich exportiert/importiert, nicht
automatisch mit `asset.json` oder Markdown-Dateien synchronisiert.

PySide6 ist ausschließlich UI-Abhängigkeit. Der Kern läuft ohne Qt und ohne
Godot. Das neue Paket liegt neben PyGameTools; historische Starter werden
nicht allein für einen schöneren Namen umbenannt.

Canvas-Layout ist eine Ansicht. Herkunft, Verwendung und technische
Abhängigkeit bleiben verschiedene Beziehungen. Deshalb verändern weder
Kartenbewegung noch Fensterpräferenzen Asset-Revisionen oder Builds.

Unveränderliche Originalkopien sind inhaltsadressiert; variable Anzeigenamen
werden nicht zu Dateipfaden. Unterbrochene Importe bleiben über ein Journal
nachvollziehbar. Es gibt keine automatische Löschung verwaister Dateien.
