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

    # Written for someone — or something — reading `zsp --help` cold, with
    # no other context. It answers the questions that otherwise turn into
    # failed commands: which arguments are ids, which are names, where the
    # values come from, and what is safe to run.
    EPILOG = """
getting started
  zsp login                       authenticate (one time)
  zsp projects                    list projects, note the id you want
  zsp sprints --project <id>      list sprints in it
  zsp use <project-id> <sprint-id>
                                  save both as defaults; after this every
                                  command below works with no ids

ids vs names
  --project and --sprint take numeric ids only.
  --status, --assignee, --type and --priority take human names, matched
  case-insensitively. An unknown name fails and lists the valid options.

discovering valid values
  zsp statuses                    values for --status, for this project
  zsp projects / zsp sprints      ids for --project / --sprint
  --type and --priority have no listing command; pass a wrong value and
  the error names the valid ones.

before you change anything
  Every write is immediate. Add --dry-run to any of them to print the
  exact request and send nothing.

for scripts and agents
  Every command accepts --json.
  Exit codes: 0 ok, 2 usage, 3 auth, 4 API error, 5 name not found.

not supported
  Listing an item's attachments, and attaching to a comment specifically:
  Zoho documents no endpoint for either. zsp attach works at item level.

docs      https://github.com/sudoSharun/zsp
API notes https://github.com/sudoSharun/zsp/blob/main/docs/api-notes.md
"""

    ABORTED = 130

    def __init__(self, application=None):
        self.application = application or Application()

    def build_parser(self):
        parser = argparse.ArgumentParser(
            prog=self.PROGRAM,
            description=self.DESCRIPTION,
            epilog=self.EPILOG,
            formatter_class=argparse.RawDescriptionHelpFormatter,
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
