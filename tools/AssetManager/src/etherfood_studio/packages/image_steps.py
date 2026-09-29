"""Portable microsteps shipped in the image toolkit; each entry has one responsibility."""

from copy import deepcopy
import base64

from etherfood_studio.pipelines.tool_sdk import images, sheet


def scale(context, inputs, settings, variant):
    from PIL import Image
    import SComicLow
    import SComicMid
    import SPixelHigh
    from etherfood_studio.domain.graphics import proportional_size

    artifact = inputs["image"]
    _, frames = images(artifact)
    size = proportional_size(*frames[0].size, settings["mode"], settings["value"])
    if variant == "pixel_low":
        if artifact.metadata["profile"] != settings["parent"]:
            raise ValueError("Pixel Low benötigt den verbundenen Pixel-High-Baustein.")
        frames = [frame.resize(size, Image.Resampling.NEAREST) for frame in frames]
    elif variant == "pixel_high":
        frames = [SPixelHigh.resize_frame(frame, size) for frame in frames]
    else:
        module = SComicLow if variant == "comic_low" else SComicMid
        frames = [module.resize_frame(frame, size) for frame in frames]
    meta = deepcopy(artifact.metadata)
    meta["profile"] = settings["profile"]
    result = sheet(context, frames, meta, variant + ".png")
    if variant == "pixel_high":
        import PyImgFixedColors

        palette = (
            PyImgFixedColors.load_palette(context.resources[settings["palette"]])["colors"]
            if settings["palette"]
            else None
        )
        with Image.open(result.path) as image:
            reduced = SPixelHigh.finish_sheet(image.convert("RGBA"), settings["colors"], palette)
            reduced.save(result.path)
    return {"image": result}


