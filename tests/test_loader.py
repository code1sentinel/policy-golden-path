import pytest

from vitals.catalog import Catalog
from vitals.loader import extract_statements


def test_unsupported_document_raises():
    with pytest.raises(ValueError, match="unsupported OSCAL document"):
        extract_statements({"profile": {}})


def test_catalog_substitutes_params_and_indexes_parts(examples):
    catalog = Catalog.load(examples / "catalog-excerpt.json")
    assert catalog.requirement("ac-2", "ac-2_smt.j") == (
        "j. Review accounts for compliance with account management requirements "
        "[Assignment: frequency of account review];"
    )
    assert "AU-6" not in catalog.requirement("au-6")  # title, not id, is prefixed
    assert catalog.requirement("au-6").startswith("Audit Record Review, Analysis, and Reporting: a. Review")
    assert catalog.requirement("zz-9") is None
    assert "ia-2" in catalog


def test_placeholder_control_titles_are_left_out():
    from vitals.catalog import Catalog

    catalog = Catalog({"catalog": {"controls": [
        {"id": "ism-1997", "title": "Control: ism-1997",
         "parts": [{"id": "ism-1997_smt", "name": "statement", "prose": "The board defines roles."}]},
        {"id": "as-1", "title": "Input Validation",
         "parts": [{"id": "as-1_smt", "name": "statement", "prose": "Validate all inputs."}]},
    ]}})
    assert catalog.requirement("ism-1997") == "The board defines roles."
    assert catalog.requirement("AS-1") == "Input Validation: Validate all inputs."


def test_resolved_profile_param_values_replace_placeholders():
    # Resolved baselines (e.g. the CCCS profiles) set organization-defined values on params.
    catalog = Catalog({"catalog": {"controls": [
        {"id": "ac-2", "title": "Account Management",
         "params": [
             {"id": "ac-02_odp.06", "label": "time period", "values": ["twenty-four (24) hours"]},
             {"id": "ac-02_odp.07", "label": "frequency"},
         ],
         "parts": [{"id": "ac-2_smt", "name": "statement", "parts": [
             {"id": "ac-2_smt.h", "name": "item", "props": [{"name": "label", "value": "h."}],
              "prose": "Notify account managers within {{ insert: param, ac-02_odp.06 }};"},
             {"id": "ac-2_smt.j", "name": "item", "props": [{"name": "label", "value": "j."}],
              "prose": "Review accounts {{ insert: param, ac-02_odp.07 }}."},
         ]}]},
    ]}})
    assert catalog.requirement("ac-2", "ac-2_smt.h") == "h. Notify account managers within twenty-four (24) hours;"
    assert catalog.requirement("ac-2", "ac-2_smt.j") == "j. Review accounts [Assignment: frequency]."


def test_catalog_control_statements_carry_their_risk():
    from vitals.models import CONTROL_STATEMENT

    items = extract_statements({"catalog": {"groups": [{"controls": [
        {"id": "br-1", "title": "Backup",
         "params": [{"id": "br-1_prm_1", "label": "time period (days)"}],
         "props": [{"name": "risk-statement", "value": "Without backups, data could be lost."}],
         "parts": [{"id": "br-1_smt", "name": "statement",
                    "prose": "Backup all important data at least every {{ insert: param, br-1_prm_1 }} day(s)."}]},
        {"id": "br-9", "title": "Withdrawn", "parts": []},
    ]}]}})
    assert [(s.kind, s.key, s.risk_statement) for s in items] == [
        (CONTROL_STATEMENT, "br-1 [Backup]", "Without backups, data could be lost.")]
    assert items[0].text == "Backup all important data at least every [Assignment: time period (days)] day(s)."
