"""A Codify project: a legacy policy, its sorted clauses, and the control statements drafted from them.

The project is plain data (JSON), shared with the web page:

    {"uuid", "title", "source", "clauses": [clause...], "controls": [control...]}
    clause:  {"id", "text", "section", "heading", "type", "reason", "duplicate_of"}
    control: {"id", "clause", "text", "guidance", "risk", "who", "notes", "status", "origin"}

Its file form is an OSCAL catalog: the deliverable and the save file in one.
Each control carries its status, origin and the legacy wording it came from;
every legacy clause, with its type, is kept in the catalog's back matter, so
opening the catalog again resumes the work exactly. A catalog that Codify did
not make opens too: each of its controls becomes a clause and a control to
work on.
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import datetime, timezone

from . import __version__
from .classify import REQUIREMENT, SCOPE, TYPE_LABELS, TYPES, sort_clauses
from .clauses import Clause, Policy
from .draft import draft

NS = "https://grcengineering.club/ns/codify"
OSCAL_VERSION = "1.1.2"
STATUSES = ("draft", "reviewed", "accepted")
ORIGINS = ("rules", "person", "ai", "catalog")


# --- Building a project ---------------------------------------------------------------------------

def _control_ids(clause_id: str, n: int) -> list[str]:
    base = re.sub(r"[^A-Za-z0-9.]+", "", clause_id) or "c1"
    if n == 1:
        return [base]
    return [f"{base}{chr(ord('a') + i)}" if base[-1].isdigit() else f"{base}-{i + 1}" for i in range(n)]


def new_project(policy: Policy, source: str = "") -> dict:
    """Sort the policy's clauses and draft control statements for its requirements."""
    sorted_ = sort_clauses(policy.clauses)
    clauses, controls = [], []
    for clause, result in zip(policy.clauses, sorted_):
        clauses.append({"id": clause.id, "text": clause.text, "section": clause.section, "heading": clause.heading,
                        "type": result.type, "reason": result.reason, "duplicate_of": result.duplicate_of})
        if result.type == REQUIREMENT and not result.duplicate_of:
            controls += draft_controls(clause.id, clause.text)
    return {"uuid": str(uuid.uuid4()), "title": policy.title, "source": source, "version": __version__,
            "clauses": clauses, "controls": controls}


def draft_controls(clause_id: str, text: str) -> list[dict]:
    """Rule-based drafts for one requirement clause, as project controls."""
    drafts = draft(text)
    return [{"id": cid, "clause": clause_id, "text": d.text, "guidance": d.guidance, "risk": "", "who": d.who,
             "notes": d.notes, "status": "draft", "origin": "rules"}
            for cid, d in zip(_control_ids(clause_id, len(drafts)), drafts)]


def summary(project: dict) -> dict:
    """Counts for the headline: '43 clauses -> 33 controls, 10 context, 6 not controls, 1 duplicate'."""
    clauses = project["clauses"]
    by_type = {t: sum(1 for c in clauses if c["type"] == t) for t in TYPES}
    controls = project["controls"]
    return {
        "clauses": len(clauses),
        "controls": len(controls),
        "by_type": by_type,
        "context": sum(by_type[t] for t in TYPES if t not in (REQUIREMENT, "not-a-control")),
        "duplicates": sum(1 for c in clauses if c.get("duplicate_of")),
        "by_status": {s: sum(1 for c in controls if c["status"] == s) for s in STATUSES},
    }


# --- Parameters --------------------------------------------------------------------------------------

_BRACKET = re.compile(r"\[([^\[\]]{1,40})\]")
_INSERT = re.compile(r"\{\{\s*insert:\s*param,\s*([^\s}]+)\s*\}\}")
_LABELS = [
    (r"business days?|working days?", "time period (business days)"), (r"days?", "time period (days)"),
    (r"hours?", "time period (hours)"), (r"minutes?", "time period (minutes)"), (r"weeks?", "time period (weeks)"),
    (r"months?", "time period (months)"), (r"years?", "time period (years)"),
    (r"characters?", "number of characters"), (r"(failed |unsuccessful |consecutive )*(login |logon )?attempts?",
                                               "number of attempts"),
    (r"passwords?", "number of passwords"), (r"versions?|generations?", "number of versions"),
]


def _param_label(after: str) -> str:
    for pattern, label in _LABELS:
        if re.match(r"\s*(" + pattern + r")\b", after, re.I):
            return label
    return "value"


