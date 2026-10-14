# 0013. Risk-first authoring flow

Date: 2026-10-14

## Status

Accepted

Refines [0012-identified-risks-as-input.md](0012-identified-risks-as-input.md): identified risks stay **input**, not a register. On the web they are no longer an optional side view — they are required for Review and export. Refines [0006-clause-only-input.md](0006-clause-only-input.md) for the **web start**: clause paste remains one of two paths, not the only entry. CLI and file ingest stay clause-in.

Does not revive [0008-risk-input-and-oscal-tracing.md](0008-risk-input-and-oscal-tracing.md). [0011-no-risk-register.md](0011-no-risk-register.md) still holds.

## Context

ADR 0012 let a project hold `{id, statement, note?}` so controls can address identified risks, with coverage flags and OSCAL `identified-risk-id` / `treats-risk` / `rel=related`. The shipped happy path stayed clause → draft → accept → catalog; risks were linked afterwards.

Control statements exist to treat risks. Starting from a clause makes coverage optional and hides the Enact handoff. Reviewers also still need to paste a clause when that is what they have.

## Decision

### Two start paths (web)

After the welcome splash (unchanged), the start screen offers:

1. **Start from risks** (recommended, visually primary). Identify risks, then write control statements that treat them. Policy clauses are optional context attachable to a risk or control.
2. **Start from a policy clause.** Paste (or open a file / Try an example) as today. Codify drafts from requirements. Then every control must be linked to an identified risk (the person may add risks inline) before Review.

Both paths use the same **Review** and **Send to Enact** steps.

A project may store `authoring_path`: `"risks"` or `"clauses"`. Missing (older saves and catalogs) means `"clauses"`. The field lives on the in-memory project and `codify:project` autosave. It is not required on the OSCAL catalog (goldens and Enact stay as 0012).

### Required steps and gates

- Identify risks: at least one record with a non-empty statement. Ids stay `R-001`, … No likelihood, impact, score, or owner.
- Develop control statements (path A): every identified risk has at least one **non-empty** control statement (`risk_ids` includes that risk). Library suggestions are local token overlap; optional AI uses the existing `ai_prompt` / `ai_reply` path. No new endpoint or key store. `source-type` remains `clause` (0012).
- Link to risks (path B): every control with a non-empty statement is linked to at least one identified risk, and every identified risk has at least one such control.
- Review: coverage flags (uncovered risks, unlinked controls), edit, accept. Purpose field wording (“the risk it treats”) is unchanged.
- Send to Enact / web export of the **project** (OSCAL, Excel, CSV, report): blocked until every identified risk has at least one **accepted** non-empty control statement, and every non-empty control is linked. Statement-library export is not gated. **CLI export is not gated** (`codify POLICY` remains a script path).

The UI shows a stepper (complete / current / upcoming) and a short per-step guide (what, why, example, common mistakes) that can be dismissed and opened again.

### Back-compat

- Older clause-first projects and catalogs open on path B and prompt the person to add risks.
- Leftover register records are still dropped as 0011 / 0012 specified.
- Splash, resume-skip-splash, and device keys (`codify:splash-seen`, `codify:project`, `codify:statements`) are unchanged.

### Privacy

No new outbound origin. Download only. Links to Enact Pages and the Codify book are user navigation.

## Consequences

- The web happy path is risk-first; clause-first is still offered and still drafts the same way.
- A catalog cannot be sent to Enact from the web wizard until coverage is accepted. Scripts using the CLI are unaffected.
- Re-introducing a scored register still needs an ADR that supersedes 0011 and this one.
