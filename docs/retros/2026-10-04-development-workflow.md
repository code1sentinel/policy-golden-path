# Retro: development workflow

| Field | Value |
| --- | --- |
| Date | 2026-10-04 |
| Feature / PRD | Process and docs only; product baseline captured in `docs/prd.md` |
| Slices / PRs | This change |

## What we shipped

AGENTS.md, PRD + template, ADRs 0001–0005, slice and PR templates (with
Mobbin design-reference fields), CHANGELOG seeded from merged PRs,
CONTRIBUTING.md, CI jobs for ruff / mypy / pip-audit / gitleaks.

## What went well

The product constraints (OSCAL 1.1.2, local-only, localhost Ollama, no IM8)
were already visible in code, tests, and PR #1–#4, so the ADRs did not need
invention.

## What was painful

No prior PRD or changelog, so the baseline had to be reverse-engineered.
Granola was not authenticated in this environment, so meeting context was
not available.

## Lessons to fold into the templates

| Lesson | Template to change |
| --- | --- |
| UI work without Mobbin links will drift; ask, do not invent | Already in AGENTS.md, PRD template, slice template, PR template |
| Type-checking a mostly untyped tree must start lenient or CI is red on day one | `pyproject.toml` `[tool.mypy]` — tighten in a later slice |
| Fake keys in e2e (`sk-test`) need an explicit gitleaks allowlist | `.gitleaks.toml` |

## Follow-ups

- Tighten mypy and ruff in dedicated slices, not by reformatting the package
  in a process PR.
- Add the first OSCAL golden file when the next slice changes catalog output.
