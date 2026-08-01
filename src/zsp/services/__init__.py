"""Resource services.

One class per Zoho resource, each taking its collaborators by constructor
injection so any of them can be built against a stub client in tests.
"""

from .base import BaseService
from .comment import CommentService
from .item import ItemService
from .lookup import LookupService
from .sprint import SprintService
from .timesheet import TimesheetService
from .workspace import ProjectService, WorkspaceService

__all__ = [
    "BaseService",
    "CommentService",
    "ItemService",
    "LookupService",
    "ProjectService",
    "SprintService",
    "TimesheetService",
    "WorkspaceService",
]
