"""Risk-first authoring flow (ADR 0013): required steps, export gating, back-compat."""

from pathlib import Path

from codify.clauses import parse_text
from codify.flow import (
    PATH_CLAUSES,
    PATH_RISKS,
    STEPS,
    authoring_path,
    can_advance,
    can_export,
    first_incomplete_step,
    step_complete,
)
from codify.project import empty_project, new_project
from codify.risks import coverage, normalize_project

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")

HUMAN_ERROR = "Company data is breached due to human error and misunderstanding of company requirements."
LOCK = "Require users to lock screens when they leave their desk."


def _clause_project():
    return new_project(parse_text("Users shall lock screens."), source="")


def _risk(rid="R-001", statement=HUMAN_ERROR, note=""):
    return {"id": rid, "statement": statement, "note": note}


def _control(cid="c1", text=LOCK, risk_ids=None, status="draft", clause="c1"):
    return {
        "id": cid, "clause": clause, "text": text, "guidance": "", "risk": "",
        "who": "", "notes": [], "status": status, "origin": "person",
        "source_type": "clause", "risk_ids": list(risk_ids or []),
    }


def test_missing_authoring_path_is_clause_first():
    project = _clause_project()
    assert "authoring_path" not in project or project.get("authoring_path") in (None, "", PATH_CLAUSES)
    assert authoring_path(project) == PATH_CLAUSES
    assert authoring_path(normalize_project(project)) == PATH_CLAUSES
    assert authoring_path({"controls": [], "clauses": [], "risks": []}) == PATH_CLAUSES
    assert STEPS[PATH_RISKS] == ("risks", "controls", "review")
    assert STEPS[PATH_CLAUSES] == ("clause", "controls", "link", "review")


def test_risk_path_requires_at_least_one_identified_risk():
    project = empty_project(authoring_path=PATH_RISKS)
    assert authoring_path(project) == PATH_RISKS
    assert step_complete(project, "risks") is False
    ok, message = can_advance(project, "risks")
    assert ok is False
    assert "risk" in message.lower()
    project["risks"] = [_risk()]
    assert step_complete(project, "risks") is True
    ok, message = can_advance(project, "risks")
    assert ok is True
    assert message == ""


def test_controls_step_requires_a_non_empty_statement_per_risk():
    project = empty_project(authoring_path=PATH_RISKS, risks=[_risk(), _risk("R-002", "Screens left unlocked.")])
    ok, message = can_advance(project, "controls")
    assert ok is False
    assert "control" in message.lower()
    project["controls"] = [_control(text="  ", risk_ids=["R-001"])]
    ok, _ = can_advance(project, "controls")
    assert ok is False
    project["controls"] = [
        _control(cid="a", text=LOCK, risk_ids=["R-001"]),
        _control(cid="b", text="Review access at least every [90] days.", risk_ids=["R-002"]),
    ]
    ok, message = can_advance(project, "controls")
    assert ok is True
    assert message == ""


def test_clause_path_link_step_requires_every_control_linked_and_every_risk_covered():
    project = _clause_project()
    project["authoring_path"] = PATH_CLAUSES
    assert step_complete(project, "clause") is True
    ok, message = can_advance(project, "link")
    assert ok is False
    project["risks"] = [_risk()]
    ok, message = can_advance(project, "link")
    assert ok is False
    assert "link" in message.lower() or "risk" in message.lower()
    project["controls"][0]["risk_ids"] = ["R-001"]
    project["controls"][0]["text"] = LOCK
    ok, message = can_advance(project, "link")
    assert ok is True
    flags = coverage(project)
    assert flags["uncovered_risk_ids"] == []
    assert flags["unlinked_control_ids"] == []


def test_export_blocked_until_every_risk_has_a_control_statement():
    project = empty_project(
        authoring_path=PATH_RISKS,
        risks=[_risk()],
        controls=[_control(text="  ", risk_ids=["R-001"], status="draft")],
    )
    ok, message = can_export(project)
    assert ok is False
    assert "control statement" in message.lower()
    assert "accept" not in message.lower()
    project["controls"][0]["text"] = LOCK
    ok, message = can_export(project)
    assert ok is True
    assert message == ""
    project["controls"].append(_control(cid="orphan", text="Encrypt laptops at rest.", risk_ids=[], status="draft"))
    ok, message = can_export(project)
    assert ok is False
    assert "link" in message.lower() or "risk" in message.lower()


def test_old_clause_first_project_opens_on_path_b_and_is_not_export_ready():
    leftover = _clause_project()
    leftover.pop("authoring_path", None)
    leftover["risks"] = []
    cleaned = normalize_project(leftover)
    assert authoring_path(cleaned) == PATH_CLAUSES
    assert first_incomplete_step(cleaned) == "link"
    ok, _ = can_export(cleaned)
    assert ok is False
    assert step_complete(cleaned, "clause") is True
    assert step_complete(cleaned, "link") is False


def test_cli_shaped_project_without_risks_still_builds():
    """CLI / scripts are not gated; can_export is the web wizard rule."""
    project = _clause_project()
    assert project["controls"]
    assert authoring_path(project) == PATH_CLAUSES
    ok, _ = can_export(project)
    assert ok is False


def test_shell_has_two_start_paths_stepper_guides_and_enact_handoff():
    assert 'id="start-from-risks"' in INDEX
    assert 'id="start-from-clause"' in INDEX
    assert "Get started" in INDEX
    assert 'id="stepper"' in INDEX
    assert 'id="step-guide"' in INDEX
    assert 'id="flow-next"' in INDEX
    assert "Policy as code (Rego)" in JS
    assert "review-page" in JS
    assert "Opens in Enact" in JS
    assert "code1sentinel.github.io/enact" in INDEX
    assert "Using Codify with Enact" in INDEX or "enact.md" in INDEX
    assert "body:has(#work:not([hidden])) #flow" in CSS
    assert "likelihood" not in INDEX.lower()
    assert "heatmap" not in JS.lower()
    assert "authoring_path" in JS or "authoringPath" in JS
    assert "canExport" in JS
    assert "the risk it treats" in JS
    assert ".stepper" in CSS
    assert ".step-guide" in CSS
    assert ".landing-hero" in CSS or ".how-card" in CSS
    assert "data-export=\"oscal\"" in INDEX
