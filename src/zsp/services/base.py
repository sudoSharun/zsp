"""Shared behaviour for every resource service."""

from ..core.errors import LookupError_


class BaseService:
    """Holds the client and config each service needs.

    Services are constructed once by :class:`~zsp.cli.Application` and
    receive their collaborators explicitly, so any of them can be built
    with a stub client in tests.
    """

    def __init__(self, client, config):
        self.client = client
        self.config = config

    @property
    def team(self):
        """Workspace id, resolved lazily and cached on the config."""
        if not self.config.team_id:
            self.config.team_id = self._first_workspace_id()
        return self.config.team_id

    def _first_workspace_id(self):
        portals = self.client.get("/teams/").get("portals") or []
        if not portals:
            raise LookupError_("No workspaces found on this account.")
        return portals[0]["zsoid"]

    def scope(self, project=None, sprint=None, need_sprint=True):
        """Apply saved defaults and return ``(team, project, sprint)``."""
        project, sprint = self.config.resolve(project, sprint, need_sprint)
        return self.team, project, sprint

    def project_path(self, project, suffix=""):
        return f"/team/{self.team}/projects/{project}/{suffix}".rstrip("/") + "/"

    def sprint_path(self, project, sprint, suffix=""):
        base = f"/team/{self.team}/projects/{project}/sprints/{sprint}/{suffix}"
        return base.rstrip("/") + "/"

    def item_path(self, project, sprint, item_id, suffix=""):
        base = (f"/team/{self.team}/projects/{project}/sprints/{sprint}"
                f"/item/{item_id}/{suffix}")
        return base.rstrip("/") + "/"
