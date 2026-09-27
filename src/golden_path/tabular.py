"""Statements from a CSV file, for batches that are not (yet) OSCAL.

One row per item. `text` is required; everything else is optional:

    kind            implementation (default), risk-statement or recommendation
    control_id      e.g. ac-2
    statement_id    e.g. ac-2_smt.j
    component       where it is implemented
    title           risk or recommendation title
    text            the statement, risk statement or recommendation
    requirement     control text, when no catalog is supplied
    policy_intent   policy intent for this row
    risk_statement  for a recommendation: the risk it responds to
    likelihood, impact, risk   ratings for a risk statement or recommendation
    owner, deadline recommendation owner and target date

Header names are case-insensitive, and spaces or hyphens count as underscores.
"""

from __future__ import annotations

import csv
import io

from .models import IMPLEMENTATION, KIND_LABELS, RECOMMENDATION, RISK_STATEMENT, Statement

COLUMNS = ("kind", "control_id", "statement_id", "component", "title", "text", "requirement", "policy_intent",
           "risk_statement", "likelihood", "impact", "risk", "owner", "deadline")
_KINDS = {
    "": IMPLEMENTATION, "implementation": IMPLEMENTATION, "implementation statement": IMPLEMENTATION,
    "control statement": IMPLEMENTATION, "risk": RISK_STATEMENT, "risk statement": RISK_STATEMENT,
    "risk-statement": RISK_STATEMENT, "recommendation": RECOMMENDATION,
}


def template() -> str:
    """A CSV template with one example row of each kind."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(COLUMNS)
    w.writerow(["implementation", "ac-2", "ac-2_smt.j", "Okta", "", "The IAM team reviews all user accounts "
                "quarterly in Okta; each review is recorded in a ServiceNow ticket.", "", "", "", "", "", "", "", ""])
    w.writerow(["risk-statement", "ac-2", "", "", "Leaver accounts remain active", "14 of 60 sampled accounts "
                "belonged to leavers because deprovisioning is manual.", "", "", "", "high", "high", "", "", ""])
    w.writerow(["recommendation", "ac-2", "", "", "Automate deprovisioning", "Integrate Workday with Okta to "
                "disable leaver accounts automatically.", "", "", "14 of 60 sampled accounts belonged to leavers "
                "because deprovisioning is manual.", "", "", "high", "IAM team lead", "2026-11-30"])
    return out.getvalue()


def parse_csv(content: str, source: str = "csv") -> list[Statement]:
    reader = csv.DictReader(io.StringIO(content.lstrip("﻿")))
    if not reader.fieldnames:
        raise ValueError("CSV file is empty")
    fields = {f: f.strip().lower().replace(" ", "_").replace("-", "_") for f in reader.fieldnames if f}
    if "text" not in fields.values():
        raise ValueError("CSV needs a 'text' column; download the template for the full set of columns")
    out = []
    for n, raw in enumerate(reader, start=2):
        row = {fields[k]: (v or "").strip() for k, v in raw.items() if k in fields}
        if not any(row.values()):
            continue
        kind = _KINDS.get(row.get("kind", "").lower())
        if kind is None:
            raise ValueError(f"CSV row {n}: unknown kind {row['kind']!r}; use one of "
                             + ", ".join(KIND_LABELS))
        ratings = {k: row[k] for k in ("likelihood", "impact", "risk") if row.get(k)}
        out.append(Statement(
            control_id=row.get("control_id", ""),
            text=row.get("text", ""),
            source=source,
            uuid=f"{source}:row-{n}",
            statement_id=row.get("statement_id") or None,
            component=row.get("component") or None,
            requirement=row.get("requirement") or None,
            policy_intent=row.get("policy_intent") or None,
            policy_ids=["csv"] if row.get("policy_intent") else [],
            kind=kind,
            title=row.get("title") or (None if kind == IMPLEMENTATION else f"Row {n}"),
            risk_statement=row.get("risk_statement") or None,
            ratings=ratings,
            owner=row.get("owner") or None,
            deadline=row.get("deadline") or None,
        ))
    return out
