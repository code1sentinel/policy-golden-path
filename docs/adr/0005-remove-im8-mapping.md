# 0005. Remove IM8 Reform mapping and coverage

Date: 2026-10-04

## Status

Accepted

## Context

Codify 1.2.0 (commit `9d13461`) mapped drafted controls to Singapore's IM8
Reform catalog: suggestions, bulk map, a coverage/gaps view, export
columns, and a bundled catalog. That surface grew chrome on the workspace
(filters, badges, a second view) and pulled the product away from "clause →
control statement → review → export".

PR #3 hid IM8 behind disclosure so the happy path stayed clause-to-control.
PR #4 (`b6afd91`, 2026-10-02) then **removed** the feature:

- no coverage view, Map to IM8 fold, suggestions, bulk map, or
  "Not mapped to IM8" filter
- no `im8` / `coverage` APIs, `im8.py`, bundled catalog, or
  `scripts/make_im8.py`
- no IM8 column in Excel/CSV, no coverage section in the report, no
  `im8-reform` props/links on export
- leftover `im8` fields on old projects are ignored so saved catalogs
  still open

Tests now assert the IM8 strings are gone (`tests/test_site.py`,
`tests/test_api.py`). The README no longer offers mapping or gap analysis.

## Decision

Codify's product is policy clause → control statement → review/accept →
OSCAL / Excel / CSV / report. It does not map to IM8 Reform or show
coverage against an external catalog.

Bringing mapping back (IM8 or another catalog) requires a new ADR that
supersedes this one, a feature PRD, and slices that do not bury the
clause-to-control path.

## Consequences

- The workspace stays one job. Exports stay smaller.
- People who need IM8 coverage must map outside Codify.
- Do not reintroduce bundled catalogs, mapping APIs, or coverage views
  "while we are here".
