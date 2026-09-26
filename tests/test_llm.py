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


def test_risk_verdict_is_parsed():
    from oscal_assess.risk import RiskRegister

    risk = RiskRegister.parse({"risks": [{
        "id": "R-9", "title": "Account takeover", "controls": {"ia-2": "vulnerability", "au-6": None},
        "inherent": {"ale": 1},
    }]}).risks[0]
    payload = {
        "confidence": 82,
        "controls": [{"control_id": "IA-2", "factors": ["vulnerability"], "score": 90, "note": "MFA"}],
        "gaps": ["au-6 has no statement."],
        "rationale": "Prevention is strong.",
    }
    client, messages = fake_client(payload=payload)
    confidence, controls, gaps, rationale, engine = ClaudeAssessor(client=client).assess_risk(
        risk, {"ia-2": [STATEMENT]})

    assert confidence == 0.82 and engine == "claude:claude-opus-5"
    assert [(c.control_id, c.score) for c in controls] == [("ia-2", 0.9), ("au-6", 0.0)]
    prompt = messages.calls[0]["messages"][0]["content"]
    assert 'expected-factor="vulnerability"' in prompt and "(no implementation statement)" in prompt


def test_risk_refusal_fails_closed():
    from oscal_assess.risk import RiskRegister

    risk = RiskRegister.parse({"risks": [{"title": "x", "controls": ["ia-2"], "inherent": {"ale": 1}}]}).risks[0]
    client, _ = fake_client(stop_reason="refusal")
    confidence, controls, gaps, rationale, _ = ClaudeAssessor(client=client).assess_risk(risk, {})
    assert confidence == 0.0 and "manually" in rationale
