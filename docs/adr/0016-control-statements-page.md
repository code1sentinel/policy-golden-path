# 0016. Control statements page is a drafting surface

Date: 2026-10-18

## Status

Accepted

Refines [0013-risk-first-authoring-flow.md](0013-risk-first-authoring-flow.md)
for **shared step 2 only** (Flow A after Identify risks, and the clause
path after paste). Does not change the two start paths, later steps,
`{id, text, risk_ids, …}`, treats-risk links, or OSCAL tracing
([0012](0012-identified-risks-as-input.md),
[0014](0014-oscal-identified-risk-statements.md)).
[0015-identify-risks-page.md](0015-identify-risks-page.md) still holds
for step 1.

## Context

ADR 0013 put a shared authoring stepper and a dismissible What / Why /
example / mistakes guide on every web step. Identify risks (ADR 0015)
dropped that chrome. Step 2 still stacks a card per risk, optional
clause fields, library suggest buttons, and Previous / Next.

The owner finds that page messy. The job is to write a control statement
for every risk or clause — not to run a four-step wizard or browse the
library as a panel.

## Decision

Shared step 2 is a single drafting page:

- The same small three-step indicator as Identify risks (Identify risks
  or Policy clause, Control statements, Policy as code (Rego)), and a
  Back link.
- Title **Write a control statement for each risk** (or **…for each
  clause**), one guidance sentence, and an optional collapsible writing
  tip.
- A split list + editor (accordion on a small viewport). Each list row
  has a coverage dot. The editor shows the selected item read-only and
  its statements as editable blocks, with add / remove. Keyboard moves
  between items.
- **Continue to policy as code** is the only primary, and it stays
  disabled until every listed item has at least one non-empty statement
  (the existing required-statement rule).
- The Statement library is a quiet **Insert from library** action in the
  editor, not a panel. Optional clause fields and the What / Why guide
  are not on this page.
- Shared stepper, step guide, and Previous / Next stay on later steps
  until those pages are redesigned.

Controls remain the same records. Adding a statement for a risk still
sets `risk_ids`. Removing a statement removes that control; other
statements and links stay.

## Consequences

- Control statements is quieter and has one job. Link to risks, Review,
  and Enact still use the ADR 0013 wizard chrome.
- Empty validation is the disabled Continue button and the progress
  line, not a red error after Next.
- The clause path shows this page after paste (before Link to risks) so
  both start paths share step 2.
