"""Work items — stories, tasks, bugs and their subtasks."""

import json

from ..api import Attachment
from ..api.parsing import Html, ZohoDate
from ..core.errors import UsageError
from .base import BaseService


class ItemService(BaseService):
    """Reading and modifying work items."""

    COLUMNS = ("id", "title", "status", "assignee", "points")

    FIELDS = {
        "title": "itemName",
        "status_id": "statusId",
        "owner_ids": "ownerId",
        "points": "points",
    }

    def __init__(self, client, config, lookups):
        super().__init__(client, config)
        self.lookups = lookups

    # -- reads -----------------------------------------------------------

    def list(self, project=None, sprint=None, assignee=None):
        """Items in a sprint, optionally filtered to one assignee."""
        _, project, sprint = self.scope(project, sprint)

        params = {"subitem": "true"}
        if assignee:
            params["filter"] = self._owner_filter(project, assignee)

        response = self.client.paginate(
            self.sprint_path(project, sprint, "item"),
            "itemJObj", action="data", **params)

        statuses = self.lookups.statuses(project)
        rows = response.rows("itemJObj", "item_prop", self.FIELDS)
        for row in rows:
            row["assignee"] = response.name_for(row.pop("owner_ids"))
            status_id = row.pop("status_id")
            row["status"] = statuses.get(status_id, status_id)
        return rows

    def _owner_filter(self, project, assignee):
        """Zoho's own server-side owner filter.

        Filtering names client-side only ever inspected the first page,
        silently hiding assignments that lived on later ones.
        """
        user_id = self.lookups.user_id(project, assignee)
        return json.dumps(
            {"I-owner": [user_id], "queryType": 1, "jsontmpl": "item_default"})

    def get(self, item_id, project=None, sprint=None):
        _, project, sprint = self.scope(project, sprint)
        return self.client.get(
            self.item_path(project, sprint, item_id), action="details")

    # -- writes ----------------------------------------------------------

    def create(self, title, project=None, sprint=None, parent=None, description=None,
               assignee=None, item_type=None, priority=None, points=None,
               start=None, end=None, files=None, dry_run=False):
        """Create an item, or a subtask when ``parent`` is given.

        ``files`` are uploaded afterwards: the API has no way to create an
        item and attach in one request, since the id does not exist yet.
        They are validated *before* the item is created, so a bad path does
        not leave an item behind with nothing attached.
        """
        _, project, sprint = self.scope(project, sprint)
        attachments = [Attachment(path) for path in files or ()]
        for attachment in attachments:
            attachment.read()

        params = self._payload(project, title=title, description=description,
                               points=points, start=start, end=end,
                               item_type=item_type, priority=priority)
        if assignee:
            params["users"] = json.dumps([self.lookups.user_id(project, assignee)])

        # A subtask is the same payload one path segment deeper, so it
        # shares this method rather than duplicating every lookup.
        path = (self.item_path(project, sprint, parent, "subitem") if parent
                else self.sprint_path(project, sprint, "item"))
        created = self.client.post(path, dry_run=dry_run, **params)

        if attachments and created and created.get("addedItemId"):
            self.attach(created["addedItemId"], files, project, sprint)
        return created

    def update(self, item_id, project=None, sprint=None, title=None, description=None,
               status=None, assignee=None, points=None, start=None, end=None,
               dry_run=False):
        """Update fields on an existing item."""
        _, project, sprint = self.scope(project, sprint)
        params = self._payload(project, title=title, description=description,
                               points=points, start=start, end=end)
        if status:
            params["statusid"] = self.lookups.pick(
                self.lookups.status_ids(project), status, "status")
        if assignee:
            params["newusers"] = json.dumps([self.lookups.user_id(project, assignee)])

        if not params:
            raise UsageError(
                "Nothing to update. Pass at least one of "
                "--title/--desc/--status/--assignee/--points/--start/--end.")
        return self.client.post(
            self.item_path(project, sprint, item_id), dry_run=dry_run, **params)

    def delete(self, item_id, project=None, sprint=None, dry_run=False):
        """Delete an item.

        Needs both ``items.DELETE`` scope *and* a project role permitting
        deletion. A role failure returns ``7401.14 Doesn't have permission
        in item``, which no scope change will fix.
        """
        _, project, sprint = self.scope(project, sprint)
        return self.client.delete(
            self.item_path(project, sprint, item_id), dry_run=dry_run)

    # -- attachments -----------------------------------------------------

    def attach(self, item_id, paths, project=None, sprint=None, dry_run=False):
        """Upload one or more files to an item.

        The only multipart endpoint in the API — note the path is *plural*
        (``/attachments/``) while deletion below is singular.
        """
        _, project, sprint = self.scope(project, sprint)
        attachments = [Attachment(path) for path in paths]
        return self.client.upload(
            self.item_path(project, sprint, item_id, "attachments"),
            attachments, dry_run=dry_run, action="attachment")

    def detach(self, item_id, resource_id, project=None, sprint=None, dry_run=False):
        """Remove an attachment by its ``docResourceId``."""
        _, project, sprint = self.scope(project, sprint)
        return self.client.delete(
            self.item_path(project, sprint, item_id, "attachment"),
            dry_run=dry_run, docResourceId=resource_id)

    # -- payload ---------------------------------------------------------

    def _payload(self, project, title=None, description=None, points=None,
                 start=None, end=None, item_type=None, priority=None):
        params = {}
        if title:
            params["name"] = title
        # `is not None`, not truthiness: an empty string is how a
        # description gets cleared, and a falsy check would drop it.
        # The field holds HTML, so plain text is converted — otherwise
        # newlines and bullets collapse into one run-on paragraph.
        if description is not None:
            params["description"] = Html.from_text(description)
        if points is not None:
            params["point"] = points
        if start:
            params["startdate"] = ZohoDate.normalise(start)
        if end:
            params["enddate"] = ZohoDate.normalise(end)
        if item_type:
            params["projitemtypeid"] = self.lookups.pick(
                self.lookups.item_types(project), item_type, "item type")
        if priority:
            params["projpriorityid"] = self.lookups.pick(
                self.lookups.priorities(project), priority, "priority")
        return params
