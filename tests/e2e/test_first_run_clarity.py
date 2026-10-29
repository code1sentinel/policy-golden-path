"""First-run clarity: bugs, result step, review copy, export, glossary."""

from playwright.sync_api import expect

from conftest import add_flow_clauses, choose_clause_path, goto_review, goto_workspace


def test_demo_header_has_no_null_and_explains_counts(demo):
    summary = demo.locator("#work-summary")
    expect(summary).to_contain_text("38 control drafts")
    expect(summary).to_contain_text("26 requirement")
    expect(summary).not_to_contain_text("null")
    expect(summary).to_contain_text("not converted")


def test_sidebar_has_identified_risks_not_a_register(page):
    page.click("#start-from-risks")
    expect(page.locator("nav.sidebar__nav").get_by_role("button", name="Risk Entry")).to_be_visible()
    expect(page.locator("nav.sidebar__nav").get_by_role("button", name="Risks", exact=True)).to_have_count(0)
    expect(page.locator("#export-dialog")).not_to_contain_text("Risk register")


def test_clause_page_pastes_into_control_statements(page):
    choose_clause_path(page)
    expect(page.locator("#clause-paste")).to_have_attribute("placeholder", "Type or paste a clause")
    expect(page.locator("#clause-example")).to_contain_text("need-to-know")
    add_flow_clauses(page, "Access to systems shall be granted on a need-to-know basis.")
    page.click("#clause-continue")
    expect(page.locator("#flow:not([hidden])")).to_be_visible()
    expect(page.locator("#statements-title")).to_contain_text("for each clause")
    goto_review(page)
    goto_workspace(page)
    expect(page.locator("#work:not([hidden]) textarea.statement")).to_be_visible()


def test_review_has_one_primary_accept_and_plain_language(demo):
    expect(demo.locator(".editor__primary .btn--primary")).to_have_text("Accept")
    expect(demo.locator("#props .btn--primary")).to_have_count(0)
    expect(demo.locator(".editor__primary")).to_contain_text("Next control")
    expect(demo.locator("#props")).to_contain_text("How complete")
    expect(demo.locator("#editor")).to_contain_text("parts assessors look for")
    expect(demo.locator("#props")).not_to_contain_text("Use this drafted control statement")


def test_access_control_purpose_hint_is_not_brute_force(page):
    choose_clause_path(page)
    add_flow_clauses(page, "Access to systems shall be granted on a need-to-know basis.")
    page.click("#clause-continue")
    goto_review(page)
    goto_workspace(page)
    expect(page.locator("#editor")).not_to_contain_text("brute-force")
    expect(page.locator("#props")).not_to_contain_text("brute-force")


def test_export_marks_oscal_recommended(demo):
    demo.click("#export-open-top")
    row = demo.locator("#export-dialog .export-list__row").first
    expect(row).to_contain_text("recommended")
    expect(row).to_contain_text("OSCAL")
    expect(row).to_contain_text("Use this when")
    expect(demo.locator("#export-dialog")).not_to_contain_text("formula-escaped")
    expect(demo.locator("#export-dialog")).to_contain_text("Safe for Excel")


def test_glossary_explains_oscal_and_catalog_vs_library(demo):
    expect(demo.locator("abbr.term", has_text="OSCAL").first).to_have_attribute(
        "title", "A standard format from NIST for writing security controls so other GRC tools can read them.")
    expect(demo.locator("#stepper, .flow").locator("abbr.term", has_text="Clause").first).to_be_visible()
    expect(demo.locator("#catalog")).to_be_attached()
    expect(demo.locator("#library")).to_be_attached()
