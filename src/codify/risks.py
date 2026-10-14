"""Identified risks as input to control authoring ([ADR 0012](../../docs/adr/0012-identified-risks-as-input.md)).

A project may hold a simple list of risks the person already identified.
This is not a register: no scores, owners, or treatment plans. Leftover
ADR 0008 register records are dropped, not converted.
"""

from __future__ import annotations

import re
import uuid

from .library import normalize_statement

MAX_RISKS = 500
MAX_LINKS = 50
RISK_ID = re.compile(r"^R-\d{3,}$")
REGISTER_FIELDS = ("likelihood", "impact", "score", "owner", "asset", "threat", "vulnerability")
REGISTER_STATUSES = ("identified", "treating", "accepted", "closed")
STOP = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "due", "for", "from", "in", "into",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "when", "with", "without",
})
_WORD = re.compile(r"[a-z0-9]{4,}")


def next_risk_id(risks: list[dict]) -> str:
    n = 0
    for risk in risks:
        match = RISK_ID.match(risk.get("id") or "")
        if match:
            n = max(n, int(risk["id"].split("-", 1)[1]))
    return f"R-{n + 1:03d}"


def _is_register_record(raw) -> bool:
    if not isinstance(raw, dict):
        return True
    if any(key in raw for key in REGISTER_FIELDS):
        return True
    if raw.get("status") in REGISTER_STATUSES:
        return True
    statement = " ".join(str(raw.get("statement") or "").split())
    return not statement


def clean_risks(value) -> list[dict]:
    """Keep identified-risk input records; drop leftover register rows."""
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for raw in value[:MAX_RISKS]:
        if _is_register_record(raw):
            continue
        statement = " ".join(str(raw.get("statement") or "").split())
        note = " ".join(str(raw.get("note") or "").split())
        risk_id = " ".join(str(raw.get("id") or "").split())
        if not risk_id or risk_id in seen or not RISK_ID.match(risk_id):
            risk_id = next_risk_id(out)
        seen.add(risk_id)
        out.append({"id": risk_id, "statement": statement, "note": note})
    return out


def _risk_ids_for_control(control: dict, known: set[str]) -> list[str]:
    raw = control.get("risk_ids")
    if not isinstance(raw, list):
        raw = []
    out: list[str] = []
    for item in raw[:MAX_LINKS]:
        risk_id = " ".join(str(item or "").split())
        if risk_id in known and risk_id not in out:
            out.append(risk_id)
    return out


def normalize_project(project: dict) -> dict:
    """Drop leftover register fields; keep identified risks and valid links."""
    if not isinstance(project, dict):
        return project
    out = dict(project)
    out["risks"] = clean_risks(out.get("risks"))
    known = {r["id"] for r in out["risks"]}
    cleaned = []
    for control in out.get("controls") or []:
        if not isinstance(control, dict):
            cleaned.append(control)
            continue
        next_control = dict(control)
        next_control["source_type"] = "clause"
        next_control["risk_ids"] = _risk_ids_for_control(next_control, known)
        next_control.pop("risk_id", None)
        cleaned.append(next_control)
    if "controls" in out:
        out["controls"] = cleaned
    return out


def drop_legacy_register(project: dict) -> dict:
    """ADR 0011 name: now normalizes identified-risk input (ADR 0012)."""
    return normalize_project(project)


def coverage(project: dict) -> dict:
    """Flags only: uncovered identified risks, unlinked controls. Not a score."""
    risks = project.get("risks") or []
    controls = [c for c in (project.get("controls") or []) if isinstance(c, dict)]
    linked: set[str] = set()
    unlinked = []
    for control in controls:
        ids = [i for i in (control.get("risk_ids") or []) if i]
        if not ids:
            unlinked.append(control.get("id") or "")
        linked.update(ids)
    uncovered = [r["id"] for r in risks if r.get("id") not in linked]
    return {
        "uncovered_risk_ids": [i for i in uncovered if i],
        "unlinked_control_ids": [i for i in unlinked if i],
    }


def purpose_from_risks(project: dict, risk_ids: list[str]) -> str:
    by_id = {r["id"]: r.get("statement") or "" for r in project.get("risks") or []}
    statements = [by_id[i] for i in risk_ids if by_id.get(i)]
    return " ".join(statements)


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(normalize_statement(text)) if w not in STOP}


def match_library(entries: list[dict], statement: str) -> list[dict]:
    """Local token overlap against the Statement library. No network."""
    needle = _tokens(statement)
    if not needle:
        return []
    ranked = []
    for entry in entries:
        hay = " ".join([
            entry.get("statement") or "",
            (entry.get("parts") or {}).get("purpose") or "" if isinstance(entry.get("parts"), dict) else "",
        ])
        overlap = needle & _tokens(hay)
        if overlap:
            ranked.append((len(overlap), entry))
    ranked.sort(key=lambda item: (-item[0], item[1].get("id") or ""))
    return [entry for _, entry in ranked]


def risk_resource_uuid(project_uuid: str, risk_id: str) -> str:
    return str(uuid.uuid5(uuid.UUID(project_uuid), "identified-risk:" + risk_id))
