"""Offline, deterministic rubric scorer.

Each statement is scored against the questions an assessor asks of an
implementation statement: who does it, with what, how often, what evidence it
leaves, whether it answers what the control actually requires, and whether it
meets the intent of the organization's policy. The weighted sum is the
confidence, reduced by wording that does not belong in a statement of fact
(hedges, obligations, open-ended examples) and capped hard when the statement
is a placeholder, describes planned work, or contradicts the policy.
"""

from __future__ import annotations

import re

from .models import Assessment, CriterionResult, Statement

# Relative weights. coverage needs a catalog and policy_intent needs a policy
# intent; when either is missing the others are rescaled to sum to 1.
WEIGHTS = {
    "substance": 0.12,
    "responsibility": 0.12,
    "mechanism": 0.12,
    "frequency": 0.12,
    "evidence": 0.12,
    "coverage": 0.20,
    "policy_intent": 0.20,
}

PLACEHOLDER_CAP = 0.20
PLANNED_CAP = 0.50
POLICY_CONFLICT_CAP = 0.50  # statement falls short of a policy commitment ("annually" vs "quarterly")
POLICY_OMISSION_CAP = 0.75  # statement does not mention a commitment the policy makes
TOLERANCE = 1.05  # "every 90 days" meets "quarterly"

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
    r"attempts? to|tries to|some|various)\b",
    re.I,
)
# Obligations restate the requirement instead of saying how it is met.
_OBLIGATIONS = re.compile(r"\b(must|shall|is required to|are required to|is expected to|are expected to)\b", re.I)
# Open-ended examples leave the scope undefined...
_OPEN_EXAMPLES = re.compile(
    r"\b(such as|for example|for instance|including but not limited to|among others|and so on)\b"
    r"|\be\.g\.|\betc\b\.?",
    re.I,
)
# ...unless the statement points to where the full set is defined.
_DEFINED_SET = re.compile(
    r"\b(listed|defined|documented|enumerated|maintained|catalogu?ed|specified) in\b[^.;]{0,60}?"
    r"\b(runbook|register|inventory|catalogu?e?|cmdb|standard|procedure|playbook|list|appendix|baseline|"
    r"library|matrix|schedule)\b"
    r"|\b(full|complete) (list|set|inventory)\b",
    re.I,
)

