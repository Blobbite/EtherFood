"""Source-mapped table operations and task markers, without HTML serialization."""

import re
from dataclasses import dataclass

from markdown_it import MarkdownIt


def parser() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])


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
    for char in value.replace("\r", " ").replace("\n", " "):
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
                   lines[end - 1].endswith("\n"))

    def text(self) -> str:
        rows = [self.rows[0], self.separators] + self.rows[1:]
        body = self.newline.join("|" + "|".join(row) + "|" for row in rows)
        return self.prefix + body + (self.newline if self.terminated else "") + self.suffix

    def edit(self, row: int, column: int, value: str) -> None:
        self.rows[row][column] = escape_cell(value)

    def insert_column(self, index: int) -> None:
        for row in self.rows:
            row.insert(index, " ")
        self.separators.insert(index, " --- ")

    def insert_row(self, index: int) -> None:
        self.rows.insert(max(1, index), [" "] * len(self.separators))

    def move_column(self, before: int, after: int) -> None:
        for row in self.rows + [self.separators]:
            row.insert(after, row.pop(before))

    def move_row(self, before: int, after: int) -> None:
        if before > 0 and after > 0:
            self.rows.insert(after, self.rows.pop(before))

    def remove_columns(self, indices: list[int]) -> None:
        if len(set(indices)) >= len(self.separators):
            return
        for index in sorted(set(indices), reverse=True):
            for row in self.rows + [self.separators]:
                del row[index]

    def remove_rows(self, indices: list[int]) -> None:
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
