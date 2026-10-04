# PRD: OSCAL JSON panel and split export

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Product-owner approval of design-review findings 3 and 4 (Andre, 2026-10-04). This agent cannot open GitHub issues; acceptance criteria live here. |
| Supercedes / extends | [docs/prd.md](../prd.md) |
| Author | Andre (product owner) / this slice |
| Date | 2026-10-04 |

## Problem

The promised output is an OSCAL control statement, but the editor only
shows prose, parts and a score. The JSON exists only inside a downloaded
catalog. You cannot see or copy the OSCAL for the clause you are looking
at.

**Save OSCAL catalog** sits next to an **Export** menu that also lists
"OSCAL catalog (.json)".

## Users

- **Primary:** a GRC reviewer who wants to inspect or copy one control's
  OSCAL without downloading the whole catalog.
- **Not this slice:** theming, AI chrome, Start-screen work.

## Job to be done

Switch to **OSCAL JSON**, read this control, copy it. Save the catalog
with one primary; other formats sit under a chevron.

## Scope

- In:
  - Editor tabs: **Statement | OSCAL JSON**.
  - JSON tab: read-only, monospace, line-numbered `<pre>` of this
    control's OSCAL 1.1.2 object (`control_oscal` API).
  - **Copy** uses the local clipboard API (no network) and an
    `aria-live` **Copied** status.
  - Split button: **Save OSCAL (.json)** plus a chevron menu of Excel,
    CSV, and Conversion report only.
- Out:
  - Changing catalog shape or OSCAL version.
  - Title field or clause numbers.
  - Theme toggle or moving the AI control.
  - New outbound calls.

## Success criteria

- Given an open control, When the person opens **OSCAL JSON**, Then they
  see this control's OSCAL (id `c-…`, statement part) with line numbers,
  and the statement textarea is hidden.
- Given that JSON, When they press **Copy**, Then an `aria-live` status
  reads **Copied** and the text is written with the local clipboard API.
- Given the workspace toolbar, When it is shown, Then there is one
  **Save OSCAL (.json)** action and the chevron menu does not repeat
  OSCAL.
- Given `control_oscal` for the unnumbered lock-screens clause, When it
  is called, Then the object matches
  `tests/goldens/unnumbered-lock-screens-control.json`.
- Full catalogs still validate as OSCAL 1.1.2. Acme key still holds.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| Browserbase — JSON panel + copy | https://mobbin.com/screens/ae95ee59-43fe-4173-887a-c3542d08c9c8 | Generated JSON beside the builder, copy |
| Mistral AI — code tabs + copied toast | https://mobbin.com/screens/911ba1b2-a744-4359-832b-451758afbd09 | Format tabs, copy, copied status |
| Claude — artifact copy / publish | https://mobbin.com/screens/587db0a6-6f7d-4a6a-b1ac-80ea594f7c7a | One copy + one primary publish/save |

Adapt the patterns. Do not copy branding.

## Privacy and outbound calls

Copy uses `navigator.clipboard` in this browser only. No new origin.

## Open questions

None. Andre approved findings 3 and 4.

## Decision log

None. Display of existing OSCAL; no ADR.
