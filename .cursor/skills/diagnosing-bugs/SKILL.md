---
name: diagnosing-bugs
description: Diagnosis loop for hard bugs and performance regressions. Use when a test, golden file, e2e run, CLI export, or the app is broken, throwing, failing, or slow.
---

# Diagnosing Bugs

Adapted from [mattpocock/skills](https://github.com/mattpocock/skills)
`skills/engineering/diagnosing-bugs` at
`49dd158d1076134a641b33efb035946536778336` (MIT, Copyright 2026 Matt Pocock).
Claude-Code "Skill tool" wording removed. Headless: never block on a human
answer. Codify loops are pytest, Playwright e2e, and OSCAL golden diffs.

A discipline for hard bugs. Skip phases only when explicitly justified.

When exploring, read `GLOSSARY.md` if it exists, and check ADRs in the
area you are touching.

## Redact

This skill has you show commands, outputs, and captured artifacts.
**Redact every secret first**: write `[REDACTED]` in its place. Build loops
against env vars so the credential stays in the environment rather than in
what you show. Never write an AI key into a fixture, script, catalog,
library, or export (use the existing `sk-test` placeholder only).

If the redacted output is not enough to diagnose the bug, say so, list the
artifact that would unblock you, and stop. Do not invent a fix.

## Phase 1: Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a
**tight** pass/fail signal for the bug (one that goes red on _this_ bug),
you will find the cause. If you don't have one, staring at code will not
save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse
to give up.**

### Ways to construct one, in this repo, in roughly this order

1. **Failing pytest** at the seam that reaches the bug:
   `pytest tests/test_<area>.py::test_<name> -q`
2. **Acme key** when classification or drafting is wrong:
   `pytest tests/test_acme.py -q`
3. **Golden-file loop** when OSCAL output drifted:
   `pytest tests/test_control_oscal.py::test_control_oscal_matches_the_catalog_control_and_golden -q`
   (expected JSON lives under `tests/goldens/`; the test compares a frozen
   catalog or control to that committed file).
4. **CLI invocation** with a fixture input, diffing stdout or `-o` JSON
   against a known-good snapshot:
   `codify examples/acme-information-security-policy-2016.md -f oscal -o /tmp/out.json`
5. **Playwright e2e** that drives the UI and asserts on DOM / download /
   `localStorage`:
   `pytest tests/e2e/test_web.py -q`
   Against the Pages build: `CODIFY_SITE=site pytest tests/e2e -q`
   (AI providers stay faked; see `tests/e2e/conftest.py`.)
6. **Privacy / CSP loop** when origins or fonts changed:
   `pytest tests/test_webapp.py tests/test_site.py tests/test_local_assets.py -q`
7. **Throwaway harness** that calls one public function with a fixture.
8. **Property / fuzz loop** if the bug is "sometimes wrong output".
9. **Bisection harness** between two commits: `git bisect run` a pytest node.
10. **Differential loop**: same input through old vs new, diff catalogs.

Do not use a human-in-the-loop script. Agents in this repo run headless.

`scripts/pytest-loop.sh` in this folder wraps a single pytest node so the
invocation and verdict are one command.

### Tighten the loop

Treat the loop as a product. Once you have _a_ loop, **tighten** it:

- Faster: one test node, not the full suite.
- Sharper: assert the exact symptom, not "didn't crash".
- Deterministic: pin UUIDs and timestamps in goldens the way existing
  tests already freeze them; isolate filesystem; never hit a real AI host.

A 30-second flaky loop is barely better than no loop; a 2-second
deterministic one is _tight_.

### Non-deterministic bugs

Raise the reproduction rate until the bug is debuggable. Loop the trigger
100×, narrow timing windows. A 50% flake is debugable; 1% is not.

### When you genuinely cannot build a loop

Stop. List what you tried and which artifact would unblock you
(redacted HAR, log, screen recording with timestamps). Do **not**
proceed to hypothesise without a loop.

### Completion criterion: a tight loop that goes red

Phase 1 is done when you can name **one command** you have **already run
at least once** (show the invocation and its output, redacted), and that
is:

- [ ] **Red-capable**: drives the actual bug path and asserts the
      **exact symptom**.
- [ ] **Deterministic**: same verdict every run (or a pinned high flake rate).
- [ ] **Fast**: seconds, not minutes.
- [ ] **Agent-runnable**: unattended. No human click required.

If you catch yourself reading code to build a theory before this command
exists, **stop**. No red-capable command, no Phase 2.

## Phase 2: Reproduce + minimise

Run the loop. Watch it go red as the bug appears.

Confirm:

- [ ] The loop produces the failure that was reported, not a nearby one.
- [ ] The failure reproduces across runs (or at a high enough flake rate).
- [ ] You have captured the exact symptom (assertion, golden mismatch,
      Playwright timeout, CLI exit).

### Minimise

Shrink the repro to the **smallest scenario that still goes red**. Cut
inputs, callers, config, and steps **one at a time**, re-running the loop
after each cut.

Done when **every remaining element is load-bearing**.

## Phase 3: Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them.

Each must be **falsifiable**:

> If \<cause\> is true, then \<probe\> will make the bug disappear / worse.

Write the ranked list into the working notes or PR, then proceed with
your ranking. Do not wait for a human to re-rank.

## Phase 4: Instrument

Each probe maps to one Phase 3 prediction. **Change one variable at a time.**

1. Debugger / REPL if the env supports it.
2. Targeted logs at the boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup
is one grep.

**Perf branch.** Measure first (timing harness, profiler), fix second.

## Phase 5: Fix + regression test

Write the regression test **before the fix**, but only if there is a
**correct seam** for it (see the `tdd` skill). For OSCAL, that seam is
usually a golden-file assertion against an independent committed JSON,
not a value you recompute with `to_oscal`.

If no correct seam exists, that itself is the finding. Note it.

If a correct seam exists:

1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase 1 loop against the original (un-minimised) scenario.

## Phase 6: Cleanup

- [ ] Original repro no longer reproduces (re-run the Phase 1 loop)
- [ ] Regression test passes (or absence of seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed
- [ ] Throwaway prototypes deleted
- [ ] The hypothesis that turned out correct is stated in the commit / PR
