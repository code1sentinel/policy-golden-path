import pytest

from vitals import heuristic
from vitals.models import IDENTIFIED_RISK, IMPLEMENTATION, RECOMMENDATION, RISK_STATEMENT
from vitals.tabular import REQUIRED, parse_csv, template

HEADER = "policy intent,control statement,risk statement,recommendation"


def test_template_has_the_four_columns_first():
    first = template().splitlines()[0]
    assert first.startswith(HEADER)


def test_each_row_follows_the_policy_path():
    items = parse_csv(template(), source="t.csv")
    assert [s.kind for s in items] == [IDENTIFIED_RISK] + [IMPLEMENTATION, RISK_STATEMENT, RECOMMENDATION] * 2
    identified, control, risk, rec = items[:4]
    # both rows link risk R-01, so it is assessed once against both rows' intents and controls
    assert identified.title == "R-01" and [t.label for t in identified.treatments] == ["Leaver accounts", "Audit review"]
    # the control and risk statements carry the row's policy intent; the recommendation carries its risk
    assert control.policy_intent == risk.policy_intent and control.policy_intent.startswith("User access")
    assert rec.risk_statement == risk.text
    assert (control.control_id, control.key) == ("ac-2", "ac-2 [Leaver accounts]")
    assert (risk.key, rec.key) == ("Leaver accounts [ac-2]", "Leaver accounts [ac-2]")
    assert risk.ratings == {"likelihood": "high", "impact": "high"}
    assert (rec.owner, rec.deadline) == ("IAM team lead", "2026-11-30")


def test_template_example_rows_score_strong_and_weak():
    items = parse_csv(template())
    scores = [heuristic.assess(s).confidence for s in items]
    assert min(scores[1:4]) > 0.8 and max(scores[4:]) < 0.35


def test_empty_cells_and_blank_rows_are_skipped():
    items = parse_csv(f"{HEADER}\n"
                      "Reviewed quarterly.,The IAM team reviews access quarterly.,,\n"
                      ",,,\n"
                      ",,Logs are not reviewed.,Enable daily log review.\n")
    assert [(s.kind, s.key) for s in items] == [
        (IMPLEMENTATION, "Row 2"), (RISK_STATEMENT, "Row 4"), (RECOMMENDATION, "Row 4")]
    assert items[1].policy_intent is None and items[2].risk_statement == "Logs are not reviewed."


def test_forgiving_headers_delimiters_and_aliases():
    items = parse_csv("﻿Policy_Intent;Implementation Statement;RISK-STATEMENT;Recommendation;Control;Deadline\n"
                      "Reviewed quarterly.;The team reviews access quarterly.;Access not reviewed.;Review it.;ac-2;2026-12-01\n")
    assert [s.kind for s in items] == [IMPLEMENTATION, RISK_STATEMENT, RECOMMENDATION]
    assert items[0].control_id == "ac-2" and items[2].deadline == "2026-12-01"
    tabbed = parse_csv("policy intent\tcontrol statement\trisk statement\trecommendation\nx\tThe team reviews.\t\t\n")
    assert tabbed[0].text == "The team reviews."


@pytest.mark.parametrize("content, message", [
    ("", "empty"),
    ("policy intent,control statement\nx,y\n", "missing: risk statement, recommendation"),
    ("kind,text\nimplementation,x\n", "missing: policy intent, control statement, risk statement, recommendation"),
    (f"{HEADER}\nOnly an intent.,,,\n", "no statements to assess"),
])
def test_bad_csv(content, message):
    with pytest.raises(ValueError, match=message):
        parse_csv(content)


def test_required_columns():
    assert REQUIRED == ("policy_intent", "control_statement", "risk_statement", "recommendation")
