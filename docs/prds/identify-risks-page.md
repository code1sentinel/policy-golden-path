# PRD: Identify risks page (Flow A, step 1)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | [COD-5](https://linear.app/code1sentinel/issue/COD-5/identify-risks-page-flow-a-step-1) |
| Supercedes / extends | [docs/prd.md](../prd.md), [risk-first-authoring-flow.md](risk-first-authoring-flow.md) (this page’s chrome only) |
| Author | Product owner / this slice |
| Date | 2026-10-16 |

## Problem

The owner finds Codify messy. Flow A step 1 (reached from the landing card
**Identify risk → Control statement → Policy as code (Rego)**) currently
mixes a four-step authoring stepper, a What / Why / mistakes guide, a
card form, a red “add at least one” error, Previous / Next, and risk-id
pills. The job on this page is only to capture identified risks.

## Users

- **Primary:** a GRC reviewer who already identified risks and wants to
  type them in so control statements can treat them.
- **Not this slice:** scoring, owners, registers, the control-statements
  page, clause paste, Review, or Send to Enact.

## Job to be done

On one calm page, write the risks already identified, then continue to
control statements.

## Scope

- In:
  - Redesign **only** the Identify risks page (Flow A, step 1).
  - Small step indicator: 1 Identify risks, 2 Control statements,
    3 Policy as code (Rego), plus a back link to the landing.
  - Title **What risks have you identified?** and one plain sentence of
    guidance.
  - Optional collapsible **How to write a good risk statement** tip with
    a short example (*Unauthorised access to customer data due to shared
    admin accounts*).
  - A document-like list: always-visible inline **Add a risk** row
    (Enter adds, Esc cancels); each row editable in place with an
    optional note and a remove action.
  - Friendly empty state.
  - One primary **Continue to control statements**, disabled until at
    least one risk exists.
  - Keyboard, labels, focus after add/remove, and a usable small viewport.
  - Keep `{id, statement, note?}` and the OSCAL risk export unchanged.
- Out:
  - Tables, modals, scores, owners, registers, likelihood/impact.
  - Redesigning later steps (controls, Review, Enact) or the sidebar
    Risks view.
  - Changing ids (`R-001`, …), coverage rules, or OSCAL tracing.
  - New outbound calls, font hosts, or AI keys.

## Success criteria

- Given Flow A step 1 with no risks, When the page renders, Then it shows
  the three-step indicator, a back link to the landing, the title, one
  guidance sentence, a collapsible writing tip, an empty state, an
  Add a risk row, and a disabled **Continue to control statements**. It
  does not show the What / Why guide, Previous / Next, a required-field
  error, or risk-id pills.
- Given the Add a risk row, When the person types a statement and presses
  Enter, Then the risk is in the list and Continue is enabled. When they
  press Esc, Then the draft is cleared and no risk is added.
- Given a risk in the list, When they edit the statement or note in
  place, Then the `{id, statement, note?}` record updates. When they
  remove the last risk, Then the empty state returns, Continue is
  disabled, and focus returns to Add a risk.
- Given at least one risk, When they activate Continue, Then they reach
  Develop control statements. Given no risks, Continue stays disabled.
- Given the back link, When it is activated, Then the landing is shown.
- Data model and OSCAL export stay `{id, statement, note?}` /
  ADR 0012 + 0014. No new outbound calls. No keys written.

## Design references

Opened and used before implementation. Adapt to Codify’s indigo /
cool-gray shell. Do not copy vendor branding.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Superlist — Getting Started list | https://mobbin.com/screens/657f85ad-6987-4e20-a56f-9d3a047f573c | Calm document: title, one lede, a list of rows with a quiet add affordance. |
| Todoist — Team Setup Guide list | https://mobbin.com/screens/3f80988f-fce8-4883-bd69-726f88146835 | Inline rows you can open and edit; optional secondary line under the statement. |
| Circle — setup checklist with steps and guide | https://mobbin.com/screens/b6520d1e-891e-49ea-8873-81ebd1a360a2 | Small step context plus a collapsible how-to beside a simple checklist. |

## Privacy and outbound calls

No new origins, fetches, or leave-device paths
([ADR 0003](../adr/0003-local-only-privacy-model.md)). Identified risks
stay on-device in `codify:project`. No AI keys written.

## Open questions

None.

## Decision log

- [ADR 0015](../adr/0015-identify-risks-page.md) — Identify risks page is
  a capture surface, not a wizard form.
