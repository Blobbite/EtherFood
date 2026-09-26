#!/usr/bin/env python3
"""Spritesheet-Farbkorrektur: gemeinsamer Kern in PiplineToos."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PiplineToos"))
from PyImgColorPipeline import *

if __name__ == "__main__":
    raise SystemExit(main())
