"""Canonical content identity; display metadata and output bytes stay separate."""

import hashlib
import json
from pathlib import Path

from ..storage.sqlite_repository import canonical


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def input_fingerprint(node, predecessors: dict[str, str]) -> str:
    return digest({
        "contract": "studio-build-input-v1", "stage": node.stage,
        "parameters": json.loads(node.parameters), "algorithm": node.algorithm,
        "tools": sorted((Path(path).name, sha) for path, sha in node.tools),
        "adapter": node.adapter,
        "inputs": sorted((v.role, v.kind, v.sha256) for v in node.inputs),
        "predecessors": sorted((r.output, r.kind, predecessors[r.node])
                               for r in node.dependencies),
        "outputs": sorted((v.path, v.kind) for v in node.outputs),
    })
