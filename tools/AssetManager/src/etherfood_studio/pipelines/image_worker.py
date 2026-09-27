"""Isolated worker entry; Python extensions are trusted code, not a security sandbox."""

import json
from importlib.metadata import version
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PIL import Image  # noqa: E402
from etherfood_studio.domain.assets import require  # noqa: E402
from etherfood_studio.pipelines.image_adapter import ImageAdapter, load_input  # noqa: E402
from etherfood_studio.pipelines.image_processing import transform  # noqa: E402
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
        result = namespace[plugin["entry_point"]](image.copy(), parameters["settings"])
        require(isinstance(result, Image.Image) and result.size == image.size and
                result.mode == "RGBA", "Python-Schritt muss ein gleich großes RGBA-Bild liefern.")
        image = result
    else:
        image, meta = transform(image, meta, parameters["operation"], parameters["settings"],
                                resources, profile=parameters["profile"])
    image.save(output / "image.png", "PNG")
    meta.update(contract="studio-image-result-v1", image_sha256=file_hash(output / "image.png"))
    (output / "metadata.json").write_text(canonical(meta) + "\n", encoding="utf-8")
    print("PNG und Frame-Metadaten erzeugt", flush=True)


if __name__ == "__main__":
    run(Path(sys.argv[1]))
