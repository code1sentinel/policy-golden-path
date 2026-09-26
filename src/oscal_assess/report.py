"""Render assessments as a terminal table, JSON, Markdown or OSCAL assessment results."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from . import __version__
from .fair import FairResult
from .models import Assessment
from .risk import RiskAssessment

NS = "https://grcengineering.club/ns/oscal-assess"


def summary(assessments: list[Assessment]) -> dict:
    passed = sum(a.passed for a in assessments)
    return {
        "total": len(assessments),
        "passed": passed,
        "failed": len(assessments) - passed,
        "threshold": assessments[0].threshold if assessments else None,
    }


def money(value: float, currency: str = "") -> str:
    for unit, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(value) >= size:
            return f"{currency} {value / size:.1f}{unit}".strip()
    return f"{currency} {value:,.0f}".strip()


def fair_line(r: FairResult, currency: str = "") -> str:
    return (f"ALE mean {money(r.ale_mean, currency)} "
            f"(P10 {money(r.ale_p10)}, P50 {money(r.ale_p50)}, P90 {money(r.ale_p90)})")


def risk_table(risks: list[RiskAssessment], currency: str = "") -> str:
    lines = ["Risk", "----"]
    for ra in risks:
        appetite = {None: "no appetite set", True: "within appetite", False: "EXCEEDS appetite"}[ra.within_appetite]
        lines.append(f"{ra.risk.id}  {ra.risk.title}")
        lines.append(f"  inherent  {fair_line(ra.inherent, currency)}")
        if ra.residual:
            reduction = ra.inherent.ale_mean - ra.residual.ale_mean
            lines.append(f"  residual  {fair_line(ra.residual, currency)}  (reduced by {money(reduction, currency)})")
        lines.append(f"  controls  " + ", ".join(
            f"{c.control_id} {c.score:.0%}" + (f" [{c.expected_factor}]" if c.expected_factor else "")
            for c in ra.controls) if ra.controls else "  controls  none linked")
        lines.append(f"  addressed {ra.confidence:.0%}, {appetite}  ->  {'PASS' if ra.passed else 'FAIL'}")
        if not ra.passed:
            lines += [f"    - {g}" for g in ra.gaps]
    passed = sum(r.passed for r in risks)
    lines.append("")
    lines.append(f"{passed}/{len(risks)} risks addressed at a {risks[0].threshold:.0%} confidence threshold"
                 + (" and within appetite." if any(r.appetite is not None for r in risks) else "."))
    return "\n".join(lines)


def to_table(assessments: list[Assessment], risks: list[RiskAssessment] | None = None,
             currency: str = "") -> str:
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
    if risks:
        lines += ["", "", risk_table(risks, currency)]
    return "\n".join(lines)


def to_json(assessments: list[Assessment], risks: list[RiskAssessment] | None = None,
            currency: str = "") -> str:
    doc = {"summary": summary(assessments), "assessments": [a.to_dict() for a in assessments]}
    if risks is not None:
        doc["risk_summary"] = {"total": len(risks), "passed": sum(r.passed for r in risks),
                               "currency": currency}
        doc["risks"] = [r.to_dict() for r in risks]
    return json.dumps(doc, indent=2)


def to_markdown(assessments: list[Assessment], risks: list[RiskAssessment] | None = None,
                currency: str = "") -> str:
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
    if risks:
        out += ["", "# Risk treatment (FAIR)", "",
                f"**{sum(r.passed for r in risks)} of {len(risks)} risks addressed.**", "",
                "| Risk | Inherent ALE (mean / P90) | Residual ALE (mean / P90) | Addressed | Appetite | Result |",
                "| --- | --- | --- | --- | --- | --- |"]
        for ra in risks:
            res = f"{money(ra.residual.ale_mean, currency)} / {money(ra.residual.ale_p90)}" if ra.residual else "—"
            appetite = {None: "—", True: "within", False: "exceeds"}[ra.within_appetite]
            out.append(
                f"| {ra.risk.id} {ra.risk.title} | {money(ra.inherent.ale_mean, currency)} / "
                f"{money(ra.inherent.ale_p90)} | {res} | {ra.confidence:.0%} | {appetite} | "
                f"{'✅ pass' if ra.passed else '❌ fail'} |"
            )
        for ra in risks:
            if ra.passed:
                continue
            out += ["", f"## {ra.risk.id} — {ra.risk.title}", "", ra.rationale, ""]
            out += [f"- {g}" for g in ra.gaps]
    return "\n".join(out) + "\n"


def _oscal_risk(ra: RiskAssessment, currency: str) -> dict:
    facets = [
        {"name": "inherent-ale-mean", "system": NS, "value": f"{ra.inherent.ale_mean:.2f}"},
        {"name": "inherent-ale-p90", "system": NS, "value": f"{ra.inherent.ale_p90:.2f}"},
    ]
    if ra.residual:
        facets += [
            {"name": "residual-ale-mean", "system": NS, "value": f"{ra.residual.ale_mean:.2f}"},
            {"name": "residual-ale-p90", "system": NS, "value": f"{ra.residual.ale_p90:.2f}"},
        ]
    facets.append({"name": "treatment-confidence", "system": NS, "value": f"{ra.confidence:.4f}"})
    return {
        "uuid": str(uuid.uuid4()),
        "title": f"{ra.risk.id}: {ra.risk.title}",
        "description": ra.risk.description or ra.risk.title,
        "statement": ra.rationale + (" Gaps: " + " ".join(ra.gaps) if ra.gaps else ""),
        "props": [{"name": "currency", "ns": NS, "value": currency or "USD"}],
        "status": "closed" if ra.passed else "open",
        "characterizations": [{
            "origin": {"actors": [{"type": "tool", "actor-uuid": TOOL_UUID}]},
            "facets": facets,
        }],
    }


TOOL_UUID = "7c3e5a9e-2f6b-4b1d-9d5e-0a5f6c1e8b21"


def to_assessment_results(assessments: list[Assessment], source_href: str,
                          risks: list[RiskAssessment] | None = None, currency: str = "") -> str:
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
                **({
                    "local-definitions": {"components": [{
                        "uuid": TOOL_UUID, "type": "software", "title": "oscal-assess",
                        "description": "FAIR quantification and control treatment assessment.",
                        "status": {"state": "operational"},
                    }]},
                    "risks": [_oscal_risk(r, currency) for r in risks],
                } if risks else {}),
            }],
        }
    }
    return json.dumps(doc, indent=2)
