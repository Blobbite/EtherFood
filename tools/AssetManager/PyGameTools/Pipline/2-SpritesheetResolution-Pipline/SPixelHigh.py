#!/usr/bin/env python3
"""HD nach pixel_high: maximal 128 Pixel pro Frame-Seite, bis zu 64 Farben."""


def resize_frame(frame, size):
    """Flächenfarben auf dem kleinen Pixelraster mitteln; Alpha binarisieren."""
    from PIL import Image

    result = frame.convert("RGBa").resize(size, Image.Resampling.BOX).convert("RGBA")
    result.putalpha(result.getchannel("A").point([0] * 128 + [255] * 128))
    return result


def finish_sheet(sheet, colors, palette=None):
    """Eine Palette für alle Frames; kein Dithering und kein Weichzeichnen."""
    from PIL import Image

    alpha = sheet.getchannel("A")
    rgb = sheet.convert("RGB")
    rgb.paste((0, 0, 0), (0, 0), alpha.point([255] + [0] * 255))
    if palette is None:
        result = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                              dither=Image.Dither.NONE).convert("RGBA")
    else:
        from PyImgColorMatch import palette_image
        with palette_image({"pixel_palette": list(palette)}) as fixed:
            result = rgb.quantize(palette=fixed, dither=Image.Dither.NONE).convert("RGBA")
    result.putalpha(alpha)
    return result


if __name__ == "__main__":
    from importlib import import_module

    main = import_module("PyPiplineStart-SpritesheetResolution").main

    raise SystemExit(main(only="pixel_high"))
