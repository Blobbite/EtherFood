"""Untrusted discovery, explicit hash-bound consent and a real optional RGBA worker."""

from copy import deepcopy
from importlib.metadata import version
import json
import os
from pathlib import Path

from PIL import Image
import pytest

from etherfood_studio.application.asset_service import AssetService
from etherfood_studio.application.pipeline_service import PipelineService
from etherfood_studio.application.plugin_service import (
    PluginService,
    read_manifest,
    validate_manifest,
)
from etherfood_studio.application.project_service import ProjectService
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


@pytest.mark.parametrize(
    "field,value",
    [
        ("capabilities", [{}]),
        ("capabilities", ["animated", "animated"]),
        ("capabilities", "animated"),
        ("inputs", ["image"]),
        ("outputs", {"file": "file"}),
        ("parameters", []),
        ("parameters", {"amount": {"type": [], "default": 1}}),
        ("parameters", {"amount": {"type": "number", "default": 1, "minimum": [], "maximum": 2}}),
        ("parameters", {"amount": {"type": "number", "default": 1, "minimum": 3, "maximum": 2}}),
        ("parameters", {"amount": {"type": "number", "default": True, "minimum": 0, "maximum": 1}}),
        (
            "parameters",
            {"amount": {"type": "number", "default": 1, "minimum": 0, "maximum": float("inf")}},
        ),
        ("parameters", {"amount": {"type": "choice", "default": "a", "choices": [{"a": 1}]}}),
        ("parameters", {"amount": {"type": "choice", "default": "a", "choices": ["a", "a"]}}),
        ("parameters", {"amount": {"type": "boolean", "default": False, "minimum": 0}}),
        ("parameters", {"amount": {"type": "string", "default": "x" * 513}}),
        ("parameters", {4: {"type": "boolean", "default": False}}),
        ("dependencies", [{}]),
        ("dependencies", ["https://example.invalid/plugin.py"]),
        ("dependencies", ["pillow==12.1.1", "Pillow==12.1.1"]),
        ("entry_point", "foo.apply"),
        ("id", "../code.py"),
        ("name", " "),
    ],
)
def test_malformed_manifest_always_has_a_studio_error(field, value):
    manifest = declaration()
    manifest[field] = value
    with pytest.raises(StudioError):
        validate_manifest(manifest)


@pytest.mark.parametrize(
    "raw", [b"{", b"[]", b"null", b' {"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b"\xff"]
)
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
