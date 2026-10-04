# Codify

**Turn legacy policy clauses into OSCAL control statements.**

A tool for GRC professionals modernising a legacy policy. Give it the policy,
and Codify:

1. **Sorts** every clause: requirement, scope, definition, role, exception, or
   not a control (aspirations, consequences, permissions). Duplicates are
   flagged.
2. **Drafts** control statements from the requirements: the action first, no
   tools, testable.
3. **Checks** each draft as you edit it, and shows its parts (action, scope,
   limit, purpose), so a missing one is easy to see.
4. **Exports** an OSCAL catalog, which is also your save file, plus Excel, CSV
   and a conversion report.

```
4.1 User accounts shall be reviewed regularly and access that is no longer
    required shall be removed as appropriate.

    -> Review user accounts at least every [N] days.
    -> Remove access that is no longer required within [N] days.
```

The drafts come from rules, not AI: the same policy always gives the same
drafts, and your policy never leaves your device. The drafts are a starting
point to edit, not finished controls. If you want, you can also
[draft with AI](#ai-drafting-optional) using your own API key, one clause at a
time.

## Use it

| Way | For | How |
| --- | --- | --- |
| **Online** | Anyone, nothing to install | https://code1sentinel.github.io/policy-golden-path/ |
| **Local web app** | The same page, run on your machine | `codify-web --open` |
| **Command line** | Scripts and pipelines | `codify POLICY` |

The online version runs entirely in your browser: Codify's Python runs there
through [Pyodide](https://pyodide.org), served from the site itself. Your
policy is read on your device and never uploaded, and neither the site nor
`codify-web` loads fonts or other assets from a third party. The page
makes no requests to any third party unless you turn on AI drafting. The first visit
loads about 13 MB, which the browser then caches. All three ways run the same
code.

To see it work, paste a clause and press **Codify**, or choose **Try an
example** to open the **Acme demo policy**
([`examples/acme-information-security-policy-2016.md`](examples/acme-information-security-policy-2016.md)):
a fictional 2016 agency policy written with typical legacy problems.
[`examples/acme-policy-key.md`](examples/acme-policy-key.md) explains what
each clause is there to show.

## What goes in

| Input | How it is read |
| --- | --- |
| Pasted text | The clause text, one paragraph per clause. Numbers are optional. A single paragraph that starts with a number (`4.2.1 …`) is kept as-is. A longer policy may still split on its own numbering (`5. Access Control` is a section, `5.1` a clause, `(a)` an item that carries its lead-in). |
| Word (`.docx`) | The same, with Word's headings as sections. Read with the Python standard library. |
| CSV or Excel (`.xlsx`) | One clause per row: a `clause text` column, and optionally `clause id` and `section`. |
| A saved catalog (`.json`) | Opens exactly where you left off. Any other OSCAL catalog opens as a starting point: each control becomes a clause to work on. |

PDF is not read: copy the text and paste it.

## How clauses are sorted

A section heading decides first: every clause under "Definitions" is a
definition, under "Roles and Responsibilities" a role. Otherwise the clause's
own wording decides:

| Type | Recognised by | Becomes |
| --- | --- | --- |
| Requirement | shall, must, should, will, is required to, is prohibited, or a present-tense rule ("Firewall rules are reviewed quarterly") | one or more control statements |
| Scope | "This policy applies to…" | the catalog's "Applies to" |
| Definition | "X means…", "refers to" | the catalog's back matter |
| Role | "is responsible", "is accountable" | the "who" for implementation, not a control |
| Exception | how exceptions or waivers are approved | catalog metadata |
| Not a control | aspirations ("committed to", "encouraged"), "discouraged", consequences ("disciplinary action"), permissions, descriptions of the policy itself | nothing: listed in the report |

A requirement that repeats an earlier one is marked as a duplicate of it and
gets no control of its own. Every clause shows the reason it was sorted the
way it was, and you can change its type: making a clause a requirement drafts
controls for it.

## How drafts are made

| Legacy wording | What the rules do | Example |
| --- | --- | --- |
| Several requirements in one clause | Split, one control each (not inside "who leave, transfer, or…") | "shall not share…, write…, or reuse…" → two prohibitions |
| Passive voice | Made active, action first | "Access shall be granted…" → "Grant access…" |
| The organisation as subject | Dropped; kept as the "who" for the implementation | "The IT Department shall back up…" → "Back up…" |
| People as subject | Kept as scope | "Users must not send…" → "Prohibit users from sending…" |
| Vague timing | A parameter for the organisation to set | "regularly" → "at least every [N] days"; "timely" → "within [N] days" |
| Legacy values | Kept as parameter values | "every 90 days" → "at least every [90] days" |
| Tools named | Moved to guidance, a generic term in their place | "Symantec Endpoint Protection shall be installed" → "Install anti-malware software", guidance "e.g. Symantec Endpoint Protection" |
| Hedges | Dropped, with a note to confirm the requirement | "should… where practical" |
| Untestable wording | Kept, with a note | "take appropriate action", open-ended "such as" lists |

Every draft carries notes saying what changed and what a person should decide.

## Checking control statements

Each statement is scored for how well it is written as a catalog control:
action first, tool-neutral, testable, and against OSCAL's own conventions.
Weights are relative: they are rescaled to add up to 100%. Well-written
requirements score in the 90s; tool-specific implementation text scores
around 60%; weak requirements ("Systems should be patched regularly where
possible") around 30%.

| Criterion | Weight | Asks |
| --- | --- | --- |
| testable | 25% | Can an assessor test it? A recurring activity (review, test, back up, patch) needs how often or how fast, a trigger or a parameter; "regularly" does not count. A standing requirement (configure, restrict, encrypt) is testable as written. |
| scope | 20% | Does it say what it applies to? A statement with nothing concrete is limited to 40%. |
| action_first | 15% | Does it start with the action, not a subject ("The IT team…", "Okta…")? |
| tool_neutral | 10% | Does it avoid naming products? |
| purpose | 10% | Does it say why ("to deter brute-force attacks"), or is the risk it treats given? |
| single | 5% | One requirement, or two closely joined. |
| labeled_parts | 5% | Is a bundle of three or more requirements split into lettered parts (a., b., c.), the way an OSCAL catalog control gives each its own referenceable part? |
| determinable | 5% | Can an assessor decide pass or fail? Subjective words ("robust", "adequate", "appropriate") cannot be tested, in the sense of a NIST SP 800-53A assessment objective. |

Hedges ("should", "may"), vague wording and open-ended lists reduce the score.
A score describes how a statement is written, not whether it is true; the
Guide in the app explains each practice with a weak and a strong example.

## AI drafting (optional)

AI drafting is off unless you turn it on (**AI drafting** at the top of the
page). Bring your own API key from Anthropic (Claude), OpenAI or Google
(Gemini), and use any model your account has. Or choose **Ollama** to draft
with a model running on this machine at `http://localhost:11434`: no API key,
and the clause never leaves this device. Ollama works with `codify-web`;
browsers block `http://localhost` from the HTTPS online site.

- **What is sent**: one clause per request: its text, its section heading and
  Codify's rule drafts for it. Nothing else from the policy. The request goes
  straight from your browser to the provider, under your account and its
  terms; there is no Codify server in between.
- **Do not send classified or sensitive text.** Turning AI drafting on asks you
  to confirm this, and drafting several clauses at once asks once more, naming
  the provider and how many clauses will be sent.
- **Your key** stays in your browser: kept for the tab only, unless you choose
  to remember it on that device. It is never put in the project, the autosave
  or any export. "Turn off" forgets it.
- **What comes back**: the AI fills in the parts of each statement (action,
  scope, limit, purpose) plus guidance and the risk; Codify joins the parts,
  scores the statement like any other draft and marks it **drafted by AI**
  (`origin: ai` in the catalog), with a note to check it against the legacy
  clause. AI drafts stay drafts, and the note keeps them out of "Select ready
  drafts", so a person reviews each one.
- **Where**: "Draft with AI" on a clause replaces its controls; with controls
  selected, the bulk "Draft with AI" redrafts their clauses one by one, and can
  be stopped. Clauses whose controls you have edited, reviewed or accepted are
  left alone in bulk.

The prompt is in [`src/codify/ai.py`](src/codify/ai.py). The command line and
the rule drafts never use AI.

## Reviewing

The workspace lists requirement clauses, with their controls under each. Select a
control to edit the statement next to its legacy clause. Mark it **reviewed** or
**accepted**, then go to the next clause. Add the risk it treats (its purpose);
guidance and who implements it sit under disclosure in the editor.

- **Filters and bulk** sit under **More** in the clause list: drafts, reviewed,
  accepted, below 80%, or the clauses that did not become controls. "Select ready
  drafts" ticks drafts scoring 80% or more with no notes left to decide, and
  "Select shown" every control the filter shows; then mark them reviewed or
  accepted, or draft them again with AI.
- **Keyboard**: <kbd>j</kbd>/<kbd>k</kbd> next and previous,
  <kbd>r</kbd> reviewed, <kbd>a</kbd> accepted.
- **Saving**: work is kept in your browser as you go. **Save OSCAL catalog**
  downloads the catalog, which is the file to keep, share or put in git, and
  opens again later.

## What comes out

**OSCAL catalog** (JSON, OSCAL 1.1.2; CI checks every catalog against NIST's
schema). One group per policy section and one control per statement:

| In the catalog | From |
| --- | --- |
| `parts[name=statement]` | the control statement, with each `[value]` as a parameter (`params`, labelled from its unit: "time period (days)", "number of attempts") |
| `parts[name=guidance]` | tools and how-to moved out of the statement |
| `parts[name=legacy-text]` | the legacy clause it came from |
| `parts[name=drafting-notes]` | what the rules changed, and what to decide |
| `props`: `legacy-clause`, `status`, `origin`, `risk-statement`, `responsible-role` | traceability and review state |
| `links[rel=derived-from]` | the legacy clause, kept in `back-matter` |
| `back-matter.resources` | every legacy clause, with its type and the reason |

Codify's own names are in the namespace `https://grcengineering.club/ns/codify`.

**Excel and CSV**: one row per control (legacy clause, statement, parameters,
guidance, risk, who, status, score, notes), then the clauses that did not
become controls. Cells that would run as spreadsheet formulas are escaped.

**Conversion report** (Markdown): "43 clauses → 38 controls", the status, every
control with its score, what still needs attention, and the clauses that are not
controls, with the reason.

## Command line

```
codify policy.docx                       # summary and every draft, as text
codify policy.docx -f oscal -o out.json  # the OSCAL catalog
codify policy.docx -f report             # Markdown conversion report
codify policy.csv -f xlsx -o out.xlsx    # one row per control
codify out.json -f report                # reopen a saved catalog
```

## Install

```
git clone https://github.com/code1sentinel/policy-golden-path.git
cd policy-golden-path
pip install -e .   # the codify and codify-web commands; no other dependencies
```

Python 3.10 or later. `codify-web --open` serves the app at
http://localhost:8765/ on this machine only; it has no authentication, refuses
cross-site requests and keeps nothing on disk.

## Development

Workflow for agents and humans: [`AGENTS.md`](AGENTS.md). Short version:
[`CONTRIBUTING.md`](CONTRIBUTING.md). Product baseline: [`docs/prd.md`](docs/prd.md).
Changelog: [`CHANGELOG.md`](CHANGELOG.md).

```
pip install -e ".[dev]"
pytest
ruff check src tests scripts
mypy src
```

The browser tests in `tests/e2e` drive the web app in Chromium, with the AI
providers faked; they are skipped unless Playwright is installed:

```
pip install -e ".[e2e]"
python -m playwright install chromium
pytest tests/e2e                                   # against codify-web
CODIFY_SITE=site pytest tests/e2e                  # against a site built with build_site.py
```

CI runs them both ways.

`tests/test_acme.py` holds Codify to the Acme key: every clause sorted as the
key says, the duplicate found, every requirement drafted, and every draft
action-first and tool-free.

### The online site

`.github/workflows/pages.yml` builds and publishes the site to GitHub Pages on
every push to `main`. To build it locally:

```
npm pack pyodide@314.0.7 && tar xzf pyodide-314.0.7.tgz
python scripts/build_site.py --pyodide package --out site
python -m http.server --directory site
```

## Layout

```
src/codify/
  clauses.py    read a policy into clauses: text, Word, CSV, Excel
  classify.py   sort clauses and find duplicates
  draft.py      rule-based drafting of control statements
  control.py    the control statement check, and the parts of a statement
  text.py       shared wording, commitment and coverage checks
  project.py    the project, the OSCAL catalog (save and open), Excel, CSV, report
  ai.py         the AI drafting prompt, and the reply turned into drafts
  api.py        the request API, shared by the local server and the browser
  webapp.py     local web server (codify-web)
  cli.py        command line (codify)
  guides.py     the best-practice guide
  xlsx.py       Excel reader and writer, standard library only
  static/       the web app, and the Acme demo policy
scripts/        build the online site; make a .docx; validate OSCAL
examples/       the Acme demo policy (Markdown and Word) and its key
```

## Origin

Codify replaces Vitals, a health check for OSCAL statements from the same
project; its last version is kept on the `vitals-v0.19` branch. It started in
the [GRC Engineering Club Singapore](https://github.com/code1sentinel/grcengineeringclub-singapore)
repository.

## License

MIT. See [LICENSE](LICENSE).
