"""Statements from a CSV file: one row per policy, followed down the policy path.

Each row carries one policy intent and the text written for it. These four
columns are required (a cell may be left empty when a row has nothing for it):

    policy intent       what the organization's policy says the control must achieve
    control statement   the requirement: what must be done, IM8 style ("Back up all important data...")
    risk statement      where practice falls short, and what it could cost
    recommendation      how to close the gap

A row yields up to four items to assess, checked along the path: the control
statement against the row's policy intent; the implementation statement, when
given, against the control statement; the risk statement against the policy
intent; and the recommendation against the risk statement.

Rows naming the same identified risk (by risk id, or by the same text) are
grouped: the risk is assessed once, against the policy intents and control
statements of all its rows together, since several controls often share one
risk.

Optional columns add context:

    implementation statement  how the control is met today: who, with which tool, how often, what evidence
    identified risk     a risk from the risk register that this row's policy intent and control treat
    risk id             links rows that treat the same risk, e.g. R-01
    control id          e.g. ac-2
    control requirement the control text, when no catalog is supplied
    title               a name for the row, used to label its risk and recommendation
    likelihood, impact  risk ratings
    owner, target date  the recommendation's owner and date

Header names are case-insensitive; spaces, hyphens and underscores are
interchangeable. Comma, semicolon and tab separated files all work, and an
Excel workbook (.xlsx) can be read directly with parse_xlsx.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, timedelta

from .models import CONTROL_STATEMENT, IDENTIFIED_RISK, IMPLEMENTATION, RECOMMENDATION, RISK_STATEMENT, Statement, Treatment

REQUIRED = ("policy_intent", "control_statement", "risk_statement", "recommendation")
OPTIONAL = ("implementation_statement", "identified_risk", "risk_id", "control_id", "control_requirement", "title", "likelihood", "impact", "owner", "target_date")
COLUMNS = REQUIRED + OPTIONAL

LABELS = {
    "policy_intent": "policy intent", "control_statement": "control statement", "risk_statement": "risk statement",
    "recommendation": "recommendation", "implementation_statement": "implementation statement",
    "identified_risk": "identified risk", "risk_id": "risk id",
    "control_id": "control id", "control_requirement": "control requirement",
    "title": "title", "likelihood": "likelihood", "impact": "impact", "owner": "owner", "target_date": "target date",
}

# Other names people use for the same columns.
_ALIASES = {
    "policy": "policy_intent", "intent": "policy_intent",
    "control_implementation": "implementation_statement", "implementation": "implementation_statement",
    "how": "implementation_statement", "statement": "control_statement",
    "risk": "risk_statement",
    "recommendations": "recommendation", "remediation": "recommendation",
    "control": "control_id", "control_ref": "control_id",
    "requirement": "control_requirement", "control_text": "control_requirement",
    "deadline": "target_date", "due_date": "target_date", "date": "target_date",
    "risk_description": "identified_risk", "register_risk": "identified_risk", "risk_register": "identified_risk",
    "risk_ref": "risk_id", "risk_reference": "risk_id",
}

EXAMPLE_ROWS = [
    {
        "policy_intent": "User access is reviewed at a frequency commensurate with the risk of the access, and "
                         "access that is no longer needed is removed within 5 business days.",
        "control_statement": "Review user access at least every [90] days for privileged and payment access and "
                             "at least annually for all other access, and remove access that is no longer needed "
                             "within [5] business days.",
        "implementation_statement": "Accounts are tiered in the annual access risk assessment owned by the CISO: "
                                    "Tier 1 covers privileged and payment access, Tier 2 everything else. Managers "
                                    "review Tier 1 access quarterly and Tier 2 annually in Okta, and unneeded access "
                                    "is removed within 2 business days. Tiers are reassessed after major changes. "
                                    "Each review is recorded in a ServiceNow ticket.",
        "risk_statement": "14 of 60 sampled Okta accounts belonged to leavers, which does not meet AC-2 and the "
                          "Access Control Policy, because leaver notices are processed manually. A former "
                          "employee could use them to approve fraudulent payments, causing financial loss; the "
                          "accounts are internet-facing, so exploitation is likely.",
        "recommendation": "Integrate Workday with Okta so leaver notices disable accounts automatically instead of "
                          "being processed manually. The IAM team lead owns this. Verify closure by re-sampling "
                          "60 accounts.",
        "identified_risk": "Former employees, or attackers using their credentials, could use accounts that are "
                           "not removed to approve fraudulent payments.",
        "risk_id": "R-01",
        "control_id": "ac-2", "title": "Leaver accounts", "likelihood": "high", "impact": "high",
        "owner": "IAM team lead", "target_date": "2026-11-30",
    },
    {
        "policy_intent": "Security events are reviewed daily and audit logs are retained for at least 3 years.",
        "control_statement": "Logs should be reviewed regularly.",
        "implementation_statement": "Logs are reviewed periodically as needed.",
        "risk_statement": "Audit logs are not always reviewed which could be a risk.",
        "recommendation": "Consider improving log review where possible.",
        "identified_risk": "Misuse of payment approver accounts could go undetected.",
        "risk_id": "R-01",
        "control_id": "au-6", "title": "Audit review",
    },
]


def template() -> str:
    """A CSV template: the columns, with one strong and one weak example row."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([LABELS[c] for c in COLUMNS])
    for row in EXAMPLE_ROWS:
        w.writerow([row.get(c, "") for c in COLUMNS])
    return out.getvalue()


