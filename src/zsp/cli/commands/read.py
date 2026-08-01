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


class ItemsCommand(Command):
    name = "items"
    help = "list items in a sprint"
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
    scoped = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")

    def execute(self, args):
        service = self.app.comments
        self.show(service, service.list(args.item_id, args.project, args.sprint))