def grid(context, inputs, settings):
    import PyImgGrid

    artifact = inputs["image"]
    _, frames = images(artifact)
    meta = deepcopy(artifact.metadata)
    columns = settings["columns"]
    if len(frames) % columns:
        raise ValueError("Die Framezahl muss durch die Spaltenzahl teilbar sein.")
    if settings["crop"]:
        box = PyImgGrid.get_common_content_box(frames)
        if box is None:
            raise ValueError("Alle Frames sind transparent.")
        old_size = meta["frame_size"]
        factors = [meta["crop_size"][i] / old_size[i] for i in (0, 1)]
        meta["crop_offset"] = [meta["crop_offset"][i] + box[i] * factors[i] for i in (0, 1)]
        meta["crop_size"] = [(box[i + 2] - box[i]) * factors[i] for i in (0, 1)]
        frames = [frame.crop(box) for frame in frames]
    return {
        "image": sheet(context, frames, meta, "grid.png", grid=[columns, len(frames) // columns])
    }


def frames(context, inputs, settings):
    import PyImgFrameSelect

    artifact = inputs["image"]
    _, source = images(artifact)
    indices = PyImgFrameSelect.uniform_indices(len(source), settings["frames"])
    meta = deepcopy(artifact.metadata)
    meta["source_indices"] = [meta["source_indices"][i] for i in indices]
    count = len(indices)
    meta["fps"] = (
        count / meta["duration"] if settings["timing"] == "keep_duration" else settings["fps"]
    )
    meta.update(duration=count / meta["fps"], timing_mode=settings["timing"])
    target = {8: [4, 2], 10: [5, 2], 12: [4, 3], 14: [7, 2], 16: [4, 4]}.get(count, [count, 1])
    return {"image": sheet(context, [source[i] for i in indices], meta, "frames.png", grid=target)}


def gif(context, inputs, settings):
    import PyImgGif

    artifact = inputs["image"]
    _, frames = images(artifact)
    fps = artifact.metadata["fps"] if settings["source_timing"] else settings["fps"]
    output = context.artifact(
        "preview.gif", "gif", {**artifact.metadata, "fps": fps, "duration": len(frames) / fps}
    )
    PyImgGif.save_gif(frames, output.path, fps, loop=artifact.metadata["loop"])
    source = context.artifact("image.png", artifact.type, artifact.metadata)
    source.path.write_bytes(artifact.path.read_bytes())
    return {"gif": output, "image": source}


def compare(context, inputs, settings, *, positions=False):
    """Use the existing interactive comparisons with self-contained image data."""
    import PyGraphicsCompare
    import PyGraphicsPoseCompare
    import PyImgGif

    groups, variants = {}, set()
    for artifact in inputs["images"]:
        if artifact.type not in {"image", "spritesheet", "gif"}:
            raise ValueError("Der Vergleich benötigt PNG- oder GIF-Eingänge.")
        meta = artifact.metadata
        if not meta:
            raise ValueError("Vergleichsbilder benötigen Raster- und Herkunftsmetadaten.")
        slot = meta["slot"]
        pose = slot.get("pose_id") or "Einzelbild"
        direction = slot.get("direction") or "?"
        variant = meta["profile"]
        variants.add(variant)
        key = (pose, meta["frames"])
        group = groups.setdefault(
            key,
            {
                "folder": pose,
                "family": pose,
                "frames": meta["frames"],
                "single": meta["kind"] != "spritesheet",
                "directions": {},
            },
        )
        tracks = group["directions"].setdefault(direction, {})
        if variant in tracks:
            raise ValueError(
                "Mehrdeutiger Vergleich: gleicher Eingang für Pose, Richtung und Variante."
            )
        raw = base64.b64encode(artifact.path.read_bytes()).decode("ascii")
        if artifact.type == "gif":
            item = PyImgGif.read_gif_for_gallery(artifact.path)
            item.update(gif="data:image/gif;base64," + raw, columns=None, rows=None)
        else:
            count = meta["frames"]
            fps = meta.get("fps", 8)
            durations = [1000 / fps] * count
            item = {
                "name": artifact.path.name,
                "width": meta["frame_size"][0],
                "height": meta["frame_size"][1],
                "bytes": artifact.path.stat().st_size,
                "sheet": "data:image/png;base64," + raw,
                "columns": meta["grid"][0],
                "rows": meta["grid"][1],
                "gif": None,
                "gifName": None,
                "durations": durations,
                "frameMap": list(range(count)),
                "storedFrames": count,
                "logicalFrames": count,
                "durationMs": sum(durations),
                "exportFps": None,
                "previewFps": fps,
                "filenameFps": None,
                "notes": [],
            }
        item["bounds"] = (
            PyGraphicsPoseCompare.content_bounds(artifact.path, item) if positions else []
        )
        tracks[variant] = item
    labels = dict(PyGraphicsCompare.VARIANTS)
    ordered = [key for key in labels if key in variants] + sorted(variants - labels.keys())
    for group in groups.values():
        for tracks in group["directions"].values():
            reference = tracks.get("comic_high") or max(
                tracks.values(), key=lambda item: item["width"] * item["height"]
            )
            for item in tracks.values():
                item.update(
                    referenceWidth=reference["width"],
                    referenceHeight=reference["height"],
                    hasHDReference="comic_high" in tracks,
                )
            for key in ordered:
                tracks.setdefault(
                    key, {"missing": True, "reason": "Dieser Bausteinausgang ist nicht verbunden."}
                )
    payload = {
        "title": settings["title"],
        "created": "Ablaufeditor",
        "fps": 8,
        "fpsChoices": PyImgGif.FPS_CHOICES,
        "directions": list(PyGraphicsCompare.DIRECTIONS) + ["?"],
        "variants": [{"id": key, "label": labels.get(key, key)} for key in ordered],
    }
    if positions:
        payload["poses"] = [
            {
                "name": pose,
                "sets": [group for (key, _), group in groups.items() if key == pose],
                "comparison": "",
            }
            for pose in sorted({key[0] for key in groups})
        ]
        content = PyGraphicsPoseCompare.HTML_TEMPLATE.replace(
            "__POSE_DATA__", PyImgGif.script_safe_json(payload)
        )
    else:
        payload["sets"] = list(groups.values())
        content = PyGraphicsCompare.HTML_TEMPLATE.replace(
            "__COMPARISON_DATA__", PyImgGif.script_safe_json(payload)
        )
    output = context.artifact(
        "positionsvergleich.html" if positions else "aufloesungsvergleich.html", "html"
    )
    output.path.write_text(content, encoding="utf-8")
    return {"html": output}


def pose_compare(context, inputs, settings):
    return compare(context, inputs, settings, positions=True)


def colors(context, inputs, settings):
    """Color mode resources are explicit inputs; source pixels stay in the job copy."""
    import PyImgColorMatch as soft
    import PyImgFixedColors as exact

    artifact = inputs["image"]
    image, _ = images(artifact)
    if settings["mode"] == "soft":
        image = soft.ColorMatcher(
            soft.load_profile(context.resources[settings["reference"]]),
            settings["strength"],
            settings["max_distance"],
        ).apply(image)
    elif settings["mode"] == "fixed":
        palette = exact.load_palette(context.resources[settings["palette"]])
        image = exact.FixedMatcher(palette).apply(image)
        exact.verify_palette(image, palette)
    else:
        from etherfood_studio.pipelines.image_processing import material_mask

        palette = exact.load_material_profile(context.resources[settings["materials"]])
        mask = material_mask(
            context.resources[settings["mask"]],
            context.resources["original"],
            artifact.metadata,
            palette,
        )
        image = exact.MaterialMatcher(palette).apply(image, mask)
        exact.verify_palette(image, palette, mask)
    output = context.artifact("colors.png", artifact.type, artifact.metadata)
    image.save(output.path)
    return {"image": output}
