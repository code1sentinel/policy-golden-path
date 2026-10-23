# Using Codify with Enact

[Enact](https://code1sentinel.github.io/enact/) is a separate app. **Codify writes the catalog. Enact runs the checks.**

They share a file format, not a server. Codify does not upload the catalog.

## The split

| App | Job |
| --- | --- |
| **Codify** | Identify risks, write reviewed control statements, and download an OSCAL 1.1.2 catalog. |
| **Enact** | Open that catalog, map checks, add evidence, and run an assessment in the browser. |

Enact's own walkthrough is: Catalog → Checks → Evidence → Run, then download the results. Nothing leaves your browser there either.

## What to hand to Enact

In Codify, finish **Send to Enact** and download **OSCAL catalog** (the recommended download). Open that JSON in Enact as the catalog.

The web wizard blocks the download until every identified risk has an accepted control statement and every control is linked to a risk. That is a local check. Nothing is sent.

You do not need the statement library, Excel, or the conversion report for Enact. Enact reads `catalog.groups[].controls[]` statements. It never sees the on-device library.

If a control has a purpose or “risk it treats” line, that travels in the catalog as a property. Identified-risk links travel as `treats-risk` properties and `rel=related` links to back-matter resources. A **Generate Rego starter** action on this step can attach a local template file (`rel=policy-as-code`, back-matter `base64`). That file is a starter to review, not a finished policy. Enact can ignore fields it does not use.

## Typical path

1. In Codify, start from risks (recommended) or from a clause, cover every risk, review, and Accept.
2. Open **Send to Enact** and download the OSCAL catalog.
3. Open [Enact](https://code1sentinel.github.io/enact/).
4. Load the catalog JSON (or Enact's own example) and continue with checks and evidence.

Codify does not run checks, collect evidence, or write assessment results. Enact does not draft control statements from policy prose.
