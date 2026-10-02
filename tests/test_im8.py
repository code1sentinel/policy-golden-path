import json

import pytest

from codify import api, im8
from codify.project import NS, to_oscal


def test_bundled_catalog():
    data = im8.catalog()
    assert data["version"] == "2025.05.13" and len(data["controls"]) == 137 and len(data["domains"]) == 15
    ac3 = data["by_id"]["ac-3"]
    assert "{{" not in ac3["statement"] and "[time period (days)]" in ac3["statement"]
    assert ac3["levels"] == {"low": 1, "medium": 0} and ac3["risk"]
    assert "(1) signed by a trusted root Certificate Authority;" in data["by_id"]["ns-6"]["statement"]


@pytest.mark.parametrize("text, expected", [
    ("Back up all servers nightly.", "br-1"),
    ("Require passwords to be at least [8] characters long.", "as-5"),
    ("Disable the accounts of staff who leave the Agency within [N] days.", "ac-3"),
    ("Install anti-malware software on all desktops and servers.", "is-7"),
    ("Apply security patches to all systems within [N] days.", "is-2"),
    ("Lock accounts after [5] failed login attempts.", "as-4"),
    ("Escort visitors at all times.", "dc-2"),
    ("Retain system logs for at least [N] days.", "lm-8"),
    ("Require MFA for administrator accounts.", "ac-2"),
])
def test_suggestions_rank_the_right_control_first(text, expected):
    assert im8.suggest(text)[0]["id"] == expected


def test_suggestions_skip_noise_and_exclusions():
    assert im8.suggest("Take appropriate action.") == []
    assert all(s["id"] != "br-1" for s in im8.suggest("Back up all servers nightly.", exclude=("br-1",)))


def test_coverage_counts_confirmed_mappings_only():
    project = {"controls": [{"id": "9.1", "im8": ["br-1", "nope"]}, {"id": "6.1", "im8": ["as-5"]},
                            {"id": "6.2", "im8": ["as-5"]}, {"id": "7.1"}]}
    cov = im8.coverage(project)
    assert cov["covered"] == 2 and cov["total"] == 137
    ap = next(d for d in cov["domains"] if d["id"] == "as")
    assert ap["covered"] == 1 and next(r for r in ap["controls"] if r["id"] == "as-5")["controls"] == ["6.1", "6.2"]
    must = cov["levels"]["low-0"]
    assert must["total"] == 6 and "pm-3" in must["gaps"]


def test_mappings_in_the_catalog_exports_and_report(examples):
    opened = api.call({"action": "open", "name": "acme.md",
                       "content": (examples / "acme-information-security-policy-2016.md").read_text()})
    project = opened["project"]
    backup = next(c for c in project["controls"] if c["id"] == "9.1a")
    backup["im8"] = ["br-1", "bogus"]
    clean = api._clean_project(project)
    assert next(c for c in clean["controls"] if c["id"] == "9.1a")["im8"] == ["br-1"]

    catalog = to_oscal(clean)["catalog"]
    control = next(c for g in catalog["groups"] for c in g["controls"] if c["id"] == "c-9.1a")
    assert {"name": "im8-reform", "value": "br-1", "ns": NS} in control["props"]
    link = next(x for x in control["links"] if x["rel"] == "related")
    assert link["href"] == "#" + im8.catalog()["uuid"] and link["text"] == "IM8 Reform br-1: Backup"
    assert any(r["uuid"] == im8.catalog()["uuid"] for r in catalog["back-matter"]["resources"])

    saved = api.call({"action": "export", "format": "oscal", "project": clean})
    again = api.call({"action": "open", "name": "x.json", "content": saved["content"]})["project"]
    assert next(c for c in again["controls"] if c["id"] == "9.1a")["im8"] == ["br-1"]

    csv = api.call({"action": "export", "format": "csv", "project": clean})["content"]
    assert "IM8 Reform" in csv.splitlines()[0] and ",br-1," in csv
    report = api.call({"action": "export", "format": "report", "project": clean})["content"]
    assert "## IM8 Reform coverage" in report and "**1 of 137**" in report
    assert "Not covered: pm-3 System Security Plan (SSP) Development" in report


def test_the_im8_catalog_opens_mapped_to_itself():
    raw = {"catalog": {"uuid": im8.catalog()["uuid"], "metadata": {"title": "IM8"}, "groups": [{
        "id": "br", "title": "Backup", "controls": [{"id": "br-1", "title": "Backup", "parts": [
            {"id": "br-1_smt", "name": "statement", "prose": "Backup all important data."}]}]}]}}
    project = api.call({"action": "open", "name": "im8.json", "content": json.dumps(raw)})["project"]
    assert project["controls"][0]["im8"] == ["br-1"]


def test_api():
    listing = api.call({"action": "im8"})
    assert len(listing["controls"]) == 137 and listing["domains"]["br"] == "Backup and Recovery"
    out = api.call({"action": "im8", "text": "Back up all servers nightly.", "context": "9.1 backups", "exclude": ["br-3"]})
    assert out["suggestions"][0]["id"] == "br-1" and all(s["id"] != "br-3" for s in out["suggestions"])
    cov = api.call({"action": "coverage", "project": {"clauses": [], "controls": [
        {"id": "1", "clause": "1", "text": "Back up data.", "im8": ["br-1"]}]}})
    assert cov["covered"] == 1
    with pytest.raises(api.BadRequest, match="list of IM8"):
        api.call({"action": "coverage", "project": {"clauses": [], "controls": [{"id": "1", "im8": "br-1"}]}})
