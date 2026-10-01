"""Build the browser-only Codify site for GitHub Pages.

    python scripts/build_site.py --pyodide path/to/pyodide/package --out site

The site is static: the page runs Codify's Python in the browser with
Pyodide, which is served from the site itself, so nothing is uploaded and no
third party is contacted. Output:

    index.html, app.css, app.js   the web app, in browser mode
    codify.zip                    the Codify package, unpacked into Pyodide
    config.json, guide.json       what the local server returns from /api/*
    acme-policy.md, .docx         the demo policy
    pyodide/                      the Pyodide runtime
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from codify import api  # noqa: E402

PACKAGE = ROOT / "src" / "codify"
STATIC = PACKAGE / "static"
# Modules only the local server and command line need.
SERVER_ONLY = {"webapp.py", "cli.py", "__main__.py"}
PYODIDE_FILES = ("pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json")

# No third-party origins: fonts fall back to the system font, and Pyodide is served from the site.
CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; base-uri 'none'; form-action 'none'")


def build_index() -> str:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    html = html.replace('<html lang="en">', '<html lang="en" data-mode="browser">', 1)
    # Drop the Google Fonts links: the site makes no third-party requests.
    lines = [ln for ln in html.splitlines() if "fonts.googleapis.com" not in ln]
    html = "\n".join(lines) + "\n"
    meta = f'  <meta http-equiv="Content-Security-Policy" content="{CSP}">\n'
    return html.replace('  <meta name="viewport"', meta + '  <meta name="viewport"', 1)


def build_package_zip(dest: Path) -> None:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PACKAGE.glob("*.py")):
            if path.name not in SERVER_ONLY:
                zf.write(path, f"codify/{path.name}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--pyodide", required=True, type=Path, help="directory holding the Pyodide npm package files")
    p.add_argument("--out", default=ROOT / "site", type=Path, help="output directory (default: site/)")
    args = p.parse_args(argv)

    missing = [f for f in PYODIDE_FILES if not (args.pyodide / f).exists()]
    if missing:
        p.error(f"{args.pyodide} is missing Pyodide files: {', '.join(missing)}")

    out: Path = args.out
    if out.exists():
        shutil.rmtree(out)
    (out / "pyodide").mkdir(parents=True)

    (out / "index.html").write_text(build_index(), encoding="utf-8")
    for name in ("app.css", "app.js", "acme-policy.md", "acme-policy.docx"):
        shutil.copy2(STATIC / name, out / name)
    build_package_zip(out / "codify.zip")
    (out / "config.json").write_text(json.dumps(api.config()), encoding="utf-8")
    (out / "guide.json").write_text(json.dumps(api.guide()), encoding="utf-8")
    for name in PYODIDE_FILES:
        shutil.copy2(args.pyodide / name, out / "pyodide" / name)
    (out / ".nojekyll").write_text("")

    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"built {out} ({size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
