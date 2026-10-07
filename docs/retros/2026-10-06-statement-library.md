# Retro: Statement library

| Field | Value |
| --- | --- |
| Date | 2026-10-06 |
| Feature / PRD | [docs/prds/statement-library.md](../prds/statement-library.md) |
| Slices / PRs | This feature PR |

## What we shipped

A device-wide Statement library. Accept upserts the control statement into
`codify:statements` (deduped by normalized text). Library view: search,
remove, local CSV/JSON export, empty state. Drafting offers **From library**
(Use / Add) beside risk templates and the editor. The OSCAL catalog stays
the per-project save.

## What went well

- ADR 0009 named the separate key and schema before the UI landed, so the
  catalog and `codify:project` were not overloaded.
- Reusing the existing Accept path meant Use still goes through
  `assess_control_statement`.
- HoneyBook / HubSpot / PandaDoc / Slite / Vanta / Dovetail Mobbin refs
  mapped cleanly onto the #24 shell.

## What was painful

- Accept is now async (library upsert). e2e tests have to wait for
  `codify:statements`, not only the Accepted chip.
- Sidebar destination counts (`data-view`) are brittle; a new nav item
  touches several existing tests.

## Lessons to fold into the templates

| Lesson | Template to change |
| --- | --- |
| Device-wide stores need a key named in an ADR, separate from `codify:project`. | ADR template / this retro |
| Tests that count nav destinations should list names, not only a number. | Follow-up; not changed in this slice |

## Follow-ups

- CLI-side library file is out of this decision.
- Cloud / team libraries would need a new ADR that supersedes 0003 and 0009.
