"""Offline, deterministic rubric scorer.

Each statement is scored against the questions an assessor asks of an
implementation statement: who does it, with what, how often, what evidence it
leaves, and whether it answers what the control actually requires. The
weighted sum is the confidence, reduced by hedging language and capped hard
when the statement is a placeholder.
"""

from __future__ import annotations

import re

from .models import Assessment, CriterionResult, Statement

WEIGHTS = {
    "substance": 0.15,
    "responsibility": 0.15,
    "mechanism": 0.15,
    "frequency": 0.15,
    "evidence": 0.15,
    "coverage": 0.25,
}

PLACEHOLDER_CAP = 0.20
PLANNED_CAP = 0.50

_PLACEHOLDER = re.compile(
    r"\b(tbd|tbc|todo|to be (determined|confirmed|completed)|lorem ipsum|n/?a|placeholder|fill in)\b|\[insert|<[^>]+>",
    re.I,
)
_PLANNED = re.compile(
    r"\b(will be (implemented|configured|deployed|established|developed)|is planned|are planned|planned for|"
    r"plan to|intends? to|in progress|not yet|future release|roadmap)\b",
    re.I,
)
_HEDGES = re.compile(
    r"\b(as needed|as appropriate|as required|where (possible|practical|feasible)|when necessary|if necessary|"
    r"periodically|from time to time|best effort|generally|typically|usually|may|might|should|could|"
    r"attempts? to|tries to|some|various|etc)\b",
    re.I,
)
_ROLES = re.compile(
    r"\b(administrators?|admins?|team|officer|owner|isso|issm|ciso|cio|cto|manager|managers|"
    r"soc|noc|security operations|personnel|staff|custodians?|engineers?|analysts?|operators?|"
    r"supervisors?|approvers?|reviewers?|auditors?|committee|board|help ?desk|service desk|"
    r"department|hr|human resources|lead|director|responsible|accountable)\b",
    re.I,
)
_MECHANISMS = re.compile(
    r"\b(configured|enforced?s?|automated|automatically|scripted|policy|policies|procedures?|workflow|"
    r"active directory|entra|azure ad|okta|ldap|saml|oidc|sso|mfa|multi-factor|iam|rbac|"
    r"siem|splunk|sentinel|elastic|guardduty|cloudtrail|config rules?|terraform|ansible|"
    r"group policy|gpo|firewall|waf|edr|crowdstrike|defender|intune|vault|kms|hsm|tls|aes|fips|"
    r"servicenow|jira|ticket(ing)?|pipeline|scanner|nessus|qualys|tenable|agent|baseline|"
    r"encrypt(ed|ion|s)?|hash(ed|ing)?|backup|replicat(ed|ion))\b",
    re.I,
)
_FREQUENCY = re.compile(
    r"\b(hourly|daily|weekly|fortnightly|monthly|quarterly|semi-?annually|annually|yearly|"
    r"every \d+|each (day|week|month|quarter|year)|within \d+|\d+ (minutes?|hours?|days?|weeks?|months?)|"
    r"real[- ]time|continuous(ly)?|on (each|every)|upon|prior to|before|immediately|"
    r"at least (once|every)|at login|at each)\b",
    re.I,
)
_EVIDENCE = re.compile(
    r"\b(logs?|logged|logging|records?|recorded|reports?|tickets?|audit trails?|retained|retention|"
    r"documented|evidence|attestations?|sign-?off|approv(al|ed)|alerts?|dashboards?|screenshots?|"
    r"exports?|reviewed|minutes|history|archived?)\b",
    re.I,
)

_STOPWORDS = set(
    """a an and any are as at be been by for from has have in into is it its of on or other that the their
    these this those to under upon was were when where which with within without all also each such than
    then there they not only more most must shall will can may using used use based including include
    includes organization organizational organizations defined assignment selection one following""".split()
)
_WORD = re.compile(r"[a-z][a-z-]+")


def _stem(word: str) -> str:
    for suffix in ("ations", "ation", "ments", "ment", "ities", "ity", "ings", "ing", "ies", "als", "al",
                   "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            word = word[: -len(suffix)]
            break
    return word[:-1] if word.endswith("e") and len(word) > 4 else word


def _terms(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(text.lower()) if len(w) >= 4 and w not in _STOPWORDS}


def _distinct(pattern: re.Pattern, text: str) -> set[str]:
    return {m.group(0).lower() for m in pattern.finditer(text)}


def _ratio(found: int, full_at: int) -> float:
    return min(1.0, found / full_at)


def assess(statement: Statement, threshold: float) -> Assessment:
    text = statement.text.strip()
    words = len(text.split())
    criteria: list[CriterionResult] = []
    gaps: list[str] = []

    substance = 0.0 if words < 12 else min(1.0, (words - 12) / 38 + 0.25)
    criteria.append(CriterionResult("substance", substance, WEIGHTS["substance"], f"{words} words"))
    if words < 25:
        gaps.append("Statement is too brief to show how the control is met.")

    for name, pattern, full_at, gap in (
        ("responsibility", _ROLES, 1, "Name the role or team responsible for performing the control."),
        ("mechanism", _MECHANISMS, 2, "Describe the specific tool, configuration or process that implements it."),
        ("frequency", _FREQUENCY, 1, "State how often or on what trigger the control operates."),
        ("evidence", _EVIDENCE, 2, "Say what records or artefacts prove the control operated."),
    ):
        hits = _distinct(pattern, text)
        score = _ratio(len(hits), full_at)
        criteria.append(CriterionResult(name, score, WEIGHTS[name], ", ".join(sorted(hits)) or "none found"))
        if score < 0.5:
            gaps.append(gap)

    if statement.requirement:
        req_terms = _terms(statement.requirement)
        matched = req_terms & _terms(text)
        coverage = len(matched) / len(req_terms) if req_terms else 1.0
        score = min(1.0, coverage / 0.4)
        criteria.append(
            CriterionResult("coverage", score, WEIGHTS["coverage"],
                            f"{len(matched)}/{len(req_terms)} requirement terms addressed")
        )
        if score < 0.6:
            missing = sorted(req_terms - matched)[:8]
            gaps.append("Address more of the control requirement (missing terms: " + ", ".join(missing) + ").")
    else:
        # No catalog text: spread the coverage weight over the other criteria.
        scale = 1.0 / (1.0 - WEIGHTS["coverage"])
        for c in criteria:
            c.weight *= scale

    confidence = sum(c.score * c.weight for c in criteria)
    notes: list[str] = []

    hedges = _distinct(_HEDGES, text)
    if hedges:
        factor = max(0.6, 1.0 - 0.08 * len(hedges))
        confidence *= factor
        notes.append(f"hedging language ({', '.join(sorted(hedges))}) reduced confidence by {1 - factor:.0%}")
        gaps.append("Replace hedging words with definite commitments.")

    if _PLANNED.search(text):
        confidence = min(confidence, PLANNED_CAP)
        notes.append(f"describes planned rather than implemented work; capped at {PLANNED_CAP:.0%}")
        gaps.append("Describe what is implemented today, not what is planned.")

    if not text or _PLACEHOLDER.search(text):
        confidence = min(confidence, PLACEHOLDER_CAP)
        notes.append(f"placeholder or empty text; capped at {PLACEHOLDER_CAP:.0%}")
        gaps.insert(0, "Replace the placeholder with a real implementation statement.")

    rationale = f"Rubric score {confidence:.0%}" + (f"; {'; '.join(notes)}" if notes else "") + "."
    return Assessment(statement, round(confidence, 4), threshold, "heuristic", criteria, gaps, rationale)
