"""Identify risks page (Flow A step 1): one calm capture surface."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")


def _identify_js() -> str:
    assert "function renderIdentifyStep" in JS
    return JS.split("function renderIdentifyStep", 1)[1].split("function renderDevelopStep", 1)[0]


def test_identify_page_copy_is_a_capture_surface():
    body = _identify_js()
    assert "What risks have you identified?" in body
    assert "How to write a good risk statement" in body
    assert "Unauthorised access to customer data due to shared admin accounts" in body
    assert "Continue to control statements" in body
    assert "Add a risk" in body
    assert "Back to the landing" in body
    assert "identify-continue" in body
    assert "identify-back" in body
    assert "identify-steps" in body
    assert "Identify risks" in body
    assert "Control statements" in body
    assert "Policy as code (Rego)" in body


def test_identify_page_has_no_register_or_wizard_chrome():
    body = _identify_js()
    assert "flow-risk-add" not in body
    assert "Add an identified risk" not in body
    assert "likelihood" not in body.lower()
    assert "heatmap" not in body.lower()
    assert "owner" not in body.lower()
    assert "<table" not in body.lower()
    assert "confirm(" not in body
    assert "R-001" not in body
    assert "Hide guide" not in body
    assert "Previous" not in body
    assert "Common mistakes" not in body
    assert "identified risk to continue" not in body.lower()


def test_identify_page_uses_existing_tokens():
    assert ".identify-page" in CSS
    assert ".identify-list" in CSS
    assert ".identify-empty" in CSS
    assert "flow-view--identify" in CSS
    title_css = CSS.split(".identify-title {", 1)[1][:400]
    assert "var(--text)" in title_css
    assert "fonts.googleapis" not in CSS
    assert "Inter" not in CSS.split("Identify risks page", 1)[1][:2500]
