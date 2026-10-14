# 0012. Identified risks as input to control authoring

Date: 2026-10-14

## Status

Accepted. Refined by
[0013-risk-first-authoring-flow.md](0013-risk-first-authoring-flow.md): identified
risks stay input, not a register; on the web they are required for Review and
export, with two start paths.

Refines [0011-no-risk-register.md](0011-no-risk-register.md): Codify still has
no risk **register**. This ADR restores a narrow path that 0011 closed —
storing a list of risks on the project at all — and uses it only as **input**
to authoring. It does not revive
[0008-risk-input-and-oscal-tracing.md](0008-risk-input-and-oscal-tracing.md).

## Context

PR #30 / ADR 0011 removed the local risk register because GRC engineering
should engineer risk (controls, checks, automation) rather than maintain a
scored artifact. Each control still has a purpose field with “the risk it
treats” wording; that wording stays.

Reviewers already identify risks outside Codify. They want those statements
in the project so control statements can address them, with coverage and a
trace in the OSCAL catalog. Putting a scored register back would reverse
0011. Ignoring identified risks entirely leaves purpose as free text only.

OSCAL 1.1.2 catalogs have no first-class Risk object ([ADR 0002](0002-oscal-1-1-2.md)).
Tracing has to use schema-valid `props`, `links`, and back-matter resources.
Clause-only happy-path input ([ADR 0006](0006-clause-only-input.md)) and the
local-only privacy model ([ADR 0003](0003-local-only-privacy-model.md)) stay.

## Decision

### Input, not a register

- A project may hold `project.risks`: a list of identified risks the person
  already has. Each record is `{id, statement, note?}`. `id` is `R-001`,
  `R-002`, … (or a unique token they supply). `statement` is the short risk
  wording. `note` is optional context.
- This is **input only**. There is no likelihood, impact, score, owner,
  status, asset, threat, vulnerability, review cycle, residual risk, heatmap,
  treatment plan, register import, `codify --risks`, or Risk register export.
- The control-statement purpose field (`risk` / `risk-statement`, “the risk
  it treats”) is unchanged. When a control is linked to identified risks,
  that field **displays** the linked statement(s).
- Clause paste remains the happy path. Identified risks are a parallel
  optional input. A project with only clauses still opens, scores, and
  exports as today.

### Linking and coverage

- A control may link to one or more risk ids (`risk_ids`). Linking does not
  change `source-type`; catalogs still emit `source-type=clause`. Controls
  drafted from a clause can treat a risk; a suggested library statement can
  be added and linked without inventing a clause.
- Coverage is a flag, not a score: an identified risk with no linked control
  is uncovered; a control with no linked risk is unlinked. The UI may flag
  those rows. It must not present them as a register.

### Persistence

- The list lives in memory and the existing `codify:project` autosave. It is
  never posted to a Codify server. No new outbound origin.
- Older saves and catalogs that have **no** identified-risk list load with
  `risks: []`.
- Leftover **register** records from ADR 0008 (likelihood, impact, score,
  owner, status, title-without-statement, `source-type=risk`, scalar
  `risk-id` tracing, `codify:risks` store) are still dropped as 0011
  specified. They are not converted into identified risks.
- Loading an older Codify catalog still skips back-matter resources that
  only have the old `risk-id` prop.

### OSCAL 1.1.2 tracing

On export, using only catalog constructs the NIST 1.1.2 schema allows:

1. One `back-matter.resources[]` entry per identified risk:
   - `uuid` — UUID5 of `(project.uuid, "identified-risk:" + id)`
   - `title` and `description` — the short statement
   - Codify-namespace props: `identified-risk-id`, and `note` when present
2. Each linked control carries a repeatable Codify-namespace prop
   `treats-risk` (the risk id) and a `links` entry
   `{ "href": "#<resource-uuid>", "rel": "related" }`.
   Clause-derived controls keep `derived-from` the clause resource.
3. The purpose field still exports as `risk-statement` when set.
4. Do not emit `source-type=risk`, the old `risk-id` prop, or
   `rel=reference` to a register resource.

Opening a Codify catalog restores `project.risks` from resources that have
`identified-risk-id`, and `risk_ids` from `treats-risk` / `rel=related`.
Enact can ignore these fields; if it wants a trace, follow `rel=related`
or read `treats-risk`.

### Suggestions

- For each identified risk, Codify may suggest matching statements from the
  on-device Statement library using **local** token overlap only.
- If optional AI assist is already on, the same existing `ai_prompt` /
  `ai_reply` path may also draft suggestions from the risk statement (the
  risk text is the prompt input). No new endpoint, origin, or key store.

## Consequences

- ADR 0011 remains binding for the register: no scored artifact, no
  `--risks`, no Risk register export. Re-introducing those needs a new ADR
  that supersedes this one and 0011.
- Goldens that write OSCAL stay valid 1.1.2. Projects without identified
  risks emit the same catalog shape as before this ADR (no extra resources).
- Older browsers that still hold a leftover `codify:risks` key continue to
  drop it; `codify:statements` is not rewritten.
