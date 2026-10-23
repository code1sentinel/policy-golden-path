# PRD: Generate Rego starter on Policy as code (step 3)

| Field | Value |
| --- | --- |
| Status | Agreed |
| Slice issues | [COD-13](https://linear.app/code1sentinel/issue/COD-13/slice-generate-rego-starter-on-policy-as-code-step-3) |
| Supercedes / extends | [docs/prd.md](../prd.md), [technical-policy-rego-label.md](technical-policy-rego-label.md) |
| Author | This slice |
| Date | 2026-10-23 |

## Problem

Step 3 is labelled **Policy as code (Rego)** and hands an OSCAL catalog to
Enact, but Codify does not produce any Rego. Reviewers leave with a catalog
and still have to invent the first policy file by hand.

A MIT-licensed, fully offline generator already exists in the GRC Engineering
Club plugin pack: keyword matching against a tiny template set (S3 public /
tagging, EC2 encryption, plus a generic default). Codify can port and expand
that idea without AI and without a network call.

## Users

- **Primary:** a GRC reviewer who has accepted control statements and is on
  **Send to Enact** / Policy as code (Rego).
- **Not this slice:** people who need a finished, environment-specific policy;
  engineers who want aws-config or Terraform modules; anyone expecting an
  LLM to draft Rego.

## Job to be done

From each control statement, get a **starter** OPA Rego policy (optionally
Sentinel or Checkov) that is traced to that control, so Enact and git have
something to review — knowing it is a skeleton, not production policy.

## Scope

- In:
  - On step 3 only, each control statement has **Generate Rego starter**.
  - A small format picker: **Rego** (default), Sentinel, Checkov.
  - Local, deterministic keyword matching against an expanded template
    library adapted from `policy-generator.js`: storage public access,
    encryption at rest, encryption in transit/TLS, required tags, MFA,
    logging enabled, least-privilege IAM wildcard, backup or retention,
    network ingress `0.0.0.0/0`. Unmatched statements get a commented
    generic skeleton with TODOs.
  - Each generated file has a header: control statement, linked risk or
    clause, OSCAL control id, and a starter disclaimer.
  - Rego uses OPA v1 (`import rego.v1`, `if` / `contains`) in the shape
    Enact evaluates (`result.passed` / `result.message`).
  - Read-only code view with **Copy** and **Download** (`.rego` / `.sentinel`
    / `.yaml`).
  - Generated starters travel in the OSCAL catalog as back-matter resources
    (base64 file + `rel=policy-as-code` link) without breaking NIST 1.1.2.
  - MIT copyright for the ported matching/template idea in `THIRD_PARTY.md`
    and a source header. **No GRC Engineering Club branding in the UI.**
- Out:
  - AI, outbound network, or new origins.
  - aws-config and Terraform formats from the upstream plugin.
  - Step 1 or step 2 page changes.
  - Auto-generating starters on export when the person never clicked
    Generate.
  - Running the policy inside Codify (Enact still runs checks).

## Success criteria

- Given a control on step 3, When I choose **Generate Rego starter**, Then a
  read-only starter is shown with Copy and Download, and copy that it is a
  starter to review, not a finished policy. No AI or network call.
- Given statement text for each built-in family, When I generate, Then that
  family’s template is used; unmatched text gets the generic TODO skeleton.
- Given a generated Rego starter, Then the header names the statement, the
  linked risk or clause, and the OSCAL control id; the body has
  `import rego.v1` and compiles with `opa check`.
- Given a generated starter, When I export the OSCAL catalog, Then a
  back-matter resource holds the file and the control links to it, and the
  catalog still validates against NIST OSCAL 1.1.2.
- Given the step 3 UI, Then it does not name the GRC Engineering Club.

## Design references

| Screen / flow | Mobbin URL | What we take from it |
| --- | --- | --- |
| GitLab — shared snippet | https://mobbin.com/screens/37dfd77e-5d72-41c0-b2c0-01c1afe78c55 | Read-only code with copy and download on the snippet header |
| Relume — component code | https://mobbin.com/screens/b2e28cc0-3db1-4e21-adfc-378e9a859787 | Dark code panel, language tabs, Copy |
| Hashnode — guide snippet | https://mobbin.com/screens/6b48b2bd-4daf-42c4-926f-8037314a0042 | Language picker and Copied status |
| Browserbase — JSON + copy | https://mobbin.com/screens/ae95ee59-43fe-4173-887a-c3542d08c9c8 | Existing Codify OSCAL copy pattern (numbered, Copy) |

Adapt to Codify’s dark workspace. Do not copy product branding.

## Privacy and outbound calls

No new network call, origin, or leave-device path
([ADR 0003](../adr/0003-local-only-privacy-model.md)). Generation is local
keyword matching in the `codify` package (same path as rule drafts).

## Open questions

None.

## Decision log

[ADR 0019](../adr/0019-local-policy-as-code-starters.md) — starters are
local, deterministic templates, not AI, and attach to the catalog as
back-matter files.
