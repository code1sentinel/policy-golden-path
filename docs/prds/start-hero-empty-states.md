# PRD: Start hero and empty states

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Product-owner approval of design-review findings 2 and 5 (Andre, 2026-10-04). This agent cannot open GitHub issues; acceptance criteria live here. |
| Supercedes / extends | [docs/prd.md](../prd.md) |
| Author | Andre (product owner) / this slice |
| Date | 2026-10-04 |

## Problem

The Start view leads with a large orange "Try the Acme demo" button. The
real path (paste a clause → Codify) sits below in a dashed "Or load your
policy" card with a second primary. Two primaries, and the main task
looks secondary.

Empty panes are a muted line with no next step: the editor says "Select
a clause…" and a tight filter says "Nothing matches this filter."

## Users

- **Primary:** a GRC reviewer arriving at Codify to paste a clause.
- **Not this slice:** OSCAL preview, export split, theming, AI chrome.

## Job to be done

Paste a clause and press Codify. If the list or editor is empty, see
one action that unblocks you.

## Scope

- In:
  - Clause textarea as the Start hero; one primary **Codify**.
  - Demo becomes a quiet **Try an example** chip (still opens Acme).
  - **Open a file** stays secondary.
  - Editor empty state: icon, one line, **Open first draft**.
  - Filter empty state: icon, one line, **Show all**.
  - Escape clears the current selection so the editor empty state is
    reachable from the keyboard.
- Out:
  - Title field or clause numbers (keep [ADR 0006](../adr/0006-clause-only-input.md)).
  - OSCAL JSON tab, export split, theme toggle, moving the AI control.

## Success criteria

- Given the Start view with no resume card, When it is shown, Then the
  only primary button is **Codify**, the demo is a non-primary **Try an
  example** chip, and there is no "Or load your policy" heading.
- Given **Try an example**, When it is clicked, Then the Acme demo
  opens with drafts.
- Given a filter that matches nothing, When the list is empty, Then it
  shows an icon, "Nothing matches this filter.", and **Show all** resets
  the filter to All.
- Given a project with no selection, When the editor is empty, Then it
  shows an icon, "Select a clause to draft its control.", and **Open
  first draft** opens the first draft.
- No Title field. No new outbound calls.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Krea AI — single prompt + Generate | https://mobbin.com/screens/323e22c9-d758-4bf1-aee3-dcc9e284a2ef | One hero input, one primary generate |
| Gamma — example prompts | https://mobbin.com/screens/23a25ddc-5d71-44d3-af2b-ff2ea0ec1767 | Quiet examples under the input |
| Arcade — empty output | https://mobbin.com/screens/7b9d6805-0331-41c2-b7aa-165ea081bb09 | Centred icon + line in the empty pane |

Adapt the patterns to Codify's dark workspace. Do not copy branding.

## Privacy and outbound calls

No new network call, origin, or leave-device path.

## Open questions

None. Andre approved findings 2 and 5.

## Decision log

None. Layout only; no ADR.
