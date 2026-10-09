"""Static checks for the second first-time GRC walkthrough polish."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")


def test_accept_shows_accepted_state_and_undo():
    assert "Accepted ✓" in JS
    assert "Undo accept" in JS
    assert 'id="undo-accept"' in JS or "undo-accept" in JS
    assert "next-control" in JS
    editor = JS.split("function renderControlEditor")[1].split("function showResult")[0]
    assert "btn--primary" in editor
    assert "Next control" in editor


def test_flow_strip_is_status_not_a_control():
    assert 'aria-label="Review stages (status, not links)"' in INDEX or "not links" in INDEX
    assert "flow__caption" in INDEX or "flow__caption" in JS
    assert "pointer-events" in CSS.split(".flow", 1)[1].split(".menu", 1)[0] or "cursor: default" in CSS.split(".flow", 1)[1][:800]
    assert "flow--status" in CSS or "flow li + li::before" in CSS


def test_review_shows_parts_and_purpose_once():
    show = JS.split("function showResult")[1].split("function renderProps")[0]
    assert "partsList(" not in show
    assert "improvementsList(" not in show
    assert "scoreLine(" in show
    assert "partsSubitems(" in JS


def test_accepted_gaps_are_optional_improvements():
    assert "Optional" in JS
    assert "optional improvement" in JS.lower() or "optional improvements" in JS.lower()
    assert "is-optional" in JS or "is-optional" in CSS


def test_unfilled_placeholders_are_set_this_value_prompts():
    assert "Set this value" in JS
    assert "paramPrompts" in JS
    assert "param-token" in CSS
    assert "[N]" in JS


def test_count_breakdown_is_not_hover_only_and_first_look_has_more():
    assert "work-counts" in JS or "work__counts" in JS
    assert "and ${" in JS or "and " in JS.split("function renderResult")[1].split("function continueFromResult")[0]
    assert "more" in JS.split("function renderResult")[1].split("function continueFromResult")[0]
    head = JS.split("function renderHead")[1].split("function scorePill")[0]
    assert "summary.title" not in head or "work-counts" in head or "work__counts" in head


def test_oscal_and_catalog_library_have_visible_lines():
    assert "oscal-view__help" in JS or "NIST" in JS.split("function oscalPanel")[1][:800]
    assert "The catalog is this project's" in INDEX or "catalog is this project" in INDEX.lower()
    assert "library is" in INDEX.lower()
    export = INDEX.split('id="export-dialog"', 1)[1].split("</dialog>", 1)[0]
    assert "save file" not in export.lower()


def test_export_groups_library_downloads_and_drops_save_file():
    export = INDEX.split('id="export-dialog"', 1)[1].split("</dialog>", 1)[0]
    assert "save file" not in export.lower()
    assert "export-more" in export or "Statement library (optional)" in export
    assert export.lower().count("statement library") >= 1
    assert 'data-export="oscal"' in export
    assert 'data-export="library-json"' in export
    assert 'data-export="library-csv"' in export


def test_workspace_nav_stays_on_start_and_title_is_editable():
    show = JS.split("function showView")[1].split("function renderCrumb")[0]
    assert 'view === "workspace" && state.project' not in show or "renderCurrentProject" in show
    assert "renderCurrentProject" in JS
    assert 'data-nav="workspace"' in INDEX
    assert "work-title-input" in CSS or 'id="work-title"' in INDEX
    assert "Untitled policy" in JS


def test_library_shows_the_statement_once():
    detail = JS.split("function renderLibraryDetail")[1].split("function renderLibrary()")[0]
    assert "library-detail__title" not in detail or "lead !==" in detail or "same" in detail.lower()
    render = JS.split("function renderLibrary()")[1].split("async function removeLibraryEntry")[0]
    assert "library-layout--single" in render or "filtered.length === 1" in render


def test_keeps_risk_purpose_wording_and_no_register():
    assert "the risk it treats" in JS
    assert "Guidance, risk, who" in JS
    assert 'data-nav="risks"' not in INDEX
    assert "Risk register" not in INDEX
    from codify.guides import GUIDE
    joined = str(GUIDE)
    assert "risk it treats" in joined
