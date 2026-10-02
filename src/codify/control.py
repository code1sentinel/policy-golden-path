"""Control statements: the requirement itself, written action-first and testable.

A control statement says what must be done, not who does it or with what:

    Back up all important data and systems at least every [N] day(s), and store
    backups in a secure and separate location.

It starts with the action, names no product (tools belong in guidance, or
with however the organization implements it), says what it applies to, can
be tested, and says why. How the organization meets it, with which tools and
people, is a separate concern, checked elsewhere.

A handful of criteria draw on OSCAL's own authoring conventions for a catalog
control: joined requirements get their own lettered, referenceable parts
(`labeled_parts`), as a catalog's own `statement`/`item` parts do; and a
requirement should be written so an assessor can determine pass or fail, not
left to a subjective judgment call (`determinable`), the way a NIST SP 800-53A
assessment objective is.
"""

from __future__ import annotations

import re

from .text import (
    Improvements, _distinct, _finish, _policy_intent, _term_words, _terms, commitments, requirement_coverage,
    requirement_parts,
)
from .models import Assessment, CriterionResult, Statement

WEIGHTS = {
    "action_first": 0.15, "tool_neutral": 0.10, "scope": 0.20, "testable": 0.25,
    "purpose": 0.10, "single": 0.05, "coverage": 0.15, "policy_intent": 0.20,
    "labeled_parts": 0.05, "determinable": 0.05,
}

# Verbs a requirement can open with: the usual control verbs.
VERBS = set("""
    adopt allow analyse analyze apply approve archive assess assign audit authenticate authorise authorize automate
    back backup block build calibrate centralise centralize change check classify collect conduct configure confirm
    contain control create decommission define delete deny deploy destroy detect develop disable dispose document
    encrypt enable enforce engage ensure escalate establish evaluate filter generate get grant harden host identify
    implement inform install inspect integrate investigate isolate keep label limit lint lock log maintain manage
    mask measure minimise minimize monitor notify obtain operate patch perform pin place plan prevent prohibit
    protect provide publish rate-limit reconcile record recover redact register reject release remediate remove
    renew replace report require respond restore restrict retain retire review revoke rotate route run sanitise
    sanitize scan schedule secure segment segregate send separate set share sign store submit synchronise
    synchronize terminate test track train triage update upgrade use validate verify witness
    take carry complete follow escort wipe erase shred reset comply enrol enroll attend print
""".split())
# A requirement may lead with an adverb or a condition before its verb: "Only allow...", "Where X, restrict...".
_LEAD_ADVERB = re.compile(r"^(only|physically|securely|automatically|centrally|immediately|promptly|regularly|"
                          r"continuously|always|never|strictly)\s+", re.I)
_CONDITION = re.compile(r"^(where|when|if|for|before|after|unless|in the event)\b[^,]{1,120},\s*", re.I)
# Openings that put a subject first: "The team...", "Users are...", "We...".
_SUBJECT = re.compile(r"^(the|our|we|it|this|these|those|all|each|every|any|staff|users?|employees?|managers?|"
                      r"administrators?|admins?|teams?|[a-z]+ (team|officer|owner|manager)s?)\b", re.I)

