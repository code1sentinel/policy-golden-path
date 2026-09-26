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
  heuristic.py  offline rubric scorer
  llm.py        Claude assessor
  report.py     table, JSON, Markdown and OSCAL assessment-results output
examples/       NIST SP 800-53 excerpt, example SSP and component definition
tests/
```
