import json

from codify.cli import main


def test_text_summary(examples, capsys):
    assert main([str(examples / "acme-information-security-policy-2016.docx")]) == 0
    out = capsys.readouterr().out
    assert "43 clauses -> 38 draft controls" in out and "6.3  [Duplicate of 6.1]" in out
    assert "guidance: e.g. Veritas Backup Exec" in out


def test_writes_oscal_report_and_excel(examples, tmp_path):
    policy = str(examples / "acme-information-security-policy-2016.md")
    assert main([policy, "-f", "oscal", "-o", str(tmp_path / "c.json")]) == 0
    catalog = json.loads((tmp_path / "c.json").read_text())
    assert catalog["catalog"]["metadata"]["oscal-version"] == "1.1.2"
    assert main([str(tmp_path / "c.json"), "-f", "report", "-o", str(tmp_path / "r.md")]) == 0
    assert "conversion report" in (tmp_path / "r.md").read_text()
    assert main([policy, "-f", "xlsx", "-o", str(tmp_path / "c.xlsx")]) == 0
    assert (tmp_path / "c.xlsx").read_bytes()[:2] == b"PK"


def test_risks_flag_traces_controls_in_oscal(examples, tmp_path):
    policy = str(examples / "acme-information-security-policy-2016.md")
    risks = str(examples / "acme-risk-register.csv")
    out = tmp_path / "mixed.json"
    assert main([policy, "--risks", risks, "-f", "oscal", "-o", str(out)]) == 0
    catalog = json.loads(out.read_text())["catalog"]
    resources = catalog["back-matter"]["resources"]
    assert any(any(p.get("name") == "risk-id" and p.get("value") == "R-001" for p in r.get("props", []))
               for r in resources)
    risk_group = next(g for g in catalog["groups"] if g["id"] == "s-risks")
    assert risk_group["controls"]
    assert any(p.get("name") == "source-type" and p.get("value") == "risk"
               for c in risk_group["controls"] for p in c["props"])


def test_errors(tmp_path, capsys):
    assert main([str(tmp_path / "missing.docx")]) == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{")
    assert main([str(bad)]) == 1 and "not valid JSON" in capsys.readouterr().err
    good = tmp_path / "p.txt"
    good.write_text("1.1 Users shall lock screens.")
    assert main([str(good), "-f", "xlsx"]) == 2  # Excel needs -o
