# PRD: Personal start chrome

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | This agent cannot open GitHub issues; acceptance criteria live here. |
| Supercedes / extends | [docs/prd.md](../prd.md) |
| Author | Product owner (personal app feel) / this slice |
| Date | 2026-10-05 |

## Problem

The start page footer reads “Codify is open source (MIT) from the GRC
Engineering Club Singapore. Version 1.2.1.” That org-and-version line
makes the local app feel like club software, not a personal tool.

## Users

- **Primary:** the person running Codify on their device.
- **Not this slice:** README origin history, LICENSE, CLI `--version`.

## Job to be done

Open Codify and see a quiet start screen with no club or version
attribution in the chrome.

## Scope

- In:
  - Remove the start footer that names the GRC Engineering Club Singapore,
    MIT in that sentence, and the injected version line.
  - Stop writing `Version {n}.` into the page.
  - Drop unused `.foot` styles once the footer is gone.
- Out:
  - LICENSE and README license/origin history (MIT stays documented there).
  - CLI `--version`, OSCAL `metadata`, `/api/config`.
  - Layout, theme, or other start-screen copy.
  - New outbound network calls.

## Success criteria

- Given the start page HTML, When it is loaded, Then it does not mention
  the GRC Engineering Club Singapore, does not say “open source (MIT)”,
  and has no `#version` element or footer club line.
- Given the start view in the browser, When it is shown, Then no
  “Version x.y.z” chrome is visible.
- No new outbound calls.

## Design references

None — text-only copy removal; no layout invented. Mobbin is not required
for deleting a footer sentence.

## Privacy and outbound calls

No new network call, origin, or leave-device path.

## Open questions

None.

## Decision log

None. Copy only; no ADR.
