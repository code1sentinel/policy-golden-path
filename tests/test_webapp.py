import json
import threading
import urllib.error
import urllib.request

import pytest

from codify import webapp


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
    req = urllib.request.Request(url + "/api", data, {"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def test_serves_the_page_assets_and_demo(server):
    status, headers, body = get(server + "/")
    assert status == 200 and b"<title>Codify</title>" in body
    csp = headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp and headers["X-Content-Type-Options"] == "nosniff"
    assert "http://localhost:11434" in csp and "http://127.0.0.1:11434" in csp
    for name in ("app.js", "app.css", "acme-policy.md", "acme-policy.docx"):
        assert get(f"{server}/{name}")[0] == 200
    assert json.loads(get(server + "/api/config")[2])["version"]
    assert "action_first" in json.loads(get(server + "/api/guide")[2])["guide"]["practices"]


def test_api_round_trip(server):
    status, data = post(server, {"action": "open", "text": "1.1 Users shall change passwords regularly."})
    assert status == 200 and data["project"]["controls"][0]["text"] == \
        "Require users to change passwords at least every [N] days."


def test_refuses_unknown_paths_cross_origin_non_json_and_oversized(server, monkeypatch):
    with pytest.raises(urllib.error.HTTPError) as e:
        get(server + "/secret.py")
    assert e.value.code == 404
    assert post(server, {"action": "check", "text": "x"}, {"Origin": "https://evil.example"})[0] == 403
    assert post(server, None, {"Content-Type": "text/plain"}, raw=b"{}")[0] == 415
    assert post(server, {"action": "nope"})[0] == 400
    monkeypatch.setattr(webapp, "MAX_BODY", 10)
    assert post(server, {"action": "check", "text": "a long enough body"})[0] == 413
