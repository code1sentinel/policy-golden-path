# 0014. Identified risks export as assessment-style catalog resources

Date: 2026-10-15

## Status

Accepted

Refines [0012-identified-risks-as-input.md](0012-identified-risks-as-input.md).
Does not revive [0008-risk-input-and-oscal-tracing.md](0008-risk-input-and-oscal-tracing.md)
or a risk register ([0011-no-risk-register.md](0011-no-risk-register.md)).

## Context

ADR 0012 traces identified risks in the OSCAL 1.1.2 **catalog** as
`back-matter.resources[]` with `title` and `description` both set to the
short statement, plus Codify-namespace props `identified-risk-id` and
optional `note`. Controls keep `treats-risk` and `rel=related`.

Reviewers asked for proper OSCAL **risk statements** on export: title,
description/statement, and status, in the spirit of assessment-results
`risk` objects (OSCAL 1.1.2). The catalog schema has no first-class
`risk`, `statement`, or `status` on a back-matter resource
([ADR 0002](0002-oscal-1-1-2.md)). Putting those keys on the resource
would fail NIST's `oscal_catalog_schema.json`.

`project.risks` stays `{id, statement, note?}`. Status on export must
not become a register field.

## Decision

On export, each identified risk is still one catalog
`back-matter.resources[]` entry (UUID5 of
`(project.uuid, "identified-risk:" + id)`):

1. `title` — a short title (first words of the statement), not a
   duplicate of the full wording.
2. `description` — the risk statement (assessment-style description).
3. Codify-namespace props:
   - `identified-risk-id` — the project risk id (`R-001`, …)
   - `statement` — the same wording as `description`
   - `status` — always `open` (export-only; not stored on
     `project.risks`)
   - `note` — when the person supplied one
4. Do not emit first-class `risk`, `statement`, or `status` keys on the
   resource. Those belong to assessment-results, not the catalog schema.
5. Linked controls still carry `treats-risk` and
   `{ "href": "#<resource-uuid>", "rel": "related" }`.

Opening a catalog restores `project.risks` from resources that have
`identified-risk-id`. The statement is `props.statement`, else
`description`, else `title`. `status` is ignored on load. Older
catalogs that only have title + description + `identified-risk-id`
still restore.

## Consequences

- Goldens that write identified risks change (title, `statement` prop,
  `status=open`) and stay valid 1.1.2 catalog JSON.
- CI `oscal-schema` validates the identified-risk golden (and a live
  export) against NIST's catalog schema.
- `project.risks` is unchanged. Coverage, linking, and the Risks input
  panel stay as 0012 / 0013 specified.
- Adding a real assessment-results document, or a register status on
  input, needs a new ADR.
