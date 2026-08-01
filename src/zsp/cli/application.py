"""Composition root.

:class:`Application` builds the object graph a command needs and hands
each service its collaborators explicitly, so any of them can be
constructed against a stub in tests.
"""

from ..api import Authenticator, SprintsClient
from ..core import ConfigStore
from ..services import (
    CommentService,
    ItemService,
    LookupService,
    ProjectService,
    SprintService,
    TimesheetService,
    WorkspaceService,
)
from .rendering import Renderer


class Application:
    """Lazily constructs config, client and services.

    Laziness matters: ``login`` runs before any credentials exist, and
    ``logout`` must work even when the config file is unreadable — neither
    can afford a config load at construction time.
    """

    def __init__(self, store=None, renderer=None, authenticator=None,
                 client=None, config=None):
        self.store = store or ConfigStore()
        self.renderer = renderer or Renderer()
        self._authenticator = authenticator
        self._client = client
        self._config = config
        self._services = {}

    # -- collaborators ----------------------------------------------------

    @property
    def authenticator(self):
        if self._authenticator is None:
            self._authenticator = Authenticator(self.store)
        return self._authenticator

    @property
    def config(self):
        if self._config is None:
            self._config = self.store.load()
        return self._config

    @property
    def client(self):
        if self._client is None:
            self._client = SprintsClient(self.config, self.authenticator)
        return self._client

    # -- services ---------------------------------------------------------

    def _service(self, key, factory):
        if key not in self._services:
            self._services[key] = factory()
        return self._services[key]

    @property
    def lookups(self):
        return self._service(
            "lookups", lambda: LookupService(self.client, self.config))

    @property
    def workspaces(self):
        return self._service(
            "workspaces", lambda: WorkspaceService(self.client, self.config))

    @property
    def projects(self):
        return self._service(
            "projects", lambda: ProjectService(self.client, self.config))

    @property
    def sprints(self):
        return self._service(
            "sprints", lambda: SprintService(self.client, self.config))

    @property
    def items(self):
        return self._service(
            "items", lambda: ItemService(self.client, self.config, self.lookups))

    @property
    def timesheets(self):
        return self._service(
            "timesheets",
            lambda: TimesheetService(self.client, self.config, self.lookups))

    @property
    def comments(self):
        return self._service(
            "comments", lambda: CommentService(self.client, self.config))
