# Retro: Welcome splash

| Field | Value |
| --- | --- |
| Date | 2026-10-07 |
| Feature / PRD | [docs/prds/welcome-splash.md](../prds/welcome-splash.md) |
| Slices / PRs | This feature PR |

## What we shipped

A first-visit splash in the main column: Codify mark, “Welcome to Codify”,
one on-device lede, one **Get started**. Dismiss is `codify:splash-seen`.
A saved `codify:project` skips the splash so resume is instant. After
dismiss, the existing paste start (Codify primary, Try an example) is
unchanged.

## What went well

- Linear’s Mobbin splash gave a clear hierarchy without inventing a layout.
- Reusing `codify:*` localStorage avoided a new ADR.
- Seeding `codify:splash-seen` in the shared e2e `page` fixture kept the
  start-hero, empty-state, and theme tests intact.

## What was painful

- First paint runs before `app.js`. The seen/resume check had to live in
  `theme.js` (already in `<head>`) because inline scripts are banned.
- Playwright’s `#start:not([hidden])` waits on the attribute, not computed
  style, so theme helpers that open their own context also needed the seed.

## Lessons to fold into the templates

| Lesson | Template to change |
| --- | --- |
| First-paint UI that depends on `localStorage` belongs in the early same-origin script (`theme.js` today), not an inline tag. | Follow-up; not changed in this slice |
| Shared e2e fixtures should seed “already onboarded” flags so new first-visit UI does not break the suite. | Follow-up; noted here |

## Follow-ups

- No carousel. If a later slice wants a second beat, it needs a new PRD
  and Mobbin cites.
- Closing the GitHub issue after merge (this agent cannot open issues).
