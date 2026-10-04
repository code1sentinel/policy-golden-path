# PRD: AI status chip and light / dark / system theme

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Product-owner approval of design-review findings 6, 7 and 8 (Andre, 2026-10-04). This agent cannot open GitHub issues; acceptance criteria live here. |
| Supercedes / extends | [docs/prd.md](../prd.md) |
| Author | Andre (product owner) / this slice |
| Date | 2026-10-04 |

## Problem

**AI drafting: off** sits in the same pill group as Workspace and Guide,
so a setting looks like a view. The UI is dark-only: tokens live in one
`:root`, there is no `prefers-color-scheme` handling, and several colours
are hard-coded. The dark placeholder and orange-as-text fail WCAG AA,
and a light theme would make that worse.

## Users

- **Primary:** anyone using Codify in a light or dark OS theme.
- **Not this slice:** new layouts, fonts, or outbound origins.

## Job to be done

Keep Workspace and Guide as the only view tabs. See AI as a status chip.
Choose Light, Dark, or System. Text and chrome stay at AA in both themes.

## Scope

- In:
  - Move AI drafting to a right-side status chip (`AI: Off` /
    `AI: On · provider`).
  - Compact Light / Dark / System header toggle (radio group).
  - Every hard-coded colour becomes a token. `[data-theme="dark"]` keeps
    today's dark workspace; `[data-theme="light"]` is the matching light
    set. `color-scheme` per theme.
  - Default follows `prefers-color-scheme` live. Persist under
    `codify:theme`. System clears the override.
  - Apply theme from same-origin `theme.js` in `<head>` (no inline
    script; CSP `script-src 'self'`).
  - Contrast: dark placeholder `#8A8A8A`; light accent text `#B54C00`;
    orange `#E8650A` as a fill only. Automated pair test.
- Out:
  - New fonts, icon libraries, or CDNs.
  - Changing Start, OSCAL tabs, or export behaviour.
  - Title field or clause numbers.
  - A new privacy origin (no ADR).

## Success criteria

- Given the header, When it is shown, Then Workspace and Guide are the
  only view tabs and AI is a status chip outside that nav.
- Given no saved theme, When the OS is light (or dark), Then
  `data-theme` matches (Playwright `color_scheme`).
- Given Light, When the page reloads, Then Light is still applied.
  Given System, When it is chosen, Then `codify:theme` is cleared and
  the OS theme is used.
- Given the theme toggle, When it is used, Then no third-party hosts
  are requested.
- Given the light and dark token pairs, When contrast is computed, Then
  text pairs are ≥4.5:1 and UI pairs ≥3:1.
- No inline script. `theme.js` is served from `'self'`.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Adaline — settings chips | https://mobbin.com/screens/80e3ebce-e59f-45a5-a6c5-7d9755ec4ef5 | Status chip in the toolbar, not a nav tab |
| Twenty — Light / Dark / System | https://mobbin.com/screens/bee89cac-9a8a-4f5c-a0ef-90a26ec69658 | Three-way appearance choice |
| Better Stack — Light / Dark / System | https://mobbin.com/screens/47f13a6b-5547-4aa6-bb4d-b8aa640e35d8 | Compact look-and-feel picker |
| Adaline — pass/fail on dark | https://mobbin.com/screens/081e7212-d5b4-4ca3-928c-d8a62f637b64 | Status colour that stays labelled and legible |

Adapt the patterns. Do not copy branding.

## Privacy and outbound calls

No new network call, origin, or leave-device path. Theme preference is
`localStorage` only.

## Open questions

None. Andre approved findings 6, 7 and 8. The theming spec is
`uploads/dark-mode-prompt.md` (Requirements).

## Decision log

None. Theming does not change the privacy model.
