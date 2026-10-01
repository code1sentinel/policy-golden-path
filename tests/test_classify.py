import pytest

from codify.clauses import Clause
from codify.classify import sort_clause, sort_clauses


@pytest.mark.parametrize("text, kind", [
    ("Users shall lock their screens.", "requirement"),
    ("All staff are required to complete training annually.", "requirement"),
    ("Remote access is not permitted without VPN.", "requirement"),
    ("Firewall rules are reviewed quarterly.", "requirement"),  # present tense, as legacy policies often are
    ('"Personal data" refers to data about an identifiable individual.', "definition"),
    ("This policy applies to all employees and contractors.", "scope"),
    ("Data owners are accountable for classifying their data.", "role"),
    ("The Head of IT may grant a waiver for up to 6 months.", "exception"),
    ("The organisation recognises the importance of security.", "not-a-control"),
    ("The use of USB drives is discouraged.", "not-a-control"),
    ("Staff who breach this policy will face disciplinary action.", "not-a-control"),
    ("Limited personal use is permitted.", "not-a-control"),
    ("This policy is approved by the board.", "not-a-control"),
])
def test_wording_decides_the_type(text, kind):
    assert sort_clause(Clause("x", text)).type == kind


def test_section_heading_decides_first():
    assert sort_clause(Clause("4.3", "Line managers shall ensure staff comply.", "4", "Roles and Responsibilities")).type \
        == "role"
    assert sort_clause(Clause("1.2", "Staff shall follow it.", "1", "Purpose")).type == "not-a-control"


def test_duplicates_repeat_an_earlier_requirement():
    clauses = [Clause("6.1", "Passwords shall be at least 8 characters and changed every 90 days."),
               Clause("6.2", "Accounts shall lock after 5 attempts."),
               Clause("6.3", "Users must change their passwords every 90 days.")]
    results = sort_clauses(clauses)
    assert [r.duplicate_of for r in results] == [None, None, "6.1"]
    assert results[2].reason == "repeats 6.1"
