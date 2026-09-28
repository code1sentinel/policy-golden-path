from __future__ import annotations

from dataclasses import dataclass, field

IMPLEMENTATION = "implementation"
RISK_STATEMENT = "risk-statement"
RECOMMENDATION = "recommendation"
IDENTIFIED_RISK = "identified-risk"

KIND_LABELS = {
    IMPLEMENTATION: "Implementation statement",
    RISK_STATEMENT: "Risk statement",
    RECOMMENDATION: "Recommendation",
    IDENTIFIED_RISK: "Identified risk",
}


@dataclass
class Treatment:
    """A policy intent, a control, or both, that is meant to treat an identified risk."""

    label: str
    policy_intent: str | None = None
    control_statement: str | None = None
    control_id: str | None = None

    @property
    def text(self) -> str:
        return " ".join(t for t in (self.policy_intent, self.control_statement) if t)


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
    treatments: list[Treatment] = field(default_factory=list)  # for an identified risk: what treats it

    @property
    def targets(self) -> list[tuple[str, str | None]]:
        """The (control id, statement id) pairs this text is about.

        A risk can be linked to several controls or statement parts, joined as
        "ac-2_smt.j, au-6"; each part id's control is the text before the "_".
        """
        if self.kind == IMPLEMENTATION:
            return [(self.control_id, self.statement_id)] if self.control_id else []
        out = []
        for target in filter(None, (t.strip() for t in self.control_id.split(","))):
            control, _, part = target.partition("_")
            out.append((control, target if part else None))
        return out

    @property
    def key(self) -> str:
        if self.kind != IMPLEMENTATION:
            label = self.title or self.uuid or "untitled"
            return f"{label} [{self.control_id}]" if self.control_id else label
        target = self.statement_id or self.control_id
        if not target:
            return self.component or self.uuid or "untitled"
        return f"{target} [{self.component}]" if self.component else target


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
    details: dict = field(default_factory=dict)  # kind-specific findings, e.g. each treatment's relevance

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

        s = self.statement
        out = {
            "kind": s.kind,
            "item": s.key,
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
        out.update(self.details)
        out.update({
            "confidence": round(self.confidence, 4),
            "practices": self.practices,
            "criteria": [
                {"name": c.name, "practice": (practice(s.kind, c.name) or {}).get("title", c.name),
                 "status": practice_status(c.score, bool(c.issues)), "score": round(c.score, 4),
                 "weight": round(c.weight, 4), "note": c.note, "issues": c.issues}
                for c in self.criteria
            ],
            "improvements": self.improvements,
            "rationale": self.rationale,
            "text": s.text,
        })
        return out
