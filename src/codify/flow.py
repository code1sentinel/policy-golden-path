"""Web authoring flow: two start paths, required steps, export gate ([ADR 0013](../../docs/adr/0013-risk-first-authoring-flow.md), [ADR 0020](../../docs/adr/0020-review-policy-as-code-page.md)).

Identified risks stay input, not a register. CLI export is not gated; `can_export`
is the wizard rule. Review completeness is coverage, not Accept.
"""

from __future__ import annotations

PATH_RISKS = "risks"
PATH_CLAUSES = "clauses"
STEPS = {
    PATH_RISKS: ("risks", "controls", "review"),
    PATH_CLAUSES: ("clause", "controls", "link", "review"),
}


def authoring_path(project: dict | None) -> str:
    if not isinstance(project, dict):
        return PATH_CLAUSES
    raw = project.get("authoring_path")
    if raw == PATH_RISKS:
        return PATH_RISKS
    return PATH_CLAUSES


def canonical_step(step: str | None) -> str:
    """Older saves used a separate enact step; that page is now review."""
    if step == "enact":
        return "review"
    return step or ""


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


def _clause_items(project: dict) -> list[dict]:
    clauses = [
        c for c in (project.get("clauses") or [])
        if isinstance(c, dict) and not c.get("duplicate_of")
    ]
    reqs = [c for c in clauses if c.get("type") == "requirement"]
    return reqs or clauses


def _clause_items_covered(project: dict) -> bool:
    items = _clause_items(project)
    if not items:
        return False
    controls = _controls(project)
    for clause in items:
        cid = clause.get("id")
        if not any(str(c.get("text") or "").strip() and c.get("clause") == cid for c in controls):
            return False
    return True


def step_complete(project: dict, step: str) -> bool:
    step = canonical_step(step)
    if step == "risks":
        return bool(_risks(project))
    if step == "controls":
        if authoring_path(project) == PATH_CLAUSES:
            return _clause_items_covered(project)
        return bool(_risks(project)) and not _uncovered_risk_ids(project)
    if step == "clause":
        return bool(_nonempty_controls(project)) or bool(project.get("clauses"))
    if step == "link":
        return bool(_risks(project)) and not _uncovered_risk_ids(project) and not _unlinked_control_ids(project)
    if step == "review":
        ok, _ = can_export(project)
        return ok
    return False


def can_advance(project: dict, step: str) -> tuple[bool, str]:
    """Whether the person may leave this step. Empty message when yes."""
    step = canonical_step(step)
    if step == "risks":
        if _risks(project):
            return True, ""
        return False, "Add at least one identified risk to continue."
    if step == "controls":
        if authoring_path(project) == PATH_CLAUSES:
            if not _clause_items_covered(project):
                return False, "Every clause needs at least one control statement."
            return True, ""
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
    return True, ""


def review_complete(project: dict) -> tuple[bool, str]:
    """Coverage gate for step 3 and web export ([ADR 0020](../../docs/adr/0020-review-policy-as-code-page.md))."""
    return can_export(project)


def can_export(project: dict) -> tuple[bool, str]:
    """Web wizard: every risk has a control statement; every control is linked."""
    if not _risks(project):
        return False, "Add at least one identified risk before exporting."
    if _unlinked_control_ids(project):
        return False, "Link every control statement to an identified risk before exporting."
    if _uncovered_risk_ids(project):
        return False, "Every risk needs a control statement before you can download the catalog."
    return True, ""


def first_incomplete_step(project: dict) -> str:
    path = authoring_path(project)
    for step in STEPS[path]:
        if not step_complete(project, step):
            return step
    return "review"
