"""CommonMark tokens and small product extensions, never a Markdown serializer."""

import re
import unicodedata
from dataclasses import dataclass
from html import escape
from urllib.parse import quote

from markdown_it import MarkdownIt
from markdown_it.rules_inline import image, link, autolink
from markdown_it.rules_inline.text import text as plain_text
from markdown_it.token import Token


def tracked(rule):
    def parse(state, silent):
        start, count = state.pos, len(state.tokens)
        matched = rule(state, silent)
        if matched and not silent:
            for token in state.tokens[count:]:
                if token.type in {"image", "link_open"} and "span" not in token.meta:
                    token.meta["span"] = (start, state.pos)
                    token.meta["source"] = state.src[start:state.pos]
                    break
        return matched
    return parse


def wiki(state, silent):
    start = state.pos
    picture = state.src.startswith("![[", start)
    prefix = 3 if picture else 2
    if not picture and (not state.src.startswith("[[", start) or state.linkLevel
                        or (start and state.src[start - 1] == "!")):
        return False
    end = state.src.find("]]", start + prefix, state.posMax)
    if end < 0:
        return False
    content = state.src[start + prefix:end]
    if not content or any(c in content for c in "\n\r[]\\"):
        return False
    destination, separator, alias = content.partition("|")
    if picture and (separator or "#" in destination or ":" in destination
                    or destination.lower().split("?")[0].rsplit(".", 1)[-1]
                    not in {"png", "jpg", "jpeg", "webp", "gif", "svg"}):
        return False
    if not destination.strip() or (separator and not alias):
        return False
    if not silent:
        token = state.push("image" if picture else "link_open", "img" if picture else "a",
                           0 if picture else 1)
        token.attrs = {"src" if picture else "href":
                       destination if picture else "studio-wiki:" + quote(destination, safe="")}
        token.meta = {"span": (start, end + 2), "source": state.src[start:end + 2]}
        if picture:
            token.content = destination
            token.children = [Token("text", "", 0, content=destination)]
        else:
            state.push("text", "", 0).content = alias if separator else destination
            state.push("link_close", "a", -1)
    state.pos = end + 2
    return True


def bare_url(state, silent):
    if state.linkLevel or not re.match(r"https?://", state.src[state.pos:], re.I):
        return False
    match = re.match(r'https?://[^\s<>"\x00-\x1f]+', state.src[state.pos:], re.I)
    value = match[0].rstrip(".,;:!?'")
    while value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    while value.endswith("]") and value.count("]") > value.count("["):
        value = value[:-1]
    if not state.md.validateLink(value):
        return False
    start = state.pos
    if not silent:
        token = state.push("link_open", "a", 1)
        token.attrSet("href", state.md.normalizeLink(value))
        token.meta = {"span": (start, start + len(value)), "source": value}
        state.push("text", "", 0).content = value
        state.push("link_close", "a", -1)
    state.pos += len(value)
    return True


def text_before_url(state, silent):
    start = state.pos
    matched = plain_text(state, silent)
    if matched:
        match = re.search(r"https?://", state.src[start:state.posMax], re.I)
        if match and start < start + match.start() < state.pos:
            end = start + match.start()
            if not silent:
                state.pending = state.pending[:-(state.pos - end)]
            state.pos = end
    return matched


def cell_break(state, silent):
    match = re.match(r"<br(?:/| /)?>", state.src[state.pos:])
    if not match:
        return False
    if not silent:
        state.push("hardbreak", "br", 0)
    state.pos += len(match[0])
    return True


def parser():
    md = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
    validate_link = md.validateLink
    # A file reference is syntax, not permission: MediaSession still needs an exact-file grant.
    md.validateLink = lambda value: value.lower().startswith("file:") or validate_link(value)
    md.inline.ruler.before("image", "wiki", wiki)
    md.inline.ruler.before("text", "bare_url", bare_url)
    md.inline.ruler.before("html_inline", "cell_break", cell_break)
    md.inline.ruler.at("text", text_before_url)
    for name, rule in (("image", image), ("link", link), ("autolink", autolink)):
        md.inline.ruler.at(name, tracked(rule))
    md.core.ruler.before("block", "bom", lambda state: setattr(state, "src",
        state.src.removeprefix("\ufeff")))
    return md


def visible(tokens):
    return "".join(visible(t.children) if t.children else
                   " " if t.type in {"softbreak", "hardbreak"} else
                   t.content if t.type in {"text", "code_inline", "image"} else ""
                   for t in tokens or [])


def slug(text, used):
    value = unicodedata.normalize("NFC", text).lower()
    value = re.sub(r"\s+", "-", value)
    value = "".join(c for c in value if c in "_-" or unicodedata.category(c)[0] in "LNM")
    base = value.strip("-") or "abschnitt"
    value, suffix = base, 0
    while value in used:
        suffix += 1
        value = f"{base}-{suffix}"
    used.add(value)
    return value


@dataclass(frozen=True)
class Heading:
    identifier: str
    title: str
    offset: int
    level: int


def headings(source):
    lines, used, result = source.splitlines(keepends=True), set(), []
    tokens = parser().parse(source)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            title = visible(tokens[index + 1].children)
            result.append(Heading(slug(title, used), title, offsets[token.map[0]],
                                  int(token.tag[1:])))
    return result


