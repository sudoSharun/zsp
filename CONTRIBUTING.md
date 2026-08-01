# Contributing

Thanks for taking a look. Bug reports, API corrections and pull requests
are all welcome.

## The most valuable contribution

[`docs/api-notes.md`](docs/api-notes.md) is the reason this project is
worth publishing. Zoho's own API collection is wrong in several places, and
every correction there was found by trial against a live workspace.

If you find another discrepancy — an endpoint that behaves differently, a
mandatory parameter that is undocumented, a response shape that changed —
please open an issue even if you do not want to write code. Include the
request you sent and the exact error you got back.

## Setup

```bash
git clone https://github.com/sudoSharun/zsp
cd zsp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Verify:

```bash
pytest
ruff check src tests
```

## Layout

```
src/zsp/
├── core/       config and errors      — depends on nothing else
├── api/        OAuth, HTTP, decoding  — knows Zoho, not sprints
├── services/   one class per resource — knows sprints, not the terminal
└── cli/        commands, rendering, wiring
```

Dependencies point downward only: `cli` → `services` → `api` → `core`.
Keeping that direction is what makes the services testable without a
terminal and the client reusable as a library.

## Tests

The suite never touches the network. `urlopen` is replaced by a recorder
that replays fixtures and captures the exact URLs produced, so most tests
assert on the request rather than mocking a whole client.

```python
def test_sends_the_mandatory_type_filter(self, services, opener):
    opener.payloads.append(SPRINTS_RESPONSE)
    services["sprints"].list(PROJECT)
    assert opener.query()["type"] == "[1,2,3,4]"
```

Coverage must stay at or above 90%; CI enforces it.

**Fixtures must never contain real data.** Every id, name and email in
`tests/conftest.py` is fabricated. If you add a fixture from a real
response, replace ids with the `10000000000000001` pattern and invent
names.

When you fix a bug, add the test that would have caught it. The existing
suite has several of these, each with a comment explaining the failure —
worth reading before adding a new one.

## Adding a command

1. Add the method to the relevant service in `src/zsp/services/`.
2. Add a `Command` subclass in `src/zsp/cli/commands/`.
3. Register it in `src/zsp/cli/commands/__init__.py`.
4. Test the service method and the command.
5. Document it in `docs/commands.md` and the README table.

Commands declare their own arguments and are dispatched from a registry, so
there is no central `if/elif` chain to edit.

## Writes and safety

Anything that mutates data must:

- route through `SprintsClient.post` / `.delete`, never a raw request
- accept `--dry-run`
- be covered by a test asserting that `--dry-run` performs **no** HTTP call

That guarantee is the reason someone can trust this tool against a live
project. Please do not weaken it.

When testing against a real workspace, use a project you can clean up.
Zoho's role permissions frequently prevent deleting items even when you
created them.

## Style

- `ruff` settings live in `pyproject.toml`; CI runs `ruff check`
- Comments should explain *why*, especially where behaviour looks odd —
  most oddities here are Zoho's, and the comment is what stops someone
  "fixing" it later
- Keep the package dependency-free. That is a feature, and any proposal to
  add a runtime dependency needs a strong argument

## Pull requests

- One logical change per PR
- Tests included
- `pytest` and `ruff check src tests` pass
- Update `CHANGELOG.md` under `## [Unreleased]`

## Reporting bugs

Include `zsp --version`, the command (ids redacted), the full error, and
your data centre.

**Never paste `~/.config/zsp/config.json` or any token.** `zsp config`
masks secrets and is safe to share.

## Security

Do not open a public issue for a vulnerability. Email
`ksharan2001@gmail.com` instead.

## Licence

Contributions are accepted under the MIT licence.
