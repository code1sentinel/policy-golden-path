import pytest

from control_hygiene.catalog import Catalog
from control_hygiene.loader import extract_statements, load_statements


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
        extract_statements({"catalog": {}})


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
