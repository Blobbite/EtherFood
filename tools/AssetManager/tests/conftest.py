"""Synthetic fixtures; no dependency on real game graphics."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture
def tiny_sheet(tmp_path):
    from PIL import Image

    path = tmp_path / "Grüne Quelle #1 100%.png"
    image = Image.new("RGBA", (16, 8), (60, 180, 40, 255))
    image.putpixel((0, 0), (10, 20, 30, 0))
    image.save(path)
    return path
