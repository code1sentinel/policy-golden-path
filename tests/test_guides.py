import pytest

from policygp import heuristic
from policygp.guides import ADOPTED, PARTLY, practice, practice_status
from policygp.llm import KINDS, POLICY_CRITERION
from policygp.models import IMPLEMENTATION, RECOMMENDATION, RISK_STATEMENT, Statement


def rich(kind):
    return Statement("ac-2", "x " * 30, "ssp", kind=kind, requirement="Review accounts.",
                     policy_intent="Reviewed quarterly.", risk_statement="Because it is manual.")


@pytest.mark.parametrize("kind", [IMPLEMENTATION, RISK_STATEMENT, RECOMMENDATION])
def test_every_criterion_either_engine_scores_has_a_guide(kind):
    heuristic_names = {c.name for c in heuristic.assess(rich(kind)).criteria}
    claude_names = set(KINDS[kind][1]) | ({POLICY_CRITERION} if kind == IMPLEMENTATION else set())
    for name in heuristic_names | claude_names:
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
    from policygp import report
    from policygp.loader import load_statements

    items = [heuristic.assess(s) for s in load_statements(examples / "assessment-results-example.json")]
    s = report.summary(items)["by_kind"]["risk-statement"]
    assert s["practices_total"] == 14 and s["practices_adopted"] == 7
    assert "7 of 14 best practices adopted" in report.to_table(items)
