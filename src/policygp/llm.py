"""Claude-backed assessor: an LLM judge for implementation statements, risk statements and recommendations."""

from __future__ import annotations

import json

from .models import IMPLEMENTATION, RECOMMENDATION, RISK_STATEMENT, Assessment, CriterionResult, Statement

DEFAULT_MODEL = "claude-opus-5"
POLICY_CRITERION = "policy_intent"

_COMMON = """Judge only what the text says; do not give credit for things it implies but does not \
state. Score each criterion from 0 to 100 and give an overall confidence from 0 to 100 that the text \
does its job. Then list the areas for improvement, each a concrete change the author can make, tagged \
with the criterion it would improve, and give a two or three sentence rationale. Do not decide whether the text passes or fails."""

_IMPLEMENTATION = """You are an experienced security control assessor reviewing an implementation \
statement from an OSCAL system security plan or component definition: it should show how the control \
requirement is met today.

Criteria:
- coverage: every part of the control requirement is addressed, including organization-defined values.
- specificity: names the concrete tools, configurations, settings or procedures used.
- responsibility: names who performs, owns or approves the control activity.
- frequency: states when or how often the control operates, or what triggers it.
- evidence: identifies the records, logs or artefacts an assessor could inspect.
- implemented: states as fact what operates today. Mark down plans and intentions ("will", "plans \
to"), hedges ("should", "may", "as needed"), obligations that restate the requirement instead of \
describing it ("must", "shall"), and open-ended examples ("such as", "e.g.", "etc.") unless the \
statement says where the full set is defined.
- policy_intent: only when a <policy-intent> is given. The statement meets what the organization's \
own policy requires: its objective, and any specific commitments such as frequencies, time limits, \
retention periods, approvers or technologies. A statement that falls short of a commitment (for \
example annual reviews where the policy requires quarterly) scores low. When the policy is \
risk-based (for example "commensurate with risk") rather than fixed, the statement must say how \
risk is rated (tiers, classification or criticality), give each tier a concrete frequency or time \
limit, and say who sets the tiers and when they are revisited; "based on risk" alone scores low.

Coverage matters most: a statement that is specific but misses part of the requirement should not \
score highly.

""" + _COMMON

_RISK = """You are an experienced security assessor reviewing the risk statement of a risk in OSCAL \
assessment results or a plan of action and milestones. It should let a reader who was not there \
understand what is wrong, why, and what it could cost.

Criteria:
- condition: what is wrong, stated as fact with the evidence found (samples, counts, observations).
- criteria: the control or policy requirement that is not met, described in its terms. When a \
<requirement> or <policy-intent> is given, the condition should be stated against it.
- cause: why the condition exists, specific enough for a recommendation to address it.
- threat: who or what could exploit the weakness, and how likely that is.
- impact: the effect on this system's confidentiality, integrity, availability or operations, and \
on which data or service.
- scope: which systems, accounts or components are affected, and how many.
- rating: the likelihood and impact ratings given are present and consistent with what the statement \
describes (a "low" rating should not describe fraudulent payments).
- clarity: factual and precise; no vague wording, no open-ended examples, and no remediation advice \
(that belongs in the recommendation). Conditional words such as "could" are fine when describing \
what a threat could do.

""" + _COMMON

_RECOMMENDATION = """You are an experienced security assessor reviewing a recommendation (an OSCAL \
remediation with lifecycle "recommendation") made in response to a risk. It should tell the owner \
exactly what to do and how everyone will know it is done.

Criteria:
- actionable: a concrete action, led by a verb ("Disable", "Configure"), not "consider" or "look into".
- root_cause: fixes the cause identified in the risk statement, not only the symptom.
- specific: names the system, setting or process to change.
- owner: names who is accountable.
- timeline: gives a target date, in proportion to the risk rating (a high risk warrants a sooner date).
- completion: states the evidence that will show the action is complete, so the risk can be closed.
- clarity: no vague wording, no optional phrasing ("where possible", "consider"), and no open-ended \
examples.

""" + _COMMON

