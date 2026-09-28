"""Best-practice guides: what good looks like for each criterion.

This is the Awareness part of the portal, after the approach of CSA's Internet
Hygiene Portal (Awareness, Assessment, Adoption): each criterion the health
check scores is a best practice, explained with why it matters, how to adopt
it, and a weak and a strong example.
"""

from __future__ import annotations

from .models import IDENTIFIED_RISK, IMPLEMENTATION, RECOMMENDATION, RISK_STATEMENT

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
    IMPLEMENTATION: {
        "title": "Implementation statements",
        "summary": "An implementation statement shows an assessor how a control is met today: who does what, "
                   "with which tool, how often, and what record it leaves.",
        "practices": {
            "coverage": _p(
                "Cover the whole requirement",
                "An assessor tests every part of the control. A part the statement skips is a finding waiting "
                "to happen.",
                "Walk through the control text item by item, including organization-defined values, and say how "
                "each is met.",
                "Accounts are managed in Okta.",
                "Account types are defined in the Access Standard; the IAM team is the account manager; access "
                "reviews run quarterly ...",
            ),
            "policy_intent": _p(
                "Meet the policy intent",
                "The control is how your policy is put into practice. A statement that falls short of the policy "
                "shows the policy is not being followed.",
                "Keep every commitment the policy makes (frequencies, time limits, retention). Where the policy "
                "is risk-based, say how risk is rated, give each tier its own schedule, and name who owns the "
                "tiering.",
                "Access is reviewed based on risk.",
                "Tier 1 (privileged and payment) access is reviewed quarterly and Tier 2 annually, as tiered in "
                "the CISO's annual access risk assessment.",
            ),
            "substance": _p(
                "Give enough detail",
                "One line rarely shows how a control operates, and leaves the assessor to ask.",
                "Describe the activity end to end: trigger, steps, outcome and record.",
                "MFA is enabled.",
                "Okta enforces phishing-resistant MFA at each login to AWS, GitHub and the admin console; the "
                "policy is owned by the IAM team and logged to Splunk.",
            ),
            "responsibility": _p(
                "Name who is responsible",
                "A control with no owner is not operated reliably, and an assessor needs someone to interview.",
                "Name the role or team that performs, owns or approves the activity. For an inherited control, "
                "name the provider and the authorization it relies on (a FedRAMP P-ATO, SOC 2 report or MTCS "
                "certificate), and describe any part the customer still carries out.",
                "Logs are reviewed daily.",
                "The Security Operations team reviews logs daily.",
            ),
            "mechanism": _p(
                "Name the mechanism",
                "The tool, configuration or procedure is what an assessor inspects.",
                "Name the system and the setting or procedure that implements the control.",
                "Access is restricted.",
                "Access is restricted by Okta group policies mapped to AWS IAM roles.",
            ),
            "frequency": _p(
                "Say how often, or what triggers it",
                "Without a frequency or trigger there is no way to tell whether the control is operating.",
                "State the schedule (daily, quarterly) or the event that triggers the activity (on termination, "
                "at each login).",
                "Accounts are reviewed periodically.",
                "Accounts are reviewed quarterly, and disabled on termination.",
            ),
            "evidence": _p(
                "Say what evidence it leaves",
                "Assessment runs on evidence. A statement that points to its records can be verified.",
                "Name the logs, tickets, reports or approvals produced, and where they are kept.",
                "Reviews are performed.",
                "Each review is recorded in a ServiceNow ticket retained for three years.",
            ),
            "implemented": _p(
                "State facts about today",
                "Plans, hedges and obligations describe what should happen, not what does.",
                "Write in the present tense about what operates now. Avoid 'will', 'should', 'may', 'must', "
                "'as needed', and open-ended 'such as' lists.",
                "Users should be reviewed as needed, such as leavers.",
                "Managers review all user accounts quarterly.",
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
