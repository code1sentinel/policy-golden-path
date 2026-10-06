# PRD: Authoring app shell (UI overhaul)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Listed in the PR; this agent cannot open GitHub issues. |
| Supercedes / extends | [docs/prd.md](../prd.md), [workspace-guide-declutter.md](workspace-guide-declutter.md), [indigo-theme.md](indigo-theme.md), [start-hero-empty-states.md](start-hero-empty-states.md), [oscal-panel-export.md](oscal-panel-export.md) |
| Author | Andre (product owner) / this slice |
| Date | 2026-10-06 |

## Problem

The recent declutter and palette slices (#21 footer, #22 workspace/guide,
#23 indigo-on-cool-gray) made the page quieter, but the product is still a
single long page with a header bar, not an authoring app. A GRC reviewer
moving clause → draft → review → accept → export has to hunt for the
statement, the score, and export. Andre wants a **real overhaul**: a
focused shell with a sidebar, a writing column, and a properties/review
panel — not another round of tweaks.

## Users

- **Primary:** a GRC reviewer converting a policy one control at a time.
- **Secondary:** the same person on GitHub Pages (browser-only) or
  `codify-web`.
- **Not this slice:** CLI output, classification,   drafting rules, OSCAL
  shape, AI providers, or risk-register product behaviour (stacked PR).

## Job to be done

Open Codify and work in a calm app: pick a place in the sidebar, write the
control in the centre, review it on the right, accept, next clause, export
the catalog.

## Scope

- In:
  - App shell for `codify-web` and the Pages site: collapsible left
    sidebar (Workspace / Clauses / Risks / Catalog / Export / Guide), top
    bar with breadcrumb and primary Export, centred editor column, right
    properties + review panel.
  - Control editor modelled on an issue detail: legacy source, statement,
    parts as sub-items, properties (status, control id, source, class).
  - Review panel: Accept / Dismiss for the current draft; optional AI
    result state Try again / Use this. Reuse the existing AI chip and
    providers; no new hosts.
  - Catalog view: table of controls with a source column (clause).
  - Empty states and an export dialog.
  - Keyboard: keep `j` / `k` / `↑` / `↓` / `r` / `a`; add `⌘`/`Ctrl`+Enter
    to accept (works in the statement field).
  - Light and dark themes, system fonts, CSP, privacy chrome.
- Out:
  - Risk register behaviour (sidebar item + empty state only).
  - New AI providers, origins, fonts, analytics, or outbound calls.
  - Changing OSCAL 1.1.2 output or the Acme classification key.
  - Copying Linear / Vanta / Grammarly branding.

## Success criteria

- Given no policy, the start view still has one primary **Codify** and a
  quiet **Try an example**, with a setup checklist on the side.
- Given a loaded policy, the person can pick a clause, edit the statement,
  accept with the primary or `⌘`/`Ctrl`+Enter, move next, and download an
  OSCAL catalog from the export dialog.
- Given the Catalog view, accepted and draft controls list with a source
  of clause.
- Light and dark tokens still meet WCAG 2.2 AA (`tests/test_theme_contrast.py`).
- Playwright e2e against `codify-web` and the Pages site stay green, with
  selectors updated for the shell.
- No new outbound origins; no API keys written to the project, autosave,
  or exports.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| 1. Linear app shell (list + side panel) | https://mobbin.com/screens/b9104519-abc8-4638-a2fc-206bea260188 | Primary model for the shell: quiet left sidebar, dense list, right context panel. Nav: Workspace / Clauses / Risks / Catalog / Export. |
| 2. Linear dark mode board | https://mobbin.com/screens/720724d3-f686-457f-8c00-fa7efa409b12 | Dark theme surfaces, borders, and contrast. Adapt, do not copy branding. |
| 3. Linear issue detail + properties | https://mobbin.com/screens/16e4d0c7-bf36-4daa-98f5-d3d31882cfec | Control editor: source on top, statement, parts as sub-items, right Properties (status, control ID, source, class). |
| 4. Lightfield doc editor + details | https://mobbin.com/screens/7438b199-644d-4370-b6fe-8e860addf330 | Calm, centred writing column and a slim details panel. |
| 5. Grammarly review suggestions | https://mobbin.com/screens/82d0d01f-8aa2-4fe4-a658-1498c92fb1ae | Review → accept of drafted control text: Accept / Dismiss per suggestion. |
| 6. Remote AI revision | https://mobbin.com/screens/44344cb5-9817-4d0e-b696-e8ba936b2f82 | Optional AI assist result: Try again / Use this and a disclaimer. Existing chip and providers only. |
| 10. Vanta controls table | https://mobbin.com/screens/0e24849e-96f6-4350-8e77-727f29293b4c | Catalog view: ID, control + description, source, status. |
| 12. Workable multi-step wizard | https://mobbin.com/screens/74548fe9-0ef9-4ca7-bb23-f8bc927acde8 | Quiet guided flow: Clause → Draft → Review → Accept. |
| 13. Front empty state | https://mobbin.com/screens/972f8c8c-800e-435e-9348-e51b94d329ab | Empty states: icon, one line, Create + Import, setup checklist. |
| 15. Dovetail export options | https://mobbin.com/screens/c1128474-a73d-46ed-bf7b-58aba54ae4b4 | Export dialog: one row per format, each with Download. |

Attached captures of these screens live in the working tree as
`mobbin-codify/01`–`06`, `10`, `12`, `13`, and `15`.

## Privacy and outbound calls

No new network calls, origins, or leave-device paths. The page still uses
the system font stack. CSP `connect-src` is unchanged. AI drafting stays
opt-in, one clause per request, key in the browser only.

## Open questions

- None for this slice. Risk register behaviour is a stacked PR.

## Decision log

- [ADR 0007](../adr/0007-authoring-app-shell.md) — authoring app shell
  (sidebar + writing column + properties/review). Static assets stay
  `index.html` / `app.css` / `app.js` / `theme.js`; no module split.
