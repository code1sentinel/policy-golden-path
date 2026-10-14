"""Web authoring flow: two start paths, required steps, export gate ([ADR 0013](../../docs/adr/0013-risk-first-authoring-flow.md)).

Identified risks stay input, not a register. CLI export is not gated; `can_export`
is the wizard rule.
"""

from __future__ import annotations

PATH_RISKS = "risks"
PATH_CLAUSES = "clauses"
STEPS = {
    PATH_RISKS: ("risks", "controls", "review", "enact"),
    PATH_CLAUSES: ("clause", "link", "review", "enact"),
}


def authoring_path(project: dict | None) -> str:
    if not isinstance(project, dict):
        return PATH_CLAUSES
    raw = project.get("authoring_path")
    if raw == PATH_RISKS:
        return PATH_RISKS
    return PATH_CLAUSES


def _risks(project: dict) -> list[dict]:
    return [r for r in (project.get("risks") or []) if isinstance(r, dict) and str(r.get("statement") or "").strip()]


def _controls(project: dict) -> list[dict]:
    return [c for c in (project.get("controls") or []) if isinstance(c, dict)]


def _nonempty_controls(project: dict) -> list[dict]:
    return [c for c in _controls(project) if str(c.get("text") or "").strip()]


def _linked_ids(control: dict) -> list[str]:
    return [i for i in (control.get("risk_ids") or []) if i]


def _controls_for(project: dict, risk_id: str) -> list[dict]:
    return [c for c in _nonempty_controls(project) if risk_id in _linked_ids(c)]


def _uncovered_risk_ids(project: dict) -> list[str]:
    return [r["id"] for r in _risks(project) if r.get("id") and not _controls_for(project, r["id"])]


def _unlinked_control_ids(project: dict) -> list[str]:
    return [c.get("id") or "" for c in _nonempty_controls(project) if not _linked_ids(c)]


def _unaccepted_risk_ids(project: dict) -> list[str]:
    out = []
    for risk in _risks(project):
        rid = risk.get("id")
        if not rid:
            continue
        if not any(c.get("status") == "accepted" for c in _controls_for(project, rid)):
            out.append(rid)
    return out


def step_complete(project: dict, step: str) -> bool:
    if step == "risks":
        return bool(_risks(project))
    if step == "controls":
        return bool(_risks(project)) and not _uncovered_risk_ids(project)
    if step == "clause":
        return bool(_nonempty_controls(project)) or bool(project.get("clauses"))
    if step == "link":
        return bool(_risks(project)) and not _uncovered_risk_ids(project) and not _unlinked_control_ids(project)
    if step in ("review", "enact"):
        ok, _ = can_export(project)
        return ok
    return False


def can_advance(project: dict, step: str) -> tuple[bool, str]:
    """Whether the person may leave this step. Empty message when yes."""
    if step == "risks":
        if _risks(project):
            return True, ""
        return False, "Add at least one identified risk to continue."
    if step == "controls":
        missing = _uncovered_risk_ids(project)
        if not _risks(project) or missing:
            return False, "Every risk needs at least one control statement."
        return True, ""
    if step == "clause":
        if _nonempty_controls(project) or project.get("clauses"):
            return True, ""
        return False, "Paste a policy clause to draft control statements."
    if step == "link":
        if not _risks(project):
            return False, "Add at least one identified risk and link each control to it."
        if _unlinked_control_ids(project):
            return False, "Link every control statement to an identified risk."
        if _uncovered_risk_ids(project):
            return False, "Every risk needs at least one control statement."
        return True, ""
    if step == "review":
        return can_export(project)
    if step == "enact":
        return True, ""
    return True, ""


def can_export(project: dict) -> tuple[bool, str]:
    """Web wizard: every risk has an accepted control; every control is linked."""
    if not _risks(project):
        return False, "Add at least one identified risk before exporting."
    if _unlinked_control_ids(project):
        return False, "Link every control statement to an identified risk before exporting."
    if _unaccepted_risk_ids(project):
        return False, "Every risk needs an accepted control statement before you can send this to Enact."
    return True, ""


def first_incomplete_step(project: dict) -> str:
    path = authoring_path(project)
    for step in STEPS[path]:
        if not step_complete(project, step):
            return step
    return "enact"
