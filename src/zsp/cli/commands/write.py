"""Commands that change data.

All of these accept ``--dry-run``, which prints the request and sends
nothing.
"""

from .base import Command


class CreateCommand(Command):
    name = "create"
    help = "create an item or subtask"
    description = "Create a work item, or a subtask of one with --parent."
    examples = """
examples:
  zsp create --title "Fix login redirect" --type Bug
  zsp create --title "Auth rework" --type Story --assignee ada \\
             --priority High --points 8 --start 2026-01-05 --end 2026-01-09
  zsp create --title "Backend" --type Task --parent 40000000000000004
  zsp create --title "Crash on upload" --type Bug --attach trace.log shot.png

--type and --priority are names, not ids; a wrong value lists the valid
ones. New items land in the project's default status, usually "To do".

Add --dry-run to see the request without creating anything.
"""
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
        parser.add_argument("--attach", nargs="+", metavar="FILE", dest="files",
                            help="upload files to the item once created")

    def execute(self, args):
        response = self.app.items.create(
            args.title, args.project, args.sprint, args.parent, args.desc,
            args.assignee, args.item_type, args.priority, args.points,
            args.start, args.end, args.files, args.dry_run)
        self.report(response, "Created")


class UpdateCommand(Command):
    name = "update"
    help = "update an item"
    description = "Change fields on an existing item. At least one is required."
    examples = """
examples:
  zsp update 40000000000000004 --status "In progress"
  zsp update 40000000000000004 --assignee grace --points 13
  zsp update 40000000000000004 --desc ""          # clears the description

Run `zsp statuses` for the values --status accepts in this project.
--desc accepts plain text; newlines and "-" bullets are converted to the
HTML Zoho stores, so lists render properly.
"""
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
    description = "Record time against an item."
    examples = """
examples:
  zsp log 40000000000000004 --duration 3:30
  zsp log 40000000000000004 --duration 8:00 --date 2026-01-05 \\
          --notes "traced the redirect" --billable

--duration is H:MM. Entries are non-billable unless --billable is given.
"""
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
    description = "Add a comment to an item."
    examples = """
examples:
  zsp comment 40000000000000004 --text "Deployed to staging"

  zsp comment 40000000000000004 --text "Done so far:
  - ladder added
  - multiplier dropped

  Still verifying."

Plain text is converted to the HTML Zoho stores, so line breaks and
"-"/"1." lists render as real paragraphs and lists.

Comments cannot carry attachments of their own — attach to the item with
`zsp attach` instead.
"""
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


class AttachCommand(Command):
    name = "attach"
    help = "upload files to an item"
    description = "Upload one or more files to an item."
    examples = """
examples:
  zsp attach 40000000000000004 screenshot.png
  zsp attach 40000000000000004 error.log trace.txt design.pdf
  zsp create --title "Crash" --type Bug --attach trace.log

Attachments are item-level; Zoho has no comment-level upload endpoint.
Files are checked before anything is sent, including under --dry-run.

There is no command to list an item's attachments — Zoho documents no
endpoint for it, which is also why `zsp detach` needs the id by hand.
"""
    scoped = True
    writes = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")
        parser.add_argument("files", nargs="+", metavar="FILE",
                            help="one or more paths to upload")

    def execute(self, args):
        response = self.app.items.attach(
            args.item_id, args.files, args.project, args.sprint, args.dry_run)
        self.report(response, f"Attached {len(args.files)} file(s) to {args.item_id}")


class DetachCommand(Command):
    name = "detach"
    help = "remove an attachment from an item"
    description = "Remove an attachment, identified by its docResourceId."
    examples = """
examples:
  zsp detach 40000000000000004 99000000000000001

The docResourceId is not discoverable through this CLI; take it from the
attachment's URL in the web UI, or from the response when it was uploaded.
"""
    scoped = True
    writes = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")
        parser.add_argument("resource_id", metavar="DOC_RESOURCE_ID",
                            help="docResourceId of the attachment")

    def execute(self, args):
        response = self.app.items.detach(
            args.item_id, args.resource_id, args.project, args.sprint, args.dry_run)
        self.report(response, f"Detached {args.resource_id}")


class RemoveCommand(Command):
    name = "rm"
    help = "delete an item"
    description = "Delete an item. Frequently refused by project role."
    examples = """
examples:
  zsp rm 40000000000000004 --dry-run
  zsp rm 40000000000000004

A failure reading "7401.14 Doesn't have permission in item" is a project
role restriction, not a scope problem — re-authenticating will not help,
and it applies even to items you created. Delete in the web UI instead.
"""
    scoped = True
    writes = True

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("item_id")

    def execute(self, args):
        response = self.app.items.delete(
            args.item_id, args.project, args.sprint, args.dry_run)
        self.report(response, f"Deleted {args.item_id}")
