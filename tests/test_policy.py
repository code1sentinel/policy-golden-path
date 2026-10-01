import pytest

from vitals import heuristic
from vitals.heuristic import commitments
from vitals.models import CONTROL_STATEMENT, Statement
from vitals.policy import Policy, attach_intents, load_policies, parse_policies

INTENT = ("Managers review every user account at least quarterly and remove access that is no longer needed "
          "within 5 business days. Review records are retained for at least 12 months.")
MEETS = ("Review every user account and its access at least quarterly, to limit exposure from access that is "
         "no longer needed, and remove access that is no longer needed within 2 business days. Each review "
         "record is retained for at least 3 years.")


def assess(text: str, intent: str | None = INTENT):
    return heuristic.assess(Statement("ac-2", text, "t", statement_id="ac-2_smt.j", policy_intent=intent,
                                      kind=CONTROL_STATEMENT))


def criterion(a, name):
    return next(c for c in a.criteria if c.name == name)


def test_statement_meeting_the_intent_scores_high():
    a = assess(MEETS)
    assert a.confidence >= 0.9
    assert criterion(a, "policy_intent").score == pytest.approx(1.0)
    assert "3/3 policy commitments met" in criterion(a, "policy_intent").note


def test_falling_short_of_a_commitment_lowers_the_score_without_a_limit():
    a = assess(MEETS.replace("quarterly", "annually"))
    assert assess(MEETS).confidence - a.confidence >= 0.05
    assert a.confidence > 0.5  # a normal reduction, not a hard limit
    assert criterion(a, "policy_intent").score < 0.8
    omitted = assess(MEETS.replace("quarterly", ""))
    assert criterion(a, "policy_intent").score < criterion(omitted, "policy_intent").score
    assert 'Policy requires "quarterly"; the statement says "annually".' in a.improvements


def test_slower_deadline_and_shorter_retention_are_conflicts():
    a = assess(MEETS.replace("within 2 business days", "within 30 days").replace("3 years", "6 months"))
    assert criterion(a, "policy_intent").score < 0.7
    assert any('"within 5 business days"' in g and '"within 30 days"' in g for g in a.improvements)
    assert any('"retained for at least 12 months"' in g and "6 months" in g for g in a.improvements)


def test_omitting_a_commitment_lowers_the_score():
    a = assess(MEETS.replace(" for at least 3 years", ""))
    assert a.confidence < assess(MEETS).confidence
    assert any("does not say how long records are kept" in g for g in a.improvements)


def test_equivalent_wording_counts_as_met():
    a = assess(MEETS.replace("quarterly", "every 90 days"))
    assert a.confidence >= 0.9


def test_without_intent_criterion_is_absent_and_weights_sum_to_one():
    a = assess(MEETS, intent=None)
    assert "policy_intent" not in {c.name for c in a.criteria}
    assert sum(c.weight for c in a.criteria) == pytest.approx(1.0)
    with_intent = assess(MEETS)
    assert sum(c.weight for c in with_intent.criteria) == pytest.approx(1.0)


def test_missing_terms_are_readable_words():
    a = assess("Reset passwords daily and log each reset.")
    [gap] = [g for g in a.improvements if g.startswith("Show how")]
    assert "managers" in gap and "quarterly" not in gap and "manag," not in gap


def test_commitments_are_parsed():
    c = commitments("Reviewed at least quarterly, escalated within 24 hours, logs retained for 400 days, "
                    "backups every 2 weeks, with 13-month retention.")
    assert sorted(d for d, _ in c["period"]) == [14, 91]
    assert c["deadline"] == [(1.0, "within 24 hours")]
    assert sorted(round(d) for d, _ in c["retention"]) == [395, 400]


def test_policies_map_to_controls_and_statement_parts(examples):
    statements = [
        Statement("ia-2", "x", "catalog", kind=CONTROL_STATEMENT),
        Statement("ac-2", "x", "catalog", statement_id="ac-2_smt.j", kind=CONTROL_STATEMENT),
        Statement("ac-2", "x", "catalog", statement_id="ac-2_smt.e", kind=CONTROL_STATEMENT),
    ]
    attach_intents(statements, load_policies(examples / "policy-example.json"))
    by_key = {s.key: s for s in statements}
    assert by_key["ia-2"].policy_ids == ["ISP-06"]
    assert by_key["ac-2_smt.j"].policy_ids == ["ISP-05.1"]
    assert by_key["ac-2_smt.e"].policy_ids == ["ISP-05.2"]


def test_policy_without_controls_applies_everywhere_and_intents_combine():
    s = Statement("ac-2", "x", "ssp", statement_id="ac-2_smt.j")
    attach_intents([s], [Policy("A", "Intent A."), Policy("B", "Intent B.", controls=["ac-2"]),
                         Policy("C", "Intent C.", controls=["ia-2"])])
    assert s.policy_ids == ["A", "B"] and s.policy_intent == "Intent A. Intent B."


@pytest.mark.parametrize("data, message", [
    ({}, "'policies' list"),
    ({"policies": [{"id": "P1"}]}, "P1 needs a non-empty 'intent'"),
    ({"policies": [{"id": "P1", "intent": "x", "controls": "ac-2"}]}, "must be a list"),
])
def test_invalid_policy_files(data, message):
    with pytest.raises(ValueError, match=message):
        parse_policies(data)


RISK_BASED = ("User access is reviewed at a frequency commensurate with the risk of the access, and access "
              "that is no longer needed is removed promptly.")
TIERED = ("Tier accounts in the annual access risk assessment owned by the CISO: Tier 1 covers "
          "privileged and payment access, Tier 2 everything else. Review Tier 1 access quarterly "
          "and Tier 2 access annually, and remove unneeded access within 5 business days. "
          "Reassess tiers after major changes, and record each review.")


def test_risk_based_intent_is_met_by_a_tiered_schedule():
    a = assess(TIERED, RISK_BASED)
    c = criterion(a, "policy_intent")
    assert c.score >= 0.9, c.note
    assert "risk basis named" in c.note
    assert not any("risk-based" in i or "tier" in i.lower() for i in a.improvements)


def test_based_on_risk_alone_is_not_enough():
    vague = "Review user access based on risk, and record each review."
    a = assess(vague, RISK_BASED)
    text = " ".join(a.improvements)
    assert "'based on risk' without saying how risk is rated" in text
    assert "Give each risk tier its own frequency" in text
    assert "who sets the risk tiers" in text
    assert criterion(a, "policy_intent").score < criterion(assess(TIERED, RISK_BASED), "policy_intent").score - 0.3


def test_risk_based_intent_does_not_demand_fixed_timelines():
    a = assess(TIERED, RISK_BASED)
    assert not any("Policy requires" in i for i in a.improvements)


def test_policies_apply_to_risk_statements_through_their_targets():
    from vitals.models import RISK_STATEMENT

    risk = Statement("ac-2_smt.j, au-6", "x", "assessment-results", kind=RISK_STATEMENT)
    assert risk.targets == [("ac-2", "ac-2_smt.j"), ("au-6", None)]
    attach_intents([risk], [Policy("A", "Intent A.", controls=["ac-2_smt.j"]),
                            Policy("B", "Intent B.", controls=["au-6"]),
                            Policy("C", "Intent C.", controls=["ia-2"])])
    assert risk.policy_ids == ["A", "B"]