def to_params(control_id: str, text: str) -> tuple[str, list[dict]]:
    """'within [5] business days' -> ('within {{ insert: param, x_prm_1 }} business days', [param])."""
    params: list[dict] = []

    def replace(m: re.Match) -> str:
        pid = f"{control_id}_prm_{len(params) + 1}"
        inner = m.group(1).strip()
        param = {"id": pid, "label": _param_label(text[m.end():])}
        if inner.upper() not in ("N", "X", "VALUE", "TBD") and not inner.lower().startswith(("assignment", "selection")):
            param["values"] = [inner]
        params.append(param)
        return "{{ insert: param, " + pid + " }}"

    return _BRACKET.sub(replace, text), params


def from_params(prose: str, params: list[dict]) -> str:
    """The reverse: inserts back to '[5]', or '[N]' where no value is set."""
    by_id = {p["id"]: p for p in params}

    def replace(m: re.Match) -> str:
        p = by_id.get(m.group(1), {})
        values = p.get("values") or []
        if values:
            return f"[{values[0]}]"
        if p.get("select"):
            return "[" + " | ".join(p["select"].get("choice", [])) + "]"
        return "[N]" if "time period" in p.get("label", "") or "number" in p.get("label", "") else \
            f"[{p.get('label', 'N')}]"

    return _INSERT.sub(replace, prose)


# --- OSCAL ------------------------------------------------------------------------------------------

def _prop(name: str, value: str, ns: bool = True) -> dict | None:
    value = " ".join(str(value or "").split())
    if not value:
        return None
    prop = {"name": name, "value": value}
    if ns:
        prop["ns"] = NS
    return prop


def _props(*items: dict | None) -> list[dict]:
    return [p for p in items if p]


def _token(text: str, prefix: str) -> str:
    """An OSCAL token: starts with a letter, then letters, digits, '.', '-' or '_'."""
    return prefix + re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _title(text: str) -> str:
    words = re.sub(r"[.;:]$", "", text).split()
    return " ".join(words[:8]) + ("…" if len(words) > 8 else "") if words else "Untitled control"


def to_oscal(project: dict) -> dict:
    """The project as an OSCAL catalog: one group per policy section, one control per control statement."""
    pid = project.get("uuid") or str(uuid.uuid4())
    clause_uuid = {c["id"]: str(uuid.uuid5(uuid.UUID(pid), "clause:" + c["id"])) for c in project["clauses"]}
    clauses = {c["id"]: c for c in project["clauses"]}

    groups: dict[str, dict] = {}
    for control in project["controls"]:
        clause = clauses.get(control["clause"], {})
        section = clause.get("section") or "0"
        group = groups.setdefault(section, {"id": _token(section, "s-"),
                                            "title": clause.get("heading") or ("Policy" if section == "0" else f"Section {section}"),
                                            "controls": []})
        cid = _token(control["id"], "c-")
        prose, params = to_params(cid, control["text"])
        parts = [{"id": f"{cid}_smt", "name": "statement", "prose": prose}]
        if control.get("guidance"):
            parts.append({"id": f"{cid}_gdn", "name": "guidance", "prose": control["guidance"]})
        if clause.get("text"):
            parts.append({"id": f"{cid}_legacy", "name": "legacy-text", "ns": NS, "prose": clause["text"]})
        if control.get("notes"):
            parts.append({"id": f"{cid}_notes", "name": "drafting-notes", "ns": NS,
                          "prose": "\n".join(f"- {n}" for n in control["notes"])})
        entry = {
            "id": cid,
            "title": _title(control["text"]),
            "props": _props(_prop("label", control["id"], ns=False), _prop("legacy-clause", control["clause"]),
                            _prop("status", control.get("status", "draft")),
                            _prop("origin", control.get("origin", "rules")),
                            _prop("risk-statement", control.get("risk")),
                            _prop("responsible-role", control.get("who"))),
            "parts": parts,
        }
        if params:
            entry["params"] = params
        if control["clause"] in clause_uuid:
            entry["links"] = [{"href": "#" + clause_uuid[control["clause"]], "rel": "derived-from"}]
        group["controls"].append(entry)

    scope = [c["text"] for c in project["clauses"] if c["type"] == SCOPE]
    metadata = {
        "title": f"{project.get('title') or 'Policy'}: control statements",
        "last-modified": _now(),
        "version": project.get("version_label") or "draft",
        "oscal-version": OSCAL_VERSION,
        "props": _props(_prop("source-policy", project.get("title")), _prop("source-file", project.get("source")),
                        _prop("generator", f"Codify {__version__}")),
    }
    if scope:
        metadata["remarks"] = "Applies to: " + " ".join(scope)
    resources = []
    for c in project["clauses"]:
        resources.append({
            "uuid": clause_uuid[c["id"]],
            "title": f"{c['id']} {c.get('heading') or ''}".strip(),
            "description": c["text"],
            "props": _props(_prop("clause-id", c["id"]), _prop("clause-type", c["type"]),
                            _prop("section", c.get("section")), _prop("heading", c.get("heading")),
                            _prop("reason", c.get("reason")), _prop("duplicate-of", c.get("duplicate_of"))),
        })
    catalog = {"uuid": pid, "metadata": metadata}
    if groups:
        catalog["groups"] = [groups[k] for k in sorted(groups, key=_section_key)]
    if resources:
        catalog["back-matter"] = {"resources": resources}
    return {"catalog": catalog}


