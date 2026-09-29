"""Synthetic legacy bundle fixtures retained only for migration tests."""

from copy import deepcopy
from importlib.metadata import distribution
import json
import sys
import zipfile
from PIL import Image
import pytest
from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.tool_environments import ToolEnvironments
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.sources import expected_sources


from pathlib import Path
from etherfood_studio.application.plugin_service import PluginService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.domain.pipeline_recipes import BUILTINS, step
from etherfood_studio.pipelines.image_processing import legacy_modules
from etherfood_studio.storage.blob_store import BlobStore
from etherfood_studio.storage.sqlite_repository import canonical

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/pipeline_scale/manifest.json"


@pytest.fixture
def studio(tmp_path):
    root = tmp_path / "studio"
    root.mkdir()
    project = ProjectService.new(root, "Ablaufeditor")
    yield project
    project.catalog.close()


def example():
    manifest = {
        "contract": "studio-tool-package-v1",
        "id": "report",
        "name": "Dateibericht",
        "version": "1.0.0",
        "description": "Dateien maschinell verarbeiten",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "dependencies": [],
        "files": ["report.py", "helper.py"],
        "flows": [],
        "steps": [
            {
                "id": "report",
                "name": "Bericht",
                "description": "Berichtet Größe",
                "source": "report.py",
                "entry_point": "run",
                "execution": "map",
                "capabilities": [],
                "parameters": {},
                "inputs": {"image": {"type": "image"}},
                "outputs": {"report": {"type": "json", "directory": "Ergebnisse/Berichte"}},
            }
        ],
    }
    files = {
        "helper.py": b"def size(path):\n    return path.stat().st_size\n",
        "report.py": b"import json\nfrom helper import size\n"
        b"def run(context, inputs, parameters):\n"
        b"    result = context.artifact('report.json', 'json')\n"
        b"    result.path.write_text(json.dumps({'bytes': size(inputs['image'].path)}))\n"
        b"    return {'report': result}\n",
    }
    return manifest, files


def source_asset(project, tmp_path):
    assets = AssetService(project)
    owner = next(row.id for row in project.cards() if row.kind == "global")
    asset = assets.create("Quelle", owner, default_definition("texture").to_data())
    path = tmp_path / "original.png"
    Image.new("RGBA", (16, 8), (20, 40, 80, 200)).save(path)
    imports = SourceImportService(assets)
    key = expected_sources(assets.definition(asset.id))[0]
    imports.import_plan(
        imports.prepare(asset.id, asset.revision_no, [SourceSpec(path, key, 1, 1, 1)])
    )
    return asset, path


@pytest.fixture
def offline_pillow(tmp_path, monkeypatch):
    """Build a wheel from the installed dependency; tests never use a package index."""
    dist = distribution("Pillow")
    tag = next(
        line[5:] for line in dist.read_text("WHEEL").splitlines() if line.startswith("Tag: ")
    )
    wheel = tmp_path / f"pillow-{dist.version}-{tag}.whl"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in dist.files:
            if str(item).startswith("..") or str(item).endswith(".pyc"):
                continue
            path = dist.locate_file(item)
            if path.is_file():
                archive.write(path, str(item))
    original = ToolEnvironments.command

    def local(argv, on_output):
        if "pip" in argv and "install" in argv:
            argv = [*argv, "--no-index", "--find-links", str(tmp_path)]
        return original(argv, on_output)

    monkeypatch.setattr(ToolEnvironments, "command", staticmethod(local))


def import_scale(project, manifest=EXAMPLE, *, approve=True):
    service = PluginService(project)
    package = service.package(manifest)
    recipe = service.import_package(
        manifest, package["manifest"], package["code_hash"], "Skalierung"
    )
    if approve:
        service.approve(package["manifest"]["id"], package["code_hash"])
    return recipe


