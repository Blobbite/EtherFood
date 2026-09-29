"""Isolated worker entry; Python extensions are trusted code, not a security sandbox."""

import json
from copy import deepcopy
from importlib.metadata import version
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PIL import Image  # noqa: E402
from etherfood_studio.domain.assets import require  # noqa: E402
from etherfood_studio.pipelines.image_adapter import ImageAdapter, load_input  # noqa: E402
from etherfood_studio.pipelines.image_processing import transform  # noqa: E402
from etherfood_studio.pipelines.python_contract import result_metadata  # noqa: E402
from etherfood_studio.packages import process_artifacts  # noqa: E402
from etherfood_studio.storage.blob_store import file_hash  # noqa: E402
from etherfood_studio.storage.sqlite_repository import canonical  # noqa: E402


def no_network(event, args):
    # Stops accidental network/process use; trusted Python can bypass audit hooks.
    if event.startswith("socket.") or event in {
            "subprocess.Popen", "os.system", "os.exec", "os.fork", "os.forkpty", "os.posix_spawn"}:
        raise PermissionError(
            "Pipeline-Worker: Netzwerk und weitere Prozesse sind nicht freigegeben.")


def run(workspace):
    request = json.loads((workspace / "request.json").read_text(encoding="utf-8"))
    parameters = json.loads(request["parameters"])
    ImageAdapter().validate(parameters)
    incoming, output = workspace / "input", workspace / "output"
    image, meta, resources = load_input(workspace, parameters)
    sys.addaudithook(no_network)
    if parameters["operation"] == "plugin":
        plugin = parameters["plugin"]
        for dependency in plugin["dependencies"]:
            name, expected = dependency.split("==")
            require(version(name) == expected, "Python-Abhängigkeit seit Dry-run verändert.")
        code = incoming / "plugin.py"
        require(file_hash(code) == plugin["code_hash"], "Python-Codehash stimmt nicht.")
        namespace = {"__name__": "studio_trusted_extension", "__file__": str(code)}
        exec(compile(code.read_bytes(), str(code), "exec"), namespace)
        function = namespace[plugin["entry_point"]]
        if "manifest" in plugin:
            result = function(image.copy(), deepcopy(meta), parameters["settings"])
            require(isinstance(result, tuple) and len(result) == 2,
                    "Python-Vertrag v2 erwartet (RGBA-Bild, Metadatenänderungen).")
            image, changes = result
            require(isinstance(image, Image.Image) and image.mode == "RGBA",
                    "Python-Schritt muss ein RGBA-Bild liefern.")
            meta = result_metadata(meta, changes, image.size)
        else:
            result = function(image.copy(), parameters["settings"])
            require(isinstance(result, Image.Image) and result.size == image.size and
                    result.mode == "RGBA",
                    "Python-Schritt muss ein gleich großes RGBA-Bild liefern.")
            image = result
    else:
        image, meta = transform(image, meta, parameters["operation"], parameters["settings"],
                                resources, profile=parameters["profile"])
    image.save(output / "image.png", "PNG")
    meta.update(contract="studio-image-result-v1", image_sha256=file_hash(output / "image.png"))
    (output / "metadata.json").write_text(canonical(meta) + "\n", encoding="utf-8")
    process_artifacts("write", parameters["operation"], image, meta,
                      parameters["settings"], output)
    print("PNG und Frame-Metadaten erzeugt", flush=True)


if __name__ == "__main__":
    run(Path(sys.argv[1]))
