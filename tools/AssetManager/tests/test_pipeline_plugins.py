"""Untrusted discovery, explicit hash-bound consent and a real optional RGBA worker."""

from copy import deepcopy
from importlib.metadata import version
import json
import os
from pathlib import Path

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.build_planner import BuildPlanner
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.plugin_service import (
    PluginService, read_manifest, validate_manifest,
)
from etherfood_studio.application.project_service import ProjectService
from etherfood_studio.application.recipe_builds import RecipeBuildService
from etherfood_studio.application.source_import import SourceImportService, SourceSpec
from etherfood_studio.domain.assets import default_definition
from etherfood_studio.domain.models import StudioError
from etherfood_studio.domain.pipeline_recipes import step, template
from etherfood_studio.domain.sources import expected_sources
from etherfood_studio.storage.blob_store import file_hash

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/pipeline_grayscale"


@pytest.fixture
def plugins(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project = ProjectService.new(root, "Python-Erweiterungen")
    yield PluginService(project), project
    project.catalog.close()


def declaration():
    return json.loads((EXAMPLE / "manifest.json").read_text(encoding="utf-8"))


def files(tmp_path, *, manifest=None, code="def apply(image, parameters):\n    return image\n"):
    descriptor, source = tmp_path / "manifest.json", tmp_path / "step.py"
    descriptor.write_text(json.dumps(manifest or declaration()), encoding="utf-8")
    source.write_text(code, encoding="utf-8")
    return descriptor, source


def test_discovery_registration_reload_and_consent_never_import_python(plugins, tmp_path):
    service, project = plugins
    marker = tmp_path / "MUST-NOT-EXIST"
    paths = files(tmp_path, code=f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
    registered = service.register(*paths)
    assert registered["approved_hash"] is None
    assert service.manifests()["python:grayscale"]["entry_point"] == "apply"
    assert not marker.exists()
    with pytest.raises(StudioError, match="nicht.*freigegeben"):
        service.trusted("python:grayscale")
    with pytest.raises(StudioError, match="Codeversion"):
        service.approve("python:grayscale", "0" * 64)
    service.approve("python:grayscale", registered["code_hash"])
    assert service.trusted("python:grayscale")["code_hash"] == registered["code_hash"]
    reopened = ProjectService.open(project.catalog.path.parent, read_only=True)
    try:
        assert PluginService(reopened).manifests() == service.manifests()
        assert not marker.exists()
    finally:
        reopened.catalog.close()
    service.revoke("python:grayscale")
    with pytest.raises(StudioError, match="freigegeben"):
        service.trusted("python:grayscale")
    assert not marker.exists()


def test_original_and_registered_versions_are_distinct_and_changes_revoke(plugins, tmp_path):
    service, _ = plugins
    descriptor, code = files(tmp_path)
    first = service.register(descriptor, code)
    service.approve(first["identifier"], first["code_hash"])
    code.write_text("def apply(image, parameters):\n    return image.copy()\n", encoding="utf-8")
    assert service.trusted(first["identifier"])["code_hash"] == first["code_hash"]
    second = service.register(descriptor, code)
    assert second["code_hash"] != first["code_hash"] and second["approved_hash"] is None
    with pytest.raises(StudioError, match="freigegeben"):
        service.trusted(first["identifier"])
    service.approve(second["identifier"], second["code_hash"])
    manifest = declaration()
    manifest["version"] = "1.0.1"
    descriptor.write_text(json.dumps(manifest), encoding="utf-8")
    third = service.register(descriptor, code)
    assert third["code_hash"] == second["code_hash"] and third["approved_hash"] is None
    service.approve(third["identifier"], third["code_hash"])
    service.store.path_for(third["code_hash"]).write_bytes(b"tampered stored copy")
    with pytest.raises(StudioError, match="verändert"):
        service.trusted(third["identifier"])
    with pytest.raises(StudioError, match="verändert"):
        service.approve(third["identifier"], third["code_hash"])


def test_missing_dependency_is_metadata_only_and_never_installed(plugins, tmp_path):
    service, _ = plugins
    manifest = declaration()
    manifest["dependencies"] = ["definitely-uninstalled-etherfood-example==1.0.0"]
    registered = service.register(*files(tmp_path, manifest=manifest))
    service.approve(registered["identifier"], registered["code_hash"])
    with pytest.raises(StudioError, match="Abhängigkeit fehlt"):
        service.trusted(registered["identifier"])
    manifest["dependencies"] = ["Pillow==0.0.0"]
    descriptor, code = files(tmp_path, manifest=manifest)
    registered = service.register(descriptor, code)
    service.approve(registered["identifier"], registered["code_hash"])
    with pytest.raises(StudioError, match="Abhängigkeit fehlt/abweichend"):
        service.trusted(registered["identifier"])


@pytest.mark.parametrize("field,value", [
    ("capabilities", [{}]), ("capabilities", ["animated", "animated"]),
    ("capabilities", "animated"), ("inputs", ["image"]), ("outputs", {"file": "file"}),
    ("parameters", []), ("parameters", {"amount": {"type": [], "default": 1}}),
    ("parameters", {"amount": {"type": "number", "default": 1, "minimum": [], "maximum": 2}}),
    ("parameters", {"amount": {"type": "number", "default": 1, "minimum": 3, "maximum": 2}}),
    ("parameters", {"amount": {"type": "number", "default": True, "minimum": 0, "maximum": 1}}),
    ("parameters", {"amount": {"type": "number", "default": 1, "minimum": 0,
                               "maximum": float("inf")}}),
    ("parameters", {"amount": {"type": "choice", "default": "a", "choices": [{"a": 1}]}}),
    ("parameters", {"amount": {"type": "choice", "default": "a", "choices": ["a", "a"]}}),
    ("parameters", {"amount": {"type": "boolean", "default": False, "minimum": 0}}),
    ("parameters", {"amount": {"type": "string", "default": "x" * 513}}),
    ("parameters", {4: {"type": "boolean", "default": False}}),
    ("dependencies", [{}]), ("dependencies", ["https://example.invalid/plugin.py"]),
    ("dependencies", ["pillow==12.1.1", "Pillow==12.1.1"]), ("entry_point", "foo.apply"),
    ("id", "../code.py"), ("name", " "),
])
def test_malformed_manifest_always_has_a_studio_error(field, value):
    manifest = declaration()
    manifest[field] = value
    with pytest.raises(StudioError):
        validate_manifest(manifest)


@pytest.mark.parametrize("raw", [b"{", b"[]", b"null", b' {"x":1,"x":2}',
                                b'{"x":NaN}', b'{"x":Infinity}', b"\xff"])
def test_invalid_manifest_json_rejected(raw):
    with pytest.raises(StudioError):
        read_manifest(raw)


def test_registration_limits_symlinks_and_duplicate_registration(plugins, tmp_path):
    service, _ = plugins
    manifest, code = files(tmp_path)
    link = tmp_path / "symlink.py"
    link.symlink_to(code)
    with pytest.raises(StudioError, match="Symlink"):
        service.register(manifest, link)
    link_manifest = tmp_path / "symlink.json"
    link_manifest.symlink_to(manifest)
    with pytest.raises(StudioError, match="Symlink"):
        service.register(link_manifest, code)
    service.register(manifest, code)
    with pytest.raises(StudioError, match="registriert"):
        service.register(manifest, code)
    code.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(StudioError, match="Größenbegrenzung"):
        service.register(manifest, code)
    assert len(service.manifests()) == 1


def test_code_path_must_be_the_registered_blob(plugins, tmp_path):
    service, project = plugins
    row = service.register(*files(tmp_path))
    project.catalog.db.execute("UPDATE pipeline_plugins SET code_path='somewhere.py'")
    with pytest.raises(StudioError, match="unveränderliche Kopien"):
        service.details(row["identifier"])


def test_optional_grayscale_extension_runs_only_after_approval(plugins, tmp_path):
    service, project = plugins
    assert version("Pillow") == "12.1.1"
    registered = service.register(EXAMPLE / "manifest.json", EXAMPLE / "grayscale.py")
    assets = AssetService(project)
    owner = next(r.id for r in project.cards() if r.kind == "global")
    asset = assets.create("Farbiges Einzelbild", owner, default_definition("texture").to_data())
    original = tmp_path / "original.png"
    Image.new("RGBA", (4, 2), (180, 40, 90, 127)).save(original)
    digest = file_hash(original)
    importer = SourceImportService(assets)
    slot = expected_sources(assets.definition(asset.id))[0]
    plan = importer.prepare(asset.id, asset.revision_no, [SourceSpec(original, slot, 1, 1, 1)])
    importer.import_plan(plan)
    pipelines = PipelineService(project)
    record = pipelines.create("Explizit Graustufen", "empty")
    data = deepcopy(record.data["recipe"])
    node = step(registered["identifier"], registered["manifest"])
    data["steps"].append(node)
    data["connections"].append({"from": data["steps"][0]["id"], "out": "image",
                                "to": node["id"], "in": "image"})
    pipelines.save(record.id, data, record.revision_no)
    pipelines.assign(record.id, asset_id=asset.id)
    assert all(n["operation"] != registered["identifier"] for n in template("graphics")["steps"])
    with pytest.raises(StudioError, match="freigegeben"):
        RecipeBuildService(project).plan(asset.id)
    assert project.catalog.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    service.approve(registered["identifier"], registered["code_hash"])
    result = BuildPlanner(project).execute(RecipeBuildService(project).plan(asset.id))
    assert result["status"] == "succeeded", result
    built = project.catalog.get(result["actual"][0]["build_id"])
    directory = project.catalog.path.parent / ".asset-studio/jobs" / built.data["job_id"] / "output"
    with Image.open(directory / "image.png") as image:
        assert image.size == (4, 2) and image.mode == "RGBA"
        red, green, blue, alpha = image.getpixel((0, 0))
        assert red == green == blue and alpha == 127
    assert file_hash(original) == digest
    second = BuildPlanner(project).execute(RecipeBuildService(project).plan(asset.id))
    assert all(n["actual"] == "reused" for n in second["actual"])
    service.revoke(registered["identifier"])
    with pytest.raises(StudioError, match="freigegeben"):
        RecipeBuildService(project).plan(asset.id)


@pytest.fixture
def plugin_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    yield app
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_approval_dialog_requires_warning_consent_and_full_hash(plugins, tmp_path, plugin_qt):
    from etherfood_studio.ui.pipeline_exchange_dialogs import PluginApprovalDialog

    service, _ = plugins
    registered = service.register(*files(tmp_path))
    dialog = PluginApprovalDialog(service, registered["identifier"])
    try:
        assert not dialog.approve_button.isEnabled()
        dialog.confirmation.setText(registered["code_hash"])
        assert not dialog.approve_button.isEnabled()
        dialog.consent.setChecked(True)
        assert dialog.approve_button.isEnabled()
        dialog.confirmation.setText(registered["code_hash"][:8])
        assert not dialog.approve_button.isEnabled()
        dialog.approve()
        assert service.details(registered["identifier"])["approved_hash"] is None
        dialog.confirmation.setText(registered["code_hash"])
        dialog.approve()
        assert dialog.result() == dialog.DialogCode.Accepted
        assert service.trusted(registered["identifier"])
    finally:
        dialog.deleteLater()


def test_manifest_change_during_approval_requires_new_dialog(plugins, tmp_path, plugin_qt):
    from etherfood_studio.ui.pipeline_exchange_dialogs import PluginApprovalDialog

    service, _ = plugins
    manifest, code = files(tmp_path)
    registered = service.register(manifest, code)
    dialog = PluginApprovalDialog(service, registered["identifier"])
    try:
        changed = declaration()
        changed["version"] = "new-version"
        manifest.write_text(json.dumps(changed), encoding="utf-8")
        service.register(manifest, code)
        dialog.consent.setChecked(True)
        dialog.confirmation.setText(registered["code_hash"])
        dialog.approve()
        assert "Manifest wurde geändert" in dialog.error.text()
        assert service.details(registered["identifier"])["approved_hash"] is None
    finally:
        dialog.deleteLater()
