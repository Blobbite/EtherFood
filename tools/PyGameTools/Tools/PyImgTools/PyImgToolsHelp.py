#!/usr/bin/env python3
"""Bereichshilfe und Kurzbeschreibungen für das Auswahlmenü."""


SCRIPT_DESCRIPTIONS = {'PyImg2x3.py': 'sechs horizontale Frames in ein 2x3-Spritesheet umordnen', 'PyImgGrid.py': 'gemeinsamer Raster-Optimierer unter Pipline/PiplineToos; Framezahl, Quell- und Zielraster vorgeben', 'PyImgAlpha.py': 'PyImgAlpha: helle, dunkle oder graue Hintergründe transparent machen.', 'PyImgConvert.py': 'Bilddateien in andere Formate konvertieren', 'PyImgGif.py': 'Spritesheets oder Einzelbilder im aktuellen Arbeitsordner zu GIFs animieren.', 'PyImgScal.py': 'Bilder auf eine genaue Größe skalieren und Klarheit anpassen', 'PyImgSplitA.py': 'PNG-Spritesheets automatisch in einzelne Sprites trennen', 'PyImgTestColor.py': 'Eigenständiger Farbwirkungstest mit portabler JSON-Übergabe.', 'PyImgTools.py': 'dieses Menü; Werkzeuge auswählen und starten', 'PyImgToolsHelp.py': 'Hilfe zu den Werkzeugen und zum Auswahlmenü anzeigen'}

MENU_HELP = 'Auswahlmenü PyImgTools\nStart: python3 /pfad/PyImgTools/PyImgTools.py\nPfeiltasten hoch/runter wählen, Enter startet, Q oder Escape beendet.\nDer eigene Menüeintrag aktualisiert die Auswahl. Lange Listen sind scrollbar.\nNach einem Lauf bleibt die Ausgabe stehen; Enter lädt die Auswahl neu.\n--plain: Nummernauswahl; --list: nur Liste; --dir ORDNER: anderer Skriptordner.\n--help: Bedienung. Ohne interaktive Eingabe erscheint nur die Liste,\naußer bei ausdrücklich gewähltem --plain. Bei einfachen Terminals Nummernauswahl.\nNeue .py-Dateien direkt im Skriptordner erscheinen automatisch, keine Unterordner.\nKurztexte stammen aus dieser Hilfe, sonst aus dem Modul-Docstring.\nDer Python-Interpreter, die Umgebung und der Arbeitsordner bleiben erhalten.\nDas Menü benötigt keine Zusatzpakete; die Werkzeuge haben eigene Abhängigkeiten.\nSkripte starten ohne zusätzliche Argumente. Für Werkzeuge mit Pflichtoptionen\n(z.B. PyImgGif --fps 8) den direkten Skriptaufruf mit den gewünschten Optionen nutzen.\n'

if __name__ == "__main__":
    print(MENU_HELP)
    for name, description in sorted(SCRIPT_DESCRIPTIONS.items()):
        print(f"{name[:-3]} --> für {description}")
