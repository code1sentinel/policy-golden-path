"""Pull implementation statements out of OSCAL SSPs and component definitions."""

from __future__ import annotations

import json
from pathlib import Path

from .catalog import Catalog
from .models import Statement


def load_statements(path: str | Path, catalog: Catalog | None = None) -> list[Statement]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    statements = extract_statements(data)
    if catalog is not None:
        for s in statements:
            s.requirement = catalog.requirement(s.control_id, s.statement_id)
    return statements


def extract_statements(data: dict) -> list[Statement]:
    if "system-security-plan" in data:
        return _from_ssp(data["system-security-plan"])
    if "component-definition" in data:
        return _from_component_definition(data["component-definition"])
    raise ValueError(
        "unsupported OSCAL document: expected 'system-security-plan' or 'component-definition' at the top level"
    )


def _from_ssp(ssp: dict) -> list[Statement]:
    components = {
        c["uuid"]: c.get("title", c["uuid"])
        for c in ssp.get("system-implementation", {}).get("components", [])
    }
    out: list[Statement] = []
    for req in ssp.get("control-implementation", {}).get("implemented-requirements", []):
        cid = req["control-id"]
        for bc in req.get("by-components", []):
            out.append(_ssp_statement(cid, None, bc, components))
        for smt in req.get("statements", []):
            for bc in smt.get("by-components", []):
                out.append(_ssp_statement(cid, smt.get("statement-id"), bc, components))
        if not req.get("by-components") and not req.get("statements"):
            # Nothing describes how the control is met: record it so it fails visibly.
            out.append(Statement(cid, req.get("remarks", ""), "ssp", uuid=req.get("uuid")))
    return out


def _ssp_statement(cid: str, sid: str | None, bc: dict, components: dict[str, str]) -> Statement:
    return Statement(
        control_id=cid,
        statement_id=sid,
        text=bc.get("description", ""),
        source="ssp",
        uuid=bc.get("uuid"),
        component=components.get(bc.get("component-uuid", ""), bc.get("component-uuid")),
    )


def _from_component_definition(cd: dict) -> list[Statement]:
    out: list[Statement] = []
    for comp in cd.get("components", []):
        title = comp.get("title", comp.get("uuid"))
        for ci in comp.get("control-implementations", []):
            for req in ci.get("implemented-requirements", []):
                cid = req["control-id"]
                smts = req.get("statements", [])
                # When statements are present they carry the detail; the requirement-level
                # description is usually just a heading, so only assess it on its own.
                if not smts:
                    out.append(
                        Statement(cid, req.get("description", ""), "component-definition",
                                  uuid=req.get("uuid"), component=title)
                    )
                for smt in smts:
                    out.append(
                        Statement(cid, smt.get("description", ""), "component-definition",
                                  uuid=smt.get("uuid"), statement_id=smt.get("statement-id"),
                                  component=title)
                    )
    return out