# Products and vendors: these belong in guidance, or wherever the control is implemented.
_PRODUCTS = re.compile(
    r"\b(okta|splunk|crowdstrike|falcon|microsoft|defender|entra|azure|intune|office 365|m365|sharepoint|"
    r"aws|amazon|s3|ec2|ecs|eks|lambda|dynamodb|cloudfront|cloudtrail|guardduty|google cloud|gcp|"
    r"veeam|servicenow|jira|confluence|sailpoint|sap|tenable|qualys|nessus|papercut|workday|github|gitlab|"
    r"bitbucket|jenkins|terraform|ansible|jamf|palo alto|fortinet|fortigate|cisco|cloudflare|zscaler|datadog|"
    r"pagerduty|slack|singpass|corppass|salesforce|oracle|vmware|kaspersky|symantec|sophos|trend micro)\b",
    re.I,
)
# Activities that recur, so the requirement has to say how often.
_RECURRING = re.compile(r"\b(review(s|ed)?|test(s|ed|ing)?|scan(s|ned)?|back(s|ed)? ?up|backups?|rotated?|audit(ed)?|"
                        r"assess(ed)?|reconcil(e|ed)|recertif(y|ied)|train(ed)?|patch(es|ed)?|renew(ed)?|exercised?|"
                        r"re-?evaluated?)\b"
                        # used as a noun ("audit events", "patch management tools"), not an activity
                        r"(?!\s+(events?|logs?|trails?|records?|management|tools?|results?|reports?|plans?|"
                        r"data|jobs?|coverage|findings))", re.I)
# Wording that sounds like a frequency but sets none.
_VAGUE_FREQUENCY = re.compile(r"\b(regularly|periodically|timely|promptly|from time to time|as soon as possible|"
                              r"routinely|frequently)\b", re.I)
# Wording that already says how often: it never stops.
_CONTINUOUS = re.compile(r"\b(continuous(ly)?|real[- ]time|automated|automatically|always|at all times)\b", re.I)
# Object words that say nothing about scope.
_GENERIC = set("""security measures controls control appropriate necessary relevant processes process things
    protection safeguards steps actions practices requirements best practice mechanisms solutions""".split())
_SCOPE_QUANTIFIER = re.compile(r"\b(all|every|each|any|only|no|never)\b", re.I)
_SCOPE_QUALIFIER = re.compile(
    r"\b(internet[- ]facing|public(ly)?[- ]?(facing|accessible)?|privileged|critical|production|sensitive|personal|"
    r"confidential|classified|remote|external|third[- ]party|administrative|default|high[- ]risk|important)\b",
    re.I,
)
# Something an assessor can test: a parameter left for the organization, a trigger or an absolute.
_PARAMETER = re.compile(r"\{\{\s*insert:\s*param|\[(assignment|selection)\b|\[[^\]]{1,40}\]", re.I)
_TRIGGER = re.compile(r"\b(before|after|upon|on (each|every)|at (each|every)|prior to|whenever|when(ever)? a|"
                      r"above|below|more than|less than|at least|no (more|later) than|exceeds?)\b", re.I)
_PURPOSE = re.compile(r"\b(to (ensure|prevent|protect|deter|detect|reduce|limit|contain|avoid|maintain|identify|"
                      r"minimi[sz]e|mitigate|help|enable|allow|support|preserve|guard|stop|block|restore)|"
                      r"so that|in order to|against)\b", re.I)
_CLAUSE = re.compile(r"([\w-]+)(?:,\s*(?:and\s+|or\s+)?|;\s*(?:and\s+)?|\s+and\s+)(\w+)", re.I)
# "a secure and separate location": a word joined to an adjective or verb is describing, not a new action.
_ADJECTIVE = re.compile(r"(al|ive|ous|ible|able|ful|less|ic|ary|ed|ing)$|^(secure|safe|separate|clear|strong|"
                        r"complete|accurate|current|valid)$", re.I)
# Evaluative words with no fixed test: an assessor cannot determine pass or fail against them on their own,
# the way a NIST SP 800-53A assessment objective must be determinable (OSCAL catalogs write to the same end).
_SUBJECTIVE = re.compile(
    r"\b(robust|effective(ly)?|adequate(ly)?|sufficient(ly)?|suitable|reasonable|sound|appropriate|proper(ly)?|"
    r"industry[- ]standard|best[- ]practice|state[- ]of[- ]the[- ]art)\b",
    re.I,
)


def _opening(text: str) -> str:
    """The first sentence with any leading condition or adverb removed."""
    first = re.split(r"(?<=[.;])\s+", text.strip(), maxsplit=1)[0]
    first = _CONDITION.sub("", first)
    return _LEAD_ADVERB.sub("", first)


