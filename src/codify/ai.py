"""AI drafting with the person's own key: the prompt for one clause, and the reply turned into controls.

Codify never calls a provider itself. The page sends the prompt built here straight
from the browser to the provider the person chose, under their own key, and hands
the reply back to `from_reply`. One clause goes in each call: its text, its section
heading and the rule drafts, nothing else from the policy.

The AI fills in the parts of each statement (action, scope, limit, purpose) and
its guidance and risk; Codify puts the statement together, scores it like any
other draft and marks it as drafted by AI. Nothing it returns is reviewed or
accepted until a person says so.
"""

from __future__ import annotations

import json
import re

from .control import VERBS
from .project import _control_ids, draft_controls

MAX_REPLY = 50_000  # characters
MAX_CONTROLS = 12
MAX_PART = 1_000
PARTS = ("action", "scope", "limit", "purpose")
FIELDS = PARTS + ("guidance", "risk")

# The reply's shape. Every field is required (empty when it does not apply), as strict JSON schemas need.
SCHEMA = {
    "type": "object",
    "properties": {
        "controls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {**{f: {"type": "string"} for f in FIELDS},
                               "notes": {"type": "array", "items": {"type": "string"}}},
                "required": [*FIELDS, "notes"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["controls"],
    "additionalProperties": False,
}

SYSTEM = """You help GRC professionals turn legacy policy clauses into control statements, in the style of \
Singapore's IM8 Reform control catalog.

A control statement says what must be done, testably, and nothing about who does it or with which product. \
You give each statement in parts, which Codify joins in this order:

- action: the imperative verb that starts the statement, e.g. "Review", "Encrypt", "Back up", "Prohibit", "Require".
- scope: what the action applies to, e.g. "privileged user accounts", "laptops that store Restricted data", \
"users from sharing passwords" (after "Prohibit"), "approval from the system owner before granting access" (after "Require").
- limit: how often, how fast or when, e.g. "at least every [90] days", "within [N] days of a staff member leaving", \
"before use". Empty if the requirement is standing (configure, restrict, encrypt).
- purpose: why, starting with "to", e.g. "to remove access that is no longer needed". Empty if the clause gives no reason \
and none is plainly implied.

Rules:
1. One requirement per control. Split a clause that bundles several; do not split a list inside one requirement.
2. Start with the action. Never start with a subject ("The IT Department shall", "Users must").
3. Name no products, vendors or tools in the statement. Put them in guidance as examples ("e.g. Symantec Endpoint \
Protection"). Put who implements it in guidance too, if the clause says.
4. Keep every value the clause gives as a parameter in square brackets: "every 90 days" becomes "at least every [90] days". \
Replace vague timing ("regularly", "periodically", "promptly", "in a timely manner") with "[N]": "at least every [N] days", \
"within [N] days".
5. Drop hedges ("where practical", "should", "as appropriate") and subjective words ("adequate", "robust", "appropriate"); \
say what would make the requirement testable instead, and note what you dropped.
6. Do not invent requirements, values or scope the clause does not support. If something must be decided, write \
"[N]" or a short placeholder in brackets and say so in notes.
7. risk: one sentence on what could happen without the control, or empty if unclear.
8. notes: short, for the person reviewing: what you changed from the clause and what they should decide. Empty list if nothing.

Reply with JSON only, no prose and no code fence:
{"controls": [{"action": "", "scope": "", "limit": "", "purpose": "", "guidance": "", "risk": "", "notes": []}]}"""


def prompt(clause_id: str, text: str, heading: str = "") -> dict:
    """The system and user messages for one clause, the rule drafts included as a starting point."""
    rules = draft_controls(clause_id, text)
    lines = [f"Legacy clause {clause_id}" + (f' (section "{heading}")' if heading else "") + ":", text, ""]
    if rules:
        lines.append("Codify's rule-based drafts, a starting point you may improve, split or merge:")
        for c in rules:
            lines.append(f"- {c['text']}" + (f" (guidance: {c['guidance']})" if c["guidance"] else ""))
            lines.extend(f"    note: {n}" for n in c["notes"])
        lines.append("")
    lines.append("Write the control statements for this clause.")
    return {"system": SYSTEM, "user": "\n".join(lines), "schema": SCHEMA}


def _json(reply: str) -> dict:
    """The JSON object in a reply, allowing for a code fence or a sentence around it."""
    reply = reply.strip()
    try:
        return json.loads(reply)
    except json.JSONDecodeError:
        start, end = reply.find("{"), reply.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("the AI's reply has no JSON in it") from None
        try:
            return json.loads(reply[start:end + 1])
        except json.JSONDecodeError:
            raise ValueError("the AI's reply is not valid JSON") from None


def _part(value) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()[:MAX_PART]


def statement(parts: dict) -> str:
    """The parts joined into one statement: 'Review user accounts at least every [90] days.'"""
    words = " ".join(p for p in (_part(parts.get(k)).rstrip(".;, ") for k in PARTS) if p)
    if not words:
        return ""
    return words[0].upper() + words[1:] + "."


def from_reply(clause_id: str, reply: str, model: str = "") -> list[dict]:
    """Project controls from an AI reply, each marked as drafted by AI and left as a draft."""
    if len(reply) > MAX_REPLY:
        raise ValueError("the AI's reply is too long")
    data = _json(reply)
    items = data.get("controls") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ValueError("the AI's reply has no 'controls' list")
    by = f"Drafted by AI ({model})" if model else "Drafted by AI"
    controls = []
    for item in items[:MAX_CONTROLS]:
        if not isinstance(item, dict):
            continue
        text = statement(item)
        if not text:
            continue
        notes = [f"{by}: check it against the legacy clause before accepting it."]
        first = _part(item.get("action")).split(" ")[0].lower()
        if first and first not in VERBS:
            notes.append(f'"{_part(item.get("action"))}" is not a verb Codify recognises; start with the action.')
        raw = item.get("notes") if isinstance(item.get("notes"), list) else []
        notes += [n for n in (_part(x) for x in raw[:10]) if n]
        controls.append({"clause": clause_id, "text": text, "guidance": _part(item.get("guidance")),
                         "risk": _part(item.get("risk")), "who": "", "notes": notes,
                         "status": "draft", "origin": "ai"})
    if not controls:
        raise ValueError("the AI returned no control statements")
    return [{"id": cid, **c} for cid, c in zip(_control_ids(clause_id, len(controls)), controls)]
