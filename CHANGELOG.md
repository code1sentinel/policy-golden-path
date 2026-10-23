# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Seeded from git history and merged pull requests on 2026-10-04.
There are no release tags; version numbers match `src/codify/__init__.py`.

## [Unreleased]

### Changed

- Policy clause (Flow B step 1) is a calm capture page: **Paste your
  policy clause**, one guidance sentence, a large paste textarea, a
  small side example of a good clause and how to separate several with a
  blank line, a preview list (edit / remove), optional **Add details**
  for a source policy name, and **Continue to control statements**
  disabled until at least one clause exists. The same small three-step
  indicator as Identify risks (Policy clause current). Codify, Try an
  example, Open a file, pre-filled example text, and the result step are
  gone from this page. Old clause-first projects open here. Control
  statements still uses **…for each clause**. OSCAL export is unchanged
  ([docs/prds/policy-clause-page.md](docs/prds/policy-clause-page.md),
  [ADR 0018](docs/adr/0018-policy-clause-page.md)).

- First visit is a short giga-style landing
  ([docs/prds/giga-landing.md](docs/prds/giga-landing.md)): headline
  **Controls you can test.**, one subline, two equal start buttons
  (**Get started with identified risks** and **Get started with an
  existing policy clause**) with **Private by design**, the risk →
  control → OSCAL → Rego example, one factual how-it-works statement,
  a trust strip (NIST 800-53, ISO 27001, OSCAL 1.1.2, runs in your
  browser, no data leaves your device), contribute links, and a closing
  CTA. No SOC 2 or ISO certification claims. No GRC Engineering Club
  branding. No new outbound calls.

- Control statements (shared step 2) is a split drafting page: **Write
  a control statement for each risk** (or **…for each clause**), one
  guidance sentence, a collapsible writing tip, a left list with
  coverage dots, a right editor (add / edit / remove statements, quiet
  **Insert from library**), a progress line, and **Continue to policy
  as code** disabled until every item has a statement. The same small
  three-step indicator as Identify risks; Back returns to the previous
  step. Wizard guide, Previous / Next, optional clause fields, and
  library panels are gone from this page. Treats-risk links and OSCAL
  export are unchanged
  ([docs/prds/control-statements-page.md](docs/prds/control-statements-page.md),
  [ADR 0016](docs/adr/0016-control-statements-page.md)).

- Authoring nav is three destinations: **Home**, **Risk Entry**, and
  **Policy Clause**
  ([docs/prds/three-tab-nav.md](docs/prds/three-tab-nav.md),
  [ADR 0017](docs/adr/0017-three-tab-nav.md)). Catalog, Library, Risks,
  Export, and Guide are no longer tabs; export, Insert from library, and
  per-step guides stay in the flows. The three labels sit on one row at
  390px. The landing hero uses two equal-weight start buttons: **Get
  started with identified risks** (primary) and **Get started with an
  existing policy clause** (visible secondary), with **Private by
  design** next to them; they stack on a 390px screen. No GRC
  Engineering Club branding. No new outbound calls.

- First visit was a Base-style marketing landing
  ([docs/prds/marketing-landing.md](docs/prds/marketing-landing.md)),
  superseded by the giga-style restyle above.

### Added

- Risk-first authoring flow ([ADR 0013](docs/adr/0013-risk-first-authoring-flow.md)):
  two start paths — **Start from risks** (recommended) or
  **Start from a policy clause**. Both share Review and **Send to Enact**.
  A stepper and a dismissible per-step guide sit on every step. Web export
  is blocked until every identified risk has an accepted control statement
  and every control is linked. Old clause-first projects open on the clause
  path and prompt for risks. CLI export is unchanged. No new outbound calls.

