"""Pull assessable text out of OSCAL documents.

A catalog yields its own control statements; assessment results and POA&Ms
yield risk statements and recommendations.
"""

from __future__ import annotations

import json
from pathlib import Path

from .catalog import Catalog
from .findings import extract_findings
from .models import CONTROL_STATEMENT, Statement


def load_statements(path: str | Path, catalog: Catalog | None = None) -> list[Statement]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    statements = extract_statements(data)
    if catalog is not None:
        for s in statements:
            texts = [catalog.requirement(cid, sid) for cid, sid in s.targets]
            s.requirement = " ".join(t for t in texts if t) or None
    return statements


def extract_statements(data: dict) -> list[Statement]:
    if "catalog" in data:
        return _from_catalog(data)
    if "assessment-results" in data or "plan-of-action-and-milestones" in data:
        return extract_findings(data)
    raise ValueError(
        "unsupported OSCAL document: expected 'catalog', 'assessment-results' or "
        "'plan-of-action-and-milestones' at the top level"
    )


def _from_catalog(data: dict) -> list[Statement]:
    """A catalog's own control statements, each with the risk it treats when the catalog records one (IM8 does)."""
    return [
        Statement(control_id=cid, text=text, source="catalog", uuid=f"catalog:{cid}",
                  component=title or None, kind=CONTROL_STATEMENT, risk_statement=risk)
        for cid, title, text, risk in Catalog(data).controls()
    ]
