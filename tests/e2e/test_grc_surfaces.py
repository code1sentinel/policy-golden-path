"""GRC surfaces: statement library detail (register UI is gone)."""

from playwright.sync_api import expect

from test_statement_library import CLAUSE, accept_current, open_pasted


def test_statement_library_opens_a_detail_slideover(page):
    open_pasted(page, CLAUSE)
    statement = page.locator("textarea.statement").input_value()
    accept_current(page)
    page.click("#library-from")
    expect(page.locator("#library-pick")).to_be_visible()
    expect(page.locator("#library-pick")).to_contain_text(statement[:40])
    expect(page.locator("#library-pick-detail")).to_have_count(1)
    expect(page.locator("nav.sidebar__nav").get_by_role("button", name="Library")).to_have_count(0)
    expect(page.locator("#export-dialog")).to_have_count(1)
