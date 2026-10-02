"""Build src/codify/data/im8-reform.json from a checkout of GovTech's tech-standards repository.

    git clone https://github.com/GovTechSG/tech-standards
    python scripts/make_im8.py tech-standards

Keeps what mapping needs: each control's id, title, domain, statement (parameters
shown as [label]), guidance and risk statement, and its level in the low-risk and
medium-risk profiles (0 must-have, 1 should-have, 2 good-to-have). The catalog is
MIT-licensed by the Government Technology Agency of Singapore.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "src" / "codify" / "data" / "im8-reform.json"
SOURCE = "https://github.com/GovTechSG/tech-standards"


def prose(part: dict, params: dict[str, str]) -> str:
    """A part's prose with its items, parameters written as [label]."""
    text = part.get("prose", "")
    items = [prose(p, params) for p in part.get("parts", []) if p.get("name") == "item"]
    if items:
        text = f"{text} " + " ".join(f"({i + 1}) {item}" for i, item in enumerate(items))
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # Markdown links: keep the words
    text = re.sub(r"\{\{\s*insert:\s*param,\s*([\w.-]+)\s*\}\}", lambda m: f"[{params.get(m.group(1), 'value')}]", text)
    return re.sub(r"\s+", " ", text).strip()


def levels(root: Path) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for path in sorted((root / "profiles").glob("*-risk-level-*.json")):
        risk, level = re.match(r"(\w+)-risk-level-(\d)", path.stem).groups()
        profile = json.loads(path.read_text())["profile"]
        for imp in profile["imports"]:
            for inc in imp.get("include-controls", []):
                for cid in inc.get("with-ids", []):
                    out.setdefault(cid, {})[risk] = int(level)
    return out


def build(root: Path) -> dict:
    catalog = json.loads((root / "catalogs" / "im8-reform.json").read_text())["catalog"]
    level = levels(root)
    controls = []
    for group in catalog["groups"]:
        for c in group["controls"]:
            params = {p["id"]: p.get("label", "value") for p in c.get("params", [])}
            parts = {p["name"]: prose(p, params) for p in c.get("parts", [])}
            props = {p["name"]: p["value"] for p in c.get("props", [])}
            controls.append({"id": c["id"], "title": c["title"], "domain": group["id"],
                             "statement": parts.get("statement", ""), "guidance": parts.get("guidance", ""),
                             "risk": props.get("risk-statement", ""), "levels": level.get(c["id"], {})})
    try:
        commit = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = ""
    meta = catalog["metadata"]
    return {"title": meta["title"], "version": meta.get("version", ""), "uuid": catalog["uuid"],
            "source": SOURCE, "commit": commit, "license": "MIT, Government Technology Agency of Singapore",
            "domains": {g["id"]: g["title"] for g in catalog["groups"]}, "controls": controls}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("repo", type=Path, help="a checkout of GovTechSG/tech-standards")
    p.add_argument("--out", type=Path, default=OUT)
    args = p.parse_args(argv)
    data = build(args.repo)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out.parent / "LICENSE-im8-reform.txt").write_text((args.repo / "LICENSE").read_text())
    print(f"{len(data['controls'])} controls, version {data['version']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
