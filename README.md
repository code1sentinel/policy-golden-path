# oscal-assess

Scores the implementation statements in an OSCAL system security plan or
component definition, and passes each one that reaches **80% confidence**
(configurable). Anything below the threshold fails, with a list of the gaps an
author should close.

Statements are judged against the control requirement (from an OSCAL catalog)
and, optionally, against the **policy intent** your own policies set for each
control: see [Policy intent](#policy-intent).

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

## Policy intent

OSCAL has no field for what your organization's policy requires, so it is a
separate input. Give it as a policy file, an inline intent, or both:

```
oscal-assess ssp.json -c catalog.json --policy policies.json
oscal-assess ssp.json --intent "Access is reviewed at least quarterly and records are retained for 12 months."
```

```json
{
  "policies": [
    {
      "id": "ISP-05.1",
      "title": "Access Control Policy: user access reviews",
      "intent": "Managers review every user account and its access at least quarterly, and access that is no longer needed is removed within 5 business days. Review records are retained for at least 12 months.",
      "controls": ["ac-2_smt.j"]
    }
  ]
}
```

`controls` lists control ids (`ac-2`, matching every statement of the
control) or statement ids (`ac-2_smt.j`, matching that part only). A policy
without `controls` applies to every statement, as does `--intent`. When more
than one policy matches a statement, it must meet all of them.

A statement meets the policy intent when it:

1. **Speaks to the intent**: shares the intent's key terms, such as who, what
   and which systems.
2. **Keeps its measurable commitments**. These are read from the intent and
   compared with the statement:

   | Commitment | Intent says | Met by | Falls short |
   | --- | --- | --- | --- |
   | How often | `at least quarterly`, `every 30 days`, `once a year` | the same or more often (`every 90 days`, `monthly`) | `annually` |
   | Time limit | `within 5 business days`, `within 24 hours` | the same or faster | `within 30 days` |
   | Retention | `retained for at least 12 months`, `3-year retention` | the same or longer | `kept for 6 months` |

Meeting the policy intent is required to pass, not just one more score:

- A statement that **falls short** of a commitment (`annually` against `at
  least quarterly`) is capped at **50%**.
- A statement that **does not mention** a commitment (no retention period when
  the policy sets one) is capped at **75%**.

With the default 80% threshold neither can pass. In the example, AU-6 passes
at 100% against the control alone, but fails at 75% against the logging policy
because it never says how long logs are kept:

```
$ oscal-assess examples/ssp-example.json -c examples/catalog-excerpt.json -p examples/policy-example.json
...
au-6 [Splunk]  (75%)
  - Policy requires "retained for at least 3 years"; the statement does not say how long records are kept.
```

## Engines

### `heuristic` (default)

Offline and deterministic. Each statement is scored 0 to 1 on:

| Criterion | Weight | Looks for |
| --- | --- | --- |
| coverage | 20% | Share of the control requirement's key terms the statement addresses (full marks at 40%) |
| policy_intent | 20% | 40% the intent's key terms (full marks at 50%), 60% its measurable commitments met |
| substance | 12% | Enough words to describe an implementation |
| responsibility | 12% | A named role or team |
| mechanism | 12% | Concrete tools, configurations or procedures |
| frequency | 12% | How often, or on what trigger, it operates |
| evidence | 12% | Logs, tickets, records or other artefacts an assessor can inspect |

`coverage` needs `--catalog` and `policy_intent` needs a policy intent. When
either is missing, the remaining weights are scaled up to sum to 100%.

The weighted sum is then adjusted for wording. A statement should state as
fact what happens today, so each distinct phrase below takes off 8%, up to
40% in total:

| Wording | Examples | Why it costs |
| --- | --- | --- |
| Hedges | `should`, `may`, `could`, `as needed`, `periodically`, `where possible` | Says what might happen, not what does |
| Obligations | `must`, `shall`, `is required to` | Restates the requirement instead of saying what enforces it |
| Open-ended examples | `such as`, `e.g.`, `for example`, `including but not limited to`, `etc.` | Leaves the scope undefined. Allowed when the statement says where the full set is defined (`the use cases listed in the SOC runbook, such as ...`) |

And capped:

| Condition | Cap |
| --- | --- |
| Placeholder: `TBD`, `N/A`, `[insert ...]`, empty text | 20% |
| Planned work: `will be implemented`, `planned for`, `roadmap` | 50% |
| Falls short of a policy commitment | 50% |
| Leaves out a policy commitment | 75% |

It is a quality screen, not a verdict: it rewards statements written the way
an assessor needs them, but cannot tell whether what they say is true.

### `claude`

Uses Claude as an assessor. Each statement is sent with its control text, and
the model returns a 0 to 100 confidence, per-criterion scores, gaps and a
rationale as schema-constrained JSON. When a statement has a policy intent,
it is sent too and scored as a `policy_intent` criterion; if that scores
below 50, the confidence is capped at 50%, as with the heuristic engine.

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

## Output

| Flag | Output |
| --- | --- |
| `-f table` | Terminal summary with gaps for each failure (default) |
| `-f json` | Every score, criterion, gap and rationale |
| `-f markdown` | A report suitable for a PR comment or job summary |
| `-o PATH` | Write the report to a file instead of stdout |
| `--assessment-results PATH` | Also write an OSCAL `assessment-results` document: one finding per statement, `satisfied` or `not-satisfied`, with the confidence in a `confidence` prop |

## Options

```
-c, --catalog    OSCAL catalog (JSON) for control requirement text
-p, --policy     Policy file (JSON) with the policy intent for each control
-i, --intent     A policy intent applied to every statement
-t, --threshold  Confidence needed to pass: 0.8 or 80% (default 0.8)
--no-fail        Exit 0 even when statements fail
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
  policy.py     policy intents and which statements they apply to
  heuristic.py  offline rubric scorer
  llm.py        Claude assessor
  report.py     table, JSON, Markdown and OSCAL assessment-results output
examples/       NIST SP 800-53 excerpt, example SSP, component definition and policies
tests/
```
