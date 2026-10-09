"""Removing the risk register (ADR 0011): leftover saves still open; no register surface."""

import json
from pathlib import Path

import pytest

from codify import api
from codify.cli import main
from codify.project import from_oscal, to_oscal

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_shell_has_no_risks_nav_or_register_export():
    assert 'data-nav="risks"' not in INDEX
    assert 'data-view="risks"' not in INDEX
    assert 'id="risks"' not in INDEX
    assert "Risk register" not in INDEX
    assert 'data-export="risks"' not in INDEX
    assert 'id="risk-dialog"' not in INDEX
    assert 'id="risk-import-dialog"' not in INDEX
    assert 'id="recommend-dialog"' not in INDEX
    assert "No risks yet" not in JS
    for nav in ("workspace", "clauses", "catalog", "library", "export", "guide"):
        assert f'data-nav="{nav}"' in INDEX


def test_copy_has_no_leftover_register_mentions():
    assert "Risks" not in INDEX
    assert "risk library" not in INDEX.lower()
    assert "risk register" not in INDEX.lower()
    assert "GLOSSARY" in JS
    glossary = JS.split("const GLOSSARY = {", 1)[1].split("};", 1)[0]
    assert "Risk" not in glossary
    assert ".risks-view" not in CSS
    assert "dropLegacyRegister" in JS
    assert "LEGACY_RISKS_KEY" in JS
    assert "codify:statements" in JS
    assert "codify:splash-seen" in JS


def test_clean_project_drops_malformed_risks_and_keeps_controls():
    opened = api.call({"action": "open", "text": "Users shall lock screens."})
    project = opened["project"]
    project["risks"] = "not-a-list"
    project["controls"][0]["source_type"] = "risk"
    project["controls"][0]["risk_id"] = "R-001"
    project["controls"][0]["risk"] = "Screens left unlocked."
    scored = api.call({"action": "score", "project": project})
    assert "scores" in scored
    saved = api.call({"action": "export", "format": "oscal", "project": project})
    catalog = json.loads(saved["content"])["catalog"]
    resources = catalog.get("back-matter", {}).get("resources", [])
    assert not any(any(p.get("name") == "risk-id" for p in r.get("props", [])) for r in resources)
    assert "risks" not in api.call({"action": "open", "name": saved["name"], "content": saved["content"]})["project"]
    again = api.call({"action": "score", "project": {**project, "risks": [{"title": "x"}]}})
    assert again["scores"]


def test_legacy_mixed_catalog_opens_without_a_register():
    raw = json.loads((FIXTURES / "legacy-mixed-clause-risk.json").read_text())
    project = from_oscal(raw)
    assert "risks" not in project
    texts = [c["text"] for c in project["controls"]]
    assert any("lock screens" in t.lower() for t in texts)
    assert any("Restrict access" in t for t in texts)
    assert all(c.get("source_type") == "clause" for c in project["controls"])
    assert all(not c.get("risk_id") for c in project["controls"])
    catalog = to_oscal(project)["catalog"]
    assert not any(g.get("id") == "s-risks" or g.get("title") == "Risks" for g in catalog.get("groups", []))
    resources = catalog.get("back-matter", {}).get("resources", [])
    assert not any(any(p.get("name") == "risk-id" for p in r.get("props", [])) for r in resources)


def test_legacy_risk_only_catalog_keeps_the_control_statement():
    raw = json.loads((FIXTURES / "legacy-risk-only.json").read_text())
    project = from_oscal(raw)
    assert "risks" not in project
    assert project["controls"]
    assert "Restrict access" in project["controls"][0]["text"]
    assert project["controls"][0]["source_type"] == "clause"


def test_register_actions_and_export_are_gone():
    with pytest.raises(api.BadRequest, match="'action' must be one of"):
        api.call({"action": "import_risks", "name": "x.csv", "content": "title,likelihood,impact\nA,1,1\n"})
    with pytest.raises(api.BadRequest, match="'action' must be one of"):
        api.call({"action": "suggest_risk_controls", "risk": {"title": "x", "likelihood": 1, "impact": 1}})
    with pytest.raises(api.BadRequest, match="'action' must be one of"):
        api.call({"action": "draft_risk_controls", "risk": {"title": "x", "likelihood": 1, "impact": 1}})
    opened = api.call({"action": "open", "text": "Users shall lock screens."})
    with pytest.raises(api.BadRequest, match="'format' must be"):
        api.call({"action": "export", "format": "risks", "project": opened["project"]})
    cfg = api.config()
    assert "risk_statuses" not in cfg
    assert "import_risks" not in api.ACTIONS


def test_cli_has_no_risks_flag(tmp_path, capsys):
    policy = tmp_path / "p.txt"
    policy.write_text("Users shall lock screens.")
    with pytest.raises(SystemExit) as exc:
        main([str(policy), "--risks", "nope.csv"])
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "--risks" in err
