# 0018. Policy clause page is a capture surface

Date: 2026-10-19

## Status

Accepted

Refines [0013-risk-first-authoring-flow.md](0013-risk-first-authoring-flow.md)
for **Flow B, step 1 only**. Does not change the two start paths, later
steps, coverage gates, clause records, or OSCAL tracing
([0006](0006-clause-only-input.md),
[0012](0012-identified-risks-as-input.md),
[0014](0014-oscal-identified-risk-statements.md)).
[0015-identify-risks-page.md](0015-identify-risks-page.md) still holds
for Flow A step 1.
[0016-control-statements-page.md](0016-control-statements-page.md) still
holds for shared step 2.

## Context

ADR 0013 put a Codify / Open a file / Try an example paste card on path B,
then auto-drafted and showed a result step. Identify risks (ADR 0015)
dropped that wizard chrome for Flow A step 1. Control statements (ADR 0016)
is already a calm drafting page with **…for each clause** on this path.

The owner finds the clause entry page messy. The job is to get existing
policy clause(s) in so the next step can write control statements — not
to run a converter or a file picker.

## Decision

Flow B step 1 is a single capture page:

- A small three-step indicator that matches Identify risks (Policy
  clause, Control statements, Policy as code (Rego)), and a back link
  to the landing.
- Title **Paste your policy clause**, one guidance sentence, a large
  paste textarea, and a small side example of a good clause and how to
  separate several with a blank line.
- A pasted block splits on blank lines into a preview list the person
  can edit or remove. Continue commits leftover text in the box.
  Splitting is the multi-clause model because the input is existing
  policy prose, not one-line typed rows.
- **Continue to control statements** is the only primary, and it stays
  disabled until at least one clause exists.
- No Title field (0006). Optional source policy name lives under a
  collapsed **Add details**. Project name still comes from the first
  clause.
- This page does not run classify/draft. The person writes statements
  on step 2, same as Flow A. CLI and opening a saved catalog still
  draft as today.
- Shared stepper, step guide, and Previous / Next stay on later steps
  until those pages are redesigned.

Ids remain `c1`, … (or the policy's own numbers on older catalogs). They
are not shown on this page. Removing a clause drops that clause and the
controls that pointed at it; other clauses stay.

Older clause-first projects and catalogs still open on path B. **Policy
Clause** opens this page at step 1 with the saved clauses.

## Consequences

- Policy clause is quieter and has one job. Link to risks, Review, and
  Enact still use the ADR 0013 wizard chrome.
- Empty validation is the disabled Continue button, not a Codify error.
- Auto-drafting on paste is gone from the web clause path. Rule drafts
  remain on the CLI and when opening a file or the Acme demo through
  the existing `open` action.
- Re-introducing a Title field still needs an ADR that supersedes 0006.
