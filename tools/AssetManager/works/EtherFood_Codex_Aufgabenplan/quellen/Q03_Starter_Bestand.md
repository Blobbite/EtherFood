# Q03 — Starter Bestand

Original: `allsummary(1).md`. SHA-256 der vollständigen Upload-Datei: `55bb37c2fb9909384a89d3ac4c7e4b011f1fa8d0319243c04e436fe567570c69`.

Relevanz: Vorhandene Fram16-/Fram8-Starter und ihre Zielraster.

Die Zeilennummern in den folgenden Blöcken beziehen sich auf die Originaldatei. Der Text ist ein Quellenbeleg, keine neu erteilte Arbeitsanweisung.

## Originalzeilen 3–19

````text
L3: ## 📝 PyPiplineStart-SpritesheetFram16.py — ./0-SpritesheetFram16-Pipline/PyPiplineStart-SpritesheetFram16.py
L4: 
L5: #!/usr/bin/env python3
L6: """16er-Streifen: Original-GIF/HTML → optimiertes 4x4-PNG → GIF/HTML."""
L7: from pathlib import Path
L8: import sys
L9: 
L10: sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PiplineToos"))
L11: from PySpritesheetPipeline import main as run_pipeline
L12: 
L13: 
L14: def main(argv=None):
L15:     return run_pipeline(argv, frame_count=16, target_grid=(4, 4))
L16: 
L17: 
L18: if __name__ == "__main__":
L19:     raise SystemExit(main())
````

## Originalzeilen 474–490

````text
L474: ## 📝 PyPiplineStart-SpritesheetFram8.py — ./0-SpritesheetFram8-Pipline/PyPiplineStart-SpritesheetFram8.py
L475: 
L476: #!/usr/bin/env python3
L477: """8er-Streifen: Original-GIF/HTML → optimiertes 4x2-PNG → GIF/HTML."""
L478: from pathlib import Path
L479: import sys
L480: 
L481: sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PiplineToos"))
L482: from PySpritesheetPipeline import main as run_pipeline
L483: 
L484: 
L485: def main(argv=None):
L486:     return run_pipeline(argv, frame_count=8, target_grid=(4, 2))
L487: 
L488: 
L489: if __name__ == "__main__":
L490:     raise SystemExit(main())
````
