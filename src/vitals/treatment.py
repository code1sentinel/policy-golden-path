"""Identified risks: is each risk treated, in proportion, by the policy intents and controls meant for it?

This is the first stage of a risk-based policy path. A risk from the risk
register is checked against every policy intent and control that treats it,
taken together: one control rarely treats a risk on its own, so a control that
only prevents is not marked down when another one recovers. The questions:

    described      is the risk clear enough to treat: threat, what is affected, impact
    rated          are likelihood and impact recorded
    treated        does at least one treatment address it, and does each linked one
    layered        do the treatments together prevent, detect and recover as the risk needs
    proportionate  is the treatment firm enough for the rating, and not piled on for a low risk
    tolerance      does a treatment set a measurable limit (how often, how fast, how long)

A risk with no treatment is reported as untreated. The check reads text, so it
shows whether the link is written down and plausible, not whether the
treatment works.
"""

from __future__ import annotations

import re

from .heuristic import (
    _IMPACT, _LIKELIHOOD, _RISK_BASED, _SCOPE, _SEVERE, _THREAT, Improvements, _distinct, _finish,
    _term_words, _terms, commitments,
)
from .models import Assessment, CriterionResult, Statement, Treatment

WEIGHTS = {
    "described": 0.10, "rated": 0.10, "treated": 0.25,
    "layered": 0.25, "proportionate": 0.15, "tolerance": 0.15,
}


def _re(words: str) -> re.Pattern:
    return re.compile(r"\b(" + words + r")", re.I)


# Risk themes: what signals the theme in a risk, and what treating it looks like. A treatment is relevant
# to a risk when it treats one of the risk's themes, or shares enough of its words.
THEMES: dict[str, tuple[re.Pattern, re.Pattern]] = {
    "ransomware and malware": (
        _re(r"ransomware|malware|virus|trojan|worm|malicious (code|software)|encrypt(s|ed)? (the |our )?(data|files|"
            r"servers?|systems?)"),
        _re(r"backups?|backed up|offline|immutable|restor(e|es|ed|ation)|recover|edr|endpoint detection|"
            r"anti-?(virus|malware)|application (control|allowlist)|allowlist|macro|patch|segment|"
            r"email[^.]{0,20}(filter|scann|quarantin|gateway|security)|"
            r"(filter|scann|quarantin)\w*[^.]{0,25}(e-?mails?|mail|attachments?)|malicious (attachments?|links?)"),
    ),
    "phishing and social engineering": (
        _re(r"phish|social engineering|business email compromise|bec\b|spoof|pretext"),
        _re(r"email[^.]{0,20}(filter|scann|quarantin|gateway|security)|"
            r"(filter|scann|quarantin)\w*[^.]{0,25}(e-?mails?|mail|attachments?)|malicious (attachments?|links?)|"
            r"dmarc|spf|dkim|awareness|training|phishing simulation|mfa|"
            r"multi-factor|report(ing)? suspicious|link (scan|protection)"),
    ),
    "unauthorized access": (
        _re(r"unauthori[sz]ed access|account|credential|password|privileged|insider|former (employee|staff)|"
            r"leaver|access (creep|rights)|impersonat|brute.?force|takeover"),
        _re(r"access review|review(ed|s)? (of )?(user )?access|recertif|mfa|multi-factor|least privilege|"
            r"privileged access|pam\b|joiner|mover|leaver|deprovision|disabl|revok|remov(e|ed|al) of access|"
            r"password|passphrase|sso|role-based|rbac|account|"
            r"access[^.]{0,40}(remov|revok|disabl|review|grant|approv)|(remov|revok|disabl)\w*[^.]{0,30}access"),
    ),
    "data disclosure": (
        _re(r"data (breach|leak|loss|exfiltration|disclosure)|disclos|exfiltrat|leak|personal data|customer data|"
            r"cardholder|confidential|sensitive data"),
        _re(r"encrypt|dlp|data loss prevention|classif|mask|tokeni[sz]|retention|dispos|need.to.know|"
            r"access (control|review)|least privilege"),
    ),
    "vulnerabilities": (
        _re(r"vulnerab|unpatched|exploit|zero.day|misconfigur|outdated|end.of.life|eol\b|legacy"),
        _re(r"patch|vulnerability (scan|management|assessment)|scan|harden|baseline|configuration|"
            r"penetration test|pen.?test|upgrade|decommission|remediat"),
    ),
    "outage and disaster": (
        _re(r"outage|downtime|unavailab|disrupt|halt|disaster|flood|fire|power|ddos|denial of service|"
            r"single point of failure|capacity"),
        _re(r"backups?|restor|recover|failover|redundan|resilien|continuity|disaster recovery|\bdr\b|bcp|rto|rpo|"
            r"high availability|ddos protection|capacity"),
    ),
    "third parties": (
        _re(r"third.party|vendor|supplier|outsourc|service provider|cloud provider|subcontract"),
        _re(r"due diligence|vendor (risk|assessment|review)|supplier (risk|assessment|review)|contract|sla|"
            r"right to audit|attestation|soc ?2|iso ?27001|assurance|exit plan"),
    ),
    "fraud": (
        _re(r"fraud|embezzl|misappropriat|unauthori[sz]ed (payment|transaction|transfer)"),
        _re(r"segregation of duties|separation of duties|dual (control|approval)|four.eyes|maker.checker|"
            r"approv|reconcil|limit"),
    ),
    "undetected activity": (
        _re(r"undetected|unnoticed|without (being )?detect|no (visibility|monitoring|logging)|go(es)? unnoticed"),
        _re(r"log|monitor|siem|alert|detect|review(ed)? (of )?(logs?|events?)|audit trail|soc\b"),
    ),
}

