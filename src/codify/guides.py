"""Best-practice guide for control statements: what good looks like for each criterion.

Each criterion the check scores is a best practice, explained with why it
matters, how to adopt it, and a weak and a strong example.
"""

from __future__ import annotations

# Criterion score at or above which a practice counts as adopted, or partly adopted.
ADOPTED = 0.8
PARTLY = 0.4


def practice_status(score: float, has_issues: bool = False) -> str:
    """Adopted needs a high score and no outstanding improvement; an open improvement caps it at partly."""
    if score >= ADOPTED and not has_issues:
        return "adopted"
    if score >= PARTLY:
        return "partly"
    return "not-yet"


STATUS_LABELS = {"adopted": "Adopted", "partly": "Partly adopted", "not-yet": "Not yet adopted"}


def _p(title: str, why: str, how: str, weak: str, strong: str) -> dict:
    return {"title": title, "why": why, "how": how, "weak": weak, "strong": strong}


GUIDE: dict = {
    "title": "Control statements",
    "summary": "A control statement is the requirement: what must be done, written the way Singapore's IM8 "
               "writes it. It starts with the action and names no tool; who does it, and with what, belongs in "
               "the implementation statement.",
    "practices": {
        "action_first": _p(
            "Start with the action",
            "A requirement is an instruction. Leading with the verb makes it short, clear and the same shape "
            "as every other control.",
            "Open with the verb for what must be done (Back up, Encrypt, Restrict, Require). Leave out who: "
            "the implementation statement names the team.",
            "The IT team backs up the servers.",
            "Back up all important data and systems at least every [N] day(s).",
        ),
        "tool_neutral": _p(
            "Name no tool",
            "Tools change; the requirement should not. A product in the requirement ties every system to it.",
            "Say what must be achieved. Put the product in the implementation statement, or in guidance "
            "(IM8 keeps examples like AWS Backup in its guidance).",
            "Use Okta to enforce MFA.",
            "Require phishing-resistant multi-factor authentication for all access to cloud applications.",
        ),
        "scope": _p(
            "Say what it applies to",
            "Without scope, nobody can tell whether a system is in or out.",
            "Name the objects and qualify them: all, privileged, internet-facing, production, above a "
            "threshold.",
            "Patch vulnerabilities.",
            "Patch critical vulnerabilities on internet-facing systems.",
        ),
        "testable": _p(
            "Make it testable",
            "An assessor needs something to test against: a frequency, a time limit, a threshold or a trigger.",
            "Add how often, how fast or when (before merging, above S$10,000), or leave a parameter for the "
            "organization to set, as IM8 does ([time period]).",
            "Review access regularly.",
            "Review privileged access at least every [90] days.",
        ),
        "purpose": _p(
            "Say why",
            "The purpose ties the control to the risk it treats, and helps people apply it sensibly.",
            "Add the purpose ('to deter brute-force attacks'), or link the risk it treats. IM8 records a risk "
            "statement for every control.",
            "Apply rate-limiting on authentication.",
            "Apply rate-limiting on all authentication mechanisms to deter brute-force attacks.",
        ),
        "single": _p(
            "One requirement at a time",
            "A statement that bundles several requirements is hard to test and report on: it is only met "
            "when all of them are.",
            "Keep to one requirement, or two closely joined; split longer lists into separate controls.",
            "Back up data, encrypt it, test restores, monitor jobs and report failures.",
            "Back up all important data daily, and store backups in a separate location.",
        ),
        "coverage": _p(
            "Cover the catalog requirement",
            "When you write your own statement for a catalog control, it has to carry everything the "
            "catalog asks.",
            "Walk through the catalog control text and make sure each part appears.",
            "Review accounts.",
            "Review accounts for compliance with account management requirements at least every [90] days.",
        ),
        "policy_intent": _p(
            "Meet the policy intent",
            "The control statement turns the policy into a requirement. It should keep every commitment the "
            "policy makes.",
            "Carry the policy's frequencies, time limits and retention into the statement, or its risk tiers.",
            "Remove access when no longer needed.",
            "Disable user accounts within [1 business day] of staff leaving.",
        ),
        "firm": _p(
            "Keep it firm",
            "Hedged or open-ended wording makes the requirement optional.",
            "Avoid 'should', 'may', 'as appropriate', 'regularly' and open-ended 'such as' lists.",
            "Systems should be patched regularly where possible, e.g. servers.",
            "Patch critical vulnerabilities on all servers within [14] days.",
        ),
    },
}


def practice(name: str) -> dict | None:
    return GUIDE["practices"].get(name)
