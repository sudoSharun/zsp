"""Commands that manage credentials and stored defaults."""

from ...core import DATA_CENTRES
from .base import Command


class LoginCommand(Command):
    name = "login"
    help = "authenticate with Zoho"
    description = "Authenticate with Zoho and store a refresh token locally."
    examples = """
Prompts for a client id and secret from api-console.zoho.<dc>, then opens
a browser for consent. The redirect URI registered there must be exactly:

  http://localhost:8723/callback

Setup guide:
https://github.com/sudoSharun/zsp/blob/main/docs/authentication.md
"""

    def execute(self, args):
        client_id = input("Client ID: ").strip()
        client_secret = input("Client Secret: ").strip()
        centres = "/".join(DATA_CENTRES)
        dc = input(f"Data center [{centres}] (default: in): ").strip() or "in"

        self.app.authenticator.login(client_id, client_secret, dc)
        self.renderer.message("Logged in. Try: zsp projects")


class LogoutCommand(Command):
    name = "logout"
    help = "delete stored credentials"

    def execute(self, args):
        removed = self.app.store.delete()
        self.renderer.message("Logged out." if removed else "Not logged in.")


class UseCommand(Command):
    name = "use"
    help = "save a default project (and sprint)"
    description = ("Save a default project and sprint so other commands "
                   "need no ids.")
    examples = """
examples:
  zsp use 20000000000000002 30000000000000003
  zsp use 20000000000000002              # project only

Both arguments are numeric ids, from `zsp projects` and `zsp sprints`.
Names are not accepted here.
"""

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("project", help="project id to use by default")
        parser.add_argument("sprint", nargs="?", help="sprint id to use by default")

    def execute(self, args):
        saved = self.app.store.set_defaults(args.project, args.sprint)
        # Keep the live config in step with disk, so anything holding this
        # Application already sees the new defaults.
        self.app.config.default_project = saved.default_project
        self.app.config.default_sprint = saved.default_sprint

        self.renderer.message(f"Default project: {args.project}")
        if args.sprint:
            self.renderer.message(f"Default sprint:  {args.sprint}")


class ConfigCommand(Command):
    name = "config"
    help = "show current config (secrets redacted)"
    renders = True

    def execute(self, args):
        self.renderer.detail(self.app.config.redacted())
