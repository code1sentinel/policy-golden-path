"""The Vitals request API, shared by the local server and the browser build.

`assess(body)` handles a single or batch health check and returns the result
as plain data. The local server (webapp.py) calls it for POST /api/assess; the
browser build calls `handle(json_text)` through Pyodide, so both run exactly
the same code. Nothing here does I/O.
"""

from __future__ import annotations

import base64
import binascii
import json
import re

from . import __version__, report
from .catalog import Catalog
from .guides import ADOPTED, GUIDES, PARTLY, STATUS_LABELS
from .models import IDENTIFIED_RISK, KIND_LABELS, RECOMMENDATION, RISK_STATEMENT, Statement, Treatment
from .policy import parse_policies
from .service import assess_all, parse_document, prepare


class BadRequest(Exception):
    """A request the caller can fix; `status` is the HTTP status the server answers with."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _text(value, name: str, limit: int = 20000) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise BadRequest(f"'{name}' must be text")
    if len(value) > limit:
        raise BadRequest(f"'{name}' is longer than {limit} characters")
    return value.strip()


_LABELLED = re.compile(r"^\s*([^:.]{1,60}):\s+(\S.*)$")
MAX_TREATMENTS = 50


def treatments(value) -> list[Treatment]:
    """Treatments of an identified risk: text with one per line ("Name: text" to label it), or a list of
    strings or of {"label", "policy_intent", "control_statement", "control_id"} objects."""
    if value in (None, ""):
        return []
    if isinstance(value, str):
        value = [line for line in value.splitlines() if line.strip()]
    if not isinstance(value, list):
        raise BadRequest("'treatments' must be text or a list")
    if len(value) > MAX_TREATMENTS:
        raise BadRequest(f"at most {MAX_TREATMENTS} treatments per risk")
    out = []
    for i, entry in enumerate(value, start=1):
        if isinstance(entry, dict):
            t = {k: _text(entry.get(k), k) for k in ("label", "policy_intent", "control_statement", "control_id")}
            if not (t["policy_intent"] or t["control_statement"]):
                raise BadRequest(f"treatment {i} needs a policy_intent or control_statement")
            out.append(Treatment(t["label"] or t["control_id"] or f"Treatment {i}", t["policy_intent"] or None,
                                 t["control_statement"] or None, t["control_id"] or None))
            continue
        line = _text(entry, f"treatments[{i}]")
        m = _LABELLED.match(line)
        label, text = (m.group(1).strip(), m.group(2).strip()) if m else (f"Treatment {i}", line)
        out.append(Treatment(label, policy_intent=text))
    return out


def single_statement(item: dict) -> Statement:
    if not isinstance(item, dict):
        raise BadRequest("'item' must be an object")
    kind = item.get("kind") or "implementation"
    if kind not in KIND_LABELS:
        raise BadRequest(f"unknown kind {kind!r}")
    t = {k: _text(item.get(k), k) for k in ("control_id", "statement_id", "component", "title", "text",
                                            "requirement", "policy_intent", "risk_statement", "owner",
                                            "deadline", "likelihood", "impact", "risk")}
    if not t["text"]:
        raise BadRequest("enter the text to assess")
    ratings = {k: t[k] for k in ("likelihood", "impact", "risk") if t[k]}
    if kind == IDENTIFIED_RISK:
        return Statement(control_id="", text=t["text"], source="single", kind=kind,
                         title=t["title"] or KIND_LABELS[kind], ratings=ratings,
                         treatments=treatments(item.get("treatments")))
    return Statement(
        control_id=t["control_id"], text=t["text"], source="single", uuid=None,
        statement_id=t["statement_id"] or None, component=t["component"] or None,
        requirement=t["requirement"] or None, policy_intent=t["policy_intent"] or None,
        policy_ids=["entered"] if t["policy_intent"] else [], kind=kind,
        title=t["title"] or (None if kind == "implementation" else KIND_LABELS[kind]),
        risk_statement=(t["risk_statement"] or None) if kind == RECOMMENDATION else None,
        ratings=ratings if kind in (RISK_STATEMENT, RECOMMENDATION) else {},
        owner=(t["owner"] or None) if kind == RECOMMENDATION else None,
        deadline=(t["deadline"] or None) if kind == RECOMMENDATION else None,
    )


def _upload(value, name: str) -> tuple[str, str | bytes] | None:
    """(file name, content): text as sent, or bytes for a base64-encoded binary file such as .xlsx."""
    if value in (None, ""):
        return None
    if not isinstance(value, dict):
        raise BadRequest(f"'{name}' must be an object with 'name' and 'content'")
    filename = str(value.get("name") or name)
    if isinstance(value.get("content_base64"), str):
        try:
            return filename, base64.b64decode(value["content_base64"], validate=True)
        except (binascii.Error, ValueError):
            raise BadRequest(f"{filename}: content_base64 is not valid base64") from None
    if not isinstance(value.get("content"), str):
        raise BadRequest(f"'{name}' must be an object with 'name' and 'content'")
    return filename, value["content"]


def batch_statements(body: dict) -> tuple[list[Statement], list[dict], list[str]]:
    docs = body.get("documents")
    if not isinstance(docs, list) or not docs:
        raise BadRequest("add at least one file to assess")
    catalog = policies = None
    cat = _upload(body.get("catalog"), "catalog")
    if cat:
        try:
            catalog = Catalog(json.loads(cat[1]))
        except (ValueError, KeyError, TypeError) as exc:
            raise BadRequest(f"catalog {cat[0]}: {exc}") from None
    pol = _upload(body.get("policy"), "policy")
    if pol:
        try:
            policies = parse_policies(json.loads(pol[1]))
        except (ValueError, KeyError, TypeError) as exc:
            raise BadRequest(f"policy file {pol[0]}: {exc}") from None

    items: list[Statement] = []
    names: list[str] = []
    files: list[dict] = []
    for i, doc in enumerate(docs):
        upload = _upload(doc, f"documents[{i}]")
        name, content = upload if upload else (f"file {i + 1}", "")
        try:
            found = parse_document(name, content)
        except (ValueError, KeyError, TypeError) as exc:
            files.append({"name": name, "count": 0, "error": str(exc)})
            continue
        if not found:
            files.append({"name": name, "count": 0, "error": "nothing to assess in this file"})
            continue
        files.append({"name": name, "count": len(found), "error": None})
        items += found
        names += [name] * len(found)
    prepare(items, catalog, policies)
    return items, files, names


def assess(body: dict) -> dict:
    """Run a single or batch health check described by a request body."""
    if not isinstance(body, dict):
        raise BadRequest("request body must be a JSON object")
    mode = body.get("mode")
    if mode == "single":
        items, files, names = [single_statement(body.get("item"))], [], ["Single input"]
    elif mode == "batch":
        items, files, names = batch_statements(body)
    else:
        raise BadRequest("'mode' must be 'single' or 'batch'")

    assessments = assess_all(items)
    rows = []
    for name, a in zip(names, assessments):
        d = a.to_dict()
        d["file"] = name
        rows.append(d)
    return {
        "summary": report.summary(assessments),
        "files": files,
        "assessments": rows,
        "markdown": report.to_markdown(assessments),
    }


def config() -> dict:
    return {"version": __version__, "kinds": KIND_LABELS}


def guides() -> dict:
    return {"guides": GUIDES, "statuses": STATUS_LABELS, "adopted": ADOPTED, "partly": PARTLY}


def handle(request_json: str) -> str:
    """Browser entry point: JSON in, JSON out, errors as {"error", "status"} rather than exceptions."""
    try:
        body = json.loads(request_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "request is not valid JSON", "status": 400})
    try:
        return json.dumps(assess(body))
    except BadRequest as exc:
        return json.dumps({"error": str(exc), "status": exc.status})
