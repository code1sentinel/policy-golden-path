# 0011. No risk register

Date: 2026-10-09

## Status

Accepted

Supersedes [0008-risk-input-and-oscal-tracing.md](0008-risk-input-and-oscal-tracing.md)
entirely, and the Risks **Library** / **Register** surfaces in
[0010-vanta-grc-surfaces.md](0010-vanta-grc-surfaces.md). Statement-library
surfaces from ADR 0010 remain.

## Context

Codify shipped a local risk register next to clause-only input (ADR 0008)
and later split that register into Library vs Register tabs (ADR 0010).
GRC engineering practice is to engineer risk — controls, checks, and
automation — rather than maintain it as a static artifact. A risk register
does not belong in Codify.

Clause-only input (ADR 0006), the device-wide Statement library (ADR 0009),
the Catalog, review/accept, and OSCAL export stay. Older browsers may still
hold `project.risks` inside `codify:project`, and older catalogs may still
carry risk back-matter resources.

## Decision

- Codify does not offer a risk register: no Risks view or nav item, no
  scenario drafting, no register import, no `codify --risks`, no Risk
  register export.
- New projects and new catalogs do not store or emit register records
  (`project.risks`, `source-type=risk`, `risk-id` tracing, risk
  back-matter resources, `rel=reference` to a risk).
- Loading an older `codify:project` (or an older Codify catalog) **drops**
  leftover register fields and keeps clauses, controls, and
  `codify:statements`. The control-statement purpose field (`risk` /
  `risk-statement`, “the risk it treats”) is not the register and stays.
- Library entries that already have `source-type: risk` or `risk-id` keep
  those stored fields so `codify:statements` is not rewritten. The UI does
  not present them as a register.
- Statement library list + detail slide-over from ADR 0010 remains.

## Consequences

- A GRC reviewer engineers risk by writing and accepting control
  statements, not by keeping a scored register in Codify.
- Older saves still open. Controls that were drafted from a risk remain
  in the catalog as ordinary controls.
- Re-introducing a register needs a new ADR that supersedes this one.