- Identified risks as input to control authoring
  ([ADR 0012](docs/adr/0012-identified-risks-as-input.md)): a project holds
  a simple list (`id`, short statement, optional note). Controls may link
  to those ids; “risk it treats” displays the linked statement. Coverage
  flags uncovered risks and unlinked controls. Matching Statement library
  entries are suggested locally; optional AI assist may also suggest
  through the existing `ai_prompt` / `ai_reply` path. OSCAL export traces
  links with `identified-risk-id` resources, `treats-risk` props, and
  `rel=related`. This is not a register (no scores, owners, or
  `--risks`). Older saves still load with an empty list.

- Site Git Sync: `docs/book/gitbook-docs.yaml` maps the curated book as
  the Codify site's single space (project directory `docs/book`, branch
  `main`). Repo-root `.gitbook.yaml` is unchanged for single-space sync.
  Schema and format follow
  [GitBook content configuration](https://gitbook.com/docs/docs-as-code/git-sync/content-configuration)
  and [monorepos](https://gitbook.com/docs/docs-as-code/git-sync/monorepos).
- GitBook-ready user and contributor documentation in `docs/book/`,
  selected by `.gitbook.yaml` so Git Sync publishes the curated book
  rather than every PRD. Screenshots of the live app (built-in example
  only) sit under `docs/book/assets/`.
- Agent skills adapted from [mattpocock/skills](https://github.com/mattpocock/skills)
  (MIT, commit `49dd158d1076134a641b33efb035946536778336`):
  `.cursor/skills/diagnosing-bugs/`, `.cursor/skills/tdd/`, and
  `.cursor/skills/code-review/`. Attribution in `THIRD_PARTY.md`.
- Second first-time walkthrough polish: Accepted ✓ + Next control
  primary with Undo accept; `[N]` set-this-value prompts; visible count
  breakdown and “and N more” on first look; visible OSCAL / Catalog vs
  Library lines; grouped optional library export. See
  [docs/prds/second-walkthrough-polish.md](docs/prds/second-walkthrough-polish.md).
- First-run clarity for GRC reviewers: real editable example text on
  Start, a “here’s what we drafted” result step after paste or Try an
  example, one primary Accept, plain-language review labels and score
  help, a Recommended OSCAL export, and dotted-underline glossary terms
  for OSCAL / Catalog / Library. See
  [docs/prds/first-run-clarity.md](docs/prds/first-run-clarity.md).
- First-visit welcome splash (Linear-style hierarchy, Codify tokens):
  centered mark, “Welcome to Codify”, one lede, **Get started**. Dismiss
  is stored as `codify:splash-seen`; a saved project skips the splash so
  resume stays instant. See [docs/prds/welcome-splash.md](docs/prds/welcome-splash.md).
- Device-wide Statement library ([ADR 0009](docs/adr/0009-device-wide-statement-library.md)):
  after Accept, the statement is saved on this device (deduped by
  normalized text), reusable from **Library** or **From library** in the
  editor. Search, remove, and export CSV/JSON locally. Separate
  `codify:statements` key; the OSCAL catalog stays the per-project save.
- Authoring app shell ([ADR 0007](docs/adr/0007-authoring-app-shell.md)):
  collapsible sidebar (Workspace, Clauses, Catalog, Library, Export, Guide),
  breadcrumb, centred writing column, properties/review panel, Catalog
  table, export dialog, and `⌘`/`Ctrl`+Enter to accept.
- Development workflow: `AGENTS.md`, product PRD, ADRs, slice issue template,
  pull request template, `CONTRIBUTING.md`, and retro/PRD templates.
- CI jobs for `ruff`, `mypy` (lenient), `pip-audit`, and `gitleaks`. Existing
  test, e2e, and OSCAL schema jobs are unchanged.

### Changed

- Identify risks (Flow A step 1) is a single capture page: **What
  risks have you identified?**, one guidance sentence, a collapsible
  writing tip, an inline list (Enter adds, Esc cancels, edit in place,
  optional note, remove), a friendly empty state, and **Continue to
  control statements** disabled until at least one risk exists. A small
  three-step indicator matches the landing; **Back to the landing**
  returns to the marketing landing. The shared wizard guide, Previous / Next,
  and risk-id pills are gone from this page. `{id, statement, note?}`
  and the OSCAL risk export are unchanged
  ([docs/prds/identify-risks-page.md](docs/prds/identify-risks-page.md),
  [ADR 0015](docs/adr/0015-identify-risks-page.md)).

- Landing diagrams and first-run copy name the last step **Policy as
  code (Rego)** instead of a bare **Enact**
  ([docs/prds/technical-policy-rego-label.md](docs/prds/technical-policy-rego-label.md)).
  A muted caption: *Exported as OSCAL and tested as Rego in Enact*
  (Enact still links to the Enact app). **Send to Enact** stays the
  action, with helper text that it turns control statements into
  testable Rego policy. No new outbound calls.

- Landing is only the two flows, side by side
  ([docs/prds/landing-flow-cards.md](docs/prds/landing-flow-cards.md)):
  Identify risk → Control statement (→ Enact), and Policy clause →
  Control statement (→ Enact). Each card has a mini step diagram and
  **Get started**. A saved project keeps a small **Resume** link. The
  headline, shared diagram, Recommended kicker, docs link, and Open a
  saved project are gone. No new outbound calls.
- Identified-risk OSCAL export writes assessment-style fields on each
  catalog back-matter resource: short `title`, `description` /
  `statement`, and `status=open` ([ADR 0014](docs/adr/0014-oscal-identified-risk-statements.md)).
  Controls still use `treats-risk` and `rel=related`. Status is
  export-only; `project.risks` stays `{id, statement, note?}`. CI
  validates the identified-risk catalog against NIST OSCAL 1.1.2.

- One landing instead of a splash plus a start screen
  ([docs/prds/landing-start.md](docs/prds/landing-start.md)). The
  headline is *Codify turns what you need to address into clear control
  statements, which you then test in Enact.* A simple flow shows the two
  ways in meeting at control statements, then Enact. The only primary
  actions are **Start from risks** (recommended) and **Start from a
  policy clause**; they open the existing paths from PR #38. Resume (or
  open a saved project) and a docs link are quiet secondary. The setup
  checklist and `#28` splash (`codify:splash-seen`) are gone. No new
  outbound calls.
- `AGENTS.md` trimmed to a one-line description, unusual commands, and
  pointers. Detailed rules live in `.cursor/rules/` (glob-scoped where
  they apply to one surface). TDD refactor-while-green moved into the
  code-review skill. The PR template now asks for a summary sketch,
  before/after evidence, and merge danger (one-way vs two-way door and
  blast radius).
- Review screen shows Action / Scope / Limit / Purpose once; remaining
  gaps after Accept are optional improvements. The stage strip is status,
  not links. Sidebar Workspace opens the start/paste view. Pasted
  projects are named from the first clause (editable), not “pasted
  text”. Library shows each statement once. Export no longer calls OSCAL
  a “save file”.
- Workspace header no longer appends a literal `null`. Counts now read as
  control drafts from requirements, and say why other clauses were not
  converted. Purpose hints match the statement instead of always using a
  brute-force example.
- Library follows GRC SaaS patterns from Vanta Mobbin flows
  ([ADR 0010](docs/adr/0010-vanta-grc-surfaces.md)): a statement list +
  detail slide-over. Draft, Catalog, and Export keep the same indigo
  tokens. No new stores or outbound calls.
- Happy path is clause text only ([ADR 0006](docs/adr/0006-clause-only-input.md)):
  unnumbered paragraphs are clauses, a leading number stays in the pasted
  text, and OSCAL control ids/titles are minted internally.
- Local `codify-web` uses the system font stack and no longer loads
  Inter from Google Fonts. The Pages build no longer needs to strip
  those links ([ADR 0003](docs/adr/0003-local-only-privacy-model.md)).
- Start screen: the clause textarea is the hero with one **Codify**
  primary. The Acme demo is a quiet **Try an example** chip. Empty
  editor and filter panes offer **Open first draft** and **Show all**.
- Workspace and Guide are quieter: the statement is the editor hero,
  Risk sits in extras, Guide is a single column, and the club/version
  footer is gone. The 2026-10-06 overhaul then replaced the page chrome
  with the authoring app shell.
- Editor tabs **Statement | OSCAL JSON** show this control's OSCAL with
  line numbers and a local **Copy**. **Export** is a dialog of download
  targets (OSCAL, Excel, CSV, report).
- Light / Dark / System theme (defaults to the OS, stored as
  `codify:theme`). AI drafting is a status chip, not a view tab.
  Accent and canvas tokens are indigo on cool gray in both themes.
  Contrast tokens meet WCAG 2.2 AA.

### Fixed

- GitBook pages no longer use relative paths that leave `docs/book/`.
  Those targets now use GitHub URLs (`blob`/`tree` on `main`), matching
  the Enact book, so they still resolve after Git Sync publishes only
  that folder. A pytest check fails if a book page grows another
  escaping relative link.

### Removed

- Local risk register ([ADR 0011](docs/adr/0011-no-risk-register.md)):
  Risks nav and views, scenario drafting, register import, Risk register
  export, CLI `--risks`, and OSCAL risk tracing. GRC engineering practice
  is to engineer risk (controls, checks, automation) rather than maintain
  it as a static artifact. Older `codify:project` saves and catalogs still
  open: leftover `risks` / `risk-id` fields are dropped; clauses, controls
  (including the purpose field), and `codify:statements` stay.
- Start-page footer that named the GRC Engineering Club Singapore and
  the app version. MIT remains in LICENSE and README.
- Optional Title field on the start form and the `title` argument on
  `open`. Clause numbers are no longer required or shown in the workspace.

## [1.2.1] - 2026-10-02

### Added

- Playwright browser tests against `codify-web` and the Pyodide site; four
  fixes they drove (purpose parsing, mapping preserved on redraft, mapped
  notice lifecycle, unique editor ids).
- Ollama as a key-free local AI provider at `http://localhost:11434`
  ([#1](https://github.com/code1sentinel/policy-golden-path/pull/1)).

### Changed

- Workspace polish: split list/editor, floating selection bar, clearer AI
  dialog (ready / needs-key) ([#2](https://github.com/code1sentinel/policy-golden-path/pull/2)).
- Decluttered the happy path: short start page, requirement clauses first,
  control statement as the editor hero, filters and bulk under More
  ([#3](https://github.com/code1sentinel/policy-golden-path/pull/3)).

### Removed

- IM8 Reform mapping, coverage view, bundled catalog, and export columns
  ([#4](https://github.com/code1sentinel/policy-golden-path/pull/4)).

## [1.2.0] - 2026-10-02

### Added

- Map drafted controls to Singapore's IM8 Reform catalog, coverage and gaps
  view, and IM8 columns in exports. Later removed in 1.2.1.

## [1.1.0] - 2026-10-01

### Added

- Optional AI drafting with a bring-your-own key (Anthropic, OpenAI, Gemini).
  One clause per request from the browser; keys never enter the project.
- Default Claude model Sonnet 5.5; any model the account has can still be
  entered.

## [1.0.0] - 2026-10-01

### Added

- First Codify release: sort legacy clauses, draft control statements from
  rules, score them against OSCAL-oriented criteria, review/accept, export
  an OSCAL 1.1.2 catalog (the save file), Excel, CSV, and a conversion
  report.
- CLI (`codify`), local web app (`codify-web`), and a browser-only GitHub
  Pages site via Pyodide.
- Acme demo policy and key as the regression hold.

[Unreleased]: https://github.com/code1sentinel/policy-golden-path/compare/main...HEAD
