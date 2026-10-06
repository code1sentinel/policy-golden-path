# Retro: Authoring app shell (UI overhaul)

| Field | Value |
| --- | --- |
| Date | 2026-10-06 |
| Feature / PRD | [docs/prds/ui-overhaul.md](../prds/ui-overhaul.md) |
| Slices / PRs | PR A (this branch); stacked risk slice follows |

## What we shipped

A Linear-inspired authoring shell for `codify-web` and Pages: sidebar,
breadcrumb, writing column, properties/review panel, Catalog table, and
an export dialog. Happy path is unchanged: paste/open → draft → accept →
export. Light/dark, system fonts, CSP, and OSCAL output did not change.

## What went well

The Mobbin list was in the request, so the PRD could cite screens before
code. Keeping existing element ids (`#demo`, `#work`, `.ctl`, `#ai-open`)
limited e2e churn.

## What was painful

Export moved from a split button to a dialog, so several tests that
clicked `[data-export=oscal]` in the header had to be rewritten together.
`data-view` had to stay unique (`work` vs `workspace`) because Playwright
strict mode fails on two matches.

## Lessons to fold into the templates

| Lesson | Template to change |
| --- | --- |
| When replacing chrome, keep the behavioural ids the e2e suite already uses, and treat export/entry points as a contract. | Slice template: call out “preserve e2e ids unless the test plan updates them.” |

## Follow-ups

- Fill the Risks destination (stacked PR: risk → control statements).
- Consider splitting `app.js` only with a new ADR (Pages copies named files).
