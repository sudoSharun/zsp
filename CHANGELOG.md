# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-08-01

First release.

### Added

- Read commands: `teams`, `projects`, `sprints`, `items`, `item`,
  `standup`, `comments`
- Write commands: `create` (items and subtasks), `update`, `log`,
  `comment`, `uncomment`, `rm`
- Session commands: `login`, `logout`, `use`, `config`
- `--dry-run` on every write, which prints the request and sends nothing
- `--json` on every command
- Human-readable names instead of ids for status, assignee, item type and
  priority, with the valid options listed on failure
- Access-token caching, so repeated commands do not trip Zoho's
  refresh-grant rate limit
- Distribution via PyPI, Homebrew, Chocolatey, winget, npm, Docker and a
  standalone binary
- [`docs/api-notes.md`](docs/api-notes.md) documenting Zoho Sprints API
  behaviour that is absent from, or contradicted by, the official
  collection

### Notes

Several behaviours documented here were found the hard way and are
corrected against Zoho's published collection:

- Comments live at `/sprints/{s}/item/{i}/notes/`, not the documented
  `/modules/{id}/entity/{item}/notes/`
- The sprints endpoint returns nothing without `type=[1,2,3,4]`
- Pagination is by record offset, and an empty trailing page omits the
  schema map
- `isbillable` is mandatory on time logs
- Dates must be `yyyy-MM-dd'T'HH:mm:ssZZ`

[Unreleased]: https://github.com/sudoSharun/zsp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sudoSharun/zsp/releases/tag/v0.1.0
