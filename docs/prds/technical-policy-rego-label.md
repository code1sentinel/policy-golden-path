# PRD: Name the last step Technical policy (Rego)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Acceptance criteria live here (this agent cannot open GitHub issues). |
| Supercedes / extends | [docs/prd.md](../prd.md), [landing-flow-cards.md](landing-flow-cards.md) |
| Author | Product owner / this slice |
| Date | 2026-10-15 |

## Problem

First-time users do not know what **Enact** is. The landing diagrams
end on that word, so the last step looks like a product they have never
heard of instead of the outcome: a technical policy in Rego.

## Users

- **Primary:** a GRC reviewer opening Codify for the first time.
- **Not this slice:** changing the two authoring paths, export formats,
  or Enact itself.

## Job to be done

See that the last step is a **technical policy (Rego)**, with Enact
named only as where that policy is tested.

## Scope

- In:
  - Landing flow diagrams (and any stepper/guide label that is just
    **Enact**) rename the last step to **Technical policy (Rego)**.
    Flows read: Identify risk → Control statement → Technical policy
    (Rego), and Policy clause → Control statement → Technical policy
    (Rego).
  - At most one short muted caption under the diagrams:
    *Exported as OSCAL and tested as Rego in Enact*, with **Enact**
    linking to the existing Enact Pages app.
  - Keep **Send to Enact** as the action. Add helper text that it
    turns control statements into testable Rego policy (export dialog
    and the in-app enact step / guide).
- Out:
  - New outbound calls, font hosts, CDNs, or AI keys.
  - Changing OSCAL export, coverage gates, or the two start paths.

## Success criteria

- Given the landing, When it is shown, Then each flow card's last
  step is **Technical policy (Rego)** and is not the bare word Enact.
- Given the landing, When the caption is present, Then it is muted
  and **Enact** is a link to the Enact app.
- Given **Send to Enact** (dialog or final step), When it is shown,
  Then the action title stays **Send to Enact** and helper text
  explains it turns control statements into testable Rego policy.
- Given a stepper or step guide whose label was only **Enact**, When
  it renders, Then it says **Technical policy (Rego)**. Labels that
  already say **Send to Enact** stay that action wording.
- Skip-to-content still targets `#main`. No new outbound origins.

## Design references

Same Mobbin screens as [landing-flow-cards.md](landing-flow-cards.md).
This slice only renames the last node and adds a muted caption; it
does not invent a layout.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Sprig — start cards | https://mobbin.com/screens/77add735-ba8c-4f49-a512-fabd8b2e1826 | Two equal start cards. |
| Klaviyo — headline + flow | https://mobbin.com/screens/88633529-5820-4f59-93e0-98d0806ad4fd | Simple node flow on each card. |
| Microsoft Copilot — How it works | https://mobbin.com/screens/ebac045b-3c68-4dd0-8811-1ce2a31aaf05 | One short caption, generous whitespace. |
| fal — path choice | https://mobbin.com/screens/484439bd-e04c-4d68-b977-acfc6937eebe | Quiet secondary under the cards. |

## Privacy and outbound calls

No new network call, origin, or leave-device path
([ADR 0003](../adr/0003-local-only-privacy-model.md)). The Enact link
is the same user-chosen `<a href>` already used on Send to Enact.

## Open questions

None.

## Decision log

No new ADR. Paths stay [ADR 0013](../adr/0013-risk-first-authoring-flow.md).
