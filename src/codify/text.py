"""Shared text checks: wording, commitments, policy intent, coverage of a control's parts.

These are the parts of the rubric that control statements are scored with
(carried over from Vitals, the health check Codify replaces).
"""

from __future__ import annotations

import re

from .models import Assessment, CriterionResult, Statement


# The practice that wording and placeholders count against.
WORDING_PRACTICE = "firm"


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


PLACEHOLDER_CAP = 0.20


TOLERANCE = 1.05  # "every 90 days" meets "quarterly"


_PLACEHOLDER = re.compile(
    r"\b(tbd|tbc|todo|to be (determined|confirmed|completed)|lorem ipsum|n/?a|placeholder|fill in)\b|\[insert|<[^>]+>",
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
_MODALS = re.compile(r"\b(may(?![ ,]+\d)(?<!\d may)|might|could|should)\b", re.I)  # not "1 May 2013"


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
    r"department|hr|human resources|lead|director|responsible|accountable|(cloud )?service providers?|csps?)\b",
    re.I,
)


_FREQUENCY = re.compile(
    r"\b(hourly|daily|weekly|fortnightly|monthly|quarterly|semi-?annually|annually|yearly|"
    r"every \d+|(each|every) (business |working )?(day|week|month|quarter|year)|within \d+|"
    r"\d+ (minutes?|hours?|days?|weeks?|months?)|(every|each) (monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|weekday|night|morning)|"
    r"real[- ]time|continuous(ly)?|on (each|every)|upon|prior to|before|immediately|"
    r"at least (once|every)|at login|at each|whenever|as (it|they) (occurs?|happens?)|"
    r"(all|every|each) (\w+ ){0,3}events?)\b",
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


# Top-level parts of a control, as catalogs label them: "a. Define ...; b. Assign ...".
_PART_LABEL = re.compile(r"(?:^|(?<=[;:.]\s)|(?<=\band\s)|(?<=\bor\s))([a-z])\.\s", re.M)


# Organization-defined parameters say nothing a statement has to repeat word for word.
_PARAM_TEXT = re.compile(r"\[(assignment|selection)[^\]]*\]", re.I)


def requirement_parts(requirement: str) -> list[tuple[str, str]]:
    """(label, text) for each lettered part of a control, a, b, c in order; one unlabelled part otherwise."""
    marks = [m for m in _PART_LABEL.finditer(requirement)]
    run: list[re.Match] = []
    for m in marks:  # keep the run a, b, c, ... and skip stray letters ("item e." inside a part)
        if ord(m.group(1)) - ord("a") == len(run):
            run.append(m)
    if len(run) < 2:
        return [("", requirement)]
    return [(m.group(1), requirement[m.end():(run[i + 1].start() if i + 1 < len(run) else len(requirement))])
            for i, m in enumerate(run)]


def requirement_coverage(requirement: str, text: str) -> tuple[float, str, list[str]]:
    """How much of the control requirement the statement addresses. Returns (score, note, improvements).

    A control with lettered parts is checked part by part: a part counts when the statement uses a word
    only that part has, or a good share of the part's words. A single-part control is checked on its words.
    """
    present = _terms(text)
    parts = requirement_parts(requirement)
    if len(parts) == 1:
        req_words = _term_words(_PARAM_TEXT.sub(" ", requirement))
        matched = set(req_words) & present
        score = min(1.0, (len(matched) / len(req_words) if req_words else 1.0) / 0.4)
        tips = [] if score >= 0.6 else ["Address more of the control requirement (missing terms: "
                                        + _missing(req_words, matched) + ")."]
        return score, f"{len(matched)}/{len(req_words)} requirement terms addressed", tips

    words = [_term_words(_PARAM_TEXT.sub(" ", body)) for _, body in parts]
    covered, missing = [], []
    for i, (label, body) in enumerate(parts):
        others = set().union(*(set(w) for j, w in enumerate(words) if j != i))
        own = set(words[i]) - others
        hit = set(words[i]) & present
        if (own & present) or (words[i] and len(hit) / len(words[i]) >= 0.4):
            covered.append(label)
        else:
            missing.append((label, body))
    score = len(covered) / len(parts)
    tips = []
    if missing:
        listed = "; ".join(f"{label} ({_opening_words(body)})" for label, body in missing[:4])
        more = f", and {len(missing) - 4} more" if len(missing) > 4 else ""
        tips.append(f"Address every part of the control. Not addressed: part{'s' if len(missing) > 1 else ''} "
                    f"{listed}{more}.")
    note = f"{len(covered)} of {len(parts)} parts addressed" + (f" ({', '.join(covered)})" if covered else "")
    return score, note, tips


def _opening_words(text: str, n: int = 6) -> str:
    text = re.sub(r"[\s;,]*\b(and|or)?[\s;,.]*$", "", _PARAM_TEXT.sub("…", text))
    words = text.strip(" ;,.").split()
    return " ".join(words[:n]) + ("…" if len(words) > n else "")


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
    text = re.sub(r"\[(\d+(?:\.\d+)?)\]", r"\1", text)  # a filled-in parameter: "within [5] business days"
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

    wording = WORDING_PRACTICE
    phrases, wording_improvements = _wording(text, wording_rules, "what must be done")
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
    wording_score = 0.0 if placeholder else factor
    criteria.append(CriterionResult(wording, wording_score, 0.0,
                                    ", ".join(phrases) if phrases else ("placeholder" if placeholder else "clear")))
    for c in criteria:
        c.issues = improvements.of(c.name)

    rationale = f"Rubric score {confidence:.0%}" + (f"; {'; '.join(notes)}" if notes else "") + "."
    return Assessment(statement, round(confidence, 4), criteria, improvements.texts, rationale)

