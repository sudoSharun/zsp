# Command reference

Every command accepts `--json`. Every write accepts `--dry-run`.

Ids are 19-digit numbers. Run `zsp use` once and you can omit
`--project`/`--sprint` everywhere after that.

---

## Session

### `zsp login`

Interactive: prompts for client ID, client secret and data centre, then
opens a browser for consent. See [authentication.md](authentication.md).

### `zsp logout`

Deletes `~/.config/zsp/config.json`. Does not revoke the client itself.

### `zsp use PROJECT [SPRINT]`

Saves defaults.

```console
$ zsp use 20000000000000002 30000000000000003
Default project: 20000000000000002
Default sprint:  30000000000000003
```

### `zsp config`

Prints the active configuration with secrets masked.

```console
$ zsp config
client_id: 1000.ABCD1234
client_secret: ***redacted***
refresh_token: ***redacted***
dc: in
default_project: 20000000000000002
```

---

## Reading

### `zsp teams`

```console
$ zsp teams
ID                 NAME
10000000000000001  acme
```

The first workspace is used automatically; set `team_id` in the config file
to pin a different one.

### `zsp projects`

```console
$ zsp projects
ID                 NAME    START                     END                       STATUS
20000000000000002  Apollo  2026-01-01T00:00:00.000Z  2026-06-30T00:00:00.000Z  1
```

`status` is a raw numeric code — Zoho does not expose labels for it.

### `zsp sprints [--project ID]`

```console
$ zsp sprints
ID                 NAME      START                     END                       DURATION
30000000000000003  Sprint 1  2026-01-01T00:00:00.000Z  2026-01-14T00:00:00.000Z  10d
```

Dates are UTC. A portal in IST stores midnight local as `18:30Z` the
previous day, so a sprint starting "1 January" reads as `2025-12-31T18:30Z`.

### `zsp items [--project ID] [--sprint ID] [--mine NAME]`

```console
$ zsp items --mine ada
ID                 TITLE                    STATUS       ASSIGNEE      POINTS
40000000000000004  Fix login redirect loop  In progress  Ada Lovelace  5
```

`--mine` matches a case-insensitive substring of the display name and
filters server-side, so it sees every page — not just the first.

Items with several assignees show them comma-separated.

### `zsp item ID [--project ID] [--sprint ID]`

Raw detail for one item. Most useful with `--json`.

### `zsp standup [--project ID] [--days N]`

Time logs in the window, newest data as recorded by Zoho.

```console
$ zsp standup --days 7
ID                 DATE                      ITEM       OWNER         HOURS  NOTES
11000000000000001  2026-01-05T00:00:00.000Z  Fix login  Ada Lovelace  8.0    traced the redirect
```

HTML is stripped from notes and truncated to 80 characters. Use `--json`
for the full text.

### `zsp comments ITEM_ID`

```console
$ zsp comments 40000000000000004
ID                 AUTHOR        CREATED                   TEXT
60000000000000006  Ada Lovelace  2026-01-06T00:00:00.000Z  Looks good to me
```

---

## Writing

All of these hit the API immediately. Add `--dry-run` to see the request
first.

### `zsp create --title TEXT [...]`

| Flag | Meaning |
|---|---|
| `--title` | Required |
| `--parent ITEM_ID` | Create as a subtask of that item |
| `--desc` | Description |
| `--assignee NAME` | Resolved against project members |
| `--type TYPE` | `Story`, `Task`, `Bug` … (project-specific) |
| `--priority` | `None`, `Low`, `Medium`, `High` |
| `--points N` | Story points |
| `--start`, `--end` | `YYYY-MM-DD` |

```console
$ zsp create --title "Cache title-pair scores" --type Task \
             --assignee ada --priority High --points 3 \
             --start 2026-01-05 --end 2026-01-09
Created: success
```

New items start in the project's default status, usually `To do`.

### `zsp update ITEM_ID [...]`

Same field flags as `create`, minus `--parent`/`--type`, plus `--status`.
At least one is required.

```console
$ zsp update 40000000000000004 --status "In progress"
Updated 40000000000000004: success
```

Clear a description by passing an empty string:

```bash
zsp update 40000000000000004 --desc ""
```

### `zsp log ITEM_ID --duration H:MM [...]`

| Flag | Meaning |
|---|---|
| `--duration` | Required, e.g. `8:00` |
| `--date` | `YYYY-MM-DD`, defaults to today |
| `--notes` | Free text |
| `--user NAME` | Log on someone else's behalf, if permitted |
| `--billable` | Mark billable (default: not) |

```console
$ zsp log 40000000000000004 --duration 3:30 --date 2026-01-05 --notes "traced it"
Logged on 40000000000000004: success
```

### `zsp comment ITEM_ID --text TEXT`

```console
$ zsp comment 40000000000000004 --text "Deployed to staging"
Commented on 40000000000000004: success
```

### `zsp uncomment ITEM_ID NOTE_ID`

Get the note id from `zsp comments`. Comments are deletable even where
items are not.

### `zsp rm ITEM_ID`

Deletes an item. Frequently refused by project role rather than scope — see
[troubleshooting.md](troubleshooting.md).

---

## Scripting

```bash
# Total hours this week
zsp standup --days 7 --json | jq '[.[].hours] | add'

# Everything not yet done
zsp items --json | jq -r '.[] | select(.status != "Done") | "\(.id)\t\(.title)"'

# Close every item you own that is in review
zsp items --mine ada --json \
  | jq -r '.[] | select(.status == "In review") | .id' \
  | xargs -I{} zsp update {} --status Done
```

Build pipelines like the last one with `--dry-run` appended first.

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
