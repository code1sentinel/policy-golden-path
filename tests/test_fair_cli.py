import json

from oscal_assess.fair_cli import Prompter, main


def scripted(answers):
    it = iter(answers)
    out = []
    return Prompter(ask=lambda prompt: next(it), say=out.append), out


def test_new_creates_register_from_answers(tmp_path):
    path = tmp_path / "risks.json"
    p, out = scripted([
        "SGD", "250000",                        # currency, appetite
        "", "Laptop theft exposes customer data", "staff laptops", "opportunistic thieves",
        "steal a laptop", "confidentiality", "",
        "sc-28=vulnerability, mp-6",            # controls
        "",                                     # per-risk appetite
        "3",                                    # full FAIR factors
        "", "10 20 40", "0.1",                 # derive TEF: contact frequency, probability of action
        "0.9",                                  # vulnerability directly
        "5000 20000 80000",                     # primary loss
        "",                                     # no secondary loss
        "y", "2",                               # residual, via LEF x LM
        "0.01 0.05 0.1", "5000",
        "n",                                    # no more risks
    ])
    assert main(["new", str(path), "--simulations", "500"], p) == 0

    data = json.loads(path.read_text())
    assert data["currency"] == "SGD" and data["appetite"] == 250000
    [risk] = data["risks"]
    assert risk["id"] == "R-001"
    assert risk["controls"] == {"sc-28": "vulnerability", "mp-6": None}
    assert risk["inherent"]["contact_frequency"] == {"min": 10.0, "most_likely": 20.0, "max": 40.0}
    assert risk["inherent"]["vulnerability"] == 0.9
    assert risk["residual"] == {"lef": {"min": 0.01, "most_likely": 0.05, "max": 0.1}, "lm": 5000.0}
    assert any("R-001 inherent  ALE mean SGD" in line for line in out)


def test_new_reprompts_bad_estimates_and_appends(tmp_path, examples):
    path = tmp_path / "risks.json"
    path.write_text((examples / "risks-example.json").read_text())
    p, out = scripted([
        "", "Insider fraud", "", "", "", "", "", "", "",
        "1", "lots", "9 1 3", "1000 5000 20000",   # ALE directly; two bad inputs first
        "n", "n",
    ])
    assert main(["new", str(path), "--simulations", "200"], p) == 0
    data = json.loads(path.read_text())
    assert [r["id"] for r in data["risks"]][-1] == "R-004"
    assert data["risks"][-1]["inherent"] == {"ale": {"min": 1000.0, "most_likely": 5000.0, "max": 20000.0}}
    assert any("Enter one number" in line for line in out)
    assert any("min <= most_likely <= max" in line for line in out)


def test_compute_json(examples, capsys):
    p, out = scripted([])
    assert main(["compute", str(examples / "risks-example.json"), "-f", "json", "--simulations", "500"], p) == 0
    data = json.loads(out[0])
    assert data["currency"] == "SGD"
    assert [r["id"] for r in data["risks"]] == ["R-001", "R-002", "R-003"]
    assert data["risks"][0]["reduction"] > 0


def test_compute_rejects_bad_register(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"risks": [{"title": "x", "inherent": {"lm": 1}}]}')
    assert main(["compute", str(bad)], Prompter()) == 2
    assert "give 'ale'" in capsys.readouterr().err
