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
    TeamsCommand,
)
from .session import ConfigCommand, LoginCommand, LogoutCommand, UseCommand
from .write import (
    CommentCommand,
    CreateCommand,
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
    StandupCommand,
    CommentsCommand,
    # writes
    CreateCommand,
    UpdateCommand,
    LogCommand,
    CommentCommand,
    UncommentCommand,
    RemoveCommand,
)

__all__ = ["COMMANDS", "Command"]
