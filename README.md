# oscal-assess

Scores the implementation statements in an OSCAL system security plan or
component definition, and passes each one that reaches **80% confidence**
(configurable). Anything below the threshold fails, with a list of the gaps an
author should close.

```
$ oscal-assess examples/ssp-example.json --catalog examples/catalog-excerpt.json
Statement                       Confidence  Result
------------------------------  ----------  ------
ia-2 [Okta]                           100%  PASS
au-6 [Splunk]                         100%  PASS
ac-2_smt.j [Payments Platform]         27%  FAIL
ac-2_smt.e [Okta]                       0%  FAIL

2/4 passed at a 80% confidence threshold.

ac-2_smt.j [Payments Platform]  (27%)
  - Statement is too brief to show how the control is met.
  - Name the role or team responsible for performing the control.
  ...
```

The exit code is `0` when every statement passes, `1` when any fails and `2`
on bad input, so it drops straight into CI as a gate.

It can also quantify risk with **FAIR** and check whether the control
statements actually treat each risk. See [Risk (FAIR)](#risk-fair).

## Install

```
cd oscal-assess
pip install -e .            # heuristic engine, no dependencies
pip install -e ".[claude]"  # adds the Claude engine
```

Python 3.10 or later.

## Inputs

| Document | Statements read |
| --- | --- |
| `system-security-plan` | Each `by-components[].description` under an implemented requirement, and under each of its `statements[]`. Component names come from `system-implementation.components`. A requirement with no description at all is still listed, so it fails visibly. |
| `component-definition` | Each `statements[].description` under an implemented requirement. When a requirement has no statements, its own `description` is assessed instead. |

Pass `--catalog` with an OSCAL catalog (JSON) to score each statement against
the actual control text. Statement-level ids such as `ac-2_smt.j` are matched
to that part of the control; parameters are rendered as
`[Assignment: ...]` / `[Selection: ...]`. Without a catalog, requirement
coverage is not scored and its weight is spread over the other criteria.

Only JSON is supported. Convert XML or YAML with the NIST OSCAL CLI first.

## Engines

### `heuristic` (default)

Offline and deterministic. Each statement is scored 0 to 1 on:

| Criterion | Weight | Looks for |
| --- | --- | --- |
| coverage | 25% | Share of the control requirement's key terms the statement addresses (full marks at 40%) |
| substance | 15% | Enough words to describe an implementation |
| responsibility | 15% | A named role or team |
| mechanism | 15% | Concrete tools, configurations or procedures |
| frequency | 15% | How often, or on what trigger, it operates |
| evidence | 15% | Logs, tickets, records or other artefacts an assessor can inspect |

The weighted sum is then adjusted:

- Hedging (`as needed`, `periodically`, `should`, `may`, ...) takes off 8% per distinct phrase, at most 40%.
- Planned work (`will be implemented`, `planned for`, `roadmap`, ...) is capped at 50%.
- Placeholders (`TBD`, `N/A`, `[insert ...]`, empty text) are capped at 20%.

It is a quality screen, not a verdict: it rewards statements written the way
an assessor needs them, but cannot tell whether what they say is true.

### `claude`

Uses Claude as an assessor. Each statement is sent with its control text, and
the model returns a 0 to 100 confidence, per-criterion scores, gaps and a
rationale as schema-constrained JSON.

```
export ANTHROPIC_API_KEY=...
oscal-assess ssp.json -c catalog.json --engine claude
```

| Option | Default | |
| --- | --- | --- |
| `--model` | `claude-opus-5` | Any Claude model id |
| `--effort` | `medium` | `low` to `max`; raise it for borderline statements |
| `--workers` | `4` | Parallel requests |

Requests use adaptive thinking and server-side refusal fallbacks
(`fallbacks: "default"`). If a response is refused, truncated or unreadable,
the statement fails with confidence 0 and a note to review it manually: the
tool never passes a statement it could not assess.

## Risk (FAIR)

Pass a risk register with `--risks` and each risk is quantified with FAIR and
checked against the statements of the controls linked to it:

```
$ oscal-assess examples/ssp-example.json -c examples/catalog-excerpt.json -r examples/risks-example.json
...
R-001  Account takeover of workforce SSO leads to payments data breach
  inherent  ALE mean SGD 1.5M (P10 257.4K, P50 1.3M, P90 3.2M)
  residual  ALE mean SGD 82.9K (P10 0, P50 17.1K, P90 138.1K)  (reduced by SGD 1.4M)
  controls  ia-2 100% [vulnerability], au-6 100% [loss_magnitude]
  addressed 100%, within appetite  ->  PASS
R-002  Orphaned accounts of departed staff used to approve fraudulent payments
  ...
  controls  ac-2 54% [vulnerability], au-6 90% [loss_magnitude]
  addressed 72%, within appetite  ->  FAIL
    - ac-2: statement does not mention the risk scenario (asset, threat or event); ...
    - ac-2: the statement itself scores 14%; see the statement assessment.
```

A risk **passes** when both hold:

1. The linked control statements address it with at least the threshold confidence (80% by default).
2. If an appetite is set, exposure is within it: residual exposure when a
   residual estimate is given, inherent otherwise.

### Entering risks

Answer questions to build or extend a register:

```
$ oscal-fair new risks.json
Currency [USD]: SGD
Risk appetite: the most annualized loss you will accept per risk (blank for none): 500000
Title: Account takeover of workforce SSO leads to payments data breach
Asset at risk: workforce user accounts and customer payment data
...
Controls (comma separated, '=factor' optional): ia-2=vulnerability, au-6=loss_magnitude
  1) Annualized loss exposure (ALE) directly
  2) Loss event frequency x loss magnitude
  3) Full FAIR factors
How do you want to estimate it [3]: 3
Threat events per year (leave blank to derive from contact x action): min, most likely, max or one number:
Contacts with the asset per year: min, most likely, max or one number: 4 12 40
...
R-001 inherent  ALE mean SGD 1.5M (P10 257.4K, P50 1.3M, P90 3.2M)
```

or compute exposure for a register without assessing controls:

```
oscal-fair compute risks.json            # table, with how each value was derived
oscal-fair compute risks.json -f json
```

### Risk register format

```json
{
  "currency": "SGD",
  "appetite": 500000,
  "appetite_metric": "mean",
  "risks": [
    {
      "id": "R-001",
      "title": "Account takeover of workforce SSO leads to payments data breach",
      "asset": "workforce user accounts and customer payment data",
      "threat_community": "external cybercriminals",
      "threat_event": "credential stuffing and phishing to take over user accounts",
      "effect": "confidentiality",
      "controls": { "ia-2": "vulnerability", "au-6": "loss_magnitude" },
      "appetite": 250000,
      "inherent": { "...": "FAIR factors" },
      "residual": { "...": "FAIR factors with the controls operating" }
    }
  ]
}
```

`appetite` can be set for the register, per risk, or not at all.
`appetite_metric` compares either the `mean` or the `p90` annual loss against
it. `controls` is a list of control ids, or a map from control id to the FAIR
factor that control should reduce.

### FAIR factors

Give each factor as one number or a range `{"min", "most_likely", "max"}`,
which is sampled as a PERT distribution. Provide whichever level of the FAIR
tree you have; anything missing is derived from the factors beneath it.

| Factor | Unit | Derived from |
| --- | --- | --- |
| `ale` | currency per year | `lef` x `lm` |
| `lef` loss event frequency | events per year | `tef` x `vulnerability` |
| `tef` threat event frequency | attempts per year | `contact_frequency` x `probability_of_action` (0-1) |
| `vulnerability` | 0-1 | share of trials where `threat_capability` exceeds `resistance_strength` (both 0-100 percentiles) |
| `lm` loss magnitude | currency per event | `primary_loss` + `secondary_loss` in the share `secondary_lef` (0-1) of events |

Annual loss is simulated with Monte Carlo (`--simulations`, default 10,000;
`--seed` for repeatable results). Each trial draws a Poisson number of loss
events at the sampled LEF and adds a sampled magnitude for each, so for rare
events P10 and P50 are often 0 and the tail sits at P90.

### Does the statement address the risk?

Each control is expected to reduce one FAIR factor:

| Factor | The control... | Signals in the statement |
| --- | --- | --- |
| `tef` | stops or deters the threat reaching the asset | block, restrict, segment, firewall, rate limit |
| `vulnerability` | resists the attempt, so it does not become a loss | MFA, encryption, patching, hardening, approval, review |
| `loss_magnitude` | detects, responds to or contains the loss | alert, monitor, incident response, backup, restore, within 4 hours |

Aliases work too: `avoidance`, `deterrence`, `resistance`, `detection`,
`response`, `containment`, `lm`.

With the default engine, each linked control scores:

| Part | Weight | Measures |
| --- | --- | --- |
| relevance | 30% | The statement names the scenario: shares at least 3 terms with the risk's title, asset, threat and event |
| factor | 40% | It describes reducing the expected factor (any factor when none is given; 30% credit for a different one) |
| quality | 30% | The statement's own confidence from the statement assessment |

A linked control with no statement scores 0. The risk's confidence is the
mean across its controls. With `--engine claude`, Claude reads the scenario
with all linked statements, identifies which factors each credibly reduces,
and scores the set as a whole, marking down risks that are only prevented
with nothing to detect or contain a loss.

## Output

| Flag | Output |
| --- | --- |
| `-f table` | Terminal summary with gaps for each failure (default) |
| `-f json` | Every score, criterion, gap and rationale |
| `-f markdown` | A report suitable for a PR comment or job summary |
| `-o PATH` | Write the report to a file instead of stdout |
| `--assessment-results PATH` | Also write an OSCAL `assessment-results` document: one finding per statement, `satisfied` or `not-satisfied`, with the confidence in a `confidence` prop. With `--risks`, each risk is added as an OSCAL `risk`: `closed` when it passes, `open` otherwise, with inherent and residual ALE and treatment confidence as characterization facets |

## Options

```
-t, --threshold  Confidence needed to pass: 0.8 or 80% (default 0.8)
-r, --risks      FAIR risk register (JSON)
--simulations    Monte Carlo trials per estimate (default 10000)
--seed           Random seed (default 0)
--no-fail        Exit 0 even when statements or risks fail
```

## Use in GitHub Actions

```yaml
- run: pip install ./oscal-assess
- run: |
    oscal-assess ssp.json -c catalog.json -f markdown -o report.md \
      --assessment-results assessment-results.json
- if: always()
  run: cat report.md >> "$GITHUB_STEP_SUMMARY"
```

## Development

```
pip install -e ".[dev]"
pytest
```

The Claude engine's tests use a stub client, so they run offline.

## Layout

```
src/oscal_assess/
  cli.py        argument parsing, exit codes
  loader.py     statements out of SSPs and component definitions
  catalog.py    control and statement-part text out of catalogs
  heuristic.py  offline rubric scorer
  fair.py       FAIR model and Monte Carlo simulation
  risk.py       risk register and control-to-risk alignment
  fair_cli.py   oscal-fair: interactive entry and computation
  llm.py        Claude assessor
  report.py     table, JSON, Markdown and OSCAL assessment-results output
examples/       NIST SP 800-53 excerpt, example SSP, component definition and risk register
tests/
```
