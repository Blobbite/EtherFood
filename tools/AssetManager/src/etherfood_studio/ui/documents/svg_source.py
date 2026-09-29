"""Bounded static SVG allowlist; only a preview copy reaches Qt's renderer."""

import re
import xml.etree.ElementTree as ET

from ...domain.models import StudioError

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
TAGS = {"svg", "g", "defs", "path", "rect", "circle", "ellipse", "line", "polyline",
        "polygon", "text", "tspan", "linearGradient", "radialGradient", "stop", "use",
        "clipPath", "title", "desc"}
PAINT = {"fill", "stroke", "fill-opacity", "stroke-opacity", "opacity", "fill-rule",
         "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit",
         "stroke-dasharray", "stroke-dashoffset", "color", "stop-color", "stop-opacity",
         "font-family", "font-size", "font-weight", "font-style", "text-anchor",
         "dominant-baseline", "display", "visibility", "clip-path", "clip-rule"}
ATTRIBUTES = PAINT | {"id", "x", "y", "x1", "x2", "y1", "y2", "dx", "dy", "cx", "cy",
                      "r", "rx", "ry", "width", "height", "viewBox", "preserveAspectRatio",
                      "d", "points", "transform", "gradientTransform", "gradientUnits",
                      "spreadMethod", "offset", "fx", "fy", "fr", "href", "version",
                      "clipPathUnits", "textLength", "lengthAdjust", "rotate"}


def sanitize_svg(raw, *, max_bytes=16 * 1024 * 1024):
    if len(raw) > max_bytes:
        raise StudioError("blocked", "SVG überschreitet die Größenbegrenzung.")
    try:
        source = raw.decode("utf-8-sig")
    except UnicodeError as error:
        raise StudioError("unsupported", "SVG-Vorschau benötigt UTF-8.") from error
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)|<\?(?!xml\s)", source, re.I) or "\x00" in source:
        raise StudioError("blocked",
            "SVG mit DTD, Entitäten oder Verarbeitungsanweisungen blockiert.")
    try:
        root = ET.fromstring(source)
    except ET.ParseError as error:
        raise StudioError("unsupported", "SVG ist kein gültiges XML.") from error
    if root.tag not in {"svg", "{" + SVG + "}svg"}:
        raise StudioError("unsupported", "Die Quelle ist keine SVG-Grafik.")
    identifiers, references, count, geometry = {}, {}, 0, 0

    def visit(node, depth):
        nonlocal count, geometry
        count += 1
        if count > 4096 or depth > 32:
            raise StudioError("blocked", "SVG überschreitet die Strukturbegrenzung.")
        name = node.tag.removeprefix("{" + SVG + "}")
        if name not in TAGS:
            raise StudioError("unsupported", "SVG-Inhalt nicht statisch darstellbar: " + name)
        node.tag = "{" + SVG + "}" + name
        refs = []
        for key, value in list(node.attrib.items()):
            name = key.removeprefix("{" + XLINK + "}")
            if key == "{http://www.w3.org/XML/1998/namespace}space" and value in {"preserve",
                "default"}:
                continue
            if name == "style":
                del node.attrib[key]
                for declaration in value.split(";"):
                    if not declaration.strip():
                        continue
                    prop, colon, val = declaration.partition(":")
                    prop, val = prop.strip(), val.strip()
                    if not colon or prop not in PAINT or prop in node.attrib:
                        raise StudioError("unsupported",
                            "SVG enthält nicht unterstützte Stilregeln.")
                    node.attrib[prop] = val
            elif name not in ATTRIBUTES or (key.startswith("{") and not key.startswith("{"
                + XLINK + "}")):
                raise StudioError("unsupported", "SVG-Attribut nicht freigegeben: " + name)
        for key, value in node.attrib.items():
            name = key.removeprefix("{" + XLINK + "}")
            if name in {"d", "points", "transform", "gradientTransform"}:
                geometry += len(value)
                if geometry > 500_000:
                    raise StudioError("blocked", "SVG-Geometrie überschreitet die Vorschaugrenze.")
            if (len(value) > 1_000_000 or
                    re.search(r"(?:https?:|file:|data:|@|\\|expression\s*\()", value, re.I)):
                raise StudioError("blocked", "SVG enthält externe oder aktive Inhalte.")
            if name == "id":
                if value in identifiers:
                    raise StudioError("unsupported", "SVG enthält doppelte Kennungen.")
                identifiers[value] = node
            if name == "href":
                if not re.fullmatch(r"#[\w.-]+", value):
                    raise StudioError("blocked", "SVG darf nur interne Referenzen verwenden.")
                refs.append(value[1:])
            if "url" in value.lower():
                if name not in {"fill", "stroke", "clip-path"} or not re.fullmatch(
                        r"url\(#[\w.-]+\)", value):
                    raise StudioError("blocked", "SVG-Ressource ist nicht freigegeben.")
                refs.append(value[5:-1])
        references[node] = refs
        for child in node:
            visit(child, depth + 1)

    visit(root, 0)
    operations = 0

    def expand(node, stack):
        nonlocal operations
        operations += 1
        if node in stack or len(stack) > 32 or operations > 16384:
            raise StudioError("blocked", "SVG enthält zyklische oder zu umfangreiche Referenzen.")
        for target in references[node]:
            if target not in identifiers:
                raise StudioError("unsupported", "SVG-Referenz fehlt: " + target)
            expand(identifiers[target], stack | {node})
        for child in node:
            expand(child, stack | {node})

    expand(root, set())
    ET.register_namespace("", SVG)
    ET.register_namespace("xlink", XLINK)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
