# Retro: Vanta-style GRC surfaces

| Field | Value |
| --- | --- |
| Date | 2026-10-07 |
| Feature / PRD | [docs/prds/vanta-grc-surfaces.md](../prds/vanta-grc-surfaces.md) |
| Slices / PRs | This feature PR |

## What we shipped

Risks gained Library vs Register sub-views of the same local register,
a recommended-controls modal wired to Accept → `codify:statements`, and
category pills. The Statement library is a list plus a detail slide-over.
From-library is a split picker. No new stores, origins, or product flows.

## What went well

- Andre’s Mobbin Vanta flows mapped onto existing Accept / draft_risk_controls
  without a second catalog.
- Keeping `#risk-templates`, `.risk-table`, and `.library-row` meant the
  prior e2e path stayed green while the new modal/detail tests landed.

## What was painful

- Auto-opening the recommend modal after import would block the AI-chip
  e2e (`#ai-open` behind a modal). Templates stay in the register drawer
  as well as the modal.
- Library vs Register is two presentations of one `project.risks` array.
  Easy to over-build into a hosted scenario catalog; ADR 0010 forbids that.

## Lessons to fold into the templates

| Lesson | Template to change |
| --- | --- |
| A focused modal must not block existing chrome (AI chip, nav) on the default path. | Follow-up; noted here |
| IA-only slices still need an ADR when they could be misread as a new store. | This ADR |

## Follow-ups

- Residual-risk / FAIR remains out (ADR 0008).
- Screenshots for the PR when the local app is exercised.
