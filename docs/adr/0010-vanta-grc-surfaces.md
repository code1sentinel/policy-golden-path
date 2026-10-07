# 0010. Vanta-style GRC surfaces

Date: 2026-10-07

## Status

Accepted

## Context

The authoring shell ([ADR 0007](0007-authoring-app-shell.md)), local risk
register ([ADR 0008](0008-risk-input-and-oscal-tracing.md)), and
device-wide Statement library ([ADR 0009](0009-device-wide-statement-library.md))
are shipped. Andre reviewed Mobbin Vanta flows and asked Codify’s Risks,
Library, and Accept affordances to follow those GRC patterns — without
cloning Vanta branding or adding cloud GRC features.

A silent layout rewrite would blur the product model: Risks is still one
local register, Library is still `codify:statements`, Accept still upserts
that library. The IA change needs to be named so later slices do not
treat Library vs Register as a second catalog or a hosted risk library.

## Decision

Codify’s web surfaces adapt Vanta GRC *information architecture* on top of
the existing stores and Accept path:

- **Risks** has two sub-views of the same `project.risks` array:
  **Library** (scenarios, category pills, Add / Added / Remove) and
  **Register** (inherent heatmap, scored table, detail drawer). There is
  no hosted scenario catalog.
- **Recommended controls** appear in a focused modal or matching panel.
  Add / Accept call the existing `draft_risk_controls` action and the
  existing Accept → `library_upsert` path. Dismiss is local UI state.
- **Statement library** is a list plus a detail slide-over (statement,
  source / domain, OSCAL 1.1.2 refs). Use / Add / Remove keep today’s
  behaviour. The from-library dialog is a split list + preview.
- Visual language stays indigo on cool gray ([indigo-theme PRD](../prds/indigo-theme.md)),
  system fonts, and the current CSP. We do not load Vanta assets or add
  starter-guide / tests / vendors / trust-report chrome.

Static assets stay `index.html` / `app.css` / `app.js` / `theme.js`.
Privacy rules in [ADR 0003](0003-local-only-privacy-model.md) do not
change.

## Consequences

- e2e selectors for `#risk-templates`, `.risk-table`, `#risk-drawer`,
  `.library-row`, `.library-use`, and `.library-remove` stay valid.
- A later residual-risk or hosted-library slice needs its own ADR; this
  one does not add those fields.
- Removing a risk from Library **Remove** drops the register row only.
  Catalog controls and `codify:statements` are unchanged.
