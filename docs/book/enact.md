# Using Codify with Enact

[Enact](https://code1sentinel.github.io/enact/) is a separate app. **Codify writes the catalog. Enact runs the checks.**

They share a file format, not a server.

## The split

| App | Job |
| --- | --- |
| **Codify** | Turn policy clauses into reviewed control statements and export an OSCAL 1.1.2 catalog. |
| **Enact** | Open that catalog, map checks, add evidence, and run an assessment in the browser. |

Enact's own walkthrough is: Catalog → Checks → Evidence → Run, then download the results. Nothing leaves your browser there either.

## What to hand to Enact

Export **OSCAL catalog** from Codify (the recommended download). Open that JSON in Enact as the catalog.

You do not need the statement library, Excel, or the conversion report for Enact. Enact reads `catalog.groups[].controls[]` statements. It never sees the on-device library.

If a control has a purpose or “risk it treats” line, that travels in the catalog as a property. Enact can ignore fields it does not use.

## Typical path

1. In Codify, paste a clause or try the example, review, and Accept.
2. Export the OSCAL catalog.
3. Open [Enact](https://code1sentinel.github.io/enact/).
4. Load the catalog JSON (or Enact's own example) and continue with checks and evidence.

Codify does not run checks, collect evidence, or write assessment results. Enact does not draft control statements from policy prose.