def _first_word(text: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z-]*", text)
    return words[0].lower() if words else ""


def _object_words(opening: str) -> list[str]:
    """The content words of what the requirement acts on: after the verb, before any purpose clause."""
    body = re.split(r"\b(?:to|so that|in order to)\s+(?:ensure|prevent|protect|deter|detect|reduce|limit|help|"
                    r"mitigate|avoid|maintain|identify|minimi[sz]e)\b", opening, maxsplit=1, flags=re.I)[0]
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z-]+", body)[1:]]
    return [w for w in _term_words(" ".join(words)).values() if w not in _GENERIC and w not in VERBS]


def _actions(text: str) -> list[str]:
    """The distinct requirements joined in the statement: its opening verb, and each 'and <verb>' after it."""
    opening = _opening(text)
    found = [_first_word(opening)] if _first_word(opening) in VERBS else []
    for m in _CLAUSE.finditer(text):
        before, word = m.group(1).lower(), m.group(2).lower()
        if word in VERBS and before not in VERBS and not _ADJECTIVE.search(before):
            found.append(word)
    return found


def assess_control_statement(statement: Statement) -> Assessment:
    text = statement.text.strip()
    improvements = Improvements()
    criteria: list[CriterionResult] = []

    # action_first: "Back up...", not "The team backs up...".
    opening = _opening(text)
    first = _first_word(opening)
    if first in VERBS:
        action_first, note = 1.0, f"starts with '{first}'"
    elif _PRODUCTS.match(opening) or _SUBJECT.match(opening) or re.match(r"^\w+ (is|are|will|shall|must|should)\b", opening, re.I):
        action_first, note = 0.0, f"starts with the subject ('{' '.join(opening.split()[:2])}')"
        improvements.add("action_first", "Start with the action (Back up, Encrypt, Restrict), not who does it: "
                                         "that belongs with how the control is implemented, not the requirement.")
    else:
        action_first, note = 0.5, f"starts with '{first}'"
        improvements.add("action_first", "Start with the verb for what must be done (Back up, Encrypt, Restrict).")
    criteria.append(CriterionResult("action_first", action_first, WEIGHTS["action_first"], note))

    # tool_neutral: products belong in guidance, or wherever the control is implemented.
    products = sorted(_distinct(_PRODUCTS, text))
    criteria.append(CriterionResult("tool_neutral", 0.3 if products else 1.0, WEIGHTS["tool_neutral"],
                                    ", ".join(products) or "no products named"))
    if products:
        improvements.add("tool_neutral", f"Names {', '.join(products)}: say what must be achieved, and move the "
                                         "product to guidance or wherever the control is implemented.")

    # scope: what it applies to. A qualified object is best; any concrete object will do; generic words
    # ("security", "measures") leave nobody able to tell what is in scope.
    qualifiers = sorted(_distinct(_SCOPE_QUANTIFIER, text) | _distinct(_SCOPE_QUALIFIER, text))
    objects = _object_words(opening)
    if qualifiers and objects:
        scope, note = 1.0, ", ".join(qualifiers[:3] + objects[:3])
    elif objects:
        scope, note = 0.8, ", ".join(objects[:4])
    else:
        scope, note = 0.3, "no concrete object"
        improvements.add("scope", "Say exactly what it applies to (all internet-facing systems, privileged "
                                  "accounts, payments above a threshold).")
    criteria.append(CriterionResult("scope", scope, WEIGHTS["scope"], note))

    # testable: a standing requirement is testable as written; a recurring activity needs how often or how
    # fast, a trigger, or a parameter for the organization to set.
    limits = [p for kind in commitments(text).values() for _, p in kind]
    signals = (limits + sorted(_distinct(_TRIGGER, text) | _distinct(_CONTINUOUS, text))
               + (["parameter"] if _PARAMETER.search(text) else []))
    recurring = sorted(_distinct(_RECURRING, text))
    loose = sorted(_distinct(_VAGUE_FREQUENCY, text))
    if recurring and not signals:
        testable, note = 0.0, f"{', '.join(recurring)} " + (f"'{loose[0]}'" if loose else "with no frequency")
        improvements.add("testable", f"Say how often or how fast ({recurring[0]} at least every [N] days, or "
                                     "within [time period]), or leave a parameter for the organization to set.")
    elif not objects:
        testable, note = 0.5, "nothing concrete to check"
        improvements.add("testable", "Say what exactly must be in place, so an assessor can check it.")
    else:
        testable, note = 1.0, ", ".join(signals[:4]) or "standing requirement"
    criteria.append(CriterionResult("testable", testable, WEIGHTS["testable"], note))

    # purpose: why, in the text or through the risk it treats.
    why = sorted(_distinct(_PURPOSE, text)) or ([after] if (after := _purpose_after_limit(text)) else [])
    if why:
        purpose, note = 1.0, ", ".join(why)
    elif statement.risk_statement:
        purpose, note = 1.0, "linked risk statement"
    else:
        purpose, note = 0.0, "no purpose or linked risk"
        improvements.add("purpose", "Say why: the risk it treats ('to deter brute-force attacks'), or add the "
                                    "risk it treats.")
    criteria.append(CriterionResult("purpose", purpose, WEIGHTS["purpose"], note))

    # single: one requirement, or a few clearly joined, so each can be tested and reported.
    actions = _actions(text)
    single = 1.0 if len(actions) <= 2 else 0.5
    criteria.append(CriterionResult("single", single, WEIGHTS["single"],
                                    f"{len(actions)} requirement{'s' if len(actions) != 1 else ''}"
                                    + (f" ({', '.join(actions)})" if actions else "")))
    if single < 1:
        improvements.add("single", f"Combines {len(actions)} requirements ({', '.join(actions)}): consider "
                                   "splitting them so each can be tested and reported on its own.")

    # labeled_parts: OSCAL gives each joined requirement in a catalog control its own lettered, referenceable
    # part (a., b., c.), rather than leaving them run together; a statement that bundles more than two
    # requirements (the point "single" starts flagging it) should be split that way, not just split somehow.
    if len(actions) <= 2:
        labeled_parts, parts_note = 1.0, "not bundled"
    elif len(requirement_parts(text)) > 1:
        labeled_parts, parts_note = 1.0, "already split into lettered parts"
    else:
        labeled_parts, parts_note = 0.5, "bundled, not split into lettered parts"
        improvements.add("labeled_parts", "OSCAL gives each joined requirement its own lettered part (a., b., c.) "
                                          "with a stable id, so each can be assessed and referenced on its own "
                                          "(e.g. 'ac-2_smt.j'): split this statement that way, not with commas.")
    criteria.append(CriterionResult("labeled_parts", labeled_parts, WEIGHTS["labeled_parts"], parts_note))

    # determinable: an assessor needs something to check pass or fail against, not a subjective judgment call,
    # the way a NIST SP 800-53A assessment objective must be determinable.
    subjective = sorted(_distinct(_SUBJECTIVE, text))
    determinable = 0.5 if subjective else 1.0
    criteria.append(CriterionResult("determinable", determinable, WEIGHTS["determinable"],
                                    ", ".join(subjective) or "no subjective qualifiers"))
    if subjective:
        quoted = "'" + "', '".join(subjective) + "'"
        improvements.add("determinable", f"{quoted} cannot be objectively tested: say exactly what must be true "
                                         "(a setting, a threshold, a named control) so an assessor can determine "
                                         "pass or fail.")

    # coverage: against the catalog's control text, when the statement is written for one.
    # (A catalog's own statement is not checked against itself.)
    if statement.requirement and not statement.requirement.strip().endswith(text):
        score, note, tips = requirement_coverage(statement.requirement, text)
        criteria.append(CriterionResult("coverage", score, WEIGHTS["coverage"], note))
        improvements.extend("coverage", tips)

    if statement.policy_intent:
        score, note, tips = _policy_intent(statement.policy_intent, text)
        criteria.append(CriterionResult("policy_intent", score, WEIGHTS["policy_intent"], note))
        improvements.extend("policy_intent", tips)

    concrete = [w for w in _term_words(text).values() if w not in _GENERIC and w not in VERBS]
    caps = [] if objects or concrete else [(0.4, "no concrete requirement")]
    return _finish(statement, criteria, improvements, ("vague", "modals", "examples"), caps=caps,
                   placeholder_msg="Replace the placeholder with the requirement.")


