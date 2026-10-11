## Linked issue

Fixes #

## Summary

<!-- Smallest sketch that makes the change obvious: a few lines of
     before/after, a call tree, a file tree, or a short diff. -->

```text

```

## What / why

<!-- What changed, and which PRD or ADR it follows. One slice only. -->

## Evidence

<!-- Concrete before/after. Failing then passing test, golden diff, or screenshots. -->

- **Before:**
- **After:**

## Merge danger

<!-- One-way doors are hard to walk back (destructive data, binding ADRs,
     leave-device paths). Two-way doors are cheap to revert. -->

- **Door:** one-way / two-way
- **Blast radius:** <!-- one or two words, then a line on who/what can break -->

## Tests added

<!-- The failing test you wrote first, plus any goldens or e2e. -->

- [ ] Failing test from the slice's Given / When / Then, then implementation
- [ ] Golden-file test updated if this writes OSCAL
- [ ] Acme key still holds if classification or drafting changed

## Checklist

- [ ] Acceptance criteria on the linked issue are met
- [ ] CI is green (tests, e2e, OSCAL schema, ruff, mypy, pip-audit, gitleaks)
- [ ] Security / privacy: no new outbound calls, origins, or leave-device paths (or an ADR explains why)
- [ ] `README.md` and `CHANGELOG.md` updated
- [ ] UI changes cite the Mobbin references used, with before/after screenshots
- [ ] Screenshots or a short demo attached if the UI or Pages site changed
- [ ] Retro note planned at `docs/retros/` when the feature (not just this slice) is done

## Design references (UI only)

<!-- Mobbin (mobbin.com) screen links from the PRD or slice issue. If none were provided, do not invent a design. -->

-

## Screenshots (UI only)

| Before | After |
| --- | --- |
| | |
