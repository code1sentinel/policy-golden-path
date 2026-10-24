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

- **Ingest:** two web start paths ([ADR 0013](adr/0013-risk-first-authoring-flow.md)):
  identify risk → control statement, or paste clause text (path B,
  CLI, and files). Word (`.docx`), CSV/Excel (`.xlsx`), or a saved OSCAL
  catalog still open. There is no Title field and clause numbers are optional
  ([ADR 0006](adr/0006-clause-only-input.md)). Multi-clause files may still
  split on the policy's own numbering and Word headings. There is no risk
  register ([ADR 0011](adr/0011-no-risk-register.md)). Identified risks are
  input so controls can address them
  ([ADR 0012](adr/0012-identified-risks-as-input.md)).
- **Sort:** requirement, scope, definition, role, exception, not-a-control;
  flag duplicates; show the reason; allow the type to be changed.
- **Draft:** rule-based split, active voice, drop the organisation as subject,
  keep people as scope, turn vague timing into parameters, move product names
  to guidance, drop hedges, note untestable wording.
- **Check:** weighted score (testable, scope, action-first, tool-neutral,
  purpose, single, labeled parts, determinable) with in-app Guide examples.
- **Review:** workspace lists requirement clauses; edit the statement next to
  the legacy clause; **Statement | OSCAL JSON** tabs on the current control;
  mark reviewed or accepted; filters and bulk actions under More; keyboard
  `j` / `k` / `r` / `a`. Accept also upserts the statement into a device-wide
  **Library** ([ADR 0009](adr/0009-device-wide-statement-library.md)).
  After a pasted clause, Control statements uses **…for each clause**.
  Review labels and the score have plain-language
  help; Accept is the single primary until the control is accepted, then
  **Accepted ✓** and **Next control** lead. Nav **Home** returns to the
  landing. **Risk Entry** and **Policy Clause** open each flow at step 1
  ([three-tab-nav.md](prds/three-tab-nav.md)). Pasted projects get a name
  from the first clause. Both paths share step 3 **Policy as code (Rego)**:
  a review summary with Edit back to earlier steps, Generate Rego starter,
  and an OSCAL JSON preview
  ([review-policy-as-code.md](prds/review-policy-as-code.md)).
- **Export:** Step 3 **Download OSCAL catalog** (recommended, catalog 1.1.2)
  on this device, with **Opens in Enact** as a supporting caption; Excel,
  CSV (spreadsheet-safe), the Markdown report, and optional
  statement-library JSON/CSV. Step 3 can **Generate Rego starter** for each
  control (local templates; Sentinel/Checkov optional) and attach the file
  to the catalog. The web wizard blocks project formats until every
  identified risk has a control statement and every control is linked. No
  upload.
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
- A risk register, FAIR quantitative scoring, or residual-risk workflow
  (removed; see [ADR 0011](adr/0011-no-risk-register.md)). Identified risks
  as input are in
  [identified-risks-as-input.md](prds/identified-risks-as-input.md); the
  web flow is
  [risk-first-authoring-flow.md](prds/risk-first-authoring-flow.md).
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

The local app and Pages site use the system font stack and do not load
Google Fonts. See
[docs/prds/system-fonts-no-google.md](prds/system-fonts-no-google.md).

A first visit is a short marketing landing in the spirit of giga.ai:
a punchy headline, one subline, two equal-weight start buttons —
**Get started with identified risks** (primary) and **Get started with
an existing policy clause** (visible secondary) — **Private by
design**, a risk → control → OSCAL → Rego example, one factual how-it-works
statement, a trust-badge strip of honest claims, contribute links, and
a closing CTA. A saved project shows **Resume your project**. See
[docs/prds/giga-landing.md](prds/giga-landing.md) and
[docs/prds/technical-policy-rego-label.md](prds/technical-policy-rego-label.md).
Flow A step 1 is a calm capture page: title, one guidance sentence, a
collapsible writing tip, an inline list of risks, and **Continue to
control statements** disabled until at least one risk exists. See
[docs/prds/identify-risks-page.md](prds/identify-risks-page.md).
Flow B step 1 is a matching capture page: **Paste your policy clause**,
a large paste box, a small example panel, a preview list of clauses,
and **Continue to control statements** disabled until at least one
clause exists. See
[docs/prds/policy-clause-page.md](prds/policy-clause-page.md).
Shared step 2 is a split list + editor: write a control statement for
each risk (or clause), with coverage dots, a progress line, and
**Continue to policy as code** disabled until every item has a
statement. See
[docs/prds/control-statements-page.md](prds/control-statements-page.md).
Shared step 3 is **Policy as code (Rego)**: a review summary, Rego
starters, and an OSCAL catalog preview with Copy / Download. See
[docs/prds/review-policy-as-code.md](prds/review-policy-as-code.md).
First-run copy,
the result step, review help, and export defaults are in
[docs/prds/first-run-clarity.md](prds/first-run-clarity.md).
A second first-time walkthrough polish (accepted state, `[N]` prompts,
Workspace = start, pasted titles) is in
[docs/prds/second-walkthrough-polish.md](prds/second-walkthrough-polish.md).

