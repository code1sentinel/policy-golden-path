"""The Codify request API, shared by the local server and the browser build.

`handle(json_text)` takes {"action": ..., ...} and returns JSON; the local server
(webapp.py) calls the same functions for POST /api. Nothing here does I/O, and
the project lives in the page: each call is given what it needs.

    open          a policy file or pasted text (or a saved OSCAL catalog) -> project, with scores
    check         one control statement -> score, best practices, improvements and its parts
    score         a whole project -> scores for every control
    redraft       one clause -> rule-based control drafts
    import_risks  a local CSV/JSON risk register -> parsed risks (never uploaded)
    suggest_risk_controls  one risk -> deterministic template suggestions
    draft_risk_controls    one risk -> project controls from selected templates
    export        a project -> OSCAL catalog, Excel, CSV, Markdown report, or risk CSV
    control_oscal one control in a project -> that control's OSCAL 1.1.2 object
    ai_prompt     one clause or risk -> the prompt the page sends to the person's AI provider
    ai_reply      the provider's reply -> control drafts marked as drafted by AI, with scores
"""

from __future__ import annotations

import base64
import binascii
import json
import re

from . import __version__, ai
from .classify import TYPE_LABELS, TYPES
from .clauses import read_policy
from .control import assess_control_statement, parts
from .guides import ADOPTED, GUIDE, PARTLY, STATUS_LABELS
from .models import Statement
from .project import (
    ORIGINS, STATUSES, control_oscal, draft_controls, empty_project, from_oscal, merge_risks,
    new_project, summary, to_csv, to_oscal, to_report, to_xlsx,
)
from .risks import (
    CSV_HEADER, STATUSES as RISK_STATUSES, draft_from_templates, normalize_risk, parse_csv,
    parse_register, suggest_templates, to_csv_register,
)

MAX_TEXT = 20000  # characters per field
MAX_CLAUSES = 5000
MAX_CONTROLS = 10000
MAX_RISKS = 2000


