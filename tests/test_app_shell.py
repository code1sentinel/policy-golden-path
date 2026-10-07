"""Authoring app shell: sidebar, catalog, export dialog, properties panel."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")


def test_shell_has_sidebar_nav_and_properties_panel():
    for nav in ("workspace", "clauses", "risks", "catalog", "library", "export", "guide"):
        assert f'data-nav="{nav}"' in INDEX
    assert 'id="sidebar"' in INDEX
    assert 'id="props"' in INDEX
    assert 'id="catalog"' in INDEX
    assert 'id="risks"' in INDEX
    assert 'id="library"' in INDEX
    assert 'id="export-dialog"' in INDEX
    assert "checklist__list" in INDEX
    assert ".sidebar" in CSS and ".props-card" in CSS
    assert "sidebar-collapsed" in CSS
    assert "openExportDialog" in JS
    assert "renderCatalog" in JS
    assert "renderProps" in JS
    assert "renderRiskDrawer" in JS
    assert "suggest_risk_controls" in JS
    assert "renderLibrary" in JS
    assert "LIBRARY_KEY" in JS
    assert "codify:statements" in JS


def test_accept_shortcut_is_ctrl_or_meta_enter():
    assert 'e.key === "Enter"' in JS
    assert "e.metaKey || e.ctrlKey" in JS
    assert 'setStatus([c.id], "accepted")' in JS


def test_export_dialog_has_one_download_per_format():
    assert INDEX.count('data-export="oscal"') == 1
    assert INDEX.count('data-export="xlsx"') == 1
    assert INDEX.count('data-export="csv"') == 1
    assert INDEX.count('data-export="report"') == 1
    assert INDEX.count('data-export="risks"') == 1
    assert INDEX.count('data-export="library-json"') == 1
    assert INDEX.count('data-export="library-csv"') == 1
    assert "Download" in INDEX.split('id="export-dialog"', 1)[1]
