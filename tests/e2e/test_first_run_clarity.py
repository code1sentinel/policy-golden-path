"""First-run clarity: bugs, result step, review copy, export, glossary."""

from playwright.sync_api import expect

from conftest import finish_open


def test_demo_header_has_no_null_and_explains_counts(demo):
    summary = demo.locator("#work-summary")
    expect(summary).to_contain_text("38 control drafts")
    expect(summary).to_contain_text("26 requirement")
    expect(summary).not_to_contain_text("null")
    expect(summary).to_contain_text("not converted")


def test_risks_breadcrumb_says_risks_not_library_register(page):
    page.click("[data-nav='risks']")
    expect(page.locator("#crumb")).to_contain_text("Risks")
    expect(page.locator("#crumb")).not_to_contain_text("Register")
    expect(page.locator("#crumb")).not_to_contain_text("Library")
    expect(page.locator("#risks-title")).to_contain_text("Risk")


def test_example_text_is_editable_and_codify_opens_a_result_step(page):
    box = page.locator("#paste-form textarea[name='text']")
    expect(box).not_to_have_attribute("placeholder", box.input_value())
    text = box.input_value()
    assert "Access to systems shall be granted" in text
    expect(page.locator("#paste-form")).to_contain_text("Example clause")
    page.click("#paste-submit")
    page.wait_for_selector("#result:not([hidden])", timeout=120_000)
    expect(page.locator("#result-title")).to_contain_text("what we drafted")
    expect(page.locator("#result-drafts")).to_contain_text("Grant access")
    page.click("#result-continue")
    expect(page.locator("#work:not([hidden]) textarea.statement")).to_be_visible()


def test_review_has_one_primary_accept_and_plain_language(demo):
    expect(demo.locator(".editor__primary .btn--primary")).to_have_text("Accept")
    expect(demo.locator("#props .btn--primary")).to_have_count(0)
    expect(demo.locator(".editor__primary")).to_contain_text("Next control")
    expect(demo.locator("#props")).to_contain_text("How complete")
    expect(demo.locator("#editor")).to_contain_text("parts assessors look for")
    expect(demo.locator("#props")).not_to_contain_text("Use this drafted control statement")


def test_access_control_purpose_hint_is_not_brute_force(page):
    page.fill("#paste-form textarea", "Access to systems shall be granted on a need-to-know basis.")
    page.click("#paste-submit")
    finish_open(page)
    expect(page.locator("#editor")).not_to_contain_text("brute-force")
    expect(page.locator("#props")).not_to_contain_text("brute-force")


def test_export_marks_oscal_recommended(demo):
    demo.click("#export-open-top")
    row = demo.locator("#export-dialog .export-list__row").first
    expect(row).to_contain_text("Recommended")
    expect(row).to_contain_text("OSCAL")
    expect(row).to_contain_text("Use this when")
    expect(demo.locator("#export-dialog")).not_to_contain_text("formula-escaped")
    expect(demo.locator("#export-dialog")).to_contain_text("Safe for Excel")


def test_glossary_explains_oscal_and_catalog_vs_library(demo):
    expect(demo.locator("abbr.term", has_text="OSCAL").first).to_have_attribute(
        "title", "A standard format from NIST for writing security controls so other GRC tools can read them.")
    expect(demo.locator(".flow abbr.term", has_text="Clause")).to_be_visible()
    demo.click("[data-nav='catalog']")
    expect(demo.locator("#catalog")).to_contain_text("this project's")
    expect(demo.locator("#catalog")).to_contain_text("Library")
    demo.click("[data-nav='library']")
    expect(demo.locator("#library")).to_contain_text("this device")
    expect(demo.locator("#library")).to_contain_text("catalog")
