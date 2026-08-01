"""Argument parsing and the process exit code.

This is the only module that prints errors or decides exit codes;
everything beneath it raises :class:`~zsp.core.errors.ZspError`.
"""

import argparse
import sys

from .. import __version__
from ..core import ZspError
from .application import Application
from .commands import COMMANDS
from .rendering import Renderer


class CommandLineInterface:
    """Builds the parser and runs the selected command."""

    PROGRAM = "zsp"
    DESCRIPTION = "Zoho Sprints from the command line."
    EPILOG = "Docs: https://github.com/sudoSharun/zsp"

    ABORTED = 130

    def __init__(self, application=None):
        self.application = application or Application()

    def build_parser(self):
        parser = argparse.ArgumentParser(
            prog=self.PROGRAM,
            description=self.DESCRIPTION,
            epilog=self.EPILOG,
        )
        parser.add_argument("--version", action="version",
                            version=f"{self.PROGRAM} {__version__}")
        subparsers = parser.add_subparsers(dest="command", required=True)
        for command_class in COMMANDS:
            command_class.register(subparsers)
        return parser

    def run(self, argv=None):
        """Parse ``argv`` and execute. Returns a process exit code."""
        args = self.build_parser().parse_args(argv)
        self.application.renderer = Renderer(as_json=getattr(args, "json", False))

        command = args.command_class(self.application)
        try:
            command.execute(args)
            return 0
        except ZspError as error:
            print(f"error: {error}", file=sys.stderr)
            return error.exit_code
        except KeyboardInterrupt:
            print("aborted", file=sys.stderr)
            return self.ABORTED


def main(argv=None):
    """Console-script entry point (``zsp``)."""
    return CommandLineInterface().run(argv)
