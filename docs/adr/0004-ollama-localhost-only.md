# 0004. Ollama is localhost-only

Date: 2026-10-04

## Status

Accepted

## Context

Release 2 added opt-in AI drafting with a bring-your-own key for Anthropic,
OpenAI, and Gemini. PR #1 (2026-10-02) added **Ollama** so a person can
draft with a model on their machine, with no API key, and without sending
the clause to a cloud provider.

The implementation is explicit about where that model lives:

- The page calls `http://localhost:11434/v1/chat/completions` only
  (`src/codify/static/app.js`).
- CSP `connect-src` on the local server allows
  `http://localhost:11434` and `http://127.0.0.1:11434`
  (`src/codify/webapp.py`). Tests lock that list
  (`tests/test_webapp.py`, `tests/test_site.py`).
- There is no key field for Ollama (`requiresKey: false`).
- The HTTPS Pages site cannot reach `http://localhost`; the UI explains
  that and tells the person to run `codify-web --open`.
- Codify itself still does not call Ollama; the browser does, one clause
  per request, same as the cloud providers.

## Decision

- Ollama is a local provider only: `localhost` / `127.0.0.1` port `11434`.
- Do not add a configurable remote Ollama URL, a Codify proxy, or any
  other host to `connect-src` for this provider.
- Keep Ollama key-free. Do not store a dummy key to "enable" it.
- Cloud AI stays bring-your-own-key and opt-in; the CLI never calls AI.

## Consequences

- Air-gapped drafting works on `codify-web` when Ollama is running.
- The online site cannot offer working Ollama. That is accepted.
- Pointing Codify at a networked Ollama would be a new ADR and a privacy
  review: the clause would leave the machine.
