"""Workspaces and projects."""

from .base import BaseService


class WorkspaceService(BaseService):
    """Workspaces — Zoho calls them both *teams* and *portals*."""

    COLUMNS = ("id", "name")

    def list(self):
        """All workspaces on the account.

        ``/teams/`` is the only *plural* path in the API; every other
        endpoint is ``/team/{id}/...``.
        """
        portals = self.client.get("/teams/").get("portals") or []
        return [{"id": p.get("zsoid"), "name": p.get("teamName")} for p in portals]


class ProjectService(BaseService):
    """Projects within a workspace."""

    COLUMNS = ("id", "name", "start", "end", "status")

    FIELDS = {
        "name": "projName",
        "start": "startDate",
        "end": "endDate",
        "status": "status",
    }

    def list(self, limit=25):
        response = self.client.fetch(
            f"/team/{self.team}/projects/", action="data", index=1, range=limit)
        return response.rows("projectJObj", "project_prop", self.FIELDS)

    def backlog_id(self, project):
        """The backlog behaves as a virtual sprint and has its own id."""
        return self.client.get(self.project_path(project), action="getbacklog").get("backlogId")
