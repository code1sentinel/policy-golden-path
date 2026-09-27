import pytest

from golden_path import heuristic
from golden_path.models import Statement

BASE = ("The SOC team reviews alerts daily in Splunk for privilege escalation and impossible travel, "
        "and each review is recorded in a ServiceNow ticket.")


def assess(text):
    return heuristic.assess(Statement("au-6", text, "ssp"))


def test_clean_statement_has_no_wording_penalty():
    assert "wording" not in assess(BASE).rationale


@pytest.mark.parametrize("phrase", ["must", "shall", "is required to"])
def test_obligations_are_penalised(phrase):
    a = assess(BASE + f" Analysts {phrase} escalate incidents to the CISO.")
    assert a.confidence < assess(BASE).confidence
    assert any(f"'{phrase}' restates the requirement" in g for g in a.improvements)


@pytest.mark.parametrize("phrase", ["such as", "e.g.", "for example", "including but not limited to", "etc."])
def test_open_ended_examples_are_penalised(phrase):
    a = assess(BASE.replace("for privilege escalation", f"for unusual activity, {phrase} privilege escalation"))
    assert a.confidence < assess(BASE).confidence
    assert any(f"'{phrase}' leaves the scope open" in g for g in a.improvements)


def test_examples_of_a_defined_list_are_allowed():
    text = BASE.replace("for privilege escalation",
                        "for the detection use cases listed in the SOC runbook, such as privilege escalation")
    a = assess(text)
    assert not any("scope open" in g for g in a.improvements)


def test_recorded_in_a_ticket_is_not_a_defined_list():
    a = assess(BASE.replace("for privilege escalation", "for activity such as privilege escalation"))
    assert any("scope open" in g for g in a.improvements)


def test_hedges_still_penalised_and_total_wording_penalty_is_bounded():
    a = assess(BASE + " Staff should, where possible, escalate issues such as fraud, etc., and must "
                      "notify the CISO as needed; this may generally happen.")
    assert any("vague wording" in g for g in a.improvements)
    assert "reduced confidence by 40%" in a.rationale
