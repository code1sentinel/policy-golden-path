# 0003. Local-only privacy model

Date: 2026-10-04

## Status

Accepted

## Context

Legacy policies often contain sensitive wording. The default product promise
in the README and the code is that the policy never leaves the person's
device, and that rule-based drafts do not use AI.

How the three surfaces honour that:

- **CLI:** reads a local file, writes a local file or stdout. No network.
- **Local web app (`codify-web`):** standard-library server, default bind
  `127.0.0.1:8765`, no authentication, no disk store, refuses cross-origin
  POSTs, CSP `connect-src` is `'self'` plus the opt-in AI origins. Warns if
  bound off loopback.
- **GitHub Pages:** the same Python package runs in the browser through
  Pyodide served from the site. The page and the local app use the
  system font stack; neither loads Google Fonts or other third-party
  script hosts. Policy text is not uploaded.

The request API (`src/codify/api.py`) is pure: each call is given the
project it needs. The page holds the project (memory / browser storage).
Optional AI drafting is off until turned on; the page then sends one clause
at a time **from the browser** to the provider the person chose, with their
key. Codify never sees the key. Keys are not written into the project,
autosave, or exports.

## Decision

- Default path: no outbound calls, no Codify server in the middle, no
  policy upload.
- Do not add analytics, CDNs, fonts, or other third-party origins to the
  local app or the Pages build. `index.html` has no `https://` asset
  origins; the local CSP does not list font hosts.
- Do not add a backend that receives policy text or API keys.
- Any new origin or leave-device path needs its own ADR, a CSP change with
  tests, and an explicit confirmation in the UI.
- PR review includes a privacy check: no new outbound calls.

## Consequences

- We cannot "just add" a hosted API, crash reporter, or cloud model.
- The Pages site cannot talk to `http://localhost` (browsers block it);
  local Ollama is a `codify-web` feature (see ADR 0004).
- Offline use of the CLI and `codify-web` remains possible.
