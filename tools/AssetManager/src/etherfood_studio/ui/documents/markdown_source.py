"""Source-mapped table operations and task markers, without HTML serialization."""

import re
from dataclasses import dataclass, field

from .markdown_syntax import parser


def split_cells(line: str) -> list[str]:
    """Keep cell Markdown, including escaped pipes and surrounding whitespace."""
    line = line.rstrip("\r\n").strip()
    cells, start, backslashes = [], 0, 0
    for index, char in enumerate(line):
        if char == "|" and backslashes % 2 == 0:
            cells.append(line[start:index])
            start = index + 1
        backslashes = backslashes + 1 if char == "\\" else 0
    cells.append(line[start:])
    if line.startswith("|"):
        cells.pop(0)
    if len(cells) > 1 and cells[-1] == "":
        cells.pop()
    return cells


def escape_cell(value: str) -> str:
    """Bare pipes typed into a cell are literal; already escaped pipes stay escaped."""
    result, backslashes = [], 0
    for char in value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>"):
        if char == "|" and backslashes % 2 == 0:
            result.append("\\")
        result.append(char)
        backslashes = backslashes + 1 if char == "\\" else 0
    return " " + "".join(result).strip() + " "


@dataclass
class MarkdownTable:
    prefix: str
    suffix: str
    rows: list[list[str]]
    separators: list[str]
    newline: str = "\n"
    terminated: bool = True
    original: str | None = None
    original_start: int = 0
    edits: dict = field(default_factory=dict)

    @classmethod
    def parse(cls, text: str) -> "MarkdownTable | None":
        lines = text.splitlines(keepends=True)
        roots = [token for token in parser().parse(text)
                 if token.level == 0 and token.map and token.nesting >= 0]
        if len(roots) != 1 or roots[0].type != "table_open":
            return None
        start, end = roots[0].map
        parts = [split_cells(line) for line in lines[start:end]]
        if len(parts) < 2 or not parts[0]:
            return None
        width = len(parts[0])
        # Oversized/ambiguous tables remain editable as source, never truncate cells.
        if width > 50 or len(parts) * width > 3000:
            return None
        if len(parts[1]) != width or any(len(row) > width for row in parts):
            return None
        if not all(re.fullmatch(r"\s*:?-+:?\s*", cell) for cell in parts[1]):
            return None
        rows = [parts[0]] + [row + [" "] * (width - len(row)) for row in parts[2:]]
        return cls("".join(lines[:start]), "".join(lines[end:]), rows, parts[1],
                   "\r\n" if lines[start].endswith("\r\n") else "\n",
                   lines[end - 1].endswith("\n"), text, start)

    def text(self) -> str:
        if self.original is not None:
            lines = self.original.splitlines(keepends=True)
            for row, values in self.edits.items():
                line_number = self.original_start + row + (1 if row else 0)
                raw = lines[line_number]
                content = raw.rstrip("\r\n")
                boundaries, start, backslashes = [], 0, 0
                for index, char in enumerate(content):
                    if char == "|" and backslashes % 2 == 0:
                        boundaries.append((start, index))
                        start = index + 1
                    backslashes = backslashes + 1 if char == "\\" else 0
                boundaries.append((start, len(content)))
                if content.lstrip().startswith("|"):
                    boundaries.pop(0)
                if len(boundaries) > 1 and not content[slice(*boundaries[-1])].strip():
                    boundaries.pop()
                if any(column >= len(boundaries) for column in values):
                    self.original = None
                    return self.text()
                for column in sorted(values, reverse=True):
                    start, end = boundaries[column]
                    raw = raw[:start] + self.rows[row][column] + raw[end:]
                lines[line_number] = raw
            return "".join(lines)
        rows = [self.rows[0], self.separators] + self.rows[1:]
        body = self.newline.join("|" + "|".join(row) + "|" for row in rows)
        return self.prefix + body + (self.newline if self.terminated else "") + self.suffix

    def edit(self, row: int, column: int, value: str) -> None:
        self.rows[row][column] = escape_cell(value)
        self.edits.setdefault(row, set()).add(column)

    def cell_range(self, row, column):
        text = self.text()
        lines = text.splitlines(keepends=True)
        root = next(t for t in parser().parse(text) if t.type == "table_open")
        number = root.map[0] + row + (1 if row else 0)
        raw = lines[number].rstrip("\r\n")
        ranges, start, backslashes = [], 0, 0
        for index, char in enumerate(raw):
            if char == "|" and backslashes % 2 == 0:
                ranges.append((start, index))
                start = index + 1
            backslashes = backslashes + 1 if char == "\\" else 0
        ranges.append((start, len(raw)))
        if raw.lstrip().startswith("|"):
            ranges.pop(0)
        if len(ranges) > 1 and not raw[slice(*ranges[-1])].strip():
            ranges.pop()
        if column >= len(ranges):
            return None
        start, end = ranges[column]
        offset = sum(map(len, lines[:number]))
        return offset + start, offset + end

    def insert_column(self, index: int) -> None:
        self.original = None
        for row in self.rows:
            row.insert(index, " ")
        self.separators.insert(index, " --- ")

    def insert_row(self, index: int) -> None:
        self.original = None
        self.rows.insert(max(1, index), [" "] * len(self.separators))

    def align(self, column, alignment):
        self.original = None
        self.separators[column] = {"left": " :--- ", "center": " :---: ",
            "right": " ---: "}[alignment]

    def move_column(self, before: int, after: int) -> None:
        self.original = None
        for row in self.rows + [self.separators]:
            row.insert(after, row.pop(before))

    def move_row(self, before: int, after: int) -> None:
        if before > 0 and after > 0:
            self.original = None
            self.rows.insert(after, self.rows.pop(before))

    def remove_columns(self, indices: list[int]) -> None:
        if len(set(indices)) >= len(self.separators):
            return
        self.original = None
        for index in sorted(set(indices), reverse=True):
            for row in self.rows + [self.separators]:
                del row[index]

    def remove_rows(self, indices: list[int]) -> None:
        self.original = None
        for index in sorted(set(indices) - {0}, reverse=True):
            del self.rows[index]


def checkbox_offsets(text: str) -> list[int]:
    """Find actual list-item markers, excluding fences, escapes and plain paragraphs."""
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    result = []
    for token in parser().parse(text):
        if token.type != "list_item_open" or not token.map:
            continue
        line = token.map[0]
        match = re.match(r"\s*(?:>\s*)*(?:[-+*]|\d+[.)])\s+\[([ xX])\](?:\s|$)",
                         lines[line])
        if match:
            result.append(offsets[line] + match.start(1))
    return result
