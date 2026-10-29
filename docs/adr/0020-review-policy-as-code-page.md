# 0020. Review + Policy as code (Rego) is one last step

Date: 2026-10-24

## Status

Accepted

Refines [0013-risk-first-authoring-flow.md](0013-risk-first-authoring-flow.md)
for the last web step and the web export gate. Does not change
[0012-identified-risks-as-input.md](0012-identified-risks-as-input.md),
[0014-oscal-identified-risk-statements.md](0014-oscal-identified-risk-statements.md),
or [0019-local-policy-as-code-starters.md](0019-local-policy-as-code-starters.md).

## Context

ADR 0013 ended both start paths on **Review** (the three-pane workspace)
then **Send to Enact**. Reviewers do not know what Enact is. The job on
the last page is to confirm coverage, take a Rego starter, and download
the OSCAL catalog.

ADR 0013 also blocked web export until every risk had an **accepted**
control. After Control statements (ADR 0016) already requires a
non-empty statement per item, a second Accept click on a different
surface is not the coverage gate those earlier steps taught.

## Decision

1. Both web paths share one last step, labelled **Policy as code
   (Rego)**. Internally the step id stays `review`. A saved
   `flowStep: "enact"` opens this page. Enact is a supporting caption
   or link (`Opens in Enact`), not the page title.
2. That page is a review summary (counts, coverage, Edit back to Risk
   Entry / Policy Clause / Control statements), the COD-13 Rego starter
   section, and an OSCAL JSON preview with Copy / Download. The primary
   action downloads the catalog on this device.
3. Web export of the project (OSCAL, Excel, CSV, report) is allowed when
   every identified risk has at least one **non-empty** control
   statement and every non-empty control is linked to a risk. Accept is
   not required. Statement-library export and CLI export stay ungated.
4. Identified risks remain catalog back-matter resources. Each control
   still carries `treats-risk` / `rel=related`. Starters still attach as
   `rel=policy-as-code` when the person generated them.

## Consequences

- Path A steps are `risks → controls → review`. Path B steps are
  `clause → controls → link → review`.
- The three-pane workspace remains for opened catalogs and detailed
  Accept / score editing; it is not the happy-path last step.
- Tests and copy that required Accept before download move to the
  coverage gate.
- Changing the gate back to Accept, or adding a leave-device handoff
  to Enact, needs a new ADR.
