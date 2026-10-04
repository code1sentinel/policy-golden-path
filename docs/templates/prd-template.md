# PRD: {feature name}

| Field | Value |
| --- | --- |
| Status | Draft / Agreed / Shipped |
| Slice issues | #… |
| Supercedes / extends | [docs/prd.md](../prd.md) |
| Author | |
| Date | YYYY-MM-DD |

## Problem

What is painful today, for whom, and why now.

## Users

Who this is for, and who it is not for.

## Job to be done

One paragraph: the person can do _X_ so that _Y_.

## Scope

- In:
- Out:

## Success criteria

Measurable. Each criterion should be testable as Given / When / Then on a
slice issue.

## Design references

**Required if this PRD changes any frontend or UI.** List Mobbin
(`https://mobbin.com`) screen links. If you do not have them yet, stop and
ask; do not invent a layout.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| | https://mobbin.com/... | |

If this PRD has no UI: write "None — no UI change."

## Privacy and outbound calls

Does this add a network call, a new origin, or leave-device data? Default is
no. If yes, you need an ADR and an explicit user confirmation path.

## Open questions

-

## Decision log

Link ADRs opened for this feature.
