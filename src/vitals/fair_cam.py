"""FAIR-CAM view of an identified risk's treatments (prototype).

The FAIR Controls Analytics Model (FAIR-CAM, from the FAIR Institute) sorts
controls by what they do for a loss scenario:

    Loss event controls        act on the loss event itself
        avoid                  reduce contact with the threat (segmentation, not exposing it)
        deter                  make the threat less likely to act (warnings, sanctions)
        resist                 make an attack less likely to succeed (MFA, patching, encryption)
        detect                 see that an event is happening (logging, monitoring, alerting)
        respond                end or contain the event (isolate, revoke, incident response)
        limit loss             reduce the loss once it happens (backups, failover, insurance)
    Variance management        keep the loss event controls working as intended
                               (control testing, restore tests, drift and failure alerts)
    Decision support           help people decide in line with expectations
                               (policies, standards, training, risk assessment and reporting)

Controls depend on one another: detection is worth little without response, and
a control nobody checks drifts. This module tags each treatment with the
functions its wording describes, lays them out as a map, and names the gaps.

The wording here is our own summary; see the FAIR Institute's FAIR-CAM white
paper for the model itself. Tags come from text, so they show what a treatment
claims to do, not how well it does it.
"""

from __future__ import annotations

import re

from .models import Treatment


def _re(words: str) -> re.Pattern:
    return re.compile(r"\b(" + words + r")", re.I)


# (key, label, group, pattern). A treatment can carry several functions.
FUNCTIONS: list[tuple[str, str, str, re.Pattern]] = [
    ("avoid", "Avoid", "loss event", _re(
        r"segment|isolat\w* (the )?(network|environment|system)|private (subnet|network)|not (be )?(exposed|"
        r"internet)|no (public|internet) access|block (public|inbound)|firewall|deny[- ]by[- ]default|"
        r"decommission|remove unused|disable unused|geo-?block|air.?gap|block public")),
    ("deter", "Deter", "loss event", _re(
        r"deter|warning banner|login banner|disciplinary|sanction|legal action|acceptable use|"
        r"background (check|screen)|vetting|monitoring notice")),
    ("resist", "Resist", "loss event", _re(
        r"mfa|multi-factor|phishing-resistant|fido|encrypt|patch|harden|validat|password|passphrase|"
        r"two (people|approvers)|dual (control|approval)|maker.checker|segregation of duties|approv|"
        r"filter|quarantin|anti-?(virus|malware)|allowlist|application control|least privilege|rbac|"
        r"rate-?limit|sanitis|saniti[sz]|secure configuration|disabl\w* (the )?(user )?accounts?|"
        r"remov\w* access|revok|deprovision|print release|badge|shred|clean desk|conditional access|"
        r"due diligence|before onboarding|contracts? require|cross-?train|succession|second engineer")),
    ("detect", "Detect", "loss event", _re(
        r"detect|monitor|alert|siem|sentinel|log(s|ged|ging)?\b|audit trail|anomal|impossible.travel|"
        r"reconcil|review\w* (the )?(quarantine|logs?|alerts?|sign-?ins?)|investigat|breach notification|"
        r"notif\w* (us )?within")),
    ("respond", "Respond", "loss event", _re(
        r"isolat\w* (infected |compromised )?(hosts?|devices?|endpoints?|servers?)|contain|incident response|"
        r"playbook|runbook|escalat|investigat\w* within|block\w* (the )?(sender|ip|account)|"
        r"terminat(e|es|ed|ing) (the )?(session|event|connection)")),
    ("limit", "Limit loss", "loss event", _re(
        r"backups?|backed up|restor|recover|failover|redundan|multi-(region|az|site)|high availability|"
        r"continuity|disaster recovery|insurance|immutable|offline|rto|rpo|cross-?train|succession|"
        r"runbooks? (are|is) (updated|maintained)")),
    ("variance", "Keep controls working", "variance management", _re(
        r"restore-?tests?|test\w* (the )?(restor|recover|backups?|controls?|failover|dr\b|disaster)|"
        r"restoration|alert\w*[^.;]{0,40}\b(drift|configuration changes?|failed|failures?)|drift|"
        r"configuration (monitoring|management)|failed (jobs?|backups?)|job failures?|change (control|management)|"
        r"vulnerabilit\w* scan|scan\w*[^.;]{0,40}vulnerabilit|"
        r"control test|recertif|re-?assess|health check|posture management|cspm|aws config|verif\w* (that|the)|"
        r"reviewed (quarterly|annually|monthly)|records? the (result|review)|tracked in")),
    ("decision", "Decision support", "decision support", _re(
        r"polic(y|ies)|standard|training|awareness|simulation|risk assessment|risk tier|classif|"
        r"report\w* to|metrics|dashboard|threat intel|vendor register|risk register|approved by")),
]
FUNCTION_LABELS = {key: label for key, label, _, _ in FUNCTIONS}
FREQUENCY_SIDE = ("avoid", "deter", "resist")
MAGNITUDE_SIDE = ("respond", "limit")


_PATTERNS = {key: pattern for key, _, _, pattern in FUNCTIONS}


def functions(t: Treatment) -> list[str]:
    """The FAIR-CAM functions a treatment's wording describes.

    Wording that keeps a control working ("alert on configuration drift", "scan for vulnerabilities") is
    variance management, so it is taken out before looking for detection and response.
    """
    text = t.text
    rest = _PATTERNS["variance"].sub(" ", text)
    return [key for key, _, _, pattern in FUNCTIONS
            if pattern.search(rest if key in ("detect", "respond") else text)]


def analyse(treatments: list[Treatment], impact_level: int | None, detectable: bool = True) -> dict:
    """The FAIR-CAM map for a risk's relevant treatments, and the gaps it shows.

    A policy intent is decision support in itself, so its treatment fills that cell. `detectable` is False
    for risks where detection means nothing (losing a key person).
    """
    tagged = [(t, functions(t)) for t in treatments]
    grid = {key: [t.label for t, fs in tagged if key in fs or (key == "decision" and t.policy_intent)]
            for key in FUNCTION_LABELS}
    has = {key for key, labels in grid.items() if labels}
    gaps: list[str] = []
    if not treatments:
        return {"map": grid, "gaps": gaps, "treatments": {}}

    if detectable and "detect" in has and "respond" not in has:
        gaps.append("Something detects this risk, but no treatment says how the event is contained or ended: "
                    "detection needs a response.")
    if detectable and "respond" in has and "detect" not in has:
        gaps.append("A response is in place, but nothing detects the event to set it off.")
    if not has & set(FREQUENCY_SIDE):
        gaps.append("Every treatment works after the event: nothing makes it less likely (avoid, deter or "
                    "resist).")
    if impact_level == 3 and not has & set(MAGNITUDE_SIDE):
        gaps.append("The impact is high, but every treatment works on how often it happens: add a way to limit "
                    "the loss (response, backups, failover).")
    if "variance" not in has:
        gaps.append("Nothing checks that the treatments keep working (variance management): for example, test "
                    "them, alert when they fail, or monitor them for configuration drift.")
    if "decision" not in has:
        gaps.append("No policy or standard sets the expectation for this risk (decision support).")
    return {"map": grid, "gaps": gaps, "treatments": {t.label: fs for t, fs in tagged}}
