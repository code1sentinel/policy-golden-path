# 0001. Record architecture decisions

Date: 2026-10-04

## Status

Accepted

## Context

Codify is a small repo with durable constraints (OSCAL version, local-only
data, localhost Ollama, no IM8 mapping). Those constraints live in code and
git history today. Agents and new contributors cannot see *why* they exist
unless we write them down. We also need a place for decisions that are not
yet code.

## Decision

We will record architecture and product-shaping decisions as Markdown files
in `docs/adr/`, named `NNNN-short-title.md`, starting at `0001`.

Each ADR uses this shape:

- Title and date
- Status: Proposed, Accepted, Deprecated, or Superseded (with a link)
- Context: the forces that made the decision necessary
- Decision: what we will do
- Consequences: what becomes easier, harder, or off-limits

Rules:

- One decision per file. Number from the next free integer; never reuse.
- An accepted ADR is binding until a later ADR supersedes it.
- Feature work that needs a new decision writes the ADR in the same slice
  as the first code that depends on it.
- ADRs state only what we can verify from discussion, code, or history.
  Guesswork stays out.

This file is itself the first ADR, following
[Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
(Quinn Murphy / Nygard).

## Consequences

- Agents and humans have a single place to check before reversing a constraint.
- Small implementation choices (rename a CSS class, add a test) do not need
  an ADR.
- We now owe ADRs for the decisions already visible in the tree: OSCAL
  1.1.2, the local-only privacy model, Ollama localhost-only, and the
  removal of IM8 mapping.
