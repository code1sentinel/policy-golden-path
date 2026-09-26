import json

from oscal_assess.cli import main


def test_exit_code_reflects_failures(examples, capsys):
    doc, cat = str(examples / "ssp-example.json"), str(examples / "catalog-excerpt.json")
    assert main([doc, "-c", cat]) == 1
    assert "2/4 passed at a 80% confidence threshold." in capsys.readouterr().out
    assert main([doc, "-c", cat, "--no-fail"]) == 0
    assert main([doc, "-c", cat, "-t", "0"]) == 0


def test_threshold_accepts_percent(examples, capsys):
    main([str(examples / "ssp-example.json"), "-t", "95%", "-f", "json"])
    assert json.loads(capsys.readouterr().out)["summary"]["threshold"] == 0.95


def test_json_markdown_and_assessment_results(examples, tmp_path, capsys):
    doc, cat = str(examples / "ssp-example.json"), str(examples / "catalog-excerpt.json")
    ar = tmp_path / "ar.json"
    md = tmp_path / "report.md"
    main([doc, "-c", cat, "-f", "markdown", "-o", str(md), "--assessment-results", str(ar)])

    assert "**2 of 4 passed**" in md.read_text()
    results = json.loads(ar.read_text())["assessment-results"]
    findings = results["results"][0]["findings"]
    states = {f["target"]["target-id"]: f["target"]["status"]["state"] for f in findings}
    assert states == {"ia-2": "satisfied", "au-6": "satisfied",
                      "ac-2_smt.j": "not-satisfied", "ac-2_smt.e": "not-satisfied"}
    assert results["metadata"]["oscal-version"] == "1.1.2"


def test_bad_input_exits_2(tmp_path, capsys):
    bad = tmp_path / "x.json"
    bad.write_text('{"catalog": {}}')
    assert main([str(bad)]) == 2
    assert main([str(tmp_path / "missing.json")]) == 2
