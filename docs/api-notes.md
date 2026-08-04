# Zoho Sprints API — field notes

Corrections and undocumented behaviour found while building this client,
verified against a live workspace. Zoho's published Postman collection is
wrong or silent on all of it.

Useful whatever language you are integrating in.

- Base URL: `https://sprintsapi.zoho.<dc>/zsapi`
- Auth header: `Authorization: Zoho-oauthtoken <token>`
- Rate limit: **30 requests/minute** on the data API
- Writes take **query parameters**, never a JSON body

---

## 1. Responses are positional arrays, not objects

Nothing returns named fields. A list response pairs a `*JObj` map of
`id -> array` with a `*_prop` map of `fieldName -> array index`:

```json
{
  "itemJObj":  { "40000000000000004": ["Fix login", "117", 5] },
  "item_prop": { "itemName": 0, "itemNo": 1, "points": 2 },
  "userDisplayName": { "50000000000000005": "Ada Lovelace" }
}
```

**Read the `*_prop` map at runtime.** Indices differ between endpoints, so
hardcoding positions breaks as soon as you touch a second resource.

The `*JObj` key varies by resource: `projectJObj`, `sprintJObj`, `itemJObj`,
`logJObj`, `notesJObj`, `userJObj`, `statusJObj`, `projItemTypeJObj`,
`projPriorityJObj`.

## 2. `/teams/` is the only plural path

```
GET /zsapi/teams/                     ← workspace list
GET /zsapi/team/{teamId}/projects/    ← everything else is singular
```

Workspaces come back under `portals`, and the id field is `zsoid` — not
`id`, not `teamId`.

## 3. Sprints return nothing without a `type` filter

```
GET /team/{t}/projects/{p}/sprints/?action=data&index=1&range=50
→ {"sprintIds": [], "status": "success"}      # every project, always
```

The `type` parameter is effectively mandatory:

```
GET .../sprints/?action=data&index=1&range=50&type=[1,2,3,4]
```

Valid codes are **1–4 only**. `0` and `5` fail with
`Incorrect parameter or parameter value or parameter missing`, and a bare
integer (`type=2`) fails with `Given JSON is invalid` — it must be a JSON
array.

## 4. Pagination is by record offset

`index` is a **record number**, not a page number. With `range=100`, the
second page starts at `index=101`. Responses expose `nextIndex`, plus
`next` on most endpoints and `hasNext` on the timesheet — handle both.

**An empty trailing page omits the `*_prop` map entirely.** If you merge
pages and take metadata from the last response, every decoded field
silently becomes `null`. Always keep the first page's schema.

## 5. Filtering by assignee must be server-side

```
GET .../item/?action=data&index=1&range=100&subitem=true
    &filter={"I-owner":["<userId>"],"queryType":1,"jsontmpl":"item_default"}
```

Filtering client-side only inspects the page you fetched, which quietly
hides assignments on later pages.

## 6. Comments are not where the docs say

Documented — and broken:

```
POST /team/{t}/projects/{p}/modules/{moduleId}/entity/{itemId}/notes/
     ?addnotes=addnotes&name=<text>
→ 401 Invalid oauthscope     (for every moduleId tried, 1-10)
```

What actually works:

```
POST   /team/{t}/projects/{p}/sprints/{s}/item/{i}/notes/?name=<text>
GET    /team/{t}/projects/{p}/sprints/{s}/item/{i}/notes/?index=1&range=50
DELETE /team/{t}/projects/{p}/sprints/{s}/item/{i}/notes/{noteId}/
```

Notes:

- `addnotes` is rejected outright: `7602 Extra parameter found in URL`.
  Send `name` alone.
- **No `ZohoSprints.notes.*` scope exists.** Requesting one fails at the
  consent screen with *"Invalid OAuth Scope — Scope does not exist"*.
  Comments ride on `items.*`.
- The **read** response keys rows under `notesJObj`; the **write** response
  uses `itemnotesJObj` for the same data. Reading the wrong key makes a
  successful post look like a failure — and invites duplicate posts.
- Comments are deletable even in projects where the role forbids deleting
  the items themselves.

## 7. Comments and descriptions are HTML fields

Item descriptions, comments and time-log notes all store **HTML**, not
plain text. Send raw newlines and Zoho renders the whole thing as one
run-on paragraph — line breaks and `-` bullets disappear, because that is
what HTML does with whitespace.

Convert before sending:

```
Done so far:            →  <div>Done so far:</div>
- ladder added             <ul><li>ladder added</li>
- multiplier dropped           <li>multiplier dropped</li></ul>
```

Reading back, strip the tags — but turn block-level tags into whitespace
first, or `<div>one</div><div>two</div>` becomes `onetwo`.

Zoho's own UI writes fragments like
`<div><span style="...">text</span><br/></div>`, so a plain `<div>`/`<ul>`
subset renders correctly.

## 8. Attachments are the one multipart endpoint

Everything else is query parameters with an empty body. File upload is not:

```
POST /team/{t}/projects/{p}/sprints/{s}/item/{i}/attachments/
     Content-Type: multipart/form-data; boundary=...
       action=attachment      (text, mandatory)
       uploadfile=<file>      (file, mandatory)
```

Note the path is **plural** for adding and **singular** for removing:

