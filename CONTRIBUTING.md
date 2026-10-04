# Contributing to Codify

The full contract for agents and humans is [`AGENTS.md`](AGENTS.md). This
page is the short version.

## Before you write code

1. Read [`docs/prd.md`](docs/prd.md). Feature work gets
   `docs/prds/<feature>.md` from
   [`docs/templates/prd-template.md`](docs/templates/prd-template.md).
2. Check [`docs/adr/`](docs/adr/) so you do not reverse a decision. New
   decisions go in `docs/adr/NNNN-title.md`.
3. Open a **slice** issue
   ([template](.github/ISSUE_TEMPLATE/slice.yml)): user story, Given / When
   / Then, test plan, out of scope.
4. **UI:** the PRD or slice must list Mobbin (`mobbin.com`) screen links.
   If none were provided, ask. Do not invent a design.

## While you write code

- One slice, one PR, linked to the issue.
- TDD: failing test from the acceptance criteria, then implement, then
  refactor.
- OSCAL output: golden file under `tests/goldens/` **and** NIST 1.1.2
  schema validation.
- No new outbound network calls unless an ADR says so.

## Commands

```bash
pip install -e ".[dev]"
pytest
ruff check src tests scripts
mypy src
codify-web --open
```

Browser tests: `pip install -e ".[e2e]"` then
`python -m playwright install chromium` and `pytest tests/e2e`.

More commands (OSCAL schema, Pages build, scans): [`AGENTS.md`](AGENTS.md).

## Review and merge

Use the [PR checklist](.github/pull_request_template.md). CI must be green
(`test`, `e2e`, `oscal-schema`, `lint`, `types`, `security`). Nothing
merges on red.

UI PRs cite the Mobbin references and attach before/after screenshots.

## After merge

- Update Pages comes for free on push to `main` if the site changed; attach
  a demo if you changed the UI.
- Touch `README.md` and `CHANGELOG.md` in the PR, not after.
- Close the issue.
- When the **feature** (all its slices) is done, write
  `docs/retros/YYYY-MM-DD-<feature>.md` and fold lessons into the templates.
