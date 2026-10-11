# Contributing

[`AGENTS.md`](../../AGENTS.md) is the short index. Detailed rules live in [`.cursor/rules/`](../../.cursor/rules/); procedures live in [`.cursor/skills/`](../../.cursor/skills/). The human short version is [`CONTRIBUTING.md`](../../CONTRIBUTING.md). This page is a pointer, not a second contract.

## Start from a PRD

Product behaviour is defined by [`docs/prd.md`](../prd.md) and feature PRDs under [`docs/prds/`](../prds/). Copy [`docs/templates/prd-template.md`](../templates/prd-template.md). Scope, users, success criteria, and out of scope must be explicit.

UI work needs **Design references**: Mobbin (`mobbin.com`) screen links in the PRD or slice issue **before** implementation. If none were provided, stop and ask. Do not invent a layout.

## Decisions

Do not silently reverse an accepted ADR. Read [Decision records](decisions.md) and the files in [`docs/adr/`](../adr/).

## One slice, one PR

Open a slice issue from [`.github/ISSUE_TEMPLATE/slice.yml`](../../.github/ISSUE_TEMPLATE/slice.yml): user story, Given / When / Then, test plan, out of scope, and Mobbin links when the slice touches UI.

Link the issue from the PR. Use [`.github/pull_request_template.md`](../../.github/pull_request_template.md).

## TDD

Follow [`.cursor/skills/tdd/`](../../.cursor/skills/tdd/SKILL.md) and [`.cursor/rules/tdd.mdc`](../../.cursor/rules/tdd.mdc):

1. Write a failing test from the slice's Given / When / Then.
2. Implement the smallest change that makes it pass.
3. Refactor as a [code-review](../../.cursor/skills/code-review/SKILL.md) pass, with tests still green.

Hold Codify to the Acme key (`examples/acme-policy-key.md`, `tests/test_acme.py`) whenever classification or drafting changes. Any change that writes OSCAL needs a golden-file test under `tests/goldens/` **and** NIST OSCAL 1.1.2 schema validation ([`.cursor/rules/oscal-goldens.mdc`](../../.cursor/rules/oscal-goldens.mdc)). Do not add network calls in unit tests. Do not weaken existing tests to make a slice pass.

## Cursor rules and skills

| Path | What it covers |
| --- | --- |
| [`.cursor/rules/prd-adr-slices.mdc`](../../.cursor/rules/prd-adr-slices.mdc) | Start from a PRD, record ADRs, one issue → one PR |
| [`.cursor/rules/tdd.mdc`](../../.cursor/rules/tdd.mdc) + [`.cursor/skills/tdd/`](../../.cursor/skills/tdd/SKILL.md) | Red → green from the slice Given / When / Then |
| [`.cursor/skills/diagnosing-bugs/`](../../.cursor/skills/diagnosing-bugs/SKILL.md) | Failing tests, goldens, e2e, regressions |
| [`.cursor/skills/code-review/`](../../.cursor/skills/code-review/SKILL.md) | Standards vs Spec, including refactoring |
| [`.cursor/rules/privacy.mdc`](../../.cursor/rules/privacy.mdc) + [privacy-web](../../.cursor/rules/privacy-web.mdc) | No new outbound call without an ADR; never write an AI key |
| [`.cursor/rules/mobbin-ui.mdc`](../../.cursor/rules/mobbin-ui.mdc) | Mobbin citations before any UI work |
| [`.cursor/rules/oscal-goldens.mdc`](../../.cursor/rules/oscal-goldens.mdc) | Golden files + NIST 1.1.2 |
| [`.cursor/rules/ci-merge.mdc`](../../.cursor/rules/ci-merge.mdc) | CI gates and definition of done |

Adapted skills are attributed in [`THIRD_PARTY.md`](../../THIRD_PARTY.md).

## Commands

```
pip install -e ".[dev]"
pytest
ruff check src tests scripts
mypy src
```

Browser tests: `pip install -e ".[e2e]"`, then `python -m playwright install chromium` and `pytest tests/e2e`.

CI must be green (`test`, `e2e`, `oscal-schema`, `lint`, `types`, `security`). Nothing merges on red. See [`.cursor/rules/ci-merge.mdc`](../../.cursor/rules/ci-merge.mdc).

## Privacy on every PR

No new outbound network calls, origins, or leave-device paths unless an ADR explains why. Do not write API keys into the project, catalog, library, or exports.

## After merge

Update `README.md` and `CHANGELOG.md` in the PR. When a whole feature (not just one slice) is done, write a retro at `docs/retros/` from [`docs/templates/retro-template.md`](../templates/retro-template.md) and fold lessons into the templates, [`.cursor/rules/`](../../.cursor/rules/), or [`.cursor/skills/`](../../.cursor/skills/).
