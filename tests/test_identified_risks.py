"""Identified risks as input (ADR 0012): model, persistence, coverage, matching, OSCAL."""

import json
from pathlib import Path

import pytest

from codify import api, library
from codify.clauses import parse_text
from codify.project import NS, from_oscal, new_project, to_csv, to_oscal, to_report
from codify.risks import (
    clean_risks,
    coverage,
    match_library,
    next_risk_id,
    normalize_project,
    purpose_from_risks,
)

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "goldens" / "identified-risk-lock-screens.json"
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
FIXTURES = Path(__file__).resolve().parent / "fixtures"

HUMAN_ERROR = "Company data is breached due to human error and misunderstanding of company requirements."
TRAINING = "Require security awareness training at least every [N] days to reduce human error."
BACKUP = "Back up all servers nightly."


def _project_with_clause():
    return new_project(parse_text("Users shall lock screens."), source="")


def test_clean_risks_keeps_id_statement_and_optional_note():
    raw = [
        {"id": "R-001", "statement": HUMAN_ERROR, "note": "From the workshop."},
        {"id": "", "statement": "  Screens left unlocked.  "},
    ]
    cleaned = clean_risks(raw)
    assert cleaned == [
        {"id": "R-001", "statement": HUMAN_ERROR, "note": "From the workshop."},
        {"id": "R-002", "statement": "Screens left unlocked.", "note": ""},
    ]
    assert next_risk_id(cleaned) == "R-003"


def test_clean_risks_drops_register_records_and_malformed_lists():
    register = {
        "id": "R-001", "title": "Unauthorised access", "likelihood": 4, "impact": 5, "score": 20,
        "owner": "Alex", "status": "identified",
    }
    assert clean_risks("not-a-list") == []
    assert clean_risks(None) == []
    assert clean_risks([register, {"title": "x"}]) == []
    assert clean_risks([{"id": "R-009", "statement": HUMAN_ERROR, "likelihood": 3}]) == []


def test_old_project_without_identified_risks_loads_empty_list():
    opened = api.call({"action": "open", "text": "Users shall lock screens."})
    project = opened["project"]
    assert project["risks"] == []
    assert project["controls"][0]["risk_ids"] == []
    leftover = {**project, "risks": [
        {"id": "R-001", "title": "Unauthorised access", "likelihood": 4, "impact": 5, "score": 20},
    ]}
    leftover["controls"][0]["source_type"] = "risk"
    leftover["controls"][0]["risk_id"] = "R-001"
    leftover["controls"][0]["risk"] = "Screens left unlocked."
    scored = api.call({"action": "score", "project": leftover})
    assert "scores" in scored
    cleaned = normalize_project(leftover)
    assert cleaned["risks"] == []
    assert cleaned["controls"][0]["risk_ids"] == []
    assert cleaned["controls"][0]["risk"] == "Screens left unlocked."
    assert cleaned["controls"][0]["source_type"] == "clause"


def test_identified_risks_round_trip_through_clean_and_oscal():
    project = _project_with_clause()
    project["uuid"] = "00000000-0000-4000-8000-000000000000"
    project["risks"] = [{"id": "R-001", "statement": "Screens left unlocked.", "note": "Optional note."}]
    project["controls"][0]["risk_ids"] = ["R-001"]
    project["controls"][0]["risk"] = "Screens left unlocked."
    scored = api.call({"action": "score", "project": project})
    assert scored["coverage"]["uncovered_risk_ids"] == []
    assert scored["coverage"]["unlinked_control_ids"] == []
    saved = api.call({"action": "export", "format": "oscal", "project": project})
    back = api.call({"action": "open", "name": saved["name"], "content": saved["content"]})["project"]
    assert back["risks"] == [
        {"id": "R-001", "statement": "Screens left unlocked.", "note": "Optional note."},
    ]
    assert back["controls"][0]["risk_ids"] == ["R-001"]
    assert back["controls"][0]["risk"] == "Screens left unlocked."
    assert back["controls"][0]["source_type"] == "clause"


