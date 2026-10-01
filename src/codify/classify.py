"""Sort legacy clauses: which are requirements, and which are context or not controls at all.

    requirement     something that must (or should) be done: becomes one or more controls
    scope           who or what the policy applies to: becomes the catalog's "applies to"
    definition      what a term means: goes to the catalog's back matter
    role            who is responsible or accountable: the "who" for implementation, not a control
    exception       how exceptions are approved: kept as catalog metadata
    not-a-control   aspirations, consequences, permissions and descriptions: nothing to test

A section heading decides first ("3. Definitions" makes every clause in it a
definition), then the clause's own wording. Requirements that repeat an earlier
one are flagged as duplicates. Every result carries the reason, so a person can
see why and change it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .clauses import Clause
from .text import _terms, commitments

REQUIREMENT = "requirement"
SCOPE = "scope"
DEFINITION = "definition"
ROLE = "role"
EXCEPTION = "exception"
NOT_A_CONTROL = "not-a-control"
TYPES = (REQUIREMENT, SCOPE, DEFINITION, ROLE, EXCEPTION, NOT_A_CONTROL)
TYPE_LABELS = {REQUIREMENT: "Requirement", SCOPE: "Scope", DEFINITION: "Definition", ROLE: "Role",
               EXCEPTION: "Exception", NOT_A_CONTROL: "Not a control"}


@dataclass
class Sorted:
    type: str
    reason: str
    duplicate_of: str | None = None  # the earlier clause a requirement repeats


def _re(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I)


# Section headings that decide the type of every clause in them.
_HEADINGS = [
    (_re(r"\b(purpose|introduction|objectives?|background|overview|policy statement)\b"), NOT_A_CONTROL,
     "in the {heading} section"),
    (_re(r"\b(scope|applicability|application)\b"), SCOPE, "in the {heading} section"),
    (_re(r"\b(definitions?|glossary|terms|interpretation)\b"), DEFINITION, "in the {heading} section"),
    (_re(r"\b(roles?|responsibilit(y|ies)|accountabilit(y|ies)|governance structure)\b"), ROLE,
     "in the {heading} section"),
    (_re(r"\b(exceptions?|waivers?|deviations?|dispensations?)\b"), EXCEPTION, "in the {heading} section"),
]

# The clause's own wording, checked in order.
_WORDING = [
    (_re(r'^\W*[\w /-]{1,60}\W*\s+(means|refers to|is defined as|shall mean|includes)\b'), DEFINITION,
     "defines a term"),
    (_re(r"\b(this|the) (policy|standard|document|procedure)\s+(applies|covers)\b|\bapplies to all\b"), SCOPE,
     "says what the policy applies to"),
    (_re(r"\b(exceptions?|waivers?|deviations?)\b[^.]{0,60}\b(approv|authori[sz]|grant)|"
         r"\b(approv|authori[sz]|grant)\w*[^.]{0,40}\b(exceptions?|waivers?|deviations?)\b"), EXCEPTION,
     "sets out how exceptions are approved"),
    (_re(r"\b(is|are) (responsible|accountable)\b|\bresponsibilit(y|ies) (of|for)\b"), ROLE,
     "assigns responsibility"),
    (_re(r"\b(committed to|commitment to|strives? to|aims? to|endeavou?rs? to|recogni[sz]es|believes|"
         r"encouraged to|is encouraged|are encouraged|promote a culture)\b"), NOT_A_CONTROL,
     "an aspiration: nothing to test"),
    (_re(r"\b(is|are) discouraged\b"), NOT_A_CONTROL,
     "'discouraged' is not a requirement: decide whether to make it one (restrict, prohibit) or drop it"),
    (_re(r"\b(may|will|shall) (result in|lead to) (disciplinary|termination|sanctions?)|\bdisciplinary action\b"),
     NOT_A_CONTROL, "a consequence of non-compliance, not a control"),
    (_re(r"\b(is|are) permitted\b|\bmay use\b|\bpersonal use\b"), NOT_A_CONTROL,
     "a permission: nothing to enforce"),
    (_re(r"\b(this|the) (policy|standard|document) (sets out|describes|establishes|provides|outlines)\b"),
     NOT_A_CONTROL, "describes the policy itself"),
]
_REQUIREMENT = _re(r"\b(shall|must|should|will|is required to|are required to|needs? to|is to be|are to be|"
                   r"is prohibited|are prohibited|not permitted|is not allowed|are not allowed)\b")


# Legacy policies often state a requirement in the present tense: "Firewall rules are reviewed quarterly."
_PRESENT_PASSIVE = _re(r"^(?!(this|the) (policy|standard|document)\b).*?\b(is|are) (\w+ly )?(\w+ed|\w+en|kept|set|"
                       r"held|run|built|sent|made|done|bought|met|put|shut|split|spent|stored)\b")


def sort_clause(clause: Clause) -> Sorted:
    """The type of one clause, and why."""
    heading = clause.heading or ""
    for pattern, kind, why in _HEADINGS:
        if heading and pattern.search(heading):
            return Sorted(kind, why.format(heading=heading))
    for pattern, kind, why in _WORDING:
        if pattern.search(clause.text):
            return Sorted(kind, why)
    if m := _REQUIREMENT.search(clause.text):
        return Sorted(REQUIREMENT, f"'{m.group(0).lower()}' sets a requirement")
    if _PRESENT_PASSIVE.search(clause.text):
        return Sorted(REQUIREMENT, "states what is done, in the present tense")
    return Sorted(NOT_A_CONTROL, "no requirement wording (shall, must, should)")


def _commitment_phrases(text: str) -> set[str]:
    return {p.lower() for kind in commitments(text).values() for _, p in kind}


def _repeats(later: str, earlier: str) -> bool:
    """Does the later requirement say nothing the earlier one does not?"""
    later_terms, earlier_terms = _terms(later), _terms(earlier)
    if not later_terms:
        return False
    contained = len(later_terms & earlier_terms) / len(later_terms)
    later_c, earlier_c = _commitment_phrases(later), _commitment_phrases(earlier)
    if later_c:
        return later_c <= earlier_c and contained >= 0.6
    overlap = len(later_terms & earlier_terms) / len(later_terms | earlier_terms)
    return contained >= 0.8 and overlap >= 0.6


def sort_clauses(clauses: list[Clause]) -> list[Sorted]:
    """Types for every clause, with requirements that repeat an earlier requirement marked as duplicates."""
    results = [sort_clause(c) for c in clauses]
    seen: list[Clause] = []
    for clause, result in zip(clauses, results):
        if result.type != REQUIREMENT:
            continue
        original = next((e for e in seen if _repeats(clause.text, e.text)), None)
        if original is not None:
            result.duplicate_of = original.id
            result.reason = f"repeats {original.id}"
        else:
            seen.append(clause)
    return results
