"""Pull risk statements and recommendations out of OSCAL assessment results and POA&Ms.

Each risk yields its `statement` as a risk statement, and each of its
`remediations` with `lifecycle: recommendation` as a recommendation. A risk is
tied to controls through the findings that reference it (`related-risks`) and
their `target.target-id`.
"""

from __future__ import annotations

from .models import RECOMMENDATION, RISK_STATEMENT, Statement

RATING_FACETS = ("likelihood", "impact", "risk", "severity", "priority")


def extract_findings(data: dict) -> list[Statement]:
    if "assessment-results" in data:
        out: list[Statement] = []
        for result in data["assessment-results"].get("results", []):
            out += _from_container(result, "assessment-results")
        return out
    if "plan-of-action-and-milestones" in data:
        return _from_container(data["plan-of-action-and-milestones"], "poam")
    return []


def _from_container(container: dict, source: str) -> list[Statement]:
    controls = _controls_by_risk(container.get("findings", []))
    parties = {p["uuid"]: p.get("name", p["uuid"]) for p in container.get("parties", []) if "uuid" in p}
    out: list[Statement] = []
    for risk in container.get("risks", []):
        control = ", ".join(controls.get(risk.get("uuid"), []))
        ratings = _ratings(risk)
        title = risk.get("title")
        statement = risk.get("statement", "")
        out.append(Statement(
            control_id=control, text=statement, source=source, uuid=risk.get("uuid"),
            kind=RISK_STATEMENT, title=title, ratings=ratings, deadline=risk.get("deadline"),
        ))
        for rem in risk.get("remediations", []):
            if rem.get("lifecycle") != "recommendation":
                continue
            text = ". ".join(p.strip().rstrip(".") for p in (rem.get("title", ""), rem.get("description", ""))
                             if p.strip()) + "."
            out.append(Statement(
                control_id=control, text=text if text != "." else "", source=source, uuid=rem.get("uuid"),
                kind=RECOMMENDATION, title=rem.get("title"), risk_title=title,
                risk_statement=statement, ratings=ratings,
                deadline=_deadline(rem) or risk.get("deadline"), owner=_owner(rem, parties),
            ))
    return out


def _controls_by_risk(findings: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for f in findings:
        target = f.get("target", {}).get("target-id")
        if not target:
            continue
        for rel in f.get("related-risks", []):
            ids = out.setdefault(rel.get("risk-uuid"), [])
            if target not in ids:
                ids.append(target)
    return out


def _ratings(risk: dict) -> dict[str, str]:
    ratings: dict[str, str] = {}
    for ch in risk.get("characterizations", []):
        for facet in ch.get("facets", []):
            name = facet.get("name", "").lower()
            if name in RATING_FACETS:
                ratings[name] = str(facet.get("value", ""))
    return ratings


def _deadline(rem: dict) -> str | None:
    for task in rem.get("tasks", []):
        timing = task.get("timing", {})
        if "on-date" in timing:
            return timing["on-date"].get("date")
        if "within-date-range" in timing:
            return timing["within-date-range"].get("end")
    return None


def _owner(rem: dict, parties: dict[str, str]) -> str | None:
    names = []
    for task in rem.get("tasks", []):
        for role in task.get("responsible-roles", []):
            names.append(role.get("role-id", ""))
    for origin in rem.get("origins", []):
        for actor in origin.get("actors", []):
            if actor.get("type") == "party":
                names.append(parties.get(actor.get("actor-uuid"), actor.get("actor-uuid", "")))
    names = [n for n in names if n]
    return ", ".join(dict.fromkeys(names)) or None
