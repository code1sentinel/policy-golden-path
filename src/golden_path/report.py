"""Render assessments as a terminal table, JSON, Markdown or OSCAL assessment results.

Reports give each item's confidence and its areas for improvement. They do
not pass or fail anything: that decision belongs to the reader's own process.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from . import __version__
from .models import IMPLEMENTATION, KIND_LABELS, Assessment

NS = "https://grcengineering.club/ns/golden-path"


def summary(assessments: list[Assessment]) -> dict:
    by_kind: dict[str, dict] = {}
    for kind in KIND_LABELS:
        items = [a for a in assessments if a.statement.kind == kind]
        if items:
            adopted = sum(a.practices["adopted"] for a in items)
            total = sum(a.practices["total"] for a in items)
            by_kind[kind] = {
                "count": len(items),
                "average_confidence": round(sum(a.confidence for a in items) / len(items), 4),
                "with_improvements": sum(bool(a.improvements) for a in items),
                "practices_adopted": adopted,
                "practices_total": total,
            }
    return {"total": len(assessments), "by_kind": by_kind}


def _summary_lines(assessments: list[Assessment]) -> list[str]:
    s = summary(assessments)
    lines = []
    for kind, k in s["by_kind"].items():
        noun = KIND_LABELS[kind].lower() + ("s" if k["count"] != 1 else "")
        lines.append(f"{k['count']} {noun}: average confidence {k['average_confidence']:.0%}, "
                     f"{k['practices_adopted']} of {k['practices_total']} best practices adopted, "
                     f"{k['with_improvements']} with areas for improvement.")
    return lines


def to_table(assessments: list[Assessment]) -> str:
    rows = [(KIND_LABELS[a.statement.kind], a.statement.key, f"{a.confidence:.0%}",
             f"{a.practices['adopted']}/{a.practices['total']}", str(len(a.improvements))) for a in assessments]
    kw = max([len("Kind")] + [len(r[0]) for r in rows])
    iw = max([len("Item")] + [len(r[1]) for r in rows])
    lines = [f"{'Kind':<{kw}}  {'Item':<{iw}}  Confidence  Practices adopted  Improvements",
             f"{'-' * kw}  {'-' * iw}  ----------  -----------------  ------------"]
    lines += [f"{k:<{kw}}  {i:<{iw}}  {c:>10}  {p:>17}  {n:>12}" for k, i, c, p, n in rows]
    if assessments:
        lines += [""] + _summary_lines(assessments)
    improving = [a for a in assessments if a.improvements]
    if improving:
        lines += ["", "Areas for improvement", "---------------------"]
        for a in improving:
            lines.append(f"\n{KIND_LABELS[a.statement.kind]}: {a.statement.key}  ({a.confidence:.0%})")
            lines += [f"  - {i}" for i in a.improvements]
    return "\n".join(lines)


def to_json(assessments: list[Assessment]) -> str:
    return json.dumps({"summary": summary(assessments), "assessments": [a.to_dict() for a in assessments]},
                      indent=2)


def to_markdown(assessments: list[Assessment]) -> str:
    out = ["# Golden Path: health check", ""]
    out += [f"- {line}" for line in _summary_lines(assessments)]
    out += ["", "| Kind | Item | Confidence | Practices adopted | Improvements |", "| --- | --- | --- | --- | --- |"]
    for a in assessments:
        out.append(f"| {KIND_LABELS[a.statement.kind]} | {a.statement.key} | {a.confidence:.0%} | "
                   f"{a.practices['adopted']}/{a.practices['total']} | {len(a.improvements)} |")
    improving = [a for a in assessments if a.improvements]
    if improving:
        out += ["", "## Areas for improvement"]
        for a in improving:
            out += ["", f"### {KIND_LABELS[a.statement.kind]}: {a.statement.key} — {a.confidence:.0%}", ""]
            out += [f"- {i}" for i in a.improvements]
    return "\n".join(out) + "\n"


def to_assessment_results(assessments: list[Assessment], source_href: str) -> str:
    """One OSCAL observation per assessed item, carrying its confidence and improvements."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    observations = []
    for a in assessments:
        st = a.statement
        props = [
            {"name": "assessed-kind", "ns": NS, "value": st.kind},
            {"name": "confidence", "ns": NS, "value": f"{a.confidence:.4f}"},
            {"name": "engine", "ns": NS, "value": a.engine},
            {"name": "practices-adopted", "ns": NS, "value": str(a.practices["adopted"])},
            {"name": "practices-total", "ns": NS, "value": str(a.practices["total"])},
        ]
        if st.uuid:
            props.append({"name": "assessed-uuid", "ns": NS, "value": st.uuid})
        if st.control_id:
            props.append({"name": "control-id", "ns": NS, "value": st.control_id})
        obs = {
            "uuid": str(uuid.uuid4()),
            "title": f"{KIND_LABELS[st.kind]}: {st.key}",
            "description": a.rationale or "No rationale recorded.",
            "props": props,
            "methods": ["EXAMINE"],
            "types": ["finding"] if a.improvements else ["historic"],
            "collected": now,
        }
        if a.improvements:
            obs["remarks"] = "\n".join(f"- {i}" for i in a.improvements)
        observations.append(obs)

    control_ids = sorted({a.statement.control_id for a in assessments
                          if a.statement.kind == IMPLEMENTATION and a.statement.control_id})
    selection = ({"include-controls": [{"control-id": c} for c in control_ids]} if control_ids
                 else {"include-all": {}})
    doc = {
        "assessment-results": {
            "uuid": str(uuid.uuid4()),
            "metadata": {
                "title": "Golden Path health check",
                "last-modified": now,
                "version": __version__,
                "oscal-version": "1.1.2",
            },
            "import-ap": {"href": source_href},
            "results": [{
                "uuid": str(uuid.uuid4()),
                "title": "Golden Path run",
                "description": " ".join(_summary_lines(assessments)) or "Nothing assessed.",
                "start": now,
                "end": now,
                "reviewed-controls": {"control-selections": [selection]},
                "observations": observations,
            }],
        }
    }
    return json.dumps(doc, indent=2)
