"""The local app and Pages site load no third-party fonts or other asset origins."""

import inspect
import re
import sys
from pathlib import Path

from codify import webapp

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_site  # noqa: E402

INDEX = ROOT / "src" / "codify" / "static" / "index.html"
CSS = ROOT / "src" / "codify" / "static" / "app.css"


def test_index_html_has_no_external_asset_origins():
    html = INDEX.read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html
    assert not re.search(r"""(?:href|src)\s*=\s*['"]https?://""", html), html


def test_local_csp_does_not_allow_font_origins():
    assert "fonts.googleapis.com" not in webapp.CSP
    assert "fonts.gstatic.com" not in webapp.CSP
    assert "style-src 'self'" in webapp.CSP
    assert "https://fonts" not in webapp.CSP


def test_system_font_stack_does_not_name_inter_or_a_cdn():
    css = CSS.read_text(encoding="utf-8")
    match = re.search(r"--font:\s*([^;]+);", css)
    assert match, "expected --font token"
    stack = match.group(1)
    assert "Inter" not in stack
    assert "fonts.googleapis" not in stack
    assert "system-ui" in stack


def test_build_site_does_not_strip_google_fonts():
    src = inspect.getsource(build_site.build_index)
    assert "fonts.googleapis.com" not in src
    assert "Drop the Google Fonts" not in src
