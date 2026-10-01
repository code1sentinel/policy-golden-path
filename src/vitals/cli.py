from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import report
from .catalog import Catalog
from .policy import Policy, load_policies
from .service import assess_all, parse_document, prepare


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vitals",
        description="Score OSCAL control statements, risk statements and recommendations, "
                    "and list areas for improvement.",
    )
    p.add_argument("document", help="OSCAL catalog, assessment results or POA&M (JSON), "
                                    "a CSV or an Excel workbook (.xlsx) with one row per policy")
    p.add_argument("-c", "--catalog", help="OSCAL catalog (JSON) supplying control requirement text")
    p.add_argument("-p", "--policy", metavar="PATH",
                   help="policy file (JSON) giving the policy intent each control must meet")
    p.add_argument("-i", "--intent", metavar="TEXT",
                   help="a policy intent to apply to every statement (in addition to --policy)")
    p.add_argument("-f", "--format", choices=["table", "json", "markdown"], default="table")
    p.add_argument("-o", "--output", help="write the report here instead of stdout")
    p.add_argument("--assessment-results", metavar="PATH",
                   help="also write the results as OSCAL assessment-results observations")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        catalog = Catalog.load(args.catalog) if args.catalog else None
        statements = parse_document(args.document, Path(args.document).read_bytes())
        policies = load_policies(args.policy) if args.policy else []
        if args.intent:
            policies.append(Policy("--intent", args.intent.strip()))
        prepare(statements, catalog, policies)
    except (OSError, ValueError, KeyError) as exc:
        print(f"vitals: {exc}", file=sys.stderr)
        return 2

    assessments = assess_all(statements)

    rendered = {"table": report.to_table, "json": report.to_json, "markdown": report.to_markdown}[args.format](
        assessments
    )
    if args.output:
        Path(args.output).write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
    else:
        print(rendered)

    if args.assessment_results:
        Path(args.assessment_results).write_text(
            report.to_assessment_results(assessments, Path(args.document).name) + "\n", encoding="utf-8"
        )

    if not statements:
        print("vitals: nothing to assess in this document", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
