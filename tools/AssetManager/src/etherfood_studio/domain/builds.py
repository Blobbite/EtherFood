"""Immutable typed DAG independent of the project tree and graphical canvas."""

from dataclasses import asdict, dataclass
import json
import re

from .models import StudioError

STAGES = ("profile", "maskcheck", "color", "frames", "geometry", "scale", "preview",
          "checks", "package")
ARTIFACT_KINDS = ("image", "mask", "palette", "mask_report", "preview", "check_report",
                  "package", "diagnostic", "report", "timing")


@dataclass(frozen=True)
class ContentInput:
    role: str
    kind: str
    sha256: str
    revision_id: str | None = None


@dataclass(frozen=True)
class OutputSpec:
    path: str
    kind: str


@dataclass(frozen=True)
class Dependency:
    node: str
    output: str
    kind: str


@dataclass(frozen=True)
class BuildNode:
    key: str
    stage: str
    inputs: tuple[ContentInput, ...] = ()
    dependencies: tuple[Dependency, ...] = ()
    parameters: str = "{}"
    algorithm: str = "1"
    tools: tuple[tuple[str, str], ...] = ()
    outputs: tuple[OutputSpec, ...] = ()
    adapter: str | None = None
    required: bool = True
    blockers: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class VariantTarget:
    key: str
    node: str | None
    required: bool = True


@dataclass(frozen=True)
class BuildGraph:
    nodes: tuple[BuildNode, ...]
    variants: tuple[VariantTarget, ...]

    def ordered(self) -> tuple[BuildNode, ...]:
        by_key = {n.key: n for n in self.nodes}
        if len(by_key) != len(self.nodes) or len(self.nodes) > 200000:
            raise StudioError("validation", "Doppelte Knoten oder zu großer Buildgraph.")
        for node in self.nodes:
            self._validate(node, by_key)
        if len({v.key for v in self.variants}) != len(self.variants):
            raise StudioError("validation", "Doppelte Buildvariante.")
        for variant in self.variants:
            if variant.required and (variant.node not in by_key or
                                     not by_key[variant.node].required):
                raise StudioError("validation", "Erforderliche Variante hat keinen Zielknoten.")
        # Kahn's algorithm: avoids recursion limits for valid large graphs.
        indegree = {n.key: len({d.node for d in n.dependencies}) for n in self.nodes}
        children = {key: [] for key in by_key}
        for n in self.nodes:
            for parent in {d.node for d in n.dependencies}:
                children[parent].append(n.key)
        ready = sorted(key for key, count in indegree.items() if not count)
        ordered = []
        while ready:
            key = ready.pop()
            ordered.append(by_key[key])
            for child in children[key]:
                indegree[child] -= 1
                if not indegree[child]:
                    ready.append(child)
        if len(ordered) != len(self.nodes):
            raise StudioError("validation", "Zyklus im technischen Buildgraph.")
        return tuple(ordered)

    @staticmethod
    def _validate(node: BuildNode, by_key: dict) -> None:
        if not node.key or node.stage not in STAGES or not node.algorithm or not node.outputs:
            raise StudioError("validation", "Unvollständiger Buildknoten.")
        if not isinstance(json.loads(node.parameters), dict):
            raise StudioError("validation", "Buildparameter müssen ein Objekt sein.")
        if len({o.path for o in node.outputs}) != len(node.outputs):
            raise StudioError("validation", "Doppelte Ausgabepfade.")
        for output in node.outputs:
            if (output.kind not in ARTIFACT_KINDS or not output.path or
                    output.path.startswith("/") or "\\" in output.path or ":" in output.path or
                    any(p in {"", ".", ".."} for p in output.path.split("/"))):
                raise StudioError("validation", "Ungültiger Ausgabetyp/Pfad.")
        if len({i.role for i in node.inputs}) != len(node.inputs):
            raise StudioError("validation", "Eingaberollen müssen eindeutig sein.")
        for item in node.inputs:
            if item.kind not in ARTIFACT_KINDS or not re.fullmatch(r"[a-f0-9]{64}", item.sha256):
                raise StudioError("validation", "Ungültiger Inhaltstyp/Digest.")
        for dependency in node.dependencies:
            parent = by_key.get(dependency.node)
            if (parent is None or OutputSpec(dependency.output, dependency.kind)
                    not in parent.outputs or node.required and not parent.required):
                raise StudioError("validation", "Fehlende oder typfremde Buildabhängigkeit.")

    def to_data(self) -> dict:
        return asdict(self)
