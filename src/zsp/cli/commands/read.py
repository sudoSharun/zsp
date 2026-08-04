"""Commands that only read."""

from .base import Command


class TeamsCommand(Command):
    name = "teams"
    help = "list workspaces"
    renders = True

    def execute(self, args):
        service = self.app.workspaces
        self.show(service, service.list())


class ProjectsCommand(Command):
    name = "projects"
    help = "list projects"
    renders = True

    def execute(self, args):
        service = self.app.projects
        self.show(service, service.list())


class SprintsCommand(Command):
    name = "sprints"
    help = "list sprints in a project"
    scoped = True
    needs_sprint = False

    def execute(self, args):
        service = self.app.sprints
        self.show(service, service.list(args.project))


class StatusesCommand(Command):
    """What `--status` will accept for a project."""

    name = "statuses"
    help = "list the statuses configured on a project"
    description = ("Every status configured on the project, including board "
                   "columns that currently hold no items.")
    examples = """
examples:
  zsp statuses
  zsp statuses --project 20000000000000002

Use the NAME column with `zsp update <item> --status "<name>"`.
Do not infer statuses from `zsp items` — that only shows the ones in use.
"""
    scoped = True
    needs_sprint = False

    def execute(self, args):
        service = self.app.lookups
        self.show(service, service.status_rows(args.project))


class ItemsCommand(Command):
    name = "items"
    help = "list items in a sprint"
    description = "Work items in a sprint, optionally filtered to one assignee."
    examples = """
examples:
  zsp items
  zsp items --mine ada                  # substring of a display name
  zsp items --json | jq -r '.[] | select(.status != "Done") | .title'

--mine filters server-side, so it sees every page.
Owner is not the same as who logged time — use `zsp standup` for that.
"""
    scoped = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--mine", metavar="NAME",
                            help="only items assigned to this user, e.g. --mine ada")

    def execute(self, args):
        service = self.app.items
        self.show(service, service.list(args.project, args.sprint, args.mine))


class ItemCommand(Command):
    name = "item"
    help = "show one item"
    scoped = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")

    def execute(self, args):
        self.renderer.detail(
            self.app.items.get(args.item_id, args.project, args.sprint))


class StandupCommand(Command):
    name = "standup"
    help = "recent time logs"
    description = "Time logged against items, newest window first."
    examples = """
examples:
  zsp standup                 # last 24 hours
  zsp standup --days 7
  zsp standup --days 7 --json | jq '[.[].hours] | add'

An empty result usually means nothing was logged in the window; widen it
with --days before concluding anything is wrong.
"""
    scoped = True
    needs_sprint = False

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--days", type=int, default=1,
                            help="lookback window in days (default: 1)")

    def execute(self, args):
        service = self.app.timesheets
        self.show(service, service.recent(args.project, args.days))


class CommentsCommand(Command):
    name = "comments"
    help = "list comments on an item"
    description = "Comments on an item, oldest first."
    examples = """
examples:
  zsp comments 40000000000000004

The ID column is the note id needed by `zsp uncomment`.
"""
    scoped = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")

    def execute(self, args):
        service = self.app.comments
        self.show(service, service.list(args.item_id, args.project, args.sprint))