def asset(project, tmp_path, owner, title="Wächter", *, animated=False):
    service = AssetService(project)
    definition = default_definition("effect" if animated else "texture").to_data()
    if animated:
        definition["poses"] = definition["poses"][:1]
        definition["poses"][0]["fps"] = 8.0
    record = service.create(title, owner, definition)
    source = tmp_path / (record.id + ".png")
    frames = 16 if animated else 1
    image = Image.new("RGBA", (512 * frames, 256), (20, 150, 30, 127))
    for i in range(frames):
        image.paste((i * 15, 150, 30, 127), (i * 512, 0, (i + 1) * 512, 256))
    image.save(source)
    imports = SourceImportService(service)
    key = expected_sources(service.definition(record.id))[0]
    imports.import_plan(
        imports.prepare(record.id, record.revision_no, [SourceSpec(source, key, frames, 1, frames)])
    )
    return record, source


def asset_source(project, tmp_path, *, count=1, size=(8, 4), margins=False, alpha=255):
    assets = AssetService(project)
    data = default_definition("texture" if count == 1 else "effect").to_data()
    if count > 1:
        data["poses"] = data["poses"][:1]
        data["poses"][0]["fps"] = 8.0
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("Synthetisches Bild", owner, data)
    image = Image.new("RGBA", (size[0] * count, size[1]))
    for index in range(count):
        frame = Image.new("RGBA", size)
        rect = (2, 1, size[0] - 2, size[1] - 1) if margins else (0, 0, *size)
        frame.paste((40 + index * 10, 80, 160, alpha), rect)
        image.paste(frame, (index * size[0], 0))
    path = tmp_path / (asset.id + ".png")
    image.save(path)
    imports = SourceImportService(assets)
    key = expected_sources(assets.definition(asset.id))[0]
    imports.import_plan(
        imports.prepare(asset.id, asset.revision_no, [SourceSpec(path, key, count, 1, count)])
    )
    return asset, path


def recipe_for(project, asset, template, edit=None):
    service = PipelineService(project)
    record = service.create("Bildrezept", template)
    if edit:
        recipe = deepcopy(record.data["recipe"])
        edit(recipe)
        record = service.save(record.id, recipe, record.revision_no)
    service.assign(record.id, asset_id=asset.id)
    return record


def append_step(recipe, operation, *, enabled=True, parameters=None):
    node = step(operation, BUILTINS[operation])
    node["enabled"] = enabled
    node["parameters"].update(parameters or {})
    recipe["connections"].append(
        {"from": recipe["steps"][-1]["id"], "out": "image", "to": node["id"], "in": "image"}
    )
    recipe["steps"].append(node)
    return node


def resource(project, recipe, key, path):
    blob = BlobStore(project.catalog, project.catalog.path.parent).import_file(path)
    recipe["resources"][key] = {
        "sha256": blob["sha256"],
        "length": blob["length"],
        "name": path.name,
    }
    return key


def palette_file(tmp_path, *, mode="fixed", colors=None):
    _, _, _, _, soft, exact = legacy_modules()
    colors = colors or [[12, 24, 36], [100, 120, 140]]
    refs = [
        {
            "path": "stand.png",
            "direction": direction,
            "sha256": "0" * 64,
            "size": [8, 4],
            "grid": [1, 1],
            "frames": 1,
        }
        for direction in soft.DIRECTIONS
    ]
    if mode == "soft":
        value = {
            "format": soft.FORMAT,
            "version": 1,
            "method": soft.METHOD,
            "references": refs,
            "colors": colors,
            "pixel_palette": colors,
        }
    else:
        value = {
            "format": exact.FIXED_FORMAT if mode == "fixed" else exact.MATERIAL_FORMAT,
            "version": 1,
            "color_space": "sRGB",
            "references": refs,
        }
        value.update(
            {"colors": colors}
            if mode == "fixed"
            else {"materials": [{"id": 1, "name": "Gewebe", "colors": colors}]}
        )
    path = tmp_path / (mode + ".json")
    path.write_text(canonical(value), encoding="utf-8")
    return path
