"""Primary nav is Home, Risk Entry, Policy Clause; other surfaces stay off the tabs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")


def test_nav_has_exactly_three_destinations():
    for nav in ("home", "risk-entry", "policy-clause"):
        assert f'data-nav="{nav}"' in INDEX
    assert "Home" in INDEX
    assert "Risk Entry" in INDEX
    assert "Policy Clause" in INDEX
    for gone in ("workspace", "clauses", "catalog", "library", "export", "guide", "risks"):
        assert f'data-nav="{gone}"' not in INDEX
    nav = INDEX.split('class="sidebar__nav"', 1)[1].split("</nav>", 1)[0]
    assert nav.count('class="nav-btn"') == 3
    assert nav.count("data-nav=") == 3
    assert 'aria-label="Primary"' in INDEX


def test_removed_tabs_keep_in_flow_surfaces():
    assert 'id="catalog"' in INDEX
    assert 'id="library"' in INDEX
    assert 'id="library-pick"' in INDEX
    assert 'id="risks"' in INDEX
    assert 'id="export-dialog"' in INDEX
    assert 'id="export-open-top"' in INDEX
    assert 'id="guide"' in INDEX
    assert "Insert from library" in JS
    assert "openExportDialog" in JS
    assert "renderCatalog" in JS
    assert "renderLibrary" in JS
    assert "GRC Engineering Club" not in INDEX


def test_nav_highlights_the_open_flow_and_fits_a_phone():
    assert "function navFor" in JS
    assert "risk-entry" in JS.split("function navFor", 1)[1].split("function showView", 1)[0]
    assert "policy-clause" in JS.split("function navFor", 1)[1].split("function showView", 1)[0]
    assert 'aria-current' in JS.split("function markNav", 1)[1].split("function showView", 1)[0]
    assert "openRiskEntry" in JS
    assert "openPolicyClause" in JS
    assert "flex-wrap: nowrap" in CSS
    assert "@media (max-width: 390px)" in CSS or "max-width: 980px" in CSS
