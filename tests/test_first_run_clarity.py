"""Static checks for first-run clarity: example text, export copy, glossary."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")


def test_paste_box_has_real_editable_example_text():
    assert 'id="result"' in INDEX
    assert 'id="result-continue"' in INDEX
    assert "Here's what we drafted" in INDEX or "Here’s what we drafted" in INDEX
    assert "Example clause" not in INDEX
    assert 'name="text"' not in INDEX
    clause = JS.split("function renderClauseStep", 1)[1].split("function renderIdentifyStep", 1)[0]
    assert "A good clause" in clause
    assert "Access to systems shall be granted on a need-to-know basis." in clause
    assert "blank line" in clause


def test_export_marks_oscal_recommended_with_use_when_lines():
    assert "(recommended)" in INDEX
    assert "data-export=\"oscal\"" in INDEX
    assert "export-list__row is-recommended" in INDEX or "export-list__row--recommended" in INDEX
    assert "Use this when" in INDEX or "use this when" in INDEX.lower()
    assert "formula-escaped" not in INDEX


def test_glossary_terms_and_result_step_are_wired():
    assert 'class="term"' in INDEX
    assert ".term" in CSS
    assert "GLOSSARY" in JS
    assert "state.resultStep" in JS
    assert '"control draft"' in JS and "from ${plural" in JS
    head = JS.split("function renderHead")[1].split("function scorePill")[0]
    assert "put(summary" in head
    assert "summary.replaceChildren" not in head


def test_purpose_hint_is_not_a_fixed_password_example():
    from codify.control import assess_control_statement
    from codify.models import Statement

    access = assess_control_statement(Statement(
        "x", "Grant access to Agency systems on a need-to-know basis."))
    joined = " ".join(access.improvements)
    assert "brute-force" not in joined
    assert "remove access that is no longer needed" in joined or "risk this control treats" in joined
