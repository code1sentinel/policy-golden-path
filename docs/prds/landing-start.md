# PRD: One landing (fold splash into start)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Acceptance criteria live here (this agent cannot open GitHub issues). |
| Supercedes / extends | [docs/prd.md](../prd.md), [welcome-splash.md](welcome-splash.md), [risk-first-authoring-flow.md](risk-first-authoring-flow.md), [personal-start-chrome.md](personal-start-chrome.md), [start-hero-empty-states.md](start-hero-empty-states.md) |
| Author | Product owner / this slice |
| Date | 2026-10-15 |

## Problem

Codify looks messy on first open. A splash (#28) then a start screen with a
checklist, two small choice cards, and extra chrome means the idea is not
obvious in seconds. Returning people with a saved project should not see a
different first beat — they should see the same landing with Resume.

## Users

- **Primary:** a GRC reviewer opening Codify (Pages or `codify-web`) who
  needs to understand what it does and pick a starting path.
- **Also:** a returning reviewer with a saved `codify:project` who wants
  to resume.
- **Not this slice:** changing the two authoring paths after the cards
  (PR #38 / [ADR 0013](../adr/0013-risk-first-authoring-flow.md)), the
  workspace, Catalog, Library, Risks, or export.

## Job to be done

See, in seconds, that Codify turns what you need to address into control
statements you then test in Enact. Choose **Start from risks** or
**Start from a policy clause**. Resume if this device already has a
project.

## Scope

- In:
  - One landing that replaces the splash plus the old start. No
    `#splash`, no `Get started` gate. First visit and returning visit
    share the same page.
  - One-line headline: *Codify turns what you need to address into clear
    control statements, which you then test in Enact.*
  - A simple visual of the two ways in, converging:
    Risks → Control statements → Enact, and Policy clause → Control
    statements → Enact.
  - Two large start cards as the only primary actions: **Start from
    risks** (recommended) and **Start from a policy clause**. Each has
    one plain sentence and a short example. They open the existing
    path A / path B from PR #38.
  - Quiet secondary actions: resume or open a saved project, and a docs
    link. When `codify:project` (or an in-memory project) would have
    shown resume, Resume is prominent on the same landing.
  - Remove clutter: splash, setup checklist, extra buttons, feature
    lists, stats, the separate current-project card (folded into Resume).
  - Generous whitespace, plain copy, existing colour and type tokens,
    Light / Dark / System.
  - Keyboard and screen-reader accessible; cards stack on a narrow
    viewport.
  - `codify:splash-seen` is no longer read or written. Leftover values
    on a device are ignored.
- Out:
  - Restructuring the sidebar, workspace, flow stepper, clause paste
    form, or Enact handoff.
  - New outbound calls, font hosts, CDNs, or AI keys.
  - Changing ADR 0013 path rules, coverage gates, or OSCAL.

## Success criteria

- Given a first visit with no saved project, When the page loads, Then
  there is no splash and the landing is visible with the one-line
  headline, the converging flow, and the two start cards.
- Given the landing, When **Start from risks** is activated, Then the
  existing risk-first path opens (identify-risks stepper).
- Given the landing, When **Start from a policy clause** is activated,
  Then the existing paste form is shown (Codify / Try an example / Open
  a file).
- Given a saved `codify:project`, When the page loads, Then the same
  landing is shown with a prominent **Resume**, and Resume opens the
  saved project on its existing path.
- Given the landing, When it is inspected, Then there is no splash, no
  setup checklist, no feature list or stats, and the only large primary
  actions are the two cards. Secondary actions are resume / open a saved
  project and a docs link.
- Given a keyboard or screen reader, When the landing is used, Then the
  headline, flow, and cards are reachable and named. Given a narrow
  viewport, When the landing is shown, Then the cards stack.
- Skip-to-content still targets `#main`. No new outbound origins or
  font hosts. No AI keys written.

## Design references

Opened and used before implementation. Adapt hierarchy to Codify’s
indigo-on-cool-gray tokens. Do not copy vendor branding.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Sprig — start cards | https://mobbin.com/screens/77add735-ba8c-4f49-a512-fabd8b2e1826 | Two large equal start cards: title, one sentence, short example. One marked recommended. |
| Klaviyo — headline + flow | https://mobbin.com/screens/88633529-5820-4f59-93e0-98d0806ad4fd | One headline that states the product, then a simple node flow (not a feature list). |
| Microsoft Copilot — How it works | https://mobbin.com/screens/ebac045b-3c68-4dd0-8811-1ce2a31aaf05 | Centered “how it works” steps, generous whitespace, one idea. |
| fal — path choice | https://mobbin.com/screens/484439bd-e04c-4d68-b977-acfc6937eebe | Two path cards as the only primary; quiet secondary under them. |

Related screens opened while checking those citations (same patterns;
not used as the source of layout): Higgsfield two-path cards, Uxcel
recommended vs alternative cards, Braintrust “let’s get started” pair.

## Privacy and outbound calls

No new network call, origin, or leave-device path
([ADR 0003](../adr/0003-local-only-privacy-model.md)). The docs link is
ordinary `<a href>` navigation the person chooses (same as the Enact
book link already on Send to Enact). Keys stay in the browser. The
splash dismiss key is retired; `codify:project`, `codify:statements`,
and `codify:theme` are unchanged.

## Open questions

None.

## Decision log

No new ADR. The two authoring paths stay [ADR 0013](../adr/0013-risk-first-authoring-flow.md).
This slice only changes the first screen and folds #28 into it.
