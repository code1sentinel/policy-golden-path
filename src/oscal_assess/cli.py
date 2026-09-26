from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import DEFAULT_THRESHOLD, heuristic, report
from .catalog import Catalog
from .loader import load_statements
from .policy import Policy, attach_intents, load_policies


def _threshold(value: str) -> float:
    t = float(value.rstrip("%"))
    t = t / 100 if t > 1 else t
    if not 0 <= t <= 1:
        raise argparse.ArgumentTypeError("threshold must be between 0 and 1 (or 0% and 100%)")
    return t


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="oscal-assess",
        description="Score OSCAL implementation statements. Statements at or above the threshold pass.",
    )
    p.add_argument("document", help="OSCAL SSP or component definition (JSON)")
    p.add_argument("-c", "--catalog", help="OSCAL catalog (JSON) supplying control requirement text")
    p.add_argument("-p", "--policy", metavar="PATH",
                   help="policy file (JSON) giving the policy intent each control must meet")
    p.add_argument("-i", "--intent", metavar="TEXT",
                   help="a policy intent to apply to every statement (in addition to --policy)")
    p.add_argument("-t", "--threshold", type=_threshold, default=DEFAULT_THRESHOLD,
                   help="confidence needed to pass, e.g. 0.8 or 80%% (default: 0.8)")
    p.add_argument("-e", "--engine", choices=["heuristic", "claude"], default="heuristic",
                   help="heuristic: offline rubric (default); claude: LLM judge via the Anthropic API")
    p.add_argument("--model", default=None, help="Claude model for --engine claude (default: claude-opus-5)")
    p.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"],
                   help="effort level for --engine claude (default: medium)")
    p.add_argument("--workers", type=int, default=4, help="parallel requests for --engine claude")
    p.add_argument("-f", "--format", choices=["table", "json", "markdown"], default="table")
    p.add_argument("-o", "--output", help="write the report here instead of stdout")
    p.add_argument("--assessment-results", metavar="PATH",
                   help="also write findings as an OSCAL assessment-results document")
    p.add_argument("--no-fail", action="store_true", help="exit 0 even when statements fail")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        catalog = Catalog.load(args.catalog) if args.catalog else None
        statements = load_statements(args.document, catalog)
        policies = load_policies(args.policy) if args.policy else []
        if args.intent:
            policies.append(Policy("--intent", args.intent.strip()))
        attach_intents(statements, policies)
    except (OSError, ValueError, KeyError) as exc:
        print(f"oscal-assess: {exc}", file=sys.stderr)
        return 2

    if args.engine == "claude":
        from .llm import DEFAULT_MODEL, ClaudeAssessor

        assessor = ClaudeAssessor(model=args.model or DEFAULT_MODEL, effort=args.effort)
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            assessments = list(pool.map(lambda s: assessor.assess(s, args.threshold), statements))
    else:
        assessments = [heuristic.assess(s, args.threshold) for s in statements]

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
        print("oscal-assess: no implementation statements found", file=sys.stderr)
        return 2
    return 0 if args.no_fail or all(a.passed for a in assessments) else 1


if __name__ == "__main__":
    sys.exit(main())
