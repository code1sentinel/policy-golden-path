# PRD: Device-wide Statement library

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Listed in the PR; this agent cannot open GitHub issues. |
| Supercedes / extends | [docs/prd.md](../prd.md), [ui-overhaul.md](ui-overhaul.md), [risk-to-controls.md](risk-to-controls.md) |
| Author | Andre (product owner) / this slice |
| Date | 2026-10-06 |

## Problem

After a reviewer **Accepts** a control statement (from a clause or from a
risk), that wording lives only in the current project's OSCAL catalog. The
next policy on the same device starts from scratch. Reusable, already-accepted
statements have nowhere to sit that is still on-device and not a second
catalog format.

## Users

- **Primary:** a GRC reviewer who converts more than one policy on the same
  machine and wants to reuse accepted wording.
- **Secondary:** the same person on GitHub Pages or `codify-web`.
- **Not this slice:** teams that need a shared cloud library, multi-user
  sync, or implementation statements.

## Job to be done

Accept a control and have it land in the project catalog **and** in a
device-wide Statement library. Later, pick **From library**, tweak, and
Accept into the current catalog. Search, remove, and export the library
locally. Nothing is uploaded.

## Scope

- In:
  - On Accept (clause- or risk-derived), upsert the statement into a
    device-wide library, deduped by normalized statement text.
  - Library nav view: search, remove, export CSV/JSON, empty state.
  - **From library** picks while drafting (clause editor and risk template
    suggestions): Use / Add, then tweak and Accept as today.
  - Persistence: `localStorage` key separate from `codify:project`. Schema
    `{ id, statement, parts?, source-type, risk-id?, accepted-at, last-used-at? }`.
  - Light / dark themes, system fonts, existing CSP, privacy chrome.
- Out:
  - Cloud sync, multi-user, shared team libraries.
  - FAIR / residual risk / IM8 mapping.
  - Changing clause-only happy path ([ADR 0006](../adr/0006-clause-only-input.md))
    or risk tracing ([ADR 0008](../adr/0008-risk-input-and-oscal-tracing.md)).
  - Implementation statements (catalog control statements only).
  - New AI providers, origins, fonts, or outbound calls.

## Success criteria

- Given Accept on a clause- or risk-derived control, the statement appears
  in Library on this device and survives reopening a different project.
- Given Library **Use** on a statement, the editor is filled and Accept
  still goes through `assess_control_statement` / the existing accept path
  into the current catalog.
- Given **Remove**, the statement leaves the library only (catalog
  unchanged).
- Given **Export**, CSV/JSON download locally; no upload.
- Duplicate Accept of the same normalized text does not create a second
  library row (update metadata instead).
- CI green. No new outbound. No keys written.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| 1. HoneyBook My Templates | https://mobbin.com/screens/d0a62f5f-40bf-4441-a208-1d1693111f8e | Searchable reusable list + count + toolbar search. |
| 2. HubSpot Message templates | https://mobbin.com/screens/0a9725f8-5375-441e-94d1-93ed06855143 | Table library: search, actions, created/modified. |
| 3. Workable Performance templates | https://mobbin.com/screens/2449e13f-2629-4f41-ad98-2abeac33b73d | Template cards + search + Add. |
| 4. Relume Saved empty | https://mobbin.com/screens/06b0869d-0597-4f57-a52e-8248ef1c19f6 | Empty saved library + browse CTA. |
| 5. Literal library empty | https://mobbin.com/screens/4a83311d-4351-430a-9aae-be02058bf841 | Empty library + import-style next step. |
| 6. PandaDoc My templates | https://mobbin.com/screens/10d1dcf3-aa80-4ca0-9ede-835a41af6999 | Pick-from-library modal while authoring. |
| 7. ClickUp Templates sidebar | https://mobbin.com/screens/7c851fc6-9014-412b-ae29-0ed882783e29 | Templates panel beside the editor. |
| 8. Slite Use this template | https://mobbin.com/screens/8cf6c7f8-df1b-43cb-a5c1-367a4fdf0350 | Preview + Use this template. |
| 9. Grammarly review (existing) | https://mobbin.com/screens/82d0d01f-8aa2-4fe4-a658-1498c92fb1ae | Accept / Dismiss pattern already in Codify. |
| 10. Vanta risk library (existing) | https://mobbin.com/screens/d1276fef-704c-4650-9c7b-902ffa4e2f04 | Suggestion list with Add. |
| 11. Dovetail export (existing) | https://mobbin.com/screens/c1128474-a73d-46ed-bf7b-58aba54ae4b4 | Export dialog entry for library CSV/JSON. |

Adapt to Codify's indigo / cool-gray shell. Do not copy branding. System fonts.

## Privacy and outbound calls

No new network calls, origins, or leave-device paths. The library is
`localStorage` (`codify:statements`), never posted. Closing or discarding a
project does not clear it. API keys stay out of the library, the project
autosave, and exports. CSP `connect-src` is unchanged.

## Open questions

- None. Cloud sync is out of this slice.

## Decision log

- [ADR 0009](../adr/0009-device-wide-statement-library.md) — device-wide
  library key, entry schema, dedupe, and coexistence with the OSCAL catalog.
