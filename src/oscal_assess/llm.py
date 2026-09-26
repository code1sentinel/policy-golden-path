"""Claude-backed assessor: an LLM judge that reads the statement against the control."""

from __future__ import annotations

import json

from .models import Assessment, CriterionResult, Statement

DEFAULT_MODEL = "claude-opus-5"
CRITERIA = ("coverage", "specificity", "responsibility", "frequency", "evidence", "implemented")

SYSTEM_PROMPT = """You are an experienced security control assessor reviewing implementation \
statements from OSCAL system security plans and component definitions.

For each statement, decide how confident you are that it, as written, demonstrates the control \
requirement is met. Judge only what the text says; do not give credit for things it implies but \
does not state.

Score each criterion from 0 to 100:
- coverage: every part of the control requirement is addressed, including organization-defined values.
- specificity: names the concrete tools, configurations, settings or procedures used.
- responsibility: names who performs, owns or approves the control activity.
- frequency: states when or how often the control operates, or what triggers it.
- evidence: identifies the records, logs or artefacts an assessor could inspect.
- implemented: describes what operates today rather than plans, intentions or hedged language.

Then give an overall confidence from 0 to 100 that the statement satisfies the control. Coverage \
matters most: a statement that is specific but misses part of the requirement should not score \
highly. List the concrete gaps an author should fix, and a two or three sentence rationale."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "confidence": {"type": "integer"},
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "enum": list(CRITERIA)},
                    "score": {"type": "integer"},
                    "note": {"type": "string"},
                },
                "required": ["name", "score", "note"],
                "additionalProperties": False,
            },
        },
        "gaps": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["confidence", "criteria", "gaps", "rationale"],
    "additionalProperties": False,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value / 100.0))


class ClaudeAssessor:
    def __init__(self, model: str = DEFAULT_MODEL, effort: str = "medium", client=None):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.effort = effort

    def prompt(self, statement: Statement) -> str:
        requirement = statement.requirement or "(No catalog supplied. Use your knowledge of this control id.)"
        target = statement.statement_id or statement.control_id
        return (
            f"<control id=\"{statement.control_id}\" part=\"{target}\">\n{requirement}\n</control>\n\n"
            f"<implementation component=\"{statement.component or 'unspecified'}\">\n"
            f"{statement.text or '(empty)'}\n</implementation>"
        )

    def _call(self, system: str, prompt: str, schema: dict) -> tuple[dict | None, str, str]:
        """Return (verdict, engine name, failure reason). A failure always means verdict is None."""
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        engine = f"claude:{response.model}"
        if response.stop_reason == "refusal":
            return None, engine, "The model declined to assess this; review it manually."
        if response.stop_reason == "max_tokens":
            return None, engine, "The response was truncated before a verdict; review it manually."
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            return json.loads(text), engine, ""
        except json.JSONDecodeError:
            return None, engine, "The model returned an unreadable verdict; review it manually."

    def assess(self, statement: Statement, threshold: float) -> Assessment:
        verdict, engine, failure = self._call(SYSTEM_PROMPT, self.prompt(statement), OUTPUT_SCHEMA)
        if verdict is None:
            return Assessment(statement, 0.0, threshold, engine, rationale=failure)

        weight = 1.0 / len(CRITERIA)
        criteria = [
            CriterionResult(c["name"], _clamp(c["score"]), weight, c.get("note", ""))
            for c in verdict.get("criteria", [])
        ]
        return Assessment(
            statement,
            round(_clamp(verdict["confidence"]), 4),
            threshold,
            engine,
            criteria,
            list(verdict.get("gaps", [])),
            verdict.get("rationale", ""),
        )

    def risk_prompt(self, risk, by_control: dict[str, list[Statement]]) -> str:
        lines = [f"<risk id=\"{risk.id}\">", f"Title: {risk.title}"]
        for label, value in (("Description", risk.description), ("Asset", risk.asset),
                             ("Threat community", risk.threat_community), ("Threat event", risk.threat_event),
                             ("Effect", risk.effect)):
            if value:
                lines.append(f"{label}: {value}")
        lines.append("</risk>")
        for cid, factor in risk.controls.items():
            expected = f" expected-factor=\"{factor}\"" if factor else ""
            stmts = by_control.get(cid, [])
            body = "\n\n".join(f"[{s.key}] {s.text}" for s in stmts) or "(no implementation statement)"
            lines.append(f"\n<control id=\"{cid}\"{expected}>\n{body}\n</control>")
        return "\n".join(lines)

    def assess_risk(self, risk, by_control: dict[str, list[Statement]]):
        from .risk import ControlAlignment

        verdict, engine, failure = self._call(RISK_SYSTEM_PROMPT, self.risk_prompt(risk, by_control),
                                              RISK_OUTPUT_SCHEMA)
        if verdict is None:
            return 0.0, [], [failure], failure, engine
        by_id = {c["control_id"].lower(): c for c in verdict.get("controls", [])}
        controls = []
        for cid, expected in risk.controls.items():
            c = by_id.get(cid, {})
            score = _clamp(c.get("score", 0))
            controls.append(ControlAlignment(
                cid, expected, list(c.get("factors", [])), score,
                1.0 if (not expected or expected in c.get("factors", [])) else 0.0, score, score,
                [s.key for s in by_control.get(cid, [])], c.get("note", ""),
            ))
        return (round(_clamp(verdict["confidence"]), 4), controls, list(verdict.get("gaps", [])),
                verdict.get("rationale", ""), engine)


RISK_SYSTEM_PROMPT = """You are an experienced risk analyst who uses the FAIR (Factor Analysis of \
Information Risk) model. You are given a loss scenario and the implementation statements of the \
controls meant to treat it.

Decide how confident you are that the statements, as written, address this specific risk. For each \
control, identify which FAIR factors its statement credibly reduces:
- tef: threat event frequency, by avoidance or deterrence (the threat cannot reach or is discouraged).
- vulnerability: resistance strength, so a threat event is less likely to become a loss event.
- loss_magnitude: detection, response and containment that limit primary or secondary loss.

Score each control from 0 to 100 on how well its statement addresses this scenario: it must be about \
the asset and threat in question, and do what the expected factor (when given) says it should. A \
control with no statement scores 0. Then give an overall confidence from 0 to 100 that the controls \
together address the risk. Missing factors lower confidence: a scenario treated only by prevention, \
with nothing to detect or contain a loss, is not fully addressed. List concrete gaps and give a two or \
three sentence rationale. Judge only what the statements say."""

RISK_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "confidence": {"type": "integer"},
        "controls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "control_id": {"type": "string"},
                    "factors": {"type": "array", "items": {"type": "string",
                                                           "enum": ["tef", "vulnerability", "loss_magnitude"]}},
                    "score": {"type": "integer"},
                    "note": {"type": "string"},
                },
                "required": ["control_id", "factors", "score", "note"],
                "additionalProperties": False,
            },
        },
        "gaps": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["confidence", "controls", "gaps", "rationale"],
    "additionalProperties": False,
}
