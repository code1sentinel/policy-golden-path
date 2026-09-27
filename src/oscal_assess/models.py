from __future__ import annotations

from dataclasses import dataclass, field

IMPLEMENTATION = "implementation"
RISK_STATEMENT = "risk-statement"
RECOMMENDATION = "recommendation"

KIND_LABELS = {
    IMPLEMENTATION: "Implementation statement",
    RISK_STATEMENT: "Risk statement",
    RECOMMENDATION: "Recommendation",
}


@dataclass
class Statement:
    """One piece of OSCAL text to assess.

    An implementation statement comes from an SSP or component definition; a
    risk statement or recommendation comes from a risk in assessment results
    or a POA&M.
    """

    control_id: str
    text: str
    source: str  # "ssp", "component-definition", "assessment-results" or "poam"
    uuid: str | None = None
    statement_id: str | None = None
    component: str | None = None
    requirement: str | None = None  # control text from the catalog, when one is supplied
    policy_intent: str | None = None  # what the organization's policy says this control must achieve
    policy_ids: list[str] = field(default_factory=list)
    kind: str = IMPLEMENTATION
    title: str | None = None  # risk or remediation title
    risk_title: str | None = None  # for a recommendation: the risk it responds to
    risk_statement: str | None = None
    ratings: dict[str, str] = field(default_factory=dict)  # risk characterization facets, e.g. likelihood
    deadline: str | None = None  # remediation date from the risk deadline or remediation tasks
    owner: str | None = None  # responsible roles or parties recorded on the remediation

    @property
    def key(self) -> str:
        if self.kind != IMPLEMENTATION:
            label = self.title or self.uuid or "untitled"
            return f"{label} [{self.control_id}]" if self.control_id else label
        target = self.statement_id or self.control_id
        return f"{target} [{self.component}]" if self.component else target


@dataclass
class CriterionResult:
    name: str
    score: float  # 0.0 to 1.0
    weight: float
    note: str = ""


@dataclass
class Assessment:
    statement: Statement
    confidence: float  # 0.0 to 1.0
    engine: str
    criteria: list[CriterionResult] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict:
        s = self.statement
        out = {
            "kind": s.kind,
            "control_id": s.control_id or None,
            "uuid": s.uuid,
            "source": s.source,
        }
        if s.kind == IMPLEMENTATION:
            out.update({"statement_id": s.statement_id, "component": s.component, "policies": s.policy_ids})
        else:
            out.update({"title": s.title, "ratings": s.ratings, "deadline": s.deadline, "owner": s.owner})
            if s.kind == "recommendation":
                out["risk_title"] = s.risk_title
        out.update({
            "engine": self.engine,
            "confidence": round(self.confidence, 4),
            "criteria": [
                {"name": c.name, "score": round(c.score, 4), "weight": round(c.weight, 4), "note": c.note}
                for c in self.criteria
            ],
            "improvements": self.improvements,
            "rationale": self.rationale,
            "text": s.text,
        })
        return out