def render(source, *, references="", image_renderer=None):
    """Produce trusted presentation HTML from parsed tokens; source HTML stays escaped."""
    md = parser()
    if image_renderer:
        md.renderer.rules["image"] = image_renderer
    environment = {}
    if references:
        md.parse(references, environment)
    tokens = md.parse(source, environment)
    tasks = []
    in_item = False
    used = set()
    inset = 0
    for index, token in enumerate(tokens):
        if token.type in {"blockquote_open", "bullet_list_open", "ordered_list_open"}:
            inset += 32
        elif token.type in {"blockquote_close", "bullet_list_close", "ordered_list_close"}:
            inset = max(0, inset - 32)
        if token.type == "inline":
            for child in token.children or []:
                if child.type == "image":
                    child.meta["inset"] = inset
        if token.type == "list_item_open":
            in_item = True
        elif token.type == "heading_open":
            token.attrSet("id", slug(visible(tokens[index + 1].children), used))
        elif token.type == "inline" and in_item:
            in_item = False
            if token.children and token.children[0].type == "text":
                first = token.children[0]
                match = re.match(r"^\[([ xX])\](?:\s|$)", first.content)
                if match:
                    tasks.append(match[1].lower() == "x")
                    first.content = ("☑" if tasks[-1] else "☐") + " " + first.content[match.end():]
                    first.meta["task"] = len(tasks) - 1
    def text_renderer(tokens, index, options, env):
        token = tokens[index]
        if "task" in token.meta:
            return ('<a name="studio-task-' + str(token.meta["task"]) + '">' +
                    escape(token.content[:2]) + '</a>' + escape(token.content[2:]))
        return escape(token.content)
    md.renderer.rules["text"] = text_renderer
    return md.renderer.render(tokens, md.options, environment), tasks


def code_content(source, token):
    """Copy code bytes as text with the original newline convention."""
    if token.type == "fence":
        lines = source.splitlines(keepends=True)
        start, end = token.map
        if end > start + 1 and re.match(r"^ {0,3}" + re.escape(token.markup[0]) +
                                       "{" + str(len(token.markup)) + r",}\s*$", lines[end - 1]):
            end -= 1
        indent = len(lines[start]) - len(lines[start].lstrip(" "))
        return "".join(line[min(indent, len(line) - len(line.lstrip(' '))):]
            for line in lines[start + 1:end])
    lines = source.splitlines(keepends=True)[token.map[0]:token.map[1]]
    result = []
    for line in lines:
        index, columns = 0, 0
        while index < len(line) and columns < 4 and line[index] in " \t":
            columns += 4 - columns % 4 if line[index] == "\t" else 1
            index += 1
        result.append(line[index:])
    return "".join(result)


def link_spans(source, references=""):
    """Map parser-recognized links to original source, excluding code and escapes."""
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    result = []
    md, environment, row_cursors = parser(), {}, {}
    if references:
        md.parse(references, environment)
    in_cell = False
    for token in md.parse(source, environment):
        if token.type in {"th_open", "td_open"}:
            in_cell = True
        elif token.type in {"th_close", "td_close"}:
            in_cell = False
        if token.type != "inline" or not token.map:
            continue
        mapping = []
        row = token.map[0]
        for part in token.content.split("\n"):
            matched = False
            while row < token.map[1]:
                raw = lines[row].rstrip("\r\n")
                indices = [i for i in range(len(raw)) if not (in_cell and raw[i:i + 2] == "\\|")]
                normalized = "".join(raw[i] for i in indices)
                begin = next((i for i, value in enumerate(indices)
                    if value >= row_cursors.get(row, 0)), len(indices)) if in_cell else 0
                found = normalized.find(part, begin)
                if found >= 0:
                    selected = indices[found:found + len(part)]
                    mapping.extend(offsets[row] + i for i in selected)
                    if selected:
                        row_cursors[row] = selected[-1] + 1
                    matched = True
                    break
                row += 1
            if not matched:
                break
            mapping.append(offsets[row] + len(lines[row].rstrip("\r\n")))
            row += 1
        for child in token.children or []:
            if child.type not in {"link_open", "image"} or "span" not in child.meta:
                continue
            start, end = child.meta["span"]
            if end <= len(mapping):
                result.append((mapping[start], mapping[end - 1] + 1, child))
    return result


def inline_reference(label, destination, title="", *, image=False):
    label = label.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    destination = quote(destination, safe="/:#?=&%+@!$;,*~-._")
    suffix = ' "' + title.replace("\\", "\\\\").replace('"', '\\"') + '"' if title else ""
    return ("!" if image else "") + "[" + label + "](<" + destination + ">" + suffix + ")"


def preserved_edit(original, edited):
    """Return the smallest original-source patch after Qt normalizes CRLF for display."""
    normalized = original.replace("\r\n", "\n").replace("\r", "\n")
    start, tail = 0, 0
    limit = min(len(normalized), len(edited))
    while start < limit and normalized[start] == edited[start]:
        start += 1
    while tail < limit - start and normalized[-tail - 1] == edited[-tail - 1]:
        tail += 1
    offsets, index = [0], 0
    while index < len(original):
        index += 2 if original[index:index + 2] == "\r\n" else 1
        offsets.append(index)
    newline = "\r\n" if "\r\n" in original else "\r" if "\r" in original else "\n"
    value = edited[start:len(edited) - tail].replace("\n", newline)
    return offsets[start], offsets[len(normalized) - tail], value


def utf16_position(text, offset):
    return len(text[:offset].encode("utf-16-le")) // 2


def python_position(text, position):
    return len(text.encode("utf-16-le")[:position * 2].decode("utf-16-le", errors="ignore"))


def source_position(raw, plain_position):
    """Map a normalized character offset back through original CRLF line endings."""
    index, count = 0, 0
    while count < plain_position and index < len(raw):
        index += 2 if raw[index:index + 2] == "\r\n" else 1
        count += 1
    return index
