"""Local risk register: parse, score, and suggest control-statement templates.

Risks are a parallel input to clauses ([ADR 0008](../../docs/adr/0008-risk-input-and-oscal-tracing.md)).
They stay on the device. Template drafts are deterministic and do not use AI.
"""

from __future__ import annotations

import csv
import io
import json
import re

STATUSES = ("identified", "treating", "accepted", "closed")
CSV_HEADER = (
    "id", "title", "description", "asset", "likelihood", "impact",
    "threat", "vulnerability", "owner", "status",
)
ALIASES = {
    "id": "id", "risk-id": "id", "risk_id": "id", "riskid": "id",
    "title": "title", "scenario": "title", "name": "title",
    "description": "description", "desc": "description", "details": "description",
    "asset": "asset", "process": "asset", "asset/process": "asset", "asset_process": "asset",
    "likelihood": "likelihood", "like": "likelihood",
    "impact": "impact",
    "threat": "threat",
    "vulnerability": "vulnerability", "vuln": "vulnerability",
    "owner": "owner",
    "status": "status",
}

_ID = re.compile(r"^R-\d{3,}$", re.I)


def score(likelihood: int, impact: int) -> int:
    return likelihood * impact


def _int_1_5(value, name: str) -> int:
    if isinstance(value, bool) or value is None or value == "":
        raise ValueError(f"{name} must be a number from 1 to 5")
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number from 1 to 5") from exc
    if n < 1 or n > 5:
        raise ValueError(f"{name} must be a number from 1 to 5")
    return n


def normalize_risk(raw: dict, index: int = 0) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("each risk must be an object")
    title = " ".join(str(raw.get("title") or "").split())
    if not title:
        raise ValueError("title is required")
    likelihood = _int_1_5(raw.get("likelihood"), "likelihood")
    impact = _int_1_5(raw.get("impact"), "impact")
    rid = " ".join(str(raw.get("id") or "").split())
    if rid and not _ID.match(rid):
        rid = re.sub(r"[^A-Za-z0-9-]+", "", rid)
    if not rid:
        rid = f"R-{index + 1:03d}"
    if not rid.upper().startswith("R-"):
        rid = f"R-{rid}"
    rid = rid.upper() if rid[1:2] == "-" else rid
    if rid.startswith("r-"):
        rid = "R-" + rid[2:]
    status = str(raw.get("status") or "identified").strip().lower()
    if status not in STATUSES:
        status = "identified"
    return {
        "id": rid,
        "title": title,
        "description": " ".join(str(raw.get("description") or "").split()),
        "asset": " ".join(str(raw.get("asset") or "").split()),
        "likelihood": likelihood,
        "impact": impact,
        "score": score(likelihood, impact),
        "threat": " ".join(str(raw.get("threat") or "").split()),
        "vulnerability": " ".join(str(raw.get("vulnerability") or "").split()),
        "owner": " ".join(str(raw.get("owner") or "").split()),
        "status": status,
    }


def assign_ids(risks: list[dict]) -> list[dict]:
    used: set[str] = set()
    n = 1
    out = []
    for r in risks:
        rid = r["id"]
        if not rid or rid in used:
            while f"R-{n:03d}" in used:
                n += 1
            rid = f"R-{n:03d}"
            n += 1
        used.add(rid)
        out.append({**r, "id": rid, "score": score(r["likelihood"], r["impact"])})
    return out


def _map_header(name: str) -> str | None:
    key = re.sub(r"[^a-z0-9]+", "", name.strip().lower())
    for alias, field in ALIASES.items():
        if re.sub(r"[^a-z0-9]+", "", alias) == key:
            return field
    return None


