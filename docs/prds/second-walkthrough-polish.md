# PRD: Second first-time walkthrough polish

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Product-owner walkthrough of current `main` after PRs #29 and #30. This agent cannot open GitHub issues; acceptance criteria live here. |
| Supercedes / extends | [docs/prd.md](../prd.md), [first-run-clarity.md](first-run-clarity.md), [remove-risk-register.md](remove-risk-register.md) |
| Author | Walkthrough findings / this slice |
| Date | 2026-10-09 |

## Problem

A second first-time GRC walkthrough of the live product (after first-run
clarity and risk-register removal) still blocked the happy path: Accept
did not look accepted, the stage strip looked clickable, the review
pane repeated the same parts and purpose hint, an accepted control still
read as incomplete, `[N]` blanks were unexplained, counts and glossary
terms hid behind hover, Export still talked about a “save file” and
showed two library downloads as peers of OSCAL, Workspace jumped back
into the open project, pasted work was named “pasted text”, and Library
listed the same statement twice.

## Users

- **Primary:** a GRC reviewer opening Codify for the first time to paste
  a clause, accept a control, and export the catalog.
- **Not this slice:** CLI users, AI-provider setup, or a redesign of the
  indigo workspace. No risk register.

## Job to be done

Paste a clause, understand the drafts, accept one control, fill any
`[N]` blank, and download the catalog — without contradictory status,
hidden explanations, or surprise navigation.

## Scope

- In:
  1. Clear accepted state: **Accepted ✓** plus **Next control** as the
     primary; **Undo accept** returns the control to draft.
  2. Clause / Draft / Review / Accept strip reads as status, not links
     (tooltips may stay).
  3. Action / Scope / Limit / Purpose and “Say why this control exists”
     each appear once on the review screen.
  4. After Accept, keep the score; label remaining gaps as optional
     improvements so the screen is not contradictory.
  5. Unfilled `[N]` (and similar) placeholders are highlighted “set this
     value” prompts with a one-line hint and an easy fill.
  6. Count breakdown is visible or one click away. First-look lists
     Draft 1–3 and “and N more” when there are more.
  7. Short visible lines for OSCAL and Catalog vs Library where a
     first-timer meets them (tooltips stay).
  8. Export: no “save file” wording; OSCAL is the obvious download;
     the two statement-library formats are grouped and de-emphasised.
  9. Sidebar **Workspace** opens the start/paste view. Pasted projects
     get a name from the first clause (or “Untitled policy”) that the
     person can rename.
  10. Library shows each statement once.
- Out:
  - Reintroducing a risk register, Risks nav, or register export.
  - Changing `codify:project` / `codify:statements` / `codify:splash-seen`.
  - New outbound calls, fonts, or CDNs.
  - Removing “the risk it treats” purpose wording, **Guidance, risk,
    who**, or the Guide’s risk-statement practice (they describe a
    control’s purpose, not a register).
  - Welcome splash behaviour.

## Success criteria

- Given a draft, When the person presses Accept, Then the primary
  action is **Next control**, a visible **Accepted ✓** state is shown,
  and **Undo accept** returns it to draft.
- Given the workspace header, When it renders, Then the Clause / Draft /
  Review / Accept strip is status (not a control) and the type
  breakdown is visible or one click away.
- Given the review editor, When parts and suggestions render, Then
  Action / Scope / Limit / Purpose appears once and “Say why this
  control exists” appears once.
- Given an accepted control that still lacks purpose, When it is shown,
  Then the score remains and remaining gaps are labelled optional.
- Given a draft with `[N]`, When the editor opens, Then a highlighted
  set-this-value prompt is visible and filling it updates the statement.
- Given more than three drafts, When the first-look card renders, Then
  it lists Draft 1–3 and “and N more”.
- Given Catalog, Library, Export, or the OSCAL JSON tab, When a
  first-timer lands there, Then a visible line explains the term
  (tooltips may remain).
- Given Export, When the dialog opens, Then it does not say “save
  file”, OSCAL is the recommended download, and library JSON/CSV sit
  in a grouped optional section.
- Given an open project, When the person clicks Workspace, Then they
  see the start/paste view (with the current policy named). A paste
  without a `#` title is not named “pasted text”.
- Given one accepted statement in Library, When the page renders, Then
  that statement’s wording is shown once.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| B1 Klaviyo review submission | https://mobbin.com/screens/02359910-64f7-4f23-8280-f1bf18c8e95f | Per-section status, one primary action |
| B2 Customer.io review | https://mobbin.com/screens/1bf2ba3d-44c9-4580-b59e-ced6656114ba | Field-level fix prompts for `[N]` |
| B4 Contra profile completion | https://mobbin.com/screens/33f72505-df46-40ac-a916-3b649be52606 | Score + missing checklist shown once |
| C1 Square export recommended | https://mobbin.com/screens/469e75a3-e1b7-4c59-8387-0801e4c10294 | One recommended download; extras grouped |
| A2 Twingate onboarding result | https://mobbin.com/screens/491b7913-781c-4596-876d-998856d75a86 | Summary with counts and “more” |
| F1 Square dotted-term tooltip | https://mobbin.com/screens/afbe8fd9-3b5e-4075-837a-9deb79d16841 | Glossary tooltip plus a visible line |

Adapt the patterns to Codify’s existing dark indigo workspace. Do not
copy branding.

## Privacy and outbound calls

No new network call, origin, or leave-device path. AI keys stay in the
browser. Splash / project / statement keys are unchanged.

## Open questions

None. The walkthrough listed the findings and the Mobbin screens.

## Decision log

Keep control-purpose “risk it treats” copy ([ADR 0011](../adr/0011-no-risk-register.md)).
No new ADR.
