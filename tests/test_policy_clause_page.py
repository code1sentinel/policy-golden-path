"""Policy clause page (Flow B step 1): one calm capture surface."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")


def _clause_js() -> str:
    assert "function renderClauseStep" in JS
    return JS.split("function renderClauseStep", 1)[1].split("function renderIdentifyStep", 1)[0]


def test_clause_page_copy_is_a_capture_surface():
    body = _clause_js()
    assert "Paste your policy clause" in body
    assert "write a control statement for each one next" in body
    assert "Continue to control statements" in body
    assert "Add clauses" in body
    assert "Back to the landing" in body
    assert "clause-continue" in body
    assert "clause-back" in body
    assert "clause-steps" in body
    assert "Policy clause" in body
    assert "Control statements" in body
    assert "Policy as code (Rego)" in body
    assert "Add details" in body
    assert "blank line" in body


def test_clause_page_has_no_codify_demo_or_wizard_chrome():
    body = _clause_js()
    assert "Codify" not in body
    assert "Try an example" not in body
    assert "Open a file" not in body
    assert "Example clause" not in body
    assert "Hide guide" not in body
    assert "Previous" not in body
    assert "Common mistakes" not in body
    assert "paste-submit" not in body
    assert "<table" not in body.lower()
    assert "GRC Engineering Club" not in body
    assert "name=\"title\"" not in INDEX
    assert 'id="paste-submit"' not in INDEX


def test_clause_page_uses_existing_tokens():
    assert ".clause-page" in CSS
    assert ".clause-paste" in CSS
    assert ".clause-example" in CSS
    assert "flow-view--clause" in CSS
    title_css = CSS.split(".clause-title {", 1)[1][:400]
    assert "var(--text)" in title_css
    assert "fonts.googleapis" not in CSS
    assert "Inter" not in CSS.split("Policy clause page", 1)[1][:2500]
