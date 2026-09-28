"""The assessment pipeline shared by the command line and the web app."""

from __future__ import annotations

import json

from . import heuristic
from .catalog import Catalog
from .loader import extract_statements
from .models import Assessment, Statement
from .policy import Policy, attach_intents
from .tabular import parse_csv, parse_xlsx


def parse_document(name: str, content: str | bytes) -> list[Statement]:
    """Statements from one file: OSCAL JSON, a CSV (.csv) or an Excel workbook (.xlsx)."""
    lower = name.lower()
    if lower.endswith((".xlsx", ".xls")):
        if isinstance(content, str):
            raise ValueError("an Excel workbook must be read as bytes")
        return parse_xlsx(content, source=name)
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("file is not UTF-8 text; save it as UTF-8 CSV or as .xlsx") from None
    if lower.endswith(".csv"):
        return parse_csv(content, source=name)
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not valid JSON ({exc.msg} at line {exc.lineno})") from None
    if not isinstance(data, dict):
        raise ValueError("not an OSCAL document: expected a JSON object")
    if "policies" in data:
        raise ValueError("this is a policy file: add it as the policy file instead")
    return extract_statements(data)


def prepare(statements: list[Statement], catalog: Catalog | None = None,
            policies: list[Policy] | None = None) -> None:
    """Attach catalog requirements and policy intents, keeping any the statement already carries."""
    if catalog is not None:
        for s in statements:
            if s.requirement:
                continue
            texts = [catalog.requirement(cid, sid) for cid, sid in s.targets]
            s.requirement = " ".join(t for t in texts if t) or None
    if policies:
        untouched = [s for s in statements if not s.policy_intent]
        attach_intents(untouched, policies)


def assess_all(statements: list[Statement]) -> list[Assessment]:
    return [heuristic.assess(s) for s in statements]
