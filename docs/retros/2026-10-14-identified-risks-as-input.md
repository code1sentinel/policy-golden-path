# Retro: Identified risks as input

| Field | Value |
| --- | --- |
| Date | 2026-10-14 |
| Feature / PRD | [docs/prds/identified-risks-as-input.md](../prds/identified-risks-as-input.md) |
| Slices / PRs | [#36](https://github.com/code1sentinel/policy-golden-path/pull/36) |

## What we shipped

Identified risks as optional input to control authoring ([ADR 0012](../adr/0012-identified-risks-as-input.md)). A project holds `{id, statement, note?}`; controls may link those ids; coverage flags uncovered risks and unlinked controls; library matching is local; optional AI assist reuses `ai_prompt` / `ai_reply`. OSCAL 1.1.2 traces links with `identified-risk-id` resources, `treats-risk` props, and `rel=related`. This is not a register: no scores, owners, `--risks`, or treatment plans. ADR 0011 still holds.

## What went well

- ADR 0012 named what it refined (0011) and what it did not revive (0008) before the UI landed. Distinct OSCAL props (`identified-risk-id` vs leftover `risk-id`) kept old register catalogs loadable as `risks: []`.
- Reusing the existing AI path and local token overlap meant no new origin.
- Mobbin citations (Vanta recommend dialog, mapped elements, related table) mapped onto the existing indigo shell without a second product.

## What was painful

- PR #30 left unit **and** e2e tests that asserted the Risks nav was gone. The first push of #36 restored the nav as input and CI e2e went red (`test_first_run_clarity`, `test_theme`) even though unit tests had been updated.
- Playwright strict mode: `.mapped-risk` and `#risks-related, .coverage-flag` matched more than one node (editor vs risk detail; coverage line vs table). Unique `#id` / scoped parents were needed.
- Cloud agents cannot open GitHub issues (`gh` is read-only). The slice Given / When / Then lived in the PR body.

## Lessons to fold into the templates

| Lesson | Template to change |
| --- | --- |
| Restoring a surface a previous slice deleted: grep unit **and** e2e for absence assertions (`not_to_contain_text`, `to_have_count(0)`) in the same PR as the restore. Playwright locators must be unique. | `.cursor/skills/tdd/SKILL.md` (this PR) |
| When a GitHub issue cannot be opened, put the slice GWT in the PR body rather than skipping the seam list. | Noted here; PR template already has the GWT fields |

## Follow-ups

- Residual risk / scoring / owners remain out (ADR 0011 + 0012).
- Enact can ignore the new props/links; if it wants a trace, follow `rel=related` or `treats-risk`.
