# PRD: Identified risks as input

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Listed in the PR; this agent cannot open GitHub issues. |
| Supercedes / extends | [docs/prd.md](../prd.md), [remove-risk-register.md](remove-risk-register.md) |
| Author | Product owner / this slice |
| Date | 2026-10-14 |

## Problem

ADR 0011 removed the risk register so Codify engineers risk (controls)
instead of producing a scored artifact. Reviewers still identify risks
outside the app and need those statements in the project so control
statements can address them. Today the only “risk” field is free-text
purpose on a control (“the risk it treats”). There is no way to enter
already-identified risks, link controls to them, see coverage, or trace
the link in the catalog.

## Users

- **Primary:** a GRC reviewer who already uses Codify for clauses and
  already has identified risks (from a workshop, another tool, or notes).
- **Not this slice:** anyone who wants Codify to be a risk register
  (scoring, owners, treatment plans, residual risk, FAIR).

## Job to be done

Enter the risks already identified, link control statements that address
them, see which risks have no control and which controls treat none, and
export an OSCAL 1.1.2 catalog that traces those links.

## Scope

- In:
  - A simple identified-risks list on the project (`id`, short
    `statement`, optional `note`).
  - Controls may link to one or more risk ids. “Risk it treats” displays
    the linked statement(s). Purpose scoring still uses that wording.
  - Persist in `codify:project` / the OSCAL save. Old projects and old
    register catalogs load with an empty list; leftover register fields
    stay dropped ([ADR 0011](../adr/0011-no-risk-register.md)).
  - Lightweight Risks input panel: add / edit / remove. Per risk, suggest
    matching Statement library entries (local matching). If AI assist is
    already on, it may also suggest through the existing `ai_prompt` /
    `ai_reply` path.
  - Coverage flags: uncovered risks, unlinked controls.
  - OSCAL export of the links ([ADR 0012](../adr/0012-identified-risks-as-input.md)).
    Excel, CSV, and the report keep working.
- Out:
  - Scoring, likelihood/impact, owners, review cycles, treatment plans,
    heatmaps, residual risk, FAIR, register import, CLI `--risks`, Risk
    register export, `source-type=risk`.
  - New AI providers, origins, fonts, or uploads.
  - Changing clause-only happy-path input ([ADR 0006](../adr/0006-clause-only-input.md)).
  - Mapping to IM8 or any external catalog.

## Success criteria

- Given an older `codify:project` with no identified-risks list (or a
  leftover register array), When it is opened, Then `risks` is `[]` and
  clauses / controls / `codify:statements` remain.
- Given a project with identified risks `{id, statement, note?}`, When it
  is saved and reopened (autosave or OSCAL), Then the same list and
  control `risk_ids` come back.
- Given a risk with no linked control, When coverage is computed, Then
  that risk is flagged uncovered. Given a control with no `risk_ids`, Then
  it is flagged unlinked.
- Given a library statement that shares distinctive wording with a risk,
  When suggestions are requested, Then that statement is offered. A
  statement with no overlap is not.
- Given a control linked to a risk, When the catalog is exported, Then
  the catalog is valid OSCAL 1.1.2, contains a back-matter resource with
  `identified-risk-id`, a `treats-risk` prop, and a `rel=related` link,
  and does not emit `source-type=risk` or old `risk-id` register tracing.
- Given the workspace, When the sidebar renders, Then there is a Risks
  input view and no Risk register export, heatmap, or likelihood/impact
  fields.
- No new outbound calls. No keys written.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Vanta — risk scenario → recommended controls dialog | https://mobbin.com/screens/c5d6df8f-69b2-4729-950d-c0fc5b6a20e6 | Focused dialog: scenario at the top, recommended statements as a list with Add, Not now / Add statements in the footer. |
| Vanta — control detail with mapped elements | https://mobbin.com/screens/a31c2c1c-11e7-468f-8751-16bc93561d89 | Control properties: mapped risks as elements on the control (id, statement, unlink), not a second register. |
| Vanta — related controls table | https://mobbin.com/screens/615f46f7-bdab-47fd-b1ef-93a03da670e4 | Coverage table: risk / control columns, flags for uncovered and unlinked rows. |

Adapt to Codify's indigo / cool-gray shell. Do not copy Vanta branding or
add starter-guide / tests / vendors chrome.

## Privacy and outbound calls

Identified risks stay on-device like the rest of the project
([ADR 0003](../adr/0003-local-only-privacy-model.md)). Matching the
library is local. Optional AI uses the existing browser-to-provider path
(one risk statement as the prompt text) and never stores a key in the
project, catalog, library, or this repo. No new origins.

## Open questions

None.

## Decision log

- [ADR 0012](../adr/0012-identified-risks-as-input.md) — identified risks
  as input, not a register; OSCAL `identified-risk-id` / `treats-risk` /
  `rel=related`.
