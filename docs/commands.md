# Command reference

Every command accepts `--json`. Every write accepts `--dry-run`.

All ids below are fabricated. Yours will be 19-digit numbers from
`zsp projects` and `zsp sprints`.

> **`--project` and `--sprint` take ids, not names.** Unlike `--assignee`,
> `--status`, `--type` and `--priority`, which accept human names, these two
> currently require the numeric id. Run [`zsp use`](#zsp-use) once and you
> can omit them entirely.

**Contents** —
[login](#zsp-login) ·
[logout](#zsp-logout) ·
[use](#zsp-use) ·
[config](#zsp-config) ·
[teams](#zsp-teams) ·
[projects](#zsp-projects) ·
[sprints](#zsp-sprints) ·
[statuses](#zsp-statuses) ·
[items](#zsp-items) ·
[item](#zsp-item) ·
[standup](#zsp-standup) ·
[comments](#zsp-comments) ·
[create](#zsp-create) ·
[update](#zsp-update) ·
[log](#zsp-log) ·
[comment](#zsp-comment) ·
[uncomment](#zsp-uncomment) ·
[attach](#zsp-attach) ·
[detach](#zsp-detach) ·
[rm](#zsp-rm)

---

## Session

### `zsp login`

Interactive. Prompts for credentials, then opens a browser for consent.

```console
$ zsp login
Client ID: 1000.ABCD1234EFGH5678IJKL
Client Secret: ••••••••••••••••••••
Data center [in/com/eu/com.au/jp] (default: in): in
Opening browser for login...
https://accounts.zoho.in/oauth/v2/auth?scope=ZohoSprints.teams.READ%2C...
Logged in. Try: zsp projects
```

Setup walkthrough: [authentication.md](authentication.md).

### `zsp logout`

Deletes `~/.config/zsp/config.json`. Does not revoke the OAuth client
itself — do that in the API console.

```console
$ zsp logout
Logged out.
```

```console
$ zsp logout          # when there was nothing to remove
Not logged in.
```

### `zsp use`

Saves a default project, and optionally a sprint, so other commands need no
ids.

```console
$ zsp use 20000000000000002 30000000000000003
Default project: 20000000000000002
Default sprint:  30000000000000003
```

Project only — useful when you mostly work across sprints:

```console
$ zsp use 20000000000000002
Default project: 20000000000000002
```

Afterwards:

```console
$ zsp items           # no --project or --sprint needed
```

### `zsp config`

Shows the active configuration. Secrets are masked, so this is safe to
paste into a bug report.

```console
$ zsp config
client_id: 1000.ABCD1234EFGH5678IJKL
client_secret: ***redacted***
refresh_token: ***redacted***
dc: in
access_token: ***redacted***
access_token_expiry: 1785600000
team_id: 10000000000000001
default_project: 20000000000000002
default_sprint: 30000000000000003
```

---

## Reading

### `zsp teams`

Workspaces on the account. The first is used automatically unless
`team_id` is set in the config.

```console
$ zsp teams
ID                 NAME
10000000000000001  acme
```

```console
$ zsp teams --json
[
  {
    "id": "10000000000000001",
    "name": "acme"
  }
]
```

### `zsp projects`

```console
$ zsp projects
ID                 NAME           START                     END                       STATUS
20000000000000002  Apollo         2026-01-01T00:00:00.000Z  2026-06-30T00:00:00.000Z  1
20000000000000007  Internal Bugs                                                      1
```

`status` is a raw numeric code — Zoho exposes no label for it. Blank dates
mean the project has none set.

```bash
# Just the ids and names
zsp projects --json | jq -r '.[] | "\(.id)  \(.name)"'
```

### `zsp sprints`

```console
$ zsp sprints --project 20000000000000002
ID                 NAME      START                     END                       DURATION
30000000000000003  Sprint 1  2026-01-01T00:00:00.000Z  2026-01-14T00:00:00.000Z  10d
30000000000000008  Sprint 2  2026-01-15T00:00:00.000Z  2026-01-28T00:00:00.000Z  10d
```

With a default project saved:

```console
$ zsp sprints
```

> Dates are UTC. A portal set to IST stores local midnight as `18:30Z` the
> previous day, so a sprint starting 1 January reads `2025-12-31T18:30Z`.
> The web UI shows it correctly.

### `zsp statuses`

What `--status` will accept for a project — the full configured workflow,
including columns with nothing in them.

```console
$ zsp statuses --project 20000000000000002
ID                 NAME         KIND
70000000000000007  To do        open
70000000000000008  In progress  in progress
70000000000000010  InReview     in progress
70000000000000011  INQA         in progress
70000000000000009  Done         closed
```

Reading statuses off the items in a sprint is not equivalent: an empty
board column has no items, so it would be missed entirely.

`--type` and `--priority` values are not listed by a command, but an
unknown value reports the valid ones:

```console
$ zsp create --title x --type Epic
error: Unknown item type 'Epic'. Valid: Bug, Story, Task
```

### `zsp items`

```console
$ zsp items --project 20000000000000002 --sprint 30000000000000003
ID                 TITLE                             STATUS       ASSIGNEE                 POINTS
40000000000000004  Fix login redirect loop           In progress  Ada Lovelace             5
40000000000000009  Cache title-pair scores in Redis  Done         Ada Lovelace             3
40000000000000012  Migrate parser to RabbitMQ        To do        Ada Lovelace,Grace Hop…  8
```

Only your own items:

```console
$ zsp items --mine ada
ID                 TITLE                             STATUS       ASSIGNEE      POINTS
40000000000000004  Fix login redirect loop           In progress  Ada Lovelace  5
40000000000000009  Cache title-pair scores in Redis  Done         Ada Lovelace  3
```

`--mine` matches a case-insensitive substring of the display name and
filters **server-side**, so it sees every page, not just the first.

```bash
# Everything not finished
zsp items --json | jq -r '.[] | select(.status != "Done") | .title'

# Point total for the sprint
zsp items --json | jq '[.[].points] | add'
```

### `zsp item`

Full detail for one item — the raw Zoho payload, so `--json` is usually
what you want.

```console
$ zsp item 40000000000000004 --project 20000000000000002 --sprint 30000000000000003
item_prop: {'itemName': 0, 'itemNo': 2, 'createdBy': 3, ...}
itemIds: ['40000000000000004']
userDisplayName: {'50000000000000005': 'Ada Lovelace'}
itemJObj: {'40000000000000004': ['Fix login redirect loop', ...]}
status: success
```

```bash
# Pull one field out
zsp item 40000000000000004 --json | jq '.itemJObj[][0]'
```

### `zsp standup`

Time logged in the window. Defaults to the last day.

```console
$ zsp standup --days 7
ID                 DATE                      ITEM                     OWNER         HOURS  NOTES
11000000000000001  2026-01-05T00:00:00.000Z  Fix login redirect loop  Ada Lovelace  8.0    traced the redirect
11000000000000004  2026-01-06T00:00:00.000Z  Cache title-pair scores  Ada Lovelace  6.5    moved cache to Redis
```

Notes are HTML-stripped and truncated to 80 characters; `--json` has the
full text.

```bash
# Hours this week
zsp standup --days 7 --json | jq '[.[].hours] | add'

# Group by day
zsp standup --days 30 --json | jq -r 'group_by(.date[:10])[] | "\(.[0].date[:10])  \([.[].hours] | add)h"'
```

An empty result is normal if nothing was logged in the window — widen it
with `--days`.

### `zsp comments`

```console
$ zsp comments 40000000000000004
ID                 AUTHOR        CREATED                   TEXT
60000000000000006  Ada Lovelace  2026-01-06T00:00:00.000Z  Looks good to me
60000000000000011  Grace Hopper  2026-01-06T09:15:00.000Z  Deployed to staging
```

Note the ids — you need one to delete a comment with
[`zsp uncomment`](#zsp-uncomment).

---

## Writing

These hit the API immediately. Add `--dry-run` to any of them to see the
request without sending it.

### `zsp create`

| Flag | Meaning |
|---|---|
| `--title` | **Required** |
| `--type` | `Story`, `Task`, `Bug` … (project-specific) |
| `--parent ITEM_ID` | Create as a subtask of that item |
| `--desc` | Description |
| `--assignee NAME` | Matched against project members |
| `--priority` | `None`, `Low`, `Medium`, `High` |
| `--points N` | Story points |
| `--start`, `--end` | `YYYY-MM-DD` |

Minimal:

```console
$ zsp create --title "Rework title scoring" --type Story
Created: success
```

Everything:

```console
$ zsp create \
    --title "Rework title scoring" \
    --type Story \
    --desc "Replace classify-then-map with direct recruiter-perspective scoring" \
    --assignee ada \
    --priority High \
    --points 8 \
    --start 2026-01-05 \
    --end 2026-01-09
Created: success
```

A subtask under that story:

```console
$ zsp create --title "Extract attribute stage" --type Task \
             --parent 40000000000000004 --assignee ada --points 3
Created: success
```

Preview before committing to it:

```console
$ zsp create --title "Rework title scoring" --type Story --dry-run
DRY RUN — would send:
  POST https://sprintsapi.zoho.in/zsapi/team/10000000000000001/projects/20000000000000002/sprints/30000000000000003/item/?name=Rework+title+scoring&projitemtypeid=80000000000000001
    name = Rework title scoring
    projitemtypeid = 80000000000000001
```

New items land in the project's default status, usually `To do`.

```bash
# Capture the new item's id
NEW=$(zsp create --title "Spike: caching" --type Task --json | jq -r '.addedItemId')
```

### `zsp update`

Same field flags as `create` (minus `--parent` and `--type`), plus
`--status`. At least one is required.

```console
$ zsp update 40000000000000004 --status "In progress"
Updated 40000000000000004: success
```

```console
$ zsp update 40000000000000004 --assignee grace --points 13 --end 2026-01-12
Updated 40000000000000004: success
```

Clear a field by passing an empty string:

```console
$ zsp update 40000000000000004 --desc ""
Updated 40000000000000004: success
```

Unknown names fail before anything is sent, listing the valid options:

```console
$ zsp update 40000000000000004 --status Finished
error: Unknown status 'Finished'. Valid: Done, In progress, To do
```

```bash
# Close everything of yours that is in review
zsp items --mine ada --json \
  | jq -r '.[] | select(.status == "In review") | .id' \
  | xargs -I{} zsp update {} --status Done
```

Build pipelines like that with `--dry-run` on the end first.

### `zsp log`

| Flag | Meaning |
|---|---|
| `--duration` | **Required**, `H:MM` — e.g. `8:00` |
| `--date` | `YYYY-MM-DD`, defaults to today |
| `--notes` | Free text |
| `--user NAME` | Log for someone else, if your role permits |
| `--billable` | Mark billable (default: not billable) |

```console
$ zsp log 40000000000000004 --duration 3:30
Logged on 40000000000000004: success
```

```console
$ zsp log 40000000000000004 --duration 8:00 --date 2026-01-05 \
          --notes "traced the redirect loop" --billable
Logged on 40000000000000004: success
```

```console
$ zsp log 40000000000000004 --duration 1:00 --dry-run
DRY RUN — would send:
  POST https://sprintsapi.zoho.in/zsapi/team/.../item/40000000000000004/timesheet/?action=additemlog&duration=1%3A00&isbillable=0
    action = additemlog
    duration = 1:00
    isbillable = 0
```

### `zsp comment`

```console
$ zsp comment 40000000000000004 --text "Deployed to staging, watching error rates"
Commented on 40000000000000004: success
```

Comments, descriptions and log notes are HTML fields in Zoho, so line
breaks and `-`/`1.` lists are converted for you — write them as you would
in a terminal and they render properly:

```console
$ zsp comment 40000000000000004 --text "Done so far:
- Seniority ladder with an exact penalty per step
- Dropped the M_seniority multiplier

Still verifying against real JDs."
Commented on 40000000000000004: success
```

Renders as a paragraph, a real bulleted list, then a closing paragraph.
Pass HTML yourself and it is sent untouched.

Multi-line works — quote it:

```console
$ zsp comment 40000000000000004 --text "Root cause: the session cookie was
being set before the redirect. Fixed in #421."
Commented on 40000000000000004: success
```

### `zsp uncomment`

Deletes a comment. Get the note id from [`zsp comments`](#zsp-comments).

```console
$ zsp comments 40000000000000004
ID                 AUTHOR        CREATED                   TEXT
60000000000000006  Ada Lovelace  2026-01-06T00:00:00.000Z  Looks good to me

$ zsp uncomment 40000000000000004 60000000000000006
Deleted comment 60000000000000006: success
```

Comments are usually deletable even in projects where items are not.

### `zsp attach`

Upload files to an item. The only multipart endpoint in the API.

```console
$ zsp attach 40000000000000004 screenshot.png
Attached 1 file(s) to 40000000000000004: success
```

Several at once:

```console
$ zsp attach 40000000000000004 error.log trace.txt design.pdf
Attached 3 file(s) to 40000000000000004: success
```

Files are validated locally first — missing path, directory, empty file or
over the 100 MB cap fail before anything is sent, so a typo in a
multi-file upload does not leave a half-finished mess.

Attach at creation time with `--attach`:

```console
$ zsp create --title "Login fails on Safari" --type Bug \
             --attach har-file.har screenshot.png
Created: success
```

The item is created first, then the files uploaded — the API cannot do
both in one request, since the item id does not exist yet. The files are
still validated up front, so a bad path will not leave an empty item
behind.

### `zsp detach`

Remove an attachment by its `docResourceId`.

```console
$ zsp detach 40000000000000004 99000000000000001
Detached 99000000000000001: success
```

> **Finding the id is awkward.** Zoho documents no endpoint that lists an
> item's attachments, so there is no `zsp attachments` command. Get the
> `docResourceId` from the attachment's URL in the web UI, or from the
> response when you uploaded it.

### `zsp rm`

Deletes an item.

```console
$ zsp rm 40000000000000004
Deleted 40000000000000004: success
```

```console
$ zsp rm 40000000000000004 --dry-run
DRY RUN — would send:
  DELETE https://sprintsapi.zoho.in/zsapi/team/.../item/40000000000000004/
```

> **Frequently refused by role, not scope.** Even with `items.DELETE`
> granted, Zoho enforces your project role, and it commonly blocks deleting
> items *you created yourself*:
>
> ```console
> $ zsp rm 40000000000000004
> error: API error 401: {"code":7401.14,"message":"Doesn't have permission in item."}
> ```
>
> No scope change fixes that — see
> [troubleshooting.md](troubleshooting.md#permissions). Worth testing before
> you generate data somewhere you cannot clean up.

---

## Recipes

```bash
# Daily standup, ready to paste
zsp standup --days 1 --json \
  | jq -r '.[] | "- \(.item) (\(.hours)h): \(.notes)"'

# Sprint burndown input
zsp items --json | jq -r 'group_by(.status)[] | "\(.[0].status): \([.[].points] | add)"'

# Log the same hours across several items
for id in 4000...004 4000...009; do
  zsp log "$id" --duration 2:00 --notes "pairing session"
done

# Create a story with its subtasks
STORY=$(zsp create --title "Auth rework" --type Story --json | jq -r .addedItemId)
for t in "Design" "Backend" "Frontend" "QA"; do
  zsp create --title "$t" --type Task --parent "$STORY" --assignee ada
done
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Unclassified error |
| 2 | Usage error — bad or missing arguments |
| 3 | Authentication — not logged in, or token rejected |
| 4 | API error — Zoho returned a failure |
| 5 | Lookup failed — a name could not be resolved |
| 130 | Interrupted |

```bash
if ! zsp items --json > items.json 2>err.log; then
  case $? in
    3) echo "run: zsp login" ;;
    4) echo "Zoho error:"; cat err.log ;;
  esac
fi
```
