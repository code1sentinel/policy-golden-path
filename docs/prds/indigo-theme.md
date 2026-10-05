# PRD: Indigo on cool gray (light + dark)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | No GitHub issue in this environment. Acceptance criteria live here. |
| Supercedes / extends | [docs/prd.md](../prd.md), [theme-ai-chip.md](theme-ai-chip.md) (accent hue and canvas greys only) |
| Author | Product owner / this slice |
| Date | 2026-10-05 |

## Problem

Light and dark themes exist ([theme-ai-chip.md](theme-ai-chip.md)), but the
accent is orange (`#E8650A`) on a warm-neutral canvas. Reviewer tools such as
Linear and Twenty use indigo on cool gray, which reads as product chrome
rather than a warning colour. Codify’s primary buttons, selected rows, and
focus rings currently look like alerts.

## Users

- **Primary:** anyone using `codify-web` or the Pages site in Light, Dark, or
  System.
- **Not this slice:** layout, typography, or declutter of Workspace / Guide.

## Job to be done

Keep Light / Dark / System. See indigo fills and cool-gray surfaces in both
themes, with the same WCAG 2.2 AA pairs as today.

## Scope

- In:
  - Replace light and dark colour token **values** with indigo accent and
    cool-gray surfaces. Existing token names (`--orange` is the accent fill)
    stay so CSS rules do not need a rename.
  - `--on-accent` is light (white) on the indigo fill so primary buttons
    stay AA.
  - Favicon slash matches the indigo fill.
  - Contrast pairs still meet AA (text ≥4.5:1, UI ≥3:1). Automated test
    asserts indigo hue and cool (blue ≥ red) canvases, not only contrast.
- Out:
  - Layout, spacing, fonts, or Workspace / Guide declutter (PR #22).
  - Renaming every `var(--orange)` in CSS.
  - New fonts, CDNs, or outbound origins (no ADR).

## Success criteria

- Given the theme tokens, When contrast is computed, Then text pairs are
  ≥4.5:1 and UI pairs ≥3:1 in both themes.
- Given `--orange` in light and dark, When its hue is computed, Then it is
  indigo (about 220–250°), not orange (`#E8650A`).
- Given `--bg` in light and dark, When RGB is compared, Then the blue
  channel is at least the red channel (cool gray, not warm).
- Given a primary button, When it is shown, Then label colour is light on
  the indigo fill (`--on-accent` luminance high).
- Given the theme toggle, When it is used, Then no third-party hosts are
  requested (existing e2e).
- No new network call, origin, or leave-device path.

## Design references

Adapt the patterns. Do not copy branding.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Linear — dark issue list | https://mobbin.com/screens/e142df2a-3527-499c-8f81-1b715947ac0c | Near-black cool canvas, quiet list, indigo as the only accent |
| Linear — dark product + app | https://mobbin.com/screens/18191caa-a25c-4c43-a7d2-0f6e52b444b1 | Dark raised surfaces and cool gray chrome |
| Linear — light settings | https://mobbin.com/screens/4c62cf9f-feb8-4928-b62d-84585be57b07 | Cool gray sidebar, white canvas, indigo control |
| Linear — indigo toggle on light | https://mobbin.com/screens/c7223b87-8318-4848-8453-2ac4b1e1a0a9 | Indigo fill for the on state, not orange |
| Linear — Light / Dark / System | https://mobbin.com/screens/abf277ec-d00a-4504-8cfa-54930315f0ab | Same accent in both appearances |
| Twenty — appearance | https://mobbin.com/screens/bee89cac-9a8a-4f5c-a0ef-90a26ec69658 | Light / Dark / System on a cool canvas |
| Twenty — light canvas | https://mobbin.com/screens/11590444-bb89-4836-88d5-1c8a83df041c | Cool gray page, white writing surface |

## Privacy and outbound calls

No new network call, origin, or leave-device path. Theme preference stays
`localStorage` only.

## Open questions

None. Mobbin links were supplied with the request.

## Decision log

None. Palette only; privacy model unchanged
([ADR 0003](../adr/0003-local-only-privacy-model.md)).
