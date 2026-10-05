# Retro: personal chrome and quieter workspace

| Field | Value |
| --- | --- |
| Date | 2026-10-05 |
| Feature / PRD | [personal-start-chrome.md](../prds/personal-start-chrome.md), [workspace-guide-declutter.md](../prds/workspace-guide-declutter.md) |
| Slices / PRs | This change |

## What we shipped

Removed the start-page footer that attributed Codify to the GRC Engineering
Club Singapore and showed the version. Tightened Workspace and Guide:
statement as hero, Risk in extras, Guide as a single column. MIT stays in
LICENSE and README.

## What went well

The club copy lived in one footer. Mobbin web screens (Linear, Grok,
Mintlify, LangChain) mapped cleanly onto the existing list | editor split
without a new layout.

## What was painful

Granola was not authenticated, so meeting context was not available. No
GitHub issue could be opened from this environment.

## Lessons to fold into the templates

| Lesson | Template to change |
| --- | --- |
| Text-only chrome removal does not need Mobbin links | Already allowed by the personal-chrome PRD |
| Density work still needs Mobbin before CSS | Already in AGENTS.md |

## Follow-ups

- Origin history in README is unchanged on purpose.
