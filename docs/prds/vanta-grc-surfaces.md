# PRD: Vanta-style GRC surfaces

| Field | Value |
| --- | --- |
| Status | Agreed for Statement library surfaces. Risks Library/Register superseded by [remove-risk-register.md](remove-risk-register.md) / [ADR 0011](../adr/0011-no-risk-register.md) |
| Slice issues | Listed in the PR; this agent cannot open GitHub issues. |
| Supercedes / extends | [docs/prd.md](../prd.md), [ui-overhaul.md](ui-overhaul.md), [risk-to-controls.md](risk-to-controls.md), [statement-library.md](statement-library.md) |
| Author | Andre (product owner) / this slice |
| Date | 2026-10-07 |

## Problem

Risks and Library already do the product job (local register → templates →
Accept → device-wide statements → Export). The surfaces still read as a
developer table plus a drawer, not as the GRC SaaS patterns Andre picked
from Mobbin after reviewing Vanta: a risk **library** vs **register**, a
focused “add recommended controls” moment, and a control list with a
detail slide-over.

## Users

- **Primary:** a GRC reviewer already using Codify’s Draft / Risks /
  Library / Accept / Export path.
- **Secondary:** the same person on GitHub Pages or `codify-web`.
- **Not this slice:** anyone who needs Vanta’s cloud GRC (tests, vendors,
  trust report, residual-risk workflow, live scoring).

## Job to be done

Work the same local risks and accepted statements, but in a layout that
matches familiar GRC IA: pick a scenario, add recommended controls,
inspect a statement in a detail panel, export the catalog.

## Scope

- In:
  - Risks secondary nav: **Library** (scenario table, category pills,
    Add / Added / Remove) and **Register** (heatmap + identified-risk
    table + detail drawer). Same local `project.risks`; no second store.
  - Recommended control statements in a focused modal (from Library
    **Add**) and a matching panel on the register drawer. Primary
    Accept / Add and dismiss. Wired to the existing
    `draft_risk_controls` → Accept → `codify:statements` path.
  - Library view: statement list + detail slide-over (description,
    source / domain, OSCAL 1.1.2 refs, Use / Add / Remove).
  - From-library picker as a split list + preview.
  - Visual language: clean GRC tables, status/category pills, soft cards,
    indigo accent on the existing cool-gray tokens. Draft, Catalog, and
    Export stay coherent.
  - Light / dark / system, system fonts, existing CSP, privacy chrome.
- Out:
  - New product behaviour: FAIR, residual risk, IM8 or other external
    catalogs, cloud sync, tests / vendors / trust report, starter-guide
    chrome, Vanta branding.
  - New outbound origins, fonts, or leave-device paths.
  - Changing clause-only input, OSCAL 1.1.2 shape, or library schema.
  - Rewriting the authoring shell or splitting `static/` into modules.

## Success criteria

- Given risks on this device, When the person opens Risks, Then they can
  switch Library vs Register without a new upload or store.
- Given a risk in Library, When they choose **Add**, Then recommended
  control statements appear in a focused modal; **Accept** / **Add**
  still create catalog controls and upsert the Statement library.
- Given accepted statements, When they open Library, Then a list and a
  detail slide-over show the statement, source, and OSCAL 1.1.2 refs;
  **Use** / **Remove** still behave as today.
- Given Draft or Export, When they return there, Then the visual language
  matches (pills, tables, indigo) and localStorage keys are unchanged.
- CI green. No new outbound. No keys written.

## Design references

Adapt the patterns. Do not copy Vanta branding or cloud-only chrome.
Attached captures live at `mobbin-codify-fit/01`–`06`.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Adding recommended controls | https://mobbin.com/flows/7bfc9f26-e71e-421d-ad46-ab10c73edf67 | Focused modal: scenario, recommended statements, Not now / Add controls. |
| Risk library + register | https://mobbin.com/flows/fe48d77f-a607-4141-8092-61b73d4a864c | Secondary Library vs Register; scenario table; category pills; Add / Added / Remove; heatmap register. |
| Add a control (split picker) | https://mobbin.com/flows/539b1513-fc0c-4085-929a-4aea4c453860 | List + preview picker when choosing a library statement. |
| Framework / control detail | https://mobbin.com/flows/280ae4f2-78b0-4e33-8ba3-b72c8c7685a8 | Control list + slide-over: description, domain, framework refs, Add. |

## Privacy and outbound calls

No new network calls, origins, or leave-device paths. Risks and statements
stay in `codify:project` and `codify:statements`. API keys stay out of
both. CSP `connect-src` is unchanged. System font stack only.

## Open questions

- None. Residual risk and Vanta cloud features stay out.

## Decision log

- [ADR 0010](../adr/0010-vanta-grc-surfaces.md) — GRC surfaces adapt Vanta
  IA on top of the existing shell, register, and library.
