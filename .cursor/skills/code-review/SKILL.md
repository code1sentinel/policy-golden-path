---
name: code-review
description: Two-axis review of a diff (Standards vs Spec), including Fowler smells and refactoring opportunities. Use when reviewing a branch, PR, or work-in-progress, or before marking a slice ready.
---

# Code Review

Adapted from [mattpocock/skills](https://github.com/mattpocock/skills)
`skills/engineering/code-review` at
`49dd158d1076134a641b33efb035946536778336` (MIT, Copyright 2026 Matt Pocock).
Spec source is `docs/prds/` and the relevant ADRs, not an issue-tracker
setup. Runs with or without sub-agents. This pass is also where
refactoring belongs (the `tdd` loop is red → green only).

Two-axis review of the diff between `HEAD` and a fixed point:

- **Standards**: does the code follow this repo's written standards,
  plus smells and refactoring opportunities?
- **Spec**: does the code match the PRD and the ADRs it must honour?

Report the axes side by side. Do not merge or rerank findings.

## Process

### 1. Pin the fixed point

Use the supplied commit, branch, tag, or `HEAD~N`. If none was supplied,
use `origin/main` (fetch it if needed).

Capture once:

```bash
git rev-parse <fixed>
git diff <fixed>...HEAD
git log <fixed>..HEAD --oneline
```

Three-dot diff so the comparison is against the merge-base. Fail here if
the ref is missing or the diff is empty.

### 2. Identify the spec source

In this order, without asking a human:

1. Feature PRD under `docs/prds/` named in the branch, commits, or PR body
2. Given / When / Then on the linked slice issue or in the PR body
3. `docs/prd.md` when the change touches shipped product behaviour
4. ADRs under `docs/adr/` cited by that PRD or touched by the diff
   (do not silently reverse an accepted ADR)

If nothing is found, the Spec pass reports "no spec available" and you
still run Standards.

### 3. Identify the standards sources

Always include every file that documents how code should be written:

- `AGENTS.md` (pointers)
- `.cursor/rules/*.mdc`
- `.github/pull_request_template.md`
- `CONTRIBUTING.md`
- Privacy: `.cursor/rules/privacy.mdc`, `.cursor/rules/privacy-web.mdc`,
  [ADR 0003](../../../docs/adr/0003-local-only-privacy-model.md),
  [ADR 0004](../../../docs/adr/0004-ollama-localhost-only.md)
- UI: `.cursor/rules/mobbin-ui.mdc` (Mobbin citations, no invented layout)
- TDD constraints in `.cursor/skills/tdd/SKILL.md` (Acme key, goldens,
  no network in unit tests, do not weaken tests)

When `CONTRIBUTING.md` exists, it stays on the list.

On top of that, Standards always carries the **smell baseline** below
(Fowler, _Refactoring_, ch.3) and a **refactoring** look: now that
refactoring is out of the TDD loop, this pass is where you flag
opportunities. Two rules bind the baseline:

- **The repo overrides.** A documented repo standard always wins.
- **Always a judgement call.** Each smell is a labelled heuristic, never
  a hard violation. Skip anything tooling already enforces (`ruff`,
  `mypy`, `gitleaks`, `pip-audit`).

Each smell reads *what it is* → *how to fix*:

- **Mysterious Name**: a name that does not reveal what it does or holds.
  → rename it; if no honest name comes, the design is murky.
- **Duplicated Code**: the same logic shape appears in more than one hunk.
  → extract the shared shape, call it from both.
- **Feature Envy**: a method that reaches into another object's data more
  than its own. → move the method onto the data it envies.
- **Data Clumps**: the same few fields keep travelling together.
  → bundle them into one type, pass that.
- **Primitive Obsession**: a primitive standing in for a domain concept.
  → give the concept its own small type.
- **Repeated Switches**: the same `if`-cascade on the same type recurs.
  → one map or one function both sites share.
- **Shotgun Surgery**: one logical change forces scattered edits.
  → gather what changes together into one module.
- **Divergent Change**: one file edited for several unrelated reasons.
  → split so each module changes for one reason.
- **Speculative Generality**: abstraction the spec does not need.
  → delete it; inline back until a real need shows.
- **Message Chains**: long `a.b().c().d()` navigation.
  → hide the walk behind one method on the first object.
- **Middle Man**: a function that mostly delegates onward.
  → cut it, call the real target.
- **Refused Bequest**: a subclass that ignores most of what it inherits.
  → drop the inheritance, use composition.

### 4. Run both axes

If sub-agents are available, spawn **Standards** and **Spec** in
parallel, in the foreground, and aggregate what they return.

If sub-agents are not available, run both passes yourself **in
sequence**, one axis at a time, without letting findings from the first
rerank the second:

1. Standards only (ignore whether the change matches the PRD)
2. Spec only (ignore style and smells)

**Standards brief** (give this to a sub-agent, or follow it yourself):

- The full diff command and commit list
- The standards-source list from step 3, **plus the smell baseline
  pasted in full**
- Report, per file/hunk where relevant: (a) every place the diff
  violates a documented standard — cite the file and the rule; (b) any
  baseline smell — name it and quote the hunk; (c) refactoring
  opportunities the TDD loop deferred. Distinguish hard violations
  (documented-standard breaches) from judgement calls (smells). Skip
  anything tooling enforces. Under 400 words.

**Spec brief**:

- The diff command and commit list
- The PRD / ADR / Given-When-Then text
- Report: (a) requirements the spec asked for that are missing or
  partial; (b) behaviour in the diff that was not asked for (scope
  creep); (c) requirements that look implemented but look wrong. Quote
  the spec line for each finding. Under 400 words.

If the spec is missing, skip Spec and note that in the final report.

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec`, verbatim or
lightly cleaned. Do **not** merge or rerank findings.

End with a one-line summary: total findings per axis, and the worst
issue _within each axis_. Do not pick a single winner across axes.

## Why two axes

A change can pass one axis and fail the other:

- Follows every standard but implements the wrong thing → **Standards
  pass, Spec fail.**
- Does exactly what the PRD asked but breaks conventions → **Spec pass,
  Standards fail.**
