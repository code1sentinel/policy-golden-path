# PRD: System fonts only (no Google Fonts)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | Product-owner approval of design-review finding 1 (Andre, 2026-10-04). This agent cannot open GitHub issues; acceptance criteria live here. |
| Supercedes / extends | [docs/prd.md](../prd.md), [ADR 0003](../adr/0003-local-only-privacy-model.md) |
| Author | Andre (product owner) / this slice |
| Date | 2026-10-04 |

## Problem

`codify-web` loads Inter from `fonts.googleapis.com` on every page load.
The Pages build already strips those links, so the live site is clean, but
the local app calls Google. That conflicts with ADR 0003 (no outbound
calls on the default path, no third-party fonts).

## Users

- **Primary:** anyone running `codify-web` who expects the policy — and
  the page chrome — to stay on-device.
- **Not this slice:** a new visual design, self-hosted webfonts, or
  theming.

## Job to be done

Open Codify locally. The page uses the system font stack and does not
contact a font host.

## Scope

- In:
  - Remove the Google Fonts `preconnect` and stylesheet from
    `index.html`.
  - Drop `fonts.googleapis.com` / `fonts.gstatic.com` from the local
    server CSP.
  - Use the existing system stack in `--font` (no Inter, no CDN).
  - Drop the now-unneeded strip step in `build_site.py`.
  - Test that `index.html` has no `https://` asset origins.
- Out:
  - Self-hosting Inter or any other webfont.
  - Start-screen, editor, export, or theme work (later slices).
  - New outbound origins.

## Success criteria

- Given `src/codify/static/index.html`, When it is read, Then it has no
  `href`/`src` to an `http(s)://` origin and no Google Fonts hosts.
- Given `codify-web`, When it serves the page, Then the CSP
  `style-src` is `'self'` only and does not list font origins.
- Given `--font` in `app.css`, When the stack is read, Then it starts
  with `system-ui` and does not name Inter.
- Given `scripts/build_site.py`, When `build_index` is inspected, Then it
  no longer filters Google Fonts lines (they are already gone from
  source).
- The Pages site still has no third-party asset origins
  (`tests/test_site.py`).

## Design references

None — no UI pattern. This is a privacy / CSP change. Type will fall
back to the OS UI font; layout is unchanged.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| — | — | No layout change |

## Privacy and outbound calls

Removes an outbound call. No new origin, font host, or leave-device
path. Fulfils [ADR 0003](../adr/0003-local-only-privacy-model.md) for
the local app as well as Pages.

## Open questions

None. Andre approved finding 1.

## Decision log

- ADR 0003 updated in this slice: the local app no longer loads Google
  Fonts; the Pages strip step is gone because the source is clean.
