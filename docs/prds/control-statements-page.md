# PRD: Control statements page (shared step 2)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | [COD-8](https://linear.app/code1sentinel/issue/COD-8/control-statements-page-shared-step-2) |
| Supercedes / extends | [docs/prd.md](../prd.md), [risk-first-authoring-flow.md](risk-first-authoring-flow.md) (this page’s chrome only) |
| Author | Product owner / this slice |
| Date | 2026-10-18 |

## Problem

The owner finds Codify messy. Shared step 2 — reached from **Continue to
control statements** on Identify risks, or after a pasted clause — currently
stacks a card per risk, a What / Why / mistakes guide, optional clause fields,
library suggest chrome, and Previous / Next. The job on this page is only to
write a clear control statement for every risk (or clause).

## Users

- **Primary:** a GRC reviewer who has identified risks (or pasted a clause)
  and needs to write the statements that treat them.
- **Not this slice:** scoring, owners, registers, Review, Send to Enact,
  the sidebar Risks view, or changing treats-risk / OSCAL tracing.

## Job to be done

On one calm page, write a control statement for every risk or clause, then
continue to policy as code.

## Scope

- In:
  - Redesign **only** the Control statements page (shared step 2).
  - Small step indicator: 1 Identify risks / Policy clause, 2 Control
    statements, 3 Policy as code (Rego), plus a Back link.
  - Title **Write a control statement for each risk** (or **…for each
    clause** on the clause path) and one plain sentence of guidance.
  - Optional collapsible **What makes a good control statement** tip with
    an example (*Customer data at rest is encrypted with AES-256 using
    managed keys; encryption is verified monthly by automated scan.*).
  - Desktop: left list of risks or clauses with a coverage dot; right
    editor with the selected item’s text read-only, editable statement
    blocks, **Add another statement**, and remove. Keyboard moves between
    items.
  - Mobile: one list; the editor expands on the selected item.
  - Progress line (**3 of 4 risks covered**) and one primary **Continue
    to policy as code**, disabled until every item has at least one
    non-empty statement (existing required-statement rule).
  - Quiet **Insert from library** in the editor (existing on-device
    library). No new endpoints.
  - Keep control `{id, text, risk_ids, …}`, treats-risk links, and OSCAL
    export unchanged.
- Out:
  - Redesigning Identify risks, Link to risks, Review, or Enact.
  - Changing coverage rules, ids, or OSCAL tracing.
  - New outbound calls, font hosts, or AI keys.
  - Library as a panel, optional clause fields, or the What / Why guide
    on this page.

## Success criteria

- Given Flow A step 2 with uncovered risks, When the page renders, Then
  it shows the three-step indicator (step 2 current), a Back link, the
  risk title, one guidance sentence, a collapsible writing tip, a left
  list with coverage dots, a right editor, a progress line, and a
  disabled **Continue to policy as code**. It does not show the What /
  Why guide, Previous / Next, or optional-clause fields.
- Given a selected risk, When the person types a statement and adds
  another, Then both persist on that risk (`risk_ids` includes it). When
  they edit or remove a statement, Then the control text updates or the
  control is removed, and the coverage dot and progress line update.
- Given some items still uncovered, Continue stays disabled. Given every
  item has at least one non-empty statement, When they activate Continue,
  Then they reach the next existing step (Review on the risk path; Link
  to risks on the clause path).
- Given the clause path after paste, When they reach this page, Then the
  title is **Write a control statement for each clause** and the list
  shows clauses.
- Given the Back link on the risk path, When it is activated, Then
  Identify risks is shown.
- Data model and OSCAL export stay unchanged (ADR 0012 + 0014). No new
  outbound calls. No keys written.

## Design references

Opened and used before implementation. Adapt to Codify’s indigo /
cool-gray shell. Do not copy vendor branding.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Gemini Notebook — sources list + editor | https://mobbin.com/screens/859f9ce4-e9e8-40e4-9a3b-3e1a5997dcb8 | Split: a quiet source list on the left, a large writing surface on the right. |
| Asana — brief with suggestion panel | https://mobbin.com/screens/2cc892bb-10ca-4907-8168-82fa2a11634d | Document editor plus a secondary suggestion column used only as a quiet insert action. |
| WRITER — doc with checks panel | https://mobbin.com/screens/67394092-56f9-4816-aaec-16534fee6527 | Writing column with a compact side list of items and their check state. |

## Privacy and outbound calls

No new origins, fetches, or leave-device paths
([ADR 0003](../adr/0003-local-only-privacy-model.md)). Statements stay
on-device in `codify:project`. Library insert is local. No AI keys written.

## Open questions

None.

## Decision log

- [ADR 0016](../adr/0016-control-statements-page.md) — Control statements
  page is a drafting surface, not a wizard form.
