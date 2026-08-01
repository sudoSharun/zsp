"""Sprints."""

from .base import BaseService


class SprintService(BaseService):
    """Sprints within a project."""

    COLUMNS = ("id", "name", "start", "end", "duration")

    FIELDS = {
        "name": "sprintName",
        "start": "startDate",
        "end": "endDate",
        "duration": "duration",
    }

    #: Sprint state codes. Only 1-4 are valid — 0 and 5 are rejected with
    #: "Incorrect parameter or parameter value", and omitting the filter
    #: entirely makes the endpoint return an empty list for every project.
    ALL_STATES = "[1,2,3,4]"

    def list(self, project=None, limit=50):
        _, project, _ = self.scope(project, need_sprint=False)
        response = self.client.fetch(
            self.project_path(project, "sprints"),
            action="data", index=1, range=limit, type=self.ALL_STATES)
        return response.rows("sprintJObj", "sprint_prop", self.FIELDS)
