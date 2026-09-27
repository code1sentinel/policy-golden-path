import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from policygp import api
from policygp.tabular import template

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_site  # noqa: E402


def test_handle_returns_results_and_errors_as_json():
    ok = json.loads(api.handle(json.dumps({"mode": "batch", "documents": [{"name": "t.csv", "content": template()}]})))
    assert ok["summary"]["total"] == 6 and ok["files"][0]["count"] == 6
    bad = json.loads(api.handle(json.dumps({"mode": "single", "item": {"text": ""}})))
    assert bad == {"error": "enter the text to assess", "status": 400}
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
    for name in ("index.html", "app.css", "app.js", "policygp.zip", "config.json", "guides.json",
                 "template.csv", "template.xlsx", ".nojekyll", *(f"pyodide/{f}" for f in build_site.PYODIDE_FILES)):
        assert (site / name).exists(), name
    assert json.loads((site / "config.json").read_text()) == api.config()


def test_index_runs_in_browser_mode_with_no_third_parties(site):
    html = (site / "index.html").read_text()
    assert '<html lang="en" data-mode="browser">' in html
    assert "Content-Security-Policy" in html and "'wasm-unsafe-eval'" in html
    assert "fonts.googleapis.com" not in html and "https://cdn" not in html


def test_browser_package_works_without_server_modules(site, tmp_path):
    with zipfile.ZipFile(site / "policygp.zip") as zf:
        names = set(zf.namelist())
        zf.extractall(tmp_path / "unpacked")
    assert "policygp/api.py" in names and "policygp/xlsx.py" in names
    assert not {"policygp/webapp.py", "policygp/cli.py"} & names
    # Import and run it in a clean interpreter that can only see the unpacked archive, as Pyodide does.
    # -I -S: no environment, no site-packages, so the installed policygp cannot be picked up instead.
    unpacked = tmp_path / "unpacked"
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import json, policygp.api as a; "
            "print(a.__file__); "
            "print(json.loads(a.handle(json.dumps({'mode': 'single', 'item': {'text': 'Logs are reviewed.'}})))"
            "['summary']['total'])")
    out = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(unpacked)],
                         capture_output=True, text=True, check=True)
    module_file, total = out.stdout.split()
    assert Path(module_file).is_relative_to(unpacked) and total == "1"


def test_build_refuses_incomplete_pyodide(tmp_path):
    (tmp_path / "pyodide").mkdir()
    with pytest.raises(SystemExit):
        build_site.main(["--pyodide", str(tmp_path / "pyodide"), "--out", str(tmp_path / "site")])
