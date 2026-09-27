import pytest

from policygp import heuristic
from policygp.findings import extract_findings
from policygp.loader import load_statements
from policygp.models import RECOMMENDATION, RISK_STATEMENT, Statement


@pytest.fixture
def items(examples):
    return load_statements(examples / "assessment-results-example.json")


def test_assessment_results_yield_risk_statements_and_recommendations(items):
    assert [(s.kind, s.key) for s in items] == [
        (RISK_STATEMENT, "Leaver accounts can approve payments [ac-2_smt.j]"),
        (RECOMMENDATION, "Automate leaver deprovisioning [ac-2_smt.j]"),
        (RISK_STATEMENT, "Audit review gaps [au-6]"),
        (RECOMMENDATION, "Improve log review [au-6]"),
    ]
    risk, rec = items[0], items[1]
    assert risk.ratings == {"likelihood": "high", "impact": "high"}
    assert rec.risk_title == risk.title and rec.risk_statement == risk.text
    assert rec.owner == "iam-team-lead"
    assert rec.deadline == "2026-11-30T00:00:00Z"
    assert rec.text.startswith("Automate leaver deprovisioning. Integrate Workday")


def test_example_scores_separate_strong_from_weak(items):
    scores = [heuristic.assess(s).confidence for s in items]
    assert scores[0] >= 0.9 and scores[1] >= 0.9
    assert scores[2] <= 0.2 and scores[3] <= 0.2


def test_poam_and_non_recommendation_remediations():
    data = {"plan-of-action-and-milestones": {
        "findings": [{"target": {"target-id": "si-2"}, "related-risks": [{"risk-uuid": "r1"}]}],
        "risks": [{
            "uuid": "r1", "title": "Unpatched servers", "statement": "12 servers are unpatched.",
            "deadline": "2026-12-01T00:00:00Z",
            "remediations": [
                {"uuid": "m1", "lifecycle": "recommendation", "title": "Patch servers"},
                {"uuid": "m2", "lifecycle": "planned", "title": "Planned patching"},
            ],
        }],
    }}
    risk, rec = extract_findings(data)
    assert (risk.source, risk.control_id, rec.title) == ("poam", "si-2", "Patch servers")
    assert rec.deadline == "2026-12-01T00:00:00Z"  # falls back to the risk deadline


def risk(text: str, **ratings) -> float:
    return heuristic.assess(Statement("ac-2", text, "assessment-results", kind=RISK_STATEMENT,
                                      ratings=ratings))


GOOD_RISK = ("14 of 60 sampled Okta accounts belonged to leavers, which does not meet AC-2, because leaver "
             "notices are processed manually. A former employee could use them to approve fraudulent payments, "
             "causing financial loss; the accounts are internet-facing, so exploitation is likely.")


def test_risk_statement_criteria():
    a = risk(GOOD_RISK, likelihood="high", impact="high")
    assert {c.name: c.score for c in a.criteria} == {
        "condition": 1.0, "criteria": 1.0, "cause": 1.0, "threat": 1.0, "impact": 1.0, "scope": 1.0, "rating": 1.0,
        "clarity": 1.0}
    assert a.improvements == []


def test_risk_statement_flags_missing_ratings_inconsistency_and_remediation():
    assert any("Record likelihood and impact" in i for i in risk(GOOD_RISK).improvements)
    low = risk(GOOD_RISK, risk="low")
    assert any("Rated 'low'" in i for i in low.improvements)
    fix = risk(GOOD_RISK + " The IAM team should disable these accounts.", likelihood="high", impact="high")
    assert any("Move the remediation" in i for i in fix.improvements)


def test_could_is_fine_in_a_risk_statement():
    a = risk(GOOD_RISK, likelihood="high", impact="high")
    assert "wording" not in a.rationale


def rec(text: str, risk_statement: str = GOOD_RISK, **kw):
    return heuristic.assess(Statement("ac-2", text, "assessment-results", kind=RECOMMENDATION,
                                      risk_statement=risk_statement, **kw))


GOOD_REC = ("Integrate Workday with Okta so leaver notices disable accounts automatically instead of being "
            "processed manually. The IAM team lead owns this by 2026-11-30. Verify closure by re-sampling "
            "60 accounts.")


def test_recommendation_criteria():
    a = rec(GOOD_REC)
    assert all(c.score >= 0.9 for c in a.criteria), [(c.name, c.score) for c in a.criteria]
    assert a.improvements == []


def test_recommendation_uses_recorded_owner_and_deadline():
    text = "Integrate Workday with Okta to disable leaver accounts automatically; verify by re-sampling accounts."
    a = rec(text, owner="iam-team-lead", deadline="2026-11-30")
    by = {c.name: c for c in a.criteria}
    assert by["owner"].score == 1.0 and by["timeline"].score == 1.0


def test_weak_recommendation_improvements():
    a = rec("Consider improving the process where possible, such as reviewing things.", ratings={"risk": "high"})
    text = " ".join(a.improvements)
    for expected in ("concrete action", "accountable", "target date", "evidence", "'consider'", "scope open"):
        assert expected in text
    assert "(risk high)" in text


def test_recommendation_must_address_the_cause():
    off = rec("Disable the 14 identified accounts in Okta now. The IAM team lead owns this by 2026-11-30 "
              "and will verify by re-sampling.")
    on = rec(GOOD_REC)
    assert on.confidence > off.confidence
    assert any("cause identified in the risk statement" in i for i in off.improvements)


def test_risk_statement_is_checked_against_catalog_and_policy(examples):
    from policygp.catalog import Catalog
    from policygp.policy import attach_intents, load_policies

    items = load_statements(examples / "assessment-results-example.json",
                            Catalog.load(examples / "catalog-excerpt.json"))
    attach_intents(items, load_policies(examples / "policy-example.json"))
    good, weak = items[0], items[2]
    assert good.requirement.startswith("j. Review accounts") and good.policy_ids == ["ISP-05.1"]
    assert weak.requirement.startswith("Audit Record Review") and weak.policy_ids == ["ISP-09"]

    by = {c.name: c for c in heuristic.assess(good).criteria}
    assert by["criteria"].score >= 0.9 and "control and policy terms" in by["criteria"].note
    weak_a = heuristic.assess(weak)
    assert any("Describe the condition against what the control and policy require" in i
               for i in weak_a.improvements)


def test_criteria_without_catalog_only_checks_a_requirement_is_named():
    a = risk(GOOD_RISK, likelihood="high", impact="high")
    assert {c.name: c for c in a.criteria}["criteria"].note == "ac-2"
