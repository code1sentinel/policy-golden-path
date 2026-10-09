import json

import pytest

from codify.clauses import read_policy
from codify.project import NS, from_oscal, from_params, new_project, to_csv, to_oscal, to_params, to_report, to_rows


@pytest.fixture
def acme(examples):
    return new_project(read_policy("acme.md", (examples / "acme-information-security-policy-2016.md").read_text()),
                       source="acme.md")


def test_parameters_round_trip():
    prose, params = to_params("c-6.4", "Lock accounts after [5] failed login attempts within [N] minutes.")
    assert prose == ("Lock accounts after {{ insert: param, c-6.4_prm_1 }} failed login attempts within "
                     "{{ insert: param, c-6.4_prm_2 }} minutes.")
    assert params == [{"id": "c-6.4_prm_1", "label": "number of attempts", "values": ["5"]},
                      {"id": "c-6.4_prm_2", "label": "time period (minutes)"}]
    assert from_params(prose, params) == "Lock accounts after [5] failed login attempts within [N] minutes."


def test_catalog_shape(acme):
    cat = to_oscal(acme)["catalog"]
    assert cat["metadata"]["oscal-version"] == "1.1.2"
    assert cat["metadata"]["remarks"].startswith("Applies to: This policy applies to all employees")
    group = next(g for g in cat["groups"] if g["title"] == "Backup and Recovery")
    control = group["controls"][0]
    assert control["id"] == "c-9.1a" and control["parts"][0] == {
        "id": "c-9.1a_smt", "name": "statement", "prose": "Back up all servers nightly."}
    props = {p["name"]: p["value"] for p in control["props"]}
    assert props["legacy-clause"] == "9.1" and props["status"] == "draft" and props["responsible-role"] == \
        "The IT Department"
    assert props["source-type"] == "clause"
    assert {p["name"] for p in control["parts"]} == {"statement", "guidance", "legacy-text", "drafting-notes"}
    # every legacy clause, with its type, is kept in the back matter
    resources = cat["back-matter"]["resources"]
    assert len(resources) == 43
    six_three = next(r for r in resources if r["title"].startswith("6.3"))
    assert {p["name"]: p["value"] for p in six_three["props"]}["duplicate-of"] == "6.1"
    assert all(p.get("ns") == NS for p in six_three["props"])


def test_saved_catalog_resumes_exactly(acme):
    acme["controls"][0]["status"] = "accepted"
    acme["controls"][0]["risk"] = "Excess access could be misused."
    back = from_oscal(json.loads(json.dumps(to_oscal(acme))))
    keys = ("id", "clause", "text", "guidance", "risk", "who", "notes", "status", "origin", "source_type", "risk_id")
    assert [{k: c[k] for k in keys} for c in back["controls"]] == [{k: c[k] for k in keys} for c in acme["controls"]]
    assert back["clauses"] == acme["clauses"] and back["title"] == acme["title"] and back["uuid"] == acme["uuid"]
    assert "risks" not in back


def test_any_catalog_opens_as_a_starting_point():
    catalog = {"catalog": {"uuid": "00000000-0000-4000-8000-000000000000", "metadata": {"title": "Backup catalog"},
                           "groups": [{"id": "br", "title": "Backup and Recovery", "controls": [{
                               "id": "br-1", "title": "Backup",
                               "params": [{"id": "br-1_prm_1", "label": "time period (days)"}],
                               "props": [{"name": "risk-statement", "value": "Data could be lost."}],
                               "parts": [{"id": "br-1_smt", "name": "statement",
                                          "prose": "Back up data every {{ insert: param, br-1_prm_1 }} day(s)."},
                                         {"id": "br-1_gdn", "name": "guidance", "prose": "Use AWS Backup."}]}]}]}}
    p = from_oscal(catalog)
    assert p["controls"] == [{"id": "br-1", "clause": "br-1", "text": "Back up data every [N] day(s).",
                              "guidance": "Use AWS Backup.", "risk": "Data could be lost.", "who": "", "notes": [],
                              "status": "draft", "origin": "catalog", "source_type": "clause", "risk_id": ""}]
    assert p["clauses"][0]["heading"] == "Backup and Recovery"
    with pytest.raises(ValueError, match="no controls"):
        from_oscal({"catalog": {"metadata": {"title": "empty"}}})
    with pytest.raises(ValueError, match="not an OSCAL catalog"):
        from_oscal({"profile": {}})


def test_rows_report_and_formula_safety(acme):
    rows = to_rows(acme, {c["id"]: 0.9 for c in acme["controls"]})
    assert rows[1][:5] == ["5.1a", "5.1", "Requirement", acme["clauses"][11]["text"],
                           "Grant access to Agency systems on a need-to-know basis."]
    assert rows[0] == ["control id", "legacy clause", "clause type", "legacy text", "control statement",
                       "parameters", "guidance", "risk it treats", "who", "status", "origin", "score", "notes"]
    assert len(rows) == 1 + len(acme["controls"]) + 17  # plus the 16 non-requirement clauses and the duplicate
    acme["controls"][0]["text"] = "=HYPERLINK(\"http://evil\")"
    assert "'=HYPERLINK" in to_csv(acme)
    report = to_report(acme)
    assert report.startswith("# Acme Agency Information Security Policy: conversion report")
    assert "**43 clauses → 38 controls**" in report and "| 6.3 | Duplicate |" in report
