"""Workspace and Guide chrome is quieter; the statement stays the hero."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")


def test_open_project_hides_start_only_chrome():
    assert "body:has(#start[hidden]) .brand__tag" in CSS
    assert "body:has(#start[hidden]) .local-note" in CSS


def test_editor_hero_is_the_statement_not_risk_or_score_meta():
    extras = JS.index("Guidance, risk")
    assert "Risk it treats" in JS[extras:]
    assert "Risk it treats" not in JS[:extras]
    assert "practices adopted" not in JS
    editor = JS.split("function renderControlEditor")[1].split("function renderProps")[0]
    assert '"aria-label": "Control statement"' in editor
    assert 'text: "Control statement"' not in editor


def test_guide_is_single_column_without_lecture_chrome():
    assert "minmax(320px, 1fr)" not in CSS
    assert ".guide-view" in CSS and "max-width" in CSS
    assert "anatomy__key" not in INDEX
    assert "Okta, Veritas, Symantec" not in INDEX
    assert "guide-foot" not in INDEX
    assert 'text: "How: "' not in JS
    assert "Weak" in JS and "Strong" in JS
