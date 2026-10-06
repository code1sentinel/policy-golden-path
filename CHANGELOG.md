# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Seeded from git history and merged pull requests on 2026-10-04.
There are no release tags; version numbers match `src/codify/__init__.py`.

## [Unreleased]

### Added

- Authoring app shell ([ADR 0007](docs/adr/0007-authoring-app-shell.md)):
  collapsible sidebar (Workspace, Clauses, Risks, Catalog, Export, Guide),
  breadcrumb, centred writing column, properties/review panel, Catalog
  table, export dialog, and `⌘`/`Ctrl`+Enter to accept.
- Development workflow: `AGENTS.md`, product PRD, ADRs, slice issue template,
  pull request template, `CONTRIBUTING.md`, and retro/PRD templates.
- CI jobs for `ruff`, `mypy` (lenient), `pip-audit`, and `gitleaks`. Existing
  test, e2e, and OSCAL schema jobs are unchanged.

### Changed

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

### Removed

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
