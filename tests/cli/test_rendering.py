"""Renderer: aligned tables, JSON mode, empty results."""

import json

from zsp.cli import Renderer


def collect():
    """A renderer that captures output instead of printing it."""
    lines = []
    return lines, lambda text: lines.append(text)


class TestTable:
    def test_json_round_trips(self):
        rows = [{"id": "1", "name": "a"}]
        lines, printer = collect()
        Renderer(as_json=True, printer=printer).table(rows, ["id", "name"])
        assert json.loads(lines[0]) == rows

    def test_columns_are_aligned(self):
        rows = [{"id": "1", "name": "alpha"}, {"id": "22", "name": "b"}]
        text = Renderer(printer=lambda *a: None).table(rows, ["id", "name"])
        header, first, second = text.splitlines()

        offset = header.index("NAME")
        assert header.startswith("ID")
        assert first[offset:offset + 5] == "alpha"
        assert second[offset] == "b"

    def test_empty_rows_report_none(self):
        text = Renderer(printer=lambda *a: None).table([], ["id"])
        assert text == "(none)"

    def test_empty_rows_as_json_are_a_list(self):
        text = Renderer(as_json=True, printer=lambda *a: None).table([], ["id"])
        assert json.loads(text) == []

    def test_none_values_render_blank(self):
        text = Renderer(printer=lambda *a: None).table(
            [{"id": "1", "name": None}], ["id", "name"])
        assert text.splitlines()[1].strip() == "1"

    def test_missing_column_is_tolerated(self):
        text = Renderer(printer=lambda *a: None).table([{"id": "1"}], ["id", "absent"])
        assert "1" in text


class TestDetail:
    def test_prints_key_values(self):
        text = Renderer(printer=lambda *a: None).detail({"a": 1, "b": "two"})
        assert text.splitlines() == ["a: 1", "b: two"]

    def test_json_mode(self):
        text = Renderer(as_json=True, printer=lambda *a: None).detail({"a": 1})
        assert json.loads(text) == {"a": 1}


class TestMessage:
    def test_prints_in_human_mode(self):
        lines, printer = collect()
        Renderer(printer=printer).message("done")
        assert lines == ["done"]

    def test_is_suppressed_in_json_mode(self):
        """Status chatter would make stdout invalid JSON."""
        lines, printer = collect()
        Renderer(as_json=True, printer=printer).message("done")
        assert lines == []
