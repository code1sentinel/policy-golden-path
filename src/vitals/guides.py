"""Best-practice guides: what good looks like for each criterion.

This is the Awareness part of the portal, after the approach of CSA's Internet
Hygiene Portal (Awareness, Assessment, Adoption): each criterion the health
check scores is a best practice, explained with why it matters, how to adopt
it, and a weak and a strong example.
"""

from __future__ import annotations

from .models import CONTROL_STATEMENT, IDENTIFIED_RISK, RECOMMENDATION, RISK_STATEMENT

# Criterion score at or above which a practice counts as adopted, or partly adopted.
ADOPTED = 0.8
PARTLY = 0.4


def practice_status(score: float, has_issues: bool = False) -> str:
    """Adopted needs a high score and no outstanding improvement; an open improvement caps it at partly."""
    if score >= ADOPTED and not has_issues:
        return "adopted"
    if score >= ADOPTED:
        return "partly"
    if score >= PARTLY:
        return "partly"
    return "not-yet"


STATUS_LABELS = {"adopted": "Adopted", "partly": "Partly adopted", "not-yet": "Not yet adopted"}


def _p(title: str, why: str, how: str, weak: str, strong: str) -> dict:
    return {"title": title, "why": why, "how": how, "weak": weak, "strong": strong}


