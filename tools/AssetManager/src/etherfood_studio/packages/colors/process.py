"""Alternative soft/fixed/material modes; label masks follow source geometry."""

from ...pipelines.image_processing import expected_metadata, legacy_modules, material_mask


def apply(image, metadata, operation, parameters, resources, profile):
    _, _, _, _, soft, exact = legacy_modules()
    meta = expected_metadata(image, metadata, operation, parameters, profile)
    mode = parameters["mode"]
    if mode == "soft":
        matcher = soft.ColorMatcher(soft.load_profile(resources["reference"]),
                                    parameters["strength"], parameters["max_distance"])
        image = matcher.apply(image)
    elif mode == "fixed":
        palette = exact.load_palette(resources["palette"])
        image = exact.FixedMatcher(palette).apply(image)
        exact.verify_palette(image, palette)
    else:
        palette = exact.load_material_profile(resources["materials"])
        mask = material_mask(resources["mask"], resources["original"], meta, palette)
        exact.validate_labels(mask, image, palette["materials"], grid=tuple(meta["grid"]))
        image = exact.MaterialMatcher(palette).apply(image, mask)
        exact.verify_palette(image, palette, mask)
    return image, meta
