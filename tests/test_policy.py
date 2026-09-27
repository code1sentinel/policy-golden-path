import pytest

from oscal_assess import heuristic
from oscal_assess.catalog import Catalog
from oscal_assess.heuristic import commitments
from oscal_assess.loader import load_statements
from oscal_assess.models import Statement
from oscal_assess.policy import Policy, attach_intents, load_policies, parse_policies

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


def test_falling_short_of_a_commitment_is_limited():
    a = assess(MEETS.replace("quarterly", "annually"))
    assert a.confidence <= heuristic.POLICY_CONFLICT_CAP
    assert 'Policy requires "quarterly"; the statement says "annually".' in a.improvements


def test_slower_deadline_and_shorter_retention_are_conflicts():
    a = assess(MEETS.replace("within 2 business days", "within 30 days").replace("3 years", "6 months"))
    assert a.confidence <= heuristic.POLICY_CONFLICT_CAP
    assert any('"within 5 business days"' in g and '"within 30 days"' in g for g in a.improvements)
    assert any('"retained for at least 12 months"' in g and "6 months" in g for g in a.improvements)


def test_omitting_a_commitment_is_limited():
    a = assess(MEETS.replace(" ServiceNow ticket retained for 3 years as", " ServiceNow ticket as"))
    assert heuristic.POLICY_CONFLICT_CAP < a.confidence <= heuristic.POLICY_OMISSION_CAP
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
