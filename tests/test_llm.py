import json
from types import SimpleNamespace

from oscal_assess.llm import ClaudeAssessor
from oscal_assess.models import Statement


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def fake_client(stop_reason="end_turn", payload=None, model="claude-opus-5"):
    text = json.dumps(payload) if isinstance(payload, dict) else (payload or "")
    response = SimpleNamespace(
        model=model,
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
    )
    messages = FakeMessages(response)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


STATEMENT = Statement("ac-2", "Accounts are reviewed quarterly by the IAM team.", "ssp",
                      statement_id="ac-2_smt.j", requirement="j. Review accounts ...")


def test_verdict_is_parsed():
    payload = {
        "confidence": 85,
        "criteria": [{"name": "coverage", "score": 90, "note": "ok"}],
        "improvements": ["Name the evidence."],
        "rationale": "Mostly complete.",
    }
    client, messages = fake_client(payload=payload)
    a = ClaudeAssessor(client=client).assess(STATEMENT)

    assert a.confidence == 0.85
    assert a.improvements == ["Name the evidence."]
    assert a.engine == "claude:claude-opus-5"
    call = messages.calls[0]
    assert call["model"] == "claude-opus-5"
    assert call["thinking"] == {"type": "adaptive"}
    assert call["fallbacks"] == "default"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert "ac-2_smt.j" in call["messages"][0]["content"]
    assert "pass" not in call["system"].replace("Do not decide whether the text passes", "")


def test_scores_are_clamped():
    payload = {"confidence": 140, "criteria": [{"name": "coverage", "score": -5, "note": ""}],
               "improvements": [], "rationale": ""}
    client, _ = fake_client(payload=payload)
    a = ClaudeAssessor(client=client).assess(STATEMENT)
    assert a.confidence == 1.0 and a.criteria[0].score == 0.0


def test_refusal_and_bad_output_score_zero_with_a_note():
    for stop_reason, payload in (("refusal", ""), ("max_tokens", ""), ("end_turn", "not json")):
        client, _ = fake_client(stop_reason=stop_reason, payload=payload)
        a = ClaudeAssessor(client=client).assess(STATEMENT)
        assert a.confidence == 0.0 and "manually" in a.rationale and a.improvements


def schema_names(call):
    return call["output_config"]["format"]["schema"]["properties"]["criteria"]["items"]["properties"]["name"]["enum"]


def test_policy_intent_is_sent_and_enforced():
    stmt = Statement("ac-2", "Accounts are reviewed annually.", "ssp", statement_id="ac-2_smt.j",
                     policy_intent="Accounts are reviewed at least quarterly.", policy_ids=["ISP-05.1"])
    payload = {
        "confidence": 90,
        "criteria": [{"name": "policy_intent", "score": 20, "note": "annual, not quarterly"}],
        "improvements": ["Review quarterly."],
        "rationale": "Good but annual.",
    }
    client, messages = fake_client(payload=payload)
    a = ClaudeAssessor(client=client).assess(stmt)

    call = messages.calls[0]
    assert '<policy-intent policies="ISP-05.1">' in call["messages"][0]["content"]
    assert "policy_intent" in schema_names(call)
    assert a.confidence == 0.5 and "policy intent" in a.rationale


def test_no_policy_criterion_without_intent():
    client, messages = fake_client(payload={"confidence": 50, "criteria": [], "improvements": [], "rationale": ""})
    ClaudeAssessor(client=client).assess(STATEMENT)
    call = messages.calls[0]
    assert "policy_intent" not in schema_names(call) and "<policy-intent" not in call["messages"][0]["content"]


def test_risk_statement_and_recommendation_prompts():
    from oscal_assess.models import RECOMMENDATION, RISK_STATEMENT

    empty = {"confidence": 70, "criteria": [], "improvements": [], "rationale": ""}
    risk = Statement("ac-2_smt.j", "14 of 60 accounts belong to leavers.", "assessment-results",
                     kind=RISK_STATEMENT, title="Leaver accounts", ratings={"likelihood": "high"})
    client, messages = fake_client(payload=empty)
    ClaudeAssessor(client=client).assess(risk)
    call = messages.calls[0]
    assert "risk statement of a risk" in call["system"]
    assert set(schema_names(call)) == {"condition", "criteria", "cause", "threat", "impact", "scope", "rating",
                                       "clarity"}
    assert "Ratings: likelihood: high" in call["messages"][0]["content"]

    rec = Statement("ac-2_smt.j", "Disable the accounts.", "assessment-results", kind=RECOMMENDATION,
                    title="Disable leavers", risk_title="Leaver accounts", risk_statement=risk.text,
                    owner="iam-team-lead", deadline="2026-11-30")
    client, messages = fake_client(payload=empty)
    ClaudeAssessor(client=client).assess(rec)
    call = messages.calls[0]
    content = call["messages"][0]["content"]
    assert "remediation with lifecycle" in call["system"]
    assert "root_cause" in schema_names(call)
    assert 'title="Leaver accounts"' in content and "Risk statement: 14 of 60" in content
    assert 'owner="iam-team-lead" deadline="2026-11-30"' in content