def _section_key(section: str) -> tuple:
    return tuple(int(p) if p.isdigit() else 0 for p in re.split(r"\D+", section) if p) or (0,)


def _ns_props(item: dict) -> dict[str, str]:
    return {p["name"]: p["value"] for p in item.get("props", []) if p.get("ns") == NS}


def _walk(node: dict):
    for group in node.get("groups", []):
        yield from ((group, c) for c in _walk_controls(group))
    for control in node.get("controls", []):
        yield from ((node, c) for c in _walk_controls({"controls": [control]}))


def _walk_controls(node: dict):
    for control in node.get("controls", []):
        yield control
        yield from _walk_controls(control)


def _part_text(control: dict, name: str) -> str:
    def flatten(part: dict) -> str:
        own = part.get("prose", "")
        return " ".join(t for t in [own] + [flatten(p) for p in part.get("parts", [])] if t).strip()
    return " ".join(flatten(p) for p in control.get("parts", []) if p.get("name") == name).strip()


def from_oscal(data: dict) -> dict:
    """A project from an OSCAL catalog: one saved by Codify resumes exactly; any other becomes a starting point."""
    root = data.get("catalog")
    if not isinstance(root, dict):
        raise ValueError("not an OSCAL catalog: missing top-level 'catalog'")
    meta = root.get("metadata", {})
    meta_props = _ns_props(meta)
    resources = root.get("back-matter", {}).get("resources", [])
    clauses = []
    for r in resources:
        p = _ns_props(r)
        if "clause-id" in p:
            clauses.append({"id": p["clause-id"], "text": r.get("description", ""), "section": p.get("section", ""),
                            "heading": p.get("heading", ""), "type": p.get("clause-type", REQUIREMENT),
                            "reason": p.get("reason", ""), "duplicate_of": p.get("duplicate-of")})
    ours = bool(clauses)
    title = meta_props.get("source-policy") or re.sub(r":\s*control statements$", "", meta.get("title", "Catalog"))
    controls = []
    for group, control in _walk(root):
        params = control.get("params", [])
        text = from_params(_part_text(control, "statement"), params)
        if not text:
            continue
        p = _ns_props(control)
        label = next((x["value"] for x in control.get("props", []) if x.get("name") == "label"), control["id"])
        risk = p.get("risk-statement") or next(
            (x["value"] for x in control.get("props", []) if x.get("name") == "risk-statement"), "")
        notes = [n[2:] if n.startswith("- ") else n
                 for n in _part_text(control, "drafting-notes").split("\n- ") if n.strip()] if ours else []
        clause_id = p.get("legacy-clause") or label
        controls.append({"id": label, "clause": clause_id, "text": text,
                         "guidance": _part_text(control, "guidance"), "risk": risk,
                         "who": p.get("responsible-role", ""), "notes": notes,
                         "status": p.get("status", "draft") if p.get("status") in STATUSES else "draft",
                         "origin": p.get("origin", "rules" if ours else "catalog")})
        if not ours:
            clauses.append({"id": clause_id, "text": text, "section": group.get("id", ""),
                            "heading": group.get("title", ""), "type": REQUIREMENT,
                            "reason": "a control in the catalog opened", "duplicate_of": None})
    if not clauses:
        raise ValueError("this catalog has no controls with statements")
    return {"uuid": root.get("uuid") or str(uuid.uuid4()), "title": title,
            "source": meta_props.get("source-file", ""), "version": __version__,
            "clauses": clauses, "controls": controls}


# --- Spreadsheet and report ---------------------------------------------------------------------------

COLUMNS = ("control id", "legacy clause", "clause type", "legacy text", "control statement", "parameters",
           "guidance", "risk it treats", "who", "status", "origin", "score", "notes")


