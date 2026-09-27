"""Project-local copies, declarative resources, safe archives and visual-only legacy imports."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import stat
import zipfile

from PIL import Image
import pytest

from etherfood_studio.application import pipeline_exchange as exchange_module
from etherfood_studio.application.pipeline_exchange import PipelineExchange, read_json
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.plugin_service import PluginService
from etherfood_studio.application.profile_service import ProfileService
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.pipeline_recipes import blockers, step, template
from etherfood_studio.storage.blob_store import BlobStore
from etherfood_studio.storage.sqlite_repository import canonical

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = Path(__file__).resolve().parents[1] / "examples/pipeline_grayscale"


@pytest.fixture
def projects(tmp_path):
    opened = []

    def create(name):
        root = tmp_path / name
        root.mkdir()
        project = ProjectService.new(root, name)
        opened.append(project)
        return project

    yield create
    for project in opened:
        project.catalog.close()


def document(project, template_id="graphics"):
    return {"contract": "studio-pipeline-export-v1", "name": "Importierte Pipeline",
            "recipe": template(template_id),
            "profiles": list(ProfileService(project).profiles().values())}


def write_document(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def add_resources(project, recipe, tmp_path, *, absolute=False):
    palette = tmp_path / "palette.json"
    provenance = str(tmp_path / "private" / "stand.png") if absolute else "stand.png"
    colors = {"format": "pyimg-fixed-palette", "version": 1, "color_space": "sRGB",
              "colors": [[0, 0, 0], [255, 255, 255]],
              "references": [{"path": provenance, "sha256": "a" * 64, "size": [2, 2],
                              "grid": [1, 1], "frames": 1, "direction": d}
                             for d in ("N", "NO", "O", "SO", "S", "SW", "W", "NW")]}
    palette.write_text(json.dumps(colors, indent=2), encoding="utf-8")
    mask = tmp_path / "mask.png"
    Image.new("L", (2, 2), 1).save(mask)
    store = BlobStore(project.catalog, project.catalog.path.parent)
    for key, path in (("palette", palette), ("mask", mask)):
        copied = store.import_file(path)
        recipe["resources"][key] = {"name": path.name, "sha256": copied["sha256"],
                                    "length": copied["length"]}
    return palette, mask


def test_package_roundtrip_copies_recipe_ids_layout_and_resources(projects, tmp_path):
    source, destination = projects("source"), projects("destination")
    pipelines = PipelineService(source)
    record = pipelines.create("Frame-Rezept", "frames")
    recipe = deepcopy(record.data["recipe"])
    recipe["profiles"] = ["comic_mid"]
    node = recipe["steps"][1]
    node["parameters"].update(frames=10, fps=8.0, timing="keep_duration")
    recipe["overridable"] = [node["id"] + ".fps"]
    files = add_resources(source, recipe, tmp_path)
    original_bytes = {p.name: p.read_bytes() for p in files}
    pipelines.save(record.id, recipe, record.revision_no)
    source.catalog.save_layout(record.id, {"x": 99, "y": 55, "pipeline_nodes": {
        node["id"]: {"x": 36, "y": -18, "w": 280, "h": 120}}})
    package = tmp_path / "recipe.zip"
    PipelineExchange(source).export(record.id, package, package=True)
    before = destination.catalog.export_snapshot()
    exchange = PipelineExchange(destination)
    preview = exchange.preview(package)
    assert destination.catalog.export_snapshot() == before  # Preview is read-only.
    imported = exchange.accept(preview, "Eigene Kopie")
    copied = imported.data["recipe"]
    assert imported.id != record.id and imported.data["project_id"] == destination.project().id
    assert {n["id"] for n in copied["steps"]}.isdisjoint(n["id"] for n in recipe["steps"])
    assert [n["parameters"] for n in copied["steps"]] == [n["parameters"] for n in recipe["steps"]]
    assert copied["connections"][0]["to"] == copied["steps"][1]["id"]
    assert copied["overridable"] == [copied["steps"][1]["id"] + ".fps"]
    layout = destination.catalog.layout(imported.id)
    assert set(layout) == {"pipeline_nodes"}
    assert layout["pipeline_nodes"][copied["steps"][1]["id"]] == {
        "x": 36, "y": -18, "w": 280, "h": 120}
    store = BlobStore(destination.catalog, destination.catalog.path.parent)
    for resource in copied["resources"].values():
        assert store.path_for(resource["sha256"]).read_bytes() == original_bytes[resource["name"]]
    assert PipelineService(destination).assignments() == []
    assert destination.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    copied["category"] = "Nur im Zielprojekt"
    PipelineService(destination).save(imported.id, copied, imported.revision_no)
    assert pipelines.recipe(record.id).data["recipe"]["category"] == recipe["category"]
    destination.validate_structure()


def test_profile_conflicts_remap_dependents_without_repointing_local_profiles(projects, tmp_path):
    source, target = projects("source"), projects("target")
    values = list(ProfileService(source).profiles().values())
    next(v for v in values if v["key"] == "pixel_high")["value"] = 96
    ProfileService(source).save(values, source.project().revision_no)
    recipe = PipelineService(source).create("Pixel", "graphics")
    data = deepcopy(recipe.data["recipe"])
    data["profiles"] = ["pixel_low"]
    PipelineService(source).save(recipe.id, data, recipe.revision_no)
    path = tmp_path / "pixel.json"
    PipelineExchange(source).export(recipe.id, path)
    exchange = PipelineExchange(target)
    plan = exchange.preview(path)
    assert sum("Profilkonflikt:" in warning for warning in plan.warnings) == 2
    record = exchange.accept(plan, "Importierter Pixelablauf")
    profiles = ProfileService(target).profiles()
    low = record.data["recipe"]["profiles"][0]
    assert low.startswith("pixel_low_")
    high = profiles[low]["parent"]
    assert high.startswith("pixel_high_") and profiles[high]["value"] == 96
    assert profiles["pixel_low"]["parent"] == "pixel_high"
    assert profiles["pixel_high"]["value"] == 128
    assert ProfileService(source).profiles()["pixel_high"]["value"] == 96


def test_default_profile_conflict_is_explicitly_previewed(projects, tmp_path):
    project = projects("project")
    data = document(project)
    data["profiles"][2]["value"] = 0.2
    plan = PipelineExchange(project).preview(write_document(tmp_path / "recipe.json", data))
    assert any("automatische Asset-Profilauswahl entfällt" in v for v in plan.warnings)
    copied = PipelineExchange(project).accept(plan, "Kopie")
    assert any(v.startswith("comic_low_") for v in copied.data["recipe"]["profiles"])


def test_legacy_provenance_is_redacted_without_mutating_stored_originals(projects, tmp_path):
    source, target = projects("source"), projects("target")
    service = PipelineService(source)
    record = service.create("Palette", "graphics")
    recipe = deepcopy(record.data["recipe"])
    paths = add_resources(source, recipe, tmp_path, absolute=True)
    before = paths[0].read_bytes()
    digest = recipe["resources"]["palette"]["sha256"]
    service.save(record.id, recipe, record.revision_no)
    package = tmp_path / "palette.zip"
    PipelineExchange(source).export(record.id, package, package=True)
    preview = PipelineExchange(target).preview(package)
    resource = read_json(preview.document)["recipe"]["resources"]["palette"]
    assert resource["sha256"] != digest
    redacted = json.loads(dict(preview.resources)[resource["sha256"]])
    assert all(v["path"] == "stand.png" for v in redacted["references"])
    assert paths[0].read_bytes() == before
    store = BlobStore(source.catalog, source.catalog.path.parent)
    assert store.path_for(digest).read_bytes() == before


def test_missing_resources_json_and_missing_plugin_are_blocked_drafts(projects, tmp_path):
    project = projects("project")
    data = document(project, "color")
    data["recipe"]["steps"][1]["parameters"].update(mode="fixed", palette="palette")
    data["recipe"]["resources"]["palette"] = {
        "name": "palette.json", "sha256": "a" * 64, "length": 20}
    exchange = PipelineExchange(project)
    plan = exchange.preview(write_document(tmp_path / "recipe.json", data))
    assert any("Ressource fehlt" in v for v in plan.warnings)
    imported = exchange.accept(plan, "Fehlende Ressourcen")
    assert imported.data["recipe"]["resources"] == data["recipe"]["resources"]
    assert any("Ressource fehlt" in v
               for v in exchange.dependency_blockers(imported.data["recipe"]))
    assert PipelineService(project).summary(imported.id)["status"] == "blockiert"
    foreign = deepcopy(data)
    node = foreign["recipe"]["steps"][1]
    node.update(operation="python:not_installed", parameters={"strength": 0.5})
    foreign["recipe"]["overridable"] = [node["id"] + ".strength"]
    plan = exchange.preview(write_document(tmp_path / "plugin.json", foreign))
    assert any("Werkzeug fehlt" in v for v in plan.warnings)
    record = exchange.accept(plan, "Fehlender Schritt")
    assert any("Werkzeug fehlt" in v
               for v in PipelineService(project).summary(record.id)["blockers"])
    copied = record.data["recipe"]
    assert copied["overridable"] == [copied["steps"][1]["id"] + ".strength"]
    reopened = ProjectService.open(project.catalog.path.parent, read_only=True)
    assert PipelineService(reopened).summary(record.id)["status"] == "blockiert"
    reopened.catalog.close()
    assert project.catalog.db.execute("SELECT COUNT(*) FROM pipeline_plugins").fetchone()[0] == 0
    assert project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_export_does_not_include_registered_python_or_trust(projects, tmp_path):
    project, target = projects("project"), projects("target")
    plugins = PluginService(project)
    registered = plugins.register(EXAMPLE / "manifest.json", EXAMPLE / "grayscale.py")
    plugins.approve(registered["identifier"], registered["code_hash"])
    service = PipelineService(project)
    record = service.create("Graustufen", "empty")
    recipe = deepcopy(record.data["recipe"])
    node = step(registered["identifier"], registered["manifest"])
    recipe["steps"].append(node)
    recipe["connections"].append({"from": recipe["steps"][0]["id"], "out": "image",
                                  "to": node["id"], "in": "image"})
    service.save(record.id, recipe, record.revision_no)
    package = tmp_path / "plugin.zip"
    PipelineExchange(project).export(record.id, package, package=True)
    with zipfile.ZipFile(package) as archive:
        assert archive.namelist() == ["recipe.json"]
        payload = archive.read("recipe.json")
        assert registered["code_hash"].encode() not in payload
        assert b"approved_hash" not in payload and b"code_path" not in payload
    preview = PipelineExchange(target).preview(package)
    copied = PipelineExchange(target).accept(preview, "Unfreigegebene Kopie")
    assert PluginService(target).manifests() == {}
    assert PipelineService(target).summary(copied.id)["status"] == "blockiert"


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(contract="future-version"),
    lambda d: d.update(name=[]),
    lambda d: d.update(recipe=[]),
    lambda d: d.update(profiles={}),
    lambda d: d["profiles"][0].update(method=[]),
    lambda d: d["profiles"][0].update(parent={}),
    lambda d: d["profiles"][0].update(value=float("nan")),
    lambda d: d["recipe"].update(capabilities=[{}]),
    lambda d: d["recipe"]["steps"][0].update(operation="../script.py"),
    lambda d: d["recipe"]["steps"][0].update(parameters=[]),
    lambda d: d["recipe"]["connections"][0].update(to="unknown"),
    lambda d: d["recipe"].update(profiles=["unexported"]),
    lambda d: d.update(layout={"pipeline_nodes": {"unknown": {"x": 1}}}),
])
def test_malformed_export_is_a_studio_error_with_no_writes(projects, tmp_path, mutation):
    project = projects("project")
    data = document(project)
    mutation(data)
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError):
        PipelineExchange(project).preview(write_document(tmp_path / "broken.json", data))
    assert project.catalog.export_snapshot() == before


@pytest.mark.parametrize("raw", [b"{", b' {"name":"one","name":"two"}', b"\xff",
                                b'{"x":1e9999}', b"[" * 80 + b"0" + b"]" * 80])
def test_json_parser_rejects_duplicates_overflow_depth_and_bad_utf8(raw):
    with pytest.raises(StudioError):
        read_json(raw)


@pytest.mark.parametrize("bad_name", ["../escape", "/recipe.json", "resources/../evil.dat",
    "C:/evil", "resources\\evil.dat", "resources//" + "a" * 64 + ".dat",
    "./recipe.json", "script.py", "resources/" + "a" * 63 + ".dat"])
def test_archive_rejects_unsafe_names(projects, tmp_path, bad_name):
    project = projects("project")
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("recipe.json", canonical(document(project)))
        archive.writestr(bad_name, b"data")
    with pytest.raises(StudioError, match="Paketeintrag"):
        PipelineExchange(project).preview(path)
    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize("mode", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFDIR])
def test_archive_rejects_symlinks_devices_and_directories(projects, tmp_path, mode):
    project = projects("project")
    path = tmp_path / "bad.zip"
    entry = zipfile.ZipInfo("recipe.json")
    entry.create_system = 3
    entry.external_attr = (mode | 0o600) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(entry, canonical(document(project)))
    with pytest.raises(StudioError, match="Paketeintrag"):
        PipelineExchange(project).preview(path)


@pytest.mark.parametrize("second", ["recipe.json", "RECIPE.JSON"])
def test_archive_rejects_duplicate_and_case_colliding_entries(projects, tmp_path, second):
    project = projects("project")
    path = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("recipe.json", canonical(document(project)))
        if second == "recipe.json":
            with pytest.warns(UserWarning):
                archive.writestr(second, b"{}")
        else:
            archive.writestr(second, b"{}")
    with pytest.raises(StudioError, match="doppelte"):
        PipelineExchange(project).preview(path)


def test_archive_uncompressed_limit_and_resource_hash_checked(projects, tmp_path, monkeypatch):
    project = projects("project")
    path = tmp_path / "large.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("recipe.json", b" " * 10000)
    monkeypatch.setattr(exchange_module, "MAX_PACKAGE", 4000)
    assert path.stat().st_size < 4000
    with pytest.raises(StudioError, match="Entpackgröße"):
        PipelineExchange(project).preview(path)
    path = tmp_path / "wrong-hash.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("recipe.json", canonical(document(project)))
        archive.writestr("resources/" + "a" * 64 + ".dat", b"wrong hash")
    with pytest.raises(StudioError, match="Inhaltshash"):
        PipelineExchange(project).preview(path)


def test_code_resources_and_hidden_private_paths_not_exported(projects, tmp_path):
    project = projects("project")
    data = document(project)
    data["recipe"]["steps"][1].update(operation="python:missing",
                                    parameters={"path": "/home/private"})
    with pytest.raises(StudioError, match="Private absolute Pfade"):
        PipelineExchange(project).preview(write_document(tmp_path / "private.json", data))
    data["recipe"]["steps"][1]["parameters"] = {"access_token": "secret"}
    with pytest.raises(StudioError, match="Zugangsdaten"):
        PipelineExchange(project).preview(write_document(tmp_path / "token.json", data))
    data["recipe"]["steps"][1]["parameters"] = {}
    raw = b"raise RuntimeError('never execute')"
    digest = hashlib.sha256(raw).hexdigest()
    data["recipe"]["resources"]["code"] = {"name": "step.py", "sha256": digest, "length": len(raw)}
    path = tmp_path / "code.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("recipe.json", canonical(data))
        archive.writestr("resources/" + digest + ".dat", raw)
    with pytest.raises(StudioError, match="Python-Code"):
        PipelineExchange(project).preview(path)


def test_accept_revalidates_forged_plan_and_name_conflicts_transactionally(projects, tmp_path):
    project = projects("project")
    exchange = PipelineExchange(project)
    plan = exchange.preview(write_document(tmp_path / "recipe.json", document(project)))
    for changed in (replace(plan, document='{"contract":"wrong"}'),
                    replace(plan, resources=(("../../file", b"bad"),)),
                    replace(plan, layout='{"pipeline_nodes":{}}')):
        before = project.catalog.export_snapshot()
        with pytest.raises(StudioError):
            exchange.accept(changed, "Kopie")
        assert project.catalog.export_snapshot() == before
    record = exchange.accept(plan, "Meine Pipeline")
    before = project.catalog.export_snapshot()
    with pytest.raises(StudioError, match="bereits vergeben"):
        exchange.accept(plan, "MEINE PIPELINE")
    assert project.catalog.export_snapshot() == before
    destination = tmp_path / "existing.json"
    destination.write_bytes(b"foreign bytes")
    with pytest.raises(StudioError, match="Exportziel"):
        exchange.export(record.id, destination)
    assert destination.read_bytes() == b"foreign bytes"


def test_legacy_layout_aliases_groups_and_visual_edges_remain_non_executable(projects, tmp_path):
    project = projects("project")
    old_path = "tools/AssetManager/PyGameTools/Pipline/SpritesheetFram16-Pipline/" + \
        "PyPiplineStart-SpritesheetFram16.py"
    data = {"nodes": [
        {"id": "group", "type": "group", "label": "Aufbereitung", "x": 20, "y": 40,
         "width": 600, "height": 300},
        {"id": "tool", "type": "file", "file": old_path, "label": "16 Frames",
         "x": 50, "y": 80, "group": "group", "width": 280, "height": 120},
        {"id": "unknown", "type": "text", "text": "Nicht ausführen", "x": 340, "y": 80}],
        "edges": [{"id": "visual", "fromNode": "tool", "toNode": "unknown",
                   "label": "Nur Organisation", "fromSide": "right", "toSide": "left"}]}
    exchange = PipelineExchange(project)
    plan = exchange.preview(write_document(tmp_path / "old.canvas", data))
    assert any("0-SpritesheetFram16-Pipline" in warning for warning in plan.warnings)
    imported = exchange.accept(plan, "Legacy-Kopie")
    recipe = imported.data["recipe"]
    assert recipe["connections"] == [] and not recipe["enabled"]
    assert any(n["operation"] == "prepare16" for n in recipe["steps"])
    assert blockers(recipe, PipelineService(project).manifests())
    layout = project.catalog.layout(imported.id)
    legacy = layout["pipeline_legacy"]
    assert len(legacy["edges"]) == 1 and len(legacy["nodes"]) == 3
    ids = {n["id"] for n in recipe["steps"]}
    assert set(legacy["nodes"]) <= ids
    edge = legacy["edges"][0]
    assert edge["from"] in ids and edge["to"] in ids and edge["label"] == "Nur Organisation"
    assert layout["pipeline_nodes"][edge["from"]] == {"x": 50, "y": 80, "w": 280, "h": 120}
    assert legacy["nodes"][edge["from"]]["group"] in ids
    assert legacy["mappings"][0]["node"] == edge["from"]
    assert project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    package = tmp_path / "legacy-roundtrip.zip"
    exchange.export(imported.id, package, package=True)
    other = projects("other")
    copy = PipelineExchange(other).accept(PipelineExchange(other).preview(package), "Weiterkopie")
    assert len(other.catalog.layout(copy.id)["pipeline_legacy"]["edges"]) == 1
    assert copy.data["recipe"]["connections"] == []


@pytest.mark.parametrize("node", [None, {"id": "a", "x": "not a number"},
                                {"id": "a", "x": float("inf")}, {"id": "a", "width": -1}])
def test_malformed_legacy_layout_is_rejected(projects, node):
    project = projects("project")
    with pytest.raises(StudioError):
        PipelineExchange(project).legacy({"nodes": [node], "edges": []})


def schema_validator(filename):
    jsonschema = pytest.importorskip("jsonschema")
    from referencing import Registry, Resource

    schemas = [json.loads(p.read_text()) for p in
               (ROOT / "schemas/asset-studio").glob("pipeline-*-v1.json")]
    registry = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in schemas)
    schema = next(s for s in schemas if s["$id"].endswith(filename))
    return jsonschema.Draft202012Validator(schema, registry=registry)


@pytest.mark.parametrize("filename", ["pipeline-recipe-v1.json", "pipeline-export-v1.json",
                                     "pipeline-manifest-v1.json"])
def test_versioned_schemas_are_valid(filename):
    validator = schema_validator(filename)
    validator.check_schema(validator.schema)


def test_all_templates_examples_and_export_validate_against_offline_schemas(projects):
    from etherfood_studio.domain.pipeline_recipes import TEMPLATES

    project = projects("project")
    for name in TEMPLATES:
        schema_validator("pipeline-recipe-v1.json").validate(template(name))
        schema_validator("pipeline-export-v1.json").validate(document(project, name))
    schema_validator("pipeline-manifest-v1.json").validate(
        json.loads((EXAMPLE / "manifest.json").read_text()))
    invalid = document(project)
    invalid["recipe"]["steps"][0]["enabled"] = "yes"
    assert list(schema_validator("pipeline-export-v1.json").iter_errors(invalid))
    invalid = document(project)
    invalid["profiles"][0]["value"] = -1
    assert list(schema_validator("pipeline-export-v1.json").iter_errors(invalid))


@pytest.fixture
def exchange_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    yield app
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_actual_import_dialog_previews_before_accept_and_cancel_writes_nothing(
        projects, tmp_path, exchange_qt, monkeypatch):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QFileDialog, QPlainTextEdit
    from etherfood_studio.ui.pipeline_exchange_dialogs import import_pipeline

    project = projects("project")
    path = write_document(tmp_path / "recipe.json", document(project))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(path), ""))
    before = project.catalog.export_snapshot()
    captured = []

    def inspect_and_reject():
        dialog = QApplication.activeModalWidget()
        captured.append(dialog.objectName())
        assert dialog.findChild(QPlainTextEdit, "pipeline_import_summary").toPlainText()
        assert project.catalog.export_snapshot() == before
        dialog.reject()

    QTimer.singleShot(0, inspect_and_reject)
    assert import_pipeline(project) is None
    assert captured == ["pipeline_import_preview"]
    assert project.catalog.export_snapshot() == before

    def accept_copy():
        dialog = QApplication.activeModalWidget()
        dialog.title.setText("Vom Dialog importiert")
        dialog.import_copy()

    QTimer.singleShot(0, accept_copy)
    record = import_pipeline(project)
    assert record.title == "Vom Dialog importiert"
    assert project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
