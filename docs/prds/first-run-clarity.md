# PRD: First-run clarity for GRC reviewers

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Product-owner walkthrough of the live site (2026-10-08). This agent cannot open GitHub issues; acceptance criteria live here. |
| Supercedes / extends | [docs/prd.md](../prd.md), [start-hero-empty-states.md](start-hero-empty-states.md), [welcome-splash.md](welcome-splash.md), [oscal-panel-export.md](oscal-panel-export.md), [vanta-grc-surfaces.md](vanta-grc-surfaces.md) |
| Author | Walkthrough findings / this slice |
| Date | 2026-10-08 |

## Problem

A first-time GRC user (not a developer) on the live Pages site hit two
bugs and several copy/IA problems: a literal `null` in the workspace
header, a Risks breadcrumb that reads like Library / Register, counts
that look like a loss of clauses, a grey placeholder that is not
submittable, duplicate Accept actions, unexplained review jargon, a
mismatched “Say why” example, an export list with no default, and no
glossary for OSCAL / Catalog / Library.

## Users

- **Primary:** a GRC reviewer opening Codify for the first time to paste
  a clause or try the example.
- **Not this slice:** CLI users, AI-provider setup, residual-risk
  workflow, or a redesign of the indigo workspace.

## Job to be done

Paste a clause or load the example, understand what Codify drafted,
accept a control, and export the catalog — without developer jargon
blocking the path.

## Scope

- In:
  - Fix the workspace summary `null`.
  - Honest clause / control counts.
  - Real, editable example text in the paste box; a short “here’s what
    we drafted” result step after paste or Try an example.
  - One primary Accept; secondary review actions labelled.
  - Plain-language review labels, score, parts, and `[N]` blanks.
  - Purpose hints that match the statement (or stay neutral).
  - Export: one Recommended option and a use-when line per format.
  - Dotted-underline glossary for OSCAL and related terms; Catalog vs
    Library distinction.
- Out:
  - Changing `codify:project` / `codify:statements` / `codify:splash-seen`.
  - New outbound calls, fonts, or CDNs.
  - Changing splash behaviour. The risk register was later removed
    ([ADR 0011](../adr/0011-no-risk-register.md)).
  - Welcome splash behaviour.

## Success criteria

- Given the Acme example, When the workspace header renders, Then it
  does not contain the text `null` and it explains drafts vs
  requirements vs other clauses.
- Given the sidebar, When it renders, Then there is no Risks destination
  (the register was removed; [ADR 0011](../adr/0011-no-risk-register.md)).
- Given the start view, When it is shown, Then the paste box contains
  real editable example text (not only a placeholder) and Codify
  converts that text.
- Given a paste or Try an example, When conversion finishes, Then a
  result step summarises what was drafted before the 3-pane workspace.
- Given control review, When the editor and properties render, Then
  there is one primary Accept and review jargon has a plain-language
  line.
- Given an access-control statement missing purpose, When it is
  scored, Then the hint is not the brute-force password example.
- Given Export, When the dialog opens, Then OSCAL is marked
  Recommended and each row has a use-when line.
- Glossary tooltips exist for OSCAL and the flow pills. No new
  outbound calls. Existing stores unchanged.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| A1 Mixpanel sample dataset | https://mobbin.com/screens/65625dbf-4bb2-4c68-b8e2-f895db497249 | Load a real sample, not grey fake text |
| A2 Twingate onboarding result | https://mobbin.com/screens/491b7913-781c-4596-876d-998856d75a86 | “Here’s what we made” before the full app |
| A3 Notion prefilled welcome | https://mobbin.com/screens/c237ff84-9781-4b8d-a530-0c0752322c0a | Real editable starter content |
| B1 Klaviyo review submission | https://mobbin.com/screens/02359910-64f7-4f23-8280-f1bf18c8e95f | Per-section status, inline missing X, one primary |
| B2 Customer.io review | https://mobbin.com/screens/1bf2ba3d-44c9-4580-b59e-ced6656114ba | Field-level fix prompts |
| B3 Square review promotion | https://mobbin.com/screens/7da1615c-0436-415b-b992-ff64a472a95f | “Why this?” + single primary |
| B4 Contra profile completion | https://mobbin.com/screens/33f72505-df46-40ac-a916-3b649be52606 | Score explanation + missing checklist |
| C1 Square export recommended | https://mobbin.com/screens/469e75a3-e1b7-4c59-8387-0801e4c10294 | “(recommended)” + use-when per format |
| C2 Pitch export cards | https://mobbin.com/screens/fe97c269-f702-4dfe-8185-55a1f6cbbf6c | Preselected default |
| C3 Typeform download helper | https://mobbin.com/screens/e2f9772f-62e2-49aa-8913-cf0a18bd0292 | Helper text per format |
| F1 Square dotted-term tooltip | https://mobbin.com/screens/afbe8fd9-3b5e-4075-837a-9deb79d16841 | Glossary tooltip |

Adapt the patterns to Codify's existing dark indigo workspace. Do not
copy branding.

## Privacy and outbound calls

No new network call, origin, or leave-device path. AI keys stay in the
browser. Splash / project / statement keys are unchanged.

## Open questions

None. The walkthrough listed the findings and the Mobbin screens.

## Decision log

None. Layout and copy; no ADR.
