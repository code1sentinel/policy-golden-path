# Concepts and glossary

Short definitions as Codify uses them. In the app, dotted terms show the same wording when you hover.

## Glossary

**OSCAL**
A standard format from NIST for writing security controls so other GRC tools can read them. Codify writes catalog version **1.1.2**.

**Clause**
A paragraph from the policy you pasted. Numbers are optional. One paragraph is usually one clause.

**Requirement**
A clause that states a rule (`shall`, `must`, `should`, a present-tense obligation). Codify drafts control statements from requirements.

**Control statement**
The wording of one control: what to do, to what, how often or how fast, and why. Codify scores this statement — not an implementation procedure.

**Draft**
Codify's first-pass control statement. Edit it before you accept.

**Review**
Check the draft against the original clause and the score.

**Accept**
Keep this statement in this project's catalog and on this device.

**Catalog**
This project's control statements — the set you export as OSCAL.

**Library** (statement library)
Reusable accepted statements saved on this device, across projects. Not the catalog.

**The risk it treats**
The purpose of a control: why it exists. Write it as the risk the statement addresses (for example, access that is no longer needed). This is a line on the control, not a risk register.

**Parameter / `[N]`**
A blank the organisation must set so the statement can be tested — often a number of days. Unfilled blanks look like `[N]`.

**Origin**
How the statement was written: Codify's rules, AI, opened from a catalog, or edited by you.

**Not a control**
Aspirations, consequences, permissions, or descriptions of the policy itself. They do not become controls.

## What Codify is not

- Not a mapping to IM8 or another external catalog
- Not a risk register or residual-risk workflow
- Not an assessment runner — that is [Enact](enact.md)
- Not a place that hosts your policy or API keys
