# Contributing

The contract for agents and humans is [`AGENTS.md`](../../AGENTS.md). The short version is [`CONTRIBUTING.md`](../../CONTRIBUTING.md). This page is a pointer, not a second contract.

## Start from a PRD

Product behaviour is defined by [`docs/prd.md`](../prd.md) and feature PRDs under [`docs/prds/`](../prds/). Copy [`docs/templates/prd-template.md`](../templates/prd-template.md). Scope, users, success criteria, and out of scope must be explicit.

UI work needs **Design references**: Mobbin (`mobbin.com`) screen links in the PRD or slice issue **before** implementation. If none were provided, stop and ask. Do not invent a layout.

## Decisions

Do not silently reverse an accepted ADR. Read [Decision records](decisions.md) and the files in [`docs/adr/`](../adr/).

## One slice, one PR

Open a slice issue from [`.github/ISSUE_TEMPLATE/slice.yml`](../../.github/ISSUE_TEMPLATE/slice.yml): user story, Given / When / Then, test plan, out of scope, and Mobbin links when the slice touches UI.

Link the issue from the PR. Use [`.github/pull_request_template.md`](../../.github/pull_request_template.md).

## TDD

1. Write a failing test from the slice's Given / When / Then.
2. Implement the smallest change that makes it pass.
3. Refactor with tests still green.

Hold Codify to the Acme key (`examples/acme-policy-key.md`, `tests/test_acme.py`) whenever classification or drafting changes. Any change that writes OSCAL needs a golden-file test under `tests/goldens/` **and** NIST OSCAL 1.1.2 schema validation. Do not add network calls in unit tests. Do not weaken existing tests to make a slice pass.

## Cursor rules and skills

[`AGENTS.md`](../../AGENTS.md) is the in-repo contract. This repository does not currently ship a `.cursor/rules` tree or in-repo skills — follow `AGENTS.md` and `CONTRIBUTING.md` so local Cursor rules stay aligned with the repo.

## Commands

```
pip install -e ".[dev]"
pytest
ruff check src tests scripts
mypy src
```

Browser tests: `pip install -e ".[e2e]"`, then `python -m playwright install chromium` and `pytest tests/e2e`.

CI must be green (`test`, `e2e`, `oscal-schema`, `lint`, `types`, `security`). Nothing merges on red.

## Privacy on every PR

No new outbound network calls, origins, or leave-device paths unless an ADR explains why. Do not write API keys into the project, catalog, library, or exports.

## After merge

Update `README.md` and `CHANGELOG.md` in the PR. When a whole feature (not just one slice) is done, write a retro at `docs/retros/` from [`docs/templates/retro-template.md`](../templates/retro-template.md).
