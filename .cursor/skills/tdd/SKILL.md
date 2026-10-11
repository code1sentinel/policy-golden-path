---
name: tdd
description: Test-driven development for features and bug fixes. Use when building a slice, adding a test, touching classification or drafting, writing OSCAL, or working red-green.
---

# Test-Driven Development

Adapted from [mattpocock/skills](https://github.com/mattpocock/skills)
`skills/engineering/tdd` at `49dd158d1076134a641b33efb035946536778336`
(MIT, Copyright 2026 Matt Pocock). Seams come from the PRD or slice
Given / When / Then — do not ask a human to confirm them. Examples are
pytest (and Playwright where the seam is the page). Refactoring is a
`code-review` pass, not part of this loop.

TDD is the red → green loop. This skill is the reference that makes that
loop produce tests worth keeping. Consult every section before and during
the loop, not after.

When exploring, read `GLOSSARY.md` if it exists so names match the
domain, and respect ADRs in the area you are touching.

## What a good test is

Tests verify behavior through public interfaces, not implementation
details. Code can change entirely; tests shouldn't. A good test reads
like a specification: "every requirement gets a draft except the
duplicate" tells you exactly what capability exists.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for
mocking guidelines.

## Seams: where tests go

A **seam** is the public boundary you test at. Tests live at seams,
never against internals.

**Test only at the seams the slice already named.** Before writing any
test, write down the seams from:

1. The slice issue's Given / When / Then
2. The feature PRD success criteria (`docs/prds/<feature>.md`)
3. The product PRD (`docs/prd.md`) when the slice extends shipped behaviour

Give each seam a one-line note on what it catches and what it misses.
No test is written at a seam the slice did not name. You cannot test
everything; the acceptance criteria are how effort lands on the critical
path.

Typical Codify seams:

| Seam | What it catches |
| --- | --- |
| `codify.project.new_project` / `to_oscal` | catalog shape, OSCAL 1.1.2 fields |
| `codify.classify` / `codify.draft` | clause type and draft wording |
| `codify.api.call` | request API used by server and browser |
| committed JSON under `tests/goldens/` | exact OSCAL bytes vs an independent expected |
| Playwright page (`tests/e2e`) | workspace behaviour a reviewer sees |
| `tests/test_acme.py` | classification and drafting vs the Acme key |

## Anti-patterns

- **Implementation-coupled**: mocks internal collaborators, tests private
  helpers, or verifies through a side channel. The tell: the test breaks
  when you refactor but behavior hasn't changed.
- **Tautological**: the assertion recomputes the expected value the way
  the code does, so it can never disagree. Expected values come from an
  independent source of truth: a known-good literal, a worked example,
  the spec, the Acme key, or a committed golden. For OSCAL, do not
  `assert to_oscal(project) == to_oscal(project)` and do not generate the
  golden from the same function under test in the same run.
- **Horizontal slicing**: writing all tests first, then all
  implementation. Work in **vertical slices**: one test → one
  implementation → repeat.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough
  code to pass it.
- **One slice at a time.** One seam, one test, one minimal implementation
  per cycle.
- **Refactoring is not part of the loop.** It belongs to the review
  stage (see the `code-review` skill), not the red → green cycle.

## Codify constraints (every cycle)

- Hold classification and drafting to the Acme key
  (`examples/acme-policy-key.md`, `tests/test_acme.py`).
- A change that writes OSCAL adds or updates a golden under
  `tests/goldens/` **and** stays valid against NIST OSCAL 1.1.2
  (`scripts/validate_oscal.mjs`).
- Unit tests make no network calls. E2E fakes AI providers.
- Do not weaken existing tests to make a slice pass.
