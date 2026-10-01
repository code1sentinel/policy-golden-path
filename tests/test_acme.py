"""The Acme demo policy against its key (examples/acme-policy-key.md): what each clause is, and how it converts."""

import re

import pytest

from codify.clauses import read_policy
from codify.control import parts
from codify.project import new_project, summary

NOT_CONTROLS = {"1.1", "1.2", "11.1", "12.1", "17.1", "17.2"}
CONTEXT = {"2.1": "scope", "2.2": "scope", "3.1": "definition", "3.2": "definition", "3.3": "definition",
           "4.1": "role", "4.2": "role", "4.3": "role", "4.4": "role", "16.1": "exception"}
VAGUE = {"5.2", "8.1", "9.2", "10.1", "10.2"}  # "regularly", "timely", "periodically", "as needed", "appropriate"
TOOLS = {"7.1": "Symantec", "9.1": "Veritas"}


@pytest.fixture(scope="module", params=["md", "docx"])
def project(request, examples_dir):
    path = examples_dir / f"acme-information-security-policy-2016.{request.param}"
    content = path.read_bytes() if request.param == "docx" else path.read_text()
    return new_project(read_policy(path.name, content))


def test_every_clause_is_sorted_as_the_key_says(project):
    for c in project["clauses"]:
        expected = "not-a-control" if c["id"] in NOT_CONTROLS else CONTEXT.get(c["id"], "requirement")
        assert c["type"] == expected, (c["id"], c["reason"])
    assert [c["id"] for c in project["clauses"] if c["duplicate_of"]] == ["6.3"]


def test_headline(project):
    s = summary(project)
    assert (s["clauses"], s["by_type"]["requirement"], s["duplicates"], s["context"], s["by_type"]["not-a-control"]) \
        == (43, 27, 1, 10, 6)
    # the key's ideal is 33 controls; the rules split a little more eagerly, and a person merges
    assert 33 <= s["controls"] <= 40


def test_every_requirement_gets_a_draft_except_the_duplicate(project):
    drafted = {c["clause"] for c in project["controls"]}
    requirements = {c["id"] for c in project["clauses"] if c["type"] == "requirement"}
    assert drafted == requirements - {"6.3"}


def test_drafts_are_control_shaped(project):
    for c in project["controls"]:
        p = parts(c["text"])
        assert p["action"], c["text"]                      # starts with the action
        assert not p["tools"], c["text"]                   # no product named
        assert not re.search(r"\b(shall|must|should)\b", c["text"], re.I), c["text"]


def test_vague_timing_becomes_parameters_and_tools_move_to_guidance(project):
    for clause in VAGUE:
        texts = " ".join(c["text"] for c in project["controls"] if c["clause"] == clause)
        assert "[N]" in texts, clause
    for clause, tool in TOOLS.items():
        guidance = " ".join(c["guidance"] for c in project["controls"] if c["clause"] == clause)
        assert tool in guidance, clause
    six_one = [c["text"] for c in project["controls"] if c["clause"] == "6.1"]
    assert any("[8]" in t for t in six_one) and any("[90]" in t for t in six_one)