# How a treatment acts on a risk.
TREATMENT_TYPES: dict[str, re.Pattern] = {
    "prevent": _re(r"prevent|block|restrict|enforc|mfa|multi-factor|encrypt|patch|harden|least privilege|"
                   r"segregat|separat|allowlist|filter|disabl|revok|deprovision|remov|approv|train|awareness|"
                   r"segment|limit|deny|lock"),
    "detect": _re(r"detect|monitor|log|alert|siem|review|scan|audit|reconcil|recertif|inspect|test(ed|s|ing)? "
                  r"(controls?|for)"),
    "respond": _re(r"incident response|respond|contain|isolat|escalat|notif|playbook|runbook|investigat"),
    "recover": _re(r"backups?|backed up|restor|recover|failover|redundan|continuity|disaster recovery|rto|rpo|"
                   r"resilien|rebuild"),
}

# Impacts that need a way back, not only prevention.
_DISRUPTIVE = _re(r"outage|downtime|unavailab|disrupt|halt|stop|encrypt|destroy|wipe|delet|ransomware|"
                  r"cannot (operate|process|trade)|several (hours|days)|days|disaster")
# A risk-based principle with no values ("backed up at a frequency commensurate with criticality").
_PRINCIPLE = re.compile(_RISK_BASED.pattern + r"|\b(commensurate with|proportionate to|in proportion to|"
                        r"based on (their|its|the) (criticality|classification|sensitivity|risk))", re.I)
_TOLERANCE = _re(r"rto|rpo|recovery (time|point)|tolerance|appetite|threshold|no more than|at most|maximum")

_LEVELS = [
    (re.compile(r"^\s*(very[- ]?high|critical|severe|extreme|high|5|4)\s*$", re.I), 3),
    (re.compile(r"^\s*(medium|moderate|significant|3)\s*$", re.I), 2),
    (re.compile(r"^\s*(very[- ]?low|low|minor|minimal|negligible|1|2)\s*$", re.I), 1),
]
_LEVEL_NAMES = {1: "low", 2: "medium", 3: "high"}


def _level(value: str | None) -> int | None:
    for pattern, level in _LEVELS:
        if value and pattern.match(value):
            return level
    return None


