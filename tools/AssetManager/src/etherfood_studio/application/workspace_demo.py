"""Explicit, repeatable synthetic examples using the current script/pipeline contract."""

from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from ..domain.assets import default_definition
from ..domain.pipeline_contract import INPUT, empty_definition
from ..domain.sources import expected_sources
from .asset_service import AssetService
from .pipeline_workspace import PipelineWorkspace
from .source_import import SourceImportService, SourceSpec
from .workspace_files import WorkspaceFiles

COPY = """def run(context, inputs, parameters):
    source = inputs["image"]
    result = context.artifact("spritesheet.png", source.type, source.metadata)
    result.path.write_bytes(source.path.read_bytes())
    return {"image": result}
"""
GIF = """from etherfood_studio.pipelines.tool_sdk import images


def run(context, inputs, parameters):
    source = inputs["image"]
    image, frames = images(source)
    if len(frames) < 2 or source.metadata.get("fps", 0) <= 0:
        raise ValueError("Animiertes Spritesheet mit gültigen Timingdaten erforderlich")
    result = context.artifact("animation.gif", "gif", source.metadata)
    options = {"save_all": True, "append_images": frames[1:],
               "duration": round(1000 / source.metadata["fps"]), "disposal": 2}
    if source.metadata.get("loop"):
        options["loop"] = 0
    frames[0].save(result.path, format="GIF", **options)
    image.close()
    for frame in frames:
        frame.close()
    return {"animation": result}
"""


class WorkspaceDemo:
    def __init__(self, project):
        self.project, self.catalog = project, project.catalog

    def create(self):
        project = self.project.project()
        previous = project.data.get("synthetic_workspace_demo")
        if previous:
            return {**previous, "existing": True}
        assets = AssetService(self.project)
        files = WorkspaceFiles(self.project)
        workspace = PipelineWorkspace(self.project)
        with self.catalog.transaction():
            act = self.project.create_card("act", "Demo: Akt 1", project.id)
            one = self.project.create_card("chapter", "Demo: Kapitel 1", act.id)
            two = self.project.create_card("chapter", "Demo: Kapitel 2", act.id)
            package = self.project.create_card("package", "Demo: Testpaket", one.id)
            values = {}
            with TemporaryDirectory(prefix="studio-demo-") as folder:
                for key, title, type_id, owner in (
                    ("hero", "Demo: rote Animation", "effect", package.id),
                    ("effect", "Demo: blaue Animation", "effect", package.id),
                    ("texture", "Demo: Einzelbild", "texture", two.id),
                ):
                    asset = assets.create(title, owner, default_definition(type_id).to_data())
                    values[key] = asset.id
                    definition = assets.definition(asset.id)
                    source_key = expected_sources(definition)[0]
                    count = 1 if type_id == "texture" else 8
                    image = Image.new("RGBA", (8 * count, 8))
                    for frame in range(count):
                        color = (
                            ((40 + frame * 25) % 255, 40, 180, 255)
                            if key == "effect"
                            else (220, (20 + frame * 25) % 255, 30, 255)
                        )
                        image.paste(color, (frame * 8, 0, (frame + 1) * 8, 8))
                    path = Path(folder) / (key + ".png")
                    image.save(path)
                    imports = SourceImportService(assets)
                    imports.import_plan(
                        imports.prepare(
                            asset.id,
                            asset.revision_no,
                            [SourceSpec(path, source_key, count, 1, count)],
                        )
                    )
            self.project.relate(two.id, values["hero"], "uses")
            spec = {"image": {"type": "spritesheet", "animated": True}}
            created = []
            for title, code, output, output_type in (
                ("Demo: Spritesheets übernehmen", COPY, "image", "spritesheet"),
                ("Demo: GIF erzeugen", GIF, "animation", "gif"),
            ):
                script = files.create_script(
                    title,
                    code=code,
                    description={
                        "inputs": spec,
                        "outputs": {output: {"type": output_type}},
                        "description": (
                            "Synthetisches Beispiel. Bearbeitung erfolgt " "in dieser Python-Datei."
                        ),
                    },
                )
                value = empty_definition("pending")
                value["inputs"] = spec
                value["nodes"] = [{"id": "process", "script_id": script.id, "parameters": {}}]
                value["connections"] = [
                    {"from": INPUT, "out": "image", "to": "process", "in": "image"}
                ]
                value["folders"] = [
                    {
                        "id": output,
                        "node": "process",
                        "port": output,
                        "directory": "Demo/{pose}",
                        "scope": "asset",
                    }
                ]
                created.append(files.create_definition(title, definition=value))
            first = workspace.use(created[0].id, [act.id], title="Demo: PA")
            second = workspace.use(created[1].id, title="Demo: PB")
            workspace.update_usage(
                second.id,
                connections=[{"usage": first.id, "out": "image", "in": "image"}],
                expected_revision=second.revision_no,
            )
            from .document_service import DocumentService

            DocumentService(self.project).create(
                act.id,
                "Demoablauf",
                "# Synthetischer Test\n\n"
                "PA verarbeitet beide Animationen. Erst danach verarbeitet PB deren Ergebnisse.\n\n"
                "Prüfen und Freigeben erfolgen ausdrücklich in Skripte & Pipelines. "
                "Das Einzelbild passt nicht zum animierten Spritesheet-Eingang.\n",
            )
            result = {
                "act": act.id,
                "one": one.id,
                "two": two.id,
                "temple": package.id,
                **values,
                "pipelines": [r.id for r in created],
                "usages": [first.id, second.id],
            }
            current = self.project.project()
            self.catalog.save(current, data=current.data | {"synthetic_workspace_demo": result})
        return result
