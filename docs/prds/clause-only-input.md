# PRD: Clause-only happy path input

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Product-owner request (Andre), 2026-10-04 |
| Supercedes / extends | [docs/prd.md](../prd.md) |
| Author | Andre (product owner) / this slice |
| Date | 2026-10-04 |

## Problem

The happy path is "paste a policy clause, get a control statement." Today that
path asks for an optional **Title** and works best when the person numbers
clauses (`4.2.1 …`). A single unnumbered sentence is taken as the document
title and rejected ("number them"). A leading number is stripped into an id
and can leak into drafts. Reviewers should not have to invent titles or
clause numbers to convert one clause.

## Users

- **Primary:** a GRC reviewer converting one or more clauses they already
  have in prose.
- **Not this slice:** a new visual design for the workspace.

## Job to be done

Paste the clause text. Codify drafts the control. Numbers and a policy title
are not part of the input.

## Scope

- In:
  - Remove the optional Title field from the web app, Pages site, `open`
    API, and any caller/fixture that sent it.
  - Accept unnumbered clause text. Do not treat the first line as a title.
  - Keep pasted text that starts with a number (`4.2.1 Users shall…`) as the
    clause text. Do not require numbers; do not show them in the UI.
  - Mint stable internal clause/control ids and OSCAL titles so catalogs
    stay valid OSCAL 1.1.2.
  - Structured files (Acme, Word, numbered multi-clause paste) still split
    on the policy's own numbering so the Acme key holds.
- Out:
  - New layout, chrome, or interaction patterns.
  - Changing OSCAL version, privacy, or AI drafting.
  - Removing document titles that come from a `#` heading, Word Title
    style, or filename (those are not the form field).

## Success criteria

- Given only clause text (no title, no number), When the person pastes it
  or opens it as a text file, Then Codify produces at least one clause and
  a rule draft.
- Given text that starts with `4.2.1`, When it is a single pasted
  paragraph, Then that number stays in the stored clause text and is not
  shown as a required field.
- Given the start form, When it is rendered (web app or Pages), Then there
  is no Title input and the workspace list does not display clause numbers.
- Given an unnumbered clause, When Codify writes a catalog, Then every
  control id is an OSCAL token and the catalog matches the golden file and
  NIST 1.1.2.
- The Acme key (`tests/test_acme.py`) still holds.

## Design references

**No new design.** This slice only removes the Title field and hides clause
numbers. Existing dark-workspace styling stays. No Mobbin screen was used
because no layout was invented.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Start form — field removal only | — | Keep the existing paste card; drop Title |
| Workspace list — hide ids only | — | Keep cards, type, and statement text |

## Privacy and outbound calls

No new network call, origin, or leave-device path.

## Open questions

None. Andre decided the three points in this PRD.

## Decision log

- [ADR 0006](../adr/0006-clause-only-input.md) — clause-only input and
  internal OSCAL ids.