```
DELETE /team/{t}/projects/{p}/sprints/{s}/item/{i}/attachment/?docResourceId=<id>
```

There is **no documented endpoint that lists an item's attachments**, so
obtaining a `docResourceId` in order to delete one means reading it from
the web UI or from the upload response. The item payload exposes only an
`isDocsAdded` boolean.

Creating an item with attachments takes two requests — the id does not
exist until the item is created.

Comments carry a `hasAttach` field, but no endpoint is documented for
attaching to a comment specifically.

## 9. Dates must carry a time and offset

```
?startdate=2026-01-05
→ 500 Only yyyy-MM-dd'T'HH:mm:ssZZ will be allowed
```

Send `2026-01-05T00:00:00+0000`. Zoho then interprets it in the **portal's**
timezone regardless of the offset you sent, so an IST portal stores
`2026-01-04T18:30:00Z` for 5 January. Reading dates back as UTC makes them
look a day early; that is correct behaviour, not drift.

## 10. `isbillable` is mandatory on time logs

```
POST .../item/{i}/timesheet/?action=additemlog&duration=8:00
→ 500 Parameter missing in Request   (allowedRegex "0|1", paramName "isbillable")
```

`duration` accepts `H:MM`. Deleting logs needs
`ZohoSprints.timesheets.DELETE`, which is separate from `.CREATE`:

```
DELETE /team/{t}/projects/{p}/timesheet/?action=deletelogs&logidarr=["<id>",...]
```

## 11. Scopes vs roles are different failures

| Response | Meaning | Fix |
|---|---|---|
| `401 7601 Invalid oauthscope` | Token lacks the scope | Re-login with it added |
| `401 7401.14 Doesn't have permission in item` | Your **project role** forbids it | Nothing API-side; the admin must change your role |

Item deletion commonly fails the second way *even for items you created*.
Check before generating test data somewhere you cannot clean up.

Error payloads sometimes leak useful internals — a failed item delete
returns `"module": 3`, Zoho's internal module id for items.

## 12. Token refresh is rate-limited separately

The `refresh_token` grant is throttled far more aggressively than the
30/min data API. Refreshing once per process trips
`Access Denied — You have made too many requests continuously` within a
handful of commands, and repeated retries extend the lockout.

Cache the access token (they last ~1 hour) and reuse it across invocations.

## Working scope string

```
ZohoSprints.teams.READ,
ZohoSprints.projects.READ,
ZohoSprints.sprints.READ,
ZohoSprints.items.READ, ZohoSprints.items.CREATE,
ZohoSprints.items.UPDATE, ZohoSprints.items.DELETE,
ZohoSprints.timesheets.READ, ZohoSprints.timesheets.CREATE,
ZohoSprints.timesheets.DELETE,
ZohoSprints.teamusers.READ, ZohoSprints.projectusers.READ
```

`ZohoSprints.notes.*` does not exist. Some endpoints
(`/settings/customization/modules/`) need scopes not in Zoho's published
list at all and remain unreachable.

## Endpoints used by this client

| Purpose | Method | Path |
|---|---|---|
| Workspaces | GET | `/teams/` |
| Projects | GET | `/team/{t}/projects/?action=data` |
| Backlog id | GET | `/team/{t}/projects/{p}/?action=getbacklog` |
| Sprints | GET | `/team/{t}/projects/{p}/sprints/?action=data&type=[1,2,3,4]` |
| Items | GET | `/team/{t}/projects/{p}/sprints/{s}/item/?action=data&subitem=true` |
| Item detail | GET | `/team/{t}/projects/{p}/sprints/{s}/item/{i}/?action=details` |
| Statuses | GET | `/team/{t}/projects/{p}/itemstatus/?action=data` |
| Item types | GET | `/team/{t}/projects/{p}/itemtype/?action=data` |
| Priorities | GET | `/team/{t}/projects/{p}/priority/?action=data` |
| Project users | GET | `/team/{t}/projects/{p}/users/?action=data` |
| Time logs | GET | `/team/{t}/projects/{p}/timesheet/?action=data` |
| Create item | POST | `/team/{t}/projects/{p}/sprints/{s}/item/` |
| Create subtask | POST | `/team/{t}/projects/{p}/sprints/{s}/item/{i}/subitem/` |
| Update item | POST | `/team/{t}/projects/{p}/sprints/{s}/item/{i}/` |
| Delete item | DELETE | `/team/{t}/projects/{p}/sprints/{s}/item/{i}/` |
| Log time | POST | `/team/{t}/projects/{p}/sprints/{s}/item/{i}/timesheet/?action=additemlog` |
| Delete logs | DELETE | `/team/{t}/projects/{p}/timesheet/?action=deletelogs` |
| Attach file | POST | `/team/{t}/projects/{p}/sprints/{s}/item/{i}/attachments/` (multipart) |
| Remove attachment | DELETE | `/team/{t}/projects/{p}/sprints/{s}/item/{i}/attachment/?docResourceId=` |
| Comments | GET/POST | `/team/{t}/projects/{p}/sprints/{s}/item/{i}/notes/` |
| Delete comment | DELETE | `/team/{t}/projects/{p}/sprints/{s}/item/{i}/notes/{n}/` |

---

Found something else, or something changed? Please open an issue — this
page is the point of the project.
