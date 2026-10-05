# Retro: personal start chrome

| Field | Value |
| --- | --- |
| Date | 2026-10-05 |
| Feature / PRD | [docs/prds/personal-start-chrome.md](../prds/personal-start-chrome.md) |
| Slices / PRs | This change |

## What we shipped

Removed the start-page footer that attributed Codify to the GRC Engineering
Club Singapore and showed the version. MIT stays in LICENSE and README.

## What went well

The copy lived in one footer, one JS write, and unused `.foot` styles. No
OSCAL, privacy, or layout change.

## What was painful

Granola was not authenticated, so meeting context was not available. No
GitHub issue could be opened from this environment.

## Lessons to fold into the templates

| Lesson | Template to change |
| --- | --- |
| Text-only chrome removal does not need Mobbin links | Already allowed by this PRD; no template change |

## Follow-ups

- None for this slice. Origin history in README is unchanged on purpose.