def parse_csv(text: str, mapping: dict | None = None) -> dict:
    """Parse a risk-register CSV. Returns {risks, errors, columns, recognised}.

    `mapping` is an optional {column-index-or-header: field} overlay for the
    person to correct automatic matches. Parsing stays on this device.
    """
    if not text or not str(text).strip():
        raise ValueError("the CSV is empty")
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValueError("the CSV is empty") from exc
    auto: dict[int, str] = {}
    recognised = []
    unknown = []
    for i, cell in enumerate(header):
        field = _map_header(cell)
        if field:
            auto[i] = field
            recognised.append({"column": cell, "field": field, "index": i})
        elif cell.strip():
            unknown.append(cell.strip())
    if mapping:
        overlay: dict[int, str] = {}
        valid = set(CSV_HEADER)
        for key, field in mapping.items():
            if field not in valid:
                continue
            if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
                overlay[int(key)] = field
            else:
                for i, cell in enumerate(header):
                    if cell.strip().lower() == str(key).strip().lower():
                        overlay[i] = field
        auto.update(overlay)
        recognised = [{"column": header[i], "field": f, "index": i} for i, f in sorted(auto.items())]
        unknown = [c.strip() for i, c in enumerate(header) if c.strip() and i not in auto]
    mapping = auto
    if "title" not in mapping.values() or "likelihood" not in mapping.values() or "impact" not in mapping.values():
        raise ValueError("CSV needs columns for title, likelihood and impact")
    risks: list[dict] = []
    errors: list[dict] = []
    for row_n, row in enumerate(reader, start=2):
        if not any(c.strip() for c in row):
            continue
        raw: dict[str, str] = {}
        for i, field in mapping.items():
            raw[field] = row[i] if i < len(row) else ""
        try:
            risks.append(normalize_risk(raw, index=len(risks)))
        except ValueError as exc:
            errors.append({"row": row_n, "error": str(exc)})
    return {
        "risks": assign_ids(risks),
        "errors": errors,
        "columns": [c.strip() for c in header if c.strip()],
        "recognised": recognised,
        "unknown": unknown,
    }


