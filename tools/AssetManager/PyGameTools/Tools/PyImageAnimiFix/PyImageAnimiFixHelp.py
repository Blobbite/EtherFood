#!/usr/bin/env python3
"""Bereichshilfe und Kurzbeschreibungen für das Auswahlmenü."""


SCRIPT_DESCRIPTIONS = {'PyImgAnimFix.py': 'Gezielte Loop-Fixes mit unveränderter Framezahl, einschließlich 16, 12, 10 und 8 Frames.', 'PyImgAnimFixDropEnd.py': 'Separater Notfall-Fix: doppelte Schlussposen entfernen und die Framezahl reduzieren.', 'PyImageAnimiFix.py': 'dieses Menü; Werkzeuge auswählen und starten', 'PyImageAnimiFixHelp.py': 'Hilfe zu den Werkzeugen und zum Auswahlmenü anzeigen'}

MENU_HELP = 'Auswahlmenü PyImageAnimiFix\nStart: python3 /pfad/PyImageAnimiFix/PyImageAnimiFix.py\nPfeiltasten hoch/runter wählen, Enter startet, Q oder Escape beendet.\nDer eigene Menüeintrag aktualisiert die Auswahl. Lange Listen sind scrollbar.\nNach einem Lauf bleibt die Ausgabe stehen; Enter lädt die Auswahl neu.\n--plain: Nummernauswahl; --list: nur Liste; --dir ORDNER: anderer Skriptordner.\n--help: Bedienung. Ohne interaktive Eingabe erscheint nur die Liste,\naußer bei ausdrücklich gewähltem --plain. Bei einfachen Terminals Nummernauswahl.\nNeue .py-Dateien direkt im Skriptordner erscheinen automatisch, keine Unterordner.\nKurztexte stammen aus dieser Hilfe, sonst aus dem Modul-Docstring.\nDer Python-Interpreter, die Umgebung und der Arbeitsordner bleiben erhalten.\nDas Menü benötigt keine Zusatzpakete; die Werkzeuge haben eigene Abhängigkeiten.\nSkripte starten ohne zusätzliche Argumente. Für Werkzeuge mit Pflichtoptionen\n(z.B. PyImgGif --fps 8) den direkten Skriptaufruf mit den gewünschten Optionen nutzen.\n'

if __name__ == "__main__":
    print(MENU_HELP)
    for name, description in sorted(SCRIPT_DESCRIPTIONS.items()):
        print(f"{name[:-3]} --> für {description}")
