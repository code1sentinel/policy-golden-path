import pytest

from vitals import heuristic
from vitals.guides import ADOPTED, PARTLY, practice, practice_status
from vitals.models import IMPLEMENTATION, RECOMMENDATION, RISK_STATEMENT, Statement


def rich(kind):
    return Statement("ac-2", "x " * 30, "ssp", kind=kind, requirement="Review accounts.",
                     policy_intent="Reviewed quarterly.", risk_statement="Because it is manual.")


@pytest.mark.parametrize("kind", [IMPLEMENTATION, RISK_STATEMENT, RECOMMENDATION])
def test_every_scored_criterion_has_a_guide(kind):
    for name in {c.name for c in heuristic.assess(rich(kind)).criteria}:
        guide = practice(kind, name)
        assert guide, f"no guide for {kind}/{name}"
        assert all(guide[k] for k in ("title", "why", "how", "weak", "strong"))


def test_practice_status_thresholds():
    assert practice_status(ADOPTED) == "adopted"
    assert practice_status(ADOPTED - 0.01) == "partly"
    assert practice_status(PARTLY) == "partly"
    assert practice_status(PARTLY - 0.01) == "not-yet"


def test_assessment_reports_practices_adopted():
    strong = ("The Security Operations team reviews audit records in Splunk daily for unusual activity; each "
              "review is recorded in a ServiceNow ticket and reported to the CISO weekly.")
    a = heuristic.assess(Statement("au-6", strong, "ssp"))
    d = a.to_dict()
    assert d["practices"]["total"] == len(d["criteria"])
    assert d["practices"]["adopted"] + d["practices"]["partly"] + d["practices"]["not-yet"] == d["practices"]["total"]
    responsibility = next(c for c in d["criteria"] if c["name"] == "responsibility")
    assert responsibility["status"] == "adopted" and responsibility["practice"] == "Name who is responsible"


def test_summary_counts_practices(examples):
    from vitals import report
    from vitals.loader import load_statements

    items = [heuristic.assess(s) for s in load_statements(examples / "assessment-results-example.json")]
    s = report.summary(items)["by_kind"]["risk-statement"]
    assert s["practices_total"] == 16 and s["practices_adopted"] == 8
    assert "8 of 16 best practices adopted" in report.to_table(items)


def _all_assessments(examples):
    from vitals.catalog import Catalog
    from vitals.loader import load_statements
    from vitals.policy import attach_intents, load_policies

    catalog = Catalog.load(examples / "catalog-excerpt.json")
    policies = load_policies(examples / "policy-example.json")
    out = []
    for name in ("ssp-example.json", "component-definition-example.json", "assessment-results-example.json"):
        items = load_statements(examples / name, catalog)
        attach_intents(items, policies)
        out += [heuristic.assess(s) for s in items]
    return out


def test_every_improvement_belongs_to_a_practice(examples):
    for a in _all_assessments(examples):
        attached = [i for c in a.criteria for i in c.issues]
        assert sorted(attached) == sorted(a.improvements), a.statement.key


def test_no_adopted_practice_has_an_open_improvement(examples):
    for a in _all_assessments(examples):
        for c in a.to_dict()["criteria"]:
            if c["status"] == "adopted":
                assert c["issues"] == [], (a.statement.key, c["name"])
        if a.improvements:
            assert a.practices["adopted"] < a.practices["total"], a.statement.key


def test_open_improvement_caps_a_high_score_at_partly():
    assert practice_status(0.95, has_issues=True) == "partly"
    assert practice_status(0.95, has_issues=False) == "adopted"
    assert practice_status(0.2, has_issues=True) == "not-yet"


def test_wording_practice_carries_no_weight():
    text = ("The SOC team reviews alerts daily in Splunk for unusual activity such as privilege escalation, "
            "and each review is recorded in a ServiceNow ticket.")
    a = heuristic.assess(Statement("au-6", text, "ssp"))
    implemented = next(c for c in a.criteria if c.name == "implemented")
    assert implemented.weight == 0 and implemented.issues
    assert abs(sum(c.weight for c in a.criteria) - 1.0) < 1e-9
