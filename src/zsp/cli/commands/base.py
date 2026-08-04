"""The command abstraction.

Each command is a class that declares its own arguments and knows how to
run itself. Adding a command means writing a class and listing it in
:data:`zsp.cli.commands.COMMANDS` — never editing a dispatch chain.
"""

import argparse


class Command:
    """Base class: name, help text, arguments and an ``execute`` body."""

    #: Subcommand name as typed on the command line.
    name = ""
    #: One-line help shown in ``zsp --help``.
    help = ""
    #: Longer explanation shown at the top of ``zsp <command> --help``.
    description = ""
    #: Worked examples shown at the bottom of ``zsp <command> --help``.
    #: Agents and newcomers read these before the flag list, so they carry
    #: the things flags cannot say: which values are ids, which are names,
    #: and which command discovers them.
    examples = ""
    #: Adds ``--project`` (and ``--sprint``) plus ``--json``.
    scoped = False
    #: Whether ``--sprint`` is included when :attr:`scoped`.
    needs_sprint = True
    #: Adds ``--dry-run``.
    writes = False
    #: Adds ``--json`` even when not :attr:`scoped`.
    renders = False

    def __init__(self, application):
        self.app = application

    # -- argument declaration --------------------------------------------

    @classmethod
    def register(cls, subparsers):
        """Attach this command's parser to ``subparsers``."""
        parser = subparsers.add_parser(
            cls.name,
            help=cls.help,
            description=cls.description or cls.help,
            epilog=cls.examples,
            # Raw, so example blocks keep their line breaks and indentation.
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        if cls.scoped:
            parser.add_argument("--project",
                                help="project id (default: from `zsp use`)")
            if cls.needs_sprint:
                parser.add_argument("--sprint",
                                    help="sprint id (default: from `zsp use`)")

        cls.add_arguments(parser)

        if cls.scoped or cls.renders:
            parser.add_argument("--json", action="store_true",
                                help="machine-readable output")
        if cls.writes:
            parser.add_argument("--dry-run", action="store_true",
                                help="print the request without sending it")

        parser.set_defaults(command_class=cls)
        return parser

    @classmethod
    def add_arguments(cls, parser):
        """Hook for command-specific flags."""

    # -- execution --------------------------------------------------------

    def execute(self, args):
        raise NotImplementedError

    # -- helpers ----------------------------------------------------------

    @property
    def renderer(self):
        return self.app.renderer

    def show(self, service, rows):
        """Render rows using the service's declared columns."""
        return self.renderer.table(rows, list(service.COLUMNS))

    def report(self, response, label):
        """Print a write result.

        ``None`` means it was a dry run, which has already printed itself.
        """
        if response is None:
            return
        if self.renderer.as_json:
            self.renderer.detail(response)
        else:
            self.renderer.message(f"{label}: {response.get('status', response)}")
