# 0015. Identify risks page is a capture surface

Date: 2026-10-16

## Status

Accepted

Refines [0013-risk-first-authoring-flow.md](0013-risk-first-authoring-flow.md)
for **Flow A, step 1 only**. Does not change the two start paths, later
steps, coverage gates, `{id, statement, note?}`, or OSCAL tracing
([0012](0012-identified-risks-as-input.md),
[0014](0014-oscal-identified-risk-statements.md)).
[0011-no-risk-register.md](0011-no-risk-register.md) still holds.

## Context

ADR 0013 put a shared authoring stepper (complete / current / upcoming)
and a dismissible What / Why / example / mistakes guide on every web
step. On Identify risks that chrome sits next to a card form, a red
empty error, Previous / Next, and `R-001` pills.

The owner finds that page messy. The job is to capture identified risks
so the next step can write control statements — not to run a four-step
wizard or a register.

## Decision

Flow A step 1 is a single capture page:

- A small three-step indicator that matches the landing card
  (Identify risks, Control statements, Policy as code (Rego)), and a
  back link to the landing.
- Title **What risks have you identified?**, one guidance sentence, and
  an optional collapsible writing tip.
- A document-like list: Enter on the always-visible Add a risk row
  adds; Esc cancels the draft; each row is editable in place with an
  optional note and remove. No tables, modals, scores, or owners.
- **Continue to control statements** is the only primary, and it stays
  disabled until at least one identified risk exists.
- Shared stepper, step guide, and Previous / Next stay on later steps
  until those pages are redesigned.

Ids remain `R-001`, … in the project. They are not shown as register
pills on this page. Removing a risk still drops the link on controls;
the statements stay.

## Consequences

- Identify risks is quieter and has one job. Later Flow A steps still
  use the ADR 0013 wizard chrome.
- Empty validation is the disabled Continue button, not an inline error
  after Next.
- Re-introducing a scored register still needs an ADR that supersedes
  0011 and this one.
