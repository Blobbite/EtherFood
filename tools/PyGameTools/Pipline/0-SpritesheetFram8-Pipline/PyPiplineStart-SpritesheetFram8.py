#!/usr/bin/env python3
"""8er-Streifen: Original-GIF/HTML → optimiertes 4x2-PNG → GIF/HTML."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PiplineToos"))
from PySpritesheetPipeline import main as run_pipeline


def main(argv=None):
    return run_pipeline(argv, frame_count=8, target_grid=(4, 2))


if __name__ == "__main__":
    raise SystemExit(main())
