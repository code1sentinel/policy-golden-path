"""The Codify request API, shared by the local server and the browser build.

`handle(json_text)` takes {"action": ..., ...} and returns JSON; the local server
(webapp.py) calls the same functions for POST /api. Nothing here does I/O, and
the project lives in the page: each call is given what it needs.

    open      a policy file or pasted text (or a saved OSCAL catalog) -> project, with scores
    check     one control statement -> score, best practices, improvements and its parts
    score     a whole project -> scores for every control
    redraft   one clause -> rule-based control drafts
    export    a project -> OSCAL catalog, Excel, CSV or Markdown report
"""

from __future__ import annotations

import base64
import binascii
import json
import re

from . import __version__
from .classify import TYPE_LABELS, TYPES
from .clauses import read_policy
from .control import assess_control_statement, parts
from .guides import ADOPTED, GUIDE, PARTLY, STATUS_LABELS
from .models import Statement
from .project import (
    ORIGINS, STATUSES, draft_controls, from_oscal, new_project, summary, to_csv, to_oscal, to_report, to_xlsx,
)

MAX_TEXT = 20000  # characters per field
MAX_CLAUSES = 5000
MAX_CONTROLS = 10000


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

def _clean_project(value) -> dict:
    """A project sent back by the page, checked field by field."""
    if not isinstance(value, dict):
        raise BadRequest("'project' must be an object")
    clauses, controls = value.get("clauses"), value.get("controls")
    if not isinstance(clauses, list) or not isinstance(controls, list):
        raise BadRequest("'project' needs 'clauses' and 'controls' lists")
    if len(clauses) > MAX_CLAUSES or len(controls) > MAX_CONTROLS:
        raise BadRequest("project is too large")
    out = {"uuid": _text(value.get("uuid"), "uuid", 64), "title": _text(value.get("title"), "title", 500),
           "source": _text(value.get("source"), "source", 500), "version": __version__,
           "clauses": [], "controls": []}
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
        out["controls"].append({
            "id": _text(c.get("id"), "control id", 64) or "?", "clause": _text(c.get("clause"), "clause", 64),
            "text": _text(c.get("text"), "text"), "guidance": _text(c.get("guidance"), "guidance"),
            "risk": _text(c.get("risk"), "risk"), "who": _text(c.get("who"), "who", 500),
            "notes": [_text(n, "note", 2000) for n in notes[:50]],
            "status": c.get("status") if c.get("status") in STATUSES else "draft",
            "origin": c.get("origin") if c.get("origin") in ORIGINS else "person",
        })
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
            if body.get("title"):
                project["title"] = _text(body["title"], "title", 500)
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


def _filename(project: dict, suffix: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "-", project.get("title") or "policy").strip("-").lower()[:60] or "policy"
    return f"{stem}-{suffix}"


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
    raise BadRequest("'format' must be oscal, csv, xlsx or report")


def config() -> dict:
    return {"version": __version__, "types": TYPE_LABELS, "statuses": list(STATUSES),
            "adopted": ADOPTED, "partly": PARTLY, "status_labels": STATUS_LABELS}


def guide() -> dict:
    return {"guide": GUIDE, "statuses": STATUS_LABELS, "adopted": ADOPTED, "partly": PARTLY}


ACTIONS = {"open": open_policy, "check": check, "score": score, "redraft": redraft, "export": export}


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
