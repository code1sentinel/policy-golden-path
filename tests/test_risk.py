import pytest

from oscal_assess.catalog import Catalog
from oscal_assess.fair import FairError
from oscal_assess.loader import load_statements
from oscal_assess.models import Statement
from oscal_assess.risk import RiskRegister, align_heuristic, assess_risks, detect_factors, parse_controls


@pytest.fixture
def results(examples):
    catalog = Catalog.load(examples / "catalog-excerpt.json")
    statements = load_statements(examples / "ssp-example.json", catalog)
    register = RiskRegister.load(examples / "risks-example.json")
    return {r.risk.id: r for r in assess_risks(register, statements, 0.8, simulations=2000)}


def test_example_register_outcomes(results):
    r1, r2, r3 = results["R-001"], results["R-002"], results["R-003"]
    assert r1.passed and r1.within_appetite and r1.residual.ale_mean < r1.inherent.ale_mean
    assert not r2.passed and any("ac-2" in g for g in r2.gaps)
    assert not r3.passed and r3.confidence == 0.0
    assert any("cp-9: no implementation statement" in g for g in r3.gaps)


def test_appetite_uses_residual_when_given(examples):
    register = RiskRegister.load(examples / "risks-example.json")
    register.appetite = 100_000
    [r1] = [r for r in assess_risks(register, [], 0.8, simulations=2000) if r.risk.id == "R-001"]
    assert r1.exposure is r1.residual
    assert r1.within_appetite == (r1.residual.ale_mean <= 100_000)


def test_exceeding_appetite_fails_even_when_addressed(examples):
    register = RiskRegister.load(examples / "risks-example.json")
    register.risks[0].appetite = 1
    statements = load_statements(examples / "ssp-example.json", Catalog.load(examples / "catalog-excerpt.json"))
    r1 = assess_risks(register, statements, 0.8, simulations=2000)[0]
    assert r1.addressed and r1.within_appetite is False and not r1.passed
    assert any("exceeds the appetite" in g for g in r1.gaps)


def test_p90_appetite_metric(examples):
    register = RiskRegister.load(examples / "risks-example.json")
    register.appetite_metric = "p90"
    r3 = assess_risks(register, [], 0.8, simulations=2000)[2]
    assert r3.exposure_value == r3.inherent.ale_p90


def test_detect_factors():
    assert detect_factors("Traffic is blocked at the firewall.") == ["tef"]
    assert detect_factors("Users authenticate with MFA.") == ["vulnerability"]
    assert detect_factors("The SOC is alerted and contains the incident within 4 hours.") == ["loss_magnitude"]


def test_wrong_factor_scores_lower():
    register = RiskRegister.parse({"risks": [{
        "title": "Ransomware encrypts file servers", "controls": {"cp-9": "loss_magnitude"},
        "inherent": {"ale": 1},
    }]})
    risk = register.risks[0]
    on = Statement("cp-9", "The infrastructure team backs up the file servers daily to immutable storage and "
                           "restores from backup within 4 hours after ransomware; restore tests are logged.", "ssp")
    off = Statement("cp-9", "The infrastructure team patches the file servers weekly against ransomware "
                            "using a configured baseline; patch reports are logged.", "ssp")
    score_on, _, _ = align_heuristic(risk, {"cp-9": [on]}, 0.8)
    score_off, _, gaps = align_heuristic(risk, {"cp-9": [off]}, 0.8)
    assert score_on > score_off
    assert any("expected to reduce loss magnitude" in g for g in gaps)


def test_parse_controls_accepts_aliases_and_rejects_unknown():
    assert parse_controls(["IA-2"]) == {"ia-2": None}
    assert parse_controls({"au-6": "detection", "ia-2": "resistance"}) == {"au-6": "loss_magnitude",
                                                                         "ia-2": "vulnerability"}
    with pytest.raises(FairError, match="unknown FAIR factor"):
        parse_controls({"ia-2": "magic"})


def test_register_validation():
    with pytest.raises(FairError, match="'risks' list"):
        RiskRegister.parse({})
    with pytest.raises(FairError, match="'title' is required"):
        RiskRegister.parse({"risks": [{"inherent": {"ale": 1}}]})
    with pytest.raises(FairError, match="duplicate risk id"):
        RiskRegister.parse({"risks": [{"id": "A", "title": "x", "inherent": {"ale": 1}}] * 2})
