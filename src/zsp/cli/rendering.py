"""Terminal output.

Two modes chosen per invocation: aligned columns for humans, JSON for
scripts and agents (``--json``).
"""

import json


class Renderer:
    """Formats command results for the terminal."""

    GAP = "  "
    EMPTY = "(none)"

    def __init__(self, as_json=False, printer=print):
        self.as_json = as_json
        self._print = printer

    def table(self, rows, columns):
        """Render a list of dicts as aligned columns, or as JSON."""
        text = json.dumps(rows, indent=2) if self.as_json else self._tabulate(rows, columns)
        self._print(text)
        return text

    def detail(self, data):
        """Render a single record as key/value lines, or as JSON."""
        if self.as_json:
            text = json.dumps(data, indent=2)
        else:
            text = "\n".join(f"{key}: {value}" for key, value in data.items())
        self._print(text)
        return text

    def message(self, text):
        """Plain status line, suppressed in JSON mode to keep stdout valid."""
        if not self.as_json:
            self._print(text)

    def _tabulate(self, rows, columns):
        if not rows:
            return self.EMPTY

        widths = {
            column: max(len(column), *(len(self._cell(row, column)) for row in rows))
            for column in columns
        }
        header = self.GAP.join(column.upper().ljust(widths[column]) for column in columns)
        body = [
            self.GAP.join(self._cell(row, column).ljust(widths[column])
                          for column in columns).rstrip()
            for row in rows
        ]
        return "\n".join([header, *body])

    @staticmethod
    def _cell(row, column):
        value = row.get(column)
        return "" if value is None else str(value)
