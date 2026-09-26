from oscal_assess import DEFAULT_THRESHOLD, heuristic
from oscal_assess.catalog import Catalog
from oscal_assess.loader import load_statements
from oscal_assess.models import Statement

STRONG = (
    "The Security Operations team reviews and analyzes audit records in Splunk daily for indications of "
    "inappropriate or unusual activity and assesses the potential impact of each alert. Each review is "
    "recorded in a ServiceNow ticket and findings are reported to the CISO weekly."
)


def score(text: str, requirement: str | None = None) -> float:
    return heuristic.assess(Statement("au-6", text, "ssp", requirement=requirement), DEFAULT_THRESHOLD).confidence


def test_default_threshold_is_eighty_percent():
    assert DEFAULT_THRESHOLD == 0.80


def test_example_ssp_passes_strong_and_fails_weak(examples):
    catalog = Catalog.load(examples / "catalog-excerpt.json")
    results = {a.statement.key: a for a in (
        heuristic.assess(s, DEFAULT_THRESHOLD) for s in load_statements(examples / "ssp-example.json", catalog)
    )}
    assert results["ia-2 [Okta]"].passed
    assert results["au-6 [Splunk]"].passed
    assert not results["ac-2_smt.j [Payments Platform]"].passed
    assert not results["ac-2_smt.e [Okta]"].passed
    assert results["ac-2_smt.e [Okta]"].confidence <= heuristic.PLACEHOLDER_CAP


def test_pass_is_inclusive_at_threshold():
    a = heuristic.assess(Statement("au-6", STRONG, "ssp"), threshold=0.0)
    a.threshold = a.confidence
    assert a.passed


def test_placeholder_is_capped():
    assert score("TBD") <= heuristic.PLACEHOLDER_CAP
    assert score(STRONG + " Retention is [insert period].") <= heuristic.PLACEHOLDER_CAP
    assert score("") == 0.0


def test_planned_work_is_capped():
    assert score(STRONG + " Automated correlation is planned for next quarter.") <= heuristic.PLANNED_CAP


def test_hedging_lowers_confidence():
    hedged = STRONG.replace("daily", "periodically as needed")
    assert score(hedged) < score(STRONG)


def test_coverage_rewards_addressing_the_requirement():
    requirement = "Report findings to [Assignment: personnel or roles to receive findings]."
    on_topic = STRONG
    off_topic = (
        "The Security Operations team patches servers in Splunk daily using Ansible and records each change "
        "in a ServiceNow ticket that is retained with logs as evidence for the CISO."
    )
    assert score(on_topic, requirement) > score(off_topic, requirement)


def test_coverage_weight_redistributed_without_catalog():
    a = heuristic.assess(Statement("au-6", STRONG, "ssp"), DEFAULT_THRESHOLD)
    assert "coverage" not in {c.name for c in a.criteria}
    assert abs(sum(c.weight for c in a.criteria) - 1.0) < 1e-9


def test_gaps_explain_failures():
    a = heuristic.assess(Statement("ac-2", "Accounts are reviewed.", "ssp"), DEFAULT_THRESHOLD)
    assert not a.passed
    assert any("responsible" in g for g in a.gaps)
    assert any("how often" in g for g in a.gaps)
