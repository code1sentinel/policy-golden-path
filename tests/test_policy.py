import pytest

from golden_path import heuristic
from golden_path.catalog import Catalog
from golden_path.heuristic import commitments
from golden_path.loader import load_statements
from golden_path.models import Statement
from golden_path.policy import Policy, attach_intents, load_policies, parse_policies

INTENT = ("Managers review every user account at least quarterly and remove access that is no longer needed "
          "within 5 business days. Review records are retained for at least 12 months.")
MEETS = ("The IAM team and line managers review every user account and its access quarterly in the Okta "
         "access certification workflow. Access flagged as no longer needed is removed within 2 business days, "
         "and each review is recorded in a ServiceNow ticket retained for 3 years as evidence.")


def assess(text: str, intent: str | None = INTENT):
    return heuristic.assess(Statement("ac-2", text, "ssp", statement_id="ac-2_smt.j", policy_intent=intent))


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
    a = assess(MEETS.replace(" ServiceNow ticket retained for 3 years as", " ServiceNow ticket as"))
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
    a = assess("The service desk resets passwords daily and logs each reset.")
    [gap] = [g for g in a.improvements if g.startswith("Show how")]
    assert "managers" in gap and "quarterly" not in gap and "manag," not in gap


def test_commitments_are_parsed():
    c = commitments("Reviewed at least quarterly, escalated within 24 hours, logs retained for 400 days, "
                    "backups every 2 weeks, with 13-month retention.")
    assert sorted(d for d, _ in c["period"]) == [14, 91]
    assert c["deadline"] == [(1.0, "within 24 hours")]
    assert sorted(round(d) for d, _ in c["retention"]) == [395, 400]


def test_policies_map_to_controls_and_statement_parts(examples):
    catalog = Catalog.load(examples / "catalog-excerpt.json")
    statements = load_statements(examples / "ssp-example.json", catalog)
    attach_intents(statements, load_policies(examples / "policy-example.json"))
    by_key = {s.key: s for s in statements}
    assert by_key["ia-2 [Okta]"].policy_ids == ["ISP-06"]
    assert by_key["ac-2_smt.j [Payments Platform]"].policy_ids == ["ISP-05.1"]
    assert by_key["ac-2_smt.e [Okta]"].policy_ids == ["ISP-05.2"]


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
TIERED = ("Accounts are tiered in the annual access risk assessment owned by the CISO: Tier 1 covers "
          "privileged and payment access, Tier 2 everything else. Managers review Tier 1 access quarterly "
          "and Tier 2 access annually in Okta, and unneeded access is removed within 5 business days. "
          "Tiers are reassessed after major changes. Each review is recorded in a ServiceNow ticket.")


def test_risk_based_intent_is_met_by_a_tiered_schedule():
    a = assess(TIERED, RISK_BASED)
    c = criterion(a, "policy_intent")
    assert c.score >= 0.9, c.note
    assert "risk basis named" in c.note
    assert not any("risk-based" in i or "tier" in i.lower() for i in a.improvements)


def test_based_on_risk_alone_is_not_enough():
    vague = ("Managers review user access in Okta based on risk, and each review is recorded in a "
             "ServiceNow ticket.")
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
    from golden_path.models import RISK_STATEMENT

    risk = Statement("ac-2_smt.j, au-6", "x", "assessment-results", kind=RISK_STATEMENT)
    assert risk.targets == [("ac-2", "ac-2_smt.j"), ("au-6", None)]
    attach_intents([risk], [Policy("A", "Intent A.", controls=["ac-2_smt.j"]),
                            Policy("B", "Intent B.", controls=["au-6"]),
                            Policy("C", "Intent C.", controls=["ia-2"])])
    assert risk.policy_ids == ["A", "B"]
