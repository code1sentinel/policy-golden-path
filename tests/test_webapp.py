import json
import threading
import urllib.error
import urllib.request

import pytest

from vitals import webapp
from vitals.tabular import template


@pytest.fixture
def server():
    srv = webapp.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()
    srv.server_close()


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.headers, r.read()


def post(url, body, headers=None, raw=None):
    data = raw if raw is not None else json.dumps(body).encode()
    req = urllib.request.Request(url + "/api/assess", data,
                                 {"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def test_serves_page_assets_and_config(server):
    status, headers, body = get(server + "/")
    assert status == 200 and b"Batch health check" in body and b"Guides" in body and b"ihp.csa.gov.sg" in body
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    for name in ("app.js", "app.css"):
        assert get(f"{server}/{name}")[0] == 200
    config = json.loads(get(server + "/api/config")[2])
    assert config["kinds"]["risk-statement"] == "Risk statement" and "engines" not in config
    guides = json.loads(get(server + "/api/guides")[2])
    assert set(guides["guides"]) == {"control-statement", "identified-risk", "implementation", "risk-statement", "recommendation"}
    assert guides["statuses"]["not-yet"] == "Not yet adopted" and guides["adopted"] == 0.8
    status, headers, body = get(server + "/api/template.xlsx")
    assert body[:2] == b"PK" and "vitals-template.xlsx" in headers["Content-Disposition"]
    assert get(server + "/template.xlsx")[2][:2] == b"PK"  # relative links from the page
    assert get(server + "/template.csv")[2].decode() == template()
    status, headers, body = get(server + "/api/template.csv")
    assert body.decode() == template() and "attachment" in headers["Content-Disposition"]


def test_unknown_paths_404(server):
    for path in ("/nope", "/../pyproject.toml", "/static/../webapp.py"):
        with pytest.raises(urllib.error.HTTPError) as exc:
            get(server + path)
        assert exc.value.code == 404


def test_single_input_for_each_kind(server):
    status, data = post(server, {"mode": "single", "item": {
        "kind": "implementation", "control_id": "ac-2", "text": "Accounts are reviewed periodically as needed.",
        "policy_intent": "Access is reviewed at a frequency commensurate with risk.",
    }})
    assert status == 200
    [a] = data["assessments"]
    assert a["kind"] == "implementation" and a["file"] == "Single input"
    assert any("risk-based" in i for i in a["improvements"])
    assert "result" not in a and "threshold" not in a

    status, data = post(server, {"mode": "single", "item": {
        "kind": "recommendation", "text": "Consider improving log review.", "risk": "high",
        "owner": "SOC lead", "deadline": "2026-12-01", "risk_statement": "Logs are not reviewed.",
    }})
    a = data["assessments"][0]
    by = {c["name"]: c for c in a["criteria"]}
    assert by["owner"]["score"] == 1.0 and by["timeline"]["note"] == "recorded: 2026-12-01"
    assert a["ratings"] == {"risk": "high"}

    status, data = post(server, {"mode": "single", "item": {
        "kind": "risk-statement", "text": "Logs are not reviewed.", "likelihood": "high", "owner": "ignored"}})
    assert data["assessments"][0]["ratings"] == {"likelihood": "high"} and data["assessments"][0]["owner"] is None


def test_batch_mixes_oscal_and_csv_with_catalog_and_policy(server, examples):
    read = lambda n: {"name": n, "content": (examples / n).read_text()}  # noqa: E731
    status, data = post(server, {
        "mode": "batch",
        "documents": [read("ssp-example.json"), read("assessment-results-example.json"),
                      {"name": "rows.csv", "content": template()}, {"name": "broken.json", "content": "{"},
                      read("catalog-excerpt.json")],
        "catalog": read("catalog-excerpt.json"),
        "policy": read("policy-example.json"),
    })
    assert status == 200
    files = {f["name"]: f for f in data["files"]}
    assert files["ssp-example.json"]["count"] == 4 and files["rows.csv"]["count"] == 9
    assert "not valid JSON" in files["broken.json"]["error"]
    # a catalog uploaded as a document has its own control statements assessed
    assert files["catalog-excerpt.json"]["count"] == 3 and files["catalog-excerpt.json"]["error"] is None
    assert data["summary"]["total"] == 20
    assert {a["file"] for a in data["assessments"]} == {"ssp-example.json", "assessment-results-example.json",
                                                        "rows.csv", "catalog-excerpt.json"}
    au6 = next(a for a in data["assessments"] if a["item"] == "au-6 [Splunk]")
    assert au6["policies"] == ["ISP-09"]  # policy applied
    assert "# Vitals: health check" in data["markdown"]


@pytest.mark.parametrize("body, status, message", [
    ({"mode": "batch", "documents": [{"name": "a.xlsx", "content_base64": "not base64!"}]}, 400, "not valid base64"),
    ({"mode": "single", "item": {"text": ""}}, 400, "enter the text"),
    ({"mode": "single", "item": {"kind": "finding", "text": "x"}}, 400, "unknown kind"),
    ({"mode": "batch", "documents": []}, 400, "at least one file"),
    ({"mode": "batch", "documents": [{"name": "a.json", "content": "{}"}],
      "catalog": {"name": "c.json", "content": "{}"}}, 400, "catalog c.json"),
    ({"mode": "other"}, 400, "'mode'"),
])
def test_bad_requests(server, body, status, message):
    code, data = post(server, body)
    assert code == status and message in data["error"]


def test_rejects_cross_origin_non_json_and_oversized(server, monkeypatch):
    code, data = post(server, {"mode": "single", "item": {"text": "x"}}, {"Origin": "https://evil.example"})
    assert code == 403
    code, data = post(server, None, {"Content-Type": "text/plain"}, raw=b"{}")
    assert code == 415
    monkeypatch.setattr(webapp, "MAX_BODY", 10)
    code, data = post(server, {"mode": "single", "item": {"text": "a long enough body"}})
    assert code == 413


def test_batch_reports_unreadable_workbook(server):
    import base64

    doc = {"name": "old.xls", "content_base64": base64.b64encode(b"\xd0\xcf\x11\xe0" + b"\0" * 50).decode()}
    code, data = post(server, {"mode": "batch", "documents": [doc,
                                                              {"name": "rows.csv", "content": template()}]})
    assert code == 200
    assert "old-style .xls" in data["files"][0]["error"] and data["files"][1]["count"] == 9


def test_cli_accepts_xlsx(tmp_path, capsys):
    from vitals.cli import main
    from vitals.tabular import template_xlsx

    path = tmp_path / "policies.xlsx"
    path.write_bytes(template_xlsx())
    assert main([str(path), "-f", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["total"] == 9


def test_cli_accepts_csv(tmp_path, capsys):
    from vitals.cli import main

    path = tmp_path / "rows.csv"
    path.write_text(template())
    assert main([str(path), "-f", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["total"] == 9
