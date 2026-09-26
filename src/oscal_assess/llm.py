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

    def assess(self, statement: Statement, threshold: float) -> Assessment:
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": self.prompt(statement)}],
        )
        engine = f"claude:{response.model}"

        if response.stop_reason == "refusal":
            return Assessment(statement, 0.0, threshold, engine,
                              rationale="The model declined to assess this statement; review it manually.")
        if response.stop_reason == "max_tokens":
            return Assessment(statement, 0.0, threshold, engine,
                              rationale="The response was truncated before a verdict; review it manually.")

        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            verdict = json.loads(text)
        except json.JSONDecodeError:
            return Assessment(statement, 0.0, threshold, engine,
                              rationale="The model returned an unreadable verdict; review it manually.")

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
