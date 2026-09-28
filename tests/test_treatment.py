import pytest

from vitals import api, heuristic
from vitals.models import IDENTIFIED_RISK, Statement, Treatment
from vitals.tabular import parse_csv

RISK = ("Ransomware delivered by phishing could encrypt the finance file servers and their online backups, "
        "halting payments processing for several days.")
BACKUP = Treatment("Backup policy", "Backups of critical systems are taken daily, kept offline and immutable, and "
                                    "restores are tested quarterly so services can be recovered within 24 hours.")
EMAIL = Treatment("Email security", "Inbound email is filtered for malicious attachments and links, and staff "
                                    "complete phishing awareness training annually.")
EDR = Treatment("EDR", control_statement="EDR on all servers alerts the SOC, which isolates infected hosts "
                                         "within 1 hour.")
ACCESS = Treatment("Access policy", "User access is reviewed quarterly.")


def check(*treatments, **ratings):
    ratings = ratings or {"likelihood": "high", "impact": "high"}
    return heuristic.assess(Statement("", RISK, "t", kind=IDENTIFIED_RISK, title="R-07", ratings=ratings,
                                      treatments=list(treatments)))


def crit(a, name):
    return next(c for c in a.criteria if c.name == name)


def test_untreated_and_unrelated_risks_score_low():
    for a in (check(), check(ACCESS)):
        assert a.confidence < 0.3 and crit(a, "treated").score == 0
    assert "No policy intent or control treats this risk" in check().improvements[0]
    assert any("'Access policy' does not appear to address" in i for i in check(ACCESS).improvements)


def test_controls_are_judged_together():
    # One control that only recovers leaves prevention and detection open ...
    alone = check(BACKUP)
    assert crit(alone, "layered").score < 0.5
    assert any("Nothing prevents" in i for i in alone.improvements)
    # ... which other controls sharing the risk supply.
    layered = check(BACKUP, EMAIL, EDR)
    assert crit(layered, "layered").score == 1.0 and layered.confidence > 0.9
    assert {t["label"]: t["types"] for t in layered.details["treatments"]}["EDR"] == ["detect", "respond"]


def test_a_stray_link_is_flagged_without_hiding_real_treatment():
    a = check(BACKUP, EMAIL, EDR, ACCESS)
    assert crit(a, "treated").note == "3 of 4 linked treatments address it"
    assert [t["relevant"] for t in a.details["treatments"]] == [True, True, True, False]


def test_high_risk_needs_a_firm_commitment_and_a_tier():
    vague = Treatment("Backup principle", "Critical systems are backed up at a frequency commensurate with their "
                                          "criticality, and backups are kept offline.")
    a = check(vague)
    assert crit(a, "proportionate").score < 0.5 and crit(a, "tolerance").score == 0
    assert any("is risk-based: say which tier" in i for i in a.improvements)


def test_low_risk_with_heavy_treatment_is_questioned():
    a = check(BACKUP, EMAIL, EDR, likelihood="low", impact="low")
    assert any("check the effort is justified" in i for i in a.improvements)


def test_unrated_risk_is_asked_for_a_rating():
    a = heuristic.assess(Statement("", "Staff could lose laptops.", "t", kind=IDENTIFIED_RISK,
                                   treatments=[Treatment("Encryption", "Laptops are encrypted with BitLocker.")]))
    assert crit(a, "rated").score < 1 and any("Record likelihood and impact" in i for i in a.improvements)


def test_csv_groups_rows_that_share_a_risk():
    rows = parse_csv(
        "risk id,identified risk,policy intent,control statement,risk statement,recommendation,title,likelihood,impact\n"
        f'R-07,"{RISK}","{BACKUP.policy_intent}",,,,Backup,high,high\n'
        f'R-07,,"{EMAIL.policy_intent}",The mail gateway blocks macros.,,,Email,,\n'
        'R-08,"Former staff could reuse accounts.","Access is removed within 1 day of leaving.",,,,Leavers,,\n')
    risks = [s for s in rows if s.kind == IDENTIFIED_RISK]
    assert [(r.title, len(r.treatments)) for r in risks] == [("R-07", 2), ("R-08", 1)]
    assert risks[0].ratings == {"likelihood": "high", "impact": "high"}
    assert risks[0].treatments[1].control_statement == "The mail gateway blocks macros."
    assert len(rows) == 3  # the email row also yields its control statement


def test_csv_risk_id_without_text_is_an_error():
    with pytest.raises(ValueError, match="R-09 has no identified risk text"):
        parse_csv("risk id,policy intent,control statement,risk statement,recommendation\nR-09,Backups daily.,,,\n")


def test_api_reads_treatments_one_per_line():
    item = {"kind": IDENTIFIED_RISK, "text": RISK, "likelihood": "high", "impact": "high",
            "treatments": f"Backup policy: {BACKUP.policy_intent}\n\n{EMAIL.policy_intent}"}
    a = api.assess({"mode": "single", "item": item})["assessments"][0]
    assert [t["label"] for t in a["treatments"]] == ["Backup policy", "Treatment 2"]
    assert a["kind"] == IDENTIFIED_RISK and a["risk_level"] == "high"
    with pytest.raises(api.BadRequest):
        api.single_statement({**item, "treatments": [{"label": "empty"}]})
