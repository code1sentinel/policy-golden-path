"""Risk register loading, and whether control statements address each risk.

A risk passes when the statements for its linked controls address it with
enough confidence and, if an appetite is set, its exposure is within it:
residual exposure when a residual estimate is given, inherent otherwise.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import heuristic
from .fair import DEFAULT_SIMULATIONS, FairError, FairModel, FairResult, simulate
from .models import Statement

# How a control's alignment with a risk is scored.
WEIGHTS = {"relevance": 0.30, "factor": 0.40, "quality": 0.30}

# Which FAIR factor a control reduces.
FACTORS = {
    "tef": "threat event frequency (avoidance, deterrence)",
    "vulnerability": "vulnerability (resistance strength)",
    "loss_magnitude": "loss magnitude (detection, response, containment)",
}
_FACTOR_ALIASES = {
    "tef": "tef", "threat_event_frequency": "tef", "avoidance": "tef", "deterrence": "tef",
    "vulnerability": "vulnerability", "vuln": "vulnerability", "resistance": "vulnerability",
    "resistance_strength": "vulnerability", "lef": "vulnerability",
    "loss_magnitude": "loss_magnitude", "lm": "loss_magnitude", "detection": "loss_magnitude",
    "response": "loss_magnitude", "containment": "loss_magnitude",
}
_FACTOR_SIGNALS = {
    "tef": re.compile(
        r"\b(block(s|ed|ing)?|deny|denies|denied|prohibit(s|ed)?|restrict(s|ed)?|allow-?list(s|ed)?|"
        r"segment(ed|ation)?|isolat(e|ed|ion)|geo-?block(ing)?|rate[- ]limit(s|ed|ing)?|throttl(e|ed|ing)|"
        r"deter(s|red|rence)?|disabl(e|ed|es)|remov(e|ed|es)|not exposed|private (network|subnet|endpoint)|"
        r"firewall|waf|filter(s|ed|ing)?|quarantin(e|ed))\b", re.I),
    "vulnerability": re.compile(
        r"\b(mfa|multi-factor|phishing-resistant|authenticat(e|es|ed|ion)|encrypt(s|ed|ion)?|patch(es|ed|ing)?|"
        r"harden(ed|ing)?|least privilege|approv(al|als|ed)|review(s|ed)?|unique(ly)?|password|credential|"
        r"validat(e|es|ed|ion)|baseline|configur(ed|ation)|access control|rbac|sso|saml|key rotation|"
        r"vulnerability scan(s|ning)?|secure coding)\b", re.I),
    "loss_magnitude": re.compile(
        r"\b(detect(s|ed|ion)?|alert(s|ed|ing)?|monitor(s|ed|ing)?|incident response|respond(s|ed)?|"
        r"contain(s|ed|ment)?|revok(e|es|ed)|backup(s)?|restor(e|es|ed|ation)|recover(y|ed)?|"
        r"within \d+ (minutes?|hours?)|real[- ]time|escalat(e|es|ed|ion)|insurance|failover|"
        r"investigat(e|es|ed|ion)|report(s|ed)? to|notif(y|ies|ied|ication))\b", re.I),
}


@dataclass
class Risk:
    id: str
    title: str
    controls: dict[str, str | None]  # control id -> FAIR factor it should reduce, if stated
    inherent: FairModel
    residual: FairModel | None = None
    description: str = ""
    asset: str = ""
    threat_community: str = ""
    threat_event: str = ""
    effect: str = ""
    appetite: float | None = None

    @property
    def scenario(self) -> str:
        parts = [self.title, self.description, self.asset, self.threat_community, self.threat_event, self.effect]
        return " ".join(p for p in parts if p)

    def to_dict(self) -> dict:
        out = {"id": self.id, "title": self.title}
        for k in ("description", "asset", "threat_community", "threat_event", "effect"):
            if getattr(self, k):
                out[k] = getattr(self, k)
        out["controls"] = {c: f for c, f in self.controls.items()}
        if self.appetite is not None:
            out["appetite"] = self.appetite
        out["inherent"] = self.inherent.to_dict()
        if self.residual is not None:
            out["residual"] = self.residual.to_dict()
        return out


@dataclass
class RiskRegister:
    risks: list[Risk]
    currency: str = "USD"
    appetite: float | None = None
    appetite_metric: str = "mean"  # compare "mean" or "p90" ALE against appetite

    @classmethod
    def load(cls, path: str | Path) -> "RiskRegister":
        with open(path, encoding="utf-8") as fh:
            return cls.parse(json.load(fh))

    @classmethod
    def parse(cls, data: dict) -> "RiskRegister":
        if not isinstance(data, dict) or not isinstance(data.get("risks"), list):
            raise FairError("risk register: expected an object with a 'risks' list")
        metric = data.get("appetite_metric", "mean")
        if metric not in ("mean", "p90"):
            raise FairError("risk register: 'appetite_metric' must be 'mean' or 'p90'")
        seen: set[str] = set()
        risks = []
        for i, r in enumerate(data["risks"]):
            risk = _parse_risk(r, i)
            if risk.id in seen:
                raise FairError(f"risk register: duplicate risk id {risk.id!r}")
            seen.add(risk.id)
            risks.append(risk)
        return cls(risks, data.get("currency", "USD"), data.get("appetite"), metric)

    def to_dict(self) -> dict:
        out = {"currency": self.currency}
        if self.appetite is not None:
            out["appetite"] = self.appetite
        if self.appetite_metric != "mean":
            out["appetite_metric"] = self.appetite_metric
        out["risks"] = [r.to_dict() for r in self.risks]
        return out


def _parse_risk(r: dict, i: int) -> Risk:
    name = f"risks[{i}]"
    if not isinstance(r, dict):
        raise FairError(f"{name}: expected an object")
    rid = r.get("id") or f"R-{i + 1:03d}"
    name = f"risk {rid}"
    if not r.get("title"):
        raise FairError(f"{name}: 'title' is required")
    if "inherent" not in r:
        raise FairError(f"{name}: 'inherent' FAIR factors are required")
    return Risk(
        id=rid,
        title=r["title"],
        controls=parse_controls(r.get("controls", []), name),
        inherent=FairModel.parse(r["inherent"], f"{name}.inherent"),
        residual=FairModel.parse(r["residual"], f"{name}.residual") if r.get("residual") else None,
        description=r.get("description", ""),
        asset=r.get("asset", ""),
        threat_community=r.get("threat_community", ""),
        threat_event=r.get("threat_event", ""),
        effect=r.get("effect", ""),
        appetite=r.get("appetite"),
    )


def parse_controls(value, name: str = "controls") -> dict[str, str | None]:
    if isinstance(value, list):
        return {str(c).lower(): None for c in value}
    if isinstance(value, dict):
        out = {}
        for c, f in value.items():
            if f is None:
                out[c.lower()] = None
                continue
            factor = _FACTOR_ALIASES.get(str(f).lower().replace(" ", "_").replace("-", "_"))
            if factor is None:
                raise FairError(f"{name}: unknown FAIR factor {f!r} for {c}; use one of {', '.join(FACTORS)}")
            out[c.lower()] = factor
        return out
    raise FairError(f"{name}: expected a list of control ids or a map of control id to FAIR factor")


def detect_factors(text: str) -> list[str]:
    return [f for f, pattern in _FACTOR_SIGNALS.items() if pattern.search(text)]


@dataclass
class ControlAlignment:
    control_id: str
    expected_factor: str | None
    detected_factors: list[str]
    relevance: float
    factor_score: float
    quality: float
    score: float
    statements: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "control_id": self.control_id,
            "expected_factor": self.expected_factor,
            "detected_factors": self.detected_factors,
            "relevance": round(self.relevance, 4),
            "factor_score": round(self.factor_score, 4),
            "quality": round(self.quality, 4),
            "score": round(self.score, 4),
            "statements": self.statements,
            "note": self.note,
        }


@dataclass
class RiskAssessment:
    risk: Risk
    inherent: FairResult
    residual: FairResult | None
    confidence: float
    threshold: float
    engine: str
    appetite: float | None
    appetite_metric: str
    controls: list[ControlAlignment] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    rationale: str = ""

    @property
    def exposure(self) -> FairResult:
        return self.residual or self.inherent

    @property
    def exposure_value(self) -> float:
        e = self.exposure
        return e.ale_p90 if self.appetite_metric == "p90" else e.ale_mean

    @property
    def within_appetite(self) -> bool | None:
        return None if self.appetite is None else self.exposure_value <= self.appetite

    @property
    def addressed(self) -> bool:
        return self.confidence >= self.threshold

    @property
    def passed(self) -> bool:
        return self.addressed and self.within_appetite is not False

    def to_dict(self) -> dict:
        return {
            "risk_id": self.risk.id,
            "title": self.risk.title,
            "engine": self.engine,
            "confidence": round(self.confidence, 4),
            "threshold": self.threshold,
            "addressed": self.addressed,
            "appetite": self.appetite,
            "appetite_metric": self.appetite_metric,
            "within_appetite": self.within_appetite,
            "result": "pass" if self.passed else "fail",
            "inherent": self.inherent.to_dict(),
            "residual": self.residual.to_dict() if self.residual else None,
            "controls": [c.to_dict() for c in self.controls],
            "gaps": self.gaps,
            "rationale": self.rationale,
        }


def quantify(risk: Risk, simulations: int = DEFAULT_SIMULATIONS, seed: int | None = 0):
    inherent = simulate(risk.inherent, simulations, seed)
    residual = simulate(risk.residual, simulations, seed) if risk.residual else None
    return inherent, residual


def statements_by_control(statements: list[Statement]) -> dict[str, list[Statement]]:
    out: dict[str, list[Statement]] = {}
    for s in statements:
        out.setdefault(s.control_id.lower(), []).append(s)
    return out


RELEVANCE_FULL_AT = 3  # scenario terms a statement must share to count as fully on-topic


def _scenario_terms(text: str) -> set[str]:
    return heuristic._terms(text.replace("-", " "))


def _relevance(scenario: str, text: str) -> tuple[float, list[str]]:
    scenario_terms = _scenario_terms(scenario)
    matched = sorted(scenario_terms & _scenario_terms(text))
    if not scenario_terms:
        return 1.0, matched
    return min(1.0, len(matched) / min(RELEVANCE_FULL_AT, len(scenario_terms))), matched


def align_heuristic(risk: Risk, by_control: dict[str, list[Statement]], threshold: float):
    """Score how well each linked control's statements address the risk scenario and FAIR factor."""
    results: list[ControlAlignment] = []
    gaps: list[str] = []
    if not risk.controls:
        gaps.append("Link the risk to the controls that treat it.")
    for cid, expected in risk.controls.items():
        stmts = by_control.get(cid, [])
        if not stmts:
            results.append(ControlAlignment(cid, expected, [], 0.0, 0.0, 0.0, 0.0,
                                            note="no implementation statement found"))
            gaps.append(f"{cid}: no implementation statement found for this control.")
            continue
        text = " ".join(s.text for s in stmts)
        relevance, matched = _relevance(risk.scenario, text)
        detected = detect_factors(text)
        if expected:
            factor_score = 1.0 if expected in detected else (0.3 if detected else 0.0)
        else:
            factor_score = 1.0 if detected else 0.0
        quality = sum(heuristic.assess(s, threshold).confidence for s in stmts) / len(stmts)
        score = WEIGHTS["relevance"] * relevance + WEIGHTS["factor"] * factor_score + WEIGHTS["quality"] * quality
        note = f"scenario terms matched: {', '.join(matched) or 'none'}"
        results.append(ControlAlignment(cid, expected, detected, relevance, factor_score, quality, score,
                                        [s.key for s in stmts], note))
        if relevance < 0.6:
            gaps.append(f"{cid}: statement does not mention the risk scenario "
                        f"(asset, threat or event); tie it to '{risk.title}'.")
        if expected and expected not in detected:
            gaps.append(f"{cid}: expected to reduce {FACTORS[expected]}, but the statement does not say how.")
        elif not detected:
            gaps.append(f"{cid}: statement does not describe how it prevents, resists or limits the loss.")
        if quality < threshold:
            gaps.append(f"{cid}: the statement itself scores {quality:.0%}; see the statement assessment.")
    confidence = sum(c.score for c in results) / len(results) if results else 0.0
    return round(confidence, 4), results, gaps


def assess_risks(register: RiskRegister, statements: list[Statement], threshold: float,
                 engine: str = "heuristic", assessor=None, simulations: int = DEFAULT_SIMULATIONS,
                 seed: int | None = 0) -> list[RiskAssessment]:
    by_control = statements_by_control(statements)
    out = []
    for risk in register.risks:
        inherent, residual = quantify(risk, simulations, seed)
        appetite = risk.appetite if risk.appetite is not None else register.appetite
        if assessor is not None:
            confidence, controls, gaps, rationale, engine_name = assessor.assess_risk(risk, by_control)
        else:
            confidence, controls, gaps = align_heuristic(risk, by_control, threshold)
            rationale, engine_name = f"Control alignment {confidence:.0%}.", engine
        ra = RiskAssessment(risk, inherent, residual, confidence, threshold, engine_name, appetite,
                            register.appetite_metric, controls, gaps, rationale)
        if ra.within_appetite is False:
            basis = "residual" if residual else "inherent (no residual estimate given)"
            ra.gaps.append(
                f"{basis.capitalize()} exposure {ra.exposure_value:,.0f} {register.currency} "
                f"({register.appetite_metric}) exceeds the appetite of {appetite:,.0f}."
            )
        out.append(ra)
    return out
