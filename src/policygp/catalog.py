"""Read control requirement text out of an OSCAL catalog."""

from __future__ import annotations

import json
import re
from pathlib import Path

_INSERT = re.compile(r"\{\{\s*insert:\s*param,\s*([^\s}]+)\s*\}\}")


class Catalog:
    """Maps control ids and statement part ids to their requirement prose."""

    def __init__(self, data: dict):
        root = data.get("catalog")
        if root is None:
            raise ValueError("not an OSCAL catalog: missing top-level 'catalog'")
        self._params: dict[str, str] = {}
        self._controls: dict[str, str] = {}
        self._parts: dict[str, str] = {}
        self._titles: dict[str, str] = {}
        for control in _walk_controls(root):
            for param in control.get("params", []):
                self._params[param["id"]] = _param_text(param)
        for control in _walk_controls(root):
            cid = control["id"].lower()
            self._titles[cid] = control.get("title", "")
            for part in control.get("parts", []):
                if part.get("name") == "statement":
                    self._controls[cid] = self._flatten(part)

    @classmethod
    def load(cls, path: str | Path) -> "Catalog":
        with open(path, encoding="utf-8") as fh:
            return cls(json.load(fh))

    def requirement(self, control_id: str, statement_id: str | None = None) -> str | None:
        if statement_id and statement_id.lower() in self._parts:
            return self._parts[statement_id.lower()]
        text = self._controls.get(control_id.lower())
        if text is None:
            return None
        title = self._titles.get(control_id.lower())
        # Some catalogs (the ASD ISM) title every control "Control: ism-1234"; that says nothing, so skip it.
        if not title or control_id.lower() in title.lower():
            return text
        return f"{title}: {text}"

    def __contains__(self, control_id: str) -> bool:
        return control_id.lower() in self._controls

    def _flatten(self, part: dict) -> str:
        pieces = []
        label = next((p["value"] for p in part.get("props", []) if p.get("name") == "label"), "")
        prose = self._substitute(part.get("prose", ""))
        if prose:
            pieces.append(f"{label} {prose}".strip())
        for sub in part.get("parts", []):
            pieces.append(self._flatten(sub))
        text = " ".join(p for p in pieces if p)
        if part.get("id"):
            self._parts[part["id"].lower()] = text
        return text

    def _substitute(self, prose: str) -> str:
        return _INSERT.sub(lambda m: self._params.get(m.group(1), f"[{m.group(1)}]"), prose)


def _walk_controls(node: dict):
    for group in node.get("groups", []):
        yield from _walk_controls(group)
    for control in node.get("controls", []):
        yield control
        yield from _walk_controls(control)


def _param_text(param: dict) -> str:
    if param.get("select"):
        choices = param["select"].get("choice", [])
        return "[Selection: " + "; ".join(choices) + "]"
    if param.get("label"):
        return f"[Assignment: {param['label']}]"
    return f"[{param['id']}]"
