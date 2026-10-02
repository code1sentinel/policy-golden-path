import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from codify import api

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_site  # noqa: E402


def test_handle_returns_results_and_errors_as_json():
    ok = json.loads(api.handle(json.dumps({"action": "open", "text": "1.1 Users shall lock screens."})))
    assert ok["summary"]["controls"] == 1
    assert json.loads(api.handle("{not json"))["status"] == 400


@pytest.fixture
def site(tmp_path):
    pyodide = tmp_path / "pyodide"
    pyodide.mkdir()
    for name in build_site.PYODIDE_FILES:
        (pyodide / name).write_text("stub")
    out = tmp_path / "site"
    assert build_site.main(["--pyodide", str(pyodide), "--out", str(out)]) == 0
    return out


def test_site_has_everything_the_page_loads(site):
    for name in ("index.html", "app.css", "app.js", "codify.zip", "config.json", "guide.json", "acme-policy.md",
                 "acme-policy.docx", ".nojekyll", *(f"pyodide/{f}" for f in build_site.PYODIDE_FILES)):
        assert (site / name).exists(), name
    assert json.loads((site / "config.json").read_text()) == api.config()


def test_index_runs_in_browser_mode_with_no_third_parties(site):
    html = (site / "index.html").read_text()
    assert '<html lang="en" data-mode="browser">' in html
    assert "Content-Security-Policy" in html and "'wasm-unsafe-eval'" in html
    assert "fonts.googleapis.com" not in html and "https://cdn" not in html
    # the only other origins it may reach are the AI providers, for AI drafting the person turns on
    csp = re.search(r'Content-Security-Policy" content="([^"]+)"', html).group(1)
    connect = next(d for d in csp.split("; ") if d.startswith("connect-src")).split()[1:]
    assert connect == ["'self'", "https://api.anthropic.com", "https://api.openai.com",
                       "https://generativelanguage.googleapis.com", "http://localhost:11434",
                       "http://127.0.0.1:11434"]
    assert "script-src 'self' 'wasm-unsafe-eval'" in csp


def test_app_js_treats_ollama_as_ready_without_a_key():
    js = (ROOT / "src/codify/static/app.js").read_text()
    assert "requiresKey: false" in js and "localhost:11434" in js
    # the merge left AI drafting "on" but not ready unless a key was set
    assert "const aiReady = () => ai.on && !!ai.key;" not in js


def test_browser_package_works_without_server_modules(site, tmp_path):
    with zipfile.ZipFile(site / "codify.zip") as zf:
        names = set(zf.namelist())
        zf.extractall(tmp_path / "unpacked")
    assert {"codify/api.py", "codify/xlsx.py", "codify/draft.py", "codify/data/im8-reform.json"} <= names
    assert not {"codify/webapp.py", "codify/cli.py"} & names
    # Import and run it in a clean interpreter that can only see the unpacked archive, as Pyodide does.
    # -I -S: no environment, no site-packages, so the installed codify cannot be picked up instead.
    unpacked = tmp_path / "unpacked"
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import json, codify.api as a; "
            "print(a.__file__); "
            "print(json.loads(a.handle(json.dumps({'action': 'open', 'text': '1.1 Logs shall be reviewed.'})))"
            "['summary']['controls']); "
            "print(json.loads(a.handle(json.dumps({'action': 'im8', 'text': 'Back up all servers nightly.'})))"
            "['suggestions'][0]['id'])")
    out = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(unpacked)],
                         capture_output=True, text=True, check=True)
    module_file, total, im8 = out.stdout.split()
    assert Path(module_file).is_relative_to(unpacked) and total == "1" and im8 == "br-1"


def test_build_refuses_incomplete_pyodide(tmp_path):
    (tmp_path / "pyodide").mkdir()
    with pytest.raises(SystemExit):
        build_site.main(["--pyodide", str(tmp_path / "pyodide"), "--out", str(tmp_path / "site")])
