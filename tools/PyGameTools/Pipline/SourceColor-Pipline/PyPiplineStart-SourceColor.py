#!/usr/bin/env python3
"""Source-Einzelbilder mit einer gemeinsamen Farbreferenz vereinheitlichen."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PiplineToos"))
from PyImgColorPipeline import main

if __name__ == "__main__":
    raise SystemExit(main(single_images=True))
