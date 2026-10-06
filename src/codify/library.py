"""Device-wide Statement library: normalize, upsert, search, and local export.

The library is a browser store (`codify:statements`), not the OSCAL catalog
([ADR 0009](../../docs/adr/0009-device-wide-statement-library.md)). These
functions are pure: the page passes the entries it holds.
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone

SOURCE_TYPES = ("clause", "risk")
CSV_HEADER = ("id", "statement", "parts", "source-type", "risk-id", "accepted-at", "last-used-at")
PART_KEYS = ("action", "scope", "limit", "purpose")
MAX_ENTRIES = 2000
_ID = re.compile(r"^S-\d{3,}$")


def normalize_statement(text: str) -> str:
    """Collapse whitespace and case-fold so duplicate Accepts share one row."""
    return " ".join((text or "").split()).casefold()


def _now(value: str | None = None) -> str:
    if value:
        return value
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parts(value) -> dict | None:
    if not value:
        return None
    if not isinstance(value, dict):
        raise ValueError("'parts' must be an object")
    out = {}
    for key in PART_KEYS:
        raw = value.get(key)
        out[key] = " ".join(str(raw).split()) if raw else None
    return out if any(out.values()) else None


def next_id(entries: list[dict]) -> str:
    n = 0
    for entry in entries:
        match = _ID.match(entry.get("id") or "")
        if match:
            n = max(n, int(entry["id"].split("-", 1)[1]))
    return f"S-{n + 1:03d}"


def clean_entry(raw, index: int = 0) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("each library entry must be an object")
    statement = " ".join(str(raw.get("statement") or "").split())
    if not statement:
        raise ValueError("statement is required")
    entry_id = " ".join(str(raw.get("id") or "").split())
    if not entry_id or not _ID.match(entry_id):
        entry_id = f"S-{index + 1:03d}"
    source = raw.get("source-type") or raw.get("source_type")
    source_type = source if source in SOURCE_TYPES else "clause"
    risk_id = " ".join(str(raw.get("risk-id") or raw.get("risk_id") or "").split())
    if source_type != "risk":
        risk_id = risk_id if risk_id else ""
    return {
        "id": entry_id,
        "statement": statement,
        "parts": _parts(raw.get("parts")),
        "source-type": source_type,
        "risk-id": risk_id,
        "accepted-at": " ".join(str(raw.get("accepted-at") or raw.get("accepted_at") or "").split()),
        "last-used-at": " ".join(str(raw.get("last-used-at") or raw.get("last-used_at") or "").split()),
    }


def clean_library(value) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("'library' must be a list")
    if len(value) > MAX_ENTRIES:
        raise ValueError("library is too large")
    return [clean_entry(entry, i) for i, entry in enumerate(value)]


def upsert(entries, statement: str, *, parts=None, source_type: str = "clause",
           risk_id: str = "", used: bool = False, now: str | None = None) -> tuple[dict, list[dict]]:
    """Insert or update by normalized statement text. `used` touches last-used-at only."""
    text = " ".join((statement or "").split())
    if not text:
        raise ValueError("statement is required")
    if source_type not in SOURCE_TYPES:
        source_type = "risk" if risk_id else "clause"
    when = _now(now)
    key = normalize_statement(text)
    out = [dict(e) for e in entries]
    for i, entry in enumerate(out):
        if normalize_statement(entry.get("statement") or "") != key:
            continue
        updated = dict(entry)
        if used:
            updated["last-used-at"] = when
        else:
            updated["statement"] = text
            updated["source-type"] = source_type
            updated["risk-id"] = risk_id if source_type == "risk" else (risk_id or "")
            updated["accepted-at"] = when
            if parts is not None:
                updated["parts"] = _parts(parts)
        out[i] = updated
        return updated, out
    entry = {
        "id": next_id(out),
        "statement": text,
        "parts": _parts(parts),
        "source-type": source_type,
        "risk-id": risk_id if source_type == "risk" else "",
        "accepted-at": "" if used else when,
        "last-used-at": when if used else "",
    }
    out.append(entry)
    return entry, out


def remove(entries, entry_id: str) -> list[dict]:
    return [entry for entry in entries if entry.get("id") != entry_id]


def search(entries, query: str = "") -> list[dict]:
    needle = normalize_statement(query)
    hits = []
    for entry in entries:
        hay = " ".join([
            entry.get("statement") or "",
            entry.get("source-type") or "",
            entry.get("risk-id") or "",
            entry.get("id") or "",
        ])
        if not needle or needle in normalize_statement(hay):
            hits.append(entry)
    hits.sort(key=lambda e: (e.get("last-used-at") or "", e.get("accepted-at") or ""), reverse=True)
    return hits


def _escape_cell(value: str) -> str:
    if value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def to_json(entries) -> str:
    return json.dumps(entries, indent=2)


def to_csv(entries) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(CSV_HEADER)
    for entry in entries:
        parts = entry.get("parts")
        row = [
            entry.get("id") or "",
            entry.get("statement") or "",
            json.dumps(parts) if parts else "",
            entry.get("source-type") or "",
            entry.get("risk-id") or "",
            entry.get("accepted-at") or "",
            entry.get("last-used-at") or "",
        ]
        writer.writerow([_escape_cell(str(cell)) for cell in row])
    return out.getvalue()
