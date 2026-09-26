import pytest

from oscal_assess.fair import Estimate, FairError, FairModel, simulate


def test_estimate_parses_point_and_range():
    assert Estimate.parse(5, "x").to_dict() == 5.0
    assert Estimate.parse({"min": 1, "max": 3}, "x").mode == 2
    with pytest.raises(FairError, match="min <= most_likely <= max"):
        Estimate.parse({"min": 5, "most_likely": 1, "max": 3}, "x")
    with pytest.raises(FairError, match="expected a number"):
        Estimate.parse("lots", "x")


def test_pert_samples_stay_in_range():
    import random

    est, rng = Estimate(10, 20, 100), random.Random(1)
    samples = [est.sample(rng) for _ in range(2000)]
    assert min(samples) >= 10 and max(samples) <= 100
    assert abs(sum(samples) / len(samples) - est.mean) < 3


def test_direct_ale_is_passed_through():
    r = simulate(FairModel.parse({"ale": 1000}))
    assert r.ale_mean == r.ale_p90 == 1000


def test_point_lef_and_lm_give_expected_mean():
    r = simulate(FairModel.parse({"lef": 2, "lm": 1000}), simulations=20000)
    assert r.ale_mean == pytest.approx(2000, rel=0.05)


def test_tef_times_vulnerability():
    r = simulate(FairModel.parse({"tef": 10, "vulnerability": 0.5, "primary_loss": 100}), simulations=20000)
    assert r.lef_mean == pytest.approx(5)
    assert r.ale_mean == pytest.approx(500, rel=0.05)
    assert "LEF from TEF x vulnerability" in r.derived


def test_contact_frequency_and_capability_vs_resistance():
    weak = {"contact_frequency": 100, "probability_of_action": 0.5, "threat_capability": 80,
            "resistance_strength": {"min": 0, "most_likely": 10, "max": 20}, "primary_loss": 10}
    strong = dict(weak, resistance_strength={"min": 90, "most_likely": 95, "max": 100})
    assert simulate(FairModel.parse(weak)).vulnerability == 1.0
    assert simulate(FairModel.parse(strong)).vulnerability == 0.0


def test_secondary_loss_adds_to_magnitude():
    base = {"lef": 1, "primary_loss": 100}
    with_secondary = dict(base, secondary_lef=1, secondary_loss=900)
    assert simulate(FairModel.parse(with_secondary), 5000).lm_mean == pytest.approx(1000)
    assert simulate(FairModel.parse(base), 5000).lm_mean == pytest.approx(100)


def test_seed_makes_results_repeatable():
    model = FairModel.parse({"lef": {"min": 0.1, "max": 3}, "lm": {"min": 10, "max": 1000}})
    assert simulate(model, seed=7).ale_mean == simulate(model, seed=7).ale_mean


@pytest.mark.parametrize("data, message", [
    ({"lm": 5}, "give 'ale', 'lef'"),
    ({"lef": 1}, "size the loss"),
    ({"tef": 1, "lm": 5}, "give 'ale', 'lef'"),
    ({"lef": 1, "lm": 1, "vulnerability": 2}, "probability"),
    ({"ale": 1, "threat_capability": 150}, "percentile"),
    ({"ale": -1}, "negative"),
    ({"ale": 1, "risk": 3}, "unknown FAIR factor"),
])
def test_invalid_models_are_rejected(data, message):
    with pytest.raises(FairError, match=message):
        FairModel.parse(data)
