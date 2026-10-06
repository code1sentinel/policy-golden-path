# Golden files

Expected OSCAL catalogs (and other frozen outputs) for TDD.

When a slice writes or changes OSCAL:

1. Add a failing test that compares `to_oscal(...)` to a file here.
2. Implement until it matches.
3. Keep the `oscal-schema` CI job green against NIST 1.1.2.

Commit the golden JSON. Do not regenerate goldens to hide an accidental
format change — review the diff.

`unnumbered-lock-screens.json` is the catalog for a single unnumbered
clause ("Users shall lock screens."). UUIDs and `last-modified` are
frozen in the test.

`unnumbered-lock-screens-control.json` is that catalog's first control
object (`control_oscal`), with the derived-from href frozen.

`risk-only.json` is a catalog with one risk (R-001) and one template
control, traced with `source-type=risk`, `risk-id`, and `rel=reference`.

`mixed-clause-risk.json` is the unnumbered lock-screens clause plus that
same risk-derived control.
