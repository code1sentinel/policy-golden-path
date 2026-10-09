"""codify: turn a legacy policy into draft OSCAL control statements, from the command line.

    codify policy.docx                       summary and every draft, as text
    codify policy.docx -f oscal -o out.json  the OSCAL catalog
    codify policy.docx -f report             Markdown conversion report
    codify policy.csv -f xlsx -o out.xlsx    one row per control
    codify catalog.json -f report            reopen a saved catalog
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, api
from .classify import TYPE_LABELS
from .project import summary


def _text(project: dict, scores: dict) -> str:
    s = summary(project)
    by_type = s["by_type"]
    lines = [f"{project['title']}",
             f"{s['clauses']} clauses -> {s['controls']} draft controls "
             f"({by_type['requirement']} requirement clauses, {s['duplicates']} duplicate; {s['context']} context; "
             f"{by_type['not-a-control']} not controls)", ""]
    by_clause: dict[str, list[dict]] = {}
    for c in project["controls"]:
        by_clause.setdefault(c["clause"], []).append(c)
    for clause in project["clauses"]:
        kind = "Duplicate of " + clause["duplicate_of"] if clause.get("duplicate_of") else TYPE_LABELS[clause["type"]]
        lines.append(f"{clause['id']}  [{kind}]  {clause['text']}")
        for c in by_clause.get(clause["id"], []):
            lines.append(f"    {c['id']:8} {scores[c['id']]['confidence']:4.0%}  {c['text']}")
            if c.get("guidance"):
                lines.append(f"             guidance: {c['guidance']}")
            for note in c.get("notes", []):
                lines.append(f"             - {note}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="codify", description="Turn a legacy policy into draft OSCAL control statements.")
    p.add_argument("policy", help="a policy (.docx, .csv, .xlsx or text) or a saved OSCAL catalog (.json)")
    p.add_argument("-f", "--format", choices=("text", "oscal", "report", "csv", "xlsx"), default="text")
    p.add_argument("-o", "--output", help="write to this file instead of standard output")
    p.add_argument("--version", action="version", version=f"codify {__version__}")
    args = p.parse_args(argv)

    path = Path(args.policy)
    try:
        data = path.read_bytes()
    except OSError as exc:
        print(f"codify: {exc}", file=sys.stderr)
        return 2
    binary = path.suffix.lower() in (".docx", ".doc", ".xlsx", ".xls")
    body = {"action": "open", "name": path.name}
    if binary:
        import base64

        body["content_base64"] = base64.b64encode(data).decode()
    else:
        body["content"] = data.decode("utf-8-sig", errors="replace")
    try:
        opened = api.call(body)
        if args.format == "text":
            out: str | bytes = _text(opened["project"], opened["scores"])
        else:
            exported = api.call({"action": "export", "project": opened["project"],
                                 "format": "oscal" if args.format == "oscal" else args.format})
            if "content_base64" in exported:
                import base64

                out = base64.b64decode(exported["content_base64"])
            else:
                out = exported["content"]
    except api.BadRequest as exc:
        print(f"codify: {exc}", file=sys.stderr)
        return 1
    if isinstance(out, bytes) and not args.output:
        print("codify: Excel output needs -o FILE", file=sys.stderr)
        return 2
    if args.output:
        mode = "wb" if isinstance(out, bytes) else "w"
        with open(args.output, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as fh:
            fh.write(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
