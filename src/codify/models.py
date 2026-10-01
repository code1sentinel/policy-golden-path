"""What Codify works with: a control statement to score, and the result of scoring it."""

from __future__ import annotations

from dataclasses import dataclass, field

CONTROL_STATEMENT = "control-statement"


@dataclass
class Statement:
    """A control statement to score, with what it is checked against."""

    control_id: str
    text: str
    source: str = "codify"
    requirement: str | None = None  # the control text it must cover, when there is one
    policy_intent: str | None = None  # what the policy says the control must achieve
    risk_statement: str | None = None  # the risk it treats: gives the control its purpose
    kind: str = CONTROL_STATEMENT


@dataclass
class CriterionResult:
    name: str
    score: float  # 0.0 to 1.0
    weight: float
    note: str = ""
    issues: list[str] = field(default_factory=list)  # areas for improvement that belong to this practice


@dataclass
class Assessment:
    statement: Statement
    confidence: float  # 0.0 to 1.0
    criteria: list[CriterionResult] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    rationale: str = ""

    @property
    def practices(self) -> dict[str, int]:
        """How many of the scored best practices are adopted, partly adopted or not yet adopted."""
        from .guides import practice_status

        counts = {"adopted": 0, "partly": 0, "not-yet": 0}
        for c in self.criteria:
            counts[practice_status(c.score, bool(c.issues))] += 1
        return {**counts, "total": len(self.criteria)}

    def to_dict(self) -> dict:
        from .guides import practice, practice_status

        return {
            "confidence": round(self.confidence, 4),
            "practices": self.practices,
            "criteria": [
                {"name": c.name, "practice": (practice(c.name) or {}).get("title", c.name),
                 "status": practice_status(c.score, bool(c.issues)), "score": round(c.score, 4),
                 "weight": round(c.weight, 4), "note": c.note, "issues": c.issues}
                for c in self.criteria
            ],
            "improvements": self.improvements,
            "rationale": self.rationale,
        }
