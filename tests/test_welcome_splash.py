"""Splash #28 is folded into the landing. See tests/test_landing.py."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
THEME = (ROOT / "src/codify/static/theme.js").read_text(encoding="utf-8")


def test_splash_is_gone_and_landing_is_the_first_screen():
    assert 'id="splash"' not in INDEX
    assert "codify:splash-seen" not in JS
    assert "codify:splash-seen" not in THEME
    assert 'id="start"' in INDEX
    assert 'id="start-from-risks"' in INDEX
    assert "Get started" in INDEX
