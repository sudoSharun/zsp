# Troubleshooting

Errors are printed as `error: ...` on stderr, with an exit code that
distinguishes the category (see [commands.md](commands.md#exit-codes)).

---

## Authentication

### `Not logged in. Run: zsp login`

No config file. If you expected one, check `ZSP_CONFIG_DIR` is not
pointing somewhere else.

### `Session expired or revoked`

The refresh token no longer works — usually revoked in the API console, or
the client was deleted. Run `zsp login` again.

### `Access Denied — You have made too many requests continuously`

Zoho rate-limits the **token refresh** grant far more tightly than the API
itself. `zsp` caches access tokens for this reason, so hitting it usually
means many separate processes each forced a refresh.

Wait a few minutes. Retrying immediately extends the lockout.

### `Invalid OAuth Scope — Scope does not exist`

A requested scope is not real. Only the scopes listed in
[authentication.md](authentication.md#scopes-requested) exist; notably
there is **no** `ZohoSprints.notes.*`.

### Browser opens, terminal never returns

The callback never reached `http://localhost:8723/callback`. Check the
redirect URI in the API console matches exactly, and that port 8723 is
free. Ctrl-C is safe — config is only written on success.

---

## Permissions

### `7601 Invalid oauthscope` vs `7401.14 Doesn't have permission in item`

These look similar and are completely different problems.

| Error | Cause | Fix |
|---|---|---|
| `401 7601 Invalid oauthscope` | Your **token** lacks the scope | `zsp login` again |
| `401 7401.14 Doesn't have permission in item` | Your **project role** forbids it | Ask an admin to change your role |

The second cannot be fixed from the CLI. It commonly blocks deleting items
*you created yourself* — worth testing before generating test data in a
shared project, because you may not be able to clean up.

Comments are governed separately and are usually deletable even when items
are not.

---

## Arguments and lookups

### `No project given. Pass --project, or save a default with: zsp use ...`

Run `zsp use <project> [sprint]` once.

### `Unknown status 'X'. Valid: Done, In progress, To do`

Statuses are per-project and configurable. The message lists what this
project actually has. Matching is case-insensitive.

### `No project user matching 'x'. Known: ...`

`--assignee`/`--user` match a substring of the display name, not the email
or username.

### `Nothing to update`

`zsp update` needs at least one field flag.

---

## Data that looks wrong

### Dates are a day earlier than I set

Expected. Zoho interprets dates in the **portal's** timezone and returns
UTC. An IST portal stores 5 January as `2026-01-04T18:30:00Z`. The web UI
shows it correctly.

### `zsp sprints` returns nothing

If you are calling the API yourself, this is the `type=[1,2,3,4]` filter —
without it the endpoint returns an empty list for every project. `zsp`
always sends it, so an empty result here means the project genuinely has no
sprints. Check the backlog in the UI.

### An item I can see in the UI is missing

Most likely paging. `zsp` follows pagination automatically, but stops at 20
pages as a safety limit. For very large sprints, narrow with `--mine`.

### `--mine` returns nothing but I have work in that sprint

There is a real difference between being an item's **owner** and having
**logged time** against it. `--mine` filters by owner. Use `zsp standup` to
see what you have logged.

### Hours look wrong

Zoho stores log time in milliseconds; `zsp` converts to hours rounded to
two decimals. `--json` gives you the same rounded value — use the Zoho UI
if you need exact raw figures.

---

## Output

### `--json` output has extra text in it

Status lines are suppressed in JSON mode. If you still see stray output,
it is on **stderr** — redirect it:

```bash
zsp items --json 2>/dev/null | jq .
```

### Table columns are misaligned in my terminal

Column widths assume a monospace font and no wrapping. Pipe through `less
-S`, or use `--json`.

---

## Still stuck

Include in a bug report:

- `zsp --version`
- the exact command, with ids replaced by placeholders
- the full error output
- your data centre (`in`, `com`, `eu`, …)

**Never paste `~/.config/zsp/config.json`, or the output of anything that
might contain a token.** `zsp config` masks secrets and is safe to share.

Open an issue: <https://github.com/sudoSharun/zsp/issues>
