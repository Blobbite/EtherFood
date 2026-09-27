"""Lossless boundaries and predictable structural operations for Markdown editing."""

import pytest

from etherfood_studio.ui.documents.markdown_source import MarkdownTable, checkbox_offsets


def test_table_changes_preserve_other_source_escapes_alignment_and_crlf():
    original = ("\r\n| **Name** | Wert |\r\n| :--- | ---: |\r\n"
                "| a \\| b | `x\\|y` |\r\n| [Link][ref] | 🧩 |\r\n\r\n"
                "[ref]: https://example.org \"Titel\"\r\n")
    model = MarkdownTable.parse(original)
    assert model is not None
    assert model.text() == original
    model.move_column(0, 1)
    model.move_row(1, 2)
    value = model.text()
    assert "| Wert | **Name** |\r\n| ---: | :--- |" in value
    assert value.index("[Link][ref]") < value.index("a \\| b")
    assert value.endswith("\r\n\r\n[ref]: https://example.org \"Titel\"\r\n")
    model.edit(2, 0, "x|y und z\\|q")
    assert " x\\|y und z\\|q " == model.rows[2][0]
    model.insert_column(1)
    model.insert_row(2)
    assert len(model.rows) == 4 and all(len(row) == 3 for row in model.rows)
    model.remove_columns([1])
    model.remove_rows([0, 2])
    assert len(model.rows) == 3 and len(model.separators) == 2
    before = model.text()
    model.remove_columns([0, 1])
    model.move_row(0, 1)
    assert model.text() == before


@pytest.mark.parametrize("text", [
    "Text ohne Tabelle", "```md\n| A |\n|---|\n```", "| A |\n|---|\n|1|2|",
    "| A |\n|---|\n\nWeiterer Absatz", "|" + "A|" * 51 + "\n|" + "---|" * 51,
])
def test_unsupported_tables_remain_source_instead_of_dropping_data(text):
    assert MarkdownTable.parse(text) is None


def test_checkbox_source_positions_only_for_real_list_items():
    value = ("- [ ] Eins\r\n  - [X] Kind\r\n- kein Haken\r\n\r\n"
             "> - [x] Zitat\r\n\r\n1. [ ] Nummeriert\r\n\r\n"
             "```md\r\n- [ ] Code\r\n```\r\n\r\n"
             "    - [ ] Eingerückter Code\r\n\r\n\\- [ ] Text\r\n\r\n"
             "- \\[ ] Maskiert\r\n\r\nAbsatz [ ] kein To-do\r\n")
    offsets = checkbox_offsets(value)
    assert len(offsets) == 4
    assert [value[offset] for offset in offsets] == [" ", "X", "x", " "]
    for offset in offsets:
        assert value[offset - 1:offset + 2] in {"[ ]", "[x]", "[X]"}
