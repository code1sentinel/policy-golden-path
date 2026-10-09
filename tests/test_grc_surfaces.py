"""Statement library GRC surfaces (list + detail). Register UI is gone (ADR 0011)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")


def test_statement_library_keeps_detail_and_picker():
    assert 'id="library-pick-detail"' in INDEX
    assert "renderLibraryDetail" in JS
    assert "LIBRARY_KEY" in JS
    assert 'SAVE_KEY = "codify:project"' in JS
    assert ".library-detail" in CSS
    assert ".picker" in CSS
    assert "rememberStatement" in JS
    assert "fonts.googleapis" not in JS
    assert "fonts.googleapis" not in INDEX
    assert "vanta.com" not in JS.lower()
    assert "vanta.com" not in INDEX.lower()


def test_register_surfaces_are_gone():
    assert 'id="recommend-dialog"' not in INDEX
    assert "data-risk-pane" not in JS
    assert "openRecommendDialog" not in JS
    assert "risks-subnav" not in JS
    assert 'action: "draft_risk_controls"' not in JS
    assert ".subnav" not in CSS
