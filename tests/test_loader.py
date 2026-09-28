import pytest

from vitals.catalog import Catalog
from vitals.loader import extract_statements, load_statements


def test_ssp_statements_resolve_components_and_requirements(examples):
    catalog = Catalog.load(examples / "catalog-excerpt.json")
    statements = load_statements(examples / "ssp-example.json", catalog)

    keys = [s.key for s in statements]
    assert keys == ["ia-2 [Okta]", "au-6 [Splunk]", "ac-2_smt.j [Payments Platform]", "ac-2_smt.e [Okta]"]
    assert all(s.source == "ssp" for s in statements)
    assert statements[0].requirement.startswith("Identification and Authentication (Organizational Users):")
    assert "personnel or roles required to approve" in statements[3].requirement


def test_component_definition_skips_heading_when_statements_exist(examples):
    statements = load_statements(examples / "component-definition-example.json")
    assert [s.statement_id for s in statements] == ["ac-2_smt.e", "ac-2_smt.j"]
    assert {s.component for s in statements} == {"Identity Platform"}


def test_component_definition_uses_description_without_statements():
    data = {"component-definition": {"components": [{
        "title": "Vault",
        "control-implementations": [{"implemented-requirements": [
            {"uuid": "u1", "control-id": "sc-12", "description": "Keys are managed in Vault."}
        ]}],
    }]}}
    [s] = extract_statements(data)
    assert (s.control_id, s.text, s.component) == ("sc-12", "Keys are managed in Vault.", "Vault")


def test_ssp_requirement_with_no_description_is_kept():
    data = {"system-security-plan": {"control-implementation": {"implemented-requirements": [
        {"uuid": "u1", "control-id": "ac-1"}
    ]}}}
    [s] = extract_statements(data)
    assert s.control_id == "ac-1" and s.text == ""


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
