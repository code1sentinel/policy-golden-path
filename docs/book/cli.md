# Command line and Python

The same conversion as the web app, for scripts and pipelines. Rule drafts only — the CLI never calls AI.

## Install

Python 3.10 or later. The package has no runtime dependencies.

```
git clone https://github.com/code1sentinel/policy-golden-path.git
cd policy-golden-path
pip install -e .
```

That installs two commands: `codify` and `codify-web`.

## `codify`

```
codify policy.docx                       # summary and every draft, as text
codify policy.docx -f oscal -o out.json  # the OSCAL catalog
codify policy.docx -f report             # Markdown conversion report
codify policy.csv -f xlsx -o out.xlsx    # one row per control
codify out.json -f report                # reopen a saved catalog
```

Formats: `text` (default), `oscal`, `report`, `csv`, `xlsx`.

Inputs: Word, CSV, Excel, Markdown or text, or a saved catalog JSON.

## `codify-web`

```
codify-web --open
```

Serves the app at http://127.0.0.1:8765/ on this machine only. It has no authentication, refuses cross-site requests, and keeps nothing on disk.

## Python

The web app, the CLI, and the Pages site all call the same package (`codify`). There is no separate public HTTP API to a Codify server.

Typical library use from a script is the same actions the CLI uses: open a policy, then export. See `src/codify/api.py` if you are wiring a pipeline.

## Acme demo

[`examples/acme-information-security-policy-2016.md`](https://github.com/code1sentinel/policy-golden-path/blob/main/examples/acme-information-security-policy-2016.md) is the fictional demo policy. [`examples/acme-policy-key.md`](https://github.com/code1sentinel/policy-golden-path/blob/main/examples/acme-policy-key.md) explains what each clause is there to show.