class BadRequest(Exception):
    """A request the caller can fix; `status` is the HTTP status the server answers with."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _text(value, name: str, limit: int = MAX_TEXT) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise BadRequest(f"'{name}' must be text")
    if len(value) > limit:
        raise BadRequest(f"'{name}' is longer than {limit} characters")
    return value.strip()


# --- Scoring ------------------------------------------------------------------------------------------

def _assess(text: str, risk: str = "", requirement: str = "", policy_intent: str = ""):
    return assess_control_statement(Statement("", text, requirement=requirement or None,
                                              policy_intent=policy_intent or None, risk_statement=risk or None))


def check(body: dict) -> dict:
    text = _text(body.get("text"), "text")
    if not text:
        raise BadRequest("enter a control statement to check")
    a = _assess(text, _text(body.get("risk"), "risk"), _text(body.get("requirement"), "requirement"),
                _text(body.get("policy_intent"), "policy_intent"))
    return {"assessment": a.to_dict(), "parts": parts(text)}


def _scores(project: dict) -> dict[str, dict]:
    out = {}
    for c in project["controls"]:
        a = _assess(c["text"], c.get("risk", ""))
        out[c["id"]] = {"confidence": round(a.confidence, 4), "improvements": a.improvements}
    return out


# --- Projects -----------------------------------------------------------------------------------------

def _clean_risk(value, index: int) -> dict:
    if not isinstance(value, dict):
        raise BadRequest("each risk must be an object")
    try:
        return normalize_risk(value, index=index)
    except ValueError as exc:
        raise BadRequest(str(exc)) from None


def _clean_project(value) -> dict:
    """A project sent back by the page, checked field by field."""
    if not isinstance(value, dict):
        raise BadRequest("'project' must be an object")
    clauses, controls = value.get("clauses"), value.get("controls")
    if not isinstance(clauses, list) or not isinstance(controls, list):
        raise BadRequest("'project' needs 'clauses' and 'controls' lists")
    risks = value.get("risks") or []
    if not isinstance(risks, list):
        raise BadRequest("'risks' must be a list")
    if len(clauses) > MAX_CLAUSES or len(controls) > MAX_CONTROLS or len(risks) > MAX_RISKS:
        raise BadRequest("project is too large")
    out = {"uuid": _text(value.get("uuid"), "uuid", 64), "title": _text(value.get("title"), "title", 500),
           "source": _text(value.get("source"), "source", 500), "version": __version__,
           "clauses": [], "controls": [], "risks": []}
    for c in clauses:
        if not isinstance(c, dict):
            raise BadRequest("each clause must be an object")
        kind = c.get("type")
        if kind not in TYPES:
            raise BadRequest(f"unknown clause type {kind!r}")
        out["clauses"].append({"id": _text(c.get("id"), "clause id", 64) or "?", "text": _text(c.get("text"), "text"),
                               "section": _text(c.get("section"), "section", 64),
                               "heading": _text(c.get("heading"), "heading", 500), "type": kind,
                               "reason": _text(c.get("reason"), "reason", 500),
                               "duplicate_of": _text(c.get("duplicate_of"), "duplicate_of", 64) or None})
    for c in controls:
        if not isinstance(c, dict):
            raise BadRequest("each control must be an object")
        notes = c.get("notes") or []
        if not isinstance(notes, list):
            raise BadRequest("'notes' must be a list")
        source_type = c.get("source_type") if c.get("source_type") in ("clause", "risk") else (
            "risk" if c.get("risk_id") else "clause")
        out["controls"].append({
            "id": _text(c.get("id"), "control id", 64) or "?", "clause": _text(c.get("clause"), "clause", 64),
            "text": _text(c.get("text"), "text"), "guidance": _text(c.get("guidance"), "guidance"),
            "risk": _text(c.get("risk"), "risk"), "who": _text(c.get("who"), "who", 500),
            "notes": [_text(n, "note", 2000) for n in notes[:50]],
            "status": c.get("status") if c.get("status") in STATUSES else "draft",
            "origin": c.get("origin") if c.get("origin") in ORIGINS else "person",
            "source_type": source_type,
            "risk_id": _text(c.get("risk_id"), "risk_id", 64),
        })
    for i, r in enumerate(risks):
        out["risks"].append(_clean_risk(r, i))
    return out


def _upload(body: dict) -> tuple[str, str | bytes]:
    name = str(body.get("name") or "pasted text")
    if isinstance(body.get("content_base64"), str):
        try:
            return name, base64.b64decode(body["content_base64"], validate=True)
        except (binascii.Error, ValueError):
            raise BadRequest(f"{name}: content_base64 is not valid base64") from None
    if isinstance(body.get("text"), str):
        return name, _text(body["text"], "text", 2_000_000)
    if isinstance(body.get("content"), str):
        return name, body["content"]
    raise BadRequest("send a file ('name' with 'content' or 'content_base64'), or pasted 'text'")


def open_policy(body: dict) -> dict:
    """A project from a policy (pasted text, .docx, .csv, .xlsx) or a saved OSCAL catalog (.json)."""
    name, content = _upload(body)
    try:
        if name.lower().endswith(".json"):
            raw = content.decode("utf-8-sig") if isinstance(content, bytes) else content
            project = from_oscal(json.loads(raw))
        else:
            project = new_project(read_policy(name, content), source=name if body.get("name") else "")
    except json.JSONDecodeError as exc:
        raise BadRequest(f"{name}: not valid JSON ({exc.msg})") from None
    except (ValueError, KeyError, TypeError) as exc:
        raise BadRequest(f"{name}: {exc}") from None
    return {"project": project, "summary": summary(project), "scores": _scores(project)}


def score(body: dict) -> dict:
    project = _clean_project(body.get("project"))
    return {"summary": summary(project), "scores": _scores(project)}


def redraft(body: dict) -> dict:
    clause_id = _text(body.get("clause_id"), "clause_id", 64)
    text = _text(body.get("text"), "text")
    if not text:
        raise BadRequest("the clause has no text")
    controls = draft_controls(clause_id, text)
    return {"controls": controls, "scores": _scores({"controls": controls})}


def _risk_from_body(body: dict) -> dict:
    raw = body.get("risk")
    if not isinstance(raw, dict):
        raise BadRequest("'risk' must be an object")
    return _clean_risk(raw, 0)


def import_risks(body: dict) -> dict:
    """Parse a local CSV/JSON register. Nothing is stored or uploaded."""
    name, content = _upload(body)
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    mapping = body.get("mapping") if isinstance(body.get("mapping"), dict) else None
    try:
        if mapping is not None:
            parsed = parse_csv(text, mapping=mapping)
        else:
            parsed = parse_register(name, text)
    except ValueError as exc:
        raise BadRequest(str(exc)) from None
    out = {"risks": parsed["risks"], "errors": parsed.get("errors") or [],
           "columns": parsed.get("columns") or [], "recognised": parsed.get("recognised") or [],
           "unknown": parsed.get("unknown") or [], "header": list(CSV_HEADER)}
    if body.get("apply"):
        project = _clean_project(body["project"]) if body.get("project") else empty_project()
        project = merge_risks(project, parsed["risks"], draft=False)
        out["project"] = project
        out["summary"] = summary(project)
        out["scores"] = _scores(project)
    return out


def suggest_risk_controls(body: dict) -> dict:
    risk = _risk_from_body(body)
    return {"risk": risk, "suggestions": suggest_templates(risk)}


def draft_risk_controls(body: dict) -> dict:
    risk = _risk_from_body(body)
    ids = body.get("template_ids")
    if ids is not None and not isinstance(ids, list):
        raise BadRequest("'template_ids' must be a list")
    template_ids = [str(x) for x in ids] if ids else None
    controls = draft_from_templates(risk, template_ids)
    if not controls:
        raise BadRequest("no templates matched that risk")
    return {"controls": controls, "scores": _scores({"controls": controls})}


def ai_prompt(body: dict) -> dict:
    if isinstance(body.get("risk"), dict):
        risk = _risk_from_body(body)
        return ai.risk_prompt(risk)
    text = _text(body.get("text"), "text")
    if not text:
        raise BadRequest("the clause has no text")
    return ai.prompt(_text(body.get("clause_id"), "clause_id", 64), text, _text(body.get("heading"), "heading", 500))


def ai_reply(body: dict) -> dict:
    source_type = body.get("source_type") if body.get("source_type") in ("clause", "risk") else (
        "risk" if body.get("risk_id") else "clause")
    risk_id = _text(body.get("risk_id"), "risk_id", 64)
    try:
        controls = ai.from_reply(_text(body.get("clause_id"), "clause_id", 64),
                                 _text(body.get("reply"), "reply", ai.MAX_REPLY), _text(body.get("model"), "model", 100),
                                 source_type=source_type, risk_id=risk_id)
    except ValueError as exc:
        raise BadRequest(str(exc)) from None
    return {"controls": controls, "scores": _scores({"controls": controls})}


def _filename(project: dict, suffix: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "-", project.get("title") or "policy").strip("-").lower()[:60] or "policy"
    return f"{stem}-{suffix}"


def control_oscal_action(body: dict) -> dict:
    project = _clean_project(body.get("project"))
    control_id = _text(body.get("control_id"), "control_id", 64)
    if not control_id:
        raise BadRequest("enter a control id")
    try:
        return {"control": control_oscal(project, control_id)}
    except KeyError as exc:
        raise BadRequest(str(exc)) from None


def export(body: dict) -> dict:
    project = _clean_project(body.get("project"))
    fmt = body.get("format")
    scores = {k: v["confidence"] for k, v in _scores(project).items()}
    if fmt == "oscal":
        return {"name": _filename(project, "catalog.json"), "mime": "application/json",
                "content": json.dumps(to_oscal(project), indent=2)}
    if fmt == "csv":
        return {"name": _filename(project, "controls.csv"), "mime": "text/csv", "content": to_csv(project, scores)}
    if fmt == "xlsx":
        return {"name": _filename(project, "controls.xlsx"),
                "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "content_base64": base64.b64encode(to_xlsx(project, scores)).decode()}
    if fmt == "report":
        improvements = {k: v["improvements"] for k, v in _scores(project).items()}
        return {"name": _filename(project, "report.md"), "mime": "text/markdown",
                "content": to_report(project, scores, improvements)}
    if fmt == "risks":
        return {"name": _filename(project, "risks.csv"), "mime": "text/csv",
                "content": to_csv_register(project.get("risks") or [])}
    raise BadRequest("'format' must be oscal, csv, xlsx, report or risks")


def config() -> dict:
    return {"version": __version__, "types": TYPE_LABELS, "statuses": list(STATUSES),
            "risk_statuses": list(RISK_STATUSES), "header": list(CSV_HEADER),
            "adopted": ADOPTED, "partly": PARTLY, "status_labels": STATUS_LABELS}


def guide() -> dict:
    return {"guide": GUIDE, "statuses": STATUS_LABELS, "adopted": ADOPTED, "partly": PARTLY}


ACTIONS = {"open": open_policy, "check": check, "score": score, "redraft": redraft, "export": export,
           "control_oscal": control_oscal_action, "ai_prompt": ai_prompt, "ai_reply": ai_reply,
           "import_risks": import_risks, "suggest_risk_controls": suggest_risk_controls,
           "draft_risk_controls": draft_risk_controls}


def call(body: dict) -> dict:
    if not isinstance(body, dict):
        raise BadRequest("request body must be a JSON object")
    action = ACTIONS.get(body.get("action"))
    if action is None:
        raise BadRequest(f"'action' must be one of: {', '.join(ACTIONS)}")
    return action(body)


def handle(request_json: str) -> str:
    """Browser entry point: JSON in, JSON out, errors as {"error", "status"} rather than exceptions."""
    try:
        body = json.loads(request_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "request is not valid JSON", "status": 400})
    try:
        return json.dumps(call(body))
    except BadRequest as exc:
        return json.dumps({"error": str(exc), "status": exc.status})
