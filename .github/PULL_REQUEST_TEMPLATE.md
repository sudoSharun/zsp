## What this changes

## Why

<!-- If this works around Zoho API behaviour, describe the behaviour —
     that context belongs in a code comment too, so nobody "fixes" it
     later. -->

## Checklist

- [ ] `pytest` passes (coverage stays at or above 90%)
- [ ] `ruff check src tests` passes
- [ ] Tests added for the change; for a bug fix, a test that fails without it
- [ ] No real workspace data in fixtures — ids and names are fabricated
- [ ] Writes route through `SprintsClient.post`/`.delete` and honour `--dry-run`
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] Docs updated (`docs/commands.md`, README table, `docs/api-notes.md`)

## Tested against a real workspace?

<!-- Optional but helpful. Say which commands, and whether with --dry-run. -->