_UNIT_WORDS = r"(minutes?|hours?|(business |working )?days?|weeks?|months?|quarters?|years?|attempts?|characters?|" \
              r"passwords?|versions?)"
_LIMIT = re.compile(
    r"\b(at least (once )?(every |a |per )?|no (more|later) than |within |every |for at least |for |after |before |"
    r"above |below |more than |less than )(\[[^\]]{1,40}\]|\d+(\.\d+)?|one|two|three|five|ten)( [\w-]+){0,3}? ?"
    + _UNIT_WORDS + r"\b"
    r"|\b(hourly|daily|nightly|weekly|fortnightly|monthly|quarterly|semi-annually|annually|yearly|"
    r"at all times|immediately|continuously|in real time)\b"
    r"|\b(before|after|upon|on|when|whenever|prior to) (\w+ ){0,4}?(leaving|joining|deploy\w*|merg\w*|release|"
    r"discovery|request|termination|transfer|change\w*|access|use|onboarding|granting|installation)\b",
    re.I,
)
_SCOPE_END = re.compile(r"\s+(at least|within|every|each|daily|nightly|weekly|monthly|quarterly|annually|before|"
                        r"after|upon|when|whenever|immediately|at all times|for at least|so that|in order to|"
                        r"to (ensure|prevent|protect|deter|detect|reduce|limit|avoid|maintain|minimi[sz]e|"
                        r"mitigate|stop|block))\b|[,;.]", re.I)


