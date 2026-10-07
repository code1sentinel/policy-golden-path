"""GRC surfaces: risk Library vs Register, recommend modal, library detail."""

from playwright.sync_api import expect

from .test_risks import CSV
from .test_statement_library import (
    CLAUSE,
    accept_current,
    open_pasted,
    wait_for_library_entries,
)


def import_demo_risk(page, tmp_path):
    csv = tmp_path / "risks.csv"
    csv.write_text(CSV)
    page.click("[data-nav='risks']")
    page.set_input_files("#risk-file", str(csv))
    expect(page.locator("#risk-import-dialog")).to_contain_text("recognised", timeout=120_000)
    page.click("#risk-import-apply")
    expect(page.locator(".risk-table")).to_contain_text("R-001")


def test_risks_empty_state_lists_library_and_register(page):
    page.click("[data-nav='risks']")
    expect(page.locator("#risks-subnav")).to_contain_text("Library")
    expect(page.locator("#risks-subnav")).to_contain_text("Register")
    expect(page.locator("#risks")).to_contain_text("No risks yet")


def test_risk_library_add_opens_recommend_modal_and_accept_uses_library(page, tmp_path):
    import_demo_risk(page, tmp_path)
    expect(page.locator(".heatmap")).to_be_visible()
    page.click("[data-risk-pane='library']")
    expect(page.locator("#risks-title")).to_contain_text("Risk library")
    expect(page.locator(".risk-library-table")).to_contain_text("Unauthorised access")
    expect(page.locator(".risk-library-table .pill")).to_contain_text("Agency systems")
    page.locator(".risk-library-table .risk-add-controls").click()
    expect(page.locator("#recommend-dialog")).to_be_visible()
    expect(page.locator("#recommend-dialog")).to_contain_text("recommended control")
    expect(page.locator("#recommend-list")).to_contain_text("Restrict access", timeout=30_000)
    page.locator('#recommend-list [data-template="restrict-access"] button', has_text="Accept").click()
    expect(page.locator("textarea.statement")).to_be_visible()
    wait_for_library_entries(page)
    page.click("[data-nav='library']")
    expect(page.locator("#library .library-row")).to_have_count(1)
    expect(page.locator("#library-detail")).to_contain_text("R-001")


def test_statement_library_opens_a_detail_slideover(page):
    open_pasted(page, CLAUSE)
    statement = page.locator("textarea.statement").input_value()
    accept_current(page)
    page.click("[data-nav='library']")
    expect(page.locator("#library .library-row")).to_have_count(1)
    expect(page.locator("#library-detail")).to_be_visible()
    expect(page.locator("#library-detail")).to_contain_text(statement[:40])
    expect(page.locator("#library-detail")).to_contain_text("OSCAL 1.1.2")
    expect(page.locator("#library-detail")).to_contain_text("Clause")
    expect(page.locator("#library-detail .library-use")).to_be_visible()
    expect(page.locator("#library-pick-detail")).to_have_count(1)
