# PRD: First-visit welcome splash

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | This agent cannot open GitHub issues; acceptance criteria live here. |
| Supercedes / extends | [docs/prd.md](../prd.md), [start-hero-empty-states.md](start-hero-empty-states.md), [personal-start-chrome.md](personal-start-chrome.md) |
| Author | Andre (product owner, 2026-10-07) / this slice |
| Date | 2026-10-07 |

## Problem

A first visit drops the person straight onto the paste start. There is no
calm “you are in the right place” beat before the clause box. Returning
work must stay instant: anyone with a saved project must not be trapped
behind an intro.

## Users

- **Primary:** a GRC reviewer opening Codify on this device for the first
  time (Pages or `codify-web`).
- **Not this slice:** accounts, multi-step onboarding, AI chrome, changing
  the paste start that already shipped.

## Job to be done

See a short welcome, press one button, then paste a clause. If this device
already has a project, skip the welcome and resume.

## Scope

- In:
  - One full-viewport-in-main splash instead of the paste start, only when
    the person has not dismissed it and there is no resume card.
  - Codify mark (existing `.brand__mark` geometry), “Welcome to Codify”,
    one lede, one primary **Get started**.
  - Dismiss stored in `localStorage` as `codify:splash-seen` (same
    `codify:*` family as theme, project, and library). No new ADR: this is
    a UI preference on this device, not a new leave-device path.
  - Skip splash when `codify:project` would show the resume card, even if
    the splash flag is unset.
  - Light / Dark / System via existing tokens.
- Out:
  - Carousel, pagination dots, or extra onboarding questions.
  - Accounts, email capture, or outbound calls.
  - Linear branding, purple, or new font hosts.
  - Changing the paste start, checklist, or club-footer-already-removed
    chrome.

## Success criteria

- Given a first visit with no `codify:splash-seen` and no saved project,
  When the page loads, Then a splash is shown instead of `#start`, with
  the Codify mark, “Welcome to Codify”, a one-line lede about on-device
  OSCAL drafting, and one primary **Get started**.
- Given the splash, When **Get started** is pressed, Then the splash is
  dismissed, `codify:splash-seen` is set, and the existing paste start is
  shown with **Codify** as the only start primary.
- Given `codify:splash-seen` is already set, When the page loads, Then the
  splash is not shown and the paste start appears as today.
- Given a resume card would show (`codify:project` with a project), When
  the page loads, Then the splash is skipped even if the seen flag is
  unset.
- Given the splash was dismissed, When **Try an example** is pressed,
  Then the Acme demo still opens.
- Skip-to-content still targets `#main`. Privacy note, loading, and error
  behaviour are unchanged. No new outbound origins or font hosts.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Linear — welcome splash | https://mobbin.com/screens/62773d0f-3574-4191-ac91-eb8a51697a95 | Centered mark, “Welcome to …”, one short product line, one primary Get started, generous whitespace. Codify stays one screen (no carousel). Indigo button uses Codify tokens, not Linear purple. |

Adapt the hierarchy to Codify’s indigo-on-cool-gray workspace. Do not copy
Linear branding.

## Privacy and outbound calls

No new network call, origin, or leave-device path. Dismiss is a
`codify:splash-seen` flag in `localStorage`, consistent with `codify:theme`.
The policy never leaves the device.

## Open questions

None. Andre chose this direction on 2026-10-07.

## Decision log

None. Storage key matches the existing `codify:*` family; no ADR.