def parse_json(text: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not valid JSON ({exc.msg})") from None
    if isinstance(data, dict) and isinstance(data.get("risks"), list):
        items = data["risks"]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("JSON must be a list of risks or an object with a 'risks' list")
    risks: list[dict] = []
    errors: list[dict] = []
    for i, item in enumerate(items, start=1):
        try:
            risks.append(normalize_risk(item, index=len(risks)))
        except ValueError as exc:
            errors.append({"row": i, "error": str(exc)})
    return {"risks": assign_ids(risks), "errors": errors, "columns": list(CSV_HEADER),
            "recognised": [{"column": h, "field": h} for h in CSV_HEADER], "unknown": []}


def parse_register(name: str, content: str) -> dict:
    lower = (name or "").lower()
    if lower.endswith(".json"):
        return parse_json(content)
    return parse_csv(content)


def to_csv_register(risks: list[dict]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(CSV_HEADER)
    for r in risks:
        writer.writerow([r.get(k, "") if k != "score" else r.get("score", "") for k in CSV_HEADER])
    return out.getvalue()


# --- Template library --------------------------------------------------------
# Statements are written to pass control.py: action first, tool-neutral, testable,
# with a purpose clause. {scope} is the asset or a generic object.

TEMPLATES = (
    {
        "id": "restrict-access",
        "label": "Restrict access",
        "keywords": ("access", "unauthor", "unauthorized", "privilege", "account", "credential", "identity"),
        "statement": "Restrict access to {scope} to authorised users to prevent unauthorised use.",
    },
    {
        "id": "review-access",
        "label": "Review access",
        "keywords": ("access", "account", "privilege", "vendor", "third", "supplier", "recertif"),
        "statement": "Review access to {scope} at least every [90] days to remove access that is no longer needed.",
    },
    {
        "id": "anti-malware",
        "label": "Install anti-malware",
        "keywords": ("malware", "virus", "ransomware", "endpoint", "desktop"),
        "statement": "Install anti-malware software on all {scope} and keep it up to date to detect malicious software.",
    },
    {
        "id": "backup",
        "label": "Back up",
        "keywords": ("backup", "disaster", "recover", "ransom", "loss of data", "unrecover"),
        "statement": "Back up all {scope} at least every [N] days and store backups in a secure and separate location to restore after a disruption.",
    },
    {
        "id": "password-length",
        "label": "Require password length",
        "keywords": ("password", "credential stuffing", "brute", "guessable"),
        "statement": "Require passwords for {scope} to be at least [12] characters long to deter guessing.",
    },
    {
        "id": "patch",
        "label": "Apply security updates",
        "keywords": ("unpatch", "vulnerab", "patch", "cve", "endpoint"),
        "statement": "Apply security updates to {scope} within [N] days of release to reduce known vulnerabilities.",
    },
    {
        "id": "encrypt",
        "label": "Encrypt data",
        "keywords": ("encrypt", "confidential", "leak", "data at rest", "eavesdrop"),
        "statement": "Encrypt {scope} at rest and in transit to protect confidentiality.",
    },
    {
        "id": "log-review",
        "label": "Log and review access",
        "keywords": ("log", "audit", "detect", "misuse", "monitor"),
        "statement": "Log access to {scope} and review the logs at least every [N] days to detect misuse.",
    },
)


def _haystack(risk: dict) -> str:
    return " ".join(str(risk.get(k) or "") for k in ("title", "description", "asset", "threat", "vulnerability")).lower()


def _scope(risk: dict) -> str:
    asset = (risk.get("asset") or "").strip()
    return asset[0].lower() + asset[1:] if asset else "the affected systems"


def fill_template(template: dict, risk: dict) -> str:
    return template["statement"].format(scope=_scope(risk))


def suggest_templates(risk: dict, limit: int = 4) -> list[dict]:
    """Deterministic template suggestions for one risk, highest keyword-hit first."""
    text = _haystack(risk)
    ranked = []
    for tmpl in TEMPLATES:
        hits = sum(1 for kw in tmpl["keywords"] if kw in text)
        if hits:
            ranked.append((hits, tmpl["id"], tmpl))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    if not ranked:
        ranked = [(0, TEMPLATES[0]["id"], TEMPLATES[0]), (0, TEMPLATES[1]["id"], TEMPLATES[1])]
    out = []
    for hits, _tid, tmpl in ranked[:limit]:
        statement = fill_template(tmpl, risk)
        out.append({
            "id": tmpl["id"],
            "label": tmpl["label"],
            "statement": statement,
            "guidance": "",
            "hits": hits,
        })
    return out


def draft_from_templates(risk: dict, template_ids: list[str] | None = None) -> list[dict]:
    """Project controls from selected (or all suggested) templates."""
    library = {t["id"]: t for t in TEMPLATES}
    if template_ids:
        chosen = []
        for tid in template_ids:
            tmpl = library.get(tid)
            if tmpl:
                chosen.append({
                    "id": tmpl["id"], "label": tmpl["label"],
                    "statement": fill_template(tmpl, risk), "guidance": "",
                })
    else:
        chosen = suggest_templates(risk)
    base = risk.get("id") or "R-001"
    drafts = []
    for tmpl in chosen:
        drafts.append({
            "text": tmpl["statement"],
            "guidance": tmpl.get("guidance", ""),
            "risk": risk.get("title") or "",
            "who": risk.get("owner") or "",
            "notes": [f"Drafted from risk {base} using the '{tmpl['label']}' template."],
            "status": "draft",
            "origin": "rules",
            "source_type": "risk",
            "risk_id": base,
            "clause": "",
        })
    return [{"id": cid, **d} for cid, d in zip(_control_ids(base, len(drafts)), drafts)]


def _control_ids(risk_id: str, n: int) -> list[str]:
    base = re.sub(r"[^A-Za-z0-9.]+", "", risk_id) or "r1"
    if n == 1:
        return [base]
    return [f"{base}{chr(ord('a') + i)}" if base[-1].isdigit() else f"{base}-{i + 1}" for i in range(n)]
