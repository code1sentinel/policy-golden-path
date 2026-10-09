"""GRC surfaces: statement library detail (register UI is gone)."""

from playwright.sync_api import expect

from test_statement_library import CLAUSE, accept_current, open_pasted


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
    expect(page.locator("nav.sidebar__nav")).not_to_contain_text("Risks")
