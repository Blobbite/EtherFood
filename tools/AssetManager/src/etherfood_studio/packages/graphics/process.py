"""Frame-wise comic/pixel scaling with the existing PyGameTools algorithms."""

from PIL import Image

from ...pipelines.image_processing import expected_metadata, legacy_modules, split_frames


def apply(image, metadata, operation, parameters, resources, profile):
    grid, _, comic, pixel, _, exact = legacy_modules()
    meta = expected_metadata(image, metadata, operation, parameters, profile)
    frames = split_frames(image, metadata["grid"])
    size, method = tuple(meta["frame_size"]), profile["method"]
    if method == "pixel_low":
        frames = [frame.resize(size, Image.Resampling.NEAREST) for frame in frames]
    elif method == "pixel":
        frames = [pixel.resize_frame(frame, size) for frame in frames]
    else:
        frames = [frame.copy() if frame.size == size else comic.resize_frame(frame, size)
                  for frame in frames]
    image = grid.pack_frames(frames, tuple(meta["grid"]), optimize=False)
    if method == "pixel":
        palette = exact.load_palette(resources["palette"])["colors"] \
            if "palette" in resources else None
        image = pixel.finish_sheet(image, profile["colors"], palette)
    return image, meta
