"""Render assessments as a terminal table, JSON, Markdown or OSCAL assessment results."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from . import __version__
from .models import Assessment

NS = "https://grcengineering.club/ns/oscal-assess"


def summary(assessments: list[Assessment]) -> dict:
    passed = sum(a.passed for a in assessments)
    return {
        "total": len(assessments),
        "passed": passed,
        "failed": len(assessments) - passed,
        "threshold": assessments[0].threshold if assessments else None,
    }


def to_table(assessments: list[Assessment]) -> str:
    rows = [(a.statement.key, f"{a.confidence:.0%}", "PASS" if a.passed else "FAIL") for a in assessments]
    width = max([len("Statement")] + [len(r[0]) for r in rows])
    lines = [f"{'Statement':<{width}}  Confidence  Result", f"{'-' * width}  ----------  ------"]
    lines += [f"{k:<{width}}  {c:>10}  {r}" for k, c, r in rows]
    s = summary(assessments)
    if s["total"]:
        lines.append("")
        lines.append(f"{s['passed']}/{s['total']} passed at a {s['threshold']:.0%} confidence threshold.")
        for a in assessments:
            if not a.passed and a.gaps:
                lines.append(f"\n{a.statement.key}  ({a.confidence:.0%})")
                lines += [f"  - {g}" for g in a.gaps]
    return "\n".join(lines)


def to_json(assessments: list[Assessment]) -> str:
    return json.dumps(
        {"summary": summary(assessments), "assessments": [a.to_dict() for a in assessments]}, indent=2
    )


def to_markdown(assessments: list[Assessment]) -> str:
    s = summary(assessments)
    out = [
        "# OSCAL control statement assessment",
        "",
        f"**{s['passed']} of {s['total']} passed** at a {s['threshold']:.0%} confidence threshold.",
        "",
        "| Statement | Component | Confidence | Result |",
        "| --- | --- | --- | --- |",
    ]
    for a in assessments:
        st = a.statement
        out.append(
            f"| `{st.statement_id or st.control_id}` | {st.component or ''} | {a.confidence:.0%} | "
            f"{'✅ pass' if a.passed else '❌ fail'} |"
        )
    for a in assessments:
        if a.passed:
            continue
        out += ["", f"## `{a.statement.key}` — {a.confidence:.0%}", "", a.rationale, ""]
        out += [f"- {g}" for g in a.gaps]
    return "\n".join(out) + "\n"


def to_assessment_results(assessments: list[Assessment], source_href: str) -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    s = summary(assessments)
    findings = []
    for a in assessments:
        st = a.statement
        findings.append({
            "uuid": str(uuid.uuid4()),
            "title": f"{st.key}: {'satisfied' if a.passed else 'not satisfied'}",
            "description": a.rationale or "No rationale recorded.",
            "props": [
                {"name": "confidence", "ns": NS, "value": f"{a.confidence:.4f}"},
                {"name": "threshold", "ns": NS, "value": f"{a.threshold:.4f}"},
                {"name": "engine", "ns": NS, "value": a.engine},
            ],
            "target": {
                "type": "statement-id" if st.statement_id else "objective-id",
                "target-id": st.statement_id or st.control_id,
                "status": {"state": "satisfied" if a.passed else "not-satisfied"},
            },
            **({"remarks": "\n".join(a.gaps)} if a.gaps else {}),
        })
    control_ids = sorted({a.statement.control_id for a in assessments})
    doc = {
        "assessment-results": {
            "uuid": str(uuid.uuid4()),
            "metadata": {
                "title": "Implementation statement assessment",
                "last-modified": now,
                "version": __version__,
                "oscal-version": "1.1.2",
            },
            "import-ap": {"href": source_href},
            "results": [{
                "uuid": str(uuid.uuid4()),
                "title": "oscal-assess run",
                "description": f"{s['passed']} of {s['total']} statements reached the "
                               f"{s['threshold']:.0%} confidence threshold.",
                "start": now,
                "end": now,
                "reviewed-controls": {
                    "control-selections": [{"include-controls": [{"control-id": c} for c in control_ids]}]
                },
                "findings": findings,
            }],
        }
    }
    return json.dumps(doc, indent=2)
