import json

from policygp.cli import main


def test_reports_results_and_exits_zero(examples, capsys):
    doc, cat = str(examples / "ssp-example.json"), str(examples / "catalog-excerpt.json")
    assert main([doc, "-c", cat]) == 0
    out = capsys.readouterr().out
    assert "4 implementation statements: average confidence" in out
    assert "Areas for improvement" in out
    assert "PASS" not in out and "FAIL" not in out


def test_assessment_results_input(examples, capsys):
    assert main([str(examples / "assessment-results-example.json"), "-f", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert set(data["summary"]["by_kind"]) == {"risk-statement", "recommendation"}
    kinds = [a["kind"] for a in data["assessments"]]
    assert kinds == ["risk-statement", "recommendation", "risk-statement", "recommendation"]
    assert data["assessments"][1]["risk_title"] == "Leaver accounts can approve payments"


def test_markdown_and_oscal_observations(examples, tmp_path, capsys):
    doc, cat = str(examples / "ssp-example.json"), str(examples / "catalog-excerpt.json")
    ar = tmp_path / "ar.json"
    md = tmp_path / "report.md"
    main([doc, "-c", cat, "-f", "markdown", "-o", str(md), "--assessment-results", str(ar)])

    text = md.read_text()
    assert "## Areas for improvement" in text and "pass" not in text.lower().replace("passw", "")
    result = json.loads(ar.read_text())["assessment-results"]["results"][0]
    assert "findings" not in result
    obs = result["observations"]
    assert len(obs) == 4 and all(o["methods"] == ["EXAMINE"] for o in obs)
    props = {p["name"] for p in obs[0]["props"]}
    assert {"confidence", "assessed-kind", "control-id"} <= props
    assert result["reviewed-controls"]["control-selections"][0]["include-controls"]


def test_no_threshold_option(examples, capsys):
    import pytest

    with pytest.raises(SystemExit):
        main([str(examples / "ssp-example.json"), "--threshold", "0.8"])


def test_bad_input_exits_2(tmp_path, capsys):
    bad = tmp_path / "x.json"
    bad.write_text('{"catalog": {}}')
    assert main([str(bad)]) == 2
    assert main([str(tmp_path / "missing.json")]) == 2
    empty = tmp_path / "empty.json"
    empty.write_text('{"assessment-results": {"results": []}}')
    assert main([str(empty)]) == 2
    assert "nothing to assess" in capsys.readouterr().err


def test_policy_intent_is_applied(examples, capsys):
    doc, cat = str(examples / "ssp-example.json"), str(examples / "catalog-excerpt.json")
    main([doc, "-c", cat, "-f", "json"])
    before = {a["control_id"]: a for a in json.loads(capsys.readouterr().out)["assessments"]}

    main([doc, "-c", cat, "-p", str(examples / "policy-example.json"), "-f", "json"])
    after = {a["control_id"]: a for a in json.loads(capsys.readouterr().out)["assessments"]}
    assert after["au-6"]["confidence"] < before["au-6"]["confidence"]
    assert after["au-6"]["policies"] == ["ISP-09"]
    assert any("retained for at least 3 years" in i for i in after["au-6"]["improvements"])


def test_inline_intent_applies_to_every_statement(examples, capsys):
    main([str(examples / "ssp-example.json"), "-i", "Reviewed at least weekly.", "-f", "json"])
    data = json.loads(capsys.readouterr().out)
    assert all(a["policies"] == ["--intent"] for a in data["assessments"])


def test_bad_policy_file_exits_2(examples, tmp_path):
    bad = tmp_path / "p.json"
    bad.write_text('{"policies": [{"id": "P"}]}')
    assert main([str(examples / "ssp-example.json"), "-p", str(bad)]) == 2
