import json

import pytest

from codify import ai, api

CLAUSE = "User accounts shall be reviewed regularly and access that is no longer required shall be removed."


def reply(*controls, wrap=lambda s: s):
    return wrap(json.dumps({"controls": [
        {"action": "", "scope": "", "limit": "", "purpose": "", "guidance": "", "risk": "", "notes": [], **c}
        for c in controls]}))


def test_prompt_is_one_clause_with_the_rule_drafts():
    p = ai.prompt("4.1", CLAUSE, "Access Control")
    assert p["system"] == ai.SYSTEM and p["schema"] == ai.SCHEMA
    assert 'Legacy clause 4.1 (section "Access Control")' in p["user"] and CLAUSE in p["user"]
    assert "- Review user accounts at least every [N] days." in p["user"] and "note: Replaced 'regularly'" in p["user"]


def test_schema_is_strict():
    item = ai.SCHEMA["properties"]["controls"]["items"]
    assert set(item["required"]) == set(item["properties"]) and item["additionalProperties"] is False


def test_reply_becomes_ai_drafts():
    out = ai.from_reply("4.1", reply(
        {"action": "Review", "scope": "user accounts", "limit": "at least every [N] days",
         "purpose": "to identify access that is no longer needed", "guidance": "e.g. SailPoint",
         "risk": "Leavers keep access.", "notes": ["Set N."]},
        {"action": "Remove", "scope": "access that is no longer required", "limit": "within [N] days."}), model="claude-opus-5-5")
    assert [c["id"] for c in out] == ["4.1a", "4.1b"]
    first = out[0]
    assert first["text"] == ("Review user accounts at least every [N] days "
                             "to identify access that is no longer needed.")
    assert first["origin"] == "ai" and first["status"] == "draft" and first["guidance"] == "e.g. SailPoint"
    assert first["notes"][0].startswith("Drafted by AI (claude-opus-5-5)") and first["notes"][-1] == "Set N."
    assert out[1]["text"] == "Remove access that is no longer required within [N] days."


def test_reply_in_a_code_fence_and_odd_values():
    out = ai.from_reply("7", reply({"action": "users must  encrypt", "scope": "laptops", "notes": [3, "ok"]},
                                   {"action": " "}, wrap=lambda s: f"Here you go:\n```json\n{s}\n```"))
    assert len(out) == 1 and out[0]["id"] == "7" and out[0]["text"] == "Users must encrypt laptops."
    assert any("not a verb" in n for n in out[0]["notes"]) and out[0]["notes"][-1] == "ok"


@pytest.mark.parametrize("bad, message", [
    ("no json here", "no JSON"), ("{oops}", "not valid JSON"), ('{"items": []}', "no 'controls'"),
    (reply({"action": ""}), "no control statements"),
])
def test_bad_replies(bad, message):
    with pytest.raises(ValueError, match=message):
        ai.from_reply("1", bad)


def test_api_round_trip():
    p = api.call({"action": "ai_prompt", "clause_id": "4.1", "text": CLAUSE})
    assert "Legacy clause 4.1:" in p["user"]
    out = api.call({"action": "ai_reply", "clause_id": "4.1", "model": "m",
                    "reply": reply({"action": "Review", "scope": "user accounts", "limit": "at least every [90] days"})})
    assert out["controls"][0]["text"] == "Review user accounts at least every [90] days."
    assert out["scores"]["4.1"]["confidence"] > 0.8
    with pytest.raises(api.BadRequest, match="no JSON"):
        api.call({"action": "ai_reply", "clause_id": "4.1", "reply": "sorry"})
    with pytest.raises(api.BadRequest, match="no text"):
        api.call({"action": "ai_prompt", "clause_id": "4.1", "text": " "})


def test_ai_drafts_survive_the_catalog(examples):
    opened = api.call({"action": "open", "text": "4.1 User accounts shall be reviewed regularly."})
    project = opened["project"]
    project["controls"] = api.call({"action": "ai_reply", "clause_id": "4.1", "model": "m", "reply": reply(
        {"action": "Review", "scope": "user accounts", "limit": "at least every [N] days"})})["controls"]
    saved = api.call({"action": "export", "format": "oscal", "project": project})
    again = api.call({"action": "open", "name": "x.json", "content": saved["content"]})["project"]["controls"]
    assert again[0]["origin"] == "ai" and again[0]["notes"][0].startswith("Drafted by AI (m)")
