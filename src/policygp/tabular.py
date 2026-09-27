"""Statements from a CSV file: one row per policy, followed down the golden path.

Each row carries one policy intent and the text written for it. These four
columns are required (a cell may be left empty when a row has nothing for it):

    policy intent       what the organization's policy says the control must achieve
    control statement   how the control is implemented today
    risk statement      where practice falls short, and what it could cost
    recommendation      how to close the gap

A row yields up to three items to assess, checked along the path: the control
statement and the risk statement against the row's policy intent, and the
recommendation against the row's risk statement.

Optional columns add context:

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

from .models import IMPLEMENTATION, RECOMMENDATION, RISK_STATEMENT, Statement

REQUIRED = ("policy_intent", "control_statement", "risk_statement", "recommendation")
OPTIONAL = ("control_id", "control_requirement", "title", "likelihood", "impact", "owner", "target_date")
COLUMNS = REQUIRED + OPTIONAL

LABELS = {
    "policy_intent": "policy intent", "control_statement": "control statement", "risk_statement": "risk statement",
    "recommendation": "recommendation", "control_id": "control id", "control_requirement": "control requirement",
    "title": "title", "likelihood": "likelihood", "impact": "impact", "owner": "owner", "target_date": "target date",
}

# Other names people use for the same columns.
_ALIASES = {
    "policy": "policy_intent", "intent": "policy_intent",
    "implementation_statement": "control_statement", "control_implementation": "control_statement",
    "implementation": "control_statement", "statement": "control_statement",
    "risk": "risk_statement",
    "recommendations": "recommendation", "remediation": "recommendation",
    "control": "control_id", "control_ref": "control_id",
    "requirement": "control_requirement", "control_text": "control_requirement",
    "deadline": "target_date", "due_date": "target_date", "date": "target_date",
}

EXAMPLE_ROWS = [
    {
        "policy_intent": "User access is reviewed at a frequency commensurate with the risk of the access, and "
                         "access that is no longer needed is removed within 5 business days.",
        "control_statement": "Accounts are tiered in the annual access risk assessment owned by the CISO: Tier 1 "
                             "covers privileged and payment access, Tier 2 everything else. Managers review Tier 1 "
                             "access quarterly and Tier 2 annually in Okta, and unneeded access is removed within "
                             "2 business days. Tiers are reassessed after major changes. Each review is recorded "
                             "in a ServiceNow ticket.",
        "risk_statement": "14 of 60 sampled Okta accounts belonged to leavers, which does not meet AC-2 and the "
                          "Access Control Policy, because leaver notices are processed manually. A former "
                          "employee could use them to approve fraudulent payments, causing financial loss; the "
                          "accounts are internet-facing, so exploitation is likely.",
        "recommendation": "Integrate Workday with Okta so leaver notices disable accounts automatically instead of "
                          "being processed manually. The IAM team lead owns this. Verify closure by re-sampling "
                          "60 accounts.",
        "control_id": "ac-2", "title": "Leaver accounts", "likelihood": "high", "impact": "high",
        "owner": "IAM team lead", "target_date": "2026-11-30",
    },
    {
        "policy_intent": "Security events are reviewed daily and audit logs are retained for at least 3 years.",
        "control_statement": "Logs are reviewed periodically as needed.",
        "risk_statement": "Audit logs are not always reviewed which could be a risk.",
        "recommendation": "Consider improving log review where possible.",
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
    widths = [45, 60, 60, 50, 12, 40, 18, 11, 11, 16, 12]
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
    for n, raw in enumerate(reader, start=2):
        row = {fields[k]: (v or "").strip() for k, v in raw.items() if k in fields}
        if not any(row.get(c) for c in ("control_statement", "risk_statement", "recommendation")):
            continue  # nothing to assess on this row
        label = row.get("title") or f"Row {n}"
        control = row.get("control_id", "")
        intent = row.get("policy_intent") or None
        requirement = row.get("control_requirement") or None
        ratings = {k: row[k] for k in ("likelihood", "impact") if row.get(k)}
        common = dict(control_id=control, source=source, requirement=requirement)

        if row.get("control_statement"):
            out.append(Statement(
                text=row["control_statement"], uuid=f"{source}:row-{n}:control", kind=IMPLEMENTATION,
                component=label, policy_intent=intent, policy_ids=[f"row {n}"] if intent else [], **common,
            ))
        if row.get("risk_statement"):
            out.append(Statement(
                text=row["risk_statement"], uuid=f"{source}:row-{n}:risk", kind=RISK_STATEMENT, title=label,
                policy_intent=intent, policy_ids=[f"row {n}"] if intent else [], ratings=ratings, **common,
            ))
        if row.get("recommendation"):
            out.append(Statement(
                text=row["recommendation"], uuid=f"{source}:row-{n}:recommendation", kind=RECOMMENDATION,
                title=label, risk_title=label, risk_statement=row.get("risk_statement") or None, ratings=ratings,
                owner=row.get("owner") or None, deadline=row.get("target_date") or None,
                control_id=control, source=source,
            ))
    if not out:
        raise ValueError("CSV has the right columns but no statements to assess: fill in at least one of "
                         "control statement, risk statement or recommendation")
    return out
