"""Resolving human-readable names to Zoho ids.

Every id in Sprints is a 19-digit number. Commands accept names instead
(``--status Done``, ``--assignee ada``, ``--type Bug``) and resolve them
here, failing with the list of valid options rather than sending a wrong id.
"""

from ..core.errors import LookupError_
from .base import BaseService


class LookupService(BaseService):
    """Name → id resolution for statuses, item types, priorities and users."""

    def statuses(self, project):
        """``{status id: label}`` — e.g. ``To do``, ``In progress``, ``Done``."""
        response = self.client.fetch(
            self.project_path(project, "itemstatus"),
            action="data", index=1, range=25)
        rows = response.rows("statusJObj", "status_prop", {"name": "statusName"})
        return {row["id"]: row["name"] for row in rows}

    def status_ids(self, project):
        """``{label: status id}`` — the inverse of :meth:`statuses`."""
        return {name: sid for sid, name in self.statuses(project).items()}

    def item_types(self, project):
        """``{label: id}`` for item types, e.g. ``Story``/``Task``/``Bug``."""
        response = self.client.fetch(
            self.project_path(project, "itemtype"),
            action="data", index=1, range=25)
        rows = response.rows("projItemTypeJObj", "projItemType_prop",
                             {"name": "itemTypeName"})
        return {row["name"]: row["id"] for row in rows}

    def priorities(self, project):
        """``{label: id}`` for priorities, e.g. ``None``/``Low``/``High``."""
        response = self.client.fetch(
            self.project_path(project, "priority"),
            action="data", index=1, range=25)
        rows = response.rows("projPriorityJObj", "projPriority_prop",
                             {"name": "priorityName"})
        return {row["name"]: row["id"] for row in rows}

    def users(self, project):
        """``{display name: user id}`` for project members."""
        response = self.client.fetch(
            self.project_path(project, "users"),
            action="data", index=1, range=100)
        rows = response.rows("userJObj", "user_prop", {"name": "displayName"})
        return {row["name"]: row["id"] for row in rows if row["name"]}

    def user_id(self, project, needle):
        """First member whose display name contains ``needle``.

        Case-insensitive substring, so ``ada`` matches ``Ada Lovelace``.
        """
        members = self.users(project)
        lowered = needle.lower()
        for name, user_id in members.items():
            if lowered in name.lower():
                return user_id
        raise LookupError_(
            f"No project user matching '{needle}'. "
            f"Known: {', '.join(sorted(members))}"
        )

    @staticmethod
    def pick(mapping, wanted, label):
        """Case-insensitive ``{name: id}`` lookup, listing options on failure."""
        for name, value in mapping.items():
            if name.lower() == wanted.lower():
                return value
        raise LookupError_(
            f"Unknown {label} '{wanted}'. Valid: {', '.join(sorted(mapping))}"
        )
