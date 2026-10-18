# PRD: Two flow cards on the landing + OSCAL risk statements

| Field | Value |
| --- | --- |
| Status | Superseded by [marketing-landing.md](marketing-landing.md) |
| Slice issues | Acceptance criteria live here (this agent cannot open GitHub issues). |
| Supercedes / extends | [docs/prd.md](../prd.md), [landing-start.md](landing-start.md), [identified-risks-as-input.md](identified-risks-as-input.md) |
| Author | Product owner / this slice |
| Date | 2026-10-15 |

## Problem

The #39 landing still has a headline, a shared converging diagram, ledes,
examples, Recommended kickers, a docs link, and Open a saved project.
The two paths are the product; everything else gets in the way.

Identified risks already trace in the catalog (`identified-risk-id`,
`treats-risk`, `rel=related`) but the back-matter resource is only a
title/description copy of the statement. Export should carry
assessment-style risk fields (title, description/statement, status)
that stay valid against the OSCAL 1.1.2 **catalog** schema.

## Users

- **Primary:** a GRC reviewer opening Codify who should see only the two
  flows and start one of them.
- **Also:** a returning reviewer with a saved `codify:project` who wants
  a quiet Resume.
- **Also:** anyone who exports a catalog and opens it in Enact or another
  OSCAL 1.1.2 reader.
- **Not this slice:** changing the two authoring paths after Get started
  (PR #38 / [ADR 0013](../adr/0013-risk-first-authoring-flow.md)), the
  workspace, Catalog, Library, Risks input panel, or Enact handoff.

## Job to be done

Pick a flow from two equal cards and go straight into its first step.
Export identified risks as catalog-valid, assessment-style risk
statements that the control statements still link to.

## Scope

- In:
  - Landing shows **only** two side-by-side flow cards:
    - Flow A: Identify risk → Control statement (→ Enact)
    - Flow B: Policy clause → Control statement (→ Enact)
  - Each card: one-line title, a mini step diagram, one **Get started**
    button that opens that path's first step (identify-risks, or clause
    paste). Button ids stay `#start-from-risks` and `#start-from-clause`.
  - A small, unobtrusive **Resume** link when a saved project exists.
    No Discard, docs link, Open a saved project, Recommended kicker,
    lede, example, shared headline, or shared diagram above the cards.
  - OSCAL export: each identified risk is a catalog `back-matter`
    resource with a short `title`, `description` (the statement), and
    Codify-namespace props `identified-risk-id`, `statement`,
    `status=open`, and `note` when present. Controls keep
    `treats-risk` and `rel=related`. Status is export-only, not a
    register field on `project.risks`.
  - Golden + unit assertions + CI `oscal-schema` on the identified-risk
    catalog. Older catalogs without `statement`/`status` props still
    restore `{id, statement, note?}`.
- Out:
  - Restructuring the sidebar, workspace, flow stepper, clause paste
    form, or Enact handoff.
  - First-class `risk` / `statement` / `status` keys on the catalog
    resource (the catalog schema forbids them).
  - Reviving a risk register (scores, owners, likelihood, `--risks`).
  - New outbound calls, font hosts, CDNs, or AI keys.

## Success criteria

- Given a first visit with no saved project, When the page loads, Then
  the landing shows only the two flow cards (one-line title, mini
  diagram, **Get started** each) and no headline, shared diagram, docs
  link, or Open a saved project.
- Given the landing, When Flow A's **Get started** is activated, Then
  the identify-risks step opens.
- Given the landing, When Flow B's **Get started** is activated, Then
  the existing paste form is shown (Codify / Try an example / Open a
  file).
- Given a saved `codify:project`, When the page loads, Then the same
  two cards are shown with a small **Resume** link, and Resume opens
  the saved project on its existing path.
- Given a project with an identified risk linked to a control, When the
  catalog is exported, Then the risk resource has title,
  description/statement, and status, the control still has
  `treats-risk` and `rel=related`, and the catalog is valid OSCAL 1.1.2.
- Given an older Codify catalog that only has title + description +
  `identified-risk-id`, When it is opened, Then `project.risks` restores
  as today.
- Skip-to-content still targets `#main`. No new outbound origins or
  font hosts. No AI keys written.

## Design references

Same Mobbin screens as [landing-start.md](landing-start.md). Opened and
used before implementation. Adapt hierarchy to Codify’s indigo-on-cool-gray
tokens. Do not copy vendor branding.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Sprig — start cards | https://mobbin.com/screens/77add735-ba8c-4f49-a512-fabd8b2e1826 | Two large equal start cards as the only primary. |
| Klaviyo — headline + flow | https://mobbin.com/screens/88633529-5820-4f59-93e0-98d0806ad4fd | Simple node flow (now a mini diagram **on** each card, not above them). |
| Microsoft Copilot — How it works | https://mobbin.com/screens/ebac045b-3c68-4dd0-8811-1ce2a31aaf05 | Centered steps, generous whitespace, one idea per card. |
| fal — path choice | https://mobbin.com/screens/484439bd-e04c-4d68-b977-acfc6937eebe | Two path cards as the only primary; quiet secondary (Resume) under them. |

Related screens opened while checking those citations (same patterns;
not used as the source of layout): Higgsfield two-path cards, Uxcel
recommended vs alternative cards, Braintrust “let’s get started” pair.

## Privacy and outbound calls

No new network call, origin, or leave-device path
([ADR 0003](../adr/0003-local-only-privacy-model.md)). Keys stay in the
browser. `codify:project`, `codify:statements`, and `codify:theme` are
unchanged.

## Open questions

None.

## Decision log

[ADR 0014](../adr/0014-oscal-identified-risk-statements.md) refines
[ADR 0012](../adr/0012-identified-risks-as-input.md) for assessment-style
risk fields on catalog back-matter resources. The two authoring paths
stay [ADR 0013](../adr/0013-risk-first-authoring-flow.md).
