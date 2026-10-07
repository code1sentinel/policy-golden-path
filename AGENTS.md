# Codify agent and contributor rules

Codify turns legacy policy clauses into OSCAL 1.1.2 control statements. It
ships as a CLI (`codify`), a local web app (`codify-web`), and a GitHub Pages
site. Policy data stays on the person's device. Optional AI drafting is
opt-in: cloud providers with a key the person supplies, or Ollama on
`http://localhost:11434` only.

This file is the contract for every coding agent and human. Product behaviour
is defined by the PRD and ADRs, not by improvisation.

## 1. Start from a PRD

Every feature starts from [`docs/prd.md`](docs/prd.md) (the product as it is
today) or a feature PRD at `docs/prds/<feature>.md`.

- Copy [`docs/templates/prd-template.md`](docs/templates/prd-template.md).
- Scope, users, success criteria, and out of scope must be explicit.
- UI features must list **Design references**: Mobbin (`mobbin.com`) screen
  links. If none were provided, **stop and ask**. Do not invent a layout from
  scratch. Search Mobbin (the Mobbin MCP tools, when available) and wait for
  agreement before implementing.

## 2. Record decisions as ADRs

Architecture and product decisions go in `docs/adr/NNNN-title.md`, numbered
from the next free integer. Follow
[`docs/adr/0001-record-architecture-decisions.md`](docs/adr/0001-record-architecture-decisions.md).
Do not silently reverse an accepted ADR.

Relevant decisions already on file:

- [`0002-oscal-1-1-2.md`](docs/adr/0002-oscal-1-1-2.md)
- [`0003-local-only-privacy-model.md`](docs/adr/0003-local-only-privacy-model.md)
- [`0004-ollama-localhost-only.md`](docs/adr/0004-ollama-localhost-only.md)
- [`0005-remove-im8-mapping.md`](docs/adr/0005-remove-im8-mapping.md)
- [`0006-clause-only-input.md`](docs/adr/0006-clause-only-input.md)
- [`0007-authoring-app-shell.md`](docs/adr/0007-authoring-app-shell.md)
- [`0008-risk-input-and-oscal-tracing.md`](docs/adr/0008-risk-input-and-oscal-tracing.md)
- [`0009-device-wide-statement-library.md`](docs/adr/0009-device-wide-statement-library.md)
- [`0010-vanta-grc-surfaces.md`](docs/adr/0010-vanta-grc-surfaces.md)

## 3. Thin vertical slices, one PR each

Split work into the smallest slice that delivers a complete path (input →
behaviour → test → docs). Track each slice as a GitHub issue using
[`.github/ISSUE_TEMPLATE/slice.yml`](.github/ISSUE_TEMPLATE/slice.yml).

Every slice issue must include:

- a user story
- Given / When / Then acceptance criteria
- a test plan
- out of scope
- **Design references** (Mobbin links) when the slice touches UI

One issue → one PR. Link the issue from the PR.

## 4. TDD per slice

1. Write a failing test from the slice's Given / When / Then.
2. Implement the smallest change that makes it pass.
3. Refactor with tests still green.

Rules for this repo:

- Hold Codify to the Acme key (`examples/acme-policy-key.md`,
  `tests/test_acme.py`) whenever classification or drafting changes.
- Any change that writes OSCAL must add or update a golden-file test (expected
  catalog JSON under `tests/goldens/`) **and** stay valid against NIST's OSCAL
  1.1.2 catalog schema (`scripts/validate_oscal.mjs`, the `oscal-schema` CI
  job).
- Do not add network calls in unit tests. E2E tests fake AI providers.
- Do not weaken existing tests to make a slice pass.

## 5. CI must be green

Nothing merges on red. A PR is not done while `CI` is failing.

Required gates (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)):

| Job | What it proves |
| --- | --- |
| `test` | `pytest` on Python 3.10, 3.12, and 3.13, plus CLI smoke on the Acme policy |
| `e2e` | Playwright against `codify-web` and the Pyodide site |
| `oscal-schema` | exported catalogs validate against NIST OSCAL 1.1.2 |
| `lint` | `ruff check` |
| `types` | `mypy` (lenient today; tighten as annotations grow) |
| `security` | `pip-audit` and `gitleaks` |

Pages deploy (`.github/workflows/pages.yml`) runs on `main` only.

## 6. Review every PR against the checklist