def test_legacy_register_catalog_still_does_not_restore_a_register():
    raw = json.loads((FIXTURES / "legacy-mixed-clause-risk.json").read_text())
    project = from_oscal(raw)
    assert project["risks"] == []
    assert all(c.get("risk_ids") == [] for c in project["controls"])
    catalog = to_oscal(project)["catalog"]
    resources = catalog.get("back-matter", {}).get("resources", [])
    names = {p["name"] for r in resources for p in r.get("props", [])}
    assert "risk-id" not in names
    assert "identified-risk-id" not in names


def test_coverage_flags_uncovered_risks_and_unlinked_controls():
    project = _project_with_clause()
    project["risks"] = [
        {"id": "R-001", "statement": HUMAN_ERROR, "note": ""},
        {"id": "R-002", "statement": "Screens left unlocked.", "note": ""},
    ]
    flags = coverage(project)
    assert flags["uncovered_risk_ids"] == ["R-001", "R-002"]
    assert flags["unlinked_control_ids"] == [project["controls"][0]["id"]]
    project["controls"][0]["risk_ids"] = ["R-002"]
    flags = coverage(project)
    assert flags["uncovered_risk_ids"] == ["R-001"]
    assert flags["unlinked_control_ids"] == []
    assert purpose_from_risks(project, ["R-002"]) == "Screens left unlocked."


def test_match_library_suggests_overlapping_statements_only():
    _, entries = library.upsert([], TRAINING, now="2026-10-14T00:00:00+00:00")
    _, entries = library.upsert(entries, BACKUP, now="2026-10-14T00:00:01+00:00")
    hits = match_library(entries, HUMAN_ERROR)
    assert [e["id"] for e in hits] == ["S-001"]
    assert match_library(entries, "Screens left unlocked at unattended desks.") == []


def test_oscal_export_traces_identified_risks_without_register_fields():
    project = _project_with_clause()
    project["uuid"] = "00000000-0000-4000-8000-000000000000"
    project["risks"] = [{"id": "R-001", "statement": "Screens left unlocked.", "note": "Optional note."}]
    project["controls"][0]["risk_ids"] = ["R-001"]
    project["controls"][0]["risk"] = "Screens left unlocked."
    catalog = to_oscal(project)["catalog"]
    catalog["metadata"]["last-modified"] = "2026-10-14T00:00:00+00:00"
    catalog["metadata"]["props"] = [p for p in catalog["metadata"].get("props", []) if p.get("name") != "generator"]
    if not catalog["metadata"]["props"]:
        del catalog["metadata"]["props"]
    clause_uuid = "11111111-1111-4111-8111-111111111111"
    for resource in catalog.get("back-matter", {}).get("resources", []):
        props = {p["name"]: p["value"] for p in resource.get("props", [])}
        if "clause-id" in props:
            resource["uuid"] = clause_uuid
    for group in catalog.get("groups", []):
        for control in group.get("controls", []):
            for link in control.get("links", []):
                if link.get("rel") == "derived-from":
                    link["href"] = "#" + clause_uuid
            names = {p["name"] for p in control.get("props", [])}
            assert "risk-id" not in names
            assert control["props"]
    assert GOLDEN.is_file()
    assert catalog == json.loads(GOLDEN.read_text())["catalog"]
    control = catalog["groups"][0]["controls"][0]
    props = {p["name"]: p["value"] for p in control["props"]}
    assert props["treats-risk"] == "R-001"
    assert props["risk-statement"] == "Screens left unlocked."
    assert props["source-type"] == "clause"
    rels = {link["rel"]: link["href"] for link in control["links"]}
    assert rels["derived-from"].startswith("#")
    assert rels["related"] == "#30f6434c-00bc-5c45-af92-f7b974415c6e"
    resource = next(
        r for r in catalog["back-matter"]["resources"]
        if any(p.get("name") == "identified-risk-id" for p in r.get("props", []))
    )
    assert set(resource) <= {"uuid", "title", "description", "props", "document-ids",
                             "citation", "rlinks", "base64", "remarks"}
    assert "risk" not in resource
    assert "status" not in resource
    assert "statement" not in resource
    assert resource["title"] == "Screens left unlocked"
    assert resource["description"] == "Screens left unlocked."
    assert {p["name"]: p["value"] for p in resource["props"]} == {
        "identified-risk-id": "R-001",
        "statement": "Screens left unlocked.",
        "status": "open",
        "note": "Optional note.",
    }
    assert all(p.get("ns") == NS for p in resource["props"])


