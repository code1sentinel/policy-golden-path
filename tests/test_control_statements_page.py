"""Control statements page (shared step 2): one calm drafting surface."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")


def _statements_js() -> str:
    assert "function statementItemsFor" in JS
    return JS.split("function statementItemsFor", 1)[1].split("function renderLinkStep", 1)[0]


def test_statements_page_copy_is_a_drafting_surface():
    body = _statements_js()
    assert "Write a control statement for each risk" in body
    assert "Write a control statement for each clause" in body
    assert "What makes a good control statement" in body
    assert "AES-256 using managed keys" in body
    assert "Continue to policy as code" in body
    assert "Add another statement" in body
    assert "Insert from library" in body
    assert "statements-continue" in body
    assert "statements-back" in body
    assert "statements-steps" in body
    assert "Identify risks" in body
    assert "Policy clause" in body
    assert "Control statements" in body
    assert "Policy as code (Rego)" in body


def test_statements_page_has_no_wizard_or_library_panel():
    body = _statements_js()
    assert "Suggest from library" not in body
    assert "optional-clause" not in body
    assert "Hide guide" not in body
    assert "Previous" not in body
    assert "Common mistakes" not in body
    assert "identified risk to continue" not in body.lower()
    assert "likelihood" not in body.lower()
    assert "<table" not in body.lower()


def test_statements_page_uses_existing_tokens():
    assert ".statements-page" in CSS
    assert ".statements-layout" in CSS
    assert ".statements-dot" in CSS
    assert "flow-view--statements" in CSS
    title_css = CSS.split(".statements-title {", 1)[1][:400]
    assert "var(--text)" in title_css
    assert "fonts.googleapis" not in CSS
    assert "Inter" not in CSS.split("Control statements page", 1)[1][:2500]
