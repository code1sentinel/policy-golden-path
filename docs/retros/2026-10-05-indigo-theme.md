# Retro: indigo on cool gray

| Field | Value |
| --- | --- |
| Date | 2026-10-05 |
| Feature / PRD | [docs/prds/indigo-theme.md](../prds/indigo-theme.md) |
| Slices / PRs | This colour-token slice (PR on `cursor/indigo-theme-af4f`) |

## What we shipped

Light and dark `[data-theme]` tokens use indigo (`#5E6AD2`) on cool gray.
`--orange` stays as the accent-fill token name so CSS rules did not need a
rename. `--on-accent` is white. Favicon slash matches. Contrast tests now
assert hue and cool canvases, not only WCAG ratios. Rebased onto `#22`
(`bb7cc3e`) so the quieter Workspace/Guide layout and these tokens both land.

## What went well

Keeping token names meant the wiring was the two theme blocks plus the
favicon. Existing Light / Dark / System behaviour was unchanged.

## What was painful

A previous local commit could not `git push` (GitHub auth). Re-implementing
on a fresh branch was cheaper than recovering that VM. Contrast-only tests
would have stayed green on orange, so hue assertions had to be added first.

## Lessons to fold into the templates

| Lesson | Template to change |
| --- | --- |
| Palette slices need a hue / “not the old hex” test, not only AA pairs. | Already in this slice’s tests; no template change. |

## Follow-ups

- Optional later rename of `--orange` → `--accent` (out of this slice).
