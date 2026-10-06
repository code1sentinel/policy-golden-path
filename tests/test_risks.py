"""Risk register: parse, score, templates, and OSCAL tracing."""

import json
from pathlib import Path

import pytest

from codify.control import assess_control_statement
from codify.models import Statement
from codify.risks import (
    draft_from_templates, fill_template, normalize_risk, parse_csv, parse_json,
    parse_register, score, suggest_templates, to_csv_register,
)

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "acme-risk-register.csv"


def test_score_is_likelihood_times_impact():
    assert score(1, 1) == 1 and score(5, 5) == 25 and score(4, 5) == 20


def test_normalize_assigns_id_and_defaults():
    r = normalize_risk({"title": "Stolen laptop", "likelihood": "3", "impact": 4}, index=0)
    assert r["id"] == "R-001" and r["score"] == 12 and r["status"] == "identified"


def test_parse_csv_example_register():
    out = parse_csv(EXAMPLE.read_text())
    assert [r["id"] for r in out["risks"]] == ["R-001", "R-002", "R-003", "R-004", "R-005"]
    assert out["risks"][0]["score"] == 20
    assert out["errors"] == []
    assert {c["field"] for c in out["recognised"]} >= {"title", "likelihood", "impact"}


def test_parse_csv_rejects_missing_required_columns():
    with pytest.raises(ValueError, match="title, likelihood and impact"):
        parse_csv("foo,bar\n1,2\n")


def test_parse_csv_reports_malformed_rows():
    text = "id,title,likelihood,impact\nR-001,Ok,4,5\nR-002,Bad,nine,2\nR-003,Also,3,9\n"
    out = parse_csv(text)
    assert [r["id"] for r in out["risks"]] == ["R-001"]
    assert len(out["errors"]) == 2
    assert "1 to 5" in out["errors"][0]["error"]


def test_parse_csv_empty_and_blank_rows():
    with pytest.raises(ValueError, match="empty"):
        parse_csv("   ")
    out = parse_csv("title,likelihood,impact\nKeep,2,2\n,,\n")
    assert len(out["risks"]) == 1


def test_parse_json_list_and_wrapper():
    raw = [{"title": "Phish", "likelihood": 2, "impact": 3, "asset": "Email"}]
    a = parse_json(json.dumps(raw))
    b = parse_json(json.dumps({"risks": raw}))
    assert a["risks"][0]["title"] == "Phish" and a["risks"][0]["score"] == 6
    assert b["risks"][0]["id"] == a["risks"][0]["id"]
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_json("{")
    with pytest.raises(ValueError, match="list"):
        parse_json('{"nope": 1}')


def test_templates_match_keywords_and_pass_statement_checks():
    risk = normalize_risk({
        "id": "R-001", "title": "Unauthorised access", "description": "Stolen credentials",
        "asset": "agency systems", "likelihood": 4, "impact": 5,
        "threat": "Stolen credentials", "vulnerability": "Excessive access rights",
    })
    suggestions = suggest_templates(risk)
    assert suggestions
    assert any(s["id"] == "restrict-access" for s in suggestions)
    for s in suggestions:
        a = assess_control_statement(Statement("x", s["statement"], risk_statement=risk["title"]))
        assert a.confidence >= 0.7, (s["id"], s["statement"], a.improvements)


def test_every_built_in_template_passes_the_checker():
    risk = normalize_risk({"title": "Generic risk", "asset": "production systems", "likelihood": 3, "impact": 3})
    from codify.risks import TEMPLATES
    for tmpl in TEMPLATES:
        text = fill_template(tmpl, risk)
        a = assess_control_statement(Statement("x", text, risk_statement=risk["title"]))
        assert a.confidence >= 0.7, (tmpl["id"], text, a.improvements)


def test_draft_from_templates_marks_source_type_risk():
    risk = normalize_risk({"id": "R-002", "title": "Malware on desktops", "asset": "agency desktops",
                           "likelihood": 3, "impact": 4, "threat": "Malware"})
    controls = draft_from_templates(risk)
    assert controls
    assert all(c["source_type"] == "risk" and c["risk_id"] == "R-002" and c["clause"] == "" for c in controls)
    assert all(c["origin"] == "rules" and c["status"] == "draft" for c in controls)


def test_csv_round_trip_keeps_fields():
    out = parse_csv(EXAMPLE.read_text())
    again = parse_csv(to_csv_register(out["risks"]))
    assert [r["title"] for r in again["risks"]] == [r["title"] for r in out["risks"]]


def test_parse_csv_with_column_mapping_overlay():
    text = "scenario,L,I\nStolen laptop,3,4\n"
    out = parse_csv(text, mapping={"scenario": "title", "L": "likelihood", "I": "impact"})
    assert out["risks"][0]["title"] == "Stolen laptop" and out["risks"][0]["score"] == 12


def test_parse_register_picks_json_by_name():
    data = parse_register("risks.json", json.dumps([{"title": "X", "likelihood": 1, "impact": 1}]))
    assert data["risks"][0]["id"] == "R-001"
