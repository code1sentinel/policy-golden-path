# PRD: Three-tab nav (Home, Risk Entry, Policy Clause)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | [COD-11](https://linear.app/code1sentinel/issue/COD-11/slice-three-tab-nav-home-risk-entry-policy-clause) |
| Supercedes / extends | [docs/prd.md](../prd.md), [ui-overhaul.md](ui-overhaul.md). Nav destinations only; authoring shell, flows, and OSCAL stay. |
| Author | Product owner / this slice |
| Date | 2026-10-18 |

## Problem

The authoring chrome lists seven destinations: Workspace, Clauses, Catalog, Library, Risks, Export, Guide. On a phone the row wraps and overflows. Reviewers need two flows and a way home, not a second information architecture in the nav. Catalog, library, export, identified risks, and Guide still exist inside the flows.

## Users

- **Primary:** a GRC reviewer on desktop or a 390px-wide phone who starts from Home, Risk Entry, or Policy Clause.
- **Not this slice:** CLI users; anyone who needs a scored risk register; anyone changing OSCAL shape or the data model.

## Job to be done

See three quiet destinations, start the matching flow at step 1, and know which flow is current. On a narrow screen the three labels stay on one row.

## Scope

- In:
  - Replace the seven nav buttons with exactly **Home**, **Risk Entry**, and **Policy Clause**.
  - Home (rename of Workspace) returns to the marketing landing.
  - Risk Entry opens the risk-first flow at Identify risks (step 1) and stays current for that flow.
  - Policy Clause opens the clause-first flow at step 1 (paste) and stays current for that flow.
  - One-row nav at 390px: no wrap, no overflow.
  - Accessible names, current-item marking (`aria-pressed` / `aria-current`).
  - Keep catalog, library, identified-risks, export dialog, and Guide implementations for in-flow use (OSCAL from step 3, Insert from library).
- Out:
  - Deleting those features or their code paths.
  - Changing the project data model or OSCAL 1.1.2 export.
  - New outbound calls, AI keys, GRC Engineering Club branding.
  - Redesigning the marketing landing hero.

## Success criteria

- Given the authoring chrome, When the nav is shown, Then it has exactly three destinations: Home, Risk Entry, Policy Clause, and it does not list Catalog, Library, Risks, Export, or Guide.
- Given the nav, When Home is activated, Then the landing is shown.
- Given the nav, When Risk Entry is activated, Then Identify risks (step 1) opens and Risk Entry is the current item for that flow.
- Given the nav, When Policy Clause is activated, Then the clause paste step opens and Policy Clause is the current item for that flow.
- Given a 390px-wide viewport, When the nav is shown, Then the three items sit on one row with no wrap or overflow.
- Given step 3 or the statement editor, When the person exports OSCAL or inserts from the library, Then those paths still work.
- No new outbound calls. No keys written. Acme key and goldens unchanged.

## Design references

Web screens from Mobbin. Adapt to Codify's existing indigo / cool-gray workspace; do not copy branding.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Linear app shell (list + side panel) | https://mobbin.com/screens/b9104519-abc8-4638-a2fc-206bea260188 | Existing Codify Linear reference: quiet, few destinations. Keep the shell; shrink the nav to three items. |
| Linear — My issues compact tabs | https://mobbin.com/screens/a085c0e8-477c-4459-b2ee-25d5a4c0340a | Assigned / Created / Subscribed as a short one-row tab set. Adapt as Home / Risk Entry / Policy Clause. |

## Privacy and outbound calls

No new network call, origin, or leave-device path ([ADR 0003](../adr/0003-local-only-privacy-model.md)).

## Open questions

None.

## Decision log

- [ADR 0017](../adr/0017-three-tab-nav.md) — three primary destinations; refines [ADR 0007](../adr/0007-authoring-app-shell.md) nav list only.
