"""OSCAL tracing for risk-derived controls (ADR 0008) and frozen goldens."""

import json
from pathlib import Path

from codify.clauses import parse_text
from codify.project import NS, from_oscal, merge_risks, new_project, to_oscal
from codify.risks import draft_from_templates, normalize_risk, parse_csv

ROOT = Path(__file__).resolve().parent.parent
GOLDENS = Path(__file__).resolve().parent / "goldens"
EXAMPLE = ROOT / "examples" / "acme-risk-register.csv"
RISK_ONLY = GOLDENS / "risk-only.json"
MIXED = GOLDENS / "mixed-clause-risk.json"

FROZEN_CATALOG = "00000000-0000-4000-8000-000000000000"
FROZEN_CLAUSE = "11111111-1111-4111-8111-111111111111"
FROZEN_RISK = "22222222-2222-4222-8222-222222222222"
FROZEN_WHEN = "2026-10-06T00:00:00+00:00"


def _access_risk():
    return normalize_risk({
        "id": "R-001",
        "title": "Unauthorised access to agency systems",
        "description": "A compromised account could reach systems beyond need-to-know.",
        "asset": "Agency systems",
        "likelihood": 4,
        "impact": 5,
        "threat": "Stolen credentials",
        "vulnerability": "Excessive access rights",
        "owner": "Jane Smith",
        "status": "identified",
    })


def _freeze(catalog: dict) -> dict:
    catalog = json.loads(json.dumps(catalog))
    cat = catalog["catalog"]
    cat["uuid"] = FROZEN_CATALOG
    cat["metadata"]["last-modified"] = FROZEN_WHEN
    cat["metadata"]["props"] = [p for p in cat["metadata"].get("props", []) if p.get("name") != "generator"]
    for resource in cat.get("back-matter", {}).get("resources", []):
        names = {p["name"] for p in resource.get("props", [])}
        if "risk-id" in names:
            resource["uuid"] = FROZEN_RISK
        elif "clause-id" in names:
            resource["uuid"] = FROZEN_CLAUSE
    for group in cat.get("groups", []):
        for control in group.get("controls", []):
            for link in control.get("links", []):
                if link.get("rel") == "derived-from":
                    link["href"] = "#" + FROZEN_CLAUSE
                elif link.get("rel") == "reference":
                    link["href"] = "#" + FROZEN_RISK
    return catalog


def test_risk_control_is_traced_in_oscal():
    project = {"uuid": FROZEN_CATALOG, "title": "", "source": "", "version": "test",
               "clauses": [], "controls": draft_from_templates(_access_risk(), ["restrict-access"]),
               "risks": [_access_risk()]}
    cat = to_oscal(project)["catalog"]
    control = cat["groups"][0]["controls"][0]
    props = {p["name"]: p["value"] for p in control["props"] if p.get("ns") == NS}
    assert props["source-type"] == "risk" and props["risk-id"] == "R-001"
    assert any(link.get("rel") == "reference" for link in control["links"])
    resource = next(r for r in cat["back-matter"]["resources"] if any(p["name"] == "risk-id" for p in r["props"]))
    assert resource["title"].startswith("Unauthorised")
    assert {p["name"] for p in resource["props"]} >= {"risk-id", "likelihood", "impact", "score"}
    back = from_oscal(to_oscal(project))
    assert back["risks"][0]["id"] == "R-001"
    assert back["controls"][0]["source_type"] == "risk" and back["controls"][0]["risk_id"] == "R-001"
    assert back["clauses"] == []


def test_risk_only_catalog_golden():
    project = {"uuid": FROZEN_CATALOG, "title": "", "source": "", "version": "test",
               "clauses": [], "controls": draft_from_templates(_access_risk(), ["restrict-access"]),
               "risks": [_access_risk()]}
    frozen = _freeze(to_oscal(project))
    assert RISK_ONLY.is_file()
    assert frozen == json.loads(RISK_ONLY.read_text())


def test_mixed_clause_and_risk_catalog_golden():
    project = new_project(parse_text("Users shall lock screens."), source="")
    project["uuid"] = FROZEN_CATALOG
    project = merge_risks(project, [_access_risk()], draft=False)
    project["controls"] = list(project["controls"]) + draft_from_templates(_access_risk(), ["restrict-access"])
    frozen = _freeze(to_oscal(project))
    assert MIXED.is_file()
    assert frozen == json.loads(MIXED.read_text())


def test_example_register_drafts_into_a_mixed_catalog():
    risks = parse_csv(EXAMPLE.read_text())["risks"]
    project = new_project(parse_text("Users shall lock screens."), source="")
    project = merge_risks(project, risks, draft=True)
    cat = to_oscal(project)["catalog"]
    assert any(g["id"] == "s-risks" for g in cat["groups"])
    risk_controls = [c for g in cat["groups"] if g["id"] == "s-risks" for c in g["controls"]]
    assert risk_controls
    assert all(any(p["name"] == "source-type" and p["value"] == "risk" for p in c["props"]) for c in risk_controls)
    clause_controls = [c for g in cat["groups"] if g["id"] != "s-risks" for c in g["controls"]]
    assert all(any(p["name"] == "source-type" and p["value"] == "clause" for p in c["props"]) for c in clause_controls)
