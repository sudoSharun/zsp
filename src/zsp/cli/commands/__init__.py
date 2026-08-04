"""Command objects, grouped by what they touch.

The order of :data:`COMMANDS` is the order shown in ``zsp --help``.
"""

from .base import Command
from .read import (
    CommentsCommand,
    ItemCommand,
    ItemsCommand,
    ProjectsCommand,
    SprintsCommand,
    StandupCommand,
    StatusesCommand,
    TeamsCommand,
)
from .session import ConfigCommand, LoginCommand, LogoutCommand, UseCommand
from .write import (
    AttachCommand,
    CommentCommand,
    CreateCommand,
    DetachCommand,
    LogCommand,
    RemoveCommand,
    UncommentCommand,
    UpdateCommand,
)

COMMANDS = (
    # session
    LoginCommand,
    LogoutCommand,
    UseCommand,
    ConfigCommand,
    # reads
    TeamsCommand,
    ProjectsCommand,
    SprintsCommand,
    ItemsCommand,
    ItemCommand,
    StatusesCommand,
    StandupCommand,
    CommentsCommand,
    # writes
    CreateCommand,
    UpdateCommand,
    LogCommand,
    CommentCommand,
    UncommentCommand,
    AttachCommand,
    DetachCommand,
    RemoveCommand,
)

__all__ = ["COMMANDS", "Command"]
