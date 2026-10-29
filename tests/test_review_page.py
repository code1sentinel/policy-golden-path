"""Review + Policy as code (Rego) step 3: coverage gate and page chrome."""

from pathlib import Path

from codify.flow import (
    PATH_CLAUSES,
    PATH_RISKS,
    STEPS,
    can_export,
    first_incomplete_step,
    review_complete,
    step_complete,
)
from codify.project import empty_project

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")

LOCK = "Require users to lock screens when they leave their desk."
HUMAN_ERROR = "Company data is breached due to human error and misunderstanding of company requirements."


def _risk(rid="R-001", statement=HUMAN_ERROR, note=""):
    return {"id": rid, "statement": statement, "note": note}


def _control(cid="c1", text=LOCK, risk_ids=None, status="draft", clause="c1"):
    return {
        "id": cid, "clause": clause, "text": text, "guidance": "", "risk": "",
        "who": "", "notes": [], "status": status, "origin": "person",
        "source_type": "clause", "risk_ids": list(risk_ids or []),
    }


def test_last_step_is_review_not_a_separate_enact():
    assert STEPS[PATH_RISKS] == ("risks", "controls", "review")
    assert STEPS[PATH_CLAUSES] == ("clause", "controls", "link", "review")
    complete = empty_project(
        authoring_path=PATH_RISKS,
        risks=[_risk()],
        controls=[_control(text=LOCK, risk_ids=["R-001"], status="draft")],
    )
    assert first_incomplete_step(complete) == "review"
    assert step_complete(complete, "review") is True


def test_review_complete_when_every_risk_has_a_statement_even_if_draft():
    project = empty_project(
        authoring_path=PATH_RISKS,
        risks=[_risk()],
        controls=[_control(text=LOCK, risk_ids=["R-001"], status="draft")],
    )
    ok, message = review_complete(project)
    assert ok is True
    assert message == ""
    ok, message = can_export(project)
    assert ok is True
    assert message == ""


def test_review_incomplete_without_a_statement_or_a_link():
    missing = empty_project(authoring_path=PATH_RISKS, risks=[_risk()], controls=[])
    ok, message = review_complete(missing)
    assert ok is False
    assert "control statement" in message.lower()
    assert "accept" not in message.lower()

    unlinked = empty_project(
        authoring_path=PATH_RISKS,
        risks=[_risk()],
        controls=[_control(text=LOCK, risk_ids=["R-001"]), _control(cid="orphan", text="Encrypt laptops.", risk_ids=[])],
    )
    ok, message = can_export(unlinked)
    assert ok is False
    assert "link" in message.lower() or "risk" in message.lower()


def test_review_page_copy_is_policy_as_code_not_enact_or_club():
    body = JS.split("function renderReviewStep", 1)[1].split("function addControlForRisk", 1)[0]
    assert "Policy as code (Rego)" in body
    assert "review-page" in body
    assert "review-summary" in body
    assert "review-handoff" in body
    assert "Opens in Enact" in body
    assert "Generate Rego starter" in body
    assert "Starter to review" in body
    assert "not a finished policy" in body.lower()
    assert "Download OSCAL catalog" in body
    assert "GRC Engineering Club" not in body
    assert 'text: "Send to Enact"' not in body
    assert "review-edit-risks" in body
    assert "review-edit-statements" in body
    assert "oscal-catalog-json" in body
    assert ".review-page" in CSS
    assert "flow-view--review" in CSS
    assert "fonts.googleapis" not in CSS


def test_export_dialog_names_enact_only_as_support():
    dialog = INDEX.split('id="export-dialog"', 1)[1].split("</dialog>", 1)[0]
    assert "Download catalog" in dialog
    assert "Opens in Enact" in dialog or "code1sentinel.github.io/enact" in dialog
    assert "Nothing is uploaded" in dialog
    assert 'id="export-title">Send to Enact' not in dialog
