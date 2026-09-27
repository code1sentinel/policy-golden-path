from policygp import heuristic
from policygp.catalog import Catalog
from policygp.loader import load_statements
from policygp.models import Statement

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


def assess(statement):
    return heuristic.assess(statement)


def _stmt(text):
    return Statement("ac-1", text, "ssp")


def _crit(result, name):
    return next(c for c in result.criteria if c.name == name)


def test_month_may_is_not_a_hedge():
    result = assess(_stmt("Access was last recertified on 1 May 2025 by the IAM team using Okta."))
    assert "may" not in _crit(result, "implemented").note
    assert "may" in _crit(assess(_stmt("The IAM team may review access in Okta.")), "implemented").note


def test_event_driven_trigger_counts_as_frequency():
    result = assess(_stmt("AWS CloudTrail logs all available API events to an S3 bucket owned by the SOC."))
    assert _crit(result, "frequency").score == 1.0


def test_fully_inherited_control_needs_provider_and_authorization():
    named = assess(_stmt("This control is inherited from the AWS cloud service provider under its "
                         "FedRAMP High P-ATO; the SOC 2 Type II report is reviewed yearly by the ISSO."))
    assert _crit(named, "evidence").score == 1.0
    assert _crit(named, "frequency").note == "operated by the provider"
    assert not any("authorization" in t for t in named.improvements)

    unnamed = assess(_stmt("This control is inherited from the hosting provider."))
    assert any("authorization or attestation" in t for t in unnamed.improvements)
    assert unnamed.confidence < named.confidence


def test_partly_inherited_control_must_describe_customer_part():
    silent = assess(_stmt("The system partially inherits this control from the FedRAMP P-ATO granted to "
                          "the AWS Cloud Service Provider dated 1 May 2013."))
    assert any("customer's part" in t for t in silent.improvements)
    assert _crit(silent, "evidence").score == 0.5
    described = assess(_stmt("The system partially inherits this control from the AWS FedRAMP P-ATO; the "
                             "customer configures AWS Config rules, reviewed weekly by the cloud team, with "
                             "results logged to Security Hub."))
    assert not any("customer's part" in t for t in described.improvements)
