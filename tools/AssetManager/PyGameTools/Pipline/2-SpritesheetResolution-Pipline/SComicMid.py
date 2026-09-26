#!/usr/bin/env python3
"""HD-Spritesheets nach comic_mid: standardmäßig 50 Prozent pro Frame."""


def resize_frame(frame, size):
    """Lanczos mit vormultipliziertem Alpha verhindert dunkle Transparenzsäume."""
    from PIL import Image

    return frame.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")


if __name__ == "__main__":
    from importlib import import_module

    main = import_module("PyPiplineStart-SpritesheetResolution").main

    raise SystemExit(main(only="comic_mid"))
