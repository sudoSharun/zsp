# Authentication

`zsp` uses OAuth 2.0 against Zoho Accounts. You register an OAuth client
once, log in once, and the refresh token is stored locally from then on.

## 1. Pick your data centre

Zoho runs regional deployments and they do **not** share accounts. Look at
the URL when you are signed into Sprints:

| Sprints URL | Data centre | API console |
|---|---|---|
| `sprints.zoho.in` | `in` | `api-console.zoho.in` |
| `sprints.zoho.com` | `com` | `api-console.zoho.com` |
| `sprints.zoho.eu` | `eu` | `api-console.zoho.eu` |
| `sprints.zoho.com.au` | `com.au` | `api-console.zoho.com.au` |
| `sprints.zoho.jp` | `jp` | `api-console.zoho.jp` |

Using the wrong one gives `invalid_client` at login.

## 2. Register an OAuth client

1. Open `api-console.zoho.<dc>` and sign in with the account you use for
   Sprints.
2. **Add Client → Server-based Applications.**
3. Fill in:
   - **Client Name** — anything, e.g. `zsp-cli`
   - **Homepage URL** — anything, e.g. `http://localhost`
   - **Authorized Redirect URI** — exactly:
     ```
     http://localhost:8723/callback
     ```
4. **Create.** Copy the **Client ID** and **Client Secret**.

The redirect URI must match character for character; `zsp login` runs a
one-shot local server on port 8723 to catch the callback.

> **Corporate accounts.** Some administrators restrict client creation. If
> **Add Client** is unavailable, ask an admin — there is no way around it
> from the CLI.

## 3. Log in

```bash
zsp login
```

You will be prompted for the client ID, the secret, and your data centre. A
browser opens for consent; approve it and the terminal confirms.

## Scopes requested

| Scope | Enables |
|---|---|
| `ZohoSprints.teams.READ` | `zsp teams` |
| `ZohoSprints.projects.READ` | `zsp projects` |
| `ZohoSprints.sprints.READ` | `zsp sprints` |
| `ZohoSprints.items.READ` | `zsp items`, `zsp item` |
| `ZohoSprints.items.CREATE` | `zsp create`, `zsp comment` |
| `ZohoSprints.items.UPDATE` | `zsp update` |
| `ZohoSprints.items.DELETE` | `zsp rm`, `zsp uncomment` |
| `ZohoSprints.timesheets.READ` | `zsp standup` |
| `ZohoSprints.timesheets.CREATE` | `zsp log` |
| `ZohoSprints.timesheets.DELETE` | deleting time logs |
| `ZohoSprints.teamusers.READ`, `ZohoSprints.projectusers.READ` | resolving `--assignee` names |

Comments have **no scope of their own** — they ride on `items.*`.
`ZohoSprints.notes.*` does not exist and breaks login if requested.

## Where credentials live

`~/.config/zsp/config.json`, created with mode `0600`:

```json
{
  "client_id": "1000.XXXX",
  "client_secret": "...",
  "refresh_token": "1000....",
  "dc": "in",
  "access_token": "1000....",
  "access_token_expiry": 1785600000,
  "default_project": "20000000000000002",
  "default_sprint": "30000000000000003"
}
```

Inspect it safely — secrets are masked:

```bash
zsp config
```

Override the location with `ZSP_CONFIG_DIR`, useful for keeping work and
personal portals apart:

```bash
ZSP_CONFIG_DIR=~/.config/zsp-work zsp items
```

Never commit this file. It is not repo-relative, and `config.json` is in
`.gitignore` regardless.

## Token lifetime

Access tokens last about an hour and are cached on disk. The refresh token
does not expire until revoked.

Caching matters: Zoho rate-limits the refresh grant far more tightly than
the API itself, and refreshing on every command trips
`You have made too many requests continuously` within a few invocations.

## Revoking

Remove local credentials:

```bash
zsp logout
```

To revoke access entirely, delete the client in `api-console.zoho.<dc>`.
Do that too if a secret has ever been pasted somewhere shared.

## Troubleshooting

**"Invalid OAuth Scope — Scope does not exist"** — a requested scope is not
real. If you edited the scope list, revert it.

**`invalid_client`** — wrong data centre, or the client was deleted.

**`invalid_redirect_uri`** — the console entry does not match
`http://localhost:8723/callback` exactly.

**Browser opens but the terminal hangs** — the callback never arrived.
Ctrl-C and retry; existing credentials are untouched because config is only
written on success. If port 8723 is occupied, free it first.

**`Session expired or revoked`** — the refresh token is dead. Run
`zsp login` again.

**`Access Denied — too many requests`** — refresh-grant rate limit. Wait a
few minutes; retrying immediately extends the lockout.
