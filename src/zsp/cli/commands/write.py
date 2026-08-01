"""Commands that change data.

All of these accept ``--dry-run``, which prints the request and sends
nothing.
"""

from .base import Command


class CreateCommand(Command):
    name = "create"
    help = "create an item or subtask"
    scoped = True
    writes = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--title", required=True)
        parser.add_argument("--parent", metavar="ITEM_ID",
                            help="create as a subtask of this item")
        parser.add_argument("--desc")
        parser.add_argument("--assignee", metavar="NAME")
        parser.add_argument("--type", dest="item_type", metavar="TYPE",
                            help="Story, Task, Bug ... (project-specific)")
        parser.add_argument("--priority", help="None, Low, Medium, High")
        parser.add_argument("--points", type=int)
        parser.add_argument("--start", metavar="YYYY-MM-DD")
        parser.add_argument("--end", metavar="YYYY-MM-DD")

    def execute(self, args):
        response = self.app.items.create(
            args.title, args.project, args.sprint, args.parent, args.desc,
            args.assignee, args.item_type, args.priority, args.points,
            args.start, args.end, args.dry_run)
        self.report(response, "Created")


class UpdateCommand(Command):
    name = "update"
    help = "update an item"
    scoped = True
    writes = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")
        parser.add_argument("--title")
        parser.add_argument("--desc", help='pass "" to clear')
        parser.add_argument("--status", help="To do, In progress, Done ...")
        parser.add_argument("--assignee", metavar="NAME")
        parser.add_argument("--points", type=int)
        parser.add_argument("--start", metavar="YYYY-MM-DD")
        parser.add_argument("--end", metavar="YYYY-MM-DD")

    def execute(self, args):
        response = self.app.items.update(
            args.item_id, args.project, args.sprint, args.title, args.desc,
            args.status, args.assignee, args.points, args.start, args.end,
            args.dry_run)
        self.report(response, f"Updated {args.item_id}")


class LogCommand(Command):
    name = "log"
    help = "log time on an item"
    scoped = True
    writes = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")
        parser.add_argument("--duration", required=True, metavar="H:MM",
                            help='e.g. "8:00"')
        parser.add_argument("--date", metavar="YYYY-MM-DD")
        parser.add_argument("--notes")
        parser.add_argument("--user", metavar="NAME")
        parser.add_argument("--billable", action="store_true",
                            help="mark the entry billable (default: not billable)")

    def execute(self, args):
        response = self.app.timesheets.log(
            args.item_id, args.duration, args.project, args.sprint,
            args.date, args.notes, args.user, args.billable, args.dry_run)
        self.report(response, f"Logged on {args.item_id}")


class CommentCommand(Command):
    name = "comment"
    help = "comment on an item"
    scoped = True
    writes = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")
        parser.add_argument("--text", required=True)

    def execute(self, args):
        response = self.app.comments.add(
            args.item_id, args.text, args.project, args.sprint, args.dry_run)
        self.report(response, f"Commented on {args.item_id}")


class UncommentCommand(Command):
    name = "uncomment"
    help = "delete a comment"
    scoped = True
    writes = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")
        parser.add_argument("note_id")

    def execute(self, args):
        response = self.app.comments.delete(
            args.item_id, args.note_id, args.project, args.sprint, args.dry_run)
        self.report(response, f"Deleted comment {args.note_id}")


class RemoveCommand(Command):
    name = "rm"
    help = "delete an item"
    scoped = True
    writes = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")

    def execute(self, args):
        response = self.app.items.delete(
            args.item_id, args.project, args.sprint, args.dry_run)
        self.report(response, f"Deleted {args.item_id}")
