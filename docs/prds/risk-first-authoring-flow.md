# PRD: Risk-first authoring flow

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | This PR (one issue → one PR; GitHub issue creation is not available to this agent) |
| Supercedes / extends | [docs/prd.md](../prd.md), [identified-risks-as-input.md](identified-risks-as-input.md). Identify risks page chrome: [identify-risks-page.md](identify-risks-page.md). |
| Author | Product owner / this slice |
| Date | 2026-10-14 |

## Problem

PR #36 / [ADR 0012](../adr/0012-identified-risks-as-input.md) added identified risks as an optional side view. The happy path is still clause → draft → accept → catalog; risks are linked afterwards. Control statements exist to treat risks, so starting from a clause leaves coverage optional and the Enact handoff implicit.

## Users

- **Primary:** a GRC reviewer who already identified risks and wants control statements that treat them, then a catalog Enact can load.
- **Also:** a reviewer who still wants to paste a policy clause first, then must link each draft to a risk.
- **Not this slice:** anyone who wants a scored risk register (likelihood, impact, owners, residual risk). [ADR 0011](../adr/0011-no-risk-register.md) holds.

## Job to be done

Start from risks (recommended) or from a clause, write control statements that cover every identified risk, review and accept, then download an OSCAL catalog and load it in Enact.

## Scope

- In:
  - Two start paths after the welcome splash (splash behaviour unchanged):
    - **(A) Start from risks** (recommended, default primary): identify risks → develop control statements → review → send to Enact.
    - **(B) Start from a policy clause:** paste (or Try an example / open a file) as today, then link each control to an identified risk (add risks inline if needed) → the same review and send-to-Enact steps.
  - Both paths share Review and Send to Enact. Same rules: every risk has at least one control statement; every control is linked to a risk; export is blocked until every risk has an accepted control statement.
  - Visible stepper with completion state. Per-step guide (what, why, a good example, common mistakes): dismissible and re-openable. Plain short copy.
  - Path A: at least one identified risk (`id`, statement, optional note) to continue. For each risk, one or more non-empty control statements (suggest from the on-device Statement library; existing optional AI assist path allowed; no new endpoints; never store AI keys). Policy clauses are optional context attachable to a risk or control.
  - Path B: Codify still drafts from the pasted clause. Then the user must link each control to a risk before Review.
  - Review: coverage (uncovered risks, unlinked controls), edit, accept. Keep “the risk it treats” purpose wording.
  - Send to Enact: export existing formats with a clear download-only handoff (link to Enact’s Pages app and [Using Codify with Enact](../book/enact.md)). No new outbound calls.
  - Old clause-first projects open on path B and prompt the user to add risks.
  - CLI `codify POLICY` stays clause-in, catalog-out (scripts). Web wizard gates export; CLI does not.
- Out:
  - Risk scoring, likelihood/impact, owners, heatmaps, treatment plans, FAIR, register import, CLI `--risks`, Risk register export, `source-type=risk`.
  - New AI providers, origins, fonts, or uploads.
  - Mapping to IM8 or any external catalog.
  - Changing OSCAL 1.1.2 tracing from ADR 0012.

## Success criteria

- Given the start screen after splash, When it renders, Then two paths are offered and **Start from risks** is the recommended primary.
- Given path A with no risks, When the person tries to continue, Then they stay on Identify risks with inline validation. Given at least one risk, When they continue, Then they reach Write a control statement for each risk.
- Given path A, When a risk has no non-empty control, Then they cannot move on; each risk can take a library suggestion or a typed statement; a policy clause may be attached as optional context.
- Given path B, When the person pastes a clause (or Try an example), Then Codify drafts as today, and they must link every control to a risk (adding risks inline if needed) before Review.
- Given Review, When coverage is shown, Then uncovered risks and unlinked controls are flagged; the person can edit and accept.
- Given Send to Enact, When every risk does not yet have an accepted control, Then download of the catalog (and other project formats) is blocked with a clear reason. Given coverage, When they download, Then the file is local only and the step explains how to load it in Enact.
- Given an old clause-first `codify:project` (no `authoring_path`, possibly empty risks), When it is opened, Then it uses path B and prompts to add risks. Splash, resume skip, and “the risk it treats” wording remain.
- No new outbound calls. No keys written.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Snowflake — Create Search Service stepper | https://mobbin.com/screens/01219fec-3d72-4a0a-a10f-5e7e119942e7 | Numbered wizard steps with current / complete state. Adapted as a horizontal stepper (Codify already has an app sidebar). |
| SoundCloud — Vinyl Studio rights, per-step guide + required fields | https://mobbin.com/screens/44ede9ee-7c41-4422-acc9-8c63adfae176 | Short what / why / example / mistakes beside the step; inline required-field errors. |
| Vanta — risk scenario → recommended controls | https://mobbin.com/screens/c5d6df8f-69b2-4729-950d-c0fc5b6a20e6 | Per-risk suggested library statements dialog (already shipped). |
| DoorDash Merchant — do you already have X? | https://mobbin.com/screens/2fd80f67-ebf0-4615-a9d0-74099c07498e | Start: two choices, one recommended primary, the other a clear alternative. |

Adapt to Codify’s indigo / cool-gray shell. Do not copy vendor branding.

## Privacy and outbound calls

No new origins, fetches, or leave-device paths ([ADR 0003](../adr/0003-local-only-privacy-model.md)). Export is a local download. Links to Enact and the Codify book are ordinary `<a href>` navigation the person chooses. Optional AI still uses the existing browser-to-provider path. Keys stay in the browser.

## Open questions

None.

## Decision log

- [ADR 0013](../adr/0013-risk-first-authoring-flow.md) — risk-first web flow with two start paths; refines ADR 0012 (and clause-only happy path on the web from ADR 0006).
