from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Statement:
    """One implementation statement pulled out of an SSP or component definition."""

    control_id: str
    text: str
    source: str  # "ssp" or "component-definition"
    uuid: str | None = None
    statement_id: str | None = None
    component: str | None = None
    requirement: str | None = None  # control text from the catalog, when one is supplied
    policy_intent: str | None = None  # what the organization's policy says this control must achieve
    policy_ids: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
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
    threshold: float
    engine: str
    criteria: list[CriterionResult] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    rationale: str = ""

    @property
    def passed(self) -> bool:
        return self.confidence >= self.threshold

    def to_dict(self) -> dict:
        s = self.statement
        return {
            "control_id": s.control_id,
            "statement_id": s.statement_id,
            "component": s.component,
            "uuid": s.uuid,
            "source": s.source,
            "policies": s.policy_ids,
            "engine": self.engine,
            "confidence": round(self.confidence, 4),
            "threshold": self.threshold,
            "result": "pass" if self.passed else "fail",
            "criteria": [
                {"name": c.name, "score": round(c.score, 4), "weight": round(c.weight, 4), "note": c.note}
                for c in self.criteria
            ],
            "gaps": self.gaps,
            "rationale": self.rationale,
            "statement": s.text,
        }
