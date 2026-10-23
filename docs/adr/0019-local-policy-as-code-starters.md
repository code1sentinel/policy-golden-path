# 0019. Local policy-as-code starters

Date: 2026-10-23

## Status

Accepted

Does not change [0003-local-only-privacy-model.md](0003-local-only-privacy-model.md)
or [0002-oscal-1-1-2.md](0002-oscal-1-1-2.md).

## Context

Codify’s last authoring step is **Policy as code (Rego)** and the catalog is
the handoff to Enact. Enact evaluates OPA/Rego (`import rego.v1`, a `result`
object) in the browser. Until this decision, Codify wrote no policy code.

A MIT-licensed, fully offline generator in the GRC Engineering Club plugin
pack (`policy-generator.js`) turns a natural-language requirement into
template code by keyword matching. It has only two concrete patterns plus a
generic default. Porting that idea into Codify is useful only if we keep the
privacy model: no AI, no network, same deterministic package on CLI, web,
and Pages.

OSCAL 1.1.2 has no first-class policy-as-code field on a catalog control.
Putting arbitrary keys on the control would fail NIST’s catalog schema. A
back-matter `resource` may carry a `base64` file and a control `link`.

## Decision

1. Codify may generate **starter** policy-as-code from a control statement
   using a local, deterministic template library (keyword matching). It must
   not call an AI provider or any network endpoint to do so.
2. The default format is OPA Rego in v1 syntax, shaped so Enact can evaluate
   it (`result.passed` / `result.message`). Sentinel and Checkov are optional
   formats on the same matcher. aws-config and Terraform modules are out.
3. Generated code is a starter to review, not a finished policy. The UI and
   the file header say so. The UI does not use GRC Engineering Club branding.
4. The person opts in per control (**Generate Rego starter**). Export does
   not invent starters that were never generated.
5. When a starter exists, the catalog includes it as a `back-matter`
   resource with a `base64` payload and a control link
   `rel=policy-as-code`. Do not emit keys the catalog schema rejects.
6. The MIT copyright notice for the ported matching/template idea lives in
   `THIRD_PARTY.md` and the source header of the generator module.

## Consequences

- Step 3 can show Copy / Download of a `.rego` file without leaving the
  device.
- Goldens that attach a starter must stay valid 1.1.2 catalog JSON; CI
  `oscal-schema` checks them.
- CI runs `opa check` on generated Rego.
- Improving starters with a model, a remote template service, or a new
  leave-device path needs a new ADR.
