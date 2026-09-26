#!/usr/bin/env python3
"""HD-Spritesheets direkt nach comic_low: standardmäßig 25 Prozent pro Frame."""


def resize_frame(frame, size):
    """Jeder Frame wird direkt aus HD mit alphagewichtetem Lanczos verkleinert."""
    from PIL import Image

    return frame.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")


if __name__ == "__main__":
    from importlib import import_module

    main = import_module("PyPiplineStart-SpritesheetResolution").main

    raise SystemExit(main(only="comic_low"))
