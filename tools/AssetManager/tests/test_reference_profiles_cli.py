"""The public color starters and formal schemas consume the same explicit reference contract."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image
import jsonschema
import pytest

from etherfood_studio.pipelines.image_processing import TOOL_ROOT, legacy_modules
from etherfood_studio.storage.blob_store import file_hash


def selection_file(tmp_path, count=1):
    legacy_modules()
    from PyImgReferenceSelection import SAMPLING, SELECTION_FORMAT

    root = tmp_path / "references"
    root.mkdir()
    refs = []
    for index, direction in enumerate(("O", "W")[:count]):
        path = root / f"referenz_{direction}.png"
        Image.new("RGBA", (4, 4), (60 + index * 80, 100, 30, 255)).save(path)
        refs.append({"id": direction, "source_revision": "source-" + direction, "path": path.name,
            "pose": "frei", "direction": direction, "sha256": file_hash(path),
            "size": [4, 4], "grid": [1, 1], "frames": 1})
    value = {"format": SELECTION_FORMAT, "version": 1, "sampling": SAMPLING,
             "references": refs, "preview_reference": refs[0]["id"]}
    path = root / "selection.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path, value


def cli(*args):
    script = TOOL_ROOT / "SourceColor-Pipline/PyPiplineStart-SourceColor.py"
    return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True,
                          text=True, timeout=30)


@pytest.mark.parametrize("mode", ["soft", "fixed", "material"])
def test_v2_profile_roundtrip_through_cli_and_html(tmp_path, mode):
    selection, value = selection_file(tmp_path, 2)
    schemas = TOOL_ROOT / "PiplineToos/schemas"
    jsonschema.validate(value, json.loads((
        schemas / "reference-selection-v1.schema.json").read_text()))
    source = tmp_path / "source"
    source.mkdir()
    target_image = source / "npc_angriff_S.png"
    Image.new("RGBA", (4, 4), (75, 105, 25, 255)).save(target_image)
    before = file_hash(target_image)
    profile_path = selection.parent / "profile.json"
    output = tmp_path / "output"
    if mode == "soft":
        result = cli(source, "--reference-selection", selection, "--output-dir", output)
        saved = output / ".color_profile/reference-colors.json"
    else:
        export_flag = "--export-fixed-palette" if mode == "fixed" else "--export-material-profile"
        extra = []
        if mode == "material":
            exact = legacy_modules()[-1]
            definitions = tmp_path / "materials.json"
            definitions.write_text(json.dumps({"format": exact.DEFINITIONS_FORMAT, "version": 1,
                "materials": [{"id": 1, "name": "Stoff", "levels": 2}]}))
            masks = tmp_path / "masks"
            masks.mkdir()
            for ref in value["references"]:
                Image.new("L", (4, 4), 1).save(masks / ref["path"],
                    pnginfo=exact.mask_metadata([1, 1], ref["sha256"]))
            Image.new("L", (4, 4), 1).save(masks / target_image.name,
                pnginfo=exact.mask_metadata([1, 1], before))
            extra = ["--material-definitions", definitions, "--mask-dir", masks]
        exported = cli(source, "--reference-selection", selection, export_flag, profile_path,
            *extra)
        assert exported.returncode == 0, exported.stderr
        args = ["--fixed-palette", profile_path] if mode == "fixed" else ["--material-profile",
            profile_path, "--mask-dir", masks]
        result = cli(source, "--color-mode", mode, *args, "--output-dir", output)
        saved = profile_path
    assert result.returncode == 0, result.stderr
    profile = json.loads(saved.read_text())
    assert profile["version"] == 2 and len(profile["references"]) == 2
    jsonschema.validate(profile, json.loads((schemas / "color-profile-v2.schema.json").read_text()))
    assert (output / target_image.name).is_file()
    assert file_hash(target_image) == before
    html = (output / "farbvergleich.html").read_text()
    assert "2 ausdrücklich gewählte Referenzen" in html
    assert "Ausdrücklich gewählte gemeinsame Vorschau-Referenz: O" in html
    assert "Alle acht Stand-Richtungen" not in html
    loader = {"soft": legacy_modules()[-2].load_profile, "fixed": legacy_modules()[-1].load_palette,
              "material": legacy_modules()[-1].load_material_profile}[mode]
    assert loader(saved) == profile
    profile["version"] = 99
    saved.write_text(json.dumps(profile))
    with pytest.raises(ValueError):
        loader(saved)


@pytest.mark.parametrize("damage", ["hash", "traversal", "duplicate", "unknown", "grid",
                                    "preview", "missing_pose", "extra"])
def test_reference_manifest_rejects_wrong_binding(tmp_path, damage):
    path, value = selection_file(tmp_path, 2)
    from PyImgReferenceSelection import load_selection

    if damage == "hash":
        value["references"][0]["sha256"] = "0" * 64
    elif damage == "traversal":
        value["references"][0]["path"] = "../escape.png"
    elif damage == "duplicate":
        value["references"].append(deepcopy(value["references"][0]))
    elif damage == "unknown":
        value["version"] = 2
    elif damage == "grid":
        value["references"][1].update(grid=[2, 1], frames=2)
    elif damage == "missing_pose":
        del value["references"][0]["pose"]
    elif damage == "extra":
        value["unknown"] = True
    else:
        value["preview_reference"] = "nicht ausgewählt"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        load_selection(path)
