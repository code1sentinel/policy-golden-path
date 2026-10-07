"""First-visit welcome splash: markup, persist key, skip when seen or resume."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
THEME = (ROOT / "src/codify/static/theme.js").read_text(encoding="utf-8")


def test_splash_markup_is_centered_welcome_with_one_primary():
    assert 'id="splash"' in INDEX
    assert 'id="splash-title"' in INDEX
    assert "Welcome to Codify" in INDEX
    assert "Get started" in INDEX
    assert 'id="splash-continue"' in INDEX
    continue_chunk = INDEX.split('id="splash-continue"', 1)[0][-160:]
    assert "btn--primary" in continue_chunk
    splash = INDEX.split('id="splash"', 1)[1].split('id="start"', 1)[0]
    assert "brand__mark" in splash
    assert "OSCAL" in splash
    assert "this device" in splash.lower()
    assert "Linear" not in splash
    assert 'class="splash__dots"' not in INDEX
    assert 'href="#main"' in INDEX


def test_splash_uses_existing_tokens_and_system_fonts():
    assert ".splash" in CSS
    splash_css = CSS.split(".splash {", 1)[1]
    assert "var(--text)" in splash_css
    assert "var(--muted)" in splash_css
    assert "var(--orange)" in splash_css
    assert "fonts.googleapis" not in splash_css
    assert "Inter" not in splash_css


def test_splash_persist_key_and_skip_rules_live_in_the_page():
    assert 'codify:splash-seen' in JS
    assert "SPLASH_KEY" in JS
    assert "shouldShowSplash" in JS
    assert "dismissSplash" in JS
    assert "splashSeen" in JS
    seen_fn = JS.split("function splashSeen", 1)[1].split("function ", 1)[0]
    assert "SPLASH_KEY" in seen_fn or "codify:splash-seen" in seen_fn
    should = JS.split("function shouldShowSplash", 1)[1].split("function ", 1)[0]
    assert "splashSeen" in should
    assert "loadLocal" in should
    dismiss = JS.split("function dismissSplash", 1)[1].split("function ", 1)[0]
    assert "SPLASH_KEY" in dismiss or "codify:splash-seen" in dismiss
    assert "setItem" in dismiss


def test_first_paint_skips_splash_when_resume_or_seen():
    assert "codify:splash-seen" in THEME
    assert "codify:project" in THEME
    assert 'data-splash' in THEME
    assert 'html[data-splash="open"]' in CSS
    assert "#start" in CSS.split('html[data-splash="open"]', 1)[1][:400]
