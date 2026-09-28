"""A second importable v2 package: select original frames and preserve explicit timing."""

from etherfood_studio.pipelines.image_processing import transform


def apply(image, metadata, parameters):
    image, result = transform(image, metadata, "frames", parameters, {})
    return image, {key: result[key] for key in ("grid", "source_indices", "fps", "timing_mode")}
