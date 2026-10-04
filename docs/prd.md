# PRD: Codify (as shipped)

One page. Reverse-engineered from the code, README, tests, and merged PRs
on 2026-10-04. This is the product baseline every feature PRD extends.

| Field | Value |
| --- | --- |
| Product | Codify |
| Version | 1.2.1 |
| Surfaces | CLI (`codify`), local web app (`codify-web`), GitHub Pages (Pyodide) |
| Repo | https://github.com/code1sentinel/policy-golden-path |
| Site | https://code1sentinel.github.io/policy-golden-path/ |

## Problem

GRC people modernising a legacy policy have to turn mixed prose — requirements,
scope, definitions, roles, exceptions, aspirations — into testable control
statements and an OSCAL catalog. Doing that by hand is slow and inconsistent.
The policy is often sensitive, so a cloud upload is the wrong default.

## Users

- **Primary:** GRC professionals converting a legacy policy into catalog
  controls they will review, accept, and keep in git.
- **Secondary:** engineers scripting the same conversion (`codify POLICY`).
- **Not a user of the default path:** anyone who needs the policy processed
  on a remote server.

## Job to be done

Give Codify a policy. It sorts every clause, drafts control statements from
the requirements (action first, no tools, testable), scores each draft as it
is edited, and exports an OSCAL 1.1.2 catalog (also the save file), plus
Excel, CSV, and a conversion report.

Rule drafts are deterministic: the same policy always gives the same drafts.
They are a starting point to edit, not finished controls.

## Scope (today)

- **Ingest:** pasted clause text (the happy path), Word (`.docx`),
  CSV/Excel (`.xlsx`), or a saved OSCAL catalog. There is no Title field
  and clause numbers are optional ([ADR 0006](adr/0006-clause-only-input.md)).
  Multi-clause files may still split on the policy's own numbering and
  Word headings.
- **Sort:** requirement, scope, definition, role, exception, not-a-control;
  flag duplicates; show the reason; allow the type to be changed.
- **Draft:** rule-based split, active voice, drop the organisation as subject,
  keep people as scope, turn vague timing into parameters, move product names
  to guidance, drop hedges, note untestable wording.
- **Check:** weighted score (testable, scope, action-first, tool-neutral,
  purpose, single, labeled parts, determinable) with in-app Guide examples.
- **Review:** workspace lists requirement clauses; edit the statement next to
  the legacy clause; mark reviewed or accepted; filters and bulk actions
  under More; keyboard `j` / `k` / `r` / `a`.
- **Export:** OSCAL catalog 1.1.2, Excel, CSV (formula-escaped), Markdown
  report. Catalog is the save file.
- **AI drafting (opt-in):** Anthropic, OpenAI, or Gemini with the person's
  key; or Ollama on localhost. One clause per request. Marked `origin: ai`.
  The CLI and rule drafts never use AI.
- **Demo:** fictional Acme 2016 policy and key, used as the regression hold.

## Out of scope

- Reading PDF (paste the text).
- Mapping to IM8 Reform or any other external catalog (removed; see
  [ADR 0005](adr/0005-remove-im8-mapping.md)).
- Hosting policy text or API keys on a Codify server.
- Server-side calls to AI providers.
- Authentication, multi-user, or exposing `codify-web` on a public interface.
- FAIR-CAM / risk-register product surfaces (removed before Codify 1.0).
- Implementation statements (Codify scores catalog control statements only).

## Success criteria

- Same input policy → same rule drafts (no hidden model in the default path).
- Policy bytes stay on-device unless the person turns AI drafting on and
  confirms; even then, only one clause, its heading, and the rule drafts
  leave, and only to the provider they chose.
- Every catalog Codify writes is valid OSCAL 1.1.2 (CI vs NIST schema).
- Acme key holds: types, the duplicate, a draft for every requirement,
  action-first and tool-free wording (`tests/test_acme.py`).
- All three surfaces run the same `codify` package.
- CI green on every merge. No new outbound origins without an ADR.

## Design references

None recorded for the shipped workspace. Earlier polish named production
apps as inspiration but did not store Mobbin URLs.

The 2026-10-04 clause-only input slice removed the Title field and hid
clause numbers. No new layout: see
[docs/prds/clause-only-input.md](prds/clause-only-input.md).

**Future UI work must list Mobbin (`https://mobbin.com`) screen links here
or in `docs/prds/<feature>.md` before implementation.** If a request has no
links, ask for them; do not invent a design.

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| _required for any UI slice_ | https://mobbin.com/... | _layout / density / interaction — not branding_ |

## Constraints that new work must keep

- OSCAL 1.1.2 as the catalog format and save file ([ADR 0002](adr/0002-oscal-1-1-2.md)).
- Local-only privacy model ([ADR 0003](adr/0003-local-only-privacy-model.md)).
- Ollama localhost-only ([ADR 0004](adr/0004-ollama-localhost-only.md)).
- No IM8 (or similar) mapping surface without a new ADR that supersedes
  [ADR 0005](adr/0005-remove-im8-mapping.md).
- Clause-only happy-path input ([ADR 0006](adr/0006-clause-only-input.md)):
  no Title field; clause numbers are not required or shown.
- Standard-library runtime for the package; optional `dev` / `e2e` only for
  tests.

## How we change this PRD

Feature work that extends or narrows the above gets its own
`docs/prds/<feature>.md` (see [prd-template.md](templates/prd-template.md))
and, if it decides something durable, an ADR. Update this page when the
shipped product changes.
