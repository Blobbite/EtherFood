"""Alternative source preparation and explicit frame selection/timing."""

from ...pipelines.image_processing import expected_metadata, legacy_modules, split_frames


def apply(image, metadata, operation, parameters, resources, profile):
    grid, selection, _, _, _, _ = legacy_modules()
    meta = expected_metadata(image, metadata, operation, parameters, profile)
    frames = split_frames(image, metadata["grid"])
    if operation.startswith("prepare"):
        box = grid.get_common_content_box(frames)
        frames = [frame.crop(box) for frame in frames]
    else:
        frames = [frames[i] for i in selection.uniform_indices(len(frames), parameters["frames"])]
    return grid.pack_frames(frames, tuple(meta["grid"]), optimize=False), meta
