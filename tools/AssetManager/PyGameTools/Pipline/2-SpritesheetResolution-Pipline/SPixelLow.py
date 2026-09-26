#!/usr/bin/env python3
"""Pixel Low: 90 Prozent der Pixel-High-Größe, standardmäßig dieselbe Palette."""

if __package__:
    from . import SPixelHigh
else:
    import SPixelHigh


def convert_sheet(image, grid, high_size, low_size, colors, palette=None):
    """High aus HD reproduzieren, dann ohne neue Farben frameweise verkleinern.

    Die vorhandene High-Datei wird weder verändert noch vorausgesetzt.
    Eine zweite unabhängige Quantisierung auf 16 Farben entfällt.
    """
    from PIL import Image

    columns, rows = grid
    cell_w, cell_h = image.width // columns, image.height // rows
    high_w, high_h = high_size
    low_w, low_h = low_size
    with Image.new("RGBA", (columns * high_w, rows * high_h)) as high:
        for row in range(rows):
            for column in range(columns):
                with image.crop((column * cell_w, row * cell_h,
                                 (column + 1) * cell_w, (row + 1) * cell_h)) as frame:
                    with SPixelHigh.resize_frame(frame, high_size) as resized:
                        high.paste(resized, (column * high_w, row * high_h))
        with SPixelHigh.finish_sheet(high, colors, palette=palette) as indexed:
            output = Image.new("RGBA", (columns * low_w, rows * low_h))
            for row in range(rows):
                for column in range(columns):
                    with indexed.crop((column * high_w, row * high_h,
                                       (column + 1) * high_w, (row + 1) * high_h)) as frame:
                        with frame.resize(low_size, Image.Resampling.NEAREST) as resized:
                            output.paste(resized, (column * low_w, row * low_h))
    return output


if __name__ == "__main__":
    from importlib import import_module

    main = import_module("PyPiplineStart-SpritesheetResolution").main

    raise SystemExit(main(only="pixel_low"))
