from policy_golden_path import heuristic
from policy_golden_path.catalog import Catalog
from policy_golden_path.loader import load_statements
from policy_golden_path.models import Statement

STRONG = (
    "The Security Operations team reviews and analyzes audit records in Splunk daily for indications of "
    "inappropriate or unusual activity and assesses the potential impact of each alert. Each review is "
    "recorded in a ServiceNow ticket and findings are reported to the CISO weekly."
)


def score(text: str, requirement: str | None = None) -> float:
    return heuristic.assess(Statement("au-6", text, "ssp", requirement=requirement)).confidence


def test_example_ssp_ranks_strong_above_weak(examples):
    catalog = Catalog.load(examples / "catalog-excerpt.json")
    results = {a.statement.key: a for a in (
        heuristic.assess(s) for s in load_statements(examples / "ssp-example.json", catalog)
    )}
    strong = min(results["ia-2 [Okta]"].confidence, results["au-6 [Splunk]"].confidence)
    weak = max(results["ac-2_smt.j [Payments Platform]"].confidence, results["ac-2_smt.e [Okta]"].confidence)
    assert strong >= 0.9 and weak <= 0.35
    assert results["ia-2 [Okta]"].improvements == []
    assert results["ac-2_smt.e [Okta]"].confidence <= heuristic.PLACEHOLDER_CAP


def test_no_pass_or_fail_is_reported():
    d = heuristic.assess(Statement("au-6", STRONG, "ssp")).to_dict()
    assert not {"result", "threshold", "passed"} & set(d)
    assert "improvements" in d


def test_placeholder_is_limited():
    assert score("TBD") <= heuristic.PLACEHOLDER_CAP
    assert score(STRONG + " Retention is [insert period].") <= heuristic.PLACEHOLDER_CAP
    assert score("") == 0.0


def test_planned_work_is_limited():
    assert score(STRONG + " Automated correlation is planned for next quarter.") <= heuristic.PLANNED_CAP


def test_hedging_lowers_confidence():
    hedged = STRONG.replace("daily", "periodically as needed")
    assert score(hedged) < score(STRONG)


def test_coverage_rewards_addressing_the_requirement():
    requirement = "Report findings to [Assignment: personnel or roles to receive findings]."
    off_topic = (
        "The Security Operations team patches servers in Splunk daily using Ansible and records each change "
        "in a ServiceNow ticket that is retained with logs as evidence for the CISO."
    )
    assert score(STRONG, requirement) > score(off_topic, requirement)


def test_coverage_weight_redistributed_without_catalog():
    a = heuristic.assess(Statement("au-6", STRONG, "ssp"))
    assert "coverage" not in {c.name for c in a.criteria}
    assert abs(sum(c.weight for c in a.criteria) - 1.0) < 1e-9


def test_improvements_explain_low_scores():
    a = heuristic.assess(Statement("ac-2", "Accounts are reviewed.", "ssp"))
    assert a.confidence < 0.5
    assert any("responsible" in i for i in a.improvements)
    assert any("how often" in i for i in a.improvements)