Start is one clause box and one **Codify** button; the demo is a quiet
example chip. Empty editor and filter panes include a next-step action.
The start page has no club or version footer. See
[docs/prds/start-hero-empty-states.md](prds/start-hero-empty-states.md)
and [docs/prds/personal-start-chrome.md](prds/personal-start-chrome.md).

The editor can show this control as OSCAL JSON (copy locally). Export is
a split **Save OSCAL (.json)** button. See
[docs/prds/oscal-panel-export.md](prds/oscal-panel-export.md).

Workspace and Guide are the view tabs; AI drafting is a status chip.
Light / Dark / System theming defaults to the OS. Accent fills are indigo
on cool-gray canvases. See
[docs/prds/theme-ai-chip.md](prds/theme-ai-chip.md) and
[docs/prds/indigo-theme.md](prds/indigo-theme.md).

The open workspace hides Start-only chrome. The editor leads with the
control statement; Risk sits under extras. Guide is a single column.
See [docs/prds/workspace-guide-declutter.md](prds/workspace-guide-declutter.md).

The 2026-10-06 authoring app shell rebuilt Workspace around a sidebar,
writing column, and properties/review panel. See
[docs/prds/ui-overhaul.md](prds/ui-overhaul.md) and
[ADR 0007](adr/0007-authoring-app-shell.md). The primary nav is three
destinations: Home, Risk Entry, Policy Clause
([three-tab-nav.md](prds/three-tab-nav.md),
[ADR 0017](adr/0017-three-tab-nav.md)).

Accepted statements also land in a device-wide Statement library, reusable
across projects on this machine. See
[docs/prds/statement-library.md](prds/statement-library.md) and
[ADR 0009](adr/0009-device-wide-statement-library.md).

