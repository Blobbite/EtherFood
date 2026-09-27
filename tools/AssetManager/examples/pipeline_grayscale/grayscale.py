"""Optional trusted extension; no side effects on import or changes to input geometry."""

from PIL import Image, ImageOps


def apply(image, parameters):
    rgb = image.convert("RGB")
    gray = ImageOps.grayscale(rgb).convert("RGB")
    result = Image.blend(rgb, gray, float(parameters["amount"])).convert("RGBA")
    result.putalpha(image.getchannel("A"))
    return result