def risk_level(statement: Statement) -> tuple[int | None, str]:
    """(1 low, 2 medium, 3 high or None, how it was worked out) from the ratings, or else the text."""
    r = statement.ratings
    if _level(r.get("risk")):
        return _level(r["risk"]), f"rated {r['risk']}"
    likelihood, impact = _level(r.get("likelihood")), _level(r.get("impact"))
    if likelihood and impact:
        return -(-(likelihood + impact) // 2), f"likelihood {r['likelihood']}, impact {r['impact']}"
    if likelihood or impact:
        return likelihood or impact, ", ".join(f"{k} {r[k]}" for k in ("likelihood", "impact") if r.get(k))
    if len(_distinct(_SEVERE, statement.text)) >= 2:
        return 3, "not rated; the text describes a severe impact"
    return None, "not rated"


def themes(text: str) -> list[str]:
    return [name for name, (signal, _) in THEMES.items() if signal.search(text)]


def _relevance(risk_text: str, risk_themes: list[str], t: Treatment) -> tuple[bool, str]:
    """Is the treatment about this risk? (relevant, why)."""
    text = t.text
    treats = [name for name in risk_themes if THEMES[name][1].search(text)]
    if treats:
        return True, "treats " + ", ".join(treats)
    shared = sorted(set(_term_words(risk_text)) & _terms(text))
    if len(shared) >= 3:
        return True, "shares " + ", ".join(shared[:5])
    return False, "no link found"


def _types(text: str) -> list[str]:
    return [name for name, pattern in TREATMENT_TYPES.items() if pattern.search(text)]


def _overlaps(relevant: list[tuple[Treatment, list[str]]]) -> list[tuple[str, str]]:
    """Pairs of treatments that do the same job in mostly the same words."""
    out = []
    for i, (a, a_types) in enumerate(relevant):
        a_terms = _terms(a.text)
        for b, b_types in relevant[i + 1:]:
            b_terms = _terms(b.text)
            if not a_terms or not b_terms or set(a_types) != set(b_types):
                continue
            if len(a_terms & b_terms) / len(a_terms | b_terms) >= 0.6:
                out.append((a.label, b.label))
    return out


def assess_identified_risk(statement: Statement) -> Assessment:
    text = statement.text.strip()
    improvements = Improvements()
    criteria: list[CriterionResult] = []
    risk_themes = themes(text)

    # described: threat or cause, what is affected, and the impact.
    threat = _distinct(_THREAT, text) | set(risk_themes)
    affected = _distinct(_SCOPE, text)
    impact = _distinct(_IMPACT, text) | {m for m in _distinct(_DISRUPTIVE, text)}
    parts = [bool(threat), bool(affected), bool(impact)]
    criteria.append(CriterionResult("described", sum(parts) / 3, WEIGHTS["described"],
                                    f"threat {'named' if threat else 'missing'}, affected "
                                    f"{'named' if affected else 'missing'}, impact {'named' if impact else 'missing'}"))
    if not threat:
        improvements.add("described", "Name the threat or cause: who or what could make this happen.")
    if not affected:
        improvements.add("described", "Say which systems, data or services are exposed.")
    if not impact:
        improvements.add("described", "Describe the impact in business terms: what stops, leaks or is lost.")

    # rated
    level, how = risk_level(statement)
    level_inferred = how.startswith("not rated")
    r = statement.ratings
    rated = (bool(_level(r.get("likelihood")) or _distinct(_LIKELIHOOD, text))
             + bool(_level(r.get("impact")) or _level(r.get("risk")))) / 2
    criteria.append(CriterionResult("rated", rated, WEIGHTS["rated"], how))
    if rated < 1:
        improvements.add("rated", "Record likelihood and impact, so the treatment can be judged against them.")

    # treated: every linked treatment should be about this risk.
    findings = []
    relevant: list[tuple[Treatment, list[str]]] = []
    for t in statement.treatments:
        ok, why = _relevance(text, risk_themes, t)
        kinds = _types(t.text) if ok else []
        findings.append({"label": t.label, "control_id": t.control_id, "policy_intent": t.policy_intent,
                         "control_statement": t.control_statement, "relevant": ok, "why": why, "types": kinds})
        if ok:
            relevant.append((t, kinds))
        else:
            improvements.add("treated", f"'{t.label}' does not appear to address this risk: check the link, or "
                                        "say how it treats the risk.")
    n = len(statement.treatments)
    if not n:
        treated = 0.0
        improvements.first("treated", "No policy intent or control treats this risk. Link the ones that do, or "
                                      "record the risk as accepted.")
    elif not relevant:
        treated = 0.0
    else:
        treated = 0.6 + 0.4 * len(relevant) / n
    criteria.append(CriterionResult("treated", treated, WEIGHTS["treated"],
                                    f"{len(relevant)} of {n} linked treatments address it"))

    # layered: the treatments together should act as the risk needs.
    covered = sorted({k for _, kinds in relevant for k in kinds})
    needed = ["prevent"]
    if _DISRUPTIVE.search(text):
        needed.append("recover")
    if level == 3:
        needed.append("detect")
    missing = [k for k in needed if k not in covered]
    layered = (len(needed) - len(missing)) / len(needed) if relevant else 0.0
    criteria.append(CriterionResult("layered", layered, WEIGHTS["layered"],
                                    f"covers {', '.join(covered) or 'nothing'}; needs {', '.join(needed)}"))
    advice = {
        "prevent": "Nothing prevents this risk: add a treatment that reduces its likelihood.",
        "recover": "Nothing recovers from this risk, and its impact is disruptive: add a way back (tested "
                   "restores, failover) or record the impact as accepted.",
        "detect": f"The risk {'reads as' if level_inferred else 'is'} high and nothing would detect it happening: "
                  "add monitoring or alerting.",
    }
    if relevant:
        for k in missing:
            improvements.add("layered", advice[k])

    # proportionate: firm enough for the rating, and not piled on for a low risk.
    firm = [t for t, _ in relevant if any(commitments(t.text).values())]
    vague_risk_based = [t for t, _ in relevant if _PRINCIPLE.search(t.text) and not any(commitments(t.text).values())]
    if not relevant:
        proportionate = 0.0
    elif level is None:
        proportionate = 0.5
        improvements.add("proportionate", "Rate the risk, so the strength of its treatment can be judged.")
    elif level >= 2 and not firm:
        proportionate = 0.3
        improvements.add("proportionate", f"The risk is {_LEVEL_NAMES[level]}, but no treatment commits to how often, "
                                          "how fast or how long: give at least one a firm commitment.")
    elif level == 1 and len(firm) >= 3:
        proportionate = 0.7
        improvements.add("proportionate", f"The risk is low, yet {len(firm)} treatments carry firm commitments: "
                                          "check the effort is justified.")
    else:
        proportionate = 1.0
    for t in vague_risk_based:
        improvements.add("proportionate", f"'{t.label}' is risk-based: say which tier this risk falls in and what "
                                          "that tier requires.")
        proportionate = min(proportionate, 0.7)
    for a, b in _overlaps(relevant):
        improvements.add("proportionate", f"'{a}' and '{b}' do the same job in much the same words: check both are "
                                          "needed.")
    criteria.append(CriterionResult("proportionate", proportionate, WEIGHTS["proportionate"],
                                    f"{len(firm)} treatment{'s' if len(firm) != 1 else ''} with firm commitments; "
                                    f"risk {_LEVEL_NAMES.get(level, 'unrated')}"))

    # tolerance: a measurable limit somewhere in the treatments.
    limits = sorted({p for t, _ in relevant for kind in commitments(t.text).values() for _, p in kind}
                    | {m for t, _ in relevant for m in _distinct(_TOLERANCE, t.text)})
    tolerance = 1.0 if limits else 0.0
    criteria.append(CriterionResult("tolerance", tolerance, WEIGHTS["tolerance"],
                                    ", ".join(limits[:4]) or "no measurable limit"))
    if relevant and not limits:
        improvements.add("tolerance", "Set a measurable limit in a treatment (recover within 24 hours, patch "
                                      "within 14 days) so it can be tested against the risk.")

    assessment = _finish(statement, criteria, improvements, ("vague", "examples"),
                         placeholder_msg="Describe the identified risk.")
    assessment.details = {"treatments": findings, "themes": risk_themes,
                          "risk_level": _LEVEL_NAMES.get(level) if level else None}
    return assessment
