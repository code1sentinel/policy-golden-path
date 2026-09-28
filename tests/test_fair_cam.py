"""FAIR-CAM view of an identified risk's treatments (prototype)."""

from vitals import fair_cam, heuristic
from vitals.models import IDENTIFIED_RISK, Statement, Treatment


def tags(text, intent=None):
    return fair_cam.functions(Treatment("t", policy_intent=intent, control_statement=text))


def test_treatments_are_tagged_with_what_they_do():
    assert tags("Require phishing-resistant multi-factor authentication for all cloud access.") == ["resist"]
    assert tags("CrowdStrike alerts the SOC, which isolates infected hosts within 1 hour.") == ["detect", "respond"]
    assert set(tags("Back up critical systems daily and test restoration quarterly.")) == {"limit", "variance"}
    assert "avoid" in tags("Place databases in private subnets with no internet access.")


def test_keeping_a_control_working_is_not_detecting_the_event():
    # alerting on drift and scanning for vulnerabilities are variance management, not detection
    assert tags("AWS Config alerts the cloud team to any drift within 15 minutes.") == ["variance"]
    assert "detect" not in tags("Tenable scans internet-facing servers for vulnerabilities weekly.")
    assert "respond" not in tags("Workday termination events disable the Okta account.")


def gaps(*treatments, impact=3, detectable=True):
    return " ".join(fair_cam.analyse(list(treatments), impact, detectable)["gaps"])


def test_dependency_and_reliability_gaps():
    detect_only = Treatment("Monitoring", control_statement="Alert the SOC on anomalous sign-ins.")
    assert "detection needs a response" in gaps(detect_only)
    backups = Treatment("Backups", "Backups are taken daily.", "Back up all servers daily.")
    assert "nothing makes it less likely" in gaps(backups)
    assert "keep working" in gaps(backups)  # nothing tests the backups
    mfa = Treatment("MFA", control_statement="Require multi-factor authentication for all access.")
    assert "impact is high" in gaps(mfa) and "impact is high" not in gaps(mfa, impact=1)
    assert "No policy or standard" in gaps(mfa) and "No policy or standard" not in gaps(backups)


def test_a_layered_and_maintained_set_has_no_gaps():
    ts = [Treatment("Backups", "Backups are kept offline.", "Back up servers daily and test restores quarterly."),
          Treatment("Email", "Email is filtered.", "Filter inbound email for malicious attachments."),
          Treatment("EDR", "Endpoints are monitored.", "EDR alerts the SOC, which isolates infected hosts.")]
    assert fair_cam.analyse(ts, 3)["gaps"] == []


def test_detection_gaps_are_skipped_where_detection_means_nothing():
    runbooks = Treatment("Runbooks", control_statement="Maintain runbooks for the settlement system.")
    assert "nothing detects" not in gaps(runbooks, detectable=False)


def test_identified_risk_carries_the_view_without_changing_its_score():
    risk = Statement("", "Ransomware could encrypt the finance file servers, halting payments for days.", "t",
                     kind=IDENTIFIED_RISK, ratings={"likelihood": "high", "impact": "high"},
                     treatments=[Treatment("Backups", "Backups are kept offline.",
                                           "Back up servers daily and test restores quarterly.")])
    a = heuristic.assess(risk)
    fc = a.details["fair_cam"]
    assert fc["map"]["limit"] == ["Backups"] and fc["map"]["variance"] == ["Backups"]
    assert a.to_dict()["fair_cam"]["gaps"] and "fair_cam" not in {c.name for c in a.criteria}
