# PolicyGP

**Policy Golden Path: the golden path for policy development.**

Policy development follows one path, from what the organization commits to,
through how it is done, to where it falls short and how to fix it. Each stage
has to carry the intent of the one before it. PolicyGP follows that path
through your OSCAL documents and checks each stage, and the links between
them:

| Stage | What it says | Where it lives | Checked for |
| --- | --- | --- | --- |
| 1. Policy intent | What the organization commits to | your policy file (input) | |
| 2. Control requirement | What the control demands | OSCAL catalog (input) | |
| 3. Implementation statement | How it is met today | SSP, component definition | meeting stages 1 and 2, and being specific, owned, scheduled and evidenced |
| 4. Risk statement | Where practice falls short, and what it could cost | assessment results, POA&M | the requirement it fails (stages 1 and 2), condition, cause, threat, impact, scope and rating |
| 5. Recommendation | How to get back on the path | assessment results, POA&M | fixing the cause in stage 4, and being actionable, owned, dated and verifiable |

Like a platform team's golden path, the aim is to make the right way the easy
way: show what good looks like at each stage, check your text against it, and
say how to close the gaps.

The portal around those checks follows the three A's of CSA's
[Internet Hygiene Portal](https://ihp.csa.gov.sg/) (IHP), which checks websites
and email against internet best practices:

| | IHP | PolicyGP |
| --- | --- | --- |
| **Awareness** | Guides on internet hygiene standards | **Guides**: each best practice with why it matters, how to adopt it, and a weak and a strong example |
| **Assessment** | Self-service health checks for website, email and connectivity | **Health check** for one statement, **batch health check** for OSCAL or CSV files |
| **Adoption** | Actionable suggestions to adopt best practices | Each practice marked **adopted**, **partly adopted** or **not yet adopted**, with how to adopt it, plus the specific areas for improvement |

Each item gets a **confidence score** (0 to 100%), a count of **best
practices adopted**, and its **areas for improvement**. Unlike IHP's rating,
PolicyGP does not pass or fail anything: use the results in your own review
process to decide that.

This project is not affiliated with or endorsed by the Cyber Security Agency
of Singapore; it borrows IHP's approach, not its content.

```
$ policygp examples/assessment-results-example.json
Kind            Item                                               Confidence  Practices adopted  Improvements
--------------  -------------------------------------------------  ----------  -----------------  ------------
Risk statement  Leaver accounts can approve payments [ac-2_smt.j]        100%                8/8             0
Recommendation  Automate leaver deprovisioning [ac-2_smt.j]               98%                7/7             0
Risk statement  Audit review gaps [au-6]                                   5%                0/8             9
Recommendation  Improve log review [au-6]                                 11%                0/7             8

2 risk statements: average confidence 52%, 8 of 16 best practices adopted, 1 with areas for improvement.
2 recommendations: average confidence 55%, 7 of 14 best practices adopted, 1 with areas for improvement.

Areas for improvement
---------------------

Risk statement: Audit review gaps [au-6]  (5%)
  - State the condition as fact, with the evidence found (for example '14 of 60 sampled accounts belonged to leavers').
  - Explain the cause, so the recommendation can address it.
  ...

Recommendation: Improve log review [au-6]  (11%)
  - State a concrete action, starting with a verb ('Disable ...', 'Configure ...').
  - Set a target date in proportion to the risk (risk low).
  - 'consider' makes the action optional; state the action to take.
  ...
```

The exit code is `0` whenever the document was assessed and `2` on bad input.

## Use it

| Way | For | How |
| --- | --- | --- |
| **Online** | Anyone, nothing to install | https://code1sentinel.github.io/policy-golden-path/ |
| **Local web app** | The same page, run on your machine | `policygp-web --open` |
| **Command line** | CI pipelines and scripts | `policygp FILE` |

The online version runs entirely in your browser: PolicyGP's Python runs
there through [Pyodide](https://pyodide.org), served from the site itself.
Your files are checked on your device and never uploaded, and the site makes
no requests to any third party. The first visit loads about 13 MB (less over
the wire, as it is compressed), which the browser then caches; after that each
check takes a fraction of a second. All three ways run the same code and give
the same scores.

## Install

```
git clone https://github.com/code1sentinel/policy-golden-path.git
cd policy-golden-path
pip install -e .   # installs the policygp and policygp-web commands; no other dependencies
```

Python 3.10 or later.

## Web app

```
policygp-web --open
```

Opens the portal at http://localhost:8765/ with three sections:

- **Guides**: the best practices for each kind of text, each with why it
  matters, how to adopt it, and a weak and a strong example.
- **Health check**: choose implementation statement, risk statement or
  recommendation, paste the text, and optionally add context: the control
  requirement and policy intent; likelihood and impact for a risk; the risk
  statement, rating, owner and target date for a recommendation. The result
  shows the confidence, how many best practices are adopted, the areas for
  improvement, and each practice with how to adopt it. **Load example** fills
  in a weak example of each kind.
- **Batch health check**: drop an Excel workbook or CSV with one row per
  policy (columns `policy intent`, `control statement`, `risk statement`,
  `recommendation`; the page shows them and offers Excel and CSV templates), or OSCAL JSON files (SSP,
  component definition, assessment results, POA&M), several at once, with an
  optional catalog and policy file. Results show the average confidence and
  practices adopted per kind, a **by file** table, then every item,
  which you can filter by kind, search, sort, and expand. Download them as
  CSV, JSON or Markdown. A file that cannot be read is listed with the reason
  and the rest are still assessed.

Confidence bars use one colour throughout, and adoption status is shown by
label and shape rather than red and green: the page shows scores, not pass or
fail.

| Option | Default | |
| --- | --- | --- |
| `--host` | `127.0.0.1` | Interface to bind |
| `--port` | `8765` | Port |
| `--open` | off | Open the page in a browser |

The server uses only the Python standard library. It has **no
authentication**, so it listens on this machine only by default; binding
another interface prints a warning. It refuses cross-site requests, limits
requests to 20 MB, keeps nothing on disk, and renders uploaded text as text,
never markup.

## Command line

```
policygp DOCUMENT [options]

-c, --catalog PATH          OSCAL catalog (JSON) for control requirement text
-p, --policy PATH           policy file (JSON) with the policy intent for each control
-i, --intent TEXT           a policy intent applied to every implementation statement
-f, --format FORMAT         table (default), json or markdown
-o, --output PATH           write the report to a file
--assessment-results PATH   also write the results as OSCAL observations
```

## Inputs

| Document | What is read |
| --- | --- |
| `system-security-plan` | Each `by-components[].description` under an implemented requirement, and under each of its `statements[]`. Component names come from `system-implementation.components`. A requirement with no description at all is still listed, and scores 0. |
| `component-definition` | Each `statements[].description` under an implemented requirement. When a requirement has no statements, its own `description` is read instead. |
| `assessment-results` | For each risk in each result: its `statement` as a risk statement, and each `remediations[]` entry with `lifecycle: recommendation` as a recommendation. |
| `plan-of-action-and-milestones` | The same, from the top-level `risks`. |
| CSV (`.csv`) or Excel (`.xlsx`) | One row per policy: policy intent, control statement, risk statement, recommendation. See below. |

For risks, the control comes from the findings that reference the risk
(`related-risks`) and their `target.target-id`. `--catalog` and `--policy`
apply to risk statements through those controls, as they do to
implementation statements. Ratings come from the
`characterizations` facets named `likelihood`, `impact`, `risk`, `severity` or
`priority`. A recommendation's date comes from its tasks' `timing`, or else the
risk's `deadline`; its owner from its tasks' `responsible-roles` or its
`origins`.

Any OSCAL catalog in JSON works as the `--catalog`, including published ones
tested with PolicyGP:

| Catalog | Publisher | Control ids |
| --- | --- | --- |
| [NIST SP 800-53](https://github.com/usnistgov/oscal-content) | NIST, United States | `ac-2`, `ac-2_smt.j` |
| [Information Security Manual (ISM)](https://github.com/AustralianCyberSecurityCentre/ism-oscal) | ASD, Australia | `ism-1997` |
| [ICT&SS Policy (IM8) Reform](https://github.com/GovTechSG/tech-standards) | GovTech, Singapore | `as-1` |

The ISM's resolved profile catalogs (for example the Essential Eight maturity
levels) are catalogs too, so they work the same way.

Only JSON OSCAL is supported. Convert XML or YAML with the NIST OSCAL CLI
first.

### CSV and Excel

The easiest way to start, for example from a spreadsheet. **One row per
policy**, followed down the golden path. These four columns are required; a
cell can be left empty when a row has nothing for it:

| policy intent | control statement | risk statement | recommendation |
| --- | --- | --- | --- |
| What your policy says the control must achieve | How the control is implemented today | Where practice falls short, and what it could cost | How to close the gap |

Each row gives up to three items to assess, checked along the path:

- the **control statement** against the row's policy intent,
- the **risk statement** against the same policy intent,
- the **recommendation** against the row's risk statement.

Optional columns add context: `control id`, `control requirement` (the control
text, when no catalog is given), `title` (labels the row's risk and
recommendation), `likelihood`, `impact`, `owner` and `target date`.

Column names are not case-sensitive; spaces, hyphens and underscores are
interchangeable, and common alternatives work too (`implementation
statement`, `remediation`, `deadline`).

- **Excel workbooks (`.xlsx`)** are read directly. The first sheet whose header
  row has the four columns is used, so a workbook can keep instructions or
  other tabs; formulas are read as their last calculated value and date cells
  as dates. Old `.xls` workbooks need saving as `.xlsx` first.
- **CSV** files may be comma, semicolon or tab separated, in UTF-8.

Download a template with a strong and a weak example row from the web app, as
Excel (`/api/template.xlsx`) or CSV (`/api/template.csv`).

Workbooks are read with the Python standard library, so there is still
nothing extra to install. Because they are untrusted input, oversized files
(zip bombs) and XML with a DOCTYPE are refused.

## Best practices

Each criterion below is a best practice. A practice is **adopted** when it
scores 80% or more and has no outstanding area for improvement, **partly
adopted** from 40% (or when a high score still has an improvement open), and
**not yet adopted** below that. Every area for improvement belongs to one
practice, so the counts and the list always agree.

Wording issues (hedges, open-ended examples, obligations, placeholders and
planned work) count against a practice of their own: **State facts about
today** for implementation statements, **Keep it factual** for risk
statements, **Keep it firm** for recommendations. It has no weight, because
wording already reduces the score directly. The guides for every practice are in
`src/policygp/guides.py`, shown in the web app's Guides section.

All three kinds share the same wording rules, adjusted to what each is for:

| Wording | Implementation statement | Risk statement | Recommendation |
| --- | --- | --- | --- |
| Vague: `as needed`, `periodically`, `where possible`, `some`, `various` | reduces | reduces | reduces |
| Possibility: `may`, `might`, `could`, `should` | reduces | fine ("could allow an attacker") | fine |
| Obligation: `must`, `shall`, `is required to` | reduces: it restates the requirement | fine | fine |
| Tentative action: `consider`, `explore`, `look into`, `where feasible` | | | reduces |
| Open-ended examples: `such as`, `e.g.`, `for example`, `etc.` | reduces, unless the text says where the full set is defined | reduces | reduces |

Each distinct phrase takes 8% off the score, up to 40% in total. Placeholder
or empty text (`TBD`, `N/A`, `[insert ...]`) is limited to 20%.

### Implementation statements

| Criterion | Weight | Asks |
| --- | --- | --- |
| coverage | 20% | Does it address every part of the control requirement? (needs `--catalog`) |
| policy_intent | 20% | Does it meet the policy intent? (needs `--policy` or `--intent`) |
| substance | 12% | Is there enough detail to describe an implementation? |
| responsibility | 12% | Does it name who does it? |
| mechanism | 12% | Does it name the tool, configuration or procedure? |
| frequency | 12% | Does it say how often, or what triggers it? |
| evidence | 12% | Does it say what records an assessor can inspect? |

When there is no catalog or no policy intent, the other weights scale up to
100%. Describing planned work (`will be implemented`, `roadmap`) limits the
score to 50%. Nothing about the policy limits the score: falling short of it
lowers the `policy_intent` criterion like any other.

### Risk statements

| Criterion | Weight | Asks |
| --- | --- | --- |
| condition | 20% | Is what is wrong stated as fact, with the evidence found? ("14 of 60 sampled accounts...") |
| impact | 20% | What is the effect on the system's data, service or the business? |
| cause | 15% | Why did it happen, specifically enough to fix? |
| threat | 15% | Who or what could exploit it, and how likely is that? |
| scope | 10% | Which systems, accounts or components, and how many? |
| criteria | 10% | Which control or policy requirement is not met? With `--catalog` or `--policy`, the condition should also be described in that requirement's terms. |
| rating | 10% | Are likelihood and impact recorded in `characterizations`, and consistent with the text? A `low` rating on a statement about fraudulent payments is flagged. |

Remediation advice inside a risk statement ("the team should...") is flagged
to move into a recommendation.

### Recommendations

| Criterion | Weight | Asks |
| --- | --- | --- |
| actionable | 20% | Does it lead with a concrete action? ("Disable...", "Integrate...") |
| root_cause | 20% | Does it fix the cause named in the risk statement, not just the symptom? |
| specific | 15% | Does it name the system, setting or process to change? |
| owner | 15% | Is someone accountable? (from the text, or `responsible-roles`) |
| timeline | 15% | Is there a target date? (from the text, task `timing` or the risk `deadline`) The improvement quotes the risk rating so the date can be set in proportion to it. |
| completion | 15% | What evidence will show it is done, so the risk can be closed? |

## Policy intent

OSCAL has no field for what your organization's policy requires, so it is a
separate input for implementation statements. Give it as a policy file, an
inline intent, or both:

```
policygp ssp.json -c catalog.json --policy policies.json
policygp ssp.json --intent "Access is reviewed at least quarterly and records are retained for 12 months."
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
than one policy matches a statement, all of them apply.

The `policy_intent` criterion is 40% whether the statement speaks to the
intent (its key terms) and 60% what the intent asks for, which depends on the
kind of policy.

### Fixed commitments

When the intent states measurable commitments, the statement must keep them:

| Commitment | Intent says | Kept by | Falls short |
| --- | --- | --- | --- |
| How often | `at least quarterly`, `every 30 days` | the same or more often (`every 90 days`, `monthly`) | `annually` |
| Time limit | `within 5 business days`, `within 24 hours` | the same or faster | `within 30 days` |
| Retention | `retained for at least 12 months`, `3-year retention` | the same or longer | `kept for 6 months` |

A commitment the statement leaves out earns nothing; one it falls short of
counts against it, so falling short scores lower than leaving it out.

### Risk-based intent

A risk-based intent sets a principle and leaves the values to you:
"reviewed at a frequency commensurate with the risk of the access". It is
recognised by wording such as `risk-based`, `commensurate with risk`,
`based on criticality` or `risk tier`, and needs no fixed timeline. Instead the
statement must show how risk becomes a schedule:

| Check | Looks for |
| --- | --- |
| Risk basis | How items are rated: tiers, classification, criticality, privileged or high-risk |
| Schedule per tier | A concrete frequency or time limit for each tier |
| Ownership | Who sets the tiers, and when they are revisited or reassessed |

"Managers review access based on risk" scores low on all three. This scores
full marks:

> Accounts are tiered in the annual access risk assessment owned by the CISO:
> Tier 1 covers privileged and payment access, Tier 2 everything else.
> Managers review Tier 1 access quarterly and Tier 2 access annually in Okta.
> Tiers are reassessed after major changes.

An intent can mix both, for example risk-based review frequency with a fixed
5-day removal time; each part is checked.

## How it scores

All checks run offline and are deterministic: the same text always gets the
same score, and nothing is sent anywhere. The checks look for the signals in
the tables above, so they reward text written the way an assessor needs it,
but they cannot tell whether what the text says is true.

## Output

| Flag | Output |
| --- | --- |
| `-f table` | Scores, a summary per kind, and the areas for improvement (default) |
| `-f json` | Every score, criterion, improvement and rationale |
| `-f markdown` | The same as a report, for a PR comment or job summary |
| `--assessment-results PATH` | An OSCAL `assessment-results` document with one `observation` per item: its confidence, practices adopted, kind, control and original uuid as props, and the improvements in `remarks` |

## Use in GitHub Actions

```yaml
- run: pip install git+https://github.com/code1sentinel/policy-golden-path.git
- run: policygp ssp.json -c catalog.json -p policies.json -f markdown -o report.md
- run: cat report.md >> "$GITHUB_STEP_SUMMARY"
```

## Development

CI runs the tests on Python 3.10, 3.12 and 3.13 on every push and pull request
(`.github/workflows/ci.yml`).

### The online site

`.github/workflows/pages.yml` builds and publishes the site to GitHub Pages
on every push to `main` (enable it once under Settings → Pages → Source:
GitHub Actions). To build it locally:

```
npm pack pyodide@314.0.7 && tar xzf pyodide-314.0.7.tgz
python scripts/build_site.py --pyodide package --out site
python -m http.server --directory site
```

The build copies the web app in browser mode, zips the `policygp` package
(without the server and command-line modules) for Pyodide to import, and
writes the guides, config and templates as static files. A fork gets its own
site by enabling Pages the same way.

```
pip install -e ".[dev]"
pytest
```

## Layout

```
src/policygp/
  cli.py        command line (policygp)
  webapp.py     web app server (policygp-web)
  api.py        request handling, shared by the server and the browser build
  guides.py     best-practice guides and adoption status
  static/       web app page, styles and script (server or browser mode)
  service.py    the pipeline both share
  tabular.py    CSV and Excel input, and the templates
  xlsx.py       reads and writes .xlsx workbooks with the standard library
  loader.py     reads each supported OSCAL document
  findings.py   risk statements and recommendations out of assessment results and POA&Ms
  catalog.py    control and statement-part text out of catalogs
  policy.py     policy intents and which statements they apply to
  heuristic.py  offline rubrics for each kind
  report.py     table, JSON, Markdown and OSCAL output
scripts/build_site.py   builds the browser-only site for GitHub Pages
examples/       NIST SP 800-53 excerpt, example SSP, component definition, policies and assessment results
tests/
```

## Origin

Started in the [GRC Engineering Club Singapore Chapter](https://github.com/code1sentinel/grcengineeringclub-singapore)
repository and moved here with its history.

## License

MIT. See [LICENSE](LICENSE).
