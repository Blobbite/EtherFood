"""Small Python API supplied to each isolated script process (SDK version 1)."""

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from ..domain.assets import require
from ..domain.tool_contract import relative_name


@dataclass(frozen=True)
class Artifact:
    path: Path
    type: str = "file"
    metadata: dict = field(default_factory=dict)


class Context:
    def __init__(self, output, package, resources=None):
        self.output = Path(output)
        self.package = Path(package)
        self.resources = resources or {}

    def path(self, name):
        relative_name(name)
        path = self.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def artifact(self, name, type="file", metadata=None):
        return Artifact(self.path(name), type, deepcopy(metadata or {}))

    def log(self, message):
        print(str(message), flush=True)


def images(artifact):
    """Read a registered image and split its explicit frame grid; never guess it."""
    from PIL import Image
    from .image_processing import split_frames, validate_metadata

    image = Image.open(artifact.path).convert("RGBA")
    validate_metadata(artifact.metadata, image.size)
    return image, split_frames(image, artifact.metadata["grid"])


def sheet(context, frames, metadata, name="image.png", *, grid=None):
    from PIL import Image
    from .image_processing import finish_metadata, validate_metadata

    meta = deepcopy(metadata)
    meta.pop("contract", None)
    meta.pop("image_sha256", None)
    grid = list(grid or meta["grid"])
    require(frames and grid[0] * grid[1] == len(frames), "Raster passt nicht zur Framezahl.")
    size = frames[0].size
    require(all(frame.size == size for frame in frames), "Frames haben verschiedene Größen.")
    image = Image.new("RGBA", (grid[0] * size[0], grid[1] * size[1]))
    for index, frame in enumerate(frames):
        image.paste(frame, (index % grid[0] * size[0], index // grid[0] * size[1]))
    meta.update(grid=grid, frames=len(frames))
    finish_metadata(meta, size)
    validate_metadata(meta, image.size)
    result = context.artifact(
        name, "spritesheet" if meta["kind"] == "spritesheet" else "image", meta
    )
    image.save(result.path, format="PNG")
    return result