def test_from_oscal_restores_risks_from_older_title_description_only():
    catalog = {
        "catalog": {
            "uuid": "00000000-0000-4000-8000-000000000000",
            "metadata": {
                "title": "Policy: control statements",
                "last-modified": "2026-10-14T00:00:00+00:00",
                "version": "draft",
                "oscal-version": "1.1.2",
                "props": [{"name": "generator", "value": "Codify test", "ns": NS}],
            },
            "groups": [{
                "id": "s-0", "title": "Policy",
                "controls": [{
                    "id": "c-c1",
                    "title": "Require users to lock screens",
                    "props": [
                        {"name": "label", "value": "c1"},
                        {"name": "legacy-clause", "value": "c1", "ns": NS},
                        {"name": "status", "value": "draft", "ns": NS},
                        {"name": "origin", "value": "rules", "ns": NS},
                        {"name": "source-type", "value": "clause", "ns": NS},
                        {"name": "treats-risk", "value": "R-001", "ns": NS},
                    ],
                    "parts": [{"id": "c-c1_smt", "name": "statement",
                               "prose": "Require users to lock screens."}],
                    "links": [{"href": "#30f6434c-00bc-5c45-af92-f7b974415c6e", "rel": "related"}],
                }],
            }],
            "back-matter": {"resources": [{
                "uuid": "30f6434c-00bc-5c45-af92-f7b974415c6e",
                "title": "Screens left unlocked.",
                "description": "Screens left unlocked.",
                "props": [
                    {"name": "identified-risk-id", "value": "R-001", "ns": NS},
                    {"name": "note", "value": "Optional note.", "ns": NS},
                ],
            }]},
        }
    }
    project = from_oscal(catalog)
    assert project["risks"] == [
        {"id": "R-001", "statement": "Screens left unlocked.", "note": "Optional note."},
    ]
    assert project["controls"][0]["risk_ids"] == ["R-001"]
    assert "status" not in project["risks"][0]


def test_csv_and_report_still_include_the_purpose_field():
    project = _project_with_clause()
    project["risks"] = [{"id": "R-001", "statement": "Screens left unlocked.", "note": ""}]
    project["controls"][0]["risk_ids"] = ["R-001"]
    project["controls"][0]["risk"] = "Screens left unlocked."
    rows = to_csv(project)
    assert "risk it treats" in rows.splitlines()[0]
    assert "Screens left unlocked." in rows
    report = to_report(project)
    assert "Require users to lock screens" in report


def test_shell_has_risks_input_not_a_register():
    assert 'data-nav="risks"' not in INDEX
    assert 'id="risks"' in INDEX
    assert 'id="risks"' in INDEX
    assert 'id="risk-suggest-dialog"' in INDEX
    assert "Risk register" not in INDEX
    assert 'data-export="risks"' not in INDEX
    assert "likelihood" not in INDEX.lower()
    assert "heatmap" not in JS.lower()
    assert "openRecommendDialog" not in JS
    assert 'action: "draft_risk_controls"' not in JS
    assert "match_library" in JS or "matchLibrary" in JS
    assert "the risk it treats" in JS
    assert "Guidance, risk, who" in JS
    glossary = JS.split("const GLOSSARY = {", 1)[1].split("};", 1)[0]
    assert "Identified risks" in glossary or "identified risks" in glossary.lower()
    assert ".risks-input" in CSS or ".risks-view" in CSS
    assert ".mapped-risk" in CSS
    assert ".risk-suggest" in CSS


def test_register_actions_stay_gone():
    with pytest.raises(api.BadRequest, match="'action' must be one of"):
        api.call({"action": "import_risks", "name": "x.csv", "content": "title,likelihood,impact\nA,1,1\n"})
    with pytest.raises(api.BadRequest, match="'action' must be one of"):
        api.call({"action": "draft_risk_controls", "risk": {"title": "x"}})
    opened = api.call({"action": "open", "text": "Users shall lock screens."})
    with pytest.raises(api.BadRequest, match="'format' must be"):
        api.call({"action": "export", "format": "risks", "project": opened["project"]})
