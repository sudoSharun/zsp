# zsp — Zoho Sprints CLI

[![CI](https://github.com/sudoSharun/zsp/actions/workflows/ci.yml/badge.svg)](https://github.com/sudoSharun/zsp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/zsp.svg)](https://pypi.org/project/zsp/)
[![Python](https://img.shields.io/pypi/pyversions/zsp.svg)](https://pypi.org/project/zsp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Drive [Zoho Sprints](https://www.zoho.com/sprints/) from your terminal — list
sprints, create and update work items, log time and post comments without
opening the web UI.

**Zero runtime dependencies.** Everything is Python standard library.

```console
$ zsp items --mine ada
ID                 TITLE                             STATUS       ASSIGNEE      POINTS
40000000000000004  Fix login redirect loop           In progress  Ada Lovelace  5
40000000000000009  Cache title-pair scores in Redis  Done         Ada Lovelace  3

$ zsp log 40000000000000004 --duration 3:30 --notes "traced the redirect"
Logged on 40000000000000004: success
```

---

## Why this exists

Zoho Sprints has a REST API but no official CLI, and its published API
collection is **wrong in several places** — comments are documented at an
endpoint that returns 401 for every input, and the parameter it tells you to
send is rejected outright.

Everything in [`docs/api-notes.md`](docs/api-notes.md) was found by trial
against a live workspace and is documented nowhere else. If you are writing
your own Zoho Sprints integration in any language, read that file first — it
will save you a day.

## Install

Requires Python 3.9+. No other dependencies.

```bash
pipx install git+https://github.com/sudoSharun/zsp
```

[pipx](https://pipx.pypa.io/) keeps it in its own environment, out of the
way of your projects. Plain pip works too:

```bash
pip install git+https://github.com/sudoSharun/zsp
```

> **Not yet on PyPI.** `pip install zsp` will not work until the first
> release is published — use the commands above meanwhile. Homebrew,
> Chocolatey, winget, npm and the prebuilt binaries described in
> [`docs/installation.md`](docs/installation.md) also become available with
> that release.

Upgrade:

```bash
pipx upgrade zsp        # or: pipx reinstall zsp
```

## Quickstart

**1. Register an OAuth client.** Go to `api-console.zoho.<dc>` (`.in`, `.com`,
`.eu`, `.com.au` or `.jp` — match the domain you use for Sprints), create a
**Server-based Application**, and set the redirect URI to exactly:

```
http://localhost:8723/callback
```

Note the Client ID and Client Secret. Full walkthrough:
[`docs/authentication.md`](docs/authentication.md).

**2. Log in.**

```bash
zsp login
```

Paste the client ID and secret; a browser opens for consent. Credentials are
stored in `~/.config/zsp/config.json` with `0600` permissions.

**3. Find your project and sprint, then save them as defaults.**

```bash
zsp projects
zsp sprints --project 20000000000000002
zsp use 20000000000000002 30000000000000003
```

Now every command runs without ids:

```bash
zsp items
zsp standup --days 7
```

## Commands

| Command | What it does |
|---|---|
| `zsp login` / `logout` | Authenticate; delete stored credentials |
| `zsp use PROJECT [SPRINT]` | Save defaults so other commands need no ids |
| `zsp config` | Show current config, secrets redacted |
| `zsp teams` | List workspaces |
| `zsp projects` | List projects |
| `zsp sprints` | List sprints in a project |
| `zsp items [--mine NAME]` | List items in a sprint |
| `zsp item ID` | Show one item in full |
| `zsp standup [--days N]` | Recent time logs |
| `zsp comments ID` | List comments on an item |
| `zsp create --title T` | Create an item, or a subtask with `--parent` |
| `zsp update ID` | Change status, assignee, dates, points, text |
| `zsp log ID --duration H:MM` | Log time |
| `zsp comment ID --text T` | Add a comment |
| `zsp uncomment ID NOTE_ID` | Delete a comment |
| `zsp rm ID` | Delete an item |

Every command takes `--json`. Every write takes `--dry-run`.

Full reference with examples: [`docs/commands.md`](docs/commands.md).

## Safety

Writes are real and immediate. Two things protect you:

**`--dry-run`** prints the exact request and sends nothing:

```console
$ zsp create --title "Spike: caching" --type Task --dry-run
DRY RUN — would send:
  POST https://sprintsapi.zoho.in/zsapi/team/.../item/?name=Spike%3A+caching&projitemtypeid=...
    name = Spike: caching
    projitemtypeid = 80000000000000002
```

**Names, not ids.** `--status Done`, `--assignee ada`, `--type Bug` and
`--priority High` are resolved against the project, and an unknown name fails
with the valid options rather than sending a wrong id.

> **Deleting items needs more than scope.** Even with `items.DELETE` granted,
> Zoho enforces your *project role*. If it refuses, you get
> `7401.14 Doesn't have permission in item`, and no scope change will fix it —
> you will have to delete in the web UI. Worth checking before you create test
> data in a shared project.

## Automation

`--json` makes every command scriptable:

```bash
# Hours logged this week
zsp standup --days 7 --json | jq '[.[].hours] | add'

# Item titles still open
zsp items --json | jq -r '.[] | select(.status != "Done") | .title'
```

This works well as a tool for coding agents — point one at `zsp --help` and it
can read and update your sprint directly.

## Development

```bash
git clone https://github.com/sudoSharun/zsp
cd zsp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest              # test suite, no network access
ruff check src tests
```

The test suite never touches the network — `urlopen` is replaced by a recorder
that replays fixtures and asserts the exact URLs produced. All fixture ids and
names are fabricated.

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Layout

```
src/zsp/
├── core/       config, errors        — depends on nothing
├── api/        auth, HTTP, decoding  — knows Zoho, not sprints
├── services/   one class per resource
└── cli/        commands, rendering, wiring
```

## Licence

MIT — see [LICENSE](LICENSE).

Not affiliated with or endorsed by Zoho Corporation.
