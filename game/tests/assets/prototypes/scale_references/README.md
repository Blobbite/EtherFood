# Originale Größenreferenz-Prototypassets

Die PNG-Dateien in diesem Ordner sind originale EtherFood-Prototypgrafiken.
Sie werden ausschließlich aus fest definierten Pixelprimitiven erzeugt:

```bash
python game/tools/generate_scale_reference_assets.py
python game/tools/generate_scale_reference_assets.py --check
python game/tools/generate_scale_reference_assets.py --preview-output /tmp/scale-row.png
```

Das Hilfsskript verwendet nur die Python-Standardbibliothek, greift nicht auf
das Netzwerk zu und erzeugt bei identischen Eingaben bytegleiche Dateien. Die
Figuren und Weltobjekte werden zunächst aus groben Silhouetten aufgebaut,
anschließend auf einem feineren Raster mit Materialpixeln versehen und ohne
Kantenglättung einheitlich vergrößert. Die sichtbare Alpha-Höhe endet jeweils
am unteren mittigen Bodenanker. Das Skript ist kein Bestandteil der
Spiel-Laufzeit. Es erzeugt außerdem die paarigen Prototypassets unter
`../world_states/`.
