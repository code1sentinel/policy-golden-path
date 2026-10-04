# 0006. Clause-only input and internal OSCAL ids

Date: 2026-10-04

## Status

Accepted

## Context

The happy path is clause text → control statement. The start form offered an
optional Title, and `parse_text` treated an unnumbered first line as the
policy title. A lone sentence therefore produced no clauses. Numbered
prefixes (`4.2.1`) were parsed out of the clause to become ids, which the
UI then displayed.

OSCAL 1.1.2 still needs a catalog title and a token id and title on every
control ([ADR 0002](0002-oscal-1-1-2.md)). Those cannot come from a field
we no longer collect.

Andre (product owner) decided: drop Title everywhere it is an input; do not
require or display clause numbers; keep pasted text that starts with a
number as-is; generate stable ids internally.

## Decision

- The only happy-path input is **clause text**. There is no Title field on
  the form, no `title` argument on `open`, and no CLI flag for a title.
- Document titles that already exist in a file (`#` heading, Word Title
  style, filename stem) may still fill `project.title` for the catalog
  metadata and export filename. They are not collected from the person.
- Clause numbers are optional. An unnumbered paragraph is a clause. A
  single pasted paragraph that starts with a number keeps that text
  unchanged. Multi-clause documents may still *split* on the policy's own
  numbering so the Acme key holds; those numbers are internal, not shown
  in the UI.
- Unnumbered clauses get a sequential id (`c1`, `c2`, …). Numbered
  clauses keep the policy number as an internal id. Control ids are
  derived from that id (`c1`, `5.1a`) as today. OSCAL control ids stay
  `c-` plus a token (`c-c1`, `c-5.1a`). OSCAL control titles are the
  first words of the statement. Catalog `metadata.title` is
  `{project.title or "Policy"}: control statements`.

## Consequences

- A GRC person can paste one sentence and get a draft.
- Saved catalogs remain OSCAL 1.1.2 and reopen. Callers that sent
  `title` on `open` are ignored.
- The workspace no longer shows clause or control numbers. Internal ids
  remain on the project for scoring, export, and resume.
- Changing this id scheme later needs a new ADR and a golden update.