GUIDES: dict[str, dict] = {
    IDENTIFIED_RISK: {
        "title": "Identified risks",
        "summary": "In a risk-based approach, policy starts from risk. Each identified risk should be treated by "
                   "the policy intents and controls linked to it, taken together, and in proportion to its rating.",
        "practices": {
            "described": _p(
                "Describe the risk",
                "A risk that is not clearly described cannot be matched to a treatment.",
                "Name the threat or cause, what is exposed, and the impact in business terms.",
                "Cyber risk.",
                "Ransomware delivered by phishing could encrypt the finance file servers and their backups, "
                "halting payments for several days.",
            ),
            "rated": _p(
                "Rate it",
                "The rating sets how strong the treatment needs to be.",
                "Record likelihood and impact, or an overall risk rating, from your risk methodology.",
                "No rating.",
                "Likelihood high, impact high.",
            ),
            "treated": _p(
                "Link the treatments that address it",
                "An untreated risk is a gap in policy; a treatment linked to the wrong risk is false comfort.",
                "Link every policy intent and control that treats the risk. Several controls can share one risk. "
                "If nothing treats it, record the risk as accepted.",
                "Ransomware risk linked only to the user access review policy.",
                "Ransomware risk linked to the backup policy, the email filtering standard and the EDR control.",
            ),
            "layered": _p(
                "Layer the treatments",
                "Prevention fails sometimes. A disruptive risk needs a way back, and a high risk needs to be seen "
                "when it happens.",
                "Across all linked treatments, cover prevent, and also recover when the impact is disruptive, "
                "and detect when the risk is high.",
                "Staff complete phishing awareness training.",
                "Email is filtered and staff trained (prevent), EDR alerts the SOC (detect), and offline backups "
                "are restore-tested quarterly (recover).",
            ),
            "proportionate": _p(
                "Treat in proportion",
                "Under-treating a high risk leaves exposure; over-treating a low one wastes effort.",
                "Give a medium or high risk at least one treatment with a firm commitment. For a risk-based "
                "intent, say which tier the risk falls in. Question duplicate or heavy treatment of a low risk.",
                "Critical systems are backed up at a frequency commensurate with their criticality.",
                "Tier 1 systems, which include the finance file servers, are backed up daily.",
            ),
            "tolerance": _p(
                "Set a measurable limit",
                "A limit turns the treatment into something that can be tested against the risk.",
                "State how often, how fast or how long: a recovery time, a patch window, a review frequency.",
                "Backups are taken regularly.",
                "Services are restored within 24 hours, from backups taken daily and kept offline.",
            ),
            "clarity": _p(
                "Keep it clear",
                "Vague wording hides what could actually happen.",
                "Avoid 'as needed' and open-ended 'such as' lists; say what the risk is.",
                "Various cyber threats such as malware etc.",
                "Ransomware delivered by phishing email.",
            ),
        },
    },
    CONTROL_STATEMENT: {
        "title": "Control statements",
        "summary": "A control statement is the requirement: what must be done, written the way Singapore's IM8 "
                   "writes it, and to OSCAL's own conventions for a catalog control. It starts with the action and "
                   "names no tool; who does it, and with what, belongs elsewhere.",
        "practices": {
            "action_first": _p(
                "Start with the action",
                "A requirement is an instruction. Leading with the verb makes it short, clear and the same shape "
                "as every other control.",
                "Open with the verb for what must be done (Back up, Encrypt, Restrict, Require). Leave out who: "
                "that belongs with how the control is implemented.",
                "The IT team backs up the servers.",
                "Back up all important data and systems at least every [N] day(s).",
            ),
            "tool_neutral": _p(
                "Name no tool",
                "Tools change; the requirement should not. A product in the requirement ties every system to it.",
                "Say what must be achieved. Put the product in guidance (IM8 keeps examples like AWS Backup in "
                "its guidance), or wherever the control is implemented.",
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
            "labeled_parts": _p(
                "Label joined parts",
                "A catalog control gives each requirement its own lettered, referenceable part, so it can be "
                "assessed and cited on its own (e.g. 'ac-2_smt.j'). Run-on prose loses that.",
                "When a statement bundles more than two requirements, split it into lettered parts (a., b., c.) "
                "with stable ids, the way a catalog control does, instead of joining them with commas.",
                "Back up data daily, encrypt it, test restores quarterly and report failures within 1 day.",
                "a. Back up data daily; b. encrypt backups; c. test restores quarterly; d. report failures "
                "within 1 day.",
            ),
            "determinable": _p(
                "Make it determinable",
                "An assessment objective has to be answerable pass or fail. A subjective word like 'adequate' or "
                "'robust' leaves the call to whoever is assessing it.",
                "Replace evaluative words (robust, effective, adequate, sufficient, reasonable, appropriate) with "
                "the setting, threshold or named control that would make it true.",
                "Apply adequate access controls to production systems.",
                "Restrict access to production systems to members of the platform-admins group.",
            ),
        },
    },
    RISK_STATEMENT: {
        "title": "Risk statements",
        "summary": "A risk statement lets a reader who was not there understand what is wrong, why it happened, "
                   "who could exploit it and what it could cost.",
        "practices": {
            "condition": _p(
                "State the condition with evidence",
                "The condition is the fact the risk rests on. Evidence makes it hard to dispute.",
                "Say what was found, how (sampled, tested, inspected) and how much.",
                "Access reviews are not done properly.",
                "14 of 60 sampled accounts belonged to staff who left more than 30 days earlier.",
            ),
            "criteria": _p(
                "Name the requirement not met",
                "The requirement is the yardstick. Without it, the condition is an opinion.",
                "Name the control and policy, and describe the gap in their terms.",
                "This is bad practice.",
                "This does not meet AC-2 or the Access Control Policy, which require access removed on departure.",
            ),
            "cause": _p(
                "Explain the cause",
                "A recommendation can only fix what the risk statement explains.",
                "Say why the condition exists: a missing process, a manual step, a gap between systems.",
                "Leaver accounts were missed.",
                "Leaver notices are emailed and processed manually, with no integration between Workday and Okta.",
            ),
            "threat": _p(
                "Name the threat and likelihood",
                "A weakness only matters if something can exploit it.",
                "Say who or what could exploit it, and how likely that is.",
                "This could be a risk.",
                "A former employee, or an attacker who phished their credentials, could use the accounts; they are "
                "internet-facing, so exploitation is likely.",
            ),
            "impact": _p(
                "Describe the impact",
                "Impact is what decision makers weigh the risk by.",
                "Say what would happen to which data or service, in business terms.",
                "This affects security.",
                "Fraudulent payments could be approved, causing direct financial loss and regulatory reporting.",
            ),
            "scope": _p(
                "Give the scope",
                "Scope tells the owner how big the fix is.",
                "Name the systems, accounts or components affected, and how many.",
                "Some accounts are affected.",
                "14 Okta accounts, 3 of them holding the payment approver role.",
            ),
            "rating": _p(
                "Rate it consistently",
                "Ratings drive priority. A rating that contradicts the text undermines both.",
                "Record likelihood and impact in the risk's characterizations, and check they match the statement.",
                "Rated low, while describing fraudulent payments.",
                "Likelihood high, impact high.",
            ),
            "clarity": _p(
                "Keep it factual",
                "Vague wording and embedded fixes blur what the risk is.",
                "Avoid 'as needed' and open-ended 'such as' lists, and move remediation advice into the "
                "recommendation.",
                "Logs are sometimes not reviewed, etc. The team should review more.",
                "Audit logs for the payments cluster were not reviewed on 41 of 90 days sampled.",
            ),
        },
    },
    RECOMMENDATION: {
        "title": "Recommendations",
        "summary": "A recommendation tells an owner exactly what to do, by when, and how everyone will know it "
                   "is done.",
        "practices": {
            "actionable": _p(
                "Lead with the action",
                "An owner needs to know what to do. Tentative wording invites no action.",
                "Start with a verb (Disable, Configure, Integrate). Avoid 'consider' and 'where possible'.",
                "Consider improving the leaver process.",
                "Integrate Workday with Okta so that a termination disables the Okta account.",
            ),
            "root_cause": _p(
                "Fix the cause",
                "Fixing only the symptom lets the risk come back.",
                "Address the cause named in the risk statement, as well as the instances found.",
                "Disable the 14 accounts.",
                "Disable the 14 accounts now, and automate deprovisioning so leavers are removed within 4 hours.",
            ),
            "specific": _p(
                "Be specific",
                "A specific action can be planned, costed and verified.",
                "Name the system, setting or process to change.",
                "Improve access management.",
                "Configure the Workday to Okta connector to deactivate users on termination.",
            ),
            "owner": _p(
                "Name an owner",
                "Unowned actions do not get done.",
                "Name the accountable role, in the text or as the remediation's responsible role.",
                "This should be fixed.",
                "The IAM team lead owns this change.",
            ),
            "timeline": _p(
                "Set a date by risk",
                "A date makes the action trackable; tying it to the risk rating sets the right urgency.",
                "Give a target date, sooner for higher risks, in the text or the remediation's task timing.",
                "Fix this soon.",
                "Complete by 30 November 2026 (risk rated high).",
            ),
            "completion": _p(
                "Define done",
                "Without completion evidence, the risk cannot be closed with confidence.",
                "Say what evidence will show the action worked.",
                "Update the process.",
                "Verify by re-sampling 60 accounts and confirming none belong to leavers.",
            ),
            "clarity": _p(
                "Keep it firm",
                "Optional and open-ended wording lets the action shrink.",
                "Avoid 'where possible', 'consider' and 'such as' lists.",
                "Consider reviewing things such as alerts, etc.",
                "Review every alert raised by the SOC detection rules listed in the runbook.",
            ),
        },
    },
}


def practice(kind: str, name: str) -> dict | None:
    return GUIDES.get(kind, {}).get("practices", {}).get(name)
