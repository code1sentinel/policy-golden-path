# Retro: Risk → control statements

| Field | Value |
| --- | --- |
| Date | 2026-10-06 |
| Feature / PRD | [docs/prds/risk-to-controls.md](../prds/risk-to-controls.md) |
| Slices / PRs | Stacked on the UI overhaul PR; this feature PR |

## What we shipped

A local risk register next to clause-only input. Risks stay on the device,
template drafts are deterministic, optional AI reuses the existing chip, and
accepted controls are traced in the OSCAL 1.1.2 catalog so Enact can still
read the file.

## What went well

- ADR 0008 made coexistence with ADR 0006 explicit before the UI landed.
- Reusing `control.py` as the template gate kept drafts in the same voice.
- Additive OSCAL props/resources avoided a second save format.

## What was painful

- Control ids from one-template-at-a-time adds collide unless the page
  assigns unique ids. Worth a shared helper next time.
- Existing goldens had to gain `source-type` even for clause-only catalogs
  so the field is always present.

## Lessons to fold into the templates

| Lesson | Template to change |
| --- | --- |
| Parallel inputs need an ADR that names the ADR they must not reverse. | ADR template / AGENTS.md (already implies this) |
| Always-on catalog props (like `source-type`) belong in every golden, not only the new ones. | Golden-file note in AGENTS.md |

## Follow-ups

- Residual risk / treatment workflow (explicitly out of this slice).
- Enact can follow `rel=reference` when it wants a trace; no Codify change required.
