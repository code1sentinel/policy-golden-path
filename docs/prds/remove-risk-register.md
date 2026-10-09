# PRD: Remove the risk register

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Listed in the PR; this agent cannot open GitHub issues. |
| Supercedes / extends | [docs/prd.md](../prd.md), [risk-to-controls.md](risk-to-controls.md), [vanta-grc-surfaces.md](vanta-grc-surfaces.md), [first-run-clarity.md](first-run-clarity.md) |
| Author | Product owner / this slice |
| Date | 2026-10-09 |

## Problem

Codify shipped a local risk register (PRs #24/#25, ADR 0008) and later
Library vs Register tabs (ADR 0010). GRC engineering practice is to
engineer risk (controls, checks, automation) rather than maintain it as a
static artifact, so the register does not belong in the product.

## Users

- **Primary:** a GRC reviewer converting a policy into catalog controls.
- **Not this slice:** anyone who wanted Codify to be a risk-register tool.

## Job to be done

Open Codify and work clause → draft → review → accept → catalog / library
→ OSCAL export, without a Risks destination or a register export.

## Scope

- In:
  - Remove the Risks view/nav, register UI, scenario drafting, Risk
    register export, CLI `--risks`, and code/tests/fixtures/copy that
    exist only for the register.
  - Superseding ADR for ADR 0008 and the register half of ADR 0010.
  - Safe load of older `codify:project` (and leftover keys): drop register
    fields; do not corrupt clauses, controls, or `codify:statements`.
  - Keep Statement library (PR #26), Catalog, review/accept, OSCAL export,
    welcome splash (`codify:splash-seen`), and first-run clarity (PR #29)
    except bits that only served Risks (e.g. the Risks breadcrumb fix).
- Out:
  - A new layout or visual language. Removing the Risks nav item is the
    only chrome change; keep the existing indigo / Linear tokens.
  - Changing control-statement purpose scoring (“the risk it treats”).
  - Rewriting historical retros.

## Success criteria

- Given the workspace, When the sidebar renders, Then there is no Risks
  nav item and Export has no Risk register option.
- Given an older `codify:project` with a `risks` array (and controls that
  still have `risk_id`), When it is resumed, Then clauses and controls
  remain, the register fields are ignored or dropped, and
  `codify:statements` is untouched.
- Given an older Codify catalog with risk back-matter, When it is opened,
  Then its control statements load and no register is restored.
- Given Catalog, Library, splash, and first-run copy, When the app is
  used, Then those paths still work.

## Design references

None — no new UI patterns. The Risks nav item is removed from the
existing indigo / Linear shell. Statement library list + detail from
ADR 0010 stays as it is.

## Privacy and outbound calls

No new network calls, origins, fonts, or CDNs. AI keys still stay in the
browser only.

## Open questions

None.
