import pytest

from policy_golden_path import heuristic
from policy_golden_path.models import IMPLEMENTATION, RECOMMENDATION, RISK_STATEMENT
from policy_golden_path.tabular import parse_csv, template


def test_template_parses_to_one_of_each_kind():
    items = parse_csv(template(), source="t.csv")
    assert [s.kind for s in items] == [IMPLEMENTATION, RISK_STATEMENT, RECOMMENDATION]
    impl, risk, rec = items
    assert (impl.control_id, impl.statement_id, impl.component) == ("ac-2", "ac-2_smt.j", "Okta")
    assert risk.ratings == {"likelihood": "high", "impact": "high"}
    assert (rec.owner, rec.deadline, rec.ratings) == ("IAM team lead", "2026-11-30", {"risk": "high"})
    assert rec.risk_statement.startswith("14 of 60")
    assert impl.uuid == "t.csv:row-2"
    assert all(0 <= heuristic.assess(s).confidence <= 1 for s in items)


def test_headers_are_forgiving_and_blank_rows_skipped():
    items = parse_csv("﻿Kind,Control ID,Text,Policy Intent\n"
                      "Risk Statement,au-6,Logs are not reviewed.,\n"
                      ",,,\n"
                      ",ac-2,Accounts are reviewed.,Reviewed quarterly.\n")
    assert [(s.kind, s.control_id) for s in items] == [(RISK_STATEMENT, "au-6"), (IMPLEMENTATION, "ac-2")]
    assert items[1].policy_intent == "Reviewed quarterly." and items[1].policy_ids == ["csv"]


@pytest.mark.parametrize("content, message", [
    ("", "empty"),
    ("control_id,description\nac-2,x\n", "'text' column"),
    ("kind,text\nfinding,x\n", "row 2: unknown kind 'finding'"),
])
def test_bad_csv(content, message):
    with pytest.raises(ValueError, match=message):
        parse_csv(content)
