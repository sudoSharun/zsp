"""Time logs."""

import json
from datetime import datetime, timedelta, timezone

from ..api.parsing import Html, ZohoDate
from .base import BaseService


class TimesheetService(BaseService):
    """Reading and recording logged time."""

    COLUMNS = ("id", "date", "item", "owner", "hours", "notes")

    FIELDS = {
        "item": "itemName",
        "owner_id": "Owner",
        "date": "logDate",
        "millis": "logTime",
        "notes": "logNotes",
        "item_id": "itemId",
    }

    MILLIS_PER_HOUR = 3_600_000
    NOTE_PREVIEW = 80

    def __init__(self, client, config, lookups):
        super().__init__(client, config)
        self.lookups = lookups

    def recent(self, project=None, days=1):
        """Logs from the last ``days`` days.

        The endpoint has no server-side date filter, so every page is
        fetched and the window applied locally.
        """
        _, project, _ = self.scope(project, need_sprint=False)
        response = self.client.paginate(
            self.project_path(project, "timesheet"), "logJObj", action="data")

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        entries = []
        for row in response.rows("logJObj", "log_prop", self.FIELDS):
            logged_at = self._parse_date(row["date"])
            if logged_at is None or logged_at < cutoff:
                continue
            row["owner"] = response.name_for(row.pop("owner_id"))
            row["hours"] = round(int(row.pop("millis")) / self.MILLIS_PER_HOUR, 2)
            row["notes"] = Html.to_text(row.get("notes"), limit=self.NOTE_PREVIEW)
            entries.append(row)
        return entries

    @staticmethod
    def _parse_date(value):
        try:
            return datetime.fromisoformat((value or "").replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def log(self, item_id, duration, project=None, sprint=None, date=None,
            notes=None, user=None, billable=False, dry_run=False):
        """Record time against an item.

        ``duration`` passes through as typed (``"8:00"`` works).
        ``isbillable`` is mandatory — Zoho rejects the call without it
        (``allowedRegex 0|1``).
        """
        _, project, sprint = self.scope(project, sprint)
        params = {
            "action": "additemlog",
            "duration": duration,
            "isbillable": 1 if billable else 0,
        }
        if date:
            params["date"] = ZohoDate.normalise(date)
        if notes:
            params["notes"] = notes
        if user:
            params["users"] = self.lookups.user_id(project, user)

        return self.client.post(
            self.item_path(project, sprint, item_id, "timesheet"),
            dry_run=dry_run, **params)

    def delete_logs(self, log_ids, project=None, dry_run=False):
        """Delete one or more logs. Requires ``timesheets.DELETE`` scope."""
        _, project, _ = self.scope(project, need_sprint=False)
        return self.client.delete(
            self.project_path(project, "timesheet"), dry_run=dry_run,
            action="deletelogs", logidarr=json.dumps(list(log_ids)))
