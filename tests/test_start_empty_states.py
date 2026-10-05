"""Start screen has one primary action; empty panes offer a next step."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")


def test_start_hero_is_the_clause_textarea_with_one_primary():
    assert 'id="demo"' in INDEX
    assert "Try an example" in INDEX
    assert "Try the Acme demo" not in INDEX
    assert 'class="start__cta"' not in INDEX
    assert "Or load your policy" not in INDEX
    assert 'id="paste-submit"' in INDEX and "Codify" in INDEX
    submit = INDEX.split('id="paste-submit"', 1)[0][-120:]
    assert "btn--primary" in submit
    demo_chunk = INDEX.split('id="demo"', 1)[0][-160:]
    assert "btn--primary" not in demo_chunk
    assert "example-chip" in demo_chunk
    assert "Open a file" in INDEX
    assert 'name="title"' not in INDEX


def test_start_chrome_has_no_club_or_version_line():
    """The start page is personal: no club attribution, MIT line, or version footer."""
    assert "GRC Engineering Club Singapore" not in INDEX
    assert "open source (MIT)" not in INDEX
    assert 'id="version"' not in INDEX
    assert "<footer" not in INDEX
    assert "$(\"#version\")" not in JS
    assert "Version ${c.version}" not in JS
    assert ".foot {" not in CSS


def test_empty_states_have_icon_line_and_action():
    assert "Open first draft" in JS
    assert "Show all" in JS
    assert "Select a clause to draft its control." in JS
    assert "Nothing matches this filter." in JS
    assert "empty__icon" in CSS or "empty__glyph" in CSS
    assert ".empty" in CSS