def to_rows(project: dict, scores: dict[str, float] | None = None) -> list[list[str]]:
    """One row per control, then one per clause that produced none (context, not controls, duplicates)."""
    clauses = {c["id"]: c for c in project["clauses"]}
    rows = [list(COLUMNS)]
    used = set()
    for c in project["controls"]:
        clause = clauses.get(c["clause"], {})
        used.add(c["clause"])
        params = "; ".join(f"[{m}]" for m in _BRACKET.findall(c["text"]))
        score = (scores or {}).get(c["id"])
        rows.append([c["id"], c["clause"], TYPE_LABELS.get(clause.get("type", ""), ""), clause.get("text", ""),
                     c["text"], params, c.get("guidance", ""), c.get("risk", ""), c.get("who", ""),
                     c["status"], c.get("origin", ""), f"{score:.0%}" if score is not None else "",
                     " ".join(c.get("notes", []))])
    for clause in project["clauses"]:
        if clause["id"] in used:
            continue
        note = f"Duplicate of {clause['duplicate_of']}" if clause.get("duplicate_of") else clause.get("reason", "")
        rows.append(["", clause["id"], TYPE_LABELS.get(clause["type"], clause["type"]), clause["text"],
                     "", "", "", "", "", "", "", "", note])
    return rows


def to_csv(project: dict, scores: dict[str, float] | None = None) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    for row in to_rows(project, scores):
        # a cell starting with = + - @ would run as a formula in a spreadsheet
        writer.writerow(["'" + v if v[:1] in ("=", "+", "-", "@") else v for v in row])
    return out.getvalue()


def to_xlsx(project: dict, scores: dict[str, float] | None = None) -> bytes:
    from .xlsx import write_rows

    return write_rows(to_rows(project, scores), sheet_name="Controls",
                      widths=[10, 10, 14, 60, 60, 16, 30, 40, 20, 10, 10, 8, 50])


def to_report(project: dict, scores: dict[str, float] | None = None,
              improvements: dict[str, list[str]] | None = None) -> str:
    """A Markdown conversion report: the summary, then each control and what still needs attention."""
    s = summary(project)
    by_type = s["by_type"]
    lines = [f"# {project.get('title') or 'Policy'}: conversion report", "",
             f"**{s['clauses']} clauses → {s['controls']} controls**, from {by_type[REQUIREMENT]} requirement "
             f"clauses ({s['duplicates']} duplicate). The other clauses: {s['context']} context "
             f"({by_type['scope']} scope, {by_type['definition']} definitions, {by_type['role']} roles, "
             f"{by_type['exception']} exceptions) and {by_type['not-a-control']} not controls.", "",
             f"Status: {s['by_status']['accepted']} accepted, {s['by_status']['reviewed']} reviewed, "
             f"{s['by_status']['draft']} draft.", "", "| Control | From | Statement | Score | Status |",
             "| --- | --- | --- | --- | --- |"]
    for c in project["controls"]:
        score = (scores or {}).get(c["id"])
        cell = c["text"].replace("|", "\\|")
        lines.append(f"| {c['id']} | {c['clause']} | {cell} | {f'{score:.0%}' if score is not None else ''} | "
                     f"{c['status']} |")
    attention = [(c, (improvements or {}).get(c["id"], []) + c.get("notes", [])) for c in project["controls"]
                 if c["status"] != "accepted"]
    attention = [(c, items) for c, items in attention if items]
    if attention:
        lines += ["", "## Still needs attention", ""]
        for c, items in attention:
            lines.append(f"**{c['id']}** {c['text']}")
            lines += [f"- {i}" for i in dict.fromkeys(items)]
            lines.append("")
    others = [c for c in project["clauses"] if c["type"] != REQUIREMENT or c.get("duplicate_of")]
    if others:
        lines += ["", "## Clauses that are not controls", "", "| Clause | Type | Why |", "| --- | --- | --- |"]
        for c in others:
            kind = "Duplicate" if c.get("duplicate_of") else TYPE_LABELS.get(c["type"], c["type"])
            lines.append(f"| {c['id']} | {kind} | {c.get('reason', '')} |")
    return "\n".join(lines).rstrip() + "\n"


def clause_from(project: dict, clause_id: str) -> Clause | None:
    c = next((x for x in project["clauses"] if x["id"] == clause_id), None)
    return Clause(c["id"], c["text"], c.get("section", ""), c.get("heading", "")) if c else None
