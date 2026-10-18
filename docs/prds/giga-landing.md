# PRD: Giga-style landing restyle

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | [COD-12](https://linear.app/code1sentinel/issue/COD-12/slice-restyle-landing-after-gigaai-short-hero-proof-trust-strip) |
| Supercedes / extends | [docs/prd.md](../prd.md), [marketing-landing.md](marketing-landing.md), [three-tab-nav.md](three-tab-nav.md) |
| Author | Product owner / this slice |
| Date | 2026-10-18 |

## Problem

The Base-style full-bleed blue hero, floating chips, three How it works
cards, and four feature cards read as a long marketing page. Andre
wants the first visit to feel like [giga.ai](https://giga.ai): a short
confident headline, lots of whitespace, a product visual just below,
one proof, a trust-badge strip, and a clean closing CTA — adapted to
Codify, not cloned.

## Users

- **Primary:** a GRC reviewer opening Codify (Pages or `codify-web`) who
  needs to understand the product in seconds, then start writing control
  statements.
- **Also:** a returning reviewer with a saved `codify:project` who wants
  **Resume your project**.
- **Not this slice:** Identify risks, control statements, Review, Enact
  handoff, OSCAL export, or the authoring nav destinations.

## Job to be done

See that Codify turns identified risks or policy clauses into control
statements you can export as OSCAL and test as Rego. Press **Get
started with identified risks** or **Get started with an existing
policy clause**. Resume if this device already has a project.

## Scope

- In:
  - Restyle the marketing landing after giga.ai: short punchy headline
    (*Controls you can test.*), one subline (risks or policy clauses
    become control statements; OSCAL and Rego), lots of whitespace, a
    strong hero, the existing risk → control → OSCAL → Rego example
    just below the start actions, a single factual how-it-works /
    principle section (not a testimonial), a trust-badge strip, and a
    clean closing CTA.
  - Keep the two equal start buttons exactly: **Get started with
    identified risks** (`#start-from-risks`, path A step 1) and **Get
    started with an existing policy clause** (`#start-from-clause`,
    path B step 1), plus **Private by design**. Stack the pair on a
    390px screen.
  - Trust strip in giga's badge style with honest claims only:
    frameworks supported (NIST 800-53, ISO 27001), OSCAL 1.1.2, runs
    in your browser, no data leaves your device. Do not claim SOC 2 or
    ISO certifications.
  - Keep the 3-tab authoring nav (Home, Risk Entry, Policy Clause), the
    Enact link, and the contribute links. No GRC Engineering Club
    branding.
  - Drop the Base-style full-bleed `#0052FF` hero, floating chips, and
    **Scroll to explore**. Light and dark. Responsive. Accessible
    (semantic sections, skip link, focus states). System fonts only.
  - `#resume` / `#resume-open` stay. Hide the authoring sidebar and
    workspace top bar while the landing is showing.
- Out:
  - Cloning giga.ai copy, assets, or branding.
  - Fake testimonials or certification claims.
  - Changing ADR 0013 path rules, coverage gates, catalog shape, or
    the three-tab nav destinations.
  - New outbound calls, font hosts, CDNs, or AI keys.

## Success criteria

- Given a first visit with no saved project, When the page loads, Then
  the landing shows the short headline, one subline, the two start
  buttons with **Private by design**, the risk → control → OSCAL →
  Rego example, one factual how-it-works section, a trust strip of
  honest claims, contribute links, a closing CTA, and a footer.
- Given the landing, When **Get started with identified risks** is
  activated, Then the identify-risks step opens.
- Given the landing, When **Get started with an existing policy
  clause** is activated, Then the existing paste form is shown.
- Given a saved `codify:project`, When the page loads, Then **Resume
  your project** is shown.
- Given a 390px-wide viewport, When the landing hero is shown, Then
  the two start buttons stack (risk above clause) with no overflow.
- Given the landing, When it is shown, Then it does not claim SOC 2 or
  ISO certifications, does not include testimonials, and does not
  include GRC Engineering Club branding.
- Skip-to-content still targets `#main`. No new outbound origins or
  font hosts. No AI keys written.

## Design references

**Required.** Opened and used before implementation. Do not copy vendor
branding. No web fonts. giga.ai is not on Mobbin; cite it directly.

| Screen / flow | URL | What we take from it |
| --- | --- | --- |
| **Primary — giga.ai** | https://giga.ai | Very short confident headline, lots of whitespace, strong hero, product visual just below, one proof section, trust-badge strip, clean closing CTA. Adapt structure and feel; do not clone copy or assets. |
| Railway landing | https://mobbin.com/screens/bc1febcc-0367-485b-8a9b-4f2df7d6e78a | Short headline, two CTAs, product visual immediately below the hero. |
| Langdock landing | https://mobbin.com/screens/b3db08cc-9aa6-43a7-9beb-436148558a52 | Whitespace-heavy landing structure and a quiet close. |
| Pin landing | https://mobbin.com/screens/815f7685-3c6a-4827-90dd-ca32d94119ab | Short headline and a product visual under the hero. |

## Privacy and outbound calls

No new network call, origin, or leave-device path
([ADR 0003](../adr/0003-local-only-privacy-model.md)). Docs, GitHub,
and Enact in the page are user-clicked navigations, not asset loads.
Keys stay in the browser. `codify:project`, `codify:statements`, and
`codify:theme` are unchanged.

## Open questions

None.

## Decision log

Authoring paths stay [ADR 0013](../adr/0013-risk-first-authoring-flow.md).
Nav destinations stay [ADR 0017](../adr/0017-three-tab-nav.md).
No new ADR: this is first-visit chrome, not a new leave-device path or
catalog shape. The Base blue hero from
[marketing-landing.md](marketing-landing.md) is superseded.
