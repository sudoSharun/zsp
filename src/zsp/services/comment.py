"""Item comments.

Zoho's published API collection documents comments at
``/modules/{moduleId}/entity/{itemId}/notes/`` with an ``addnotes``
parameter. That path returns 401 for every module id, and ``addnotes`` is
rejected as *"Extra parameter found in URL"*. The sprint-scoped endpoint
used here, with ``name`` alone, is what actually works.

A second trap: the **read** payload keys rows under ``notesJObj`` while the
**write** response uses ``itemnotesJObj`` for the same data. Reading the
wrong key makes a successful post look like a failure.
"""

from ..api.parsing import Html
from .base import BaseService


class CommentService(BaseService):
    """Reading, adding and deleting comments on an item."""

    COLUMNS = ("id", "author", "created", "text")

    FIELDS = {
        "text": "notes",
        "author_id": "createdBy",
        "created": "createdOn",
    }

    def list(self, item_id, project=None, sprint=None, limit=50):
        _, project, sprint = self.scope(project, sprint)
        response = self.client.fetch(
            self.item_path(project, sprint, item_id, "notes"),
            index=1, range=limit)

        rows = response.rows("notesJObj", "notes_prop", self.FIELDS)
        for row in rows:
            row["author"] = response.name_for(row.pop("author_id"))
            row["text"] = Html.to_text(row.get("text"))
        return rows

    def add(self, item_id, text, project=None, sprint=None, dry_run=False):
        """Add a comment.

        The field holds HTML, so plain text is converted first — otherwise
        newlines and ``-`` bullets collapse into one run-on paragraph.
        """
        _, project, sprint = self.scope(project, sprint)
        return self.client.post(
            self.item_path(project, sprint, item_id, "notes"),
            dry_run=dry_run, name=Html.from_text(text))

    def delete(self, item_id, note_id, project=None, sprint=None, dry_run=False):
        """Delete a comment.

        Comments are deletable even in projects where the role forbids
        deleting the items themselves.
        """
        _, project, sprint = self.scope(project, sprint)
        return self.client.delete(
            self.item_path(project, sprint, item_id, f"notes/{note_id}"),
            dry_run=dry_run)
