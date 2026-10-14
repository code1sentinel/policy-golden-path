# Decision records

Architecture and product decisions live as Markdown files in [`docs/adr/`](https://github.com/code1sentinel/policy-golden-path/tree/main/docs/adr). This page is an index with one-line summaries. The ADRs themselves are the source of truth — do not copy their full text here.

Status is taken from each file. An accepted ADR is binding until a later one supersedes it.

| ADR | Status | Summary |
| --- | --- | --- |
| [0001. Record architecture decisions](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0001-record-architecture-decisions.md) | Accepted | Write durable decisions as numbered Markdown ADRs in `docs/adr/`. |
| [0002. OSCAL 1.1.2](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0002-oscal-1-1-2.md) | Accepted | OSCAL 1.1.2 is the catalog format and the project save file. |
| [0003. Local-only privacy model](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0003-local-only-privacy-model.md) | Accepted | The policy stays on the person's device; rule drafts use no AI. |
| [0004. Ollama localhost only](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0004-ollama-localhost-only.md) | Accepted | Ollama may be called only at `localhost:11434`, never a remote host. |
| [0005. Remove IM8 mapping](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0005-remove-im8-mapping.md) | Accepted | IM8 Reform mapping and coverage views are removed. |
| [0006. Clause-only input](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0006-clause-only-input.md) | Accepted | Happy-path input is clause text; no Title field; numbers are optional. |
| [0007. Authoring app shell](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0007-authoring-app-shell.md) | Accepted | The web app is a sidebar + writing column + properties shell. (Risks nav later removed by 0011.) |
| [0008. Risk input and OSCAL tracing](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0008-risk-input-and-oscal-tracing.md) | Superseded by 0011 | Added a local risk register and catalog tracing. Enact still reads the catalog. |
| [0009. Device-wide statement library](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0009-device-wide-statement-library.md) | Accepted | Accepted statements are stored on this device, separate from the catalog. |
| [0010. Vanta GRC surfaces](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0010-vanta-grc-surfaces.md) | Accepted (register part superseded) | Statement library is a list + detail. Risks Library / Register were removed by 0011. |
| [0011. No risk register](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0011-no-risk-register.md) | Accepted (refined by 0012) | Codify has no risk register. The statement library remains. |
| [0012. Identified risks as input](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0012-identified-risks-as-input.md) | Accepted | Identified risks are optional input to authoring, not a register. |

New decisions go in `docs/adr/NNNN-title.md`, numbered from the next free integer. Follow [0001](https://github.com/code1sentinel/policy-golden-path/blob/main/docs/adr/0001-record-architecture-decisions.md).
