"""Historical foreign reports and local HTML references; no approval or script execution."""

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from threading import Event
from urllib.parse import unquote, urlsplit

from ..domain.models import StudioError
from ..storage.inventory_files import ScanLimits, check_cancel, inside_reference, read_bytes


def binding(root: Path, parent: Path, reference, digest, limits: ScanLimits,
            cancel: Event) -> dict:
    value = {"path": reference if isinstance(reference, str) else "",
             "expected_sha256": digest if isinstance(digest, str) else "", "state": "unbound"}
    if Path(value["path"]).is_absolute():
        value["path"] = "[externer historischer Pfad]"
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        value["reason"] = "Datei-SHA256 fehlt; Fremdaussage nicht an aktuelle Bytes gebunden."
        return value
    try:
        path = inside_reference(root, parent, reference)
        value["path"] = path.relative_to(root).as_posix()
        actual = hashlib.sha256(read_bytes(path, limits.max_bytes, cancel)).hexdigest()
        value["state"] = "matched" if actual == digest else "mismatch"
        value["reason"] = "Nur Dateibindung geprüft, keine fachliche Abnahme."
    except (OSError, StudioError) as error:
        check_cancel(cancel)
        value["state"], value["reason"] = "unavailable", str(error)
    # Absolute historical machine paths are displayed only locally, not persisted as identity.
    if Path(value["path"]).is_absolute():
        value["path"] = "[externer historischer Pfad]"
    return value


def inspect_report(path: Path, root: Path, limits: ScanLimits, cancel: Event) -> dict:
    raw = read_bytes(path, limits.max_report_bytes, cancel)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise StudioError("validation", "Prüfbericht ist kein JSON-Objekt.")
    files = value.get("files", value.get("images", []))
    if not isinstance(files, list) or len(files) > 1000:
        raise StudioError("limit", "Unbekannte/zu große Bericht-Dateiliste.")
    sources, outputs = [], []
    for row in files:
        check_cancel(cancel)
        if not isinstance(row, dict):
            continue
        source = row.get("source", row.get("path"))
        sources.append(binding(root, path.parent, source, row.get("source_sha256"),
                               limits, cancel))
        results = row.get("outputs", [])
        if not isinstance(results, list) or len(results) > 1000:
            raise StudioError("limit", "Ungültige/zu große Bericht-Ausgabeliste.")
        for output in results:
            if isinstance(output, dict):
                outputs.append(binding(root, path.parent, output.get("png", output.get("path")),
                                       output.get("png_sha256", output.get("sha256")),
                                       limits, cancel))
        if not results and "output" in row:
            outputs.append(binding(root, path.parent, row["output"], row.get("output_sha256"),
                                   limits, cancel))
    matched = bool(sources and outputs) and all(v["state"] == "matched" for v in sources + outputs)
    return {"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
            "state": "historical_bound" if matched else "historical_unverified",
            "sources": sources, "outputs": outputs, "approval": "not_granted",
            "note": "Fremdbericht, kein Studio-Check. Fehlende Ausgabehashes bleiben ungeprüft."}


class References(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value:
                if len(self.references) >= 2000:
                    raise StudioError("limit", "Zu viele HTML-Verweise.")
                self.references.append(value)


def inspect_page(path: Path, root: Path, limits: ScanLimits, cancel: Event) -> dict:
    raw = read_bytes(path, limits.max_report_bytes, cancel)
    parser = References()
    parser.feed(raw.decode("utf-8", errors="replace"))
    links = []
    for reference in parser.references:
        check_cancel(cancel)
        try:
            url = urlsplit(reference)
            if url.scheme or url.netloc:
                links.append({"link": reference, "state": "blocked_external"})
                continue
            if not url.path:
                continue
            target = inside_reference(root, path.parent, unquote(url.path))
            links.append({"link": reference, "state": "found",
                          "path": target.relative_to(root).as_posix()})
        except (ValueError, OSError, StudioError) as error:
            links.append({"link": reference, "state": "broken", "reason": str(error)})
    return {"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
            "links": links, "note": "Lesender Verweis; HTML/Skripte werden nicht ausgeführt."}
