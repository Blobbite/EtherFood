"""Repository-owned Python algorithms delivered through the same package contract."""

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import sys

from ..domain.pipeline_recipes import BUILTINS, parameter
from ..domain.tool_contract import empty_workflow
from .tool_packages import ToolPackageService


@lru_cache(maxsize=1)
def preview():
    root = Path(__file__).resolve().parents[3] / "PyGameTools/Pipline"
    files = {}
    for folder in ("PiplineToos", "2-SpritesheetResolution-Pipline"):
        files.update({path.name: path.read_bytes() for path in (root / folder).glob("*.py")})
    files["image_steps.py"] = (Path(__file__).parents[1] / "packages/image_steps.py").read_bytes()
    steps = []

    def add(
        key,
        name,
        function,
        *,
        parameters=None,
        inputs=None,
        outputs=None,
        collect=False,
        animated=False,
    ):
        filename = key + ".py"
        files[filename] = (
            "from image_steps import " + function + "\n\n"
            "def run(context, inputs, parameters):\n    return "
            + function
            + "(context, inputs, parameters"
            + (", '" + key + "'" if function == "scale" else "")
            + ")\n"
        ).encode()
        steps.append(
            {
                "id": key,
                "name": name,
                "description": name + " als einzelner Python-Baustein.",
                "source": filename,
                "entry_point": "run",
                "execution": "collect" if collect else "map",
                "capabilities": ["animated"] if animated else [],
                "parameters": parameters or {},
                "inputs": inputs or {"image": {"type": "spritesheet" if animated else "image"}},
                "outputs": outputs
                or {"image": {"type": "image", "directory": "Ergebnisse/{pose}/" + key}},
            }
        )

    for key, name, mode, value in (
        ("comic_high", "Comic High", "factor", 1.0),
        ("comic_mid", "SComicMid · Comic Mid", "factor", 0.5),
        ("comic_low", "SComicLow · Comic Low", "factor", 0.25),
        ("pixel_high", "SPixelHigh · Pixel High", "max_edge", 128),
        ("pixel_low", "SPixelLow · Pixel Low", "factor", 0.9),
    ):
        parameters = {
            "mode": parameter("choice", mode, choices=["factor", "max_edge"]),
            "value": parameter("number", value, minimum=0.001, maximum=16384),
            "profile": parameter("string", key),
            "parent": parameter("string", "pixel_high" if key == "pixel_low" else ""),
        }
        if key == "pixel_high":
            parameters["colors"] = parameter("integer", 64, minimum=2, maximum=256)
            parameters["palette"] = deepcopy(BUILTINS["graphics"]["parameters"]["palette"])
        add(key, name, "scale", parameters=parameters)
    add(
        "grid",
        "PyImgGrid · Raster und Zuschnitt",
        "grid",
        animated=True,
        parameters={
            "columns": parameter("integer", 4, minimum=1, maximum=64),
            "crop": parameter("boolean", True),
        },
    )
    add(
        "frames",
        "Frameauswahl",
        "frames",
        animated=True,
        parameters=deepcopy(BUILTINS["frames"]["parameters"]),
    )
    add(
        "gif",
        "PyImgGif · GIF erzeugen",
        "gif",
        animated=True,
        parameters={
            "source_timing": parameter("boolean", True),
            "fps": parameter("number", 8.0, minimum=0.1, maximum=100),
        },
        outputs={
            "gif": {"type": "gif", "directory": "previews/gif/{pose}"},
            "image": {"type": "image", "publish": False},
        },
    )
    for key, name in (
        ("compare", "PyGraphicsCompare · Grafikvergleich"),
        ("pose_compare", "PyGraphicsPoseCompare · Posenvergleich"),
    ):
        add(
            key,
            name,
            key,
            collect=True,
            parameters={"title": parameter("string", name)},
            inputs={"images": {"type": "file", "multiple": True}},
            outputs={"html": {"type": "html", "directory": "Vergleiche"}},
        )
    add(
        "colors", "Farbverarbeitung", "colors", parameters=deepcopy(BUILTINS["color"]["parameters"])
    )
    flow = empty_workflow()
    source = flow["steps"][0]["id"] = "source"
    spec = {entry["id"]: entry for entry in steps}
    for key in ("comic_high", "comic_mid", "comic_low", "pixel_high", "pixel_low", "compare"):
        entry = spec[key]
        flow["steps"].append(
            {
                "id": key,
                "operation": "local:" + key,
                "enabled": True,
                "parameters": {k: v["default"] for k, v in entry["parameters"].items()},
            }
        )
        if key == "compare":
            for variant in ("comic_high", "comic_mid", "comic_low", "pixel_high", "pixel_low"):
                flow["connections"].append(
                    {"from": variant, "out": "image", "to": key, "in": "images"}
                )
        else:
            flow["connections"].append(
                {
                    "from": "pixel_high" if key == "pixel_low" else source,
                    "out": "image",
                    "to": key,
                    "in": "image",
                }
            )
        for port, output in entry["outputs"].items():
            flow["outputs"][key] = {"node": key, "port": port, **output}
    manifest = {
        "contract": "studio-tool-package-v1",
        "id": "etherfood-images",
        "version": "1.0.0",
        "name": "EtherFood · Bildwerkzeuge",
        "description": "Kleine kombinierbare Bild- und Animationsschritte.",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "dependencies": ["Pillow==12.1.1"],
        "files": sorted(files),
        "steps": steps,
        "flows": [
            {
                "id": "resolution",
                "name": "Spritesheet-Auflösungen",
                "description": "Comic- und Pixelvarianten mit anschließendem Vergleich.",
                "recipe": flow,
            }
        ],
    }
    return ToolPackageService.inspect_content(manifest, files)


def ensure(project):
    service = ToolPackageService(project)
    return service.register(preview(), bundled=True)
