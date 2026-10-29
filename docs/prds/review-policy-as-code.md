# PRD: Review & Policy as code (Rego) handoff (step 3)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | [COD-9](https://linear.app/code1sentinel/issue/COD-9/review-and-policy-as-code-rego-handoff-page-step-3) |
| Supercedes / extends | [docs/prd.md](../prd.md), [rego-starter.md](rego-starter.md), [technical-policy-rego-label.md](technical-policy-rego-label.md), [risk-first-authoring-flow.md](risk-first-authoring-flow.md) (this page’s chrome and the web export gate) |
| Author | Product owner / this slice |
| Date | 2026-10-24 |

## Problem

Step 3 is still two leftover surfaces: the three-pane workspace **Review**
(Accept, score, parts) and a **Send to Enact** card. First-time reviewers
do not know what Enact is. They cannot see a coverage checklist, jump back
to edit a section, or read the catalog they will hand off. COD-13 added
**Generate Rego starter** onto the Enact card; the page around it still
reads as a wizard leftover, not the last calm step.

## Users

- **Primary:** a GRC reviewer who has written control statements (from
  identified risks or pasted clauses) and needs to check coverage, take a
  Rego starter, and download the OSCAL catalog.
- **Not this slice:** scoring, owners, registers, AI drafting, changing
  treats-risk / OSCAL tracing, or running policy inside Codify.

## Job to be done

On one calm page, confirm every risk or clause has a control statement,
generate a Rego starter to review, and download the OSCAL catalog — with
Enact named only as where that catalog opens.

## Scope

- In:
  - Redesign **only** the last authoring step (shared by both start
    paths). User-facing label: **Policy as code (Rego)**.
  - Small step indicator: 1 Identify risks / Policy clause, 2 Control
    statements, 3 Policy as code (Rego), plus a Back link. Hide the
    wizard Previous / Next and What / Why guide on this page (same as
    steps 1 and 2).
  - **Review summary** at the top: counts, a coverage banner, and a list
    of risks (path A) or clauses (path B) → their control statements,
    each marked covered or missing. Per-section **Edit** jumps back to
    Risk Entry / Policy Clause / Control statements without losing the
    `codify:project` draft.
  - **Policy as code (Rego)** section: keep COD-13 **Generate Rego
    starter**, format picker (Rego default; Sentinel / Checkov optional),
    read-only code, Copy / Download, and “starter to review, not
    finished” copy. No GRC Engineering Club branding.
  - **OSCAL catalog** section: read-only JSON preview, **Copy**,
    **Download** `.json`. Primary action **Download OSCAL catalog**,
    disabled until review is complete. Supporting caption **Opens in
    Enact** (existing Enact Pages link). Other formats stay in the
    export dialog.
  - Review complete / web export gate: every identified risk has at
    least one non-empty control statement, and every non-empty control
    is linked to a risk. Accept is not required for this handoff
    (refines [ADR 0013](../adr/0013-risk-first-authoring-flow.md)).
  - Identified risks stay OSCAL risk entries; each control stays linked
    to the risk it treats. COD-13 back-matter `rel=policy-as-code`
    unchanged.
  - Saved `flowStep: "enact"` resumes on this page.
- Out:
  - Removing Generate Rego starter, changing templates, or running
    policy in Codify.
  - Redesigning Identify risks, Policy clause, Control statements, or
    the three-pane workspace (Accept / score still exist for catalogs
    and the demo editor).
  - Dropping the clause-path **Link to risks** step.
  - New outbound calls, font hosts, or AI keys.
  - GRC Engineering Club branding.

## Success criteria

- Given Flow A after every risk has a statement, When they continue,
  Then step 3 shows the three-step indicator (step 3 current), a Back
  link, the title **Policy as code (Rego)**, a review summary with
  counts and covered rows, the Rego starter section, an OSCAL JSON
  preview, and an enabled **Download OSCAL catalog** with **Opens in
  Enact**. Enact is not the page title. The page does not name the GRC
  Engineering Club.
- Given a missing statement or an unlinked control, When step 3
  renders, Then the banner says review is incomplete and the primary
  download is disabled.
- Given the review summary, When they activate **Edit** on risks,
  clauses, or control statements, Then that earlier step opens and the
  draft is still in `codify:project`.
- Given a control on step 3, When they choose **Generate Rego starter**,
  Then Copy and Download still work (COD-13). The catalog still attaches
  the starter as back-matter `rel=policy-as-code` and stays NIST OSCAL
  1.1.2.
- Given a complete review, When they Copy or Download the OSCAL
  preview, Then the JSON is this project’s catalog (identified risks
  present; each control linked to the risk it treats). Download is
  local only.
- Given Flow B after statements and linking, When they reach step 3,
  Then the summary lists clauses → statements and the same Rego +
  OSCAL sections.
- No new outbound calls. No keys written.

## Design references

Opened and used before implementation. Adapt to Codify’s indigo /
cool-gray shell. Do not copy vendor branding.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Hotjar — Review your project details | https://mobbin.com/screens/746627e4-0ee6-4612-ab41-be720e1658f4 | Pre-send checklist: sections with an Edit control each |
| Contra — IN REVIEW banner | https://mobbin.com/screens/ee4e504c-c5f0-4210-8441-c7d7ada4e504 | Quiet status banner for review completeness |
| Firecrawl — JSON Response | https://mobbin.com/screens/65454e8d-1548-439b-b3ff-36bd14310874 | Read-only JSON with Copy as JSON and download |
| Klaviyo — Copy JSON payload | https://mobbin.com/screens/95dff8a0-6f15-4b0c-8436-fb7ad4ef7a95 | Sample payload + Copy JSON |
| Browserbase — JSON + copy | https://mobbin.com/screens/ae95ee59-43fe-4173-887a-c3542d08c9c8 | Existing Codify numbered JSON + Copy |
| GitLab — shared snippet | https://mobbin.com/screens/37dfd77e-5d72-41c0-b2c0-01c1afe78c55 | COD-13: read-only code with copy and download |
| Relume — component code | https://mobbin.com/screens/b2e28cc0-3db1-4e21-adfc-378e9a859787 | COD-13: dark code panel, language tabs, Copy |
| Hashnode — guide snippet | https://mobbin.com/screens/6b48b2bd-4daf-42c4-926f-8037314a0042 | COD-13: language picker and Copied status |

## Privacy and outbound calls

No new network call, origin, or leave-device path
([ADR 0003](../adr/0003-local-only-privacy-model.md)). Preview, copy,
download, and Rego generation stay on this device. The Enact link is the
same user-chosen `<a href>` already used on this step.

## Open questions

None.

## Decision log

- [ADR 0020](../adr/0020-review-policy-as-code-page.md) — step 3 is one
  Review + Policy as code page; web export is gated on coverage, not
  Accept.