Use [`.github/pull_request_template.md`](.github/pull_request_template.md).
Reviewers check the same list: linked issue, what/why, tests, acceptance
criteria, no new outbound calls, docs and CHANGELOG, Mobbin citations and
before/after screenshots if UI changed.

## 7. Definition of done

A slice is done only when all of these are true:

- the PR is merged to `main`
- CI was green on the merge commit
- if the UI or Pages site changed, a demo is recorded or Pages will pick up
  the change on deploy
- `README.md` and `CHANGELOG.md` are updated
- the GitHub issue is closed
- a short retro note is written at `docs/retros/YYYY-MM-DD-<feature>.md`
  (copy [`docs/templates/retro-template.md`](docs/templates/retro-template.md))
- lessons from the retro that change how we work are folded into the templates
  in this file, the PRD template, the slice template, or the PR template

## 8. UI changes need Mobbin references

Any frontend or UI change (HTML, CSS, workspace layout, dialogs, empty
states, Pages chrome) must cite Mobbin screen links in the PRD or slice
issue **before** implementation.

- If the request has no Mobbin links, ask for them. Do not invent a design.
- Cite the links in the PR. Attach before/after screenshots.
- Adapt patterns to Codify's existing dark workspace. Do not copy branding.
- Privacy chrome (no new third-party requests, no policy upload) is not
  negotiable for a prettier layout.

## Commands

Install (Python 3.10+; the package itself has no runtime dependencies):

```bash
pip install -e ".[dev]"
```

Tests:

```bash
pytest                  # unit and integration; skips tests/e2e without Playwright
pytest -q               # CI shape
pytest tests/test_acme.py
```

Browser tests:

```bash
pip install -e ".[e2e]"
python -m playwright install chromium
pytest tests/e2e                                   # against codify-web
CODIFY_SITE=site pytest tests/e2e                  # against a site from build_site.py
```

Lint and types:

```bash
ruff check src tests scripts
mypy src
```

OSCAL schema (same check as CI; needs Node 20 and a network fetch of the schema):

```bash
mkdir -p out
codify examples/acme-information-security-policy-2016.md -f oscal -o out/acme-md.json
curl -sSLf -o out/schema.json \
  https://github.com/usnistgov/OSCAL/releases/download/v1.1.2/oscal_catalog_schema.json
npm install --no-save --silent ajv@8 ajv-formats@3
node scripts/validate_oscal.mjs out/schema.json out/acme-md.json
```

Dependency and secret scan:

```bash
pip-audit --skip-editable    # in a clean venv or CI; do not audit the system Python
gitleaks detect --source . --redact --config .gitleaks.toml
```

Run the product:

```bash
codify examples/acme-information-security-policy-2016.md
codify examples/acme-information-security-policy-2016.md -f oscal -o out.json
codify-web --open          # http://127.0.0.1:8765/ — this machine only
```

Build the Pages site locally:

```bash
npm pack pyodide@314.0.7 && tar xzf pyodide-314.0.7.tgz
python scripts/build_site.py --pyodide package --out site
python -m http.server --directory site
```

## Privacy and security (do not regress)

- Default path: the policy never leaves the device. Rule drafts use no AI.
- `codify-web` binds to `127.0.0.1`, has no authentication, refuses
  cross-origin POSTs, and keeps nothing on disk.
- The Pages site runs Python in the browser via Pyodide served from the site.
  Do not add third-party script, font, or analytics hosts to the site build
  or to `codify-web`. Both use the system font stack.
- CSP `connect-src` may include only `'self'`, the three opt-in cloud AI
  origins, and `http://localhost:11434` / `http://127.0.0.1:11434`.
- Ollama is localhost only. Do not point it at a remote host.
- AI keys stay in the browser (tab, or optional device remember). Never write
  a key into the project, autosave, catalog, library, or exports.
- No new outbound network calls without an ADR and a PR privacy check.

## Layout (where to change things)

```
src/codify/clauses.py    read a policy into clauses
src/codify/classify.py   sort clauses and find duplicates
src/codify/draft.py      rule-based drafting
src/codify/control.py    statement check and parts
src/codify/library.py    device-wide statement library (normalize, upsert, export)
src/codify/project.py    project + OSCAL catalog
src/codify/ai.py         AI prompt and reply handling (no provider I/O)
src/codify/api.py        request API (server and browser)
src/codify/webapp.py     local server
src/codify/cli.py        command line
src/codify/static/       web app
```

More process detail: [`CONTRIBUTING.md`](CONTRIBUTING.md).