def template_xlsx() -> bytes:
    """The same template as an Excel workbook."""
    from .xlsx import write_rows

    rows = [[LABELS[c] for c in COLUMNS]] + [[row.get(c, "") for c in COLUMNS] for row in EXAMPLE_ROWS]
    widths = [45, 50, 60, 50, 60, 45, 10, 12, 40, 18, 11, 11, 16, 12]
    return write_rows(rows, sheet_name="Policies", widths=widths)


def _normalise(header: str) -> str:
    key = "_".join(header.strip().lower().replace("-", " ").replace("_", " ").split())
    return _ALIASES.get(key, key)


def _reader(content: str) -> csv.DictReader:
    first_line = content.splitlines()[0] if content.strip() else ""
    try:
        dialect = csv.Sniffer().sniff(first_line, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return csv.DictReader(io.StringIO(content), dialect=dialect)


_EXCEL_SERIAL = re.compile(r"^\d{5}(\.\d+)?$")


def _excel_date(value: str) -> str:
    """Excel stores dates as days since 1899-12-30; turn a serial like 46356 into 2026-11-30."""
    if _EXCEL_SERIAL.match(value):
        return (date(1899, 12, 30) + timedelta(days=int(float(value)))).isoformat()
    return value


def parse_xlsx(data: bytes, source: str = "xlsx") -> list[Statement]:
    """Statements from an Excel workbook laid out like the CSV: one row per policy."""
    from .xlsx import read_rows

    sheet, rows = read_rows(data, wanted_header=REQUIRED)
    if not rows:
        raise ValueError(f"worksheet '{sheet}' is empty")
    header = [_normalise(h) for h in rows[0]]
    if "target_date" in header:
        col = header.index("target_date")
        for row in rows[1:]:
            if len(row) > col:
                row[col] = _excel_date(row[col].strip())
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    try:
        return parse_csv(out.getvalue(), source=source)
    except ValueError as exc:
        raise ValueError(f"worksheet '{sheet}': {exc}") from None


def parse_csv(content: str, source: str = "csv") -> list[Statement]:
    content = content.lstrip("﻿")
    if not content.strip():
        raise ValueError("CSV file is empty")
    reader = _reader(content)
    fields = {f: _normalise(f) for f in reader.fieldnames or [] if f}
    missing = [LABELS[c] for c in REQUIRED if c not in fields.values()]
    if missing:
        raise ValueError(
            "CSV needs the columns: policy intent, control statement, risk statement, recommendation "
            f"(missing: {', '.join(missing)}). Download the template to start from."
        )

    out: list[Statement] = []
    risks: dict[str, Statement] = {}
    for n, raw in enumerate(reader, start=2):
        row = {fields[k]: (v or "").strip() for k, v in raw.items() if k in fields}
        linked = _link_risk(row, n, source, risks, out) if row.get("identified_risk") or row.get("risk_id") else None
        if not any(row.get(c) for c in ("control_statement", "implementation_statement", "risk_statement",
                                        "recommendation")):
            continue  # nothing to assess on this row
        label = row.get("title") or f"Row {n}"
        control = row.get("control_id", "")
        intent = row.get("policy_intent") or None
        requirement = row.get("control_requirement") or None
        ratings = {k: row[k] for k in ("likelihood", "impact") if row.get(k)}
        common = dict(control_id=control, source=source, requirement=requirement)

        policy_ids = [f"row {n}"] if intent else []
        if row.get("control_statement"):
            # The identified risk it treats is the control's purpose, as IM8 records a risk for each control.
            out.append(Statement(
                text=row["control_statement"], uuid=f"{source}:row-{n}:control", kind=CONTROL_STATEMENT,
                component=label, policy_intent=intent, policy_ids=policy_ids,
                risk_statement=(linked.text or None) if linked else None, **common,
            ))
        if row.get("implementation_statement"):
            # How the control is met is checked against the control statement, unless the catalog text is given.
            out.append(Statement(
                text=row["implementation_statement"], uuid=f"{source}:row-{n}:implementation", kind=IMPLEMENTATION,
                component=label, policy_intent=intent, policy_ids=policy_ids, control_id=control, source=source,
                requirement=requirement or row.get("control_statement") or None,
            ))
        if row.get("risk_statement"):
            out.append(Statement(
                text=row["risk_statement"], uuid=f"{source}:row-{n}:risk", kind=RISK_STATEMENT, title=label,
                policy_intent=intent, policy_ids=policy_ids, ratings=ratings, **common,
            ))
        if row.get("recommendation"):
            out.append(Statement(
                text=row["recommendation"], uuid=f"{source}:row-{n}:recommendation", kind=RECOMMENDATION,
                title=label, risk_title=label, risk_statement=row.get("risk_statement") or None, ratings=ratings,
                owner=row.get("owner") or None, deadline=row.get("target_date") or None,
                control_id=control, source=source,
            ))
    for risk in risks.values():
        if not risk.text:
            raise ValueError(f"risk id {risk.title} has no identified risk text in any of its rows")
    if not out:
        raise ValueError("CSV has the right columns but no statements to assess: fill in at least one of "
                         "control statement, implementation statement, risk statement, recommendation or "
                         "identified risk")
    return out


def _link_risk(row: dict, n: int, source: str, risks: dict[str, Statement], out: list[Statement]) -> Statement:
    """Add this row's policy intent and statements as a treatment of its identified risk, and return the risk."""
    text = row.get("identified_risk", "")
    key = (row.get("risk_id") or " ".join(text.lower().split())).lower()
    risk = risks.get(key)
    if risk is None:
        risk = Statement(control_id="", text=text, source=source, uuid=f"{source}:risk-{len(risks) + 1}",
                         kind=IDENTIFIED_RISK, title=row.get("risk_id") or _short(text))
        risks[key] = risk
        out.append(risk)
    elif text and not risk.text:
        risk.text = text
    for k in ("likelihood", "impact"):
        if row.get(k) and k not in risk.ratings:
            risk.ratings[k] = row[k]
    if any(row.get(k) for k in ("policy_intent", "control_statement", "implementation_statement")):
        risk.treatments.append(Treatment(
            label=row.get("title") or row.get("control_id") or f"Row {n}",
            policy_intent=row.get("policy_intent") or None,
            control_statement=row.get("control_statement") or None,
            control_id=row.get("control_id") or None,
            implementation_statement=row.get("implementation_statement") or None,
        ))
    return risk


def _short(text: str, words: int = 8) -> str:
    parts = text.split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")
