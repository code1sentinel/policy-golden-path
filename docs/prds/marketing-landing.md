# PRD: Marketing landing (explain, then Get started)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | [COD-10](https://linear.app/code1sentinel/issue/COD-10/slice-marketing-landing-that-explains-codify-then-get-started) |
| Supercedes / extends | [docs/prd.md](../prd.md), [landing-flow-cards.md](landing-flow-cards.md), [landing-start.md](landing-start.md), [technical-policy-rego-label.md](technical-policy-rego-label.md) |
| Author | Product owner / this slice |
| Date | 2026-10-18 |

## Problem

The two equal flow cards assume the person already knows what Codify is for.
A first visit should read like a product site: what it does, how it works,
then one primary **Get started** into crafting. The two cards compete and
do not explain the product.

## Users

- **Primary:** a GRC reviewer opening Codify (Pages or `codify-web`) who
  needs to understand the product in seconds, then start writing control
  statements.
- **Also:** a returning reviewer with a saved `codify:project` who wants
  **Resume your project**.
- **Not this slice:** Identify risks page (COD-5 / PR #42), Develop
  controls, Review, Enact handoff, OSCAL export, or the sidebar Risks view.

## Job to be done

See that Codify turns identified risks or policy clauses into control
statements you can export as OSCAL and test as policy as code (Rego).
Press **Get started with identified risks** and land on the risk-first
Identify risks step. **Get started with an existing policy clause**
opens paste. Resume if this device already has a project.

## Scope

- In:
  - Replace the two-card landing with a marketing-style page. Primary look
    is Base (Basenames): a full-bleed saturated blue hero (`#0052FF`), a
    tiny square logo mark, a minimal nav with a Sign In–style text link,
    a centered interactive-feeling card, soft blurred floating chips
    around it, and **Scroll to explore** at the bottom of the hero. The
    rest of the page (How it works, feature cards, closing CTA, footer)
    follows the Family / Coinbase / Kraken secondary refs: generous
    whitespace, large type, one accent. Light and dark. Responsive.
    Accessible (semantic sections, skip link, focus states). No web fonts
    or CDNs.
  - Hero card: one concrete example end to end — risk *Customer data
    stored unencrypted*, then a control statement, a short OSCAL JSON
    snippet, then one Rego line (HTML/CSS only; no images from the web).
    Floating chips (4–6) are example risks and clauses. Two equal-weight
    start buttons sit under the card: primary **Get started with
    identified risks** (`#start-from-risks`) and a visible secondary
    **Get started with an existing policy clause** (`#start-from-clause`).
    **Private by design: runs in your browser** stays next to that pair.
    On a 390px screen the two buttons stack (risk above clause). Secondary
    **See how it works** (anchor to How it works). Headline *Turn risks
    and policy into controls you can test.* Subline: *Draft control
    statements from risks or policy clauses, export OSCAL, and ship them
    as policy as code.* Both sit above the card, in white on the blue.
  - Minimal nav on the blue: tiny square mark + Codify, Docs and GitHub
    as Sign In–style text links (not a filled Get started). **Resume your
    project** in that nav when a saved project exists.
  - How it works: three steps — Identify risks or pick a policy clause;
    Draft control statements; Export as OSCAL to Policy as code (Rego) in
    Enact — showing both starting points converge. Step 3 names **Enact**
    and links to https://github.com/code1sentinel/enact.
  - Plain-text line: *Works with frameworks like ISO 27001, SOC 2 and
    NIST* (no logos).
  - Contribute section: **Star or contribute on GitHub** (repo) and
    **Contribute a control template** (`CONTRIBUTING.md#control-templates`).
    No GRC Engineering Club branding.
  - Four feature cards: Risk-first or clause-first; Plain-language guides
    at every step; Standards-based OSCAL export; Private by design (runs
    in your browser, no AI keys stored).
  - Closing CTA band with **Get started** again, and a small footer (no
    club or version line).
  - Hero **Get started with identified risks** and the closing **Get
    started** open the existing risk-first path (Identify risks). Button
    id `#start-from-risks` stays on the hero primary. The CTA button has
    its own id. `#start-from-clause` is the secondary **Get started with
    an existing policy clause** button.
  - `#resume` / `#resume-open` stay. No Discard.
  - Hide the authoring sidebar and workspace top bar while the marketing
    landing is showing. Get started / Resume / clause paste restore the
    shell as today.
  - Hero blue is `#0052FF` in both light and dark. Copy, links, and the
    Get started fill on that field stay high-contrast (white type; white
    button with blue label). The mock card stays a light surface with dark
    type so the example remains readable. The page below the fold uses
    existing indigo-on-cool-gray tokens.
- Out:
  - Identify risks page, flow stepper, clause paste fields, Enact handoff,
    OSCAL, sidebar Risks view (COD-5 / PR #42).
  - New outbound calls, font hosts, CDNs, or AI keys.
  - Changing ADR 0013 path rules, coverage gates, or catalog shape.

## Success criteria

- Given a first visit with no saved project, When the page loads, Then
  the landing shows the Base-style blue hero (tiny square mark, Sign In–
  style Docs/GitHub, centered risk-to-control mock, floating chips, Get
  started under the card, Scroll to explore), How it works, feature cards,
  closing CTA, and footer, and does not show the two flow cards.
- Given the landing, When **Get started with identified risks** is
  activated, Then the identify-risks step opens.
- Given the landing, When **Get started with an existing policy clause**
  is activated, Then the existing paste form is shown (Codify / Try an
  example / Open a file).
- Given a saved `codify:project`, When the page loads, Then **Resume your
  project** is shown, and Resume opens the saved project on its existing
  path.
- Given the landing, When **See how it works** or **Scroll to explore**
  is activated, Then the How it works section is the target.
- Skip-to-content still targets `#main`. Hero text and the Get started
  control meet contrast on `#0052FF` in light and dark. No new outbound
  origins or font hosts. No AI keys written.

## Design references

**Required.** Opened and used before implementation. Do not copy vendor
branding. No web fonts.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| **Primary — Base (Basenames)** | https://mobbin.com/screens/e4a9a595-c9fd-40eb-b78c-a87f8a7f5597 | Full-bleed saturated blue (`#0052FF`); tiny square mark top-left; only a Sign In–style text link top-right; centered interactive card; soft blurred floating chips; **Scroll to explore** at the bottom. Codify’s card is a risk → control mock; chips are example risks and clauses. |
| Sentry — two hero CTAs | https://mobbin.com/screens/b74cbcc7-12b5-4b98-be43-027a776e6ef3 | Two equal-weight start buttons: filled primary next to an outlined secondary. |
| Customer.io — Get started + Book a demo | https://mobbin.com/screens/c82a750f-4a32-486a-97c9-cdc95db1463b | Filled primary + outlined secondary with a quiet trust line under the pair. |
| Dropbox Dash — stacked CTAs | https://mobbin.com/screens/b59243e8-9c21-4120-9e4f-eee85c834d5c | Primary over outlined secondary, stacked on a narrow screen. |
| Coinbase — marketing hero (secondary) | https://mobbin.com/screens/8569c23a-5805-4014-917b-fa7685ee8773 | Large product headline and short subhead above the visual. |
| Family — centered hero with feature cards (secondary) | https://mobbin.com/screens/2a5126c9-091d-4870-b52a-12f586941c75 | Generous whitespace and a row of feature cards below the hero. |
| Kraken — hero with trust/stat strip (secondary) | https://mobbin.com/screens/5c032e77-cca1-456e-8180-41c589e2849d | Quiet trust strip (Codify: on-device, OSCAL 1.1.2, no AI keys stored — not vanity metrics). |

## Privacy and outbound calls

No new network call, origin, or leave-device path
([ADR 0003](../adr/0003-local-only-privacy-model.md)). Docs and GitHub in
the top bar are user-clicked navigations, not asset loads (same as the
Enact link). Keys stay in the browser. `codify:project`,
`codify:statements`, and `codify:theme` are unchanged.

## Open questions

None.

## Decision log

Authoring paths stay [ADR 0013](../adr/0013-risk-first-authoring-flow.md).
No new ADR: this is the first-visit chrome, not a new leave-device path
or catalog shape. The marketing hero uses Base blue `#0052FF`; the
authoring app keeps the indigo tokens from
[indigo-theme.md](indigo-theme.md).
