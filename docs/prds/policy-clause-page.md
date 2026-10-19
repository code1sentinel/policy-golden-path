# PRD: Policy clause page (Flow B, step 1)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | [COD-7](https://linear.app/code1sentinel/issue/COD-7/policy-clause-page-flow-b-step-1) |
| Supercedes / extends | [docs/prd.md](../prd.md), [risk-first-authoring-flow.md](risk-first-authoring-flow.md) (this page’s chrome only) |
| Author | Product owner / this slice |
| Date | 2026-10-19 |

## Problem

The owner finds Codify messy. Flow B step 1 (reached from the landing
button **Get started with an existing policy clause** and the **Policy
Clause** tab) is still a Codify / Open a file / Try an example card with
pre-filled example text. The job on this page is only to get the user's
existing policy clause(s) in.

## Users

- **Primary:** a GRC reviewer who already has policy wording and wants to
  paste it so they can write a control statement for each clause next.
- **Not this slice:** scoring, owners, registers, Identify risks, Control
  statements chrome, Review, Send to Enact, CLI, or file ingest.

## Job to be done

On one calm page, paste existing policy clause(s), then continue to
control statements.

## Scope

- In:
  - Redesign **only** the Policy clause page (Flow B, step 1).
  - Small step indicator: 1 Policy clause, 2 Control statements,
    3 Policy as code (Rego), plus a back link to the landing.
  - Title **Paste your policy clause** and one guidance sentence: paste a
    clause from your existing policy; you'll write a control statement
    for each one next.
  - A large paste textarea as the main element, with an optional small
    side example panel showing a good clause and how multiple clauses are
    separated (a blank line).
  - Multiple clauses by **splitting a pasted block** on blank lines into
    a preview list the person can edit or remove. (Chosen over
    Identify-risks-style add rows: clauses are pasted from an existing
    policy, not typed one line at a time.) A quiet **Add clauses** action
    commits the box; Continue also commits leftover text.
  - Optional **Add details** (collapsed) for `source` (source policy
    name). No Title field ([ADR 0006](../adr/0006-clause-only-input.md));
    the project name still comes from the first clause.
  - Friendly empty state like Identify risks.
  - One primary **Continue to control statements**, disabled until at
    least one clause exists (in the list or in the paste box).
  - Keyboard, labels, focus after add/remove, and a usable 390px viewport.
  - Keep clause `{id, text, section, heading, type, reason, duplicate_of}`,
    clause-started project compatibility (old clause projects open on
    this path), and OSCAL export unchanged. Flow straight into the
    existing Control statements page with **Write a control statement
    for each clause**.
- Out:
  - Redesigning Identify risks, Control statements, Link to risks,
    Review, Enact, or the landing.
  - Changing ids, classification, drafting rules, or OSCAL tracing.
  - A Title field, Try an example, Open a file, a Codify button, or the
    “here's what we drafted” result step on this page.
  - New outbound calls, font hosts, or AI keys.
  - GRC Engineering Club branding.

## Success criteria

- Given Flow B step 1 with no clauses, When the page renders, Then it
  shows the three-step indicator (Policy clause current), a back link to
  the landing, the title, one guidance sentence, a large paste textarea,
  a small example panel, an empty state, and a disabled **Continue to
  control statements**. It does not show Codify, Try an example, Open a
  file, pre-filled example text, the What / Why guide, or Previous / Next.
- Given the paste box, When the person pastes or adds one clause, Then
  it is in the preview list and Continue is enabled. When they paste two
  clauses separated by a blank line, Then both appear and can be edited
  or removed.
- Given a clause in the list, When they remove the last one, Then the
  empty state returns, Continue is disabled, and focus returns to the
  paste box.
- Given at least one clause, When they activate Continue, Then they
  reach **Write a control statement for each clause**. Given no clauses,
  Continue stays disabled.
- Given a saved clause-first project, When Policy Clause is activated,
  Then this page opens with those clauses (ids and OSCAL unchanged).
- Given the back link, When it is activated, Then the landing is shown.
- Data model and OSCAL export stay unchanged (ADR 0006 + 0012 + 0014).
  No new outbound calls. No keys written.

## Design references

Opened and used before implementation. Adapt to Codify’s indigo /
cool-gray shell. Do not copy vendor branding.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Gamma — Paste in text | https://mobbin.com/screens/b2687527-370a-4f7c-9476-6c5ae4880388 | Large paste textarea as the main element; a small side panel that shows how to separate blocks. |
| Chronicle — start options | https://mobbin.com/screens/9c69feea-422a-44b8-9c24-16d99ceb1782 | Calm start: paste is one focused job, not a toolbox of Codify / file / demo. |
| Ferndesk — paste to import | https://mobbin.com/screens/7d26e41d-b326-4e0b-b692-13b9475e3482 | One paste field, one Continue, optional secondary tucked away (Add details). |

## Privacy and outbound calls

No new origins, fetches, or leave-device paths
([ADR 0003](../adr/0003-local-only-privacy-model.md)). Clauses stay
on-device in `codify:project`. No AI keys written.

## Open questions

None.

## Decision log

- [ADR 0018](../adr/0018-policy-clause-page.md) — Policy clause page is
  a capture surface, not a Codify submit card.
