# 0008. Risk input and OSCAL tracing

Date: 2026-10-06

## Status

Accepted

## Context

[ADR 0006](0006-clause-only-input.md) makes **clause text** the happy-path
input: no Title field, clause numbers optional and not shown. Codify's
catalog is OSCAL 1.1.2 ([ADR 0002](0002-oscal-1-1-2.md)) and is also the
save file. Enact reads that catalog.

GRC reviewers also identify risks and want those turned into the same
kind of control statements, traced in the catalog. Putting risks *in
place of* clauses would reverse ADR 0006. Uploading the register would
reverse [ADR 0003](0003-local-only-privacy-model.md).

OSCAL 1.1.2 catalog has no first-class Risk object. Tracing has to use
back-matter resources, control `props`, and `links` that stay
schema-valid.

## Decision

### Input coexistence

- Clause-only input is unchanged. Pasting a clause still does not ask
  for a title or a risk.
- Risks are a **parallel** local register on the project (`project.risks`).
  They are optional. A project with only clauses still opens, scores, and
  exports as today.
- Importing a risk CSV/JSON does not create clauses. Drafting from a
  risk does not require a clause id.

### Risk record

Each risk has: `id` (R-001, …), `title`, `description`, `asset`
(asset or process), `likelihood` (1–5), `impact` (1–5), computed
`score` (likelihood × impact), optional `threat`, `vulnerability`,
`owner`, and `status` (`identified`, `treating`, `accepted`, `closed`).

The register lives in memory and the existing `codify:project` autosave.
It is never posted to a Codify server.

### OSCAL tracing

On export:

1. Write one `back-matter.resources[]` entry per risk:
   - `uuid` — stable UUID5 of `(project.uuid, "risk:" + id)`
   - `title` — risk title (or id)
   - `description` — risk description
   - `props` in the Codify namespace: `risk-id`, `asset`, `likelihood`,
     `impact`, `score`, `threat`, `vulnerability`, `owner`, `status`
2. Each control carries `props` `source-type` (`clause` or `risk`).
3. A control drafted from a risk also carries `props` `risk-id` and
   `links: [{ "href": "#<risk-resource-uuid>", "rel": "reference" }]`.
4. Clause-derived controls keep `links` `derived-from` the clause
   resource. A control is not required to have both.

Opening a Codify catalog restores `project.risks` from resources that
have `risk-id`. Resources with `clause-id` remain clauses. Unknown
catalogs still become clause+control pairs as today.

### Enact

Enact should keep reading `catalog.groups[].controls[]` statements.
New props and back-matter resources are additive. Enact can ignore
`source-type` and risk resources; if it wants a trace, follow
`rel=reference` or read `risk-id`. It must not assume every control has
`legacy-clause` or a `derived-from` link.

## Consequences

- Goldens gain `source-type` on controls, and new goldens cover
  risk-only and mixed catalogs.
- CLI `--risks` merges a register into the project before export.
- Reversing this (risks as the only input, or a second save format)
  needs a new ADR. Quietly dropping clause-only input is not allowed.
