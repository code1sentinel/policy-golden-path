# 0017. Three-tab primary nav

Date: 2026-10-18

## Status

Accepted

Refines [0007-authoring-app-shell.md](0007-authoring-app-shell.md): the authoring shell (collapsible sidebar on desktop, top bar, writing column, properties) stays. The **nav destinations** in that sidebar are now Home, Risk Entry, and Policy Clause. Catalog, Library, Risks, Export, and Guide are not nav tabs.

Does not change [0009-device-wide-statement-library.md](0009-device-wide-statement-library.md), [0012-identified-risks-as-input.md](0012-identified-risks-as-input.md), [0013-risk-first-authoring-flow.md](0013-risk-first-authoring-flow.md), [0016-control-statements-page.md](0016-control-statements-page.md), or OSCAL 1.1.2 ([0002](0002-oscal-1-1-2.md)). Those surfaces remain reachable from inside the flows.

## Context

ADR 0007 put Workspace, Clauses, Catalog, Export, and Guide in a left sidebar (Library in 0009; a Risks tab later came and went with the register). On viewports at or under 980px that sidebar becomes a wrapping top row. Seven items wrap and overflow on a 390px phone.

The product has two start paths (ADR 0013) plus a landing. Extra destinations (catalog table, library page, standalone risks, export, Guide) are still used from step 3, Insert from library, and per-step guides. They do not need a top-level tab.

## Decision

The local web app and the Pages site share one **primary nav** of three destinations:

1. **Home** — the marketing landing (the former Workspace start).
2. **Risk Entry** — risk-first flow, Identify risks (step 1). Stays current while that flow is open.
3. **Policy Clause** — clause-first flow, step 1 (paste capture page). Stays current while that flow is open.

On a 390px-wide screen the three labels sit on one row (no wrap, no overflow). The current item is exposed to assistive tech (`aria-pressed` and `aria-current="page"`).

Catalog, statement library, identified-risks input, the export dialog, and Guide remain in the app for in-flow use. They are not listed in the nav. The data model and OSCAL catalog export do not change.

## Consequences

- e2e selectors that clicked Catalog, Library, Risks, Export, or Guide as nav tabs move to remaining surfaces (Risk Entry / Policy Clause / Home, Insert from library, export from the toolbar or Send to Enact).
- Opening the library page or catalog table from a tab is gone; Accept still upserts the device library; Insert from library and the export dialog still work.
- Re-adding those destinations as top-level tabs needs an ADR that supersedes this one.
