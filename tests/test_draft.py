import pytest

from codify.draft import base_form, draft, gerund


def texts(clause):
    return [d.text for d in draft(clause)]


@pytest.mark.parametrize("participle, base", [
    ("granted", "grant"), ("changed", "change"), ("applied", "apply"), ("kept", "keep"), ("used", "use"),
    ("configured", "configure"), ("logged", "log"), ("reviewed", "review"), ("stored", "store"),
])
def test_base_form(participle, base):
    assert base_form(participle) == base


def test_gerund():
    assert [gerund(v) for v in ("share", "log", "open", "back up")] == ["sharing", "logging", "opening", "backing up"]


def test_passive_becomes_active_and_bundles_split():
    assert texts("Access to Agency systems shall be granted on a need-to-know basis and approved by the user's "
                 "line manager.") == ["Grant access to Agency systems on a need-to-know basis.",
                                      "Require the user's line manager to approve access to Agency systems."]


def test_people_become_scope_and_prohibitions():
    assert texts("Users shall not share their passwords, write them down, or reuse their last 5 passwords.") == [
        "Prohibit users from sharing their passwords or writing them down.",
        "Prohibit users from reusing their last [5] passwords."]
    assert texts("Staff must lock their screens.") == ["Require staff to lock their screens."]


def test_the_organisation_is_the_who_not_the_subject():
    (d,) = draft("The IT Department shall disable the accounts of staff who leave, transfer, or are on leave.")
    assert d.text == "Disable the accounts of staff who leave, transfer, or are on leave."  # not split
    assert d.who == "The IT Department" and any("time limit" in n for n in d.notes)
    (r,) = draft("This policy shall be reviewed annually by the CIO.")
    assert r.text == "Review this policy annually." and r.who == "the CIO"


def test_vague_timing_becomes_a_parameter():
    assert texts("User accounts shall be reviewed regularly.") == ["Review user accounts at least every [N] days."]
    assert texts("Security patches shall be applied in a timely manner.") == ["Apply security patches within [N] days."]
    assert texts("System logs shall be retained for an appropriate period.") == \
        ["Retain system logs for at least [N] days."]


def test_legacy_values_become_parameter_values():
    assert texts("Accounts shall be locked after 5 failed login attempts.") == \
        ["Lock accounts after [5] failed login attempts."]
    assert texts("Passwords shall be changed every 90 days.") == ["Change passwords at least every [90] days."]


def test_tools_move_to_guidance():
    ds = draft("The IT Department shall back up all servers nightly using Veritas Backup Exec, and backup tapes "
               "shall be stored off-site.")
    assert [d.text for d in ds] == ["Back up all servers nightly.", "Store backup tapes off-site."]
    assert ds[0].guidance == "e.g. Veritas Backup Exec"
    (first, _) = draft("Symantec Endpoint Protection shall be installed on all servers and kept up to date.")
    assert first.text == "Install anti-malware software on all servers." and "Symantec" in first.guidance


def test_hedges_are_dropped_with_a_note():
    (d,) = draft("The IT Department should test patches before deployment where practical.")
    assert d.text == "Test patches before deployment."
    assert "'should', 'where practical'" in d.notes[0]


def test_second_modal_borrows_the_subject_and_phrasal_verbs_hold():
    assert texts("Privileged accounts shall only be used for administrative tasks and shall not be used for "
                 "email.") == ["Use privileged accounts only for administrative tasks.",
                               "Prohibit using privileged accounts for email."]
    assert texts("Data shall be backed up daily.") == ["Back up data daily."]


def test_untestable_wording_gets_a_note():
    (_, action) = draft("The IT Department will investigate reported incidents and take appropriate action.")
    assert any("'appropriate action' is not testable" in n for n in action.notes)
    (soft,) = draft("The use of USB drives is discouraged.")
    assert soft.text == "Prohibit the use of USB drives."
    assert any("'discourage' into 'prohibit'" in n for n in soft.notes)
