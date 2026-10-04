"""This control's OSCAL is visible and copyable; export is one split action."""

import json
from pathlib import Path

from codify import api
from codify.clauses import parse_text
from codify.project import control_oscal, new_project

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "goldens" / "unnumbered-lock-screens-control.json"
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")


def test_control_oscal_matches_the_catalog_control_and_golden():
    project = new_project(parse_text("Users shall lock screens."), source="")
    project["uuid"] = "00000000-0000-4000-8000-000000000000"
    control = control_oscal(project, project["controls"][0]["id"])
    assert control["id"] == "c-c1"
    assert control["parts"][0]["name"] == "statement"
    frozen = json.loads(json.dumps(control))
    for link in frozen.get("links", []):
        if link.get("rel") == "derived-from":
            link["href"] = "#11111111-1111-4111-8111-111111111111"
    assert GOLDEN.is_file()
    assert frozen == json.loads(GOLDEN.read_text())


def test_control_oscal_api_returns_this_control():
    opened = api.call({"action": "open", "text": "Users shall lock screens."})
    out = api.call({
        "action": "control_oscal",
        "project": opened["project"],
        "control_id": opened["project"]["controls"][0]["id"],
    })
    assert out["control"]["id"] == "c-c1"
    assert "Require users to lock screens" in json.dumps(out["control"])


def test_editor_has_statement_and_oscal_tabs():
    assert "Statement" in JS and "OSCAL JSON" in JS
    assert "oscal-pre" in CSS and "oscal-ln" in CSS
    assert "Copied" in JS
    assert "aria-live" in JS
    assert "navigator.clipboard" in JS


def test_export_is_a_split_button_without_a_duplicate_oscal_item():
    assert "Save OSCAL (.json)" in INDEX
    assert "Save OSCAL catalog" not in INDEX
    menu = INDEX.split('id="export-menu"', 1)[1]
    assert 'data-export="xlsx"' in menu
    assert 'data-export="csv"' in menu
    assert 'data-export="report"' in menu
    assert menu.count('data-export="oscal"') == 0
    assert "split__chevron" in INDEX or 'id="export-more"' in INDEX
    assert INDEX.count('data-export="oscal"') == 1
