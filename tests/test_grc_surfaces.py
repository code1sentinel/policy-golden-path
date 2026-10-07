"""Vanta-style GRC surfaces: Library vs Register, recommend modal, statement detail."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")


def test_risks_have_library_register_subnav_and_recommend_dialog():
    assert 'id="recommend-dialog"' in INDEX
    assert 'id="recommend-add"' in INDEX
    assert 'id="recommend-dismiss"' in INDEX
    assert 'id="recommend-list"' in INDEX
    assert 'id="library-pick-detail"' in INDEX
    assert "data-risk-pane" in JS
    assert "openRecommendDialog" in JS
    assert "fillRecommendList" in JS
    assert "removeRisk" in JS
    assert "renderLibraryDetail" in JS
    assert "risks-subnav" in JS
    assert ".subnav" in CSS
    assert ".pill" in CSS
    assert ".recommend-dialog" in CSS
    assert ".library-detail" in CSS
    assert ".picker" in CSS


def test_grc_surfaces_reuse_existing_stores_and_accept_path():
    assert 'LIBRARY_KEY = "codify:statements"' in JS
    assert 'SAVE_KEY = "codify:project"' in JS
    assert 'action: "draft_risk_controls"' in JS
    assert "rememberStatement" in JS
    assert "fonts.googleapis" not in JS
    assert "fonts.googleapis" not in INDEX
    assert "vanta.com" not in JS.lower()
    assert "vanta.com" not in INDEX.lower()
