"""Generated starters attach to the OSCAL catalog as back-matter files."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from codify import api
from codify.clauses import parse_text
from codify.policy_as_code import POLICY_REL, generate_policy
from codify.project import NS, from_oscal, new_project, to_oscal

GOLDEN = Path(__file__).resolve().parent / "goldens" / "policy-as-code-s3-public.json"
STATEMENT = "Block public access on all object-storage buckets."


def _project_with_starter():
    project = new_project(parse_text("S3 buckets shall not be public."), source="")
    project["uuid"] = "00000000-0000-4000-8000-000000000000"
    project["risks"] = [{"id": "R-001", "statement": "Public buckets expose customer data.", "note": ""}]
    control = project["controls"][0]
    control["text"] = STATEMENT
    control["risk_ids"] = ["R-001"]
    control["risk"] = "Public buckets expose customer data."
    starter = generate_policy(
        STATEMENT, "rego",
        control_id=control["id"],
        oscal_id="c-c1",
        risk=control["risk"],
        clause=project["clauses"][0]["text"],
    )
    control["policy_as_code"] = {
        "format": starter["format"],
        "pattern": starter["pattern"],
        "code": starter["code"],
        "filename": starter["filename"],
    }
    return project


def test_oscal_export_attaches_starter_as_back_matter_file():
    project = _project_with_starter()
    catalog = to_oscal(project)["catalog"]
    catalog["metadata"]["last-modified"] = "2026-10-23T00:00:00+00:00"
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
    assert GOLDEN.is_file()
    assert catalog == json.loads(GOLDEN.read_text())["catalog"]
    control = catalog["groups"][0]["controls"][0]
    pac = next(link for link in control["links"] if link["rel"] == POLICY_REL)
    assert pac["media-type"] == "text/x-rego"
    resource = next(
        r for r in catalog["back-matter"]["resources"]
        if any(p.get("name") == "policy-as-code-control" for p in r.get("props", []))
    )
    assert resource["base64"]["filename"].endswith(".rego")
    assert resource["description"].startswith("Starter policy-as-code")
    assert all(p.get("ns") == NS for p in resource["props"])
    assert "risk" not in resource
    assert set(resource) <= {"uuid", "title", "description", "props", "document-ids",
                             "citation", "rlinks", "base64", "remarks"}


def test_catalog_round_trip_restores_starter():
    project = _project_with_starter()
    back = from_oscal(json.loads(json.dumps(to_oscal(project))))
    assert back["controls"][0]["policy_as_code"]["pattern"] == "storage_public"
    assert "import rego.v1" in back["controls"][0]["policy_as_code"]["code"]


def test_generate_policy_api_is_local_and_deterministic():
    a = api.call({"action": "generate_policy", "text": STATEMENT, "control_id": "c1",
                  "risk": "Public buckets expose customer data."})
    b = api.call({"action": "generate_policy", "text": STATEMENT, "control_id": "c1",
                  "risk": "Public buckets expose customer data."})
    assert a == b
    assert a["pattern"] == "storage_public"
    assert a["starter"] is True
    export = api.call({"action": "export", "format": "oscal", "project": _project_with_starter()})
    catalog = json.loads(export["content"])["catalog"]
    resource = next(r for r in catalog["back-matter"]["resources"] if r.get("base64"))
    code = base64.b64decode(resource["base64"]["value"]).decode("utf-8")
    assert "policy-as-code" in export["content"]
    assert "import rego.v1" in code


def test_generate_policy_rejects_empty_and_unknown_format():
    with pytest.raises(api.BadRequest, match="enter a control statement"):
        api.call({"action": "generate_policy", "text": ""})
    with pytest.raises(api.BadRequest, match="Unsupported format"):
        api.call({"action": "generate_policy", "text": STATEMENT, "format": "aws-config"})
