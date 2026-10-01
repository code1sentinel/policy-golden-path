import pytest

from codify.control import assess_control_statement, parts
from codify.models import Statement


def check(text, **kw):
    return assess_control_statement(Statement("x", text, **kw))


def crit(a, name):
    return next(c for c in a.criteria if c.name == name)


@pytest.mark.parametrize("text", [
    # IM8 Reform statements, as published
    "Backup all important data and systems at least every [Assignment: time period (days)] day(s), and store "
    "backups in a secure and separate location.",
    "Validate all application inputs to ensure that they match the expected type, structure, or format.",
    "Apply rate-limiting on all authentication mechanisms to deter brute-force attacks.",
    "Synchronise internal clocks to a common reference time source.",
    "Only allow access to production systems from managed devices.",
    "Where a service is internet-facing, restrict inbound traffic to the ports it needs.",
])
def test_im8_style_requirements_score_high(text):
    a = check(text, risk_statement="Linked risk.")
    assert a.confidence >= 0.85, a.improvements
    assert crit(a, "action_first").score == 1.0


def test_subject_first_and_tool_specific_text_is_redirected_to_the_implementation_statement():
    a = check("Workday termination events disable the Okta account automatically within 4 hours.")
    assert crit(a, "action_first").score == 0.0 and crit(a, "tool_neutral").score < 1
    assert any("Names okta, workday" in i for i in a.improvements)
    b = check("The IT team reviews access periodically.")
    assert any("not who does it" in i for i in b.improvements)
    assert a.confidence < 0.7 and b.confidence < 0.5


def test_recurring_activity_needs_how_often():
    assert crit(check("Review user access."), "testable").score == 0.0
    assert crit(check("Review user access regularly."), "testable").score == 0.0
    assert crit(check("Review user access at least every [90] days."), "testable").score == 1.0
    # nouns are not activities: "audit events", "patch management tools"
    assert crit(check("Log database audit events."), "testable").score == 1.0


def test_nothing_concrete_is_capped():
    a = check("Implement appropriate security measures.")
    assert a.confidence <= 0.4 and any("Say exactly what it applies to" in i for i in a.improvements)


def test_purpose_from_the_text_or_a_linked_risk():
    text = "Encrypt customer personal data at rest using managed keys."
    assert crit(check(text), "purpose").score == 0.0
    assert crit(check(text, risk_statement="Customer data could be disclosed."), "purpose").score == 1.0
    assert crit(check(text[:-1] + " to protect it if storage is compromised."), "purpose").score == 1.0


def test_bundled_requirements_are_flagged():
    a = check("Back up data daily, encrypt backups, test restores quarterly and report failures within 1 day.")
    assert crit(a, "single").score < 1 and any("Combines" in i for i in a.improvements)


def test_hedged_wording_is_penalised():
    a = check("Systems should be patched regularly where possible.")
    assert a.confidence < 0.4
    assert any("'should'" in i for i in a.improvements) and any("where possible" in i for i in a.improvements)


def test_filled_in_parameters_meet_the_policy():
    a = check("Review user access at least every [90] days, and disable accounts within [5] business days of "
              "staff leaving.", policy_intent="Access is reviewed at least every 90 days and removed within 5 "
                                              "business days of leaving.")
    assert "2/2 policy commitments met" in crit(a, "policy_intent").note


AU6 = ("a. Review and analyze system audit records [Assignment: frequency] for indications of [Assignment: "
       "inappropriate or unusual activity] and the potential impact of the inappropriate or unusual activity; "
       "b. Report findings to [Assignment: personnel or roles]; and c. Adjust the level of audit record review, "
       "analysis, and reporting within the system when there is a change in risk based on law enforcement "
       "information, intelligence information, or other credible sources of information.")


def test_every_part_of_the_control_is_assessed():
    from codify.text import requirement_parts

    assert [label for label, _ in requirement_parts(AU6)] == ["a", "b", "c"]
    assert requirement_parts("Validate all inputs.") == [("", "Validate all inputs.")]

    partial = check("Review and analyze audit records daily for unusual activity.", requirement=AU6)
    assert crit(partial, "coverage").note == "1 of 3 parts addressed (a)"
    assert any("Not addressed: parts b (Report findings to …); c (Adjust the level of audit record…)" in i
               for i in partial.improvements)

    whole = check("Review and analyze audit records daily for unusual activity and its potential impact, report "
                  "findings to the CISO within [1 business day], and adjust the level of review when threat "
                  "intelligence shows a change in risk.", requirement=AU6)
    assert crit(whole, "coverage").score == 1.0


def test_parts_of_a_statement():
    p = parts("Review privileged access at least every [90] days to remove access that is no longer needed.")
    assert p["action"] == "review" and p["scope"] == "privileged access"
    assert p["limit"] == "at least every [90] days" and p["purpose"] is None
    assert parts("Back up all servers nightly.")["action"] == "back up"
    assert parts("Apply rate-limiting to all logins to deter brute-force attacks.")["purpose"] == \
        "to deter brute-force attacks"
    assert parts("The IT team uses Okta to manage access.")["tools"] == "okta"
