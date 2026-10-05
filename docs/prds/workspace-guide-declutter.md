# PRD: Workspace and Guide declutter

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | This agent cannot open GitHub issues; acceptance criteria live here. |
| Supercedes / extends | [docs/prd.md](../prd.md), [personal-start-chrome.md](personal-start-chrome.md) |
| Author | Product owner (cluttered workspace/guide) / this slice |
| Date | 2026-10-05 |

## Problem

Once a policy is open, Workspace stacks a tagline, privacy chip, title,
counts, progress, list chrome, then an editor with origin line, tabs,
legacy clause, statement label, review buttons, score, parts grid,
improvement copy, a Risk field, and four footer actions. Guide is a
dense three-column card wall plus an anatomy lecture and a scoring
footnote. The happy path (clause in → control out) competes with helper
text.

## Users

- **Primary:** a GRC reviewer editing one control at a time.
- **Not this slice:** Start hero, AI dialog copy, OSCAL JSON tab
  behaviour, export split, theme tokens, classification or drafting.

## Job to be done

Open a control and see the statement. Open Guide and read one practice
at a time. Secondary fields stay one click away.

## Scope

- In:
  - Hide the brand tagline and privacy chip while a project is open.
  - Editor: statement is the hero; Risk joins the extras fold; drop
    “N of M practices adopted”; quieter origin + tabs on one row.
  - Guide: single-column stacked practices, anatomy example without the
    four-bullet lecture and tools hint, no scoring footnote.
  - More whitespace in the split workspace and Guide.
- Out:
  - New views, new outbound calls, OSCAL shape, Start form, AI dialog.
  - Inventing a three-pane layout. Keep the existing list | editor split.

## Success criteria

- Given a project is open, When Workspace or Guide is shown, Then the
  start-only tagline and “runs in your browser” chip are not visible.
- Given an open control, When the Statement tab is shown, Then the
  statement textarea and Accept / Next are visible, Risk is inside the
  extras fold, and “practices adopted” is not shown.
- Given Guide, When it is shown, Then practices stack in one column,
  there is no anatomy key list or scoring footnote, and Weak / Strong
  examples remain.
- `43 clauses → 38 controls`, OSCAL tab, split Save, empty states, and
  the Acme key still hold. No new outbound calls.

## Design references

Web screens from Mobbin. Adapt to Codify's existing dark workspace; do
not copy branding.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Linear — inbox + issue detail | https://mobbin.com/screens/beb9d6b3-ec34-46d7-9332-320fcb32a338 | Quiet list, title as hero, properties in a slim rail / collapsed |
| Grok — files + document.md | https://mobbin.com/screens/b9b4d3ed-593b-46f1-8f25-326edc5eae68 | Compact file list, large editor, thin chrome |
| Fibery — nav + empty document | https://mobbin.com/screens/2c370ce3-3e40-42cf-9717-397930f338b3 | Split: list left, generous whitespace around the writing surface |
| Frame — docs list + outline | https://mobbin.com/screens/1d845fd9-50f7-4342-bb06-534e4aa4b9b7 | Selected row, reading pane is the focus |
| Mintlify — intro + stacked cards | https://mobbin.com/screens/d4ce0aef-c205-432b-8f31-b4267315dc35 | Single-column docs, short intro, one card per idea |
| LangChain — numbered quickstart | https://mobbin.com/screens/568fff70-41fd-4660-a3b6-eb843e6e14d9 | Stacked sections, short labels, lots of space |
| Uxcel — one theory block | https://mobbin.com/screens/3c72f6e0-becb-4ad2-840c-09479eb71585 | One column, one idea, whitespace around the copy |

## Privacy and outbound calls

No new network call, origin, or leave-device path. Privacy chip stays on
Start (Pages / browser mode) and in the AI dialog.

## Open questions

None.

## Decision log

None. Layout density only; no ADR.