Library follows GRC SaaS IA (statement list + detail slide-over) adapted
from Vanta Mobbin flows. The Risks Library vs Register surfaces were
removed ([ADR 0011](adr/0011-no-risk-register.md)). Identified risks
returned as input only
([identified-risks-as-input.md](prds/identified-risks-as-input.md)). See
[docs/prds/vanta-grc-surfaces.md](prds/vanta-grc-surfaces.md) and
[ADR 0010](adr/0010-vanta-grc-surfaces.md).

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| giga.ai (not on Mobbin) | https://giga.ai | Landing: short headline, whitespace, product visual, one proof, trust badges, closing CTA |
| Railway landing | https://mobbin.com/screens/bc1febcc-0367-485b-8a9b-4f2df7d6e78a | Landing: short headline, two CTAs, product visual below |
| Langdock landing | https://mobbin.com/screens/b3db08cc-9aa6-43a7-9beb-436148558a52 | Landing: whitespace-heavy structure |
| Pin landing | https://mobbin.com/screens/815f7685-3c6a-4827-90dd-ca32d94119ab | Landing: short headline and product visual |
| Sprig — start cards | https://mobbin.com/screens/77add735-ba8c-4f49-a512-fabd8b2e1826 | Landing: two large start cards, one recommended |
| Klaviyo — headline + flow | https://mobbin.com/screens/88633529-5820-4f59-93e0-98d0806ad4fd | Landing: one headline, then a simple node flow |
| Microsoft Copilot — How it works | https://mobbin.com/screens/ebac045b-3c68-4dd0-8811-1ce2a31aaf05 | Landing: generous whitespace, one idea |
| fal — path choice | https://mobbin.com/screens/484439bd-e04c-4d68-b977-acfc6937eebe | Landing: two path cards as the only primary |
| Krea AI — single prompt + Generate | https://mobbin.com/screens/323e22c9-d758-4bf1-aee3-dcc9e284a2ef | Start: one hero input, one primary |
| Gamma — example prompts | https://mobbin.com/screens/23a25ddc-5d71-44d3-af2b-ff2ea0ec1767 | Start: quiet example under the input |
| Arcade — empty output | https://mobbin.com/screens/7b9d6805-0331-41c2-b7aa-165ea081bb09 | Empty pane: icon + line + next step |
| Browserbase — JSON + copy | https://mobbin.com/screens/ae95ee59-43fe-4173-887a-c3542d08c9c8 | Control OSCAL panel + copy |
| Mistral AI — code tabs | https://mobbin.com/screens/911ba1b2-a744-4359-832b-451758afbd09 | Statement / JSON tabs, copied status |
| Claude — copy + publish | https://mobbin.com/screens/587db0a6-6f7d-4a6a-b1ac-80ea594f7c7a | One copy + one primary save |
| Adaline — settings chips | https://mobbin.com/screens/80e3ebce-e59f-45a5-a6c5-7d9755ec4ef5 | AI as a status chip, not a tab |
| Twenty — Light / Dark / System | https://mobbin.com/screens/bee89cac-9a8a-4f5c-a0ef-90a26ec69658 | Three-way theme choice |
| Better Stack — Look & Feel | https://mobbin.com/screens/47f13a6b-5547-4aa6-bb4d-b8aa640e35d8 | Compact theme picker |
| Adaline — pass/fail on dark | https://mobbin.com/screens/081e7212-d5b4-4ca3-928c-d8a62f637b64 | Status colour with a text label |
| Linear — dark issue list | https://mobbin.com/screens/e142df2a-3527-499c-8f81-1b715947ac0c | Cool near-black canvas, indigo accent |
| Linear — dark product + app | https://mobbin.com/screens/18191caa-a25c-4c43-a7d2-0f6e52b444b1 | Dark raised surfaces |
| Linear — light settings | https://mobbin.com/screens/4c62cf9f-feb8-4928-b62d-84585be57b07 | Cool gray + white, indigo control |
| Linear — indigo toggle on light | https://mobbin.com/screens/c7223b87-8318-4848-8453-2ac4b1e1a0a9 | Indigo fill for the on state |
| Linear — Light / Dark / System | https://mobbin.com/screens/abf277ec-d00a-4504-8cfa-54930315f0ab | Same accent in both appearances |
| Twenty — light canvas | https://mobbin.com/screens/11590444-bb89-4836-88d5-1c8a83df041c | Cool gray page, white writing surface |
| Uxcel — one theory block | https://mobbin.com/screens/3c72f6e0-becb-4ad2-840c-09479eb71585 | Guide: one column, whitespace |
| Linear — inbox + issue | https://mobbin.com/screens/beb9d6b3-ec34-46d7-9332-320fcb32a338 | Workspace: quiet list, title as hero |
| Grok — files + document | https://mobbin.com/screens/b9b4d3ed-593b-46f1-8f25-326edc5eae68 | Workspace: compact list, large editor |
| Mintlify — intro + stacked cards | https://mobbin.com/screens/d4ce0aef-c205-432b-8f31-b4267315dc35 | Guide: single column, one card per idea |
| LangChain — numbered quickstart | https://mobbin.com/screens/568fff70-41fd-4660-a3b6-eb843e6e14d9 | Guide: stacked sections, short labels |
| Vanta — add a control | https://mobbin.com/flows/539b1513-fc0c-4085-929a-4aea4c453860 | From library: split list + preview |
| Vanta — framework / control detail | https://mobbin.com/flows/280ae4f2-78b0-4e33-8ba3-b72c8c7685a8 | Library: list + detail slide-over |
| Vanta — risk scenario → recommended controls | https://mobbin.com/screens/c5d6df8f-69b2-4729-950d-c0fc5b6a20e6 | Identified risk → suggested library statements dialog |
| Vanta — control detail mapped elements | https://mobbin.com/screens/a31c2c1c-11e7-468f-8751-16bc93561d89 | Control: mapped identified risks |
| Vanta — related controls table | https://mobbin.com/screens/615f46f7-bdab-47fd-b1ef-93a03da670e4 | Coverage table: risk / control, uncovered and unlinked flags |
| Snowflake — wizard stepper | https://mobbin.com/screens/01219fec-3d72-4a0a-a10f-5e7e119942e7 | Numbered steps with current / complete state |
| SoundCloud — per-step guide + required fields | https://mobbin.com/screens/44ede9ee-7c41-4422-acc9-8c63adfae176 | What / why / example / mistakes; inline required-field errors |
| DoorDash Merchant — two start choices | https://mobbin.com/screens/2fd80f67-ebf0-4615-a9d0-74099c07498e | Recommended path vs alternative on start |

## Constraints that new work must keep

- OSCAL 1.1.2 as the catalog format and save file ([ADR 0002](adr/0002-oscal-1-1-2.md)).
- Local-only privacy model ([ADR 0003](adr/0003-local-only-privacy-model.md)).
- Ollama localhost-only ([ADR 0004](adr/0004-ollama-localhost-only.md)).
- No IM8 (or similar) mapping surface without a new ADR that supersedes
  [ADR 0005](adr/0005-remove-im8-mapping.md).
- Clause-only happy-path input ([ADR 0006](adr/0006-clause-only-input.md)):
  no Title field; clause numbers are not required or shown.
- Device-wide statement library is a separate `codify:statements` store, not
  the catalog ([ADR 0009](adr/0009-device-wide-statement-library.md)).
- No risk register ([ADR 0011](adr/0011-no-risk-register.md)). Identified
  risks are input, not a register
  ([ADR 0012](adr/0012-identified-risks-as-input.md)); the web wizard
  requires them for Review and export
  ([ADR 0013](adr/0013-risk-first-authoring-flow.md)). Statement library
  list + detail slide-over remains ([ADR 0010](adr/0010-vanta-grc-surfaces.md)).
- Standard-library runtime for the package; optional `dev` / `e2e` only for
  tests.

## How we change this PRD

Feature work that extends or narrows the above gets its own
`docs/prds/<feature>.md` (see [prd-template.md](templates/prd-template.md))
and, if it decides something durable, an ADR. Update this page when the
shipped product changes.
