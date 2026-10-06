import base64
import json

import pytest

from codify import api


@pytest.fixture
def opened(examples):
    return api.call({"action": "open", "name": "acme.md",
                     "content": (examples / "acme-information-security-policy-2016.md").read_text()})


def test_open_text_word_and_saved_catalog(opened, examples):
    assert opened["summary"]["clauses"] == 43 and set(opened["scores"]) == {c["id"] for c in opened["project"]["controls"]}
    word = api.call({"action": "open", "name": "acme.docx", "content_base64": base64.b64encode(
        (examples / "acme-information-security-policy-2016.docx").read_bytes()).decode()})
    assert word["summary"]["controls"] == opened["summary"]["controls"]
    pasted = api.call({"action": "open", "text": "Users shall lock screens."})
    assert pasted["project"]["clauses"][0]["text"] == "Users shall lock screens." and pasted["project"]["source"] == ""
    saved = api.call({"action": "export", "format": "oscal", "project": opened["project"]})
    again = api.call({"action": "open", "name": saved["name"], "content": saved["content"]})
    assert [c["text"] for c in again["project"]["controls"]] == [c["text"] for c in opened["project"]["controls"]]


def test_check_scores_and_breaks_down_a_statement():
    out = api.call({"action": "check", "text": "Review user accounts at least every [90] days.",
                    "risk": "Leavers keep access."})
    assert out["assessment"]["confidence"] > 0.9 and out["parts"]["limit"] == "at least every [90] days"


def test_redraft_and_score(opened):
    out = api.call({"action": "redraft", "clause_id": "12.1", "text": "The use of USB drives is discouraged."})
    assert [c["text"] for c in out["controls"]] == ["Prohibit the use of USB drives."] and "12.1" in out["scores"]
    scored = api.call({"action": "score", "project": opened["project"]})
    assert scored["scores"] == opened["scores"]


def test_exports(opened):
    project = opened["project"]
    xlsx = api.call({"action": "export", "format": "xlsx", "project": project})
    assert xlsx["name"] == "acme-agency-information-security-policy-controls.xlsx"
    assert base64.b64decode(xlsx["content_base64"])[:2] == b"PK"
    csv = api.call({"action": "export", "format": "csv", "project": project})["content"]
    assert csv.startswith("control id,") and "IM8 Reform" not in csv.splitlines()[0]
    report = api.call({"action": "export", "format": "report", "project": project})["content"]
    assert "conversion report" in report and "IM8 Reform" not in report


def test_legacy_im8_mappings_are_dropped_on_export(opened):
    project = opened["project"]
    project["controls"][0]["im8"] = ["br-1"]
    saved = api.call({"action": "export", "format": "oscal", "project": project})
    assert "im8-reform" not in saved["content"]
    again = api.call({"action": "open", "name": saved["name"], "content": saved["content"]})["project"]
    assert "im8" not in again["controls"][0]


@pytest.mark.parametrize("body, message", [
    ({"action": "nope"}, "'action' must be one of"),
    ({"action": "im8"}, "'action' must be one of"),
    ({"action": "coverage"}, "'action' must be one of"),
    ({"action": "check", "text": ""}, "enter a control statement"),
    ({"action": "open"}, "send a file"),
    ({"action": "open", "name": "x.json", "content": "{"}, "not valid JSON"),
    ({"action": "open", "name": "x.docx", "content_base64": "!!"}, "not valid base64"),
    ({"action": "export", "format": "pdf", "project": {"clauses": [], "controls": []}}, "'format' must be"),
    ({"action": "export", "format": "csv", "project": {"clauses": [{"type": "bad"}], "controls": []}},
     "unknown clause type"),
    ({"action": "score", "project": "x"}, "'project' must be an object"),
])
def test_bad_requests_say_what_to_fix(body, message):
    with pytest.raises(api.BadRequest, match=message):
        api.call(body)


def test_handle_returns_json_errors():
    assert json.loads(api.handle("{not json"))["status"] == 400
    assert json.loads(api.handle(json.dumps({"action": "check", "text": ""}))) == {
        "error": "enter a control statement to check", "status": 400}


def test_import_risks_and_draft_templates(examples):
    csv = (examples / "acme-risk-register.csv").read_text()
    parsed = api.call({"action": "import_risks", "name": "risks.csv", "content": csv})
    assert [r["id"] for r in parsed["risks"]] == ["R-001", "R-002", "R-003", "R-004", "R-005"]
    assert parsed["errors"] == []
    risk = parsed["risks"][0]
    suggestions = api.call({"action": "suggest_risk_controls", "risk": risk})["suggestions"]
    assert any(s["id"] == "restrict-access" for s in suggestions)
    drafts = api.call({"action": "draft_risk_controls", "risk": risk,
                       "template_ids": ["restrict-access"]})["controls"]
    assert drafts[0]["source_type"] == "risk" and drafts[0]["risk_id"] == "R-001"
    opened = api.call({"action": "open", "text": "Users shall lock screens."})
    project = opened["project"]
    project["risks"] = parsed["risks"]
    project["controls"] = project["controls"] + drafts
    saved = api.call({"action": "export", "format": "oscal", "project": project})
    catalog = json.loads(saved["content"])
    assert "risk" in json.dumps(catalog)
    again = api.call({"action": "open", "name": "c.json", "content": saved["content"]})["project"]
    assert [r["id"] for r in again["risks"]] == ["R-001", "R-002", "R-003", "R-004", "R-005"]
    risk_csv = api.call({"action": "export", "format": "risks", "project": project})["content"]
    assert risk_csv.startswith("id,title,") and "R-001" in risk_csv
    with pytest.raises(api.BadRequest, match="title, likelihood and impact"):
        api.call({"action": "import_risks", "name": "x.csv", "content": "foo,bar\n1,2\n"})


def test_ai_prompt_for_a_risk():
    risk = {"id": "R-001", "title": "Unauthorised access", "likelihood": 4, "impact": 5,
            "asset": "Agency systems", "threat": "Stolen credentials", "vulnerability": "Excessive access"}
    p = api.call({"action": "ai_prompt", "risk": risk})
    assert "Identified risk R-001" in p["user"] and "Agency systems" in p["user"]
    out = api.call({"action": "ai_reply", "risk_id": "R-001", "source_type": "risk", "model": "m",
                    "reply": json.dumps({"controls": [
                        {"action": "Restrict", "scope": "access to agency systems", "limit": "",
                         "purpose": "to prevent unauthorised use", "guidance": "", "risk": "", "notes": []}]})})
    assert out["controls"][0]["source_type"] == "risk" and out["controls"][0]["risk_id"] == "R-001"
    assert out["controls"][0]["origin"] == "ai"
