"""Offline, deterministic rubric scorer.

Each statement is scored against the questions an assessor asks of an
implementation statement: who does it, with what, how often, what evidence it
leaves, whether it answers what the control actually requires, and whether it
meets the intent of the organization's policy. The weighted sum is the
confidence, reduced by wording that does not belong in a statement of fact
(hedges, obligations, open-ended examples) and limited when the statement is a
placeholder or describes planned work.
"""

from __future__ import annotations

import re

from .models import IMPLEMENTATION, RECOMMENDATION, RISK_STATEMENT, Assessment, CriterionResult, Statement


class Improvements:
    """Areas for improvement, each recorded against the best practice it belongs to."""

    def __init__(self):
        self.items: list[tuple[str, str]] = []

    def add(self, practice: str, text: str) -> None:
        self.items.append((practice, text))

    def first(self, practice: str, text: str) -> None:
        self.items.insert(0, (practice, text))

    def extend(self, practice: str, texts: list[str]) -> None:
        self.items += [(practice, t) for t in texts]

    @property
    def texts(self) -> list[str]:
        return [t for _, t in self.items]

    def of(self, practice: str) -> list[str]:
        return [t for p, t in self.items if p == practice]


# The practice that wording, placeholders and planned work count against, for each kind.
WORDING_PRACTICE = {IMPLEMENTATION: "implemented", RISK_STATEMENT: "clarity", RECOMMENDATION: "clarity"}

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
# Vague wording: never says what actually happens.
_VAGUE = re.compile(
    r"\b(as needed|as appropriate|as required|where (possible|practical|feasible)|when necessary|if necessary|"
    r"periodically|from time to time|best effort|generally|typically|usually|"
    r"attempts? to|tries to|some|various)\b",
    re.I,
)
# Possibility: fine in a risk statement ("could allow"), not in a statement of fact.
_MODALS = re.compile(r"\b(may|might|could|should)\b", re.I)
# Tentative actions: weaken a recommendation.
_WEAK_ACTIONS = re.compile(
    r"\b(consider(ing)?|explore|look into|evaluate whether|assess whether|investigate whether|"
    r"think about|aim to|try to|where feasible|if possible|may wish to|may want to|could)\b",
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
    every least longer needed within days hours weeks months years business minimum
    should could would might always regularly more less risk often frequency""".split()
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


# A risk-based policy sets a principle ("reviewed at a frequency commensurate with risk") and leaves
# the organization to decide the values. The statement must then show how risk becomes a schedule.
_RISK_BASED = re.compile(
    r"\b(risk[- ]based|based on (the )?(assessed )?(risk|criticality|classification|sensitivity)|"
    r"commensurate with (the )?(assessed )?risk|proportionate to (the )?risk|in proportion to (the )?risk|"
    r"according to (the )?(assessed )?risk|in line with (the )?risk|risk (tier|tiering|rating|level)s?|"
    r"determined by (the )?risk)\b",
    re.I,
)
_RISK_BASIS = re.compile(
    r"\b(tier(s|ed|ing)? ?\d?|classif(y|ies|ied|ication)|criticality|critical|sensitivity|"
    r"risk (rating|level|assessment|score|tier)s?|high[- ]risk|low[- ]risk|medium[- ]risk|"
    r"privileged|impact level|data classification)\b",
    re.I,
)
_REASSESS = re.compile(
    r"\b(revisit(s|ed)?|reassess(es|ed|ment)?|re-?evaluat(e|es|ed|ion)|re-?tier(s|ed)?|recalibrat(e|es|ed)|"
    r"(tiers?|tiering|ratings?|classifications?) (is|are) (reviewed|updated)|updated (after|when|annually|each))\b",
    re.I,
)


def _risk_based(text: str) -> tuple[float, str, list[str]]:
    """How far the statement turns a risk-based policy into a concrete schedule. Returns (score, note, tips)."""
    tips: list[str] = []
    basis = _distinct(_RISK_BASIS, text)
    schedule = sum(len(v) for v in commitments(text).values()) + len(_distinct(_FREQUENCY, text) - {"upon"})
    mapped = 1.0 if basis and schedule >= 2 else 0.5 if (basis and schedule) or schedule >= 2 else 0.0
    owner = 0.5 * bool(_ROLES.search(text)) + 0.5 * bool(_REASSESS.search(text))
    if not basis:
        vague = _distinct(_RISK_BASED, text)
        said = f"'{sorted(vague)[0]}' without saying how risk is rated; " if vague else ""
        tips.append(f"The policy is risk-based: {said}say how items are rated (tiers, classification or "
                    "criticality).")
    if mapped < 1:
        tips.append("Give each risk tier its own frequency or time limit.")
    if owner < 1:
        tips.append("Say who sets the risk tiers and when they are revisited.")
    score = (bool(basis) + mapped + owner) / 3
    return score, f"risk basis {'named' if basis else 'missing'}, schedule per tier {mapped:.0%}, " \
                  f"tier ownership {owner:.0%}", tips


def _policy_intent(intent: str, text: str) -> tuple[float, str, list[str]]:
    """Score how far the statement meets the policy intent. Returns (score, note, improvements).

    Fixed commitments in the intent (how often, time limits, retention) must be
    kept; a risk-based intent must be turned into a concrete schedule by risk.
    """
    required, found = commitments(intent), commitments(text)
    # Words inside a commitment ("retained for 3 years") are scored as commitments, not terms.
    phrases = " ".join(p for kind in required.values() for _, p in kind)
    intent_words = {k: w for k, w in _term_words(intent).items()
                    if k not in _terms(phrases) and k not in _terms(" ".join(_distinct(_RISK_BASED, intent)))}
    matched = set(intent_words) & _terms(text)
    term_score = min(1.0, (len(matched) / len(intent_words)) / 0.5) if intent_words else 1.0
    tips: list[str] = []
    if term_score < 0.6:
        tips.append("Show how the statement meets the policy intent (missing terms: "
                    + _missing(intent_words, matched) + ").")

    met = total = short = 0
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
                short += 1
                pick = max if kind == "retention" else min
                tips.insert(0, f'Policy requires "{phrase}"; the statement says "{pick(have)[1]}".')
            else:
                tips.insert(0, f'Policy requires "{phrase}"; the statement {_OMITTED[kind]}.')

    parts = []  # (score, weight) of each thing the intent asks for beyond its terms
    notes = [f"{len(matched)}/{len(intent_words)} intent terms"]
    if total:
        # Falling short of a commitment counts against the statement; leaving one out only earns nothing.
        parts.append(max(0.0, (met - 0.5 * short) / total))
        notes.append(f"{met}/{total} policy commitments met" + (f", {short} fallen short of" if short else ""))
    if _RISK_BASED.search(intent):
        rb_score, rb_note, rb_tips = _risk_based(text)
        parts.append(rb_score)
        notes.append(rb_note)
        tips += rb_tips
    score = 0.4 * term_score + 0.6 * (sum(parts) / len(parts)) if parts else term_score
    return score, ", ".join(notes), tips


def _open_examples(text: str) -> list[str]:
    found = {e.rstrip(".") + ("." if e.lower().startswith(("e.g", "etc")) else "")
             for e in _distinct(_OPEN_EXAMPLES, text)}
    return sorted(found) if found and not _DEFINED_SET.search(text) else []


def _quote(phrases: list[str]) -> str:
    return "'" + "', '".join(phrases) + "'"


_SAY_INSTEAD = {
    IMPLEMENTATION: "what actually happens",
    RISK_STATEMENT: "what was found",
    RECOMMENDATION: "the specific action to take",
}


def _wording(text: str, rules: tuple[str, ...], instead: str = "what actually happens") -> tuple[list[str], list[str]]:
    """Wording that does not belong in this kind of text: (phrases, improvements)."""
    phrases: list[str] = []
    improvements: list[str] = []
    if "vague" in rules:
        found = sorted(_distinct(_VAGUE, text))
        if found:
            phrases += found
            improvements.append(f"Replace vague wording ({', '.join(found)}) with {instead}.")
    if "modals" in rules:
        found = sorted(_distinct(_MODALS, text))
        if found:
            phrases += found
            improvements.append(f"Replace {_quote(found)} with {instead}.")
    if "obligations" in rules:
        found = sorted(_distinct(_OBLIGATIONS, text))
        if found:
            phrases += found
            improvements.append(f"{_quote(found)} {'restate' if len(found) > 1 else 'restates'} the requirement; "
                                "describe what enforces it and what happens today.")
    if "weak_actions" in rules:
        found = sorted(_distinct(_WEAK_ACTIONS, text))
        if found:
            phrases += found
            improvements.append(f"{_quote(found)} {'make' if len(found) > 1 else 'makes'} the action optional; "
                                "state the action to take.")
    if "examples" in rules:
        found = _open_examples(text)
        if found:
            phrases += found
            improvements.append(f"{_quote(found)} {'leave' if len(found) > 1 else 'leaves'} the scope open; "
                                "list the full set or say where it is defined.")
    return phrases, improvements


def _finish(statement: Statement, criteria: list[CriterionResult], improvements: Improvements,
            wording_rules: tuple[str, ...], caps: list[tuple[float, str]] | None = None,
            placeholder_msg: str = "Replace the placeholder with real text.") -> Assessment:
    """Weight the criteria, apply wording reductions and caps, and build the assessment."""
    text = statement.text.strip()
    total_weight = sum(c.weight for c in criteria)
    for c in criteria:
        c.weight /= total_weight
    confidence = sum(c.score * c.weight for c in criteria)
    notes: list[str] = []

    for cap, reason in caps or []:
        if confidence > cap:
            confidence = cap
            notes.append(f"{reason}; limited to {cap:.0%}")

    wording = WORDING_PRACTICE[statement.kind]
    phrases, wording_improvements = _wording(text, wording_rules, _SAY_INSTEAD[statement.kind])
    improvements.extend(wording, wording_improvements)
    factor = 1.0
    if phrases:
        factor = max(WORDING_FLOOR, 1.0 - WORDING_PENALTY * len(phrases))
        confidence *= factor
        notes.append(f"wording ({', '.join(phrases)}) reduced confidence by {1 - factor:.0%}")

    placeholder = not text or _PLACEHOLDER.search(text)
    if placeholder:
        confidence = min(confidence, PLACEHOLDER_CAP)
        notes.append(f"placeholder or empty text; limited to {PLACEHOLDER_CAP:.0%}")
        improvements.first(wording, placeholder_msg)

    # Wording is scored as a multiplier above, so its practice carries no weight of its own:
    # it is listed so the checklist and the improvements always agree.
    planned = statement.kind == IMPLEMENTATION and _PLANNED.search(text)
    wording_score = 0.0 if placeholder else factor * (PLANNED_CAP if planned else 1.0)
    criteria.append(CriterionResult(wording, wording_score, 0.0,
                                    ", ".join(phrases) if phrases else ("placeholder" if placeholder else "clear")))
    for c in criteria:
        c.issues = improvements.of(c.name)

    rationale = f"Rubric score {confidence:.0%}" + (f"; {'; '.join(notes)}" if notes else "") + "."
    return Assessment(statement, round(confidence, 4), criteria, improvements.texts, rationale)


def _signal(name: str, pattern: re.Pattern, text: str, full_at: int, weight: float) -> CriterionResult:
    hits = _distinct(pattern, text)
    return CriterionResult(name, _ratio(len(hits), full_at), weight, ", ".join(sorted(hits)) or "none found")


# --- Implementation statements ---------------------------------------------------------------

def assess_implementation(statement: Statement) -> Assessment:
    text = statement.text.strip()
    words = len(text.split())
    criteria: list[CriterionResult] = []
    improvements = Improvements()

    substance = 0.0 if words < 12 else min(1.0, (words - 12) / 38 + 0.25)
    criteria.append(CriterionResult("substance", substance, WEIGHTS["substance"], f"{words} words"))
    if words < 25:
        improvements.add("substance", "Statement is too brief to show how the control is met.")

    for name, pattern, full_at, tip in (
        ("responsibility", _ROLES, 1, "Name the role or team responsible for performing the control."),
        ("mechanism", _MECHANISMS, 2, "Describe the specific tool, configuration or process that implements it."),
        ("frequency", _FREQUENCY, 1, "State how often or on what trigger the control operates."),
        ("evidence", _EVIDENCE, 2, "Say what records or artefacts prove the control operated."),
    ):
        c = _signal(name, pattern, text, full_at, WEIGHTS[name])
        criteria.append(c)
        if c.score < 0.5:
            improvements.add(name, tip)

    if statement.requirement:
        req_words = _term_words(statement.requirement)
        matched = set(req_words) & _terms(text)
        score = min(1.0, (len(matched) / len(req_words) if req_words else 1.0) / 0.4)
        criteria.append(CriterionResult("coverage", score, WEIGHTS["coverage"],
                                        f"{len(matched)}/{len(req_words)} requirement terms addressed"))
        if score < 0.6:
            improvements.add("coverage", "Address more of the control requirement (missing terms: "
                                + _missing(req_words, matched) + ").")

    caps: list[tuple[float, str]] = []
    if statement.policy_intent:
        score, note, intent_tips = _policy_intent(statement.policy_intent, text)
        criteria.append(CriterionResult("policy_intent", score, WEIGHTS["policy_intent"], note))
        improvements.extend("policy_intent", intent_tips)
    if _PLANNED.search(text):
        caps.append((PLANNED_CAP, "describes planned rather than implemented work"))
        improvements.add("implemented", "Describe what is implemented today, not what is planned.")

    return _finish(statement, criteria, improvements, ("vague", "modals", "obligations", "examples"), caps,
                   "Replace the placeholder with a real implementation statement.")


# --- Risk statements -------------------------------------------------------------------------

RISK_WEIGHTS = {
    "condition": 0.20, "impact": 0.20, "cause": 0.15, "threat": 0.15,
    "scope": 0.10, "criteria": 0.10, "rating": 0.10,
}
_CONDITION = re.compile(
    r"\b(\d+ (of|out of) \d+|\d+(\.\d+)?%|found|identified|observed|noted|sampled|tested|inspected|"
    r"no evidence|not (configured|enabled|enforced|performed|reviewed|disabled|removed|documented|implemented|"
    r"patched|encrypted|logged|monitored)|did not|does not|do not|were not|was not|lacks?|missing|absent|"
    r"exceeded|overdue|outdated|unpatched|remain(s|ed)? (active|enabled|open))\b",
    re.I,
)
_CRITERIA_REF = re.compile(
    r"\b[a-z]{2}-\d+(\(\d+\))?\b|\b(policy|standard|requirement|required by|baseline|benchmark|procedure|"
    r"control objective)\b",
    re.I,
)
_CAUSE = re.compile(
    r"\b(because|due to|as a result of|caused by|root cause|owing to|stems? from|result(s|ed)? from|"
    r"attributable to|lack of|no (defined |documented )?(process|procedure|owner|automation|integration)|"
    r"manual(ly)?|not integrated)\b",
    re.I,
)
_THREAT = re.compile(
    r"\b(attackers?|adversar(y|ies)|threat actors?|malicious|insiders?|former (employees?|staff|contractors?)|"
    r"unauthori[sz]ed (users?|persons?|parties|individuals?)|cybercriminals?|ransomware|phishing|"
    r"exploit(s|ed|ation)?|compromis(e|ed)|abuse|misuse|fraudsters?)\b",
    re.I,
)
_LIKELIHOOD = re.compile(
    r"\b(likel(y|ihood)|probabilit(y|ies)|frequent(ly)?|exposed|internet-facing|publicly (accessible|exposed)|"
    r"known exploit|actively exploited|easily|trivial(ly)?)\b",
    re.I,
)
_IMPACT = re.compile(
    r"\b(confidentiality|integrity|availability|disclos(e|ed|ure)|unauthori[sz]ed (access|changes?|payments?|"
    r"transactions?|disclosure)|data (loss|breach|leak(age)?)|breach(es)?|fraud(ulent)?|financial (loss|impact)|"
    r"outages?|downtime|disruption|regulatory|fines?|penalt(y|ies)|reputation(al)?|customers?|cardholder|"
    r"personal data|sensitive data|loss of|tamper(ing|ed)?)\b",
    re.I,
)
_SCOPE = re.compile(
    r"\b(\d+ (accounts?|systems?|servers?|users?|hosts?|records?|endpoints?|applications?)|accounts?|systems?|"
    r"servers?|applications?|databases?|endpoints?|users?|records?|environments?|production|workloads?|hosts?|"
    r"instances?|repositor(y|ies)|subnets?|buckets?|laptops?|devices?)\b",
    re.I,
)
_SEVERE = re.compile(
    r"\b(breach|fraud(ulent)?|payments?|cardholder|customer data|personal data|regulatory|privileged|"
    r"administrator|admin|production|outage|ransomware)\b",
    re.I,
)
_REMEDY = re.compile(
    r"\b(recommend(s|ed|ation)?|(should|must|needs? to)\s+(?!have\b)\w+|to remediate|remediat(e|ion)|"
    r"we suggest|it is advised)\b",
    re.I,
)
_LOW = re.compile(r"^\s*(very[- ]?low|low|minimal|negligible|1|2)\s*$", re.I)


def _criteria_met(statement: Statement, weight: float, improvements: Improvements) -> CriterionResult:
    """Does the risk statement name the requirement it fails, and describe it in the control's or policy's terms?"""
    text = statement.text
    named = _distinct(_CRITERIA_REF, text)
    reference = " ".join(t for t in (statement.requirement, statement.policy_intent) if t)
    if not reference:
        if not named:
            improvements.add("criteria", "Name the control or policy requirement that is not met.")
        return CriterionResult("criteria", float(bool(named)), weight, ", ".join(sorted(named)) or "none found")

    words = _term_words(reference)
    matched = set(words) & _terms(text)
    overlap = min(1.0, (len(matched) / len(words) if words else 1.0) / 0.25)
    score = 0.5 * bool(named) + 0.5 * overlap
    sources = " and ".join(n for n, t in (("control", statement.requirement), ("policy", statement.policy_intent)) if t)
    if not named:
        improvements.add("criteria", "Name the control or policy requirement that is not met.")
    if overlap < 0.6:
        verb = "require" if " and " in sources else "requires"
        improvements.add("criteria", f"Describe the condition against what the {sources} {verb} "
                            f"(missing terms: {_missing(words, matched)}).")
    note = (", ".join(sorted(named)) or "no requirement named") + f"; {len(matched)}/{len(words)} {sources} terms"
    return CriterionResult("criteria", score, weight, note)


def assess_risk_statement(statement: Statement) -> Assessment:
    """Does the risk statement say what is wrong, why, who could exploit it, and what it would cost?"""
    text = statement.text.strip()
    w = RISK_WEIGHTS
    improvements = Improvements()
    criteria = [
        _signal("condition", _CONDITION, text, 2, w["condition"]),
        _criteria_met(statement, w["criteria"], improvements),
        _signal("cause", _CAUSE, text, 1, w["cause"]),
    ]
    threat = _distinct(_THREAT, text)
    likelihood = _distinct(_LIKELIHOOD, text) or ({"rated"} if "likelihood" in statement.ratings else set())
    criteria.append(CriterionResult("threat", 0.5 * bool(threat) + 0.5 * bool(likelihood), w["threat"],
                                    ", ".join(sorted(threat | likelihood)) or "none found"))
    criteria.append(_signal("impact", _IMPACT, text, 2, w["impact"]))
    scope = _distinct(_SCOPE, text) | _distinct(_MECHANISMS, text)
    criteria.append(CriterionResult("scope", _ratio(len(scope), 2), w["scope"],
                                    ", ".join(sorted(scope)) or "none found"))

    tips = {
        "condition": "State the condition as fact, with the evidence found (for example '14 of 60 sampled "
                     "accounts belonged to leavers').",
        "cause": "Explain the cause, so the recommendation can address it.",
        "impact": "Describe the impact on this system: which data or service, and the effect on "
                  "confidentiality, integrity, availability or the business.",
        "scope": "Say which systems, accounts or components are affected, and how many.",
    }
    for c in criteria:
        if c.name in tips and c.score < 0.5:
            improvements.add(c.name, tips[c.name])
    if not threat:
        improvements.add("threat", "Name the threat: who or what could exploit the weakness.")
    if not likelihood:
        improvements.add("threat", "Say how likely exploitation is, or record a likelihood rating.")

    r = statement.ratings
    rated = (("likelihood" in r) + ("impact" in r or "risk" in r)) / 2
    note = ", ".join(f"{k}={v}" for k, v in r.items()) or "no characterization facets"
    severe = sorted(_distinct(_SEVERE, text))
    level = r.get("risk") or r.get("impact")
    if level and _LOW.match(level) and len(severe) >= 2:
        rated = min(rated, 0.5)
        improvements.add("rating", f"Rated '{level}' but describes {', '.join(severe)}; check the rating matches "
                            "the statement.")
    elif rated < 1:
        improvements.add("rating", "Record likelihood and impact in the risk's characterizations.")
    criteria.append(CriterionResult("rating", rated, w["rating"], note))

    if _REMEDY.search(text):
        improvements.add("clarity", "Move the remediation out of the risk statement and into a recommendation.")
    if len(text.split()) < 20:
        improvements.first("condition", "Risk statement is too brief to explain the risk.")

    return _finish(statement, criteria, improvements, ("vague", "examples"),
                   placeholder_msg="Replace the placeholder with a real risk statement.")


# --- Recommendations ------------------------------------------------------------------------

RECOMMENDATION_WEIGHTS = {
    "actionable": 0.20, "root_cause": 0.20, "specific": 0.15,
    "owner": 0.15, "timeline": 0.15, "completion": 0.15,
}
_ACTION_VERBS = set("""
    add apply assign automate block configure conduct create decommission define delete deploy disable document
    enable encrypt enforce establish implement integrate isolate migrate monitor patch perform reconcile
    reduce remove replace require restrict retire revoke rotate schedule segment train update upgrade
    validate verify
""".split())
_DIRECTIVE = re.compile(r"\b(should|must|needs? to|is required to|are required to)\s+(be\s+)?\w+", re.I)
_DATE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{4}|"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{4}|q[1-4] \d{4}|by (end of |the end of )?"
    r"(q[1-4]|\w+ \d{4})|within \d+ (days?|weeks?|months?))\b",
    re.I,
)
_COMPLETION = re.compile(
    r"\b(verif(y|ied|ication)|validat(e|ed|ion)|confirm(ed|ation)?|re-?test(ed|ing)?|evidence|"
    r"demonstrat(e|ed)|closure|close (the|this) (finding|risk)|until|attest(ation)?|sign-?off|"
    r"report(ed)? (back|to)|screenshots?|export)\b",
    re.I,
)
_CAUSE_CLAUSE = re.compile(
    r"\b(?:because|due to|as a result of|caused by|root cause(?: is| was)?|owing to|stems? from|"
    r"result(?:s|ed)? from|attributable to)\b([^.;]*)",
    re.I,
)


def _starts_with_action(text: str) -> bool:
    for sentence in re.split(r"(?<=[.;:])\s+", text):
        first = re.sub(r"[^a-z]", "", sentence.strip().split(" ")[0].lower()) if sentence.strip() else ""
        if first in _ACTION_VERBS:
            return True
    return False


def assess_recommendation(statement: Statement) -> Assessment:
    """Is the recommendation an owned, dated action that fixes the cause and says how closure is shown?"""
    text = statement.text.strip()
    w = RECOMMENDATION_WEIGHTS
    criteria: list[CriterionResult] = []
    improvements = Improvements()

    if _starts_with_action(text):
        criteria.append(CriterionResult("actionable", 1.0, w["actionable"], "starts with an action"))
    elif _DIRECTIVE.search(text):
        criteria.append(CriterionResult("actionable", 0.7, w["actionable"], "directive, not imperative"))
        improvements.add("actionable", "Lead with the action itself ('Disable ...', 'Configure ...').")
    else:
        criteria.append(CriterionResult("actionable", 0.2, w["actionable"], "no clear action"))
        improvements.add("actionable", "State a concrete action, starting with a verb ('Disable ...', 'Configure ...').")

    if statement.risk_statement:
        causes = " ".join(m.group(1) for m in _CAUSE_CLAUSE.finditer(statement.risk_statement))
        basis = causes or statement.risk_statement
        words = _term_words(basis)
        matched = set(words) & _terms(text)
        score = min(1.0, (len(matched) / len(words) if words else 1.0) / 0.4)
        criteria.append(CriterionResult("root_cause", score, w["root_cause"],
                                        f"{len(matched)}/{len(words)} {'cause' if causes else 'risk'} terms"))
        if score < 0.6:
            what = "the cause identified in the risk statement" if causes else "the risk statement"
            improvements.add("root_cause", f"Address {what} (missing: {_missing(words, matched)}).")

    specific = _distinct(_MECHANISMS, text) | _distinct(_SCOPE, text)
    criteria.append(CriterionResult("specific", _ratio(len(specific), 2), w["specific"],
                                    ", ".join(sorted(specific)) or "none found"))
    if len(specific) < 2:
        improvements.add("specific", "Name the system, setting or process to change.")

    if statement.owner:
        criteria.append(CriterionResult("owner", 1.0, w["owner"], f"recorded: {statement.owner}"))
    else:
        c = _signal("owner", _ROLES, text, 1, w["owner"])
        criteria.append(c)
        if c.score < 1:
            improvements.add("owner", "Name who is accountable for the action.")

    if statement.deadline:
        criteria.append(CriterionResult("timeline", 1.0, w["timeline"], f"recorded: {statement.deadline}"))
    else:
        c = _signal("timeline", _DATE, text, 1, w["timeline"])
        criteria.append(c)
        if c.score < 1:
            rating = ", ".join(f"{k} {v}" for k, v in statement.ratings.items())
            improvements.add("timeline", "Set a target date in proportion to the risk"
                                + (f" ({rating})." if rating else "."))

    done = _distinct(_COMPLETION, text)
    criteria.append(CriterionResult("completion", _ratio(len(done), 1), w["completion"],
                                    ", ".join(sorted(done)) or "none found"))
    if not done:
        improvements.add("completion", "Say what evidence will show the action is complete, so the risk can be closed.")

    return _finish(statement, criteria, improvements, ("vague", "weak_actions", "examples"),
                   placeholder_msg="Replace the placeholder with a real recommendation.")


def assess(statement: Statement) -> Assessment:
    return {
        RISK_STATEMENT: assess_risk_statement,
        RECOMMENDATION: assess_recommendation,
    }.get(statement.kind, assess_implementation)(statement)