KINDS = {
    IMPLEMENTATION: (_IMPLEMENTATION,
                     ("coverage", "specificity", "responsibility", "frequency", "evidence", "implemented")),
    RISK_STATEMENT: (_RISK, ("condition", "criteria", "cause", "threat", "impact", "scope", "rating", "clarity")),
    RECOMMENDATION: (_RECOMMENDATION,
                     ("actionable", "root_cause", "specific", "owner", "timeline", "completion", "clarity")),
}

def output_schema(criteria: tuple[str, ...]) -> dict:
    return {
        "type": "object",
        "properties": {
            "confidence": {"type": "integer"},
            "criteria": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "enum": list(criteria)},
                        "score": {"type": "integer"},
                        "note": {"type": "string"},
                    },
                    "required": ["name", "score", "note"],
                    "additionalProperties": False,
                },
            },
            "improvements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "practice": {"type": "string", "enum": list(criteria)},
                        "text": {"type": "string"},
                    },
                    "required": ["practice", "text"],
                    "additionalProperties": False,
                },
            },
            "rationale": {"type": "string"},
        },
        "required": ["confidence", "criteria", "improvements", "rationale"],
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

    def criteria_for(self, statement: Statement) -> tuple[str, ...]:
        criteria = KINDS[statement.kind][1]
        if statement.kind == IMPLEMENTATION and statement.policy_intent:
            criteria += (POLICY_CRITERION,)
        return criteria

    def prompt(self, statement: Statement) -> str:
        s = statement
        if s.kind == IMPLEMENTATION:
            requirement = s.requirement or "(No catalog supplied. Use your knowledge of this control id.)"
            policy = ""
            if s.policy_intent:
                policy = (f"<policy-intent policies=\"{', '.join(s.policy_ids)}\">\n{s.policy_intent}\n"
                          "</policy-intent>\n\n")
            return (
                f"<control id=\"{s.control_id}\" part=\"{s.statement_id or s.control_id}\">\n{requirement}\n"
                f"</control>\n\n{policy}"
                f"<implementation component=\"{s.component or 'unspecified'}\">\n{s.text or '(empty)'}\n"
                "</implementation>"
            )
        ratings = ", ".join(f"{k}: {v}" for k, v in s.ratings.items()) or "none recorded"
        risk_title = s.title if s.kind == RISK_STATEMENT else s.risk_title
        header = (f"<risk title=\"{risk_title or ''}\" controls=\"{s.control_id or 'unspecified'}\">\n"
                  f"Ratings: {ratings}\n")
        if s.kind == RISK_STATEMENT:
            context = ""
            if s.requirement:
                context += f"<requirement>\n{s.requirement}\n</requirement>\n\n"
            if s.policy_intent:
                context += (f"<policy-intent policies=\"{', '.join(s.policy_ids)}\">\n{s.policy_intent}\n"
                            "</policy-intent>\n\n")
            return (header + f"</risk>\n\n{context}"
                    f"<risk-statement>\n{s.text or '(empty)'}\n</risk-statement>")
        return (header + f"Risk statement: {s.risk_statement or '(none)'}\n</risk>\n\n"
                f"<recommendation owner=\"{s.owner or 'not recorded'}\" deadline=\"{s.deadline or 'not recorded'}\">\n"
                f"{s.text or '(empty)'}\n</recommendation>")

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

    def assess(self, statement: Statement) -> Assessment:
        criteria_names = self.criteria_for(statement)
        verdict, engine, failure = self._call(KINDS[statement.kind][0], self.prompt(statement),
                                              output_schema(criteria_names))
        if verdict is None:
            return Assessment(statement, 0.0, engine, improvements=[failure], rationale=failure)

        weight = 1.0 / len(criteria_names)
        criteria = [CriterionResult(c["name"], _clamp(c["score"]), weight, c.get("note", ""))
                    for c in verdict.get("criteria", [])]
        confidence = _clamp(verdict["confidence"])
        rationale = verdict.get("rationale", "")
        # Attach each improvement to its practice, so a practice with an open improvement is never "adopted".
        improvements = []
        by_name = {c.name: c for c in criteria}
        for item in verdict.get("improvements", []):
            practice, text = (item.get("practice"), item.get("text", "")) if isinstance(item, dict) else (None, item)
            if not text:
                continue
            improvements.append(text)
            if practice in by_name:
                by_name[practice].issues.append(text)
        return Assessment(statement, round(confidence, 4), engine, criteria, improvements, rationale.strip())
