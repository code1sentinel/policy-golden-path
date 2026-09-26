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


def test_verdict_is_parsed_and_thresholded():
    payload = {
        "confidence": 85,
        "criteria": [{"name": "coverage", "score": 90, "note": "ok"}],
        "gaps": ["Name the evidence."],
        "rationale": "Mostly complete.",
    }
    client, messages = fake_client(payload=payload)
    a = ClaudeAssessor(client=client).assess(STATEMENT, 0.8)

    assert a.passed and a.confidence == 0.85
    assert a.gaps == ["Name the evidence."]
    assert a.engine == "claude:claude-opus-5"
    call = messages.calls[0]
    assert call["model"] == "claude-opus-5"
    assert call["thinking"] == {"type": "adaptive"}
    assert call["fallbacks"] == "default"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert "ac-2_smt.j" in call["messages"][0]["content"]


def test_below_threshold_fails_and_scores_are_clamped():
    payload = {"confidence": 140, "criteria": [{"name": "coverage", "score": -5, "note": ""}],
               "gaps": [], "rationale": ""}
    client, _ = fake_client(payload=payload)
    a = ClaudeAssessor(client=client).assess(STATEMENT, 0.8)
    assert a.confidence == 1.0 and a.criteria[0].score == 0.0

    payload["confidence"] = 79
    client, _ = fake_client(payload=payload)
    assert not ClaudeAssessor(client=client).assess(STATEMENT, 0.8).passed


def test_refusal_and_bad_output_fail_closed():
    for stop_reason, payload in (("refusal", ""), ("max_tokens", ""), ("end_turn", "not json")):
        client, _ = fake_client(stop_reason=stop_reason, payload=payload)
        a = ClaudeAssessor(client=client).assess(STATEMENT, 0.8)
        assert a.confidence == 0.0 and not a.passed and "manually" in a.rationale


def test_policy_intent_is_sent_and_enforced():
    stmt = Statement("ac-2", "Accounts are reviewed annually.", "ssp", statement_id="ac-2_smt.j",
                     policy_intent="Accounts are reviewed at least quarterly.", policy_ids=["ISP-05.1"])
    payload = {
        "confidence": 90,
        "criteria": [{"name": "policy_intent", "score": 20, "note": "annual, not quarterly"}],
        "gaps": ["Review quarterly."],
        "rationale": "Good but annual.",
    }
    client, messages = fake_client(payload=payload)
    a = ClaudeAssessor(client=client).assess(stmt, 0.8)

    call = messages.calls[0]
    assert '<policy-intent policies="ISP-05.1">' in call["messages"][0]["content"]
    enum = call["output_config"]["format"]["schema"]["properties"]["criteria"]["items"]["properties"]["name"]["enum"]
    assert "policy_intent" in enum
    assert a.confidence == 0.5 and not a.passed and "policy intent" in a.rationale


def test_no_policy_criterion_without_intent():
    client, messages = fake_client(payload={"confidence": 50, "criteria": [], "gaps": [], "rationale": ""})
    ClaudeAssessor(client=client).assess(STATEMENT, 0.8)
    call = messages.calls[0]
    enum = call["output_config"]["format"]["schema"]["properties"]["criteria"]["items"]["properties"]["name"]["enum"]
    assert "policy_intent" not in enum and "<policy-intent" not in call["messages"][0]["content"]
