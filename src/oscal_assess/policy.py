"""Policy intent: what the organization's own policy says a control must achieve.

A policy file maps policy statements to the controls that implement them:

    {
      "policies": [
        {
          "id": "ISP-05",
          "title": "Access Control Policy",
          "intent": "User access is reviewed at least quarterly ...",
          "controls": ["ac-2", "ac-2_smt.j"]
        }
      ]
    }

`controls` may name control ids (matching every statement of that control) or
statement ids (matching only that part). A policy without `controls` applies
to every statement. When several policies match a statement, all of their
intents apply.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .models import Statement


@dataclass
class Policy:
    id: str
    intent: str
    title: str = ""
    controls: list[str] = field(default_factory=list)  # lower-case control or statement ids; empty = all

    def applies_to(self, statement: Statement) -> bool:
        if not self.controls:
            return True
        ids = {statement.control_id.lower()}
        if statement.statement_id:
            ids.add(statement.statement_id.lower())
        return bool(ids & set(self.controls))


def load_policies(path: str | Path) -> list[Policy]:
    with open(path, encoding="utf-8") as fh:
        return parse_policies(json.load(fh))


def parse_policies(data) -> list[Policy]:
    items = data.get("policies") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ValueError("policy file: expected an object with a 'policies' list")
    policies = []
    for i, item in enumerate(items):
        pid = str(item.get("id") or f"policy-{i + 1}") if isinstance(item, dict) else f"policy-{i + 1}"
        if not isinstance(item, dict) or not str(item.get("intent", "")).strip():
            raise ValueError(f"policy file: {pid} needs a non-empty 'intent'")
        controls = item.get("controls", [])
        if not isinstance(controls, list):
            raise ValueError(f"policy file: {pid} 'controls' must be a list of control or statement ids")
        policies.append(Policy(pid, item["intent"].strip(), item.get("title", ""),
                               [str(c).lower() for c in controls]))
    return policies


def attach_intents(statements: list[Statement], policies: list[Policy]) -> None:
    """Set each statement's policy intent from every policy that applies to it."""
    for s in statements:
        matched = [p for p in policies if p.applies_to(s)]
        if matched:
            s.policy_ids = [p.id for p in matched]
            s.policy_intent = " ".join(p.intent for p in matched)
