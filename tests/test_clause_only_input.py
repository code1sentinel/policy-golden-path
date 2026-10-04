"""Happy path: the only input is clause text (Andre / ADR 0006)."""

import json
import re
from pathlib import Path

import pytest

from codify import api
from codify.clauses import parse_text, read_policy
from codify.draft import draft
from codify.project import new_project, to_oscal

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "goldens" / "unnumbered-lock-screens.json"
OSCAL_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")


def test_unnumbered_sentence_is_a_clause_not_a_title():
    policy = parse_text("Users shall lock screens when they leave their desk.")
    assert [(c.id, c.text) for c in policy.clauses] == [
        ("c1", "Users shall lock screens when they leave their desk."),
    ]
    assert policy.title == ""


def test_text_file_without_numbers_opens():
    policy = read_policy("note.txt", "Users shall lock screens when they leave their desk.")
    assert len(policy.clauses) == 1
    assert policy.clauses[0].text == "Users shall lock screens when they leave their desk."


def test_leading_number_stays_in_a_single_pasted_paragraph():
    policy = parse_text("4.2.1 Users shall lock screens when they leave their desk.")
    assert policy.clauses[0].text == "4.2.1 Users shall lock screens when they leave their desk."


def test_draft_does_not_echo_a_leading_clause_number():
    texts = [d.text for d in draft("4.2.1 Users shall lock screens.")]
    assert texts == ["Require users to lock screens."]


def test_open_ignores_a_title_field_and_uses_the_clause():
    out = api.call({"action": "open", "text": "Users shall lock screens.", "title": "Screens"})
    assert out["project"]["title"] != "Screens"
    assert out["project"]["clauses"][0]["text"] == "Users shall lock screens."
    assert out["summary"]["controls"] == 1


def test_empty_input_does_not_ask_for_clause_numbers():
    with pytest.raises(ValueError, match="no clauses found") as exc:
        read_policy("p.txt", "   \n\n")
    assert "4.1" not in str(exc.value) and "number them" not in str(exc.value)


def test_paste_form_has_no_title_field():
    html = (ROOT / "src" / "codify" / "static" / "index.html").read_text()
    assert 'name="title"' not in html
    assert re.search(r">Title\s*<em>optional</em>", html) is None
    js = (ROOT / "src" / "codify" / "static" / "app.js").read_text()
    assert "namedItem(\"title\")" not in js


def test_workspace_does_not_display_clause_numbers():
    js = (ROOT / "src" / "codify" / "static" / "app.js").read_text()
    assert 'class: "clause__id"' not in js
    assert 'class: "ctl__id"' not in js
    assert "Legacy clause ${clause.id}" not in js
    assert "Clause ${clause.id}" not in js
    assert "`Clause ${clause.id}`" not in js


def _freeze(catalog: dict) -> dict:
    catalog = json.loads(json.dumps(catalog))
    catalog["catalog"]["uuid"] = "00000000-0000-4000-8000-000000000000"
    catalog["catalog"]["metadata"]["last-modified"] = "2026-10-04T00:00:00+00:00"
    catalog["catalog"]["metadata"]["props"] = [
        p for p in catalog["catalog"]["metadata"].get("props", []) if p.get("name") != "generator"
    ]
    for resource in catalog["catalog"].get("back-matter", {}).get("resources", []):
        resource["uuid"] = "11111111-1111-4111-8111-111111111111"
    return catalog


def test_unnumbered_clause_writes_stable_oscal_ids():
    project = new_project(parse_text("Users shall lock screens."), source="")
    project["uuid"] = "00000000-0000-4000-8000-000000000000"
    catalog = to_oscal(project)
    control = catalog["catalog"]["groups"][0]["controls"][0]
    assert OSCAL_TOKEN.match(control["id"])
    assert control["title"]
    assert GOLDEN.is_file()
    assert _freeze(catalog) == json.loads(GOLDEN.read_text())