WORDING_PENALTY = 0.08  # per distinct phrase
WORDING_FLOOR = 0.60    # wording can take off at most 40%
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
    includes organization organizational organizations defined assignment selection one following
    every least longer needed within days hours weeks months years business minimum""".split()
)
_WORD = re.compile(r"[a-z][a-z-]+")


def _stem(word: str) -> str:
    for suffix in ("ations", "ation", "ments", "ment", "ities", "ity", "ings", "ing", "ies", "als", "al",
                   "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            word = word[: -len(suffix)]
            break
    return word[:-1] if word.endswith("e") and len(word) > 4 else word


def _term_words(text: str) -> dict[str, str]:
    """Key terms of the text: stem -> the first word it came from, for readable gap messages."""
    out: dict[str, str] = {}
    for w in _WORD.findall(text.lower()):
        if len(w) >= 4 and w not in _STOPWORDS:
            out.setdefault(_stem(w), w)
    return out


def _terms(text: str) -> set[str]:
    return set(_term_words(text))


def _missing(required: dict[str, str], present: set[str], limit: int = 8) -> str:
    return ", ".join(sorted(required[t] for t in set(required) - present)[:limit])


def _distinct(pattern: re.Pattern, text: str) -> set[str]:
    return {m.group(0).lower() for m in pattern.finditer(text)}


def _ratio(found: int, full_at: int) -> float:
    return min(1.0, found / full_at)


_DAYS = {"minute": 1 / 1440, "hour": 1 / 24, "day": 1, "business day": 1.4, "week": 7, "fortnight": 14,
         "month": 30.4, "quarter": 91, "year": 365}
_PERIOD_WORDS = {"hourly": 1 / 24, "daily": 1, "nightly": 1, "weekly": 7, "fortnightly": 14, "biweekly": 14,
                 "monthly": 30.4, "quarterly": 91, "semi-annually": 182, "semiannually": 182,
                 "half-yearly": 182, "biannually": 182, "annually": 365, "yearly": 365}
_UNIT = r"(minute|hour|business day|day|week|fortnight|month|quarter|year)s?"
_NUM = r"(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|twelve|thirty|ninety)"
_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "twelve": 12,
            "thirty": 30, "ninety": 90}
_PERIOD_WORD_RE = re.compile(r"\b(" + "|".join(_PERIOD_WORDS) + r")\b", re.I)
_EVERY_RE = re.compile(r"\bevery\s+(?:" + _NUM + r"\s+)?" + _UNIT + r"\b", re.I)
_ONCE_RE = re.compile(r"\b(?:once|at least once)\s+(?:a|per|each|every)\s+" + _UNIT + r"\b", re.I)
_DEADLINE_RE = re.compile(r"\bwithin\s+" + _NUM + r"\s+" + _UNIT + r"\b", re.I)
_RETENTION_RE = re.compile(
    r"\b(?:retain(?:ed|s)?|kept|stored|preserved|retention(?: period)?(?: of)?)\s+(?:for\s+)?"
    r"(?:(?:at least|a minimum of|minimum of|no less than)\s+)?" + _NUM + r"[\s-]+" + _UNIT + r"\b"
    r"|\b" + _NUM + r"[\s-]+" + _UNIT + r"\s+retention\b",
    re.I,
)


def _num(text: str | None) -> float:
    if not text:
        return 1.0
    return _NUMBERS.get(text.lower()) or float(text)


def _unit(text: str) -> float:
    return _DAYS[re.sub(r"s$", "", text.lower())]


Commitment = tuple[float, str]  # (days, the words used)


def commitments(text: str) -> dict[str, list[Commitment]]:
    """Measurable commitments in the text: how often, how fast, and how long records are kept (in days)."""
    periods = [(_PERIOD_WORDS[m.group(1).lower()], m.group(0)) for m in _PERIOD_WORD_RE.finditer(text)]
    periods += [(_num(m.group(1)) * _unit(m.group(2)), m.group(0)) for m in _EVERY_RE.finditer(text)]
    periods += [(_unit(m.group(1)), m.group(0)) for m in _ONCE_RE.finditer(text)]
    deadlines = [(_num(m.group(1)) * _unit(m.group(2)), m.group(0)) for m in _DEADLINE_RE.finditer(text)]
    retention = []
    for m in _RETENTION_RE.finditer(text):
        n, u = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        retention.append((_num(n) * _unit(u), m.group(0)))
    return {"period": periods, "deadline": deadlines, "retention": retention}


_OMITTED = {
    "period": "does not say how often",
    "deadline": "does not give a time limit",
    "retention": "does not say how long records are kept",
}


def _policy_intent(intent: str, text: str) -> tuple[float, str, list[str], list[str], list[str]]:
    """Score how far the statement meets the policy intent.

    Returns (score, note, gaps, conflicts, omissions): conflicts are commitments the
    statement falls short of, omissions are commitments it does not mention.
    """
    required, found = commitments(intent), commitments(text)
    # Words inside a commitment ("retained for 3 years") are scored as commitments, not terms.
    phrases = " ".join(p for kind in required.values() for _, p in kind)
    intent_words = {k: w for k, w in _term_words(intent).items() if k not in _terms(phrases)}
    matched = set(intent_words) & _terms(text)
    term_score = min(1.0, (len(matched) / len(intent_words)) / 0.5) if intent_words else 1.0
    gaps: list[str] = []
    conflicts: list[str] = []
    omissions: list[str] = []
    if term_score < 0.6:
        gaps.append("Show how the statement meets the policy intent (missing terms: "
                    + _missing(intent_words, matched) + ").")

    met = total = 0
    for kind, wants in required.items():
        have = found[kind]
        for want, phrase in wants:
            total += 1
            if kind == "retention":
                ok = any(days * TOLERANCE >= want for days, _ in have)
            else:
                ok = any(days <= want * TOLERANCE for days, _ in have)
            if ok:
                met += 1
            elif have:
                pick = max if kind == "retention" else min
                closest = pick(have)[1]
                conflicts.append(f'Policy requires "{phrase}"; the statement says "{closest}".')
            else:
                omissions.append(f'Policy requires "{phrase}"; the statement {_OMITTED[kind]}.')

    score = 0.4 * term_score + 0.6 * (met / total) if total else term_score
    note = f"{len(matched)}/{len(intent_words)} intent terms"
    if total:
        note += f", {met}/{total} policy commitments met"
    return score, note, gaps, conflicts, omissions


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
        req_words = _term_words(statement.requirement)
        req_terms = set(req_words)
        matched = req_terms & _terms(text)
        coverage = len(matched) / len(req_terms) if req_terms else 1.0
        score = min(1.0, coverage / 0.4)
        criteria.append(
            CriterionResult("coverage", score, WEIGHTS["coverage"],
                            f"{len(matched)}/{len(req_terms)} requirement terms addressed")
        )
        if score < 0.6:
            gaps.append("Address more of the control requirement (missing terms: "
                        + _missing(req_words, matched) + ").")

    conflicts: list[str] = []
    omissions: list[str] = []
    if statement.policy_intent:
        score, note, intent_gaps, conflicts, omissions = _policy_intent(statement.policy_intent, text)
        criteria.append(CriterionResult("policy_intent", score, WEIGHTS["policy_intent"], note))
        gaps += conflicts + omissions + intent_gaps

    # Rescale so the criteria that apply to this statement sum to 1.
    total_weight = sum(c.weight for c in criteria)
    for c in criteria:
        c.weight /= total_weight

    confidence = sum(c.score * c.weight for c in criteria)
    notes: list[str] = []

    if conflicts:
        confidence = min(confidence, POLICY_CONFLICT_CAP)
        notes.append(f"falls short of a policy commitment; capped at {POLICY_CONFLICT_CAP:.0%}")
    elif omissions:
        confidence = min(confidence, POLICY_OMISSION_CAP)
        notes.append(f"does not show a policy commitment is met; capped at {POLICY_OMISSION_CAP:.0%}")

    wording: list[str] = []
    hedges = _distinct(_HEDGES, text)
    if hedges:
        wording += sorted(hedges)
        gaps.append("Replace hedging words (" + ", ".join(sorted(hedges)) + ") with what actually happens.")
    obligations = _distinct(_OBLIGATIONS, text)
    if obligations:
        wording += sorted(obligations)
        gaps.append("'" + "', '".join(sorted(obligations)) + f"' {'restate' if len(obligations) > 1 else 'restates'} "
                    "the requirement; describe what "
                    "enforces it and what happens today.")
    examples = {e.rstrip(".") + ("." if e.startswith(("e.g", "etc")) else "") for e in _distinct(_OPEN_EXAMPLES, text)}
    if examples and not _DEFINED_SET.search(text):
        wording += sorted(examples)
        gaps.append("'" + "', '".join(sorted(examples)) + f"' {'leave' if len(examples) > 1 else 'leaves'} "
                    "the scope open; list the full set or say where it is defined.")
    if wording:
        factor = max(WORDING_FLOOR, 1.0 - WORDING_PENALTY * len(wording))
        confidence *= factor
        notes.append(f"wording ({', '.join(wording)}) reduced confidence by {1 - factor:.0%}")

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