_PURPOSE_VERBS = VERBS | {"shorten", "catch", "find", "spot", "cut", "lower", "speed", "show", "prove", "know"}


def _purpose_after_limit(text: str) -> str | None:
    """A "to ..." phrase straight after the limit says why: "every [90] days to remove stale access"."""
    for m in _LIMIT.finditer(text):
        after = re.match(r"\s*,?\s*(to ([a-z]+)\b.*)", text[m.end():], re.I)
        if after and after.group(2).lower() in _PURPOSE_VERBS:  # "to remove ...", not "to production"
            return after.group(1).strip().rstrip(".")
    return None


def parts(text: str) -> dict[str, str | None]:
    """The parts of a control statement, as found in its text: action, scope, limit, purpose, and any tools.

    The editor shows these as a checklist next to the statement, so a missing part is easy to see.
    """
    opening = _opening(text)
    first = _first_word(opening)
    action = first if first in VERBS else None
    if action and (m := re.match(r"^\s*\S+\s+(up|out|off|down)\b", opening, re.I)):
        action = f"{first} {m.group(1).lower()}"  # "back up", "carry out"
    scope = None
    if action:
        body = re.sub(r"^\s*\S+(\s+(up|out|off|down))?\s+", "", opening, count=1, flags=re.I)
        scope = _SCOPE_END.split(body, maxsplit=1)[0].strip() or None
    limit = _LIMIT.search(text)
    purpose = _PURPOSE.search(text)
    return {
        "action": action,
        "scope": scope,
        "limit": limit.group(0) if limit else None,
        "purpose": text[purpose.start():].rstrip(".") if purpose else _purpose_after_limit(text),
        "tools": ", ".join(sorted(_distinct(_PRODUCTS, text))) or None,
    }
