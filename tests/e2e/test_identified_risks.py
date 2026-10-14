"""Identified risks as input: add, coverage flags, library suggestions, mapped links."""

import json

from playwright.sync_api import expect

from test_statement_library import CLAUSE, accept_current, open_pasted, wait_for_library_entries


def test_add_identified_risk_and_flag_uncovered(page):
    open_pasted(page, CLAUSE)
    page.click("[data-nav='risks']")
    expect(page.locator("#risks:not([hidden])")).to_be_visible()
    expect(page.locator("#risks")).to_contain_text("not a register")
    page.fill("#risk-statement", "Company data is breached due to human error.")
    page.fill("#risk-note", "From the workshop.")
    page.click("#risk-add")
    expect(page.locator(".risk-row")).to_contain_text("human error")
    expect(page.locator("#risks-coverage")).to_contain_text("no control")
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    assert saved["project"]["risks"][0]["statement"] == "Company data is breached due to human error."
    assert saved["project"]["risks"][0]["note"] == "From the workshop."
    assert saved["project"]["risks"][0]["id"] == "R-001"


def test_suggest_dialog_adds_library_statement_and_clears_coverage(page):
    open_pasted(page, CLAUSE)
    accept_current(page)
    wait_for_library_entries(page, 1)
    page.click("[data-nav='risks']")
    page.fill("#risk-statement", "Access that is no longer needed could be misused.")
    page.click("#risk-add")
    page.click("[data-suggest='R-001']")
    expect(page.locator("#risk-suggest-dialog")).to_be_visible()
    expect(page.locator("#risk-suggest-scenario")).to_contain_text("Access that is no longer needed")
    expect(page.locator(".risk-suggest__row")).to_contain_text("need-to-know")
    page.locator(".risk-suggest__row button", has_text="Add").first.click()
    page.locator("#risk-suggest-not-now").click()
    expect(page.locator("#risks-coverage")).to_contain_text("Every identified risk has a linked control")
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    linked = [c for c in saved["project"]["controls"] if "R-001" in (c.get("risk_ids") or [])]
    assert linked
    page.click("[data-nav='clauses']")
    page.locator("textarea.statement").wait_for()
    expect(page.locator(".mapped-risk")).to_be_visible()


def test_unlinked_control_is_flagged_in_related_table(page):
    open_pasted(page, CLAUSE)
    page.click("[data-nav='risks']")
    expect(page.locator("#risks-related, .coverage-flag")).to_contain_text("Unlinked")
