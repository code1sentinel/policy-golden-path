"""The seeded risk register in examples/: each scenario should land where a reviewer would put it."""

from pathlib import Path

import pytest

from vitals import heuristic
from vitals.models import IDENTIFIED_RISK
from vitals.tabular import parse_csv

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture(scope="module")
def results():
    items = parse_csv((EXAMPLES / "risk-register-example.csv").read_text(), source="register")
    return {a.statement.title: a for a in map(heuristic.assess, items) if a.statement.kind == IDENTIFIED_RISK}


def has(a, text):
    return any(text in i for i in a.improvements)


@pytest.mark.parametrize("risk", ["R-01", "R-02", "R-03", "R-04", "R-07", "R-08", "R-15"])
def test_well_treated_risks_score_high(results, risk):
    a = results[risk]
    assert a.confidence >= 0.9 and all(t["relevant"] for t in a.details["treatments"]), a.improvements


def test_layered_treatments_cover_prevent_detect_recover(results):
    types = {t["label"]: set(t["types"]) for t in results["R-01"].details["treatments"]}
    assert "recover" in types["Backup and restore"] and "detect" in types["Endpoint detection"]
    assert "detect" in {k for t in results["R-02"].details["treatments"] for k in t["types"]}


def test_untreated_and_mislinked_risks_score_low(results):
    assert results["R-09"].confidence < 0.3 and has(results["R-09"], "No policy intent or control treats")
    assert results["R-10"].confidence < 0.3 and has(results["R-10"], "'Password policy' does not appear")
    assert results["R-13"].confidence < 0.1


def test_weak_treatments_are_partly_adopted(results):
    assert 0.4 < results["R-06"].confidence < 0.7 and has(results["R-06"], "says 'as appropriate'")
    assert 0.4 < results["R-12"].confidence < 0.7 and has(results["R-12"], "say which tier")


def test_backup_only_high_risk_stays_below_80_percent(results):
    a = results["R-14"]
    assert a.confidence < 0.8
    assert has(a, "Nothing prevents") and has(a, "nothing would detect") and has(a, "do the same job")


def test_low_risk_with_heavy_treatment_is_questioned_not_failed(results):
    a = results["R-11"]
    assert a.confidence > 0.8 and has(a, "check the effort is justified")


def test_control_statements_are_im8_style_and_implementations_follow_them():
    items = parse_csv((EXAMPLES / "risk-register-example.csv").read_text(), source="register")
    controls = [s for s in items if s.kind == "control-statement"]
    assert controls and all(heuristic.assess(s).confidence >= 0.8 for s in controls)
    implementations = [s for s in items if s.kind == "implementation"]
    by_label = {s.component: s for s in controls}
    assert all(s.requirement == by_label[s.component].text for s in implementations)
