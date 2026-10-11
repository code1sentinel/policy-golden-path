# Codify agent and contributor rules

Codify turns legacy policy clauses into OSCAL 1.1.2 control statements on the person's device.

Product behaviour is defined by [`docs/prd.md`](docs/prd.md) and
[`docs/adr/`](docs/adr/), not improvisation. Humans: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Pointers

- **PRD / ADR / slices:** [`.cursor/rules/prd-adr-slices.mdc`](.cursor/rules/prd-adr-slices.mdc)
- **TDD** (red → green at the slice Given / When / Then): [`.cursor/skills/tdd/`](.cursor/skills/tdd/SKILL.md)
- **Diagnose** a failing test, golden, e2e run, or regression: [`.cursor/skills/diagnosing-bugs/`](.cursor/skills/diagnosing-bugs/SKILL.md)
- **Review** Standards vs Spec, including refactoring: [`.cursor/skills/code-review/`](.cursor/skills/code-review/SKILL.md)
- **Privacy** (no new outbound call without an ADR; never write an AI key): [`.cursor/rules/privacy.mdc`](.cursor/rules/privacy.mdc)
- **UI** (Mobbin citations before implementation): [`.cursor/rules/mobbin-ui.mdc`](.cursor/rules/mobbin-ui.mdc)
- **CI / merge / done:** [`.cursor/rules/ci-merge.mdc`](.cursor/rules/ci-merge.mdc)
- **OSCAL** goldens + NIST 1.1.2: [`.cursor/rules/oscal-goldens.mdc`](.cursor/rules/oscal-goldens.mdc)

Adapted skills: [`THIRD_PARTY.md`](THIRD_PARTY.md).

## Unusual commands

```bash
pip install -e ".[dev]"
pip install -e ".[e2e]" && python -m playwright install chromium
pytest tests/e2e                    # against codify-web
CODIFY_SITE=site pytest tests/e2e   # against a site from build_site.py
pip-audit --skip-editable           # clean venv or CI; do not audit the system Python
gitleaks detect --source . --redact --config .gitleaks.toml
```

OSCAL schema (CI job `oscal-schema`; Node 20 + a network fetch of the schema):

```bash
mkdir -p out
codify examples/acme-information-security-policy-2016.md -f oscal -o out/acme-md.json
curl -sSLf -o out/schema.json \
  https://github.com/usnistgov/OSCAL/releases/download/v1.1.2/oscal_catalog_schema.json
npm install --no-save --silent ajv@8 ajv-formats@3
node scripts/validate_oscal.mjs out/schema.json out/acme-md.json
```

Pages site (local):

```bash
npm pack pyodide@314.0.7 && tar xzf pyodide-314.0.7.tgz
python scripts/build_site.py --pyodide package --out site
```

`codify-web --open` binds `http://127.0.0.1:8765/` on this machine only.
`pytest`, `ruff check src tests scripts`, and `mypy src` are the usual checks.
