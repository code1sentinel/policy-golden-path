"""FAIR (Factor Analysis of Information Risk) quantification.

A risk's annualized loss exposure (ALE) is Loss Event Frequency x Loss Magnitude.
Either can be given directly or derived from the factors below it:

    Risk
    ├── Loss Event Frequency (LEF)        events per year
    │   ├── Threat Event Frequency (TEF)  attempts per year
    │   │   ├── Contact Frequency
    │   │   └── Probability of Action     0-1
    │   └── Vulnerability                 0-1
    │       ├── Threat Capability         0-100 percentile
    │       └── Resistance Strength       0-100 percentile
    └── Loss Magnitude (LM)               per event
        ├── Primary Loss
        └── Secondary Risk
            ├── Secondary Loss Event Frequency   0-1, share of events with secondary effects
            └── Secondary Loss Magnitude

Every factor is a point value or a PERT range {"min", "most_likely", "max"}.
Annual loss is simulated with Monte Carlo: each trial draws a Poisson number
of loss events at the sampled LEF and sums a sampled magnitude for each.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

DEFAULT_SIMULATIONS = 10_000


class FairError(ValueError):
    pass


@dataclass
class Estimate:
    """A point value or a PERT (min, most likely, max) range."""

    low: float
    mode: float
    high: float

    @classmethod
    def parse(cls, value, name: str) -> "Estimate":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return cls(float(value), float(value), float(value))
        if isinstance(value, dict):
            try:
                low, high = float(value["min"]), float(value["max"])
            except (KeyError, TypeError, ValueError):
                raise FairError(f"{name}: a range needs numeric 'min' and 'max'") from None
            mode = float(value.get("most_likely", (low + high) / 2))
            if not low <= mode <= high:
                raise FairError(f"{name}: expected min <= most_likely <= max, got {low}, {mode}, {high}")
            return cls(low, mode, high)
        raise FairError(f"{name}: expected a number or {{min, most_likely, max}}, got {value!r}")

    @property
    def mean(self) -> float:
        return (self.low + 4 * self.mode + self.high) / 6

    def sample(self, rng: random.Random) -> float:
        if self.high == self.low:
            return self.low
        span = self.high - self.low
        alpha = 1 + 4 * (self.mode - self.low) / span
        beta = 1 + 4 * (self.high - self.mode) / span
        return self.low + rng.betavariate(alpha, beta) * span

    def to_dict(self):
        if self.low == self.high:
            return self.low
        return {"min": self.low, "most_likely": self.mode, "max": self.high}


@dataclass
class FairModel:
    """The factors supplied for one scenario; missing upper factors are derived from lower ones."""

    ale: Estimate | None = None
    lef: Estimate | None = None
    tef: Estimate | None = None
    contact_frequency: Estimate | None = None
    probability_of_action: Estimate | None = None
    vulnerability: Estimate | None = None
    threat_capability: Estimate | None = None
    resistance_strength: Estimate | None = None
    lm: Estimate | None = None
    primary_loss: Estimate | None = None
    secondary_lef: Estimate | None = None
    secondary_loss: Estimate | None = None

    FIELDS = ("ale", "lef", "tef", "contact_frequency", "probability_of_action", "vulnerability",
              "threat_capability", "resistance_strength", "lm", "primary_loss", "secondary_lef",
              "secondary_loss")
    PROBABILITIES = ("probability_of_action", "vulnerability", "secondary_lef")
    PERCENTILES = ("threat_capability", "resistance_strength")

    @classmethod
    def parse(cls, data: dict, name: str = "fair") -> "FairModel":
        if not isinstance(data, dict):
            raise FairError(f"{name}: expected an object of FAIR factors")
        unknown = set(data) - set(cls.FIELDS)
        if unknown:
            raise FairError(f"{name}: unknown FAIR factor(s): {', '.join(sorted(unknown))}")
        model = cls(**{k: Estimate.parse(v, f"{name}.{k}") for k, v in data.items()})
        model.validate(name)
        return model

    def validate(self, name: str) -> None:
        for f in self.FIELDS:
            est = getattr(self, f)
            if est is None:
                continue
            if est.low < 0:
                raise FairError(f"{name}.{f}: must not be negative")
            if f in self.PROBABILITIES and est.high > 1:
                raise FairError(f"{name}.{f}: is a probability, so must be between 0 and 1")
            if f in self.PERCENTILES and est.high > 100:
                raise FairError(f"{name}.{f}: is a percentile, so must be between 0 and 100")
        if self.ale is None:
            if not self._has_lef():
                raise FairError(f"{name}: give 'ale', 'lef', 'tef' with vulnerability, or the factors beneath them")
            if not self._has_lm():
                raise FairError(f"{name}: give 'ale', 'lm', or 'primary_loss' to size the loss")

    def _has_tef(self) -> bool:
        return self.tef is not None or (self.contact_frequency is not None and self.probability_of_action is not None)

    def _has_vuln(self) -> bool:
        return self.vulnerability is not None or (
            self.threat_capability is not None and self.resistance_strength is not None
        )

    def _has_lef(self) -> bool:
        return self.lef is not None or (self._has_tef() and self._has_vuln())

    def _has_lm(self) -> bool:
        return self.lm is not None or self.primary_loss is not None

    def to_dict(self) -> dict:
        return {f: getattr(self, f).to_dict() for f in self.FIELDS if getattr(self, f) is not None}


@dataclass
class FairResult:
    ale_mean: float
    ale_p10: float
    ale_p50: float
    ale_p90: float
    lef_mean: float | None
    lm_mean: float | None
    vulnerability: float | None
    simulations: int
    derived: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ale": {"mean": round(self.ale_mean, 2), "p10": round(self.ale_p10, 2),
                    "p50": round(self.ale_p50, 2), "p90": round(self.ale_p90, 2)},
            "lef_mean": None if self.lef_mean is None else round(self.lef_mean, 4),
            "lm_mean": None if self.lm_mean is None else round(self.lm_mean, 2),
            "vulnerability": None if self.vulnerability is None else round(self.vulnerability, 4),
            "simulations": self.simulations,
            "derived": self.derived,
        }


def _poisson(lam: float, rng: random.Random) -> int:
    if lam <= 0:
        return 0
    if lam > 50:
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def _percentile(sorted_values: list[float], q: float) -> float:
    idx = q * (len(sorted_values) - 1)
    lo, hi = math.floor(idx), math.ceil(idx)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (idx - lo)


def simulate(model: FairModel, simulations: int = DEFAULT_SIMULATIONS, seed: int | None = 0) -> FairResult:
    rng = random.Random(seed)
    derived: list[str] = []

    if model.ale is not None:
        samples = sorted(model.ale.sample(rng) for _ in range(simulations))
        return FairResult(sum(samples) / simulations, _percentile(samples, 0.1), _percentile(samples, 0.5),
                          _percentile(samples, 0.9), None, None, None, simulations, ["ale given directly"])

    # Vulnerability from threat capability vs resistance strength: the share of
    # trials in which a sampled attacker beats the sampled control strength.
    vuln_p = None
    if model.lef is None and model.vulnerability is None:
        wins = sum(model.threat_capability.sample(rng) > model.resistance_strength.sample(rng)
                   for _ in range(simulations))
        vuln_p = wins / simulations
        derived.append(f"vulnerability {vuln_p:.0%} from threat capability vs resistance strength")
    if model.lef is None and model.tef is None:
        derived.append("TEF from contact frequency x probability of action")
    if model.lef is None:
        derived.append("LEF from TEF x vulnerability")
    if model.lm is None:
        derived.append("LM from primary loss" + (" + secondary risk" if model.secondary_loss else ""))

    def sample_lef() -> float:
        if model.lef is not None:
            return model.lef.sample(rng)
        tef = (model.tef.sample(rng) if model.tef is not None
               else model.contact_frequency.sample(rng) * model.probability_of_action.sample(rng))
        vuln = model.vulnerability.sample(rng) if model.vulnerability is not None else vuln_p
        return tef * vuln

    def sample_lm() -> float:
        if model.lm is not None:
            return model.lm.sample(rng)
        loss = model.primary_loss.sample(rng)
        if model.secondary_loss is not None:
            slef = model.secondary_lef.sample(rng) if model.secondary_lef is not None else 1.0
            if rng.random() < slef:
                loss += model.secondary_loss.sample(rng)
        return loss

    annual, lefs, lms = [], [], []
    for _ in range(simulations):
        lef = sample_lef()
        lefs.append(lef)
        total = 0.0
        for _ in range(_poisson(lef, rng)):
            lm = sample_lm()
            lms.append(lm)
            total += lm
        annual.append(total)
    annual.sort()
    lm_mean = sum(lms) / len(lms) if lms else sample_lm()
    return FairResult(
        sum(annual) / simulations, _percentile(annual, 0.1), _percentile(annual, 0.5), _percentile(annual, 0.9),
        sum(lefs) / simulations, lm_mean,
        vuln_p if vuln_p is not None else (model.vulnerability.mean if model.vulnerability else None),
        simulations, derived,
    )
