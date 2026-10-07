# 0009. Device-wide Statement library

Date: 2026-10-06

## Status

Accepted

## Context

Codify's save file is the per-project OSCAL 1.1.2 catalog
([ADR 0002](0002-oscal-1-1-2.md)). The page also keeps the open project in
`localStorage` under `codify:project`. After Accept, a control statement
exists only in that project. Reviewers who convert more than one policy on
the same device have no on-device place to reuse accepted wording.

Uploading a shared library would reverse
[ADR 0003](0003-local-only-privacy-model.md). Putting the library *inside*
the catalog would make the catalog a second, cross-project store and
change what Enact reads. Replacing clause-only input or risk tracing
would reverse [ADR 0006](0006-clause-only-input.md) and
[ADR 0008](0008-risk-input-and-oscal-tracing.md).

[ADR 0007](0007-authoring-app-shell.md) names sidebar destinations
(Workspace, Clauses, Risks, Catalog, Export, Guide). A library needs a
home in that shell without becoming a second save format.

## Decision

### Persistence

- The Statement library is **device-wide** and **separate** from
  `codify:project`. The browser key is `codify:statements`.
- Shape on disk: `{ "entries": [entry…], "saved": ISO-8601 }`.
- Each entry:

  | Field | Required | Meaning |
  | --- | --- | --- |
  | `id` | yes | `S-001`, `S-002`, … minted on first insert |
  | `statement` | yes | the accepted control statement (original wording) |
  | `parts` | no | `{action, scope, limit, purpose}` as last scored |
  | `source-type` | yes | `clause` or `risk` (latest Accept) |
  | `risk-id` | no | set when `source-type` is `risk` |
  | `accepted-at` | yes | ISO-8601 of the latest Accept of this text |
  | `last-used-at` | no | ISO-8601 of the latest Use / Add from the library |

- Closing a project, discarding resume, or exporting OSCAL does **not**
  clear the library. Opening a different project still sees it.
- The library is never written into the catalog, the project autosave, or
  an API key store.

### Dedupe

Two Accepts of the same **normalized** statement (Unicode case-fold,
collapsed whitespace) update the existing row's metadata. They do not
create a second `id`.

### Use path

**Use** or **Add** fills or creates a control in the **current** project.
Accept still runs the existing path (`assess_control_statement`, status
`accepted`, catalog export). Remove deletes the library row only.

### Surface

The authoring shell gains a **Library** destination. Export may download
library CSV/JSON locally (same download pattern as the catalog). No new
origin, font, or AI provider.

### CLI

The CLI does not grow a statement-library file in this decision. The
library is a browser-device store. Python owns normalize / upsert / search
/ export so the page and tests share one implementation.

## Consequences

- A later cloud or team library needs a new ADR that supersedes this one
  and [ADR 0003](0003-local-only-privacy-model.md).
- Quietly merging the library into `codify:project` or the OSCAL catalog
  is not allowed.
- Enact keeps reading `catalog.groups[].controls[]`. It never sees the
  device library.
- Sidebar destination tests that counted five `data-view` buttons must
  include Library.
