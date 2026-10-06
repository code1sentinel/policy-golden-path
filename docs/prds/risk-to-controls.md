# PRD: Risk → control statements

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Listed in the PR; this agent cannot open GitHub issues. |
| Supercedes / extends | [docs/prd.md](../prd.md), [ui-overhaul.md](ui-overhaul.md) |
| Author | Andre (product owner) / this slice |
| Date | 2026-10-06 |

## Problem

Codify turns **policy clauses** into control statements. GRC people also
identify **risks** and need those translated into the same catalog
controls, traced so Enact (and a reviewer) can see which risk a control
treats. That path does not exist: FAIR-CAM / risk-register surfaces were
removed before 1.0, and the shipped PRD lists them as out of scope.

Andre: "Remember we wanted to identify risk and translate those to
control statements for Codify?"

## Users

- **Primary:** a GRC reviewer who already uses Codify for clauses and
  also keeps a local risk register.
- **Secondary:** an engineer exporting OSCAL with `codify POLICY --risks FILE`.
- **Not this slice:** anyone who needs risks hosted, scored with FAIR, or
  mapped to an external catalog (IM8 remains out, [ADR 0005](../adr/0005-remove-im8-mapping.md)).

## Job to be done

Record risks on this device, draft control statements from them
(templates first, optional AI chip), accept them like clause drafts, and
export an OSCAL 1.1.2 catalog that traces each control to its risk so
Enact can still read the file.

## Scope

- In:
  - Local risk register (memory / autosave, never uploaded).
  - Fields: id (R-001), title, description, asset/process, likelihood
    (1–5), impact (1–5), computed score, optional threat, vulnerability,
    owner, status.
  - Register view (table + optional heatmap), detail drawer, add/edit,
    empty state, local CSV/JSON import with column mapping, CSV export.
  - Per-risk deterministic template suggestions (built-in library,
    statements that pass `control.py` checks) with Add / Accept / Dismiss.
  - Optional existing AI assist chip (new prompt only; same providers).
  - One risk → 1..n accepted controls in the catalog, traced per
    [ADR 0008](../adr/0008-risk-input-and-oscal-tracing.md).
  - Catalog source column shows clause vs risk id.
  - CLI: `codify POLICY --risks risks.csv -f oscal`.
- Out:
  - FAIR quantitative scoring, residual-risk workflow, live threat intel.
  - New AI providers, origins, fonts, or uploads.
  - Changing clause-only happy-path input ([ADR 0006](../adr/0006-clause-only-input.md)).
  - Mapping to IM8 or any external catalog.
  - Implementation statements (still catalog control statements only).

## Success criteria

- Given a CSV with the documented header, Codify imports risks locally
  and computes score = likelihood × impact.
- Given a risk with access/malware/backup keywords, template suggestions
  appear; each suggestion passes `assess_control_statement`.
- Given the person accepts a template (or an edited / AI draft), the
  exported catalog contains that control with `source-type=risk`, a
  `risk-id` prop, a `reference` link to the risk's back-matter resource,
  and stays valid OSCAL 1.1.2.
- Given a mixed project, clause-derived controls still have
  `derived-from` clause links; saved catalogs reopen with both clauses
  and risks.
- Given `--risks` on the CLI, OSCAL export includes the register.
- Malformed CSV rows and missing required columns are reported, not
  silently turned into controls.
- No new outbound calls. No keys written.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| 3. Linear issue detail | https://mobbin.com/screens/16e4d0c7-bf36-4daa-98f5-d3d31882cfec | Control editor for risk-derived drafts (same as clause). |
| 5. Grammarly review | https://mobbin.com/screens/82d0d01f-8aa2-4fe4-a658-1498c92fb1ae | Accept / Dismiss per template suggestion. |
| 6. Remote AI revision | https://mobbin.com/screens/44344cb5-9817-4d0e-b696-e8ba936b2f82 | Optional AI chip result: Try again / Use this. |
| 7. Vanta risk register | https://mobbin.com/screens/a5332e5f-d99a-4ae6-9367-f6778f54235d | Primary register table. |
| 8. Vanta heatmap | https://mobbin.com/screens/aae13fcf-1920-4d9a-afac-4270fadfab87 | Compact 5×5 likelihood × impact summary. |
| 9. Vanta risk library | https://mobbin.com/screens/d1276fef-704c-4650-9c7b-902ffa4e2f04 | Deterministic template suggestions with Add. |
| 11. Attio record detail | https://mobbin.com/screens/297adfeb-8312-496b-8acf-41839a6cf775 | Risk detail drawer: fields + linked drafts. |
| 12. Workable wizard | https://mobbin.com/screens/74548fe9-0ef9-4ca7-bb23-f8bc927acde8 | Add-risk flow and Draft → Review → Accept. |
| 13. Front empty state | https://mobbin.com/screens/972f8c8c-800e-435e-9348-e51b94d329ab | No risks yet: Create + Import. |
| 14. Apollo CSV mapping | https://mobbin.com/screens/0eea03eb-c4aa-441e-979f-1293525d7152 | Local CSV/JSON column mapping. |
| 15. Dovetail export | https://mobbin.com/screens/c1128474-a73d-46ed-bf7b-58aba54ae4b4 | Export dialog adds risk register CSV. |

## Privacy and outbound calls

Risks stay on-device like projects ([ADR 0003](../adr/0003-local-only-privacy-model.md)).
CSV/JSON is parsed in the local API or in the browser; nothing is uploaded.
Optional AI sends **one risk** (title, description, asset, threat,
vulnerability, and template drafts) to the provider the person already
chose, with the same acknowledgement as clause AI. No new origins.

## Open questions

- None. Residual risk is out of this slice.

## Decision log

- [ADR 0008](../adr/0008-risk-input-and-oscal-tracing.md) — risk model,
  coexistence with clause-only input, OSCAL tracing, Enact impact.
